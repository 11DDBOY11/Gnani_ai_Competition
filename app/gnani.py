import asyncio, base64, hashlib, json, pathlib
from .config import cfg
from .dialogue import keyterms


class TTSError(Exception):
    pass


def stt_headers(c=cfg) -> dict:
    return {
        "x-api-key-id": c.api_key,
        "model": "prisma-v3.0",
        "language_code": c.stt_language,
        "x-sample-rate": str(c.sample_rate),
        "x-vad-threshold": str(c.vad_threshold),
        "x-min-speech-ms": str(c.min_speech_ms),
        "x-min-silence-ms": str(c.min_silence_ms),
        "x-idle-timeout-sec": "300",
        "topic": "Kannada farmer asking about crop pests and diseases",
        "keyterms": json.dumps(keyterms()[: c.keyterms_max]),
    }


def tts_request(text: str, c=cfg) -> dict:
    return {
        "text": text,
        "voice": c.tts_voice,
        "model": c.tts_model,
        "language": "kn-IN",
        "speed": c.tts_speed,
        "audio_config": {"sample_rate": c.sample_rate, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "raw"},
    }


class STTStream:
    def __init__(self, c=cfg):
        self.c, self.ws = c, None

    async def open(self):
        from websockets.asyncio.client import connect
        self.ws = await connect(self.c.stt_url, additional_headers=stt_headers(self.c), max_size=None, open_timeout=10)

    async def send(self, pcm: bytes):
        await self.ws.send(pcm)

    async def commit(self):
        await self.ws.send(json.dumps({"type": "commit"}))

    async def events(self):
        async for raw in self.ws:
            if isinstance(raw, (bytes, bytearray)):
                continue
            yield json.loads(raw)

    async def close(self):
        if self.ws:
            await self.ws.close()


class TTS:
    def __init__(self, c=cfg):
        self.c, self.ws, self.lock = c, None, asyncio.Lock()
        self.dir = pathlib.Path(c.cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, text):
        k = f"{self.c.tts_model}|{self.c.tts_voice}|{self.c.sample_rate}|{self.c.tts_speed}|{text}"
        return self.dir / (hashlib.sha1(k.encode("utf-8")).hexdigest() + ".pcm")

    async def _ensure(self):
        if self.ws is None:
            from websockets.asyncio.client import connect
            self.ws = await connect(self.c.tts_url, additional_headers={"X-API-Key-ID": self.c.api_key},
                                    max_size=None, open_timeout=10)

    async def _stream(self, text):
        async with self.lock:
            try:
                await self._ensure()
                await self.ws.send(json.dumps(tts_request(text, self.c)))
                first = True
                async for raw in self.ws:
                    msg = json.loads(raw)
                    t = msg.get("type")
                    if t == "audio":
                        b = base64.b64decode(msg["data"]["audio"] or "")
                        if first and b.startswith(b"RIFF"):
                            b = b[44:]
                        if b:
                            first = False
                            yield b
                    elif t == "complete":
                        return
                    elif t == "error":
                        raise TTSError(msg.get("message", "tts error"))
                raise TTSError("tts socket closed")
            except Exception:
                try:
                    if self.ws:
                        await self.ws.close()
                finally:
                    self.ws = None
                raise

    async def stream_cached(self, text):
        p = self._path(text)
        if p.exists():
            data = p.read_bytes()
            for i in range(0, len(data), 4096):
                yield data[i:i + 4096]
            return
        buf = bytearray()
        async for chunk in self._stream(text):
            buf += chunk
            yield chunk
        if buf:
            p.write_bytes(bytes(buf))

    async def synth(self, text) -> bytes:
        out = bytearray()
        async for c in self.stream_cached(text):
            out += c
        return bytes(out)

    async def close(self):
        if self.ws:
            await self.ws.close()


async def transcribe_pcm(pcm: bytes, c=cfg, tail_silence_s=1.5, wait_s=8.0):
    """Stream raw 16-bit mono PCM at real-time cadence; return transcript events."""
    stt = STTStream(c)
    await stt.open()
    frame, step = 1024, 1024 / 2 / c.sample_rate
    loop = asyncio.get_event_loop()
    out, last = [], [loop.time()]

    async def rx():
        async for ev in stt.events():
            if ev.get("type") in ("transcript", "error"):
                out.append(ev)
                last[0] = loop.time()

    task = asyncio.create_task(rx())
    pcm = pcm + bytes(int(tail_silence_s * c.sample_rate * 2))
    for i in range(0, len(pcm), frame):
        await stt.send(pcm[i:i + frame].ljust(frame, b"\x00"))
        await asyncio.sleep(step)
    end = loop.time() + wait_s
    while loop.time() < end:
        await asyncio.sleep(0.25)
        if out and loop.time() - last[0] > 2.0:
            break
    task.cancel()
    await stt.close()
    return out
