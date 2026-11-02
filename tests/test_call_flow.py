"""Whole-call test with fake STT/TTS: no network, no credits."""
import asyncio, json, time
from fastapi.testclient import TestClient
from app import server


class FakeSTT:
    script = ["ನಮ್ಮ ಭತ್ತದ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ", "ಚಿಕ್ಕ ಗಿಡ"]

    def __init__(self):
        self.q, self.bytes, self.i = None, 0, 0

    async def open(self):
        self.q = asyncio.Queue()

    async def send(self, pcm):
        assert len(pcm) == 1024
        self.bytes += len(pcm)
        if self.bytes >= 4096 and self.i < len(self.script):
            self.bytes = 0
            await self.q.put({"type": "transcript", "text": self.script[self.i], "latency": 100})
            self.i += 1

    async def events(self):
        while True:
            yield await self.q.get()

    async def close(self):
        pass


class FakeTTS:
    async def stream_cached(self, text):
        yield b"\x01\x00" * 400

    async def close(self):
        pass


def next_reply(ws, limit=60):
    for _ in range(limit):
        m = ws.receive()
        if m.get("text"):
            j = json.loads(m["text"])
            if j["type"] == "reply":
                return j
    raise AssertionError("no reply")


def feed(ws, n=8):
    for _ in range(n):
        ws.send_bytes(b"\x00" * 1024)


def test_two_turn_call(monkeypatch, tmp_path):
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    server.app.state.stt_factory = FakeSTT
    server.app.state.tts_factory = FakeTTS
    with TestClient(server.app).websocket_connect("/ws/call?phone=9999999999") as ws:
        assert "ನಮಸ್ಕಾರ" in next_reply(ws)["text"]
        time.sleep(1.2)
        feed(ws)
        assert "ಹಂತ" in next_reply(ws)["text"]
        time.sleep(1.2)
        feed(ws)
        assert "ರಾಸಾಯನಿಕ" in next_reply(ws)["text"]
    time.sleep(0.5)
    assert (tmp_path / "calls.jsonl").exists()
    assert (tmp_path / "sms_outbox.jsonl").exists()
