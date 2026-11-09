"""Compose final slides by applying HarfBuzz text overlays onto base slides."""
import subprocess

FONT_PATH = "C\\:/Windows/Fonts/Nirmala.ttc"

def run_ffmpeg(filters, in_img, out_img):
    filter_complex = ",".join(filters)
    cmd = [
        "ffmpeg", "-y",
        "-i", in_img,
        "-vf", filter_complex,
        out_img
    ]
    subprocess.run(cmd, check=True)
    print(f"Generated {out_img}")

# Header text filter macro
def header_logo_filter():
    return f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/header_logo.txt':fontcolor=white:fontsize=38:x=1580:y=32"

# 1. Slide 1
filters_1 = [
    header_logo_filter(),
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s1_header.txt':fontcolor='#2e7d32':fontsize=36:x=680:y=152",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s1_hero.txt':fontcolor='#d8f3dc':fontsize=28:x=120:y=410"
]
run_ffmpeg(filters_1, "submission/base_slides/base_1.png", "submission/corrected_slides/slide_1.png")

# 2. Slide 2
filters_2 = [
    header_logo_filter(),
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s2_header.txt':fontcolor='#2e7d32':fontsize=36:x=890:y=152",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s2_crops.txt':fontcolor='#55695f':fontsize=22:x=1000:y=560"
]
run_ffmpeg(filters_2, "submission/base_slides/base_2.png", "submission/corrected_slides/slide_2.png")

# 3. Slide 3
filters_3 = [
    header_logo_filter(),
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_header.txt':fontcolor='#2e7d32':fontsize=36:x=850:y=152",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_lang_kn.txt':fontcolor=white:fontsize=18:x=145:y=282",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_prompt_lbl.txt':fontcolor='#14231c':fontsize=26:x=110:y=350",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_q_box.txt':fontcolor='#14231c':fontsize=32:x=140:y=440",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_rec_status.txt':fontcolor='#b42828':fontsize=24:x=220:y=640",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_submit_kn.txt':fontcolor=white:fontsize=22:x=820:y=650",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_ex_title.txt':fontcolor='#55695f':fontsize=20:x=110:y=750",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_ex1.txt':fontcolor='#2e7d32':fontsize=20:x=130:y=798",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_ex2.txt':fontcolor='#2e7d32':fontsize=20:x=130:y=850",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s3_ex3.txt':fontcolor='#2e7d32':fontsize=20:x=130:y=902"
]
run_ffmpeg(filters_3, "submission/base_slides/base_3.png", "submission/corrected_slides/slide_3.png")

# 4. Slide 4
filters_4 = [
    header_logo_filter(),
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s4_header.txt':fontcolor='#2e7d32':fontsize=36:x=860:y=152",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s4_title.txt':fontcolor='#2e7d32':fontsize=20:x=160:y=435",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s4_resp1.txt':fontcolor='#14231c':fontsize=36:x=160:y=480",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s4_resp2.txt':fontcolor='#14231c':fontsize=36:x=160:y=535"
]
run_ffmpeg(filters_4, "submission/base_slides/base_4.png", "submission/corrected_slides/slide_4.png")

# 5. Slide 5
filters_5 = [
    header_logo_filter(),
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s5_header.txt':fontcolor='#2e7d32':fontsize=36:x=990:y=152"
]
run_ffmpeg(filters_5, "submission/base_slides/base_5.png", "submission/corrected_slides/slide_5.png")

# 6. Slide 6
filters_6 = [
    header_logo_filter(),
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s6_header.txt':fontcolor='#2e7d32':fontsize=36:x=970:y=152"
]
run_ffmpeg(filters_6, "submission/base_slides/base_6.png", "submission/corrected_slides/slide_6.png")

# 7. Slide 7
filters_7 = [
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s7_hero.txt':fontcolor=white:fontsize=90:x=(w-text_w)/2:y=180",
    f"drawtext=fontfile='{FONT_PATH}':textfile='submission/text_files/s7_thanks.txt':fontcolor='#d8f3dc':fontsize=28:x=800:y=950"
]
run_ffmpeg(filters_7, "submission/base_slides/base_7.png", "submission/corrected_slides/slide_7.png")

print("All corrected slides successfully generated with HarfBuzz complex text shaping!")

