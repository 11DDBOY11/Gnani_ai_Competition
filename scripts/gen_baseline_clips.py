"""Generate synthetic baseline audio clips for pipeline smoke-testing.

WARNING: These clips are synthesised by the Gnani Timbre TTS engine from
hand-written Kannada sentences. They are NOT real farmer speech recordings.
They exist only to verify that the audio pipeline (WAV format, labels.csv
schema, eval_audio --dry-run) works end-to-end. Do NOT use these clips to
measure STT accuracy or dialogue matching accuracy on real farmer speech.

Usage:
    python -m scripts.gen_baseline_clips

Requires GNANI_API_KEY to be set (calls the Timbre TTS API).
Outputs:
    tests/audio/clips/{advisory_id}_{n}.wav   (8 kHz mono 16-bit WAV)
    Appends rows to tests/audio/labels.csv
"""
import asyncio, csv, json, pathlib, sys, wave

KB_PATH = pathlib.Path("app/kb.json")
OUT_DIR = pathlib.Path("tests/audio/clips")
LABELS_CSV = pathlib.Path("tests/audio/labels.csv")

# Hand-crafted farmer-style sentences per advisory.
# Each entry is a list of exactly 2 sentences.
# NEEDS NATIVE REVIEW — written for pipeline testing only.
SENTENCES = {
    "paddy_leaf_folder": [
        "ನಮ್ಮ ಭತ್ತದ ಗದ್ದೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ.",
        "ಭತ್ತದ ಎಲೆ ಮಡಚಿಕೊಳ್ಳುತ್ತಿದೆ ಏನು ಮಾಡಲಿ.",
    ],
    "paddy_blast": [
        "ಭತ್ತದ ಗದ್ದೆಯಲ್ಲಿ ಬೆಂಕಿ ರೋಗ ಬಂದಿದೆ.",
        "ನಮ್ಮ ಗದ್ದೆಯಲ್ಲಿ ಭತ್ತಕ್ಕೆ ಬ್ಲಾಸ್ಟ್ ಆಗಿದೆ.",
    ],
    "arecanut_koleroga": [
        "ಅಡಿಕೆ ತೋಟದಲ್ಲಿ ಕಾಯಿ ಕೊಳೆ ರೋಗ ಬಂದಿದೆ.",
        "ನಮ್ಮ ಅಡಿಕೆಗೆ ಕೊಳೆರೋಗ ತಗುಲಿದೆ ಸಹಾಯ ಮಾಡಿ.",
    ],
    "coconut_rhino_beetle": [
        "ತೆಂಗಿನ ಮರಕ್ಕೆ ಕೊಂಬಿನ ದುಂಬಿ ಹಾವಳಿ ಆಗಿದೆ.",
        "ನಮ್ಮ ತೆಂಗಿನ ತೋಟದಲ್ಲಿ ದುಂಬಿ ಹಾನಿ ಮಾಡುತ್ತಿದೆ.",
    ],
    "coconut_bud_rot": [
        "ತೆಂಗಿನ ಮರದ ಸುಳಿ ಕೊಳೆ ಆಗುತ್ತಿದೆ.",
        "ನಮ್ಮ ತೆಂಗಿನ ಸುಳಿ ಕೊಳೆತು ಹೋಗುತ್ತಿದೆ.",
    ],
}


def _write_wav(path: pathlib.Path, pcm: bytes, sample_rate: int = 8000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)


async def main():
    from app.gnani import TTS
    from app.config import cfg

    if not cfg.api_key:
        sys.exit("GNANI_API_KEY not set. Cannot synthesise audio. Exiting.")

    kb = json.loads(KB_PATH.read_text(encoding="utf-8"))
    advisories = {a["id"]: a for a in kb["advisories"]}

    # Read labels.csv once to know which rows are already recorded.
    existing_labels = set()
    if LABELS_CSV.exists():
        with open(LABELS_CSV, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                existing_labels.add(row["file"])

    tts = TTS()
    total_clips = 0
    total_chars = 0
    new_rows: list[dict] = []

    for aid, adv in advisories.items():
        sentences = SENTENCES.get(aid)
        if not sentences:
            print(f"  SKIP {aid}: no hand-crafted sentences defined")
            continue

        for n, sentence in enumerate(sentences, start=1):
            fname = f"clips/{aid}_{n}.wav"
            wav_path = pathlib.Path("tests/audio") / fname
            if wav_path.exists():
                print(f"  SKIP {fname}: WAV already exists on disk")
                continue

            print(f"  TTS → {fname}  ({len(sentence)} chars)  {sentence[:50]}")
            try:
                pcm = await tts.synth(sentence)
            except Exception as e:
                print(f"  ERROR {fname}: {e}")
                continue

            _write_wav(wav_path, pcm, sample_rate=cfg.sample_rate)
            new_rows.append({
                "file": fname,
                "crop": adv["crop"],
                "problem": aid,
                "note": "synthetic-tts-baseline",  # real TTS audio
            })
            total_clips += 1
            total_chars += len(sentence)

    await tts.close()

    # Append new rows to labels.csv only for newly generated clips.
    # Write header only if the file is new or empty.
    if new_rows:
        write_header = not LABELS_CSV.exists() or LABELS_CSV.stat().st_size == 0
        with open(LABELS_CSV, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["file", "crop", "problem", "note"])
            if write_header:
                writer.writeheader()
            writer.writerows(new_rows)

    print(f"\nDone. {total_clips} clips generated, {total_chars} TTS characters sent.")
    if new_rows:
        print(f"Appended {len(new_rows)} rows to {LABELS_CSV}")


if __name__ == "__main__":
    asyncio.run(main())
