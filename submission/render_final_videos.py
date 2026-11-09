"""Render both clean and subtitled demonstration videos with authentic Indian female voice and refined compact subtitles."""
import subprocess

print("1. Rendering clean 1080p MP4 with Indian female voice...")
cmd_clean = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0", "-i", "submission/concat_slides.txt",
    "-i", "submission/master_soundtrack_indian_female_120s.wav",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
    "-c:a", "aac", "-b:a", "192k",
    "-t", "120.0",
    "-movflags", "+faststart",
    "submission/krishi_mitra_demo_2min.mp4"
]
subprocess.run(cmd_clean, check=True)
print("Clean video rendered successfully: submission/krishi_mitra_demo_2min.mp4")

print("2. Rendering subtitled 1080p MP4 with refined small font, repositioned 1 cm lower...")
# FontSize=12, BorderStyle=1 (subtle outline, no giant black box), MarginV=12 (1 cm lower than before)
sub_style = (
    "FontSize=12,"
    "PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00102518,"
    "Outline=1.2,"
    "Shadow=0.8,"
    "BorderStyle=1,"
    "MarginV=12,"
    "Alignment=2"
)

cmd_sub = [
    "ffmpeg", "-y",
    "-i", "submission/krishi_mitra_demo_2min.mp4",
    "-vf", f"subtitles=submission/krishi_mitra_subtitles.srt:force_style='{sub_style}'",
    "-c:a", "copy",
    "-movflags", "+faststart",
    "submission/krishi_mitra_demo_2min_subtitled.mp4"
]
subprocess.run(cmd_sub, check=True)
print("Subtitled video rendered successfully: submission/krishi_mitra_demo_2min_subtitled.mp4")

