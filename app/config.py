import os, pathlib
try:
    from dotenv import load_dotenv
    _root = pathlib.Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
    load_dotenv()
except ImportError:
    pass


class Config:
    def __init__(self):
        e = os.environ.get
        k = e("GNANI_API_KEY", "").strip()
        if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
            k = k[1:-1].strip()
        if k.lower().startswith("bearer "):
            k = k[7:].strip()
        self.api_key = k
        self.stt_url = "wss://api.vachana.ai/stt/v3/stream"
        self.tts_url = "wss://api.vachana.ai/api/v1/tts"
        self.stt_language = e("STT_LANGUAGE", "kn-IN")
        self.tts_model = e("TTS_MODEL", "timbre-v3.0")
        self.tts_voice = e("TTS_VOICE", "Lakshmi")
        self.tts_speed = float(e("TTS_SPEED", "0.95"))
        self.sample_rate = int(e("SAMPLE_RATE", "8000"))
        self.vad_threshold = float(e("VAD_THRESHOLD", "0.7"))
        self.min_speech_ms = int(e("MIN_SPEECH_MS", "200"))
        self.min_silence_ms = int(e("MIN_SILENCE_MS", "600"))
        self.silence_timeout_s = float(e("SILENCE_TIMEOUT_S", "15"))
        self.keyterms_max = int(e("KEYTERMS_MAX", "40"))
        self.escalation_number = e("ESCALATION_NUMBER", "1800-180-1551")
        self.cache_dir = e("CACHE_DIR", "cache/tts")
        self.log_dir = e("LOG_DIR", "logs")
        self.call_token = e("CALL_TOKEN", "")
        self.max_calls = int(e("MAX_CALLS", "3"))


cfg = Config()
