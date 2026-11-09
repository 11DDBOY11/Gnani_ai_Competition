"""Synthesize narration with authentic Indian English female voice (gTTS en-co.in) and assemble 120.0s soundtrack."""
import os, subprocess
from gtts import gTTS

AUDIO_DIR = "submission/audio_indian"
os.makedirs(AUDIO_DIR, exist_ok=True)

SCRIPTS = [
    ("1", 18.0, 
     "When a crop develops a problem, a farmer needs guidance they can understand immediately. But typing long questions, navigating complicated screens, or searching through English-only portals makes digital tools difficult to use. For Karnataka farmers, speaking in Kannada is far simpler."),
    
    ("2", 16.0, 
     "Meet Krishi Mitra, a Kannada-first agricultural voice companion built for the Gnani AI Great Indian AI Internship Challenge. The goal is simple: let farmers speak naturally, receive clear guidance, and listen to the answer in their preferred language."),
    
    ("3", 24.0, 
     "Here is the actual application. A farmer opens the app, selects Kannada or English, and taps the microphone. Gnani AI converts phone-quality speech into text in real time. The transcript stays visible, so the farmer can check or edit it before submitting the question."),
    
    ("4a", 7.0, 
     "Groq generates general guidance, and Gnani AI reads it aloud. Listen to this actual Kannada example."),
    
    ("5", 18.0, 
     "Building this voice pipeline revealed crucial engineering lessons. We solved halfway audio cutoffs with an explicit client-server playback acknowledgement protocol. We overhauled the dialogue engine so crop state is systematically retained across conversational turns, and we built an accessible web experience alongside the simulator."),
    
    ("6", 16.0, 
     "Krishi Mitra is designed with agricultural safety first. Unreviewed chemical dosages are suppressed, and serious problems refer farmers to the government Kisan Call Centre at 1800-180-1551. Our browser demo is fully operational, while telephone integration remains in progress."),
    
    ("7", 12.0, 
     "Krishi Mitra brings together voice input, agricultural intelligence, and spoken answers. Built with pride for the Gnani AI Great Indian AI Internship Challenge. Thank you.")
]

def synth_gtts(text, out_mp3):
    tts = gTTS(text=text, lang="en", tld="co.in", slow=False)
    tts.save(out_mp3)

def pad_to_exact(in_file, out_wav, target_seconds):
    # Use ffmpeg to convert to 44.1kHz stereo WAV and pad or trim to exact duration
    cmd = [
        "ffmpeg", "-y", "-i", in_file,
        "-af", f"apad=whole_dur={target_seconds}",
        "-t", str(target_seconds),
        "-ar", "44100",
        "-ac", "2",
        out_wav
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    print("Synthesizing Indian female narration clips via gTTS (co.in)...")
    for seg_id, dur, text in SCRIPTS:
        raw_mp3 = os.path.join(AUDIO_DIR, f"raw_{seg_id}.mp3")
        padded_wav = os.path.join(AUDIO_DIR, f"padded_{seg_id}.wav")
        synth_gtts(text, raw_mp3)
        pad_to_exact(raw_mp3, padded_wav, dur)
        print(f"Segment {seg_id} ({dur}s) prepared.")

    # 4b is the 6.99s real Gnani Kannada spoken answer
    pad_to_exact("submission/kannada_excerpt.wav", os.path.join(AUDIO_DIR, "padded_4b.wav"), 7.0)

    # 4c is 2.0s transition silence
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", "2.0", os.path.join(AUDIO_DIR, "padded_4c.wav")
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Segment 4 clips aligned (7s intro + 7s Gnani Kannada + 2s pause = 16s).")

    # Concatenate in order to create master 120.0s soundtrack
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

    master_audio = "submission/master_soundtrack_indian_female_120s.wav"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-t", "120.0",
        "-ar", "44100",
        "-ac", "2",
        master_audio
    ]
    subprocess.run(cmd_concat, check=True)
    print(f"Master Indian female soundtrack generated: {master_audio}")

