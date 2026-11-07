"""Diagnostic controlled comparison of Gnani STT WebSocket sample-rate handling.
Case A: Original 8000 Hz PCM, declared as 8000 Hz, paced at actual rate.
Case B: Genuinely resampled 16000 Hz PCM, declared as 16000 Hz, paced at actual rate.
"""
import asyncio
import json
import pathlib
import subprocess
import tempfile
import wave
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed
from app.config import cfg

ORIGINAL_WAV = pathlib.Path("tests/audio/real/hubli/hd_01.wav")


def print_safe_event(ev: dict, prefix: str = "Event"):
    safe = []
    for k in ("type", "message", "request_id", "config", "text"):
        if k in ev:
            safe.append(f"{k}={json.dumps(ev[k], ensure_ascii=False)}")
    print(f"  [{prefix}] {', '.join(safe)}")


async def run_case(case_label: str, wav_path: pathlib.Path, declared_sample_rate: int):
    print(f"\n======================================================================")
    print(f"CASE {case_label}: {wav_path.name} (Declared: {declared_sample_rate} Hz)")
    print(f"======================================================================")

    if not wav_path.exists():
        print(f"ERROR: File not found: {wav_path}")
        return

    with wave.open(str(wav_path), "rb") as w:
        actual_sample_rate = w.getframerate()
        channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        nframes = w.getnframes()
        audio_pcm = w.readframes(nframes)
        audio_bytes = len(audio_pcm)
        duration = nframes / actual_sample_rate

    print(f"Actual WAV sample rate : {actual_sample_rate} Hz")
    print(f"Channels / Bit depth   : {channels} channel, {sampwidth * 8}-bit")
    print(f"Audio duration (actual): {duration:.3f} s (excluding trailing silence)")
    print(f"Audio byte count       : {audio_bytes} bytes")
    print(f"Declared sample rate   : {declared_sample_rate} Hz")

    headers = {
        "x-api-key-id": cfg.api_key,
        "model": "prisma-v3.0",
        "language_code": "kn-IN",
        "x-sample-rate": str(declared_sample_rate),
    }

    ws = None
    transcript_texts = []
    server_errors = []

    try:
        ws = await connect(cfg.stt_url, additional_headers=headers, max_size=None, open_timeout=10)
        init_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
        if isinstance(init_raw, (bytes, bytearray)):
            init_raw = init_raw.decode("utf-8", errors="replace")
        init_msg = json.loads(init_raw)

        config = init_msg.get("config", {})
        request_id = init_msg.get("request_id")
        reported_sample_rate = config.get("sample_rate")

        print(f"Connected request_id   : {request_id}")
        print(f"Connected config       : {json.dumps(config, ensure_ascii=False)}")
        print(f"Requested vs Reported  : requested={declared_sample_rate}, reported={reported_sample_rate} -> MATCH = {reported_sample_rate == declared_sample_rate}")

        if init_msg.get("type") == "error":
            server_errors.append(init_msg.get("message", "unknown error"))
            print(f"Server error on connect: {init_msg.get('message')}")
            await ws.close()
            return

        async def rx():
            try:
                async for raw in ws:
                    if isinstance(raw, (bytes, bytearray)):
                        continue
                    ev = json.loads(raw)
                    ev_type = ev.get("type")
                    if ev_type == "transcript" and ev.get("text"):
                        transcript_texts.append(ev.get("text"))
                    elif ev_type == "error":
                        server_errors.append(ev.get("message", "unknown error"))
            except ConnectionClosed:
                pass

        rx_task = asyncio.create_task(rx())

        # Frame pacing = len(frame) / (2 * actual_sample_rate)
        frame_size = 1024
        pacing_interval = frame_size / (2 * actual_sample_rate)
        silence_bytes = bytes(int(1.5 * actual_sample_rate * 2))
        full_payload = audio_pcm + silence_bytes

        print(f"Frame pacing interval  : {pacing_interval * 1000:.1f} ms per 1024 bytes")
        for i in range(0, len(full_payload), frame_size):
            if rx_task.done():
                break
            await ws.send(full_payload[i:i + frame_size].ljust(frame_size, b"\x00"))
            await asyncio.sleep(pacing_interval)

        end = asyncio.get_event_loop().time() + 8.0
        while asyncio.get_event_loop().time() < end:
            if transcript_texts or rx_task.done():
                break
            await asyncio.sleep(0.25)

        rx_task.cancel()
        try:
            await rx_task
        except asyncio.CancelledError:
            pass

        await ws.close()

    except Exception as e:
        server_errors.append(f"{type(e).__name__}: {e}")
        if ws:
            await ws.close()

    final_transcript = " ".join(transcript_texts).strip()
    print(f"Transcript received    : {json.dumps(final_transcript, ensure_ascii=False) if final_transcript else 'NONE'}")
    print(f"Safe server errors     : {server_errors if server_errors else 'NONE'}")


async def main():
    if not ORIGINAL_WAV.exists():
        print(f"Original WAV missing: {ORIGINAL_WAV}")
        return

    # Case A: Original 8000 Hz WAV declared as 8000 Hz
    await run_case("A (Original 8 kHz)", ORIGINAL_WAV, declared_sample_rate=8000)

    # Case B: Genuinely resampled 16000 Hz copy in a temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        resampled_wav = pathlib.Path(tmp_dir) / "hd_01_16k.wav"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(ORIGINAL_WAV),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            str(resampled_wav),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            print(f"FFmpeg resampling failed: {res.stderr}")
            return

        await run_case("B (Resampled 16 kHz)", resampled_wav, declared_sample_rate=16000)


if __name__ == "__main__":
    asyncio.run(main())
