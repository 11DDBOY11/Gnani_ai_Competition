"""Offline unit tests for STTStream and transcribe_pcm error handling."""
import asyncio
import json
import pytest
from app.gnani import STTStream, transcribe_pcm


class MockWebSocket:
    def __init__(self, incoming_messages=None, close_code=None, close_reason=""):
        self.incoming = list(incoming_messages or [])
        self.sent = []
        self.closed = False
        self.close_code = close_code
        self.close_reason = close_reason
        self.state = 1  # OPEN

    async def recv(self):
        if self.incoming:
            item = self.incoming.pop(0)
            if isinstance(item, Exception):
                self.state = 3  # CLOSED
                raise item
            return item
        self.state = 3
        from websockets.exceptions import ConnectionClosed
        from websockets.frames import Close
        raise ConnectionClosed(Close(code=self.close_code or 1000, reason=self.close_reason), None)

    async def send(self, data):
        self.sent.append(data)

    async def close(self):
        self.closed = True
        self.state = 3

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.recv()
        except Exception:
            raise StopAsyncIteration


@pytest.mark.asyncio
async def test_connected_message_received_before_audio_is_sent(monkeypatch):
    """Verify STTStream.open waits for 'connected' and does not send audio."""
    mock_ws = MockWebSocket(incoming_messages=[
        json.dumps({"type": "connected", "config": {"sample_rate": 8000}, "request_id": "test-req-123"})
    ])

    async def fake_connect(*args, **kwargs):
        return mock_ws

    monkeypatch.setattr("websockets.asyncio.client.connect", fake_connect)

    stt = STTStream()
    await stt.open()

    assert stt.config == {"sample_rate": 8000}
    assert stt.request_id == "test-req-123"
    assert len(mock_ws.sent) == 0, "No audio or data should be sent during open()"
    await stt.close()
    assert mock_ws.closed is True


@pytest.mark.asyncio
async def test_error_message_followed_by_1008_becomes_readable_initialization_error(monkeypatch):
    """Verify error message + 1008 close converts into readable initialization error."""
    mock_ws = MockWebSocket(
        incoming_messages=[
            json.dumps({"type": "error", "message": "Invalid language_code: exactly one locale is required"})
        ],
        close_code=1008,
        close_reason="policy violation"
    )

    async def fake_connect(*args, **kwargs):
        return mock_ws

    monkeypatch.setattr("websockets.asyncio.client.connect", fake_connect)

    stt = STTStream()
    with pytest.raises(RuntimeError) as exc_info:
        await stt.open()

    err = str(exc_info.value)
    assert "Invalid language_code" in err
    assert "1008" in err
    assert mock_ws.closed is True


@pytest.mark.asyncio
async def test_receiver_failure_stops_sending_and_cleanup_completes(monkeypatch):
    """Verify receiver failure halts sender loop and triggers proper cleanup."""
    sent_count = 0
    closed = False

    class FailingSTT:
        def __init__(self, c=None):
            self.c = c

        async def open(self):
            pass

        async def send(self, pcm):
            nonlocal sent_count
            sent_count += 1
            await asyncio.sleep(0.01)

        async def events(self):
            yield {"type": "transcript", "text": "partial"}
            await asyncio.sleep(0.02)
            raise RuntimeError("Underlying receiver connection abruptly dropped")

        async def close(self):
            nonlocal closed
            closed = True

    monkeypatch.setattr("app.gnani.STTStream", FailingSTT)

    # 10 frames of audio
    audio_pcm = b"\x00" * 10240

    with pytest.raises(RuntimeError) as exc_info:
        await transcribe_pcm(audio_pcm)

    assert "Underlying receiver connection abruptly dropped" in str(exc_info.value)
    assert closed is True
    assert sent_count < 10, f"Sender should have aborted early, but sent {sent_count} frames"


def test_stt_headers_rejects_comma_separated_languages():
    """Verify stt_headers raises ValueError when multi-locale comma list is configured."""
    from app.gnani import stt_headers
    from app.config import Config

    c = Config()
    c.stt_language = "kn-IN,en-IN"
    with pytest.raises(ValueError) as exc_info:
        stt_headers(c)

    err = str(exc_info.value)
    assert "Invalid STT_LANGUAGE" in err
    assert "exactly one locale is required" in err


def test_stt_headers_accepts_single_locale():
    """Verify stt_headers accepts a single locale properly."""
    from app.gnani import stt_headers
    from app.config import Config

    c = Config()
    c.stt_language = "kn-IN"
    h = stt_headers(c)
    assert h["language_code"] == "kn-IN"


def test_get_retry_files_selects_only_failures(tmp_path):
    """Verify get_retry_files selects only api_error and empty_transcript rows."""
    from scripts.eval_audio import get_retry_files
    import csv

    report_csv = tmp_path / "sample_report.csv"
    with open(report_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "status"])
        writer.writeheader()
        writer.writerow({"file": "clip1.wav", "status": "success"})
        writer.writerow({"file": "clip2.wav", "status": "api_error"})
        writer.writerow({"file": "clip3.wav", "status": "empty_transcript"})
        writer.writerow({"file": "clip4.wav", "status": "success"})

    selected = get_retry_files(report_csv)
    assert selected == ["clip2.wav", "clip3.wav"]
    # Verify source report is unmodified
    with open(report_csv, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 5


@pytest.mark.asyncio
async def test_recovery_stops_after_two_consecutive_dns_failures(tmp_path, monkeypatch):
    """Verify recovery stops processing when two consecutive DNS failures happen."""
    from scripts.eval_audio import run_evaluation
    import wave

    # Create 4 dummy WAV files
    wav_files = []
    for i in range(4):
        p = tmp_path / f"test_{i}.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\x00" * 1600)
        wav_files.append(p)

    attempt_count = 0

    async def fake_transcribe(pcm):
        nonlocal attempt_count
        attempt_count += 1
        # Always fail with DNS resolution error
        raise RuntimeError("[Errno 11001] getaddrinfo failed")

    monkeypatch.setattr("app.gnani.transcribe_pcm", fake_transcribe)
    monkeypatch.setattr("scripts.eval_audio.load", lambda p: b"\x00" * 1600)
    monkeypatch.setattr("scripts.eval_audio.REPORTS_DIR", tmp_path / "reports")

    dummy_rows = [
        {"file": f"test_{i}.wav", "crop": "paddy", "problem": "paddy_blast", "note": "test-note"}
        for i in range(4)
    ]

    out_csv = await run_evaluation(dummy_rows, report_prefix="test_recovery", is_retry=True)

    # Should only attempt 2 clips before aborting
    assert attempt_count == 2
    # Check output CSV has exactly 2 completed rows
    import csv
    with open(out_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["file"] == "test_0.wav"
        assert rows[1]["file"] == "test_1.wav"
        assert rows[0]["status"] == "api_error"
        assert rows[1]["status"] == "api_error"


def test_sim_html_contains_token_support_and_ui_elements():
    """Verify sim.html contains password token input, warning, and half-duplex checks."""
    from fastapi.testclient import TestClient
    from app.server import app

    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # Verify password token input exists and does not store to localStorage
    assert 'type="password"' in html
    assert 'id="tok"' in html
    assert "localStorage" not in html

    # Verify ordered PCM playback, half-duplex gate, and 4401/4403 status visibility
    assert "atomic_reply" in html
    assert "source.onended=()=>" in html
    assert "source.start(this.ctx.currentTime)" in html
    assert "if(session.isPlaying)return" in html
    assert "4401" in html
    assert "4403" in html
    assert "call ended" in html
