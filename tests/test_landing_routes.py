from fastapi.testclient import TestClient

from app.server import app


def test_farmer_landing_ask_page_and_separate_simulator_route():
    client = TestClient(app)
    landing = client.get("/")
    ask = client.get("/ask")
    simulator = client.get("/sim")

    assert landing.status_code == 200
    assert 'id="startLink"' in landing.text
    assert "Phone assistance is currently unavailable." in landing.text
    assert "Coming soon" in landing.text
    assert "tel:" not in landing.text
    assert "1800-" not in landing.text
    assert "/static/manifest.webmanifest" in landing.text

    assert ask.status_code == 200
    assert 'id="questionBox"' in ask.text
    assert 'id="recordButton"' in ask.text
    assert 'id="answerCard"' in ask.text
    assert ask.text.count('class="suggestion-button"') == 3
    assert "/static/manifest.webmanifest" in ask.text
    assert "voiceModeTab" not in ask.text

    assert simulator.status_code == 200
    assert "Developer simulator" in simulator.text
    assert 'id="call"' in simulator.text and 'id="hang"' in simulator.text
    assert "CALL_TOKEN" in simulator.text
    assert "askKrishiView" not in simulator.text
    assert client.get("/health").status_code == 200
