"""Trace-field and explicit-restart checks; these do not assert browser audio playback."""
import json
import logging

from fastapi.testclient import TestClient

from app import server
from tests.test_playback_sync import MockStreamingTTS, ScriptedSTT


def _receive_json(ws, wanted, limit=80):
    for _ in range(limit):
        msg = ws.receive()
        if msg.get("text"):
            data = json.loads(msg["text"])
            if data.get("type") == wanted:
                return data
    raise AssertionError(f"did not receive {wanted}")


def test_timeout_trace_has_response_ids_and_restart_is_explicit(monkeypatch, tmp_path, caplog):
    """A timeout closes the socket; a later user-created call is marked as a new call."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    caplog.set_level(logging.INFO, logger="krishi")
    server._last_call_outcome_by_client.clear()
    server.app.state.stt_factory = ScriptedSTT
    server.app.state.tts_factory = lambda: MockStreamingTTS(chunks_per_sentence=1, chunk_delay=0.001)
    client = TestClient(server.app)
    client_session_id = "trace-test-session"

    with client.websocket_connect(f"/ws/call?ack=1&client_session_id={client_session_id}") as ws:
        reply = _receive_json(ws, "atomic_reply")
        response_id = reply["response_id"]
        assert ws.receive().get("bytes") is not None
        abort = _receive_json(ws, "playback_abort")
        assert abort["response_id"] == response_id
        assert abort["reason"] == "playback_ack_timeout"
        assert ws.receive().get("type") == "websocket.close"

    # A new connection is only made by this explicit test-client connect (the page has no retry loop).
    with client.websocket_connect(f"/ws/call?ack=1&client_session_id={client_session_id}") as ws:
        reply = _receive_json(ws, "atomic_reply")
        response_id = reply["response_id"]
        assert ws.receive().get("bytes") is not None
        ws.send_text(json.dumps({"type": "playback_done", "response_id": response_id}))
        ws.close()

    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "playback_ack_timeout response_id=" in output
    assert "elapsed_s=" in output and "expected_duration_s=" in output
    assert "playback_done_received response_id=" in output and "matched=True" in output
    assert "call_instance_created" in output
    assert "follows_prior_playback_ack_timeout=True" in output


def test_simulator_contains_playback_trace_fields_without_claiming_audio_verification():
    """The served page exposes the requested trace points and has no reconnect path."""
    html = TestClient(server.app).get("/sim").text
    for event in (
        "atomic_audio_started",
        "audio_source_onended",
        "playback_done_send_attempt",
        "playback_abort_sent",
        "atomic_reply_received",
        "automatic_reconnect:false",
        "explicit_new_call_required:true",
    ):
        assert event in html
    assert "new WebSocket(" in html
    assert "setTimeout(" not in html and "onclose=" in html
