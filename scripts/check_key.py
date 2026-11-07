"""Diagnostic utility for testing Gnani API key against the REST STT endpoint.
"""
import pathlib
import sys
import httpx
from app.config import cfg

AUDIO_PATH = pathlib.Path("tests/audio/real/hubli/hd_01.wav")


def main():
    key = cfg.api_key
    is_loaded = bool(key)
    length = len(key)
    has_spaces = any(c.isspace() for c in key)
    has_quotes = "'" in key or '"' in key

    print(f"Key loaded: {is_loaded}")
    print(f"Key length: {length}")
    print(f"Contains spaces: {has_spaces}")
    print(f"Contains quotes: {has_quotes}")

    if not AUDIO_PATH.exists():
        print(f"Audio file missing: {AUDIO_PATH}")
        sys.exit(1)

    headers = {"X-API-Key-ID": key}
    data = {"language_code": "kn-IN"}

    try:
        with open(AUDIO_PATH, "rb") as f:
            files = {"audio_file": (AUDIO_PATH.name, f, "audio/wav")}
            resp = httpx.post(
                "https://api.vachana.ai/stt/v3",
                headers=headers,
                data=data,
                files=files,
                timeout=30.0,
            )
        status_code = resp.status_code
        body_preview = resp.text[:200]
        print(f"HTTP status: {status_code}")
        print(f"Response body (first 200 chars): {body_preview}")

        if 200 <= status_code < 300:
            print("Verdict: key accepted")
        elif status_code == 401:
            print("Verdict: 401: key rejected by Gnani - recreate the key on the API platform dashboard")
        else:
            print(f"Verdict: other error ({status_code})")
    except Exception as e:
        print(f"Request failed: {e}")
        print("Verdict: other error")


if __name__ == "__main__":
    main()

