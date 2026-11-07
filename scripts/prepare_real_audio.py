"""Convert recorded audio clips to 8 kHz mono 16-bit WAV for evaluation,
and generate tests/audio/labels.csv.
"""
import csv
import pathlib
import subprocess
import sys

AUDIO_DIR = pathlib.Path("audio")
TESTS_AUDIO_DIR = pathlib.Path("tests/audio")
LABELS_CSV = TESTS_AUDIO_DIR / "labels.csv"

SUPPORTED_EXTS = (".ogg", ".mp3", ".m4a", ".wav")

MAP_HD_CK = {
    "01": ("paddy", "paddy_leaf_folder"),
    "02": ("paddy", "paddy_blast"),
    "03": ("arecanut", "arecanut_koleroga"),
    "04": ("arecanut", "arecanut_koleroga"),
    "05": ("coconut", "coconut_rhino_beetle"),
    "06": ("coconut", "coconut_bud_rot"),
    "07": ("paddy", "paddy_leaf_folder"),
    "08": ("arecanut", "arecanut_koleroga"),
    "09": ("coconut", "coconut_rhino_beetle"),
    "10": ("paddy", "paddy_blast"),
    "11": ("paddy", "paddy_leaf_folder"),
    "12": ("coconut", "coconut_bud_rot"),
}

MAP_NZ = {
    "01": ("paddy", "paddy_leaf_folder", "hubli-dharwad-noisy"),
    "02": ("arecanut", "arecanut_koleroga", "hubli-dharwad-noisy"),
    "03": ("coconut", "coconut_bud_rot", "hubli-dharwad-noisy"),
    "04": ("paddy", "paddy_blast", "hubli-dharwad-noisy"),
    "05": ("paddy", "paddy_leaf_folder", "coastal-mangaluru-noisy"),
    "06": ("arecanut", "arecanut_koleroga", "coastal-mangaluru-noisy"),
    "07": ("coconut", "coconut_bud_rot", "coastal-mangaluru-noisy"),
    "08": ("paddy", "paddy_blast", "coastal-mangaluru-noisy"),
}


def find_clip(candidate_dirs: list[pathlib.Path], base_name: str) -> pathlib.Path | None:
    for d in candidate_dirs:
        if not d.exists() or not d.is_dir():
            continue
        # Direct check
        for ext in SUPPORTED_EXTS:
            p = d / f"{base_name}{ext}"
            if p.exists() and p.is_file():
                return p
        # Case-insensitive check
        for p in d.iterdir():
            if p.is_file() and p.stem.lower() == base_name.lower() and p.suffix.lower() in SUPPORTED_EXTS:
                return p
    return None


def build_expected_items():
    items = []

    # Hubli hd_01 ... hd_12
    hubli_dirs = [AUDIO_DIR / "hubli", AUDIO_DIR / "hubbli"]
    for i in range(1, 13):
        idx = f"{i:02d}"
        name = f"hd_{idx}"
        crop, problem = MAP_HD_CK[idx]
        items.append({
            "group": "hubli",
            "name": name,
            "candidate_dirs": hubli_dirs,
            "crop": crop,
            "problem": problem,
            "note": "hubli-dharwad-quiet",
        })

    # Coastal ck_01 ... ck_12
    coastal_dirs = [AUDIO_DIR / "coastal"]
    for i in range(1, 13):
        idx = f"{i:02d}"
        name = f"ck_{idx}"
        crop, problem = MAP_HD_CK[idx]
        items.append({
            "group": "coastal",
            "name": name,
            "candidate_dirs": coastal_dirs,
            "crop": crop,
            "problem": problem,
            "note": "coastal-mangaluru-quiet",
        })

    # Noisy nz_01 ... nz_08
    noisy_dirs = [AUDIO_DIR / "noisy"]
    for i in range(1, 9):
        idx = f"{i:02d}"
        name = f"nz_{idx}"
        crop, problem, note = MAP_NZ[idx]
        items.append({
            "group": "noisy",
            "name": name,
            "candidate_dirs": noisy_dirs,
            "crop": crop,
            "problem": problem,
            "note": note,
        })

    return items


def main():
    expected_items = build_expected_items()
    converted = []
    missing = []
    failed = []

    for item in expected_items:
        group = item["group"]
        name = item["name"]
        src = find_clip(item["candidate_dirs"], name)
        if not src:
            missing.append(f"{group}/{name}")
            continue

        out_dir = TESTS_AUDIO_DIR / "real" / group
        out_dir.mkdir(parents=True, exist_ok=True)
        out_wav = out_dir / f"{name}.wav"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-ar",
            "8000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            str(out_wav),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            err = res.stderr.strip() if res.stderr else "Unknown ffmpeg error"
            failed.append((f"{group}/{name}", err))
            continue

        rel_csv_path = f"real/{group}/{name}.wav"
        converted.append({
            "file": rel_csv_path,
            "crop": item["crop"],
            "problem": item["problem"],
            "note": item["note"],
            "source": str(src),
        })

    # Overwrite labels.csv with converted rows only
    TESTS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    with open(LABELS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "crop", "problem", "note"])
        writer.writeheader()
        for c in converted:
            writer.writerow({
                "file": c["file"],
                "crop": c["crop"],
                "problem": c["problem"],
                "note": c["note"],
            })

    # Print summary table
    print("=" * 88)
    print(f"{'FILE':<26} {'CROP':<10} {'PROBLEM':<24} {'NOTE':<26}")
    print("=" * 88)
    for c in converted:
        print(f"{c['file']:<26} {c['crop']:<10} {c['problem']:<24} {c['note']:<26}")
    print("=" * 88)
    print(f"Total successfully converted: {len(converted)} / {len(expected_items)}")

    if missing:
        print("\nEXPECTED FILES THAT ARE MISSING:")
        for m in missing:
            print(f"  - {m}")
    else:
        print("\nNo expected files were missing.")

    if failed:
        print("\nFFMPEG CONVERSION FAILURES:")
        for name, err in failed:
            print(f"  - {name}: {err}")
    else:
        print("No ffmpeg failures.")

    print(f"\nWritten {len(converted)} rows to {LABELS_CSV}")


if __name__ == "__main__":
    main()

