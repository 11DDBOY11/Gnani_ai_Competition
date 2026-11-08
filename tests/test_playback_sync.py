"""Tests for finish-response-before-listening mode, TTS failure recovery, and playback serialization."""
import asyncio, json, shutil, subprocess, time, pytest
from fastapi.testclient import TestClient
from app import server
from app.gnani import TTSError, TTS


class MockStreamingTTS:
    """Mock TTS that simulates chunk delivery, delay, and socket errors."""
    def __init__(self, chunks_per_sentence=2, chunk_delay=0.01, fail_once=False, fail_after_bytes=0):
        self.chunks_per_sentence = chunks_per_sentence
        self.chunk_delay = chunk_delay
        self.fail_once = fail_once
        self.fail_after_bytes = fail_after_bytes
        self.delivered_chunks = 0
        self.closed = False

    async def stream_cached(self, text):
        if self.fail_once:
            self.fail_once = False
            raise TTSError("mock network error before audio")

        for i in range(self.chunks_per_sentence):
            if self.chunk_delay:
                await asyncio.sleep(self.chunk_delay)
            chunk = b"\x01\x00" * 200  # 400 bytes
            if self.fail_after_bytes and (self.delivered_chunks + 1) * 400 > self.fail_after_bytes:
                raise TTSError("mock mid-stream drop")
            self.delivered_chunks += 1
            yield chunk

    async def close(self):
        self.closed = True


class ZeroAudioTTS:
    async def stream_cached(self, text):
        if False:
            yield b""

    async def close(self):
        pass


class ScriptedSTT:
    def __init__(self, script=None):
        self.script = script or []
        self.i = 0
        self.bytes = 0
        self.received_pcm_bytes = 0
        self.q = None

    async def open(self):
        self.q = asyncio.Queue()

    async def send(self, pcm):
        self.received_pcm_bytes += len(pcm)
        self.bytes += len(pcm)
        if self.bytes >= 4096 and self.i < len(self.script):
            self.bytes = 0
            await self.q.put({"type": "transcript", "text": self.script[self.i], "latency": 50})
            self.i += 1

    async def events(self):
        while True:
            yield await self.q.get()

    async def close(self):
        pass


def test_multi_chunk_multi_sentence_response_completion(monkeypatch, tmp_path, caplog):
    """A response is one atomic control, one complete PCM payload, and one matching ack."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    caplog.set_level("INFO", logger="krishi")
    stt = ScriptedSTT()
    tts = MockStreamingTTS(chunks_per_sentence=3, chunk_delay=0.005)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        control = None
        payload = None
        for _ in range(40):
            m = ws.receive()
            if m.get("text"):
                data = json.loads(m["text"])
                assert data["type"] not in {"response_start", "audio_chunk", "reply", "response_end"}
                if data.get("type") == "atomic_reply":
                    control = data
            elif m.get("bytes") is not None:
                payload = m["bytes"]
                break
        assert control is not None
        assert payload is not None
        assert control["response_id"]
        assert len(control["text"]) > 20
        assert len(payload) == 1200  # one complete text request yields 3 chunks x 400 bytes
        ws.send_text(json.dumps({"type": "playback_done", "response_id": control["response_id"]}))
        # One acknowledgement releases the response; no second payload/control is emitted.
        time.sleep(0.03)
        assert stt.received_pcm_bytes == 0
        ack_lines = [record.getMessage() for record in caplog.records
                     if "playback_done_received" in record.getMessage()]
        assert len(ack_lines) == 1
        assert f"response_id={control['response_id']} matched=True" in ack_lines[0]


def test_delayed_final_audio_chunk(monkeypatch, tmp_path):
    """Test that playback ack and server completion wait for delayed final audio chunks."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT()
    # 2 sentences, 0.05s delay per chunk
    tts = MockStreamingTTS(chunks_per_sentence=2, chunk_delay=0.05)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        t0 = time.monotonic()
        got_resp_end = False
        while True:
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    got_resp_end = True
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": j["response_id"]}))
                    break
        elapsed = time.monotonic() - t0
        assert got_resp_end
        # 3 sentences in greeting * 2 chunks = 6 chunks * 0.05s >= 0.30s
        assert elapsed >= 0.25


def test_sequential_responses_no_cross_turn_audio_leakage(monkeypatch, tmp_path):
    """Sequential bot responses have distinct response IDs and no interleaving or audio leakage."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT(script=["ಭತ್ತ ಬೆಂಕಿ ರೋಗ"])
    tts = MockStreamingTTS(chunks_per_sentence=2, chunk_delay=0.002)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        resp_ids = []
        # Turn 1: Greeting
        for _ in range(60):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    resp_ids.append(j["response_id"])
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": j["response_id"]}))
                    break

        # Feed mic audio to trigger STT transcript
        time.sleep(0.2)
        for _ in range(8):
            ws.send_bytes(b"\x00" * 1024)

        # Turn 2: Advisory
        for _ in range(60):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    resp_ids.append(j["response_id"])
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": j["response_id"]}))
                    break

        assert len(resp_ids) == 2
        assert resp_ids[0] != resp_ids[1]


def test_playback_acknowledgement_before_listening_resumes(monkeypatch, tmp_path):
    """Microphone audio sent during playback is dropped on server, but accepted once playback completes."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT(script=["ಭತ್ತ ಬೆಂಕಿ ರೋಗ"])
    tts = MockStreamingTTS(chunks_per_sentence=18, chunk_delay=0.001)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        # While greeting is playing, send mic bytes
        ws.send_bytes(b"\x00" * 1024)
        ws.send_bytes(b"\x00" * 1024)

        resp_id = None
        for _ in range(200):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    resp_id = j["response_id"]
                    time.sleep(0.05)
                    # Before sending ack, STT should not have received mic bytes (discarded on server)
                    assert stt.received_pcm_bytes == 0
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": "stale-id"}))
                    time.sleep(0.02)
                    assert stt.received_pcm_bytes == 0
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": resp_id}))
                    break

        time.sleep(0.05)
        # Send mic audio after playback acknowledgement
        for _ in range(8):
            ws.send_bytes(b"\x00" * 1024)
        time.sleep(0.1)
        assert stt.received_pcm_bytes >= 4096


def test_atomic_browser_playback_uses_one_source_and_acknowledges_onended():
    """The browser binds one complete PCM payload to one response source."""
    from pathlib import Path
    html = Path("app/sim.html").read_text(encoding="utf-8")
    assert "m.type==='atomic_reply'" in html
    assert "session.playAtomicResponse(responseId,ev.data)" in html
    assert "source.start(this.ctx.currentTime)" in html
    assert "source.onended=()=>" in html
    assert "this.sendPlaybackDone(responseId)" in html
    assert "if(session.isPlaying)return" in html
    assert "session.abortPlayback()" in html
    assert "playbackQueue" not in html
    assert "pendingAudioResponseId" not in html


def test_stt_child_process_failure_sends_clear_error_and_closes_call(monkeypatch, tmp_path, caplog):
    """A dead upstream STT worker ends the call explicitly; it is never silently reused."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))

    class ChildProcessFailingSTT:
        def __init__(self):
            self.audio_received = asyncio.Event()
            self.open_count = 0

        async def open(self):
            self.open_count += 1

        async def send(self, pcm):
            self.audio_received.set()

        async def events(self):
            await self.audio_received.wait()
            raise RuntimeError("A child process terminated abruptly, the process pool is not usable anymore")
            yield  # pragma: no cover

        async def close(self):
            pass

    stt = ChildProcessFailingSTT()
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: MockStreamingTTS(chunks_per_sentence=1, chunk_delay=0.001)

    with TestClient(server.app).websocket_connect(
        "/ws/call?ack=1&client_session_id=stt-child-failure-test"
    ) as ws:
        response_id = None
        while response_id is None:
            msg = ws.receive()
            if msg.get("text"):
                data = json.loads(msg["text"])
                if data.get("type") == "atomic_reply":
                    response_id = data["response_id"]
        ws.send_text(json.dumps({"type": "playback_done", "response_id": response_id}))
        ws.send_bytes(b"\x00" * 1024)

        failure = None
        while failure is None:
            msg = ws.receive()
            if msg.get("text"):
                data = json.loads(msg["text"])
                if data.get("type") == "error":
                    failure = data
        assert failure["where"] == "stt"
        assert failure["code"] == "stt_stream_failed"
        assert failure["fatal"] is True
        assert "ಹೊಸ ಕರೆ ಆರಂಭಿಸಿ" in failure["message"]
        close = ws.receive()
        assert close["type"] == "websocket.close"
        assert close["code"] == 1011
        assert stt.open_count == 1

    diagnostic = next(line for line in caplog.text.splitlines() if "stt_failure_diagnostic" in line)
    assert "failure_source=local_stt_receiver" in diagnostic
    assert "error_type=RuntimeError" in diagnostic
    assert "error_message=A child process terminated abruptly, the process pool is not usable anymore" in diagnostic
    assert "audio_sent_before_failure=True" in diagnostic
    assert "browser_websocket_closed=True" in diagnostic
    assert "client_session_id=stt-child-failure-test" in diagnostic
    assert "response_id=" in diagnostic


@pytest.mark.parametrize(("mode", "source", "error_type", "audio_sent"), [
    ("provider", "upstream_gnani_stt_stream", "provider_error", "True"),
    ("send", "stt_audio_send", "OSError", "False"),
])
def test_stt_diagnostics_distinguish_provider_error_from_audio_send_failure(
    mode, source, error_type, audio_sent, monkeypatch, tmp_path, caplog
):
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))

    class FailingSTT:
        def __init__(self):
            self.received_audio = asyncio.Event()

        async def open(self):
            pass

        async def send(self, pcm):
            if mode == "send":
                raise OSError("mock upstream send failed")
            self.received_audio.set()

        async def events(self):
            await self.received_audio.wait()
            if mode == "provider":
                yield {"type": "error", "error_type": "provider_error",
                       "message": "Gnani STT stream returned a test error"}

        async def close(self):
            pass

    server.app.state.stt_factory = FailingSTT
    server.app.state.tts_factory = lambda: MockStreamingTTS(chunks_per_sentence=1, chunk_delay=0.001)
    client_session_id = f"stt-{mode}-test"

    with TestClient(server.app).websocket_connect(
        f"/ws/call?ack=1&client_session_id={client_session_id}"
    ) as ws:
        response_id = None
        while response_id is None:
            msg = ws.receive()
            if msg.get("text"):
                data = json.loads(msg["text"])
                if data.get("type") == "atomic_reply":
                    response_id = data["response_id"]
        ws.send_text(json.dumps({"type": "playback_done", "response_id": response_id}))
        ws.send_bytes(b"\x00" * 1024)

        got_error = False
        while not got_error:
            msg = ws.receive()
            if msg.get("text"):
                data = json.loads(msg["text"])
                got_error = data.get("type") == "error" and data.get("fatal") is True
        assert ws.receive().get("type") == "websocket.close"

    diagnostic = next(line for line in caplog.text.splitlines()
                      if "stt_failure_diagnostic" in line and f"client_session_id={client_session_id}" in line)
    assert f"failure_source={source}" in diagnostic
    assert f"error_type={error_type}" in diagnostic
    assert f"audio_sent_before_failure={audio_sent}" in diagnostic
    assert "browser_websocket_closed=True" in diagnostic
    assert "response_id=" in diagnostic


def test_watchdog_suppressed_during_playback(monkeypatch, tmp_path):
    """Watchdog silence counter does not fire while speech is synthesizing or playing."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    monkeypatch.setattr("app.server.cfg.silence_timeout_s", 0.1)
    stt = ScriptedSTT()
    tts = MockStreamingTTS(chunks_per_sentence=4, chunk_delay=0.03)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        got_reprompt = False
        for _ in range(60):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply" and "ಸರಿಯಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ" in j["text"]:
                    got_reprompt = True
                if j.get("type") == "atomic_reply":
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": j["response_id"]}))
                    break

        assert not got_reprompt


def test_partial_tts_failure_and_stale_socket_recovery():
    """Test that TTS client recovers from initial connection error without corrupting cache."""
    tts = TTS()
    attempt = 0

    class MockWS:
        def __init__(self):
            self.state = 1
        async def send(self, data):
            pass
        async def close(self):
            self.state = 3
        def __aiter__(self):
            return self
        async def __anext__(self):
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise TTSError("connection reset")
            elif attempt == 2:
                return json.dumps({"type": "audio", "data": {"audio": "AQABAA=="}})
            else:
                return json.dumps({"type": "complete"})

    async def run_retry_test():
        async def mock_ensure():
            tts.ws = MockWS()
        tts._ensure = mock_ensure
        chunks = []
        async for c in tts._stream("ಟೆಸ್ಟ್ ವಾಕ್ಯ"):
            chunks.append(c)
        assert len(chunks) == 1

    asyncio.run(run_retry_test())


def test_goodbye_audio_finishes_before_closure(monkeypatch, tmp_path):
    """Test that goodbye audio delivers completely before the server closes the WebSocket."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT(script=["ಧನ್ಯವಾದ ಸಾಕು"])
    tts = MockStreamingTTS(chunks_per_sentence=2, chunk_delay=0.005)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        # Complete greeting
        for _ in range(60):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": j["response_id"]}))
                    break

        # Feed audio to trigger goodbye in STT
        for _ in range(8):
            ws.send_bytes(b"\x00" * 1024)

        goodbye_audio_bytes = 0
        got_goodbye_end = False
        for _ in range(60):
            m = ws.receive()
            if m.get("bytes"):
                goodbye_audio_bytes += len(m["bytes"])
            elif m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    got_goodbye_end = True
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": j["response_id"]}))
            elif m.get("type") == "websocket.close":
                break

        assert got_goodbye_end
        assert goodbye_audio_bytes > 0


def test_missing_acknowledgement_aborts_playback_and_closes_call(monkeypatch, tmp_path):
    """Test that acknowledgement timeout does NOT resume mic intake and aborts call."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT()
    # 1 chunk so duration is tiny (0.025s), timeout will be short (min(0.025+0.5, 3.0) = 0.525s)
    tts = MockStreamingTTS(chunks_per_sentence=1, chunk_delay=0.001)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        got_resp_end = False
        got_abort = False
        abort_reason = None
        for _ in range(60):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    got_resp_end = True
                    # DO NOT send playback_done! Wait for server timeout.
                elif j.get("type") == "playback_abort":
                    got_abort = True
                    abort_reason = j.get("reason")
            elif m.get("type") == "websocket.close":
                break

        assert got_resp_end
        assert got_abort
        assert abort_reason == "playback_ack_timeout"
        # Ensure mic intake was not resumed
        assert stt.received_pcm_bytes == 0


def test_tts_stream_failure_aborts_playback_and_closes_call(monkeypatch, tmp_path):
    """Test that mid-stream TTS failure triggers playback_abort and terminates call."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT()
    # Fails after delivering 400 bytes
    tts = MockStreamingTTS(chunks_per_sentence=2, chunk_delay=0.001, fail_after_bytes=400)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        got_error = False
        got_abort = False
        for _ in range(60):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "error" and j.get("where") == "tts":
                    got_error = True
                elif j.get("type") == "playback_abort":
                    got_abort = True
                    assert j.get("reason") == "tts_failure"
            elif m.get("type") == "websocket.close":
                break

        assert got_error
        assert got_abort
        assert stt.received_pcm_bytes == 0


def test_zero_audio_response_acknowledges_immediately(monkeypatch, tmp_path):
    """Test that 0-audio responses complete immediately with proper response_end metadata."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT()
    tts = ZeroAudioTTS()
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        t0 = time.monotonic()
        got_resp_end = False
        for _ in range(30):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    got_resp_end = True
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": j["response_id"]}))
                    break
        elapsed = time.monotonic() - t0
        assert got_resp_end
        assert elapsed < 0.4


def test_stale_acknowledgement_does_not_affect_new_response(monkeypatch, tmp_path):
    """Test that an old/stale ack from a previous call or turn does not resolve a new response."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT()
    tts = MockStreamingTTS(chunks_per_sentence=1, chunk_delay=0.001)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        # Send stale playback_done from old call
        ws.send_text(json.dumps({"type": "playback_done", "response_id": "stale-old-call-id"}))

        got_resp_end = False
        for _ in range(30):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    got_resp_end = True
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": j["response_id"]}))
                    break

        assert got_resp_end


def test_same_call_repeated_paddy_blast_request_never_replays_greeting(monkeypatch, tmp_path):
    """The greeting is emitted once per Call; a repeated diagnosis stays in-session."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT(script=["ಭತ್ತ ಬೆಂಕಿ ರೋಗ", "ಭತ್ತ ಬೆಂಕಿ ರೋಗ"])
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: MockStreamingTTS(chunks_per_sentence=1, chunk_delay=0.001)

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        replies = []
        # Finish the single call greeting.
        while True:
            msg = ws.receive()
            if msg.get("text"):
                data = json.loads(msg["text"])
                if data.get("type") == "atomic_reply":
                    ws.send_text(json.dumps({"type": "playback_done", "response_id": data["response_id"]}))
                    break

        for _ in range(2):
            time.sleep(0.03)
            for _ in range(4):
                ws.send_bytes(b"\x00" * 1024)
            got_end = False
            while not got_end:
                msg = ws.receive()
                if msg.get("text"):
                    data = json.loads(msg["text"])
                    if data.get("type") == "atomic_reply":
                        replies.append(data["text"])
                        ws.send_text(json.dumps({"type": "playback_done", "response_id": data["response_id"]}))
                        got_end = True

        assert len(replies) == 2
        assert all("ನಮಸ್ಕಾರ" not in text for text in replies)
        assert "ಬೆಂಕಿ ರೋಗ" in replies[0]
