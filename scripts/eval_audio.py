"""Accuracy check on YOUR recordings.
Put 8 kHz mono 16-bit WAVs in tests/audio/ and list them in tests/audio/labels.csv:
file,crop,problem,note
clip1.wav,paddy,paddy_leaf_folder,udupi accent
Make WAVs:  ffmpeg -i in.m4a -ar 8000 -ac 1 -sample_fmt s16 clip1.wav

Run (full STT accuracy eval, uses Gnani API):
    python -m scripts.eval_audio

Run (format-only validation, no API calls):
    python -m scripts.eval_audio --dry-run
"""
import asyncio, csv, pathlib, sys, wave
from app.dialogue import find_crop, find_problem, KB

D = pathlib.Path("tests/audio")

KNOWN_CROPS = {"paddy", "arecanut", "coconut"}
KNOWN_PROBLEMS = set(KB.keys())


def load(p):
    with wave.open(str(p)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (8000, 1, 2), \
            f"{p.name}: need 8 kHz mono 16-bit"
        return w.readframes(w.getnframes())


def _duration_s(p: pathlib.Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def dry_run():
    csv_path = D / "labels.csv"
    if not csv_path.exists():
        print("FAIL: labels.csv not found")
        sys.exit(1)

    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    if not rows:
        print("FAIL: labels.csv has no data rows")
        sys.exit(1)

    failures = 0
    header = f"{'file':<30} {'crop':<12} {'problem':<25} {'duration':>8}  result"
    print(header)
    print("-" * len(header))

    for r in rows:
        fpath = D / r["file"]
        issues = []

        # Check WAV exists
        if not fpath.exists():
            issues.append("WAV missing")
        else:
            # Check WAV format
            try:
                with wave.open(str(fpath)) as w:
                    rate, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
                    if rate != 8000:
                        issues.append(f"rate={rate} (want 8000)")
                    if ch != 1:
                        issues.append(f"channels={ch} (want 1)")
                    if sw != 2:
                        issues.append(f"sampwidth={sw} (want 2)")
                    dur = w.getnframes() / w.getframerate() if not issues else 0.0
            except Exception as e:
                issues.append(f"unreadable: {e}")
                dur = 0.0

        # Check crop and problem are known
        if r.get("crop", "") not in KNOWN_CROPS:
            issues.append(f"unknown crop '{r.get('crop')}'")
        if r.get("problem", "") not in KNOWN_PROBLEMS:
            issues.append(f"unknown problem '{r.get('problem')}'")

        # Check crop/problem are consistent
        if r.get("problem", "") in KNOWN_PROBLEMS and r.get("crop", "") in KNOWN_CROPS:
            expected_crop = KB[r["problem"]]["crop"]
            if expected_crop != r["crop"]:
                issues.append(f"crop/problem mismatch (problem belongs to {expected_crop})")

        result = "PASS" if not issues else f"FAIL: {'; '.join(issues)}"
        if issues:
            failures += 1
        dur_str = f"{dur:.2f}s" if not issues or "WAV missing" not in issues[0:1] else "n/a"
        print(f"{r['file']:<30} {r.get('crop',''):<12} {r.get('problem',''):<25} {dur_str:>8}  {result}")

    print()
    print(f"Total: {len(rows)} rows, {failures} failures.")
    if failures:
        sys.exit(1)


async def main():
    print("WARNING: these are sine-wave placeholder clips, not real speech. "
          "Results are NOT a measure of STT accuracy.")
    rows = list(csv.DictReader(open(D / "labels.csv", encoding="utf-8")))
    from app.gnani import transcribe_pcm
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
    if "--dry-run" in sys.argv:
        dry_run()
    else:
        asyncio.run(main())
