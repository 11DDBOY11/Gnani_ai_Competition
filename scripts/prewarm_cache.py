"""Pre-generate TTS audio for fixed phrases so calls start fast and credits are saved."""
import asyncio
from app.dialogue import T, KB
from app.gnani import TTS


async def main():
    phrases = [s for v in T.values() for s in v]
    for a in KB.values():
        phrases += [s for v in a["advice_kn"].values() for s in v]
    phrases = list(dict.fromkeys(phrases))
    tts = TTS()
    for i, p in enumerate(phrases, 1):
        print(f"{i}/{len(phrases)} {len(await tts.synth(p))} bytes  {p[:40]}")
    await tts.close()


if __name__ == "__main__":
    asyncio.run(main())
