import asyncio
import os
import subprocess
import edge_tts

SAMPLE_TEXT = (
    "Meet Krishi Mitra, a Kannada-first agricultural assistant for Karnataka farmers. "
    "Speak your farming question, receive simple guidance, and listen to the answer in Kannada or English."
)

SAMPLE_DIR = "submission/voice_samples"
os.makedirs(SAMPLE_DIR, exist_ok=True)

VOICES = [
    ("en-IN-NeerjaNeural", "sample_en_IN_NeerjaNeural.mp3", "sample_en_IN_NeerjaNeural.wav"),
    ("en-IN-NeerjaExpressiveNeural", "sample_en_IN_NeerjaExpressiveNeural.mp3", "sample_en_IN_NeerjaExpressiveNeural.wav")
]

async def synthesize(voice_name, mp3_file, wav_file):
    mp3_path = os.path.join(SAMPLE_DIR, mp3_file)
    wav_path = os.path.join(SAMPLE_DIR, wav_file)
    
    print(f"Synthesizing with {voice_name}...")
    communicate = edge_tts.Communicate(SAMPLE_TEXT, voice_name, rate="+0%", pitch="+0Hz")
    await communicate.save(mp3_path)
    
    # Convert to WAV for easy inspection / lossless playback
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-ar", "44100", "-ac", "2",
        wav_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Inspect duration with ffprobe
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", wav_path
    ], capture_output=True, text=True, check=True)
    
    duration = float(result.stdout.strip())
    print(f"Done: {voice_name} -> {wav_path} (Duration: {duration:.2f}s)")

async def main():
    for voice_name, mp3_file, wav_file in VOICES:
        await synthesize(voice_name, mp3_file, wav_file)

if __name__ == "__main__":
    asyncio.run(main())

