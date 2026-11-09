import asyncio, base64, hashlib, json, pathlib
from .config import cfg
from .dialogue import keyterms


class TTSError(Exception):
    pass


def stt_headers(c=cfg) -> dict:
    if "," in c.stt_language:
        raise ValueError(
            f"Invalid STT_LANGUAGE '{c.stt_language}': exactly one locale is required (e.g. 'kn-IN'). "
            "Multi-locale comma lists are not supported for single-locale streaming."
        )
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


def tts_request(text: str, c=cfg, language="kn-IN") -> dict:
    return {
        "text": text,
        "voice": c.tts_voice,
        "model": c.tts_model,
        "language": language,
        "speed": c.tts_speed,
        "audio_config": {"sample_rate": c.sample_rate, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "raw"},
    }


class STTStream:
    def __init__(self, c=cfg):
        self.c, self.ws = c, None
        self.config = None
        self.request_id = None
        self._buffered_events = []

    async def open(self, timeout=10.0):
        from websockets.asyncio.client import connect
        from websockets.exceptions import InvalidStatus, ConnectionClosed
        try:
            self.ws = await connect(self.c.stt_url, additional_headers=stt_headers(self.c), max_size=None, open_timeout=10)
        except InvalidStatus as e:
            code = getattr(getattr(e, "response", None), "status_code", getattr(e, "status_code", None))
            if code in (401, 403) or "401" in str(e) or "403" in str(e):
                raise RuntimeError("Gnani rejected the API key (HTTP 401). Run python -m scripts.check_key") from None
            raise

        last_error = None
        try:
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                remaining = max(deadline - asyncio.get_event_loop().time(), 0.1)
                try:
                    raw = await asyncio.wait_for(self.ws.recv(), timeout=remaining)
                except asyncio.TimeoutError:
                    break
                except ConnectionClosed as e:
                    code = getattr(self.ws, "close_code", None) or getattr(getattr(e, "rcvd", None), "code", None) or getattr(e, "code", None)
                    reason = getattr(self.ws, "close_reason", "") or getattr(getattr(e, "rcvd", None), "reason", "") or getattr(e, "reason", "")
                    err_info = f" (server message: {last_error})" if last_error else ""
                    await self.close()
                    raise RuntimeError(f"STT socket closed before readiness: code={code}, reason='{reason}'{err_info}") from None

                if isinstance(raw, (bytes, bytearray)):
                    raw = raw.decode("utf-8", errors="replace")
                msg = json.loads(raw) if isinstance(raw, str) else raw
                m_type = msg.get("type")
                if m_type == "connected":
                    self.config = msg.get("config")
                    self.request_id = msg.get("request_id")
                    return
                elif m_type == "error":
                    last_error = msg.get("message", "unknown stt error")
                    code = getattr(self.ws, "close_code", None)
                    reason = getattr(self.ws, "close_reason", "")
                    try:
                        await asyncio.wait_for(self.ws.recv(), timeout=0.5)
                    except ConnectionClosed as cc:
                        code = getattr(self.ws, "close_code", None) or getattr(getattr(cc, "rcvd", None), "code", None) or getattr(cc, "code", None)
                        reason = getattr(self.ws, "close_reason", "") or getattr(getattr(cc, "rcvd", None), "reason", "") or getattr(cc, "reason", "")
                    except Exception:
                        pass
                    await self.close()
                    code_info = f" (close code={code}, reason='{reason}')" if code else ""
                    raise RuntimeError(f"STT initialization failed: {last_error}{code_info}")
                else:
                    self._buffered_events.append(msg)

            await self.close()
            raise TimeoutError("Timed out waiting for initial STT server response")
        except Exception:
            await self.close()
            raise

    async def send(self, pcm: bytes):
        await self.ws.send(pcm)

    async def commit(self):
        await self.ws.send(json.dumps({"type": "commit"}))

    async def events(self):
        while self._buffered_events:
            yield self._buffered_events.pop(0)
        async for raw in self.ws:
            if isinstance(raw, (bytes, bytearray)):
                continue
            yield json.loads(raw)

    async def close(self):
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None


class TTS:
    def __init__(self, c=cfg):
        self.c, self.ws, self.lock = c, None, asyncio.Lock()
        self.dir = pathlib.Path(c.cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, text, language="kn-IN"):
        k = f"{self.c.tts_model}|{self.c.tts_voice}|{self.c.sample_rate}|{self.c.tts_speed}|{text}"
        if language != "kn-IN":
            k = f"{language}|{k}"
        return self.dir / (hashlib.sha1(k.encode("utf-8")).hexdigest() + ".pcm")

    async def _ensure(self):
        if self.ws is None or getattr(self.ws, "state", None) not in (None, 1): # 1 is OPEN in websockets
            if self.ws is not None:
                try:
                    await self.ws.close()
                except Exception:
                    pass
                self.ws = None
            from websockets.asyncio.client import connect
            from websockets.exceptions import InvalidStatus
            try:
                self.ws = await connect(self.c.tts_url, additional_headers={"X-API-Key-ID": self.c.api_key},
                                        max_size=None, open_timeout=10, ping_interval=20, ping_timeout=20)
            except InvalidStatus as e:
                code = getattr(getattr(e, "response", None), "status_code", getattr(e, "status_code", None))
                if code in (401, 403) or "401" in str(e) or "403" in str(e):
                    raise RuntimeError("Gnani rejected the API key (HTTP 401). Run python -m scripts.check_key") from None
                raise

    async def _stream_single(self, text, language="kn-IN"):
        """Execute a single attempt to stream synthesis from Gnani TTS."""
        await self._ensure()
        await self.ws.send(json.dumps(tts_request(text, self.c, language)))
        first = True
        completed = False
        async for raw in self.ws:
            msg = json.loads(raw)
            t = msg.get("type")
            if t == "audio":
                b = base64.b64decode(msg.get("data", {}).get("audio") or "")
                if first and b.startswith(b"RIFF"):
                    b = b[44:]
                if b:
                    first = False
                    yield b
            elif t == "complete":
                completed = True
                return
            elif t == "error":
                raise TTSError(msg.get("message", "tts error"))
        if not completed:
            raise TTSError("tts socket closed before complete message")

    async def _stream(self, text, language="kn-IN"):
        async with self.lock:
            delivered_any = False
            try:
                async for chunk in self._stream_single(text, language):
                    delivered_any = True
                    yield chunk
            except Exception as e:
                try:
                    if self.ws:
                        await self.ws.close()
                finally:
                    self.ws = None
                # Bounded retry: if NO audio was delivered yet, retry once with a fresh socket
                if not delivered_any:
                    try:
                        async for chunk in self._stream_single(text, language):
                            delivered_any = True
                            yield chunk
                    except Exception:
                        try:
                            if self.ws:
                                await self.ws.close()
                        finally:
                            self.ws = None
                        raise
                else:
                    raise

    async def stream_cached(self, text, language="kn-IN"):
        p = self._path(text, language)
        if p.exists():
            data = p.read_bytes()
            for i in range(0, len(data), 4096):
                yield data[i:i + 4096]
            return
        buf = bytearray()
        complete_received = False
        try:
            async for chunk in self._stream(text, language):
                buf += chunk
                yield chunk
            complete_received = True
        finally:
            # Only write to disk cache if full stream was completed without interruption
            if complete_received and buf:
                p.write_bytes(bytes(buf))

    async def synth(self, text, language="kn-IN") -> bytes:
        out = bytearray()
        async for c in self.stream_cached(text, language):
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
    fatal_error = None
    task = None

    async def rx():
        nonlocal fatal_error
        async for ev in stt.events():
            t = ev.get("type")
            if t in ("transcript", "error"):
                out.append(ev)
                last[0] = loop.time()
                if t == "error":
                    fatal_error = ev.get("message", "stt error")
                    break

    try:
        task = asyncio.create_task(rx())
        pcm = pcm + bytes(int(tail_silence_s * c.sample_rate * 2))
        for i in range(0, len(pcm), frame):
            if task.done() or fatal_error:
                break
            await stt.send(pcm[i:i + frame].ljust(frame, b"\x00"))
            await asyncio.sleep(step)

        if not fatal_error and not task.done():
            end = loop.time() + wait_s
            while loop.time() < end:
                if task.done() or fatal_error:
                    break
                await asyncio.sleep(0.25)
                if out and loop.time() - last[0] > 2.0:
                    break

        if fatal_error:
            raise RuntimeError(f"STT server error: {fatal_error}")

        if task.done() and task.exception():
            raise task.exception()

    finally:
        if task and not task.done():
            task.cancel()
        if task:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        await stt.close()

    return out
