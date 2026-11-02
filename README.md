# Krishi Mitra - Kannada voice advisory (Gnani Prisma v3.0 + Timbre)

## Run
    python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env        # then paste GNANI_API_KEY
    pytest -q                   # offline tests, no credits used
    python -m scripts.smoke     # 1 TTS + 1 STT call
    python -m scripts.prewarm_cache
    uvicorn app.server:app --port 8000
    open http://localhost:8000  # phone simulator

Chemical advice is OFF until an agronomist fills a `chemical` block in app/kb.json and sets reviewed=true.
Have a native Kannada speaker proofread all Kannada text.
