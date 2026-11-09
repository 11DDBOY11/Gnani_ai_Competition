# Krishi Mitra

Krishi Mitra is a Kannada voice advisory assistant for farmers in Karnataka, built for the **Gnani AI Great Indian AI Internship Challenge**. It helps farmers describe crop problems in Kannada and receive practical, crop-specific guidance through a conversational voice interface.

The current advisory scope is deliberately limited to three crops:

| Crop | Kannada |
| --- | --- |
| Paddy | ಭತ್ತ |
| Arecanut | ಅಡಿಕೆ |
| Coconut | ತೆಂಗು |

## Live demo

**[Open the hosted Krishi Mitra demo](https://krishi-mitra-gn3h.onrender.com/)**

The browser simulator is the recommended way to evaluate the project. It supports Kannada speech through the browser microphone, Gnani AI speech-to-text (STT), crop and problem recognition, advisory lookup, Kannada text-to-speech (TTS), and a turn-based conversation. Unsupported crops receive a referral to the Kisan Call Centre at **1800-180-1551**.

## How it works

1. The browser captures the farmer's speech and sends 8 kHz audio to the backend over WebSocket.
2. The backend streams the audio to Gnani AI STT for Kannada transcription.
3. The dialogue manager identifies the crop and problem, then looks up a response in the controlled advisory data.
4. Gnani AI TTS synthesizes the Kannada response.
5. The browser plays the response and acknowledges completion before accepting the next turn.

```text
Farmer microphone
       |
       v
Browser simulator
       |
       v
FastAPI WebSocket backend on Render
       |
       +----> Gnani AI STT
       |
       +----> Dialogue manager and advisory data
       |
       +----> Gnani AI TTS
       |
       v
Browser audio playback
```

## Technical architecture

- **Backend:** Python and FastAPI, including WebSocket endpoints.
- **Speech:** Gnani AI STT and TTS; Kannada (`kn-IN`) and 8 kHz PCM are the configured defaults.
- **Dialogue and recognition:** Rule-based crop and problem matching with conversational state.
- **Advisory data:** Local JSON knowledge base and disease registry; no vector database is used.
- **Hosting:** Render web service, described by `render.yaml`.
- **Browser client:** `app/sim.html`, served at `/sim`; `/` serves the landing page.

## Key engineering work

- The dialogue flow is Kannada-first and filters crop-specific matching to the supported crops: paddy, arecanut, and coconut. Unsupported crops are handled with a referral rather than being given a mismatched crop advisory.
- The unsupported-crop flow can send a referral SMS directing the farmer to Kisan Call Centre **1800-180-1551**.
- Recognition handles selected Kannada word forms and morphology, including paddy leaf-folder phrases such as "ಮಡಚಿಕೊಂಡಿದೆ". Coverage is limited and should not be interpreted as support for every regional phrase.
- For browser calls, the server synthesizes a complete response, joins its PCM audio into one buffer, and sends one audio payload. The browser uses one `AudioBufferSourceNode` per response, stops the previous source before starting a new one, and sends `playback_done` when playback ends.
- Microphone intake is suppressed during playback to reduce echo and overlapping turns.
- STT disconnect diagnostics include `failure_source`, `error_type`, `error_message`, `audio_sent_before_failure`, `browser_websocket_closed`, `client_session_id`, and `response_id`.

### Telephony integration status

An Exotel call flow was configured, and the greeting playback path was demonstrated. The complete end-to-end telephone conversation was **not stabilized before the submission deadline**. The main issue observed was that after the initial greeting, when the caller began describing a problem, the call or WebSocket session disconnected.

The team investigated likely causes, including WebSocket keepalive and timeout behavior, protocol mismatch between Exotel media events and the browser-oriented WebSocket handler, event-loop blocking during synthesis, and audio streaming synchronization. An Exotel adapter is present in the project, but the full telephone conversation was not proven reliable.

Exotel production activation also requires telecom KYC verification. As an individual/student developer without a registered business, full production KYC could not be completed within the competition window. The submitted demonstration therefore uses the browser voice simulator on Render; Exotel remains a configured future production interface. **Exotel is not claimed to be fully working or production-ready.**

### Challenges and engineering decisions

1. **Audio sentence interleaving:** Earlier versions synthesized and streamed response sentences independently. Cached or faster sentences could arrive out of order and overlap audio from previous turns. The server was changed to synthesize the full response first, concatenate its PCM audio, and send one payload per turn.
2. **Cross-turn audio leakage:** Browser audio sources from earlier responses were not always stopped before a new response began. The browser now stops and disconnects active `AudioBufferSourceNode`s before starting the next response.
3. **STT disconnects:** The system observed WebSocket disconnects with code 1011 and keepalive ping timeouts. Diagnostics were added to help distinguish browser-side closure, upstream STT failure, and whether audio had been sent.
4. **Exotel integration:** The greeting path worked, but the full caller-to-advisory loop disconnected after the greeting. Likely contributors included Exotel's JSON media event protocol, WebSocket keepalive behavior, and the browser-oriented handler expecting a different audio format. The browser demo was prioritized over presenting an unstable telephone demo.
5. **KYC constraint:** Full Exotel production activation requires KYC verification. The required business KYC could not be completed by the individual developer during the competition period, so the hosted browser simulator is the primary demonstration.

## Run locally

These commands use Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.server:app --reload --port 8000
```

Configure the required API credentials through environment variables or a local `.env` file. See `.env.example` for the variable names; do not commit real credentials. Then open:

- Landing page: <http://localhost:8000/>
- Browser simulator: <http://localhost:8000/sim>

## Repository structure

```text
app/
  server.py       FastAPI routes, WebSocket call orchestration, and Exotel adapter
  dialogue.py     Dialogue state, crop/problem recognition, and response selection
  diseases.py     Disease registry, aliases, and matching
  kb.json         Crop-specific advisory knowledge
  gnani.py        Gnani AI STT and TTS clients
  config.py       Environment-based configuration
  calllog.py      Call logging and SMS queue support
  sim.html        Browser voice simulator
output/
  krishi-mitra-landing.html  Hosted landing page
tests/            Automated unit and integration tests
scripts/          Local smoke checks, audio preparation, and evaluation utilities
render.yaml       Render deployment configuration
requirements.txt  Python dependencies
.env.example     Example environment variable names
```

## Testing

The repository includes automated tests for crop recognition and filtering, unsupported-crop handling, dialogue state transitions, advisory retrieval, atomic audio delivery, playback acknowledgement, and the Exotel protocol adapter. Run them locally with:

```powershell
pytest -q
```

No passing test count is stated here; results depend on the current checkout and environment.

## Future work

- Stabilize and validate Exotel Voicebot protocol handling for JSON media events and base64 PCM.
- Improve WebSocket keepalive and connection recovery for telephony.
- Expand crop and disease coverage only after validation with agricultural experts.
- Improve Kannada speech recognition for regional accents and noisy farm environments.
- Add farmer feedback capture and advisory-quality tracking.
- Add language support beyond Kannada.

## Competition submission

Krishi Mitra was built for the **Gnani AI Great Indian AI Internship Challenge**.

A public social post should include a short project description, the [live demo](https://krishi-mitra-gn3h.onrender.com/), the tags **#GreatIndianAIInternshipChallenge #GnaniAI**, and a mention/tag of Gnani AI where platform rules allow.
