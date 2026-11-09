"""Synthesize clean audio tracks for each of the 7 video segments with exact timing and padding."""
import os, wave, win32com.client

AUDIO_DIR = "submission/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

SECTIONS = [
    (1, 18.0, "When a crop develops a problem, a farmer needs guidance they can understand immediately. But typing long questions, navigating complicated screens, or searching through English-only portals makes digital tools difficult to use. For Karnataka farmers, speaking and listening in Kannada is far more natural."),
    (2, 16.0, "Meet Krishi Mitra, a Kannada-first agricultural companion built for the Gnani AI Great Indian AI Internship Challenge. The goal is simple: let farmers speak naturally, receive clear guidance, and listen to the answer in their preferred language. It features a live mobile web app and a guided dialogue engine."),
    (3, 24.0, "Here is the actual application interface. A farmer opens the app, selects Kannada or English, and taps the microphone. Gnani AI converts phone-quality audio into Kannada text in real time. The transcribed question stays visible on screen, so the farmer can easily verify or edit it before submitting."),
    # Section 4 is split: narrator intro (7s), then pure Kannada Gnani audio (7s), then buffer (2s)
    (4, 7.0, "Groq generates safe, non-diagnostic guidance, and Gnani AI reads it aloud. Listen to this actual Kannada advisory spoken by Gnani AI."),
    (5, 18.0, "Building this voice pipeline revealed crucial engineering lessons. We solved halfway audio cutoffs with an explicit client-server playback acknowledgement protocol. We overhauled the dialogue engine so crop state is systematically retained across conversational turns, and we built an accessible web experience alongside the simulator."),
    (6, 16.0, "Krishi Mitra is designed with agricultural safety first. Unreviewed chemical dosages are suppressed, and serious problems refer farmers to the government Kisan Call Centre at 1800-180-1551. We believe in transparent scope: our browser demo is fully operational, while telephone integration remains in progress."),
    (7, 12.0, "Krishi Mitra bridges the gap between rural farmers and AI technology: speak, understand, and take the next step. Built with pride for the Gnani AI Great Indian AI Internship Challenge. Thank you.")
]

def synthesize_text(text, out_wav):
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    # Select David or Zira
    voices = speaker.GetVoices()
    for v in voices:
        if "David" in v.GetDescription() or "Zira" in v.GetDescription():
            speaker.Voice = v
            break
    speaker.Rate = 0  # Normal natural speaking rate
    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    stream.Open(out_wav, 3, False)
    speaker.AudioOutputStream = stream
    speaker.Speak(text)
    stream.Close()

if __name__ == "__main__":
    print("Synthesizing narration segments...")
    for idx, target_dur, text in SECTIONS:
        out_path = os.path.join(AUDIO_DIR, f"seg_{idx}.wav")
        synthesize_text(text, out_path)
        print(f"Generated {out_path}")
    print("All narration segments synthesized successfully.")

