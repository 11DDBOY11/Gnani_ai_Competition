"""Synthesize and align master audio track to exactly 120.000 seconds (02:00)."""
import os, wave, win32com.client, subprocess

AUDIO_DIR = "submission/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Segment text with exact target durations (total = 120.0s)
# (segment_index, duration_seconds, speech_rate, text)
SCRIPTS = [
    (1, 18.0, 1, 
     "When a crop develops a problem, a farmer needs guidance they can understand immediately. But typing long questions, navigating complicated screens, or searching through English-only portals makes digital tools difficult to use. For Karnataka farmers, speaking in Kannada is far simpler."),
    
    (2, 16.0, 1, 
     "Meet Krishi Mitra, a Kannada-first agricultural voice companion built for the Gnani AI Great Indian AI Internship Challenge. The goal is simple: let farmers speak naturally, receive clear guidance, and listen to the answer in their preferred language."),
    
    (3, 24.0, 1, 
     "Here is the actual application. A farmer opens the app, selects Kannada or English, and taps the microphone. Gnani AI converts phone-quality speech into text in real time. The transcript stays visible, so the farmer can check or edit it before submitting the question."),
    
    # 4a: Narrator intro (target 7.0s, starting at 00:58, ending at 01:05)
    ("4a", 7.0, 1, 
     "Groq generates general guidance, and Gnani AI reads it aloud. Listen to this actual Kannada example."),
    
    (5, 18.0, 2, 
     "Building this voice pipeline revealed crucial engineering lessons. We solved halfway audio cutoffs with an explicit client-server playback acknowledgement protocol. We overhauled the dialogue engine so crop state is systematically retained across conversational turns, and we built an accessible web experience alongside the simulator."),
    
    (6, 16.0, 2, 
     "Krishi Mitra is designed with agricultural safety first. Unreviewed chemical dosages are suppressed, and serious problems refer farmers to the government Kisan Call Centre at 1800-180-1551. Our browser demo is fully operational, while telephone integration remains in progress."),
    
    (7, 12.0, 1, 
     "Krishi Mitra brings together voice input, agricultural intelligence, and spoken answers. Built with pride for the Gnani AI Great Indian AI Internship Challenge. Thank you.")
]

def synth_wav(text, out_path, rate=1):
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    for v in speaker.GetVoices():
        if "David" in v.GetDescription() or "Zira" in v.GetDescription():
            speaker.Voice = v
            break
    speaker.Rate = rate
    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    stream.Open(out_path, 3, False)
    speaker.AudioOutputStream = stream
    speaker.Speak(text)
    stream.Close()

def pad_or_trim(in_wav, out_wav, target_seconds, sample_rate=44100):
    # Use ffmpeg to resample, pad with silence to target_seconds
    cmd = [
        "ffmpeg", "-y", "-i", in_wav,
        "-af", f"apad=whole_dur={target_seconds}",
        "-t", str(target_seconds),
        "-ar", str(sample_rate),
        "-ac", "2",
        out_wav
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    print("1. Synthesizing narration clips...")
    for seg_id, dur, rate, text in SCRIPTS:
        raw_wav = os.path.join(AUDIO_DIR, f"raw_{seg_id}.wav")
        padded_wav = os.path.join(AUDIO_DIR, f"padded_{seg_id}.wav")
        synth_wav(text, raw_wav, rate)
        pad_or_trim(raw_wav, padded_wav, dur)
        print(f"Segment {seg_id} prepared ({dur}s)")

    # Segment 4b is the 6.99s Kannada audio from Gnani AI
    # Pad it to exactly 7.0s
    pad_or_trim("submission/kannada_excerpt.wav", os.path.join(AUDIO_DIR, "padded_4b.wav"), 7.0)
    # Segment 4c is 2.0s silence buffer to complete the 16s of Scene 4 (7s + 7s + 2s = 16s)
    cmd_silence = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", "2.0",
        os.path.join(AUDIO_DIR, "padded_4c.wav")
    ]
    subprocess.run(cmd_silence, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Segment 4 subclips prepared (7s + 7s + 2s = 16s)")

    # Concatenate all padded segments in order:
    # 1 (18s) + 2 (16s) + 3 (24s) + 4a (7s) + 4b (7s) + 4c (2s) + 5 (18s) + 6 (16s) + 7 (12s) = 120s!
    concat_list = os.path.join(AUDIO_DIR, "concat_audio.txt")
    with open(concat_list, "w") as f:
        f.write("file 'padded_1.wav'\n")
        f.write("file 'padded_2.wav'\n")
        f.write("file 'padded_3.wav'\n")
        f.write("file 'padded_4a.wav'\n")
        f.write("file 'padded_4b.wav'\n")
        f.write("file 'padded_4c.wav'\n")
        f.write("file 'padded_5.wav'\n")
        f.write("file 'padded_6.wav'\n")
        f.write("file 'padded_7.wav'\n")

    master_audio = "submission/master_soundtrack_120s.wav"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-t", "120.0",
        "-ar", "44100",
        "-ac", "2",
        master_audio
    ]
    subprocess.run(cmd_concat, check=True)
    print(f"Master soundtrack generated: {master_audio}")

