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
import asyncio, csv, datetime, pathlib, sys, wave
from app.config import cfg
from app.dialogue import find_crop, find_problem, KB

D = pathlib.Path("tests/audio")
REPORTS_DIR = pathlib.Path("reports")

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


def _sanitize_error(err_str: str) -> str:
    """Sanitize error messages to ensure no credentials or sensitive tokens leak."""
    if not err_str:
        return ""
    # Strip any potential API key tokens or raw header blobs
    msg = str(err_str).replace("\r", " ").replace("\n", " ").strip()
    if cfg.api_key and cfg.api_key in msg:
        msg = msg.replace(cfg.api_key, "[REDACTED]")
    return msg[:300]


def get_retry_files(retry_report_path: pathlib.Path) -> list[str]:
    """Return ordered list of files needing retry from a previous eval report."""
    with open(retry_report_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            r["file"] for r in reader
            if r.get("status") in ("api_error", "empty_transcript")
        ]


def is_dns_error(err_str: str) -> bool:
    """Check if an error string indicates DNS resolution failure."""
    s = err_str.lower()
    return "getaddrinfo failed" in s or "name or service not known" in s or "nodename nor servname provided" in s


async def run_evaluation(rows: list[dict], report_prefix: str = "eval_report", is_retry: bool = False, unattempted_initial: list[dict] = None):
    from app.gnani import transcribe_pcm

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"{report_prefix}_{timestamp}.csv"

    fieldnames = [
        "file",
        "note",
        "expected_crop",
        "expected_problem",
        "transcript",
        "predicted_crop",
        "predicted_problem",
        "crop_correct",
        "problem_correct",
        "status",
        "error",
    ]

    report_file = open(report_path, "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(report_file, fieldnames=fieldnames)
    writer.writeheader()
    report_file.flush()

    total_target = len(rows)
    attempted_clips = 0
    successful_transcriptions = 0
    empty_transcripts = 0
    api_errors = 0

    overall_crop_correct = 0
    overall_problem_correct = 0

    note_stats = {}
    completed_rows = []
    unattempted_rows = []

    consecutive_dns_failures = 0

    try:
        for idx, r in enumerate(rows):
            file_rel = r["file"]
            expected_c = r.get("crop", "")
            expected_p = r.get("problem", "")
            note = r.get("note", "").strip() or "unspecified"

            # Check consecutive DNS failures threshold before starting next clip
            if consecutive_dns_failures >= 2:
                print(f"\n[ABORT] 2 consecutive DNS connection failures occurred. Stopping run to save progress.")
                unattempted_rows = rows[idx:]
                break

            attempted_clips += 1
            if note not in note_stats:
                note_stats[note] = {
                    "attempted": 0,
                    "transcribed": 0,
                    "empty": 0,
                    "api_errors": 0,
                    "crop_correct": 0,
                    "problem_correct": 0,
                }
            note_stats[note]["attempted"] += 1

            text = ""
            predicted_c = None
            predicted_p = None
            crop_ok = False
            problem_ok = False
            status = "unknown"
            error_msg = ""

            try:
                wav_bytes = load(D / file_rel)
                evs = await transcribe_pcm(wav_bytes)
                text = " ".join(e.get("text", "") for e in evs if e.get("type") == "transcript").strip()

                if text:
                    status = "success"
                    successful_transcriptions += 1
                    note_stats[note]["transcribed"] += 1
                    predicted_c = find_crop(text)
                    predicted_p = find_problem(text, predicted_c)
                    crop_ok = (predicted_c == expected_c)
                    problem_ok = (predicted_p == expected_p)
                    if crop_ok:
                        overall_crop_correct += 1
                        note_stats[note]["crop_correct"] += 1
                    if problem_ok:
                        overall_problem_correct += 1
                        note_stats[note]["problem_correct"] += 1
                    consecutive_dns_failures = 0
                else:
                    status = "empty_transcript"
                    empty_transcripts += 1
                    note_stats[note]["empty"] += 1
                    crop_ok = False
                    problem_ok = False
                    consecutive_dns_failures = 0
            except Exception as e:
                status = "api_error"
                api_errors += 1
                note_stats[note]["api_errors"] += 1
                error_msg = _sanitize_error(str(e))
                crop_ok = False
                problem_ok = False

                if is_dns_error(error_msg):
                    consecutive_dns_failures += 1
                else:
                    consecutive_dns_failures = 0

            row_data = {
                "file": file_rel,
                "note": note,
                "expected_crop": expected_c,
                "expected_problem": expected_p,
                "transcript": text,
                "predicted_crop": predicted_c or "",
                "predicted_problem": predicted_p or "",
                "crop_correct": "TRUE" if crop_ok else "FALSE",
                "problem_correct": "TRUE" if problem_ok else "FALSE",
                "status": status,
                "error": error_msg,
            }

            writer.writerow(row_data)
            report_file.flush()
            completed_rows.append(row_data)

            crop_label = "OK " if crop_ok else "BAD"
            prob_label = "OK " if problem_ok else "BAD"
            display_status = status.upper() if status != "success" else f"crop={crop_label} problem={prob_label}"
            print(f"{file_rel:<25} {display_status:<22} | {text:<40} | {note}", flush=True)

    finally:
        report_file.close()

    # Detailed Summary
    header_title = "RECOVERY EVALUATION SUMMARY" if is_retry else "EVALUATION SUMMARY"
    print("\n" + "=" * 80)
    print(header_title)
    print("=" * 80)
    print(f"Target Clips to Evaluate     : {total_target}")
    print(f"Attempted Clips              : {attempted_clips}")
    print(f"Unattempted Clips (Aborted)  : {len(unattempted_rows)}")
    print(f"Successfully Transcribed     : {successful_transcriptions}")
    print(f"Empty Transcripts            : {empty_transcripts}")
    print(f"API / Network Errors         : {api_errors}")
    print("-" * 80)

    # Denominators:
    # 1. Attempted clips denominator
    denom_att = max(attempted_clips, 1)
    acc_c_att = overall_crop_correct / denom_att
    acc_p_att = overall_problem_correct / denom_att
    print(f"Accuracy across Attempted Clips (denominator = {attempted_clips}):")
    print(f"  Crop Accuracy    : {overall_crop_correct}/{attempted_clips} = {acc_c_att:.1%}")
    print(f"  Problem Accuracy : {overall_problem_correct}/{attempted_clips} = {acc_p_att:.1%}")

    # 2. Successfully transcribed denominator
    if successful_transcriptions > 0:
        denom_tx = successful_transcriptions
        acc_c_tx = overall_crop_correct / denom_tx
        acc_p_tx = overall_problem_correct / denom_tx
        print(f"\nRecognition Accuracy across Transcribed Clips (denominator = {denom_tx}):")
        print(f"  Crop Accuracy    : {overall_crop_correct}/{denom_tx} = {acc_c_tx:.1%}")
        print(f"  Problem Accuracy : {overall_problem_correct}/{denom_tx} = {acc_p_tx:.1%}")

    # Breakdown by note
    print("\n" + "-" * 80)
    print("PER-NOTE BREAKDOWN")
    print("-" * 80)
    for note, s in sorted(note_stats.items()):
        att = s["attempted"]
        tx = s["transcribed"]
        c_cor = s["crop_correct"]
        p_cor = s["problem_correct"]
        emp = s["empty"]
        err = s["api_errors"]
        c_acc = c_cor / att if att else 0.0
        p_acc = p_cor / att if att else 0.0
        tx_c_acc = c_cor / tx if tx else 0.0
        tx_p_acc = p_cor / tx if tx else 0.0
        print(f"[{note}] (attempted={att}, transcribed={tx}, empty={emp}, api_errors={err})")
        print(f"  Attempted: crop {c_cor}/{att} ({c_acc:.1%}) | problem {p_cor}/{att} ({p_acc:.1%})")
        if tx != att and tx > 0:
            print(f"  On tx    : crop {c_cor}/{tx} ({tx_c_acc:.1%}) | problem {p_cor}/{tx} ({tx_p_acc:.1%})")

    # Unattempted clips list
    if unattempted_rows:
        print("\n" + "-" * 80)
        print(f"UNATTEMPTED CLIPS ({len(unattempted_rows)} total - NOT counted as recognition errors)")
        print("-" * 80)
        for u in unattempted_rows:
            print(f"  - {u['file']} ({u.get('note', '')})")

    # Mismatches list
    mismatches = [
        r for r in completed_rows
        if r["crop_correct"] != "TRUE" or r["problem_correct"] != "TRUE"
    ]
    print("\n" + "=" * 80)
    print(f"MISMATCHED / FAILED CLIPS ({len(mismatches)} total)")
    print("=" * 80)
    if mismatches:
        for m in mismatches:
            print(f"\nFile           : {m['file']} ({m['note']})")
            print(f"  Status       : {m['status']}" + (f" (Error: {m['error']})" if m['error'] else ""))
            print(f"  Transcript   : \"{m['transcript']}\"")
            print(f"  Expected     : crop={m['expected_crop']}, problem={m['expected_problem']}")
            print(f"  Predicted    : crop={m['predicted_crop'] or 'NONE'}, problem={m['predicted_problem'] or 'NONE'}")
            print(f"  Match Result : crop={'OK' if m['crop_correct'] == 'TRUE' else 'MISMATCH'}, problem={'OK' if m['problem_correct'] == 'TRUE' else 'MISMATCH'}")
    else:
        print("None! All evaluated clips recognized correctly.")

    print("\n" + "=" * 80)
    print(f"Report saved to: {report_path.resolve()}")
    print("=" * 80)
    return report_path


async def main():
    retry_report_arg = None
    if "--retry-report" in sys.argv:
        try:
            arg_idx = sys.argv.index("--retry-report")
            retry_report_arg = sys.argv[arg_idx + 1]
        except IndexError:
            sys.exit("Error: --retry-report requires a PATH argument")

    labels_path = D / "labels.csv"
    if not labels_path.exists():
        sys.exit("Error: tests/audio/labels.csv not found")

    all_labels = list(csv.DictReader(open(labels_path, encoding="utf-8")))

    if retry_report_arg:
        retry_path = pathlib.Path(retry_report_arg)
        if not retry_path.exists():
            sys.exit(f"Error: Retry report file not found: {retry_path}")

        retry_files = set(get_retry_files(retry_path))
        target_rows = [r for r in all_labels if r["file"] in retry_files]
        print(f"Selected {len(target_rows)} clips for recovery evaluation from {retry_path.name}")
        await run_evaluation(target_rows, report_prefix="recovery_report", is_retry=True)
    else:
        if any("placeholder" in r.get("note", "").lower() for r in all_labels):
            print("WARNING: these are sine-wave placeholder clips, not real speech. "
                  "Results are NOT a measure of STT accuracy.")
        await run_evaluation(all_labels, report_prefix="eval_report", is_retry=False)


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        dry_run()
    else:
        asyncio.run(main())
