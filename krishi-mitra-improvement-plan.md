# Krishi Mitra — Comprehensive Improvement Plan

## Top-Level Overview

**Goal:** Evolve Krishi Mitra from a functional MVP (demo-ready, single developer) into a production-grade Kannada voice advisory service that farmers can actually call, receive SMS summaries from, and trust for accurate agronomic guidance.

**Current state:** FastAPI WebSocket server + Gnani Prisma v3.0 STT + Timbre TTS + keyword-based slot-filling dialogue engine + 5 stub advisories (no chemicals approved) + browser simulator. All tests pass offline. No deployment config. SMS is queued but never dispatched.

**Scope of this plan:** Six parallel work-streams covering Content & Safety, SMS Delivery, Deployment & Security, Accuracy & Testing, Dialogue Intelligence, and Operations & Analytics. Each sub-task is independently actionable by a single developer session.

**Approach:** Minimal, targeted changes. No architectural rewrites. Extend what works; fill what is missing.

---

## Sub-Task 1 — Agronomist Content & Chemical Review Workflow

**Status:** `[ ] pending`

### Intent
All 5 advisories in `app/kb.json` have `chemical.reviewed: false` and all 7 `CHEM_FIELDS` null. The bot will never speak a pesticide name until an agronomist fills and approves each record. This sub-task creates the tooling for non-engineer agronomists to safely edit, review, and publish chemical advice.

### Expected Outcomes
- A CLI helper script (`scripts/review_kb.py`) that validates all required chemical fields and prints a per-advisory status table before allowing any field to be set.
- A KB schema document (`docs/kb_schema.md`) that defines every field with allowed values, units, and example entries — so agronomists know exactly what to fill.
- At least 2 advisories fully populated with reviewed chemical data (chosen by agronomist).
- All existing tests still pass; new test: `test_reviewed_advisory_speaks_chemical_when_all_fields_set`.

### Todo List
- [ ] Create `docs/kb_schema.md` documenting every advisory field, CHEM_FIELDS contract, `needs_stage`, `block_chemical_stages`, and example entries for each crop.
- [ ] Write `scripts/review_kb.py`: reads `app/kb.json`, prints a table of advisory IDs, missing fields, and `reviewed` status; outputs a summary to stdout.
- [ ] Expand KB with additional advisories for missing common Karnataka crops: banana (ಬಾಳೆ), ragi (ರಾಗಿ), maize (ಮೆಕ್ಕೆಜೋಳ) — stub entries only (no chemical data yet).
- [ ] Add more stage variants per advisory where agronomically meaningful (e.g., `paddy_blast` by tillering vs. heading stage).
- [ ] Add a `version` and `last_updated` field to `kb.json` root for audit traceability.
- [ ] Write test `test_reviewed_advisory_speaks_chemical_when_all_fields_set` in `tests/test_dialogue.py`.

### Relevant Context
- `app/kb.json` — all advisory records; CHEM_FIELDS = `["product", "dose", "water", "preharvest_days", "source", "reviewed_by", "review_date"]`
- `app/dialogue.py:81-87` — `chemical_allowed()` is the gate; checks `reviewed is True` and all 7 fields non-null and non-empty
- `app/dialogue.py:163-182` — `_advise()` builds the spoken chemical sentence
- `tests/test_dialogue.py:57-65` — `test_chemical_requires_every_field_and_reviewed_flag` is the reference test

---

## Sub-Task 2 — SMS Gateway Integration

**Status:** `[ ] pending`

### Intent
`app/calllog.queue_sms()` writes to `logs/sms_outbox.jsonl` with `status: "queued_not_sent"` — no message is ever delivered to the farmer. Farmers need the follow-up SMS advice summary (crop, problem, bullet advice) so they can act after the call. This sub-task wires the queue to a real SMS gateway.

### Expected Outcomes
- `app/sms.py` module with a `dispatch_queued()` function that reads `sms_outbox.jsonl`, sends pending entries via a configurable gateway, and updates status to `"sent"` or `"failed"`.
- Gateway chosen from: Twilio (global), MSG91 (India), or Kaleyra (India TRAI-compliant). Gateway is configured via env vars and abstracted behind a single `send_sms(to, text)` interface so the gateway can be swapped.
- `queue_sms()` in `app/calllog.py` unchanged — the queue contract is preserved.
- A background task in `app/server.py` (or a standalone `scripts/sms_worker.py`) that flushes the queue after each call.
- New env vars: `SMS_GATEWAY`, `SMS_API_KEY`, `SMS_SENDER_ID`.
- New test: `test_sms_dispatch_marks_sent_on_success` and `test_sms_dispatch_marks_failed_on_gateway_error` using a mock gateway.

### Todo List
- [ ] Add `SMS_GATEWAY`, `SMS_API_KEY`, `SMS_SENDER_ID` to `app/config.py` and `.env.example`.
- [ ] Create `app/sms.py` with `send_sms(to: str, text: str) -> bool` and `dispatch_queued() -> dict` (returns counts of sent/failed).
- [ ] Implement Kaleyra HTTP adapter as the default (India DLT-compliant); stub Twilio adapter as alternate.
- [ ] In `app/server.py`, call `dispatch_queued()` asynchronously after each call ends (in `Call.run()` finally block).
- [ ] Add `scripts/sms_worker.py` as an optional standalone drain script (for ops who prefer offline batch dispatch).
- [ ] Write tests in `tests/test_sms.py` using `unittest.mock.patch` for the HTTP call; verify status update in jsonl.
- [ ] Update `requirements.txt` with `httpx` (already present) — no extra dependency needed for HTTP-based gateways.

### Relevant Context
- `app/calllog.py:16-17` — `queue_sms()` writes `{"call_id", "phone_tail", "text", "status": "queued_not_sent"}`
- `app/server.py:64-65` — SMS queued if `r.sms and self.phone and r.meta.get("safety") != "escalated"`
- Note: only last 4 digits of phone stored; full phone number passed as `?phone=` query param — need to store full number in sms_outbox for dispatch.

---

## Sub-Task 3 — Deployment & Security

**Status:** `[ ] pending`

### Intent
There is no `Dockerfile`, no TLS config, no rate limiting, and no auth on `/ws/call`. The WebSocket endpoint is open to anyone. This sub-task creates a production-deployable container stack and hardens the API surface.

### Expected Outcomes
- `Dockerfile` (multi-stage: build deps + minimal runtime image).
- `docker-compose.yml` with app + Caddy (auto-TLS) services; cache and logs as named volumes.
- `Caddyfile` for reverse-proxy with wss:// upgrade.
- Rate limiting on `/ws/call` (max N concurrent calls per IP, configurable).
- `GNANI_API_KEY` never logged or exposed in error messages.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) that runs `pytest -q` on push.
- Hardcoded STT/TTS URLs moved to `app/config.py` env vars (`STT_URL`, `TTS_URL`).

### Todo List
- [ ] Write `Dockerfile`: `python:3.12-slim` base, install `requirements.txt`, `COPY app/`, expose port 8000, `CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]`.
- [ ] Write `docker-compose.yml`: services `app` (build .) + `caddy` (caddy:2 image), volumes for `cache/tts` and `logs`, environment from `.env`.
- [ ] Write `Caddyfile`: reverse proxy `localhost:8000`, auto-TLS via Let's Encrypt, WebSocket upgrade headers.
- [ ] Add `slowapi` to `requirements.txt`; configure rate limiter in `app/server.py` (10 concurrent calls per IP, 429 on breach).
- [ ] Move hardcoded `stt_url` and `tts_url` from `app/config.py` to env vars with current values as defaults.
- [ ] Create `.github/workflows/ci.yml`: triggers on push/PR, checks out repo, installs deps, runs `pytest -q`.
- [ ] Add `.dockerignore`: exclude `cache/`, `logs/`, `.env`, `__pycache__`, `.venv`.
- [ ] Verify `GNANI_API_KEY` is never written to `logs/calls.jsonl` (audit `log_call` and all `log.exception` calls).

### Relevant Context
- `app/config.py:13-14` — `stt_url` and `tts_url` hardcoded as strings
- `app/server.py:139-141` — the WebSocket endpoint `@app.websocket("/ws/call")`, no auth
- `app/gnani.py:41-43` — STT WebSocket uses `self.c.stt_url`
- `requirements.txt` — currently 6 packages; `slowapi` is the only new addition needed

---

## Sub-Task 4 — Audio Test Dataset & Accuracy Evaluation

**Status:** `[ ] pending`

### Intent
`tests/audio/labels.csv` has only a header row — zero audio samples. `scripts/eval_audio.py` has never been run against real data. Without measured STT accuracy on real farmer speech, keyword gaps are invisible. This sub-task defines the recording protocol and populates the evaluation framework.

### Expected Outcomes
- `docs/recording_guide.md`: instructions for field audio collection (device, distance, noise level, format conversion with `ffmpeg`, accent tagging).
- `tests/audio/labels.csv` populated with at least 10 labeled clips (synthetically generated via TTS as a baseline proxy, clearly noted as synthetic).
- `scripts/eval_audio.py` verified to run end-to-end; output includes per-accent breakdown.
- A new `--dry-run` flag on `eval_audio.py` that validates WAV format and CSV row structure without calling Gnani API.
- Documented baseline accuracy (crop: X%, problem: Y%) in `docs/eval_baseline.md` after first run.

### Todo List
- [ ] Write `docs/recording_guide.md`: field recording protocol, ffmpeg conversion command, CSV labeling instructions, accent diversity targets (Udupi, Haveri, Dharwad, Mangaluru).
- [ ] Generate 10 synthetic baseline audio clips using `scripts/prewarm_cache.py` logic (TTS output of farmer-speech-like sentences per advisory) as a coverage proxy; populate `tests/audio/labels.csv`.
- [ ] Add `--dry-run` flag to `scripts/eval_audio.py` that validates WAV specs and CSV schema only.
- [ ] Add per-accent breakdown to `scripts/eval_audio.py` output (group rows by `note` field).
- [ ] Run eval against synthetic clips; record results in `docs/eval_baseline.md`.
- [ ] Add missing keyword variants to `app/dialogue.py` CROPS/PROBLEMS/STAGES based on STT transcripts from the eval run.

### Relevant Context
- `scripts/eval_audio.py` — full pipeline: load WAV, call `transcribe_pcm`, run `find_crop` + `find_problem`, compare to label
- `tests/audio/labels.csv` — schema: `file,crop,problem,note`
- `app/gnani.py:132-158` — `transcribe_pcm()` streams PCM at real-time cadence; requires `GNANI_API_KEY`
- `app/dialogue.py:7-25` — CROPS (20 kw), PROBLEMS (27 kw), STAGES (10 kw) — sparse keyword sets

---

## Sub-Task 5 — Dialogue Intelligence Improvements

**Status:** `[ ] pending`

### Intent
The current `_best()` algorithm uses exact substring matching weighted by keyword length. It fails silently on STT transcription variants, phonetic near-misses, and regional dialect synonyms. This sub-task improves robustness without requiring an LLM or internet model.

### Expected Outcomes
- Fuzzy/phonetic matching layer in `app/dialogue.py` that handles STT transcription variants (1-2 character substitutions, common Gnani Prisma artefacts).
- Expanded keyword tables with verified dialect synonyms for Udupi, Dharwad, and Haveri regions.
- A `confidence` field added to `Reply.meta` so callers can see match certainty.
- Existing 11 tests all still pass; new tests covering previously-failing transcript variants.
- ScriptProcessor replaced with AudioWorklet in `app/sim.html` for browser compatibility.

### Todo List
- [ ] Add a second-pass fuzzy check in `_best()`: if no exact match found, run `difflib.SequenceMatcher` against each keyword; accept if ratio >= 0.80. No new dependency — `difflib` is stdlib.
- [ ] Expand CROPS keyword table: add `["ಬಾಳೆ", "banana"]` for banana, `["ರಾಗಿ", "ragi", "finger millet"]` for ragi once those advisories are added; add regional variants like `"ಹಣ್ಣು"` (generic fruit → coconut context).
- [ ] Expand PROBLEMS keyword table: add `["ಬ್ಲಾಸ್ಟ್", "ಬ್ಲಾಸ್ಟ", "neck rot"]` for paddy blast; `["ದುಂಬಿ ಹಾವಳಿ", "ಗಣೇಶ ದುಂಬಿ"]` for rhino beetle.
- [ ] Expand STAGES keyword table: add `["ತಿಳಿ", "boot"]` for boot stage; `["ಮಾಗಿದ", "ಬಲಿಯ"]` for late grain stage.
- [ ] Add `confidence: float` to `Reply.meta` (0.0–1.0 based on _best() score normalized by max possible score for matched key).
- [ ] Rewrite `app/sim.html` mic capture to use AudioWorkletNode instead of deprecated ScriptProcessorNode; maintain same binary PCM frame format.
- [ ] Add CORS middleware in `app/server.py` (`fastapi.middleware.cors.CORSMiddleware`) with `allow_origins` configurable via env var.
- [ ] Write new tests for fuzzy matching variants (e.g., `"ಬೆಂಕಿ ರೋಗ"` → `"ಬೆಂಕ ರೋಗ"` with a typo still matches).

### Relevant Context
- `app/dialogue.py:52-60` — `_best()` scoring loop — exact substring only
- `app/dialogue.py:46-49` — `normalize()` — NFC, lowercase, punct strip; no phonetic normalization
- `app/sim.html:17` — `createScriptProcessor(4096, 1, 1)` — deprecated, works but will fail in future Chrome
- `app/server.py:11` — `FastAPI(title="Krishi Mitra")` — no CORS middleware configured

---

## Sub-Task 6 — Operations & Analytics

**Status:** `[ ] pending`

### Intent
Call logs are append-only flat files with no tooling to read them. There is no way to see advisory hit rates, escalation rates, silence timeout frequency, STT error rates, or TTS latency trends. This sub-task adds a lightweight analytics layer and structured logging without requiring external infrastructure.

### Expected Outcomes
- `scripts/analyze_calls.py` — CLI report from `logs/calls.jsonl`: total calls, outcome breakdown (advised/escalated/silence_timeout/hangup), top 3 advisories, avg STT latency, avg first-audio latency, calls per day.
- Structured JSON logging replacing the current `logging.basicConfig` in `app/server.py`.
- A `/metrics` endpoint returning plain-text Prometheus counters: total calls, active calls, TTS cache hit rate.
- New env var `LOG_LEVEL` controlling log verbosity.

### Todo List
- [ ] Write `scripts/analyze_calls.py`: reads `logs/calls.jsonl` line-by-line, computes and pretty-prints: call count, outcome distribution, advisory_id frequency, mean/P95 STT latency, mean first_audio_ms, calls per ISO date.
- [ ] Replace `logging.basicConfig` in `app/server.py` with structured JSON logging using `python-json-logger` (add to `requirements.txt`); each log record includes `call_id`, `turn`, `stt_latency_ms`.
- [ ] Add `prometheus-client` to `requirements.txt`; create `app/metrics.py` with counters: `calls_total`, `calls_active`, `tts_cache_hits_total`, `tts_cache_misses_total`, `stt_errors_total`.
- [ ] Wire metrics increments into `app/server.py` (call start/end) and `app/gnani.py` (TTS cache hit/miss, STT error).
- [ ] Add `@app.get("/metrics")` endpoint in `app/server.py` that returns Prometheus text format.
- [ ] Add `LOG_LEVEL` env var to `app/config.py` and `.env.example`; default `"INFO"`.
- [ ] Write test `test_metrics_endpoint_returns_prometheus_text` using `httpx.AsyncClient`.

### Relevant Context
- `app/calllog.py:12-13` — `log_call` writes `{"call_id", "ts", "outcome", "turns"}` per call
- `app/server.py:9-10` — `logging.basicConfig(level=logging.INFO)` — unstructured
- `app/gnani.py:107-119` — `stream_cached()` — TTS cache hit/miss paths exist but untracked
- `app/server.py:17-19` — `/health` endpoint exists; `/metrics` is the natural companion

---

## Dependency Summary

All new Python packages required across all sub-tasks:

| Package | Version | Sub-task | Purpose |
|---|---|---|---|
| `slowapi` | `>=0.1` | Sub-task 3 | Rate limiting |
| `prometheus-client` | `>=0.20` | Sub-task 6 | `/metrics` endpoint |
| `python-json-logger` | `>=2.0` | Sub-task 6 | Structured JSON logging |

SMS gateway (`twilio` or `requests` to MSG91/Kaleyra HTTP API) handled via `httpx` which is already in `requirements.txt`.

No LLM, vector DB, or cloud ML dependency is required for any sub-task.

---

## Implementation Order

Sub-tasks are designed to be independent but the recommended order is:

1. **Sub-task 1** (Content) — unblocks real advisory value; safe to do first, no code change
2. **Sub-task 3** (Deployment) — required before any real traffic; CI unblocks others
3. **Sub-task 2** (SMS) — requires Sub-task 3 to deploy
4. **Sub-task 4** (Audio Testing) — requires GNANI_API_KEY; can run in parallel with Sub-task 5
5. **Sub-task 5** (Dialogue) — improves accuracy; ideally informed by Sub-task 4 eval results
6. **Sub-task 6** (Operations) — layered on top; best done after live traffic exists

---

## Open Questions for Agronomist / Domain Expert

Before Sub-task 1 can be completed:
1. Which SMS gateway is preferred given India DLT registration requirements? (Kaleyra, MSG91, Twilio Local?)
2. Which agronomist will sign off on chemical data? What institution affiliation should go in `reviewed_by`?
3. Should the preharvest interval (`preharvest_days`) be a number word in Kannada or a numeral? (Current test `test_all_prompts_have_no_ascii_digits_for_tts` forbids ASCII digits in TTS text.)
4. What is the target deployment environment — cloud VM, on-premise server, or IVR integration via SIP?
5. Are there Karnataka state government advisory bulletins that can be used as the source for chemical recommendations (for `source` field)?
