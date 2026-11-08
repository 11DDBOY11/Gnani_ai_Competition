from fastapi.testclient import TestClient
from app.server import app


def test_root_landing_and_separate_simulator_route():
    client = TestClient(app)
    landing = client.get("/")
    simulator = client.get("/sim")
    assert landing.status_code == 200
    assert "ಕೃಷಿ ಮಿತ್ರ" in landing.text
    assert "Government Kisan Call Centre" in landing.text
    assert "not Krishi Mitra's Exotel line" in landing.text
    assert simulator.status_code == 200
    assert "Krishi Mitra - phone simulator" in simulator.text
    assert client.get("/health").status_code == 200
