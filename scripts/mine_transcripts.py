"""Report logged farmer turns where crop was recognized but disease was not."""
import argparse
import json
from pathlib import Path

from app.dialogue import DISEASE_REGISTRY, Session, find_crop
from app.diseases import match_disease


def mine(path: Path) -> list[dict]:
    findings = []
    if not path.exists():
        return findings
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            call = json.loads(line)
        except json.JSONDecodeError:
            continue
        session = Session()
        for turn_no, turn in enumerate(call.get("turns", []), 1):
            if turn.get("who") != "farmer" or not isinstance(turn.get("text"), str):
                continue
            text = turn["text"]
            crop = find_crop(text) or session.crop
            if crop:
                match = match_disease(text, crop, DISEASE_REGISTRY)
                if not match.ids:
                    findings.append({
                        "line": line_no,
                        "turn": turn_no,
                        "crop": crop,
                        "transcript": text,
                    })
            session.respond(text)
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="logs/calls.jsonl",
                        help="calls.jsonl path (default: logs/calls.jsonl)")
    args = parser.parse_args()
    findings = mine(Path(args.path))
    for finding in findings:
        print(json.dumps(finding, ensure_ascii=False))
    print(f"crop_recognized_no_disease_match={len(findings)}")


if __name__ == "__main__":
    main()
