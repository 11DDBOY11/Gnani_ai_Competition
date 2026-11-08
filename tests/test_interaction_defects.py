"""Tests for interaction defects: crop retention, problem-before-crop flow, unsupported-crop clarification, and playback synchronization."""
import json, pytest
from app.dialogue import Session, KB, T
from app import server
from tests.test_playback_sync import ScriptedSTT, MockStreamingTTS
from fastapi.testclient import TestClient


def test_supported_crop_retention_and_no_crop_reask():
    """When user states supported crop, retain it in session state and do not ask crop again."""
    s = Session()
    # Turn 1: Caller states supported crop
    r1 = s.respond("ನಮ್ಮದು ಭತ್ತ.")
    assert s.crop == "paddy"
    assert r1.meta["state"] == "ask_problem"
    assert "ನಿಮ್ಮ ಬೆಳೆ ಯಾವುದು" not in " ".join(r1.sentences)

    # Turn 2: Caller describes general disease without repeating crop
    r2 = s.respond("ನಮ್ಮ ಬೆಳೆಯಲ್ಲಿ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?")
    assert s.crop == "paddy"
    # Must ask for problem symptoms, NOT crop
    assert r2.meta["state"] == "ask_problem"
    assert "ನಿಮ್ಮ ಬೆಳೆ ಯಾವುದು" not in " ".join(r2.sentences)
    assert not any("ನಮಸ್ಕಾರ" in sent for sent in r2.sentences)

    # Turn 3: Caller gives specific symptom/problem (paddy_blast does not need stage, so advised)
    r3 = s.respond("ಬೆಂಕಿ ರೋಗ ಬಂದಿದೆ")
    assert s.crop == "paddy"
    assert s.problem == "paddy_blast"
    assert r3.meta["state"] == "advised"


def test_problem_before_crop_asks_crop_first_then_advances_to_problem_flow():
    """If user provides problem before crop, ask crop first. Once crop is known, advance to problem flow."""
    # Subtest 1: paddy_blast (needs_stage is False -> proceeds to advised)
    s1 = Session()
    r1 = s1.respond("ಬೆಂಕಿ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?")
    assert s1.crop is None
    assert s1.problem == "paddy_blast"
    assert r1.meta["state"] == "ask_crop"
    assert "ನಿಮ್ಮ ಬೆಳೆ ಯಾವುದು" in " ".join(r1.sentences)

    r2 = s1.respond("ನಮ್ಮದು ಭತ್ತ.")
    assert s1.crop == "paddy"
    assert s1.problem == "paddy_blast"
    # Proceeded directly to advised without re-asking crop or problem
    assert r2.meta["state"] == "advised"
    assert "ನಿಮ್ಮ ಬೆಳೆ ಯಾವುದು" not in " ".join(r2.sentences)
    assert "ಬೆಳೆಯಲ್ಲಿ ಏನು ಸಮಸ್ಯೆ ಕಾಣುತ್ತಿದೆ" not in " ".join(r2.sentences)

    # Subtest 2: paddy_leaf_folder (needs_stage is True -> proceeds to ask_stage)
    s2 = Session()
    r3 = s2.respond("ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ, ಏನು ಮಾಡಬೇಕು?")
    assert s2.crop is None
    assert s2.problem == "paddy_leaf_folder"
    assert r3.meta["state"] == "ask_crop"
    assert "ನಿಮ್ಮ ಬೆಳೆ ಯಾವುದು" in " ".join(r3.sentences)

    r4 = s2.respond("ನಮ್ಮದು ಭತ್ತ.")
    assert s2.crop == "paddy"
    assert s2.problem == "paddy_leaf_folder"
    # Proceeded directly to ask_stage
    assert r4.meta["state"] == "ask_stage"
    assert "ನಿಮ್ಮ ಬೆಳೆ ಯಾವುದು" not in " ".join(r4.sentences)
    assert "ಬೆಳೆಯಲ್ಲಿ ಏನು ಸಮಸ್ಯೆ ಕಾಣುತ್ತಿದೆ" not in " ".join(r4.sentences)


def test_problem_before_crop_incompatible_crop_resets_problem():
    """If problem was provided before crop, but caller states an incompatible crop, reset problem and ask problem."""
    s = Session()
    # Turn 1: Paddy leaf folder symptom provided before crop
    r1 = s.respond("ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ, ಏನು ಮಾಡಬೇಕು?")
    assert s.crop is None
    assert s.problem == "paddy_leaf_folder"
    assert r1.meta["state"] == "ask_crop"

    # Turn 2: Caller states coconut (incompatible with paddy_leaf_folder)
    r2 = s.respond("ನಮ್ಮದು ತೆಂಗು.")
    assert s.crop == "coconut"
    assert s.problem is None
    assert r2.meta["state"] == "ask_problem"
    assert r2.sentences == ["ಎಲೆ ಹಳದಿಯಾಗಿದೆಯೇ, ಕಾಯಿ ಉದುರುತ್ತಿವೆಯೇ, ಅಥವಾ ಮೊಗ್ಗು ಕೊಳೆಯುತ್ತಿದೆಯೇ?"]


def test_unsupported_crop_explicit_supported_crops_and_referral():
    """Unsupported crop response explicitly limits scope to paddy, arecanut, and coconut, and refers to KVK/officer."""
    s = Session()
    r = s.respond("ಕಬ್ಬಿಗೆ ರೋಗ ಬಂದಿದೆ")
    assert r.meta["state"] == "unsupported_crop"
    text = " ".join(r.sentences)
    assert "ಕಬ್ಬು ಬೆಳೆಗೆ ಪರಿಹಾರ ಅಥವಾ ಚಿಕಿತ್ಸಾ ಸಲಹೆ ಸದ್ಯಕ್ಕೆ ನನ್ನಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ" in text
    assert "ಕೃಷಿ ಅಧಿಕಾರಿ ಅಥವಾ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರವನ್ನು ಸಂಪರ್ಕಿಸಿ" in text
    assert "ಪ್ರಸ್ತುತ ನಮ್ಮ ಬೆಂಬಲ ಕೇವಲ ಭತ್ತ, ಅಡಿಕೆ ಮತ್ತು ತೆಂಗು ಬೆಳೆಗಳಿಗೆ ಮಾತ್ರ ಸೀಮಿತವಾಗಿದೆ" in text
    assert not r.end


def test_conversation_started_flag_set():
    """Session marks conversation_started=True on first utterance and retains it."""
    s = Session()
    assert s.conversation_started is False
    s.respond("ನಮಸ್ಕಾರ")
    assert s.conversation_started is True


def test_playback_sync_mic_intake_suppressed_until_playback_done(monkeypatch, tmp_path):
    """Server discards mic audio while playback is active and accepts only after client acknowledges playback."""
    monkeypatch.setattr("app.calllog.cfg.log_dir", str(tmp_path))
    stt = ScriptedSTT(script=["ನಮ್ಮದು ಭತ್ತ"])
    tts = MockStreamingTTS(chunks_per_sentence=2, chunk_delay=0.01)
    server.app.state.stt_factory = lambda: stt
    server.app.state.tts_factory = lambda: tts

    with TestClient(server.app).websocket_connect("/ws/call?ack=1") as ws:
        # While greeting is streaming/playing, send mic frames
        ws.send_bytes(b"\x00" * 1024)
        ws.send_bytes(b"\x00" * 1024)

        # Wait for greeting atomic_reply
        resp_id = None
        for _ in range(60):
            m = ws.receive()
            if m.get("text"):
                j = json.loads(m["text"])
                if j.get("type") == "atomic_reply":
                    resp_id = j["response_id"]
                    break

        assert resp_id is not None
        # Verify server discarded mic frames sent during playback
        assert stt.received_pcm_bytes == 0

        # Now send playback_done to complete turn
        ws.send_text(json.dumps({"type": "playback_done", "response_id": resp_id}))

        # Send mic frames after playback_done acknowledged
        for _ in range(8):
            ws.send_bytes(b"\x00" * 1024)

        # STT should now have received the frames
        assert stt.received_pcm_bytes >= 4096
