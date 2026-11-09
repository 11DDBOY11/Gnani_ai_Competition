"""Compose base slides with HarfBuzz-rendered Kannada text overlays using FFmpeg libharfbuzz."""
import os, subprocess

os.makedirs("submission/text_files", exist_ok=True)
os.makedirs("submission/corrected_slides", exist_ok=True)

# Define text snippets for each slide
SLIDE_TEXTS = {
    # Header logo text (used across slides 1-6)
    "header_logo": "ಕೃಷಿ ಮಿತ್ರ",
    
    # Slide 1
    "s1_header": "(ಸಮಸ್ಯೆ ಮತ್ತು ಅವಕಾಶ)",
    "s1_hero": "ಕೃಷಿ ಸಮಸ್ಯೆಗಳಿಗೆ ಪರಿಹಾರ ಪಡೆಯಲು ತಾಂತ್ರಿಕ ತಡೆಗೋಡೆಗಳಿರಬಾರದು.",
    
    # Slide 2
    "s2_header": "(ವ್ಯವಸ್ಥೆಯ ವಿನ್ಯಾಸ)",
    "s2_crops": "• 3 Supported Crops: Paddy (ಭತ್ತ), Arecanut (ಅಡಿಕೆ), Coconut (ತೆಂಗು)",
    
    # Slide 3
    "s3_header": "(ಪ್ರಶ್ನೆ ಕೇಳುವ ವಿಧಾನ)",
    "s3_lang_kn": "ಕನ್ನಡ (KN)",
    "s3_prompt_lbl": "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಇಲ್ಲಿ ಹೇಳಿ ಅಥವಾ ಬರೆಯಿರಿ:",
    "s3_q_box": "ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತುವ ಹುಳು ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?",
    "s3_rec_status": "ಧ್ವನಿ ರೆಕಾರ್ಡಿಂಗ್ ಚಾಲನೆಯಲ್ಲಿದೆ...",
    "s3_submit_kn": "ಕೇಳಿ (Submit)",
    "s3_ex_title": "ಉದಾಹರಣೆ ಪ್ರಶ್ನೆಗಳು",
    "s3_ex1": "ಅಡಿಕೆಯಲ್ಲಿ ಕೊಳೆ ರೋಗದ ಲಕ್ಷಣಗಳು",
    "s3_ex2": "ತೆಂಗಿನ ಮರದಲ್ಲಿ ದುಂಬಿ ಬಾಧೆ ನಿಯಂತ್ರಣ",
    "s3_ex3": "ಭತ್ತದಲ್ಲಿ ರಸಗೊಬ್ಬರ ನಿರ್ವಹಣೆ",
    
    # Slide 4
    "s4_header": "(ಧ್ವನಿ ರೂಪದ ಉತ್ತರ)",
    "s4_title": "ಕೃಷಿ ಮಿತ್ರ ನೀಡಿದ ಧ್ವನಿ ಉತ್ತರ (Spoken Kannada Text):",
    "s4_resp1": "ಕೃಷಿ ಮಿತ್ರ: ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತುವ ಹುಳು ಕಂಡುಬಂದರೆ,",
    "s4_resp2": "ಮುನ್ನೆಚ್ಚರಿಕೆ ಕ್ರಮಗಳನ್ನು ಕೈಗೊಳ್ಳಿ.",
    
    # Slide 5
    "s5_header": "(ತಾಂತ್ರಿಕ ಸವಾಲುಗಳು ಮತ್ತು ಪರಿಹಾರ)",
    
    # Slide 6
    "s6_header": "(ಜವಾಬ್ದಾರಿಯುತ ಸಲಹೆ ಮತ್ತು ಮಿತಿಗಳು)",
    
    # Slide 7
    "s7_hero": "ಕೃಷಿ ಮಿತ್ರ",
    "s7_thanks": "ಧನ್ಯವಾದಗಳು"
}

# Write text files with UTF-8 encoding
for key, text in SLIDE_TEXTS.items():
    p = os.path.join("submission/text_files", f"{key}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)

print("Text files written successfully.")

