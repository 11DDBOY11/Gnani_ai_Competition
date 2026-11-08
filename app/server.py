import asyncio, base64, hmac, json, logging, pathlib, re, time, uuid
from collections import OrderedDict
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
_last_call_outcome_by_client = OrderedDict()
_MAX_TRACE_CLIENTS = 256
STT_FAILURE_MESSAGE = "ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆಯಲ್ಲಿ ತಾಂತ್ರಿಕ ತೊಂದರೆ ಉಂಟಾಗಿದೆ. ದಯವಿಟ್ಟು ಈ ಕರೆ ಮುಗಿಸಿ, Call ಒತ್ತಿ ಹೊಸ ಕರೆ ಆರಂಭಿಸಿ."


@app.get("/health")
def health():
    return {"ok": True, "api_key_set": bool(cfg.api_key), "tts": f"{cfg.tts_model}/{cfg.tts_voice}", "stt_language": cfg.stt_language}


@app.get("/")
def sim():
    return HTMLResponse((pathlib.Path(__file__).parent / "sim.html").read_text(encoding="utf-8"))


class Call:
    def __init__(self, ws, stt, tts, phone=None, ack_mode=False, client_session_id=None,
                 follows_prior_playback_ack_timeout=False):
        self.ws, self.stt, self.tts, self.phone, self.ack_mode = ws, stt, tts, phone, ack_mode
        self.client_session_id = client_session_id
        self.follows_prior_playback_ack_timeout = follows_prior_playback_ack_timeout
        self.id = uuid.uuid4().hex[:12]
        self.session = Session(cfg.escalation_number)
        self.is_playing = True
        self.last_event = time.monotonic()
        self.buf = bytearray()
        self.turns, self.silent_prompts, self.outcome = [], 0, "hangup"
        self.say_lock = asyncio.Lock()
        self.pending_acks = {}  # resp_id -> asyncio.Event
        self.ack_started = {}
        self.active_response_id = None
        self.call_aborted = False
        self.stt_audio_sent = False
        self.browser_ws_closed = False

    def _safe_stt_error_message(self, message):
        safe = str(message or "unspecified STT failure")
        for secret in (cfg.api_key, cfg.call_token, self.phone):
            if secret:
                safe = safe.replace(str(secret), "[redacted]")
        safe = re.sub(r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)", "[redacted-number]", safe)
        return safe.replace("\r", " ").replace("\n", " ")[:500]

    def log_stt_failure(self, source, error_type, error_message, browser_ws_closed=None):
        log.error(
            "[%s] stt_failure_diagnostic failure_source=%s error_type=%s error_message=%s "
            "audio_sent_before_failure=%s browser_websocket_closed=%s client_session_id=%s response_id=%s",
            self.id, source, error_type or "unknown",
            self._safe_stt_error_message(error_message), self.stt_audio_sent,
            self.browser_ws_closed if browser_ws_closed is None else browser_ws_closed,
            self.client_session_id or "unavailable", self.active_response_id or "unavailable",
        )

    async def send_playback_event(self, data):
        log.info("[%s] server_message type=%s response_id=%s", self.id,
                 data.get("type"), data.get("response_id"))
        await self.ws.send_json(data)

    async def say(self, sentences, t0=None):
        async with self.say_lock:
            resp_id = uuid.uuid4().hex[:8]
            self.is_playing = True
            ack_event = asyncio.Event()
            self.pending_acks[resp_id] = ack_event
            full_text = " ".join(sentences)
            chunks_for_all_sentences, chunks_synthesized, first = [], 0, None
            self.active_response_id = resp_id
            synthesis_started = time.monotonic()
            log.info("[%s] tts_synthesis_start response_id=%s sentences=%d", self.id, resp_id, len(sentences))
            try:
                async for chunk in self.tts.stream_cached(full_text):
                    if first is None:
                        first = time.monotonic()
                    chunks_for_all_sentences.append(chunk)
                    chunks_synthesized += 1
            except Exception as e:
                log.error("[%s] tts_synthesis_error response_id=%s chunks=%d elapsed_s=%.3f error_type=%s",
                          self.id, resp_id, chunks_synthesized,
                          time.monotonic() - synthesis_started, type(e).__name__)
                await self.ws.send_json({"type": "error", "where": "tts", "message": str(e), "response_id": resp_id})
                self.pending_acks.pop(resp_id, None)
                if self.ack_mode:
                    await self.abort_and_close("tts_failure", resp_id)
                else:
                    self.is_playing = False
                    self.last_event = time.monotonic()
                return

            full_payload = b"".join(chunks_for_all_sentences)
            total_bytes = len(full_payload)
            log.info("[%s] tts_synthesis_complete response_id=%s chunks=%d bytes=%d elapsed_s=%.3f",
                     self.id, resp_id, chunks_synthesized, total_bytes, time.monotonic() - synthesis_started)
            lat = int((first - t0) * 1000) if (first and t0) else None
            self.turns.append({"who": "bot", "text": full_text, "first_audio_ms_after_transcript": lat})
            await self.send_playback_event({"type": "atomic_reply", "response_id": resp_id,
                                             "text": full_text})
            await self.ws.send_bytes(full_payload)

            audio_duration = total_bytes / (2 * cfg.sample_rate)
            if self.ack_mode:
                # Wait for client playback completion ack; do not assume playback on timeout
                timeout = min(audio_duration + 0.8, 3.0) if audio_duration < 1.0 else audio_duration + 4.0
                ack_started = time.monotonic()
                self.ack_started[resp_id] = ack_started
                ack_received = False
                try:
                    await asyncio.wait_for(ack_event.wait(), timeout=timeout)
                    ack_received = True
                    log.info("[%s] playback_ack_wait_complete response_id=%s elapsed_s=%.3f expected_duration_s=%.3f",
                             self.id, resp_id, time.monotonic() - ack_started, audio_duration)
                except asyncio.TimeoutError:
                    elapsed = time.monotonic() - ack_started
                    log.warning("[%s] playback_ack_timeout response_id=%s elapsed_s=%.3f expected_duration_s=%.3f timeout_s=%.3f",
                                self.id, resp_id, elapsed, audio_duration, timeout)
                    await self.abort_and_close("playback_ack_timeout", resp_id)
                    return
                finally:
                    self.pending_acks.pop(resp_id, None)
                    self.ack_started.pop(resp_id, None)
                    if ack_received:
                        self.is_playing = False
                        self.last_event = time.monotonic()
            else:
                # Fallback duration wait for non-ack callers (e.g. legacy test harnesses)
                if audio_duration > 0:
                    await asyncio.sleep(audio_duration)
                self.pending_acks.pop(resp_id, None)
                self.is_playing = False
                self.last_event = time.monotonic()

    async def abort_and_close(self, reason: str, response_id=None):
        """Abort active playback and cleanly close connection."""
        self.outcome = reason
        self.call_aborted = True
        self.is_playing = False
        try:
            await self.send_playback_event({"type": "playback_abort", "reason": reason,
                                            "response_id": response_id or self.active_response_id})
        except Exception:
            pass
        try:
            await self.ws.close(code=1000)
            self.browser_ws_closed = True
        except Exception:
            pass

    async def on_text(self, text, stt_latency, lang):
        if self.call_aborted:
            return
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
            try:
                await self.ws.close()
                self.browser_ws_closed = True
            except Exception:
                pass

    async def fail_stt(self, source, exc=None, error_type=None, error_message=None):
        """End a call whose streaming STT connection can no longer be trusted."""
        if self.call_aborted:
            return
        self.call_aborted = True
        self.is_playing = False
        self.outcome = "stt_stream_failed"
        error_type = error_type or (type(exc).__name__ if exc else "unknown")
        error_message = error_message or (str(exc) if exc else "STT failure")
        try:
            await self.ws.send_json({
                "type": "error", "where": "stt", "code": "stt_stream_failed",
                "fatal": True, "message": STT_FAILURE_MESSAGE,
            })
        except Exception:
            pass
        try:
            await self.ws.close(code=1011, reason="STT stream failed")
            self.browser_ws_closed = True
        except Exception:
            pass
        self.log_stt_failure(source, error_type, error_message)

    async def pump_client(self):
        while True:
            msg = await self.ws.receive()
            if msg["type"] == "websocket.disconnect":
                log.info("[%s] client_message type=disconnect response_id=%s", self.id, self.active_response_id)
                self.browser_ws_closed = True
                self.log_stt_failure("browser_websocket_disconnect", "WebSocketDisconnect",
                                     f"browser disconnected code={msg.get('code', 'unknown')}", True)
                return
            t_data = msg.get("text")
            if t_data:
                try:
                    data = json.loads(t_data)
                    message_type = data.get("type", "unknown")
                    resp_id = data.get("response_id")
                    log.info("[%s] client_message type=%s response_id=%s", self.id, message_type, resp_id)
                    if message_type == "playback_done":
                        self.ack_mode = True
                        ev = self.pending_acks.get(resp_id)
                        elapsed = (time.monotonic() - self.ack_started[resp_id]
                                   if resp_id in self.ack_started else None)
                        matched = ev is not None and resp_id == self.active_response_id
                        log.info("[%s] playback_done_received response_id=%s matched=%s elapsed_s=%s",
                                 self.id, resp_id, matched,
                                 f"{elapsed:.3f}" if elapsed is not None else "n/a")
                        if matched:
                            self.is_playing = False
                            ev.set()
                    elif message_type == "playback_abort":
                        log.info("[%s] playback_abort_received response_id=%s matched=%s",
                                 self.id, resp_id,
                                 resp_id in self.pending_acks and resp_id == self.active_response_id)
                        self.outcome = "client_playback_abort"
                        await self.abort_and_close("client_playback_abort", resp_id)
                        return
                except Exception:
                    pass
            b = msg.get("bytes")
            if b:
                log.info("[%s] client_message type=audio_frame response_id=%s bytes=%d intake_enabled=%s",
                         self.id, self.active_response_id, len(b), not self.is_playing)
                if self.is_playing or self.call_aborted:
                    self.buf.clear()
                    continue
                self.buf += b
                while len(self.buf) >= FRAME:
                    try:
                        await self.stt.send(bytes(self.buf[:FRAME]))
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        await self.fail_stt("stt_audio_send", e)
                        return
                    del self.buf[:FRAME]
                    self.stt_audio_sent = True

    async def read_stt(self):
        try:
            async for ev in self.stt.events():
                t = ev.get("type")
                if t == "transcript":
                    text = (ev.get("text") or "").strip()
                    if text and not self.is_playing and not self.call_aborted:
                        await self.on_text(text, ev.get("latency"), ev.get("detected_language_code"))
                elif t == "error":
                    await self.fail_stt(
                        "upstream_gnani_stt_stream",
                        error_type=ev.get("error_type") or "provider_error",
                        error_message=ev.get("message") or "STT stream returned an error event",
                    )
                    return
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await self.fail_stt("local_stt_receiver", e)

    async def watchdog(self):
        fired_this_period = False
        while True:
            await asyncio.sleep(1)
            now = time.monotonic()
            if not self.is_playing and (now - self.last_event > cfg.silence_timeout_s):
                if not fired_this_period:
                    fired_this_period = True
                    self.silent_prompts += 1
                    if self.silent_prompts > 2:
                        self.outcome = "silence_timeout"
                        await self.say(T["bye"])
                        await self.ws.close()
                        self.browser_ws_closed = True
                        self.log_stt_failure("other_task_watchdog", "TimeoutError",
                                             "silence watchdog closed the browser WebSocket", True)
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
            self.browser_ws_closed = True
            self.log_stt_failure("upstream_gnani_stt_connect", type(e).__name__, str(e), True)
            return
        tasks = []
        try:
            tasks = [asyncio.create_task(f()) for f in (self.pump_client, self.read_stt, self.watchdog)]
            await self.say(T["greeting"])
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for d in done:
                if not d.cancelled() and d.exception():
                    exc = d.exception()
                    self.log_stt_failure("other_task_exception", type(exc).__name__, str(exc))
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


class ExotelAgentStream:
    """Adapt Exotel's JSON/base64 AgentStream protocol to Call's PCM WebSocket API."""

    MEDIA_PACKET_BYTES = 3200

    def __init__(self, ws):
        self.ws = ws
        self.stream_sid = None
        self.call_sid = None
        self.active_response_id = None

    async def wait_for_start(self):
        while True:
            message = await self.ws.receive()
            if message["type"] == "websocket.disconnect":
                raise ConnectionError("Exotel disconnected before stream start")
            raw = message.get("text")
            if not raw:
                continue
            event = json.loads(raw)
            if event.get("event") == "stop":
                raise ConnectionError("Exotel stopped before stream start")
            if event.get("event") != "start":
                continue
            start = event.get("start") or {}
            media_format = start.get("media_format") or {}
            if (media_format.get("sample_rate") not in (None, "8000", 8000)
                    or media_format.get("bit_rate") not in (None, "16", 16)
                    or media_format.get("encoding") not in (None, "audio/x-raw")):
                raise ValueError("Exotel stream must use 8 kHz raw PCM at 16 bits")
            self.stream_sid = event.get("stream_sid") or start.get("stream_sid")
            self.call_sid = start.get("call_sid")
            if not self.stream_sid:
                raise ValueError("Exotel start event did not include stream_sid")
            return

    async def send_json(self, data):
        event_type = data.get("type")
        response_id = data.get("response_id")
        if event_type == "atomic_reply":
            self.active_response_id = response_id
        elif event_type == "playback_abort" and self.stream_sid:
            await self.ws.send_json({"event": "clear", "stream_sid": self.stream_sid})
        # Exotel callers have no simulator UI; text stays in the server call log.

    async def send_bytes(self, payload):
        if not self.stream_sid or not self.active_response_id:
            raise RuntimeError("Exotel audio arrived without an active response")
        packet_size = self.MEDIA_PACKET_BYTES
        for offset in range(0, len(payload), packet_size):
            chunk = payload[offset:offset + packet_size]
            if len(chunk) < packet_size:
                chunk += bytes(packet_size - len(chunk))
            encoded = base64.b64encode(chunk).decode("ascii")
            await self.ws.send_json({
                "event": "media",
                "stream_sid": self.stream_sid,
                "media": {"payload": encoded},
            })
        if not payload:
            silence = base64.b64encode(bytes(packet_size)).decode("ascii")
            await self.ws.send_json({
                "event": "media", "stream_sid": self.stream_sid,
                "media": {"payload": silence},
            })
        await self.ws.send_json({
            "event": "mark", "stream_sid": self.stream_sid,
            "mark": {"name": self.active_response_id},
        })

    async def receive(self):
        while True:
            message = await self.ws.receive()
            if message["type"] == "websocket.disconnect":
                return message
            raw = message.get("text")
            if not raw:
                continue
            event = json.loads(raw)
            kind = event.get("event")
            if kind == "stop":
                return {"type": "websocket.disconnect", "code": 1000}
            if kind == "media":
                media = event.get("media") or {}
                payload = media.get("payload")
                if payload:
                    return {"type": "websocket.receive", "bytes": base64.b64decode(payload)}
            elif kind == "mark":
                mark_name = (event.get("mark") or {}).get("name")
                if mark_name and mark_name == self.active_response_id:
                    return {
                        "type": "websocket.receive",
                        "text": json.dumps({"type": "playback_done", "response_id": mark_name}),
                    }
            # connected, start, dtmf, and unrelated marks need no action in this PCM dialogue.

    async def close(self, code=1000, reason=None):
        try:
            await self.ws.close(code=code, reason=reason or "")
        except Exception:
            pass


@app.websocket("/ws/call")
async def ws_call(ws: WebSocket, phone: str = None, token: str = None, ack: str = None,
                  client_session_id: str = None):
    await ws.accept()
    if cfg.call_token and token != cfg.call_token:
        await ws.close(code=4401)
        return
    if _active_calls >= cfg.max_calls:
        await ws.close(code=4403)
        return
    ack_mode = (ack in ("1", "true", "yes"))
    follows_timeout = bool(client_session_id and
                           _last_call_outcome_by_client.get(client_session_id) == "playback_ack_timeout")
    call = Call(ws, app.state.stt_factory(), app.state.tts_factory(), phone, ack_mode=ack_mode,
                client_session_id=client_session_id,
                follows_prior_playback_ack_timeout=follows_timeout)
    log.info("[%s] call_instance_created client_session_id=%s follows_prior_playback_ack_timeout=%s auto_reconnect=false",
             call.id, client_session_id or "unavailable", follows_timeout)
    await call.run()
    if client_session_id:
        _last_call_outcome_by_client[client_session_id] = call.outcome
        _last_call_outcome_by_client.move_to_end(client_session_id)
        while len(_last_call_outcome_by_client) > _MAX_TRACE_CLIENTS:
            _last_call_outcome_by_client.popitem(last=False)


@app.websocket("/exotel/media")
async def exotel_media(ws: WebSocket):
    await ws.accept()
    supplied_token = ws.query_params.get("token", "")
    expected_token = cfg.exotel_stream_token
    if not expected_token or not hmac.compare_digest(supplied_token, expected_token):
        await ws.close(code=4401, reason="Invalid Exotel stream token")
        return
    if _active_calls >= cfg.max_calls:
        await ws.close(code=4403, reason="Server at maximum call capacity")
        return

    adapter = ExotelAgentStream(ws)
    try:
        await adapter.wait_for_start()
        call = Call(ws=adapter, stt=app.state.stt_factory(), tts=app.state.tts_factory(),
                    ack_mode=True, client_session_id=adapter.call_sid or adapter.stream_sid)
        log.info("[%s] exotel_agentstream_started stream_sid=%s", call.id, adapter.stream_sid)
        await call.run()
    except (ConnectionError, ValueError) as exc:
        log.warning("exotel_agentstream_rejected error_type=%s message=%s", type(exc).__name__, str(exc))
        await adapter.close(code=1003, reason="Unsupported Exotel stream")
    finally:
        await adapter.close()
