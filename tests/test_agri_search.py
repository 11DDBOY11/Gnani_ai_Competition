import io
import json
import wave

from fastapi.testclient import TestClient

from app import agri_search
from app.server import app


class FakeGroqResponse:
    def raise_for_status(self):
        return None

    def json(self):
        content = json.dumps({
            "answer": "Check the affected leaves and ask a local officer before using chemicals.",
            "confidence": "medium",
            "needs_expert_review": False,
            "sources": ["unverified model source"],
        })
        return {"choices": [{"message": {"content": f"```json\n{content}\n```"}}]}


class FakeGroqClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        assert url == agri_search.GROQ_CHAT_URL
        assert "Authorization" in kwargs["headers"]
        return FakeGroqResponse()


class FakeTTS:
    def __init__(self):
        self.language = None

    async def stream_cached(self, text, language="kn-IN"):
        self.language = language
        yield b"\x01\x00\x02\x00"


def test_agri_search_requires_question_of_at_least_five_chars():
    client = TestClient(app)
    assert client.post("/api/agri-search", json={}).status_code == 400
    response = client.post("/api/agri-search", json={"question": "leaf"})
    assert response.status_code == 400
    assert "5 and 1000" in response.json()["detail"]


def test_agri_search_defaults_to_kannada_and_parses_mocked_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(agri_search.httpx, "AsyncClient", FakeGroqClient)
    response = TestClient(app).post(
        "/api/agri-search",
        json={"question": "What should I check on the leaves?", "crop": "paddy"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "kn"
    assert data["confidence"] == "medium"
    assert data["answer"].startswith("Check the affected leaves")
    assert data["sources"] == []
    assert data["needs_expert_review"] is False


def test_agri_search_missing_groq_key_returns_clear_503(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = TestClient(app).post(
        "/api/agri-search", json={"question": "What should I do about leaf spots?"}
    )
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_agri_search_malformed_model_json_uses_safe_fallback():
    result = agri_search.parse_model_content("not json and not a safe answer", "en")
    assert result["confidence"] == "low"
    assert result["needs_expert_review"] is True
    assert result["sources"] == []
    assert "1800-180-1551" in result["answer"]


def test_pwa_static_files_are_served():
    client = TestClient(app)
    manifest = client.get("/static/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.json()["start_url"] == "/"
    assert client.get("/static/icons/icon-192.png").status_code == 200
    assert client.get("/static/icons/icon-512.png").status_code == 200


def test_speak_endpoint_returns_browser_playable_wav(monkeypatch):
    tts = FakeTTS()
    monkeypatch.setattr("app.server.cfg.api_key", "test-gnani-key")
    monkeypatch.setattr(app.state, "tts_factory", lambda: tts)
    response = TestClient(app).post(
        "/api/agri-search/speak", json={"text": "A short answer", "language": "en"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert tts.language == "en-IN"
    with wave.open(io.BytesIO(response.content), "rb") as audio:
        assert audio.getframerate() == 8000
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getnframes() == 2
