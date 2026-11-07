import asyncio, logging, pathlib, time, uuid
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from .config import cfg
from .dialogue import Session, T
from .gnani import STTStream, TTS
from .calllog import log_call, queue_sms

log = logging.getLogger("krishi")
logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Krishi Mitra")
app.state.stt_factory = lambda: STTStream()
app.state.tts_factory = lambda: TTS()
FRAME = 1024
_active_calls = 0


@app.get("/health")
def health():
    return {"ok": True, "api_key_set": bool(cfg.api_key), "tts": f"{cfg.tts_model}/{cfg.tts_voice}", "stt_language": cfg.stt_language}


@app.get("/")
def sim():
    return HTMLResponse((pathlib.Path(__file__).parent / "sim.html").read_text(encoding="utf-8"))


class Call:
    def __init__(self, ws, stt, tts, phone=None):
        self.ws, self.stt, self.tts, self.phone = ws, stt, tts, phone
        self.id = uuid.uuid4().hex[:12]
        self.session = Session(cfg.escalation_number)
        self.mute_until = float("inf")
        self.last_event = time.monotonic()
        self.buf = bytearray()
        self.turns, self.silent_prompts, self.outcome = [], 0, "hangup"
        self.say_lock = asyncio.Lock()

    async def say(self, sentences, t0=None):
        async with self.say_lock:
            self.mute_until = float("inf")
            total, first = 0, None
            try:
                for s in sentences:
                    async for chunk in self.tts.stream_cached(s):
                        if first is None:
                            first = time.monotonic()
                        await self.ws.send_bytes(chunk)
                        total += len(chunk)
            except Exception as e:
                log.exception("tts failed")
                await self.ws.send_json({"type": "error", "where": "tts", "message": str(e)})
                now = time.monotonic()
                self.mute_until = now + 2.0
                self.last_event = self.mute_until
                return
            now = time.monotonic()
            self.mute_until = (first or now) + total / (2 * cfg.sample_rate) + 0.5
            self.last_event = self.mute_until
            lat = int((first - t0) * 1000) if (first and t0) else None
            self.turns.append({"who": "bot", "text": " ".join(sentences), "first_audio_ms_after_transcript": lat})
            await self.ws.send_json({"type": "reply", "text": " ".join(sentences), "first_audio_ms": lat})

    async def on_text(self, text, stt_latency, lang):
        t0 = time.monotonic()
        self.last_event, self.silent_prompts = t0, 0
        self.turns.append({"who": "farmer", "text": text, "stt_latency_ms": stt_latency, "lang": lang})
        await self.ws.send_json({"type": "transcript", "text": text, "stt_latency_ms": stt_latency, "lang": lang})
        r = self.session.respond(text)
        self.turns[-1]["meta"] = r.meta
        if r.sms and self.phone and r.meta.get("safety") != "escalated" and not r.meta.get("repeated"):
            queue_sms(self.id, self.phone[-4:], r.sms)
        await self.say(r.sentences, t0)
        if r.end:
            self.outcome = r.meta.get("state", "ended")
            await asyncio.sleep(max(0, self.mute_until - time.monotonic()))
            await self.ws.close()

    async def pump_client(self):
        while True:
            msg = await self.ws.receive()
            if msg["type"] == "websocket.disconnect":
                return
            b = msg.get("bytes")
            if b:
                if time.monotonic() < self.mute_until:
                    self.buf.clear()
                    continue
                self.buf += b
                while len(self.buf) >= FRAME:
                    await self.stt.send(bytes(self.buf[:FRAME]))
                    del self.buf[:FRAME]

    async def read_stt(self):
        async for ev in self.stt.events():
            t = ev.get("type")
            if t == "transcript":
                text = (ev.get("text") or "").strip()
                if text and time.monotonic() >= self.mute_until:
                    await self.on_text(text, ev.get("latency"), ev.get("detected_language_code"))
            elif t == "error":
                log.warning("stt error: %s", ev.get("message"))
                await self.ws.send_json({"type": "error", "where": "stt", "message": ev.get("message")})

    async def watchdog(self):
        fired_this_period = False
        while True:
            await asyncio.sleep(1)
            now = time.monotonic()
            if now > self.mute_until and now - self.last_event > cfg.silence_timeout_s:
                if not fired_this_period:
                    fired_this_period = True
                    self.silent_prompts += 1
                    if self.silent_prompts > 2:
                        self.outcome = "silence_timeout"
                        await self.say(T["bye"])
                        await asyncio.sleep(max(0, self.mute_until - time.monotonic()))
                        await self.ws.close()
                        return
                    await self.say(T["reprompt"])
                    self.last_event = time.monotonic()
            else:
                fired_this_period = False

    async def run(self):
        global _active_calls
        _active_calls += 1
        try:
            await self.stt.open()
        except Exception as e:
            await self.ws.send_json({"type": "error", "where": "stt_connect", "message": str(e)})
            await self.ws.close()
            return
        tasks = []
        try:
            await self.say(T["greeting"])
            tasks = [asyncio.create_task(f()) for f in (self.pump_client, self.read_stt, self.watchdog)]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for d in done:
                if not d.cancelled() and d.exception():
                    log.error("task ended: %r", d.exception())
        finally:
            _active_calls -= 1
            for t in tasks:
                t.cancel()
            for c in (self.stt, self.tts):
                try:
                    await c.close()
                except Exception:
                    pass
            log_call(self.id, self.turns, self.outcome)


@app.websocket("/ws/call")
async def ws_call(ws: WebSocket, phone: str = None, token: str = None):
    await ws.accept()
    if cfg.call_token and token != cfg.call_token:
        await ws.close(code=4401)
        return
    if _active_calls >= cfg.max_calls:
        await ws.close(code=4403)
        return
    await Call(ws, app.state.stt_factory(), app.state.tts_factory(), phone).run()
