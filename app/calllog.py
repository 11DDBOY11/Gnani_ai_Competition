import json, pathlib, time
from .config import cfg


def _append(name, obj):
    d = pathlib.Path(cfg.log_dir)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / name, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def log_call(call_id, turns, outcome):
    _append("calls.jsonl", {"call_id": call_id, "ts": time.time(), "outcome": outcome, "turns": turns})


def queue_sms(call_id, phone_tail, text):
    _append("sms_outbox.jsonl", {"call_id": call_id, "phone_tail": phone_tail, "text": text, "status": "queued_not_sent"})
