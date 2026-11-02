import json
from app.config import Config
from app.gnani import stt_headers, tts_request


def test_stt_headers_match_docs_and_are_ascii_and_small():
    c = Config(); c.api_key = "k"
    h = stt_headers(c)
    assert h["model"] == "prisma-v3.0" and h["x-sample-rate"] == "8000" and h["x-api-key-id"] == "k"
    for v in h.values():
        v.encode("ascii")
    assert len(json.loads(h["keyterms"])) <= 200
    assert sum(len(k) + len(v) for k, v in h.items()) < 6000


def test_tts_request_shape():
    r = tts_request("ನಮಸ್ಕಾರ", Config())
    assert r["language"] == "kn-IN" and r["audio_config"]["container"] == "raw"
    assert r["audio_config"]["sample_rate"] == 8000 and 0.85 <= r["speed"] <= 1.15
