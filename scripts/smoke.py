"""Step-by-step API check:  python -m scripts.smoke
1) TTS: Kannada sentence -> out/tts_test.wav (prints time to first audio)
2) STT: feeds that audio back to Prisma and prints what it heard
"""
import asyncio, pathlib, sys, time, wave
from app.config import cfg
from app.gnani import TTS, transcribe_pcm

SENT = "ನಮಸ್ಕಾರ. ನನ್ನ ಭತ್ತದ ಗದ್ದೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ."


async def main():
    if not cfg.api_key:
        sys.exit("GNANI_API_KEY missing. Copy .env.example to .env and set it.")
    out = pathlib.Path("out"); out.mkdir(exist_ok=True)
    tts = TTS(); t0 = time.monotonic(); first = None; pcm = bytearray()
    async for c in tts._stream(SENT):
        first = first or time.monotonic(); pcm += c
    print(f"[TTS] first audio {int((first - t0) * 1000)} ms, {len(pcm) / 2 / cfg.sample_rate:.1f}s of audio")
    with wave.open(str(out / "tts_test.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(cfg.sample_rate); w.writeframes(bytes(pcm))
    print("[TTS] wrote out/tts_test.wav - play it and confirm it sounds like Kannada")
    evs = await transcribe_pcm(bytes(pcm))
    for e in evs:
        print("[STT]", e.get("type"), e.get("text") or e.get("message"), "| latency", e.get("latency"), "| lang", e.get("detected_language_code"))
    if not evs:
        print("[STT] no transcript - check key, sample rate, VAD settings")


if __name__ == "__main__":
    asyncio.run(main())
