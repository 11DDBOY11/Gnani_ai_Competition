"""Accuracy check on YOUR recordings.
Put 8 kHz mono 16-bit WAVs in tests/audio/ and list them in tests/audio/labels.csv:
file,crop,problem,note
clip1.wav,paddy,paddy_leaf_folder,udupi accent
Make WAVs:  ffmpeg -i in.m4a -ar 8000 -ac 1 -sample_fmt s16 clip1.wav
Run: python -m scripts.eval_audio
"""
import asyncio, csv, pathlib, wave
from app.gnani import transcribe_pcm
from app.dialogue import find_crop, find_problem

D = pathlib.Path("tests/audio")


def load(p):
    with wave.open(str(p)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (8000, 1, 2), f"{p.name}: need 8 kHz mono 16-bit"
        return w.readframes(w.getnframes())


async def main():
    rows = list(csv.DictReader(open(D / "labels.csv", encoding="utf-8")))
    ok_c = ok_p = 0
    for r in rows:
        evs = await transcribe_pcm(load(D / r["file"]))
        text = " ".join(e.get("text", "") for e in evs if e.get("type") == "transcript")
        c = find_crop(text); p = find_problem(text, c)
        ok_c += c == r["crop"]; ok_p += p == r["problem"]
        print(f"{r['file']:20} crop={'OK ' if c == r['crop'] else 'BAD'} problem={'OK ' if p == r['problem'] else 'BAD'} | {text} | {r.get('note', '')}")
    n = max(len(rows), 1)
    print(f"\ncrop accuracy {ok_c}/{len(rows)} = {ok_c / n:.0%}   problem accuracy {ok_p}/{len(rows)} = {ok_p / n:.0%}")


if __name__ == "__main__":
    asyncio.run(main())
