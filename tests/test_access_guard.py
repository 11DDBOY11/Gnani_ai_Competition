"""Access guard tests: token auth and concurrent-call cap. No network, no credits."""
import pytest
from fastapi.testclient import TestClient
from app import server
from tests.test_call_flow import FakeSTT, FakeTTS


def _client():
    server.app.state.stt_factory = FakeSTT
    server.app.state.tts_factory = FakeTTS
    return TestClient(server.app)


def _close_code(ws):
    """Read the next message and return the close code, or None if not a close frame."""
    msg = ws.receive()
    if msg.get("type") == "websocket.close":
        return msg.get("code")
    return None


def test_rejects_wrong_token(monkeypatch, tmp_path):
    monkeypatch.setattr("app.server.cfg.call_token", "secret")
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    c = _client()

    # No token at all → 4401
    with c.websocket_connect("/ws/call") as ws:
        assert _close_code(ws) == 4401

    # Wrong token → 4401
    with c.websocket_connect("/ws/call?token=wrong") as ws:
        assert _close_code(ws) == 4401

    # Correct token → NOT a close frame (greeting reply arrives instead)
    with c.websocket_connect("/ws/call?token=secret") as ws:
        msg = ws.receive()
        assert msg.get("type") != "websocket.close"


def test_rejects_when_at_cap(monkeypatch, tmp_path):
    monkeypatch.setattr("app.server.cfg.call_token", "")   # no token guard
    monkeypatch.setattr("app.server.cfg.max_calls", 1)
    monkeypatch.setattr("app.server._active_calls", 1)     # simulate one call already open
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    c = _client()

    # At cap → 4403
    with c.websocket_connect("/ws/call") as ws:
        assert _close_code(ws) == 4403
