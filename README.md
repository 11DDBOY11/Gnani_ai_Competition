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

## Exotel AgentStream

The phone simulator endpoint (`/ws/call`) uses browser PCM frames and is not the Exotel protocol. Exotel Voicebot/AgentStream connects to `/exotel/media`, which accepts Exotel JSON/base64 8 kHz PCM media, streams the farmer audio to the existing STT pipeline, sends synthesized audio back as Exotel `media` events, and waits for Exotel `mark` before accepting the next turn.

1. Deploy the `krishi-mitra` Render web service from `render.yaml` and set `GNANI_API_KEY` plus a long random `EXOTEL_STREAM_TOKEN` in the service environment. Keep the token private.
2. In the Exotel Voicebot applet (or Connect Voice AI request), set the stream URL to `wss://<your-render-host>/exotel/media?token=<EXOTEL_STREAM_TOKEN>` and select bidirectional streaming at 8 kHz.
3. For outbound calls, use Exotel's Connect Voice AI endpoint with `StreamType=bidirectional` and the same `StreamUrl`. For inbound calls, attach a Voicebot applet with that WebSocket URL to the ExoPhone flow.
4. Refresh the simulator page after deploying frontend changes. The simulator displays turns in chronological order; an already-open page keeps its older JavaScript until refreshed.

Exotel's protocol and its `media`/`mark` completion semantics are documented at [AgentStream WebSocket protocol](https://developer.exotel.com/docs/agentstream/websocket-protocol) and [Connect Voice AI](https://developer.exotel.com/docs/agentstream/connect-voice-ai).
