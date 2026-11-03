"""Seed script: generates local sine-wave placeholder WAVs for format testing.

This does NOT call the Gnani API. It produces valid 8 kHz mono 16-bit WAV
files containing a short 440 Hz tone followed by silence — enough for
format validation with eval_audio --dry-run.

To replace these with real TTS audio, run:
    python -m scripts.gen_baseline_clips   (requires GNANI_API_KEY)
"""
import csv, json, math, pathlib, struct, wave

KB_PATH = pathlib.Path("app/kb.json")
OUT_DIR = pathlib.Path("tests/audio/clips")
LABELS_CSV = pathlib.Path("tests/audio/labels.csv")

# NEEDS NATIVE REVIEW — written for pipeline testing only.
SENTENCES = {
    "paddy_leaf_folder": [
        "\u0ca8\u0cae\u0ccd\u0cae \u0cad\u0ca4\u0ccd\u0ca4\u0ca6 \u0c97\u0ca6\u0ccd\u0ca6\u0cc6\u0caf\u0cb2\u0ccd\u0cb2\u0cbf \u0c8e\u0cb2\u0cc6 \u0cb8\u0cc1\u0ca4\u0ccd\u0ca4\u0cbf\u0c95\u0cca\u0c82\u0ca1\u0cbf\u0ca6\u0cc6.",
        "\u0cad\u0ca4\u0ccd\u0ca4\u0ca6 \u0c8e\u0cb2\u0cc6 \u0cae\u0ca1\u0c9a\u0cbf\u0c95\u0cca\u0cb3\u0ccd\u0cb3\u0cc1\u0ca4\u0ccd\u0ca4\u0cbf\u0ca6\u0cc6 \u0c8f\u0ca8\u0cc1 \u0cae\u0cbe\u0ca1\u0cb2\u0cbf.",
    ],
    "paddy_blast": [
        "\u0cad\u0ca4\u0ccd\u0ca4\u0ca6 \u0c97\u0ca6\u0ccd\u0ca6\u0cc6\u0caf\u0cb2\u0ccd\u0cb2\u0cbf \u0cac\u0cc6\u0c82\u0c95\u0cbf \u0cb0\u0ccb\u0c97 \u0cac\u0c82\u0ca6\u0cbf\u0ca6\u0cc6.",
        "\u0ca8\u0cae\u0ccd\u0cae \u0c97\u0ca6\u0ccd\u0ca6\u0cc6\u0caf\u0cb2\u0ccd\u0cb2\u0cbf \u0cad\u0ca4\u0ccd\u0ca4\u0c95\u0ccd\u0c95\u0cc6 \u0cac\u0ccd\u0cb2\u0cbe\u0cb8\u0ccd\u0c9f\u0ccd \u0c86\u0c97\u0cbf\u0ca6\u0cc6.",
    ],
    "arecanut_koleroga": [
        "\u0c85\u0ca1\u0cbf\u0c95\u0cc6 \u0ca4\u0ccb\u0c9f\u0ca6\u0cb2\u0ccd\u0cb2\u0cbf \u0c95\u0cbe\u0caf\u0cbf \u0c95\u0cca\u0cb3\u0cc6 \u0cb0\u0ccb\u0c97 \u0cac\u0c82\u0ca6\u0cbf\u0ca6\u0cc6.",
        "\u0ca8\u0cae\u0ccd\u0cae \u0c85\u0ca1\u0cbf\u0c95\u0cc6\u0c97\u0cc6 \u0c95\u0cca\u0cb3\u0cc6\u0cb0\u0ccb\u0c97 \u0ca4\u0c97\u0cc1\u0cb2\u0cbf\u0ca6\u0cc6 \u0cb8\u0cb9\u0cbe\u0caf \u0cae\u0cbe\u0ca1\u0cbf.",
    ],
    "coconut_rhino_beetle": [
        "\u0ca4\u0cc6\u0c82\u0c97\u0cbf\u0ca8 \u0cae\u0cb0\u0c95\u0ccd\u0c95\u0cc6 \u0c95\u0cca\u0c82\u0cac\u0cbf\u0ca8 \u0ca6\u0cc1\u0c82\u0cac\u0cbf \u0cb9\u0cbe\u0cb5\u0cb3\u0cbf \u0c86\u0c97\u0cbf\u0ca6\u0cc6.",
        "\u0ca8\u0cae\u0ccd\u0cae \u0ca4\u0cc6\u0c82\u0c97\u0cbf\u0ca8 \u0ca4\u0ccb\u0c9f\u0ca6\u0cb2\u0ccd\u0cb2\u0cbf \u0ca6\u0cc1\u0c82\u0cac\u0cbf \u0cb9\u0cbe\u0ca8\u0cbf \u0cae\u0cbe\u0ca1\u0cc1\u0ca4\u0ccd\u0ca4\u0cbf\u0ca6\u0cc6.",
    ],
    "coconut_bud_rot": [
        "\u0ca4\u0cc6\u0c82\u0c97\u0cbf\u0ca8 \u0cae\u0cb0\u0ca6 \u0cb8\u0cc1\u0cb3\u0cbf \u0c95\u0cca\u0cb3\u0cc6 \u0c86\u0c97\u0cc1\u0ca4\u0ccd\u0ca4\u0cbf\u0ca6\u0cc6.",
        "\u0ca8\u0cae\u0ccd\u0cae \u0ca4\u0cc6\u0c82\u0c97\u0cbf\u0ca8 \u0cb8\u0cc1\u0cb3\u0cbf \u0c95\u0cca\u0cb3\u0cc6\u0ca4\u0cc1 \u0cb9\u0ccb\u0c97\u0cc1\u0ca4\u0ccd\u0ca4\u0cbf\u0ca6\u0cc6.",
    ],
}

SR = 8000


def make_pcm(duration_s: float = 1.5) -> bytes:
    """440 Hz tone for 0.3 s then silence — valid PCM for format testing."""
    n = int(SR * duration_s)
    frames = []
    for i in range(n):
        t = i / SR
        val = int(16000 * math.sin(2 * math.pi * 440 * t)) if t < 0.3 else 0
        frames.append(struct.pack("<h", val))
    return b"".join(frames)


def main():
    kb = json.loads(KB_PATH.read_text(encoding="utf-8"))
    advisories = {a["id"]: a for a in kb["advisories"]}

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    total_chars = 0

    for aid, adv in advisories.items():
        for n, sentence in enumerate(SENTENCES.get(aid, []), start=1):
            fname = f"clips/{aid}_{n}.wav"
            wav_path = pathlib.Path("tests/audio") / fname
            pcm = make_pcm(1.5)
            with wave.open(str(wav_path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SR)
                w.writeframes(pcm)
            rows.append({
                "file": fname,
                "crop": adv["crop"],
                "problem": aid,
                "note": "sine-wave-placeholder",
            })
            total_chars += len(sentence)
            print(f"  wrote {fname}  ({len(sentence)} chars)")

    # Write labels.csv fresh (header + all rows)
    with open(LABELS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "crop", "problem", "note"])
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"Done. {len(rows)} clips generated (local sine-wave placeholder, NOT TTS), {total_chars} chars.")
    print(f"Written {len(rows)} rows to {LABELS_CSV}")
    print("NOTE: Run python -m scripts.gen_baseline_clips with GNANI_API_KEY to replace with real TTS audio.")


if __name__ == "__main__":
    main()
