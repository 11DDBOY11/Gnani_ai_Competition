"""Generate 7 high-definition 1920x1080 slides for Krishi Mitra 2-minute demonstration video."""
import os
from PIL import Image, ImageDraw, ImageFont

SLIDE_DIR = "submission/slides"
os.makedirs(SLIDE_DIR, exist_ok=True)

W, H = 1920, 1080

# Color Palette
BG_DARK = (18, 48, 38)       # Deep forest green
BG_CARD = (255, 255, 255)    # Card white
BG_LIGHT = (244, 247, 245)   # Off-white / light pista
TEXT_DARK = (20, 35, 28)     # Near black / dark green
TEXT_MUTED = (85, 105, 95)   # Muted green-grey
ACCENT_GREEN = (46, 125, 50) # Vibrant agriculture green
ACCENT_LIGHT = (216, 243, 220) # Light pista green
ACCENT_GOLD = (230, 180, 34)  # Warm gold
BORDER_COLOR = (210, 225, 215)

# Fonts
FONT_NIRMALA_BOLD = r"C:\Windows\Fonts\Nirmala.ttc"
FONT_SEGOE = r"C:\Windows\Fonts\segoeui.ttf"
FONT_SEGOE_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_header(draw, title_en, title_kn=""):
    # Top banner bar
    draw.rectangle([(0, 0), (W, 110)], fill=BG_DARK)
    badge_font = get_font(FONT_SEGOE_BOLD, 22)
    draw.text((70, 25), "GNANI AI — GREAT INDIAN AI INTERNSHIP CHALLENGE", font=badge_font, fill=ACCENT_LIGHT)
    
    tag_font = get_font(FONT_SEGOE, 18)
    draw.text((70, 62), "Project Demonstration · 02:00 Edit", font=tag_font, fill=(180, 210, 195))

    logo_kn_font = get_font(FONT_NIRMALA_BOLD, 38)
    draw.text((1580, 32), "ಕೃಷಿ ಮಿತ್ರ", font=logo_kn_font, fill=(255, 255, 255))
    logo_en_font = get_font(FONT_SEGOE_BOLD, 22)
    draw.text((1740, 45), "Krishi Mitra", font=logo_en_font, fill=ACCENT_LIGHT)

    # Title area
    t_font = get_font(FONT_SEGOE_BOLD, 44)
    draw.text((70, 145), title_en, font=t_font, fill=TEXT_DARK)
    if title_kn:
        k_font = get_font(FONT_NIRMALA_BOLD, 36)
        draw.text((70 + draw.textlength(title_en, font=t_font) + 25, 152), f"({title_kn})", font=k_font, fill=ACCENT_GREEN)

    draw.line([(70, 215), (W - 70, 215)], fill=BORDER_COLOR, width=2)


def make_slide_1():
    img = Image.new("RGB", (W, H), BG_LIGHT)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "The Problem & Opportunity", "ಸಮಸ್ಯೆ ಮತ್ತು ಅವಕಾಶ")

    # Main Hero Box
    draw.rounded_rectangle([(70, 240), (W - 70, 460)], radius=18, fill=BG_DARK)
    f_quote = get_font(FONT_SEGOE_BOLD, 46)
    draw.text((120, 280), "“Farming questions should not require", font=f_quote, fill=(255, 255, 255))
    draw.text((120, 345), "complicated technology.”", font=f_quote, fill=ACCENT_GOLD)
    f_sub = get_font(FONT_NIRMALA_BOLD, 28)
    draw.text((120, 410), "ಕೃಷಿ ಸಮಸ್ಯೆಗಳಿಗೆ ಪರಿಹಾರ ಪಡೆಯಲು ತಾಂತ್ರಿಕ ತಡೆಗೋಡೆಗಳಿರಬಾರದು.", font=f_sub, fill=ACCENT_LIGHT)

    # 3 Column Cards
    cards = [
        ("The Farmer's Reality",
         "Smallholder farmers in Karnataka often face sudden crop pest attacks and disease symptoms, requiring immediate guidance in Kannada."),
        ("The Digital Barrier",
         "Existing portals demand typing in English, navigating complex multi-step forms, and reading jargon-heavy PDFs."),
        ("Voice-First Simplicity",
         "Krishi Mitra enables a farmer to simply tap a microphone, speak naturally in Kannada, and listen to a clear advisory answer.")
    ]

    cx = 70
    cw = (W - 140 - 60) // 3
    for i, (head, body) in enumerate(cards):
        x0 = cx + i * (cw + 30)
        draw.rounded_rectangle([(x0, 490), (x0 + cw, 960)], radius=16, fill=BG_CARD, outline=BORDER_COLOR, width=2)
        # Top pill
        draw.rounded_rectangle([(x0 + 30, 520), (x0 + 90, 570)], radius=10, fill=ACCENT_LIGHT)
        draw.text((x0 + 50, 532), f"0{i+1}", font=get_font(FONT_SEGOE_BOLD, 24), fill=ACCENT_GREEN)
        draw.text((x0 + 30, 600), head, font=get_font(FONT_SEGOE_BOLD, 28), fill=TEXT_DARK)

        # Word-wrapped body text
        words = body.split()
        lines = []
        cur = []
        for w in words:
            if len(" ".join(cur + [w])) > 28:
                lines.append(" ".join(cur))
                cur = [w]
            else:
                cur.append(w)
        if cur:
            lines.append(" ".join(cur))
        
        y = 660
        for l in lines:
            draw.text((x0 + 30, y), l, font=get_font(FONT_SEGOE, 23), fill=TEXT_MUTED)
            y += 36

    img.save(os.path.join(SLIDE_DIR, "slide_1.png"))


def make_slide_2():
    img = Image.new("RGB", (W, H), BG_LIGHT)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "Krishi Mitra Architecture & Workflow", "ವ್ಯವಸ್ಥೆಯ ವಿನ್ಯಾಸ")

    # Workflow Banner (Speak -> Understand -> Guide -> Listen)
    steps = [
        ("1. SPEAK", "Farmer talks in Kannada\nvia browser mic (8 kHz PCM)"),
        ("2. TRANSCRIBE", "Gnani AI Vachana STT\nreal-time speech to text"),
        ("3. REASON", "Guided Engine / Groq LLM\nnon-diagnostic agronomic guidance"),
        ("4. LISTEN", "Gnani AI Timbre-v3.0\nclear spoken Kannada audio")
    ]
    sw = (W - 140 - 90) // 4
    for i, (st, desc) in enumerate(steps):
        x0 = 70 + i * (sw + 30)
        draw.rounded_rectangle([(x0, 240), (x0 + sw, 380)], radius=14, fill=BG_DARK)
        draw.text((x0 + 25, 260), st, font=get_font(FONT_SEGOE_BOLD, 22), fill=ACCENT_GOLD)
        y = 300
        for line in desc.split("\n"):
            draw.text((x0 + 25, y), line, font=get_font(FONT_SEGOE, 18), fill=(220, 235, 225))
            y += 26

    # 2 Big Architecture Containers
    # Left: Web Ask Experience
    draw.rounded_rectangle([(70, 410), (940, 960)], radius=16, fill=BG_CARD, outline=BORDER_COLOR, width=2)
    draw.rounded_rectangle([(90, 430), (450, 475)], radius=8, fill=ACCENT_LIGHT)
    draw.text((105, 442), "FARMER-FACING ASK WEB APP (/ask)", font=get_font(FONT_SEGOE_BOLD, 18), fill=ACCENT_GREEN)
    draw.text((90, 500), "Open-Ended Agricultural Help", font=get_font(FONT_SEGOE_BOLD, 30), fill=TEXT_DARK)
    
    items_left = [
        "• Mobile PWA designed for touchscreens and rural bandwidth",
        "• Kannada & English instant language switcher",
        "• Browser microphone capture with echo cancellation",
        "• One-click sample questions to explore common problems",
        "• Integrated 'Listen' audio player with instant Stop control"
    ]
    y = 560
    for it in items_left:
        draw.text((90, y), it, font=get_font(FONT_SEGOE, 22), fill=TEXT_MUTED)
        y += 46

    # Right: Guided Helpline & Core Engine
    draw.rounded_rectangle([(980, 410), (1850, 960)], radius=16, fill=BG_CARD, outline=BORDER_COLOR, width=2)
    draw.rounded_rectangle([(1000, 430), (1420, 475)], radius=8, fill=(254, 243, 199))
    draw.text((1015, 442), "GUIDED ENGINE & CORE HELPLINE (/sim)", font=get_font(FONT_SEGOE_BOLD, 18), fill=(180, 83, 9))
    draw.text((1000, 500), "Curated Knowledge Base Pipeline", font=get_font(FONT_SEGOE_BOLD, 30), fill=TEXT_DARK)

    items_right = [
        "• 3 Supported Crops: Paddy (ಭತ್ತ), Arecanut (ಅಡಿಕೆ), Coconut (ತೆಂಗು)",
        "• Full-duplex WebSocket stream with frame-accurate chunking",
        "• Strict chemical review gate (unreviewed chemicals suppressed)",
        "• Slot-filling dialogue engine retaining crop across conversational turns",
        "• Explicit referral flow for unsupported crops to Kisan Call Centre"
    ]
    y = 560
    for it in items_right:
        draw.text((1000, y), it, font=get_font(FONT_SEGOE, 22), fill=TEXT_MUTED)
        y += 46

    img.save(os.path.join(SLIDE_DIR, "slide_2.png"))


def make_slide_3():
    img = Image.new("RGB", (W, H), BG_LIGHT)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "Real Question Input: The Ask Interface", "ಪ್ರಶ್ನೆ ಕೇಳುವ ವಿಧಾನ")

    # Left: UI mock representing /ask
    draw.rounded_rectangle([(70, 240), (1050, 960)], radius=20, fill=BG_CARD, outline=BORDER_COLOR, width=2)
    
    # Language toggle UI
    draw.rounded_rectangle([(110, 270), (420, 320)], radius=25, fill=(235, 240, 238))
    draw.rounded_rectangle([(112, 272), (265, 318)], radius=23, fill=ACCENT_GREEN)
    draw.text((145, 282), "ಕನ್ನಡ (KN)", font=get_font(FONT_SEGOE_BOLD, 18), fill=(255, 255, 255))
    draw.text((290, 282), "English (EN)", font=get_font(FONT_SEGOE_BOLD, 18), fill=TEXT_MUTED)

    # Prompt label
    draw.text((110, 350), "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಇಲ್ಲಿ ಹೇಳಿ ಅಥವಾ ಬರೆಯಿರಿ:", font=get_font(FONT_NIRMALA_BOLD, 26), fill=TEXT_DARK)
    
    # Input box with live transcribed Kannada question
    draw.rounded_rectangle([(110, 400), (1010, 580)], radius=14, fill=(250, 252, 251), outline=ACCENT_GREEN, width=2)
    q_kn = "ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತುವ ಹುಳು ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?"
    draw.text((140, 440), q_kn, font=get_font(FONT_NIRMALA_BOLD, 32), fill=TEXT_DARK)
    draw.text((140, 500), "“Leaf folder caterpillars have appeared in my paddy crop, what should I do?”", font=get_font(FONT_SEGOE, 20), fill=TEXT_MUTED)

    # Controls: Mic Button & Submit Button
    draw.ellipse([(110, 620), (200, 710)], fill=(220, 53, 69)) # Red recording mic
    draw.text((143, 648), "🎤", font=get_font(FONT_SEGOE_BOLD, 30), fill=(255, 255, 255))
    draw.text((220, 640), "ಧ್ವನಿ ರೆಕಾರ್ಡಿಂಗ್ ಚಾಲನೆಯಲ್ಲಿದೆ...", font=get_font(FONT_NIRMALA_BOLD, 24), fill=(180, 40, 40))
    draw.text((220, 672), "Listening via Gnani AI Speech-to-Text (8 kHz PCM Stream)", font=get_font(FONT_SEGOE, 18), fill=TEXT_MUTED)

    draw.rounded_rectangle([(760, 625), (1010, 705)], radius=12, fill=ACCENT_GREEN)
    draw.text((820, 650), "ಕೇಳಿ (Submit)", font=get_font(FONT_SEGOE_BOLD, 22), fill=(255, 255, 255))

    # Example question chips
    draw.text((110, 750), "ಉದಾಹರಣೆ ಪ್ರಶ್ನೆಗಳು (Sample Questions):", font=get_font(FONT_NIRMALA_BOLD, 20), fill=TEXT_MUTED)
    samples = [
        "ಅಡಿಕೆಯಲ್ಲಿ ಕೊಳೆ ರೋಗದ ಲಕ್ಷಣಗಳು",
        "ತೆಂಗಿನ ಮರದಲ್ಲಿ ದುಂಬಿ ಬಾಧೆ ನಿಯಂತ್ರಣ",
        "ಭತ್ತದಲ್ಲಿ ರಸಗೊಬ್ಬರ ನಿರ್ವಹಣೆ"
    ]
    sy = 790
    for s in samples:
        draw.rounded_rectangle([(110, sy), (680, sy + 42)], radius=8, fill=ACCENT_LIGHT)
        draw.text((130, sy + 8), s, font=get_font(FONT_NIRMALA_BOLD, 20), fill=ACCENT_GREEN)
        sy += 52

    # Right: Feature Highlights
    draw.rounded_rectangle([(1100, 240), (1850, 960)], radius=20, fill=BG_DARK)
    draw.text((1150, 290), "GNANI AI SPEECH INTEGRATION", font=get_font(FONT_SEGOE_BOLD, 20), fill=ACCENT_GOLD)
    draw.text((1150, 330), "Empowering Voice-First Access", font=get_font(FONT_SEGOE_BOLD, 38), fill=(255, 255, 255))

    points = [
        ("Live Phone-Quality Audio", "Audio captured directly through the browser at 8 kHz phone quality, mirroring telecommunication standards."),
        ("Transcript Verification", "Speech is converted to text and stays visible in the input box, so the farmer can inspect or edit before submission."),
        ("Zero Typing Required", "Farmers who cannot spell or type complex Kannada botanical terms can ask questions completely by voice."),
        ("Bilingual Native Model", "Trained to recognize rural Kannada agricultural phonemes, dialectal forms, and crop names accurately.")
    ]
    py = 430
    for p_title, p_desc in points:
        draw.text((1150, py), p_title, font=get_font(FONT_SEGOE_BOLD, 24), fill=ACCENT_LIGHT)
        draw.text((1150, py + 34), p_desc, font=get_font(FONT_SEGOE, 20), fill=(210, 225, 220))
        py += 115

    img.save(os.path.join(SLIDE_DIR, "slide_3.png"))


def make_slide_4():
    img = Image.new("RGB", (W, H), BG_LIGHT)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "Spoken Answer: Gnani AI Timbre-v3.0", "ಧ್ವನಿ ರೂಪದ ಉತ್ತರ")

    # Highlight Playback Card
    draw.rounded_rectangle([(70, 240), (W - 70, 960)], radius=20, fill=BG_CARD, outline=BORDER_COLOR, width=2)

    # Audio Banner
    draw.rounded_rectangle([(120, 275), (W - 120, 375)], radius=14, fill=BG_DARK)
    draw.ellipse([(150, 298), (205, 353)], fill=ACCENT_GOLD)
    draw.polygon([(172, 313), (172, 338), (192, 325)], fill=BG_DARK)
    draw.text((230, 305), "AUDIO EXCERPT PLAYING: GNANI AI KANNADA TEXT-TO-SPEECH", font=get_font(FONT_SEGOE_BOLD, 22), fill=ACCENT_LIGHT)
    draw.text((230, 335), "Voice: Lakshmi · Model: timbre-v3.0 · Speed: 0.95 · Sample Rate: 8000 Hz", font=get_font(FONT_SEGOE, 18), fill=(200, 225, 215))

    # Spoken Kannada Box
    draw.rounded_rectangle([(120, 410), (W - 120, 600)], radius=16, fill=(245, 252, 247), outline=ACCENT_GREEN, width=2)
    draw.text((160, 435), "ಕೃಷಿ ಮಿತ್ರ ನೀಡಿದ ಧ್ವನಿ ಉತ್ತರ (Spoken Kannada Text):", font=get_font(FONT_SEGOE_BOLD, 20), fill=ACCENT_GREEN)
    kn_resp = "ಕೃಷಿ ಮಿತ್ರ: ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತುವ ಹುಳು ಕಂಡುಬಂದರೆ,\nಮುನ್ನೆಚ್ಚರಿಕೆ ಕ್ರಮಗಳನ್ನು ಕೈಗೊಳ್ಳಿ."
    draw.text((160, 480), kn_resp, font=get_font(FONT_NIRMALA_BOLD, 36), fill=TEXT_DARK)

    # English Translation Box
    draw.rounded_rectangle([(120, 630), (W - 120, 800)], radius=16, fill=(250, 250, 252), outline=BORDER_COLOR, width=2)
    draw.text((160, 655), "Verified English Translation:", font=get_font(FONT_SEGOE_BOLD, 20), fill=TEXT_MUTED)
    en_trans = "“Krishi Mitra: If leaf folder caterpillars are observed in the paddy crop,\ntake precautionary control measures.”"
    draw.text((160, 700), en_trans, font=get_font(FONT_SEGOE_BOLD, 30), fill=TEXT_DARK)

    # Footer feature notes
    draw.line([(120, 840), (W - 120, 840)], fill=BORDER_COLOR, width=2)
    notes = [
        "✓ Real-time synthesis streaming with bounded retry and cache safety",
        "✓ Exact response end boundaries preventing audio truncations",
        "✓ Playback synchronized with UI: Listen & Stop controls always active"
    ]
    nx = 120
    for n in notes:
        draw.text((nx, 880), n, font=get_font(FONT_SEGOE_BOLD, 21), fill=ACCENT_GREEN)
        nx += 580

    img.save(os.path.join(SLIDE_DIR, "slide_4.png"))


def make_slide_5():
    img = Image.new("RGB", (W, H), BG_LIGHT)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "Engineering Challenges & Production Fixes", "ತಾಂತ್ರಿಕ ಸವಾಲುಗಳು ಮತ್ತು ಪರಿಹಾರ")

    challenges = [
        ("CHALLENGE 1: AUDIO CUTOFFS & WEBSOCKET TIMEOUTS",
         "The Problem:",
         "During voice dialogue, spoken responses sometimes cut off halfway. Gnani TTS keepalive ping timeouts dropped the WebSocket, and browser microphone frames began streaming while the bot was still speaking.",
         "Our Fix:",
         "Implemented an explicit client-server acknowledgement protocol (ack_mode). The server waits for targetSrc.onended before unmuting, while the browser suppresses all microphone processing while session.isPlaying is active."),

        ("CHALLENGE 2: CROP RETENTION & PROBLEM-FIRST FLOW",
         "The Problem:",
         "When a farmer stated a symptom first (e.g. 'ರೋಗ ಬಂದಿದೆ ಬೇರಿನಲ್ಲಿ'), the bot silently inferred crop defaults or re-asked the crop repeatedly after the farmer answered.",
         "Our Fix:",
         "Overhauled Session.respond() to systematically ask for the crop first when missing, retain confirmed crops across turns, advance immediately to problem advice, and never replay initial greetings."),

        ("CHALLENGE 3: ACCESSIBLE BILINGUAL WEB EXPERIENCE",
         "The Problem:",
         "Telephony gateways (Exotel) have carrier setup dependencies and testing friction for external evaluators.",
         "Our Fix:",
         "Engineered /ask alongside /sim: a mobile-responsive web PWA featuring instant Kannada/English toggles, Groq LLM agronomic reasoning, and direct Gnani TTS Listen playback.")
    ]

    cx = 70
    cw = (W - 140 - 60) // 3
    for i, (head, p_lbl, p_txt, f_lbl, f_txt) in enumerate(challenges):
        x0 = cx + i * (cw + 30)
        draw.rounded_rectangle([(x0, 240), (x0 + cw, 960)], radius=16, fill=BG_CARD, outline=BORDER_COLOR, width=2)
        
        # Pill header
        draw.rounded_rectangle([(x0 + 20, 260), (x0 + cw - 20, 310)], radius=8, fill=BG_DARK)
        draw.text((x0 + 30, 275), head, font=get_font(FONT_SEGOE_BOLD, 17), fill=ACCENT_GOLD)

        # Problem section
        draw.text((x0 + 25, 335), p_lbl, font=get_font(FONT_SEGOE_BOLD, 22), fill=(180, 40, 40))
        words = p_txt.split()
        lines = []
        cur = []
        for w in words:
            if len(" ".join(cur + [w])) > 30:
                lines.append(" ".join(cur))
                cur = [w]
            else:
                cur.append(w)
        if cur:
            lines.append(" ".join(cur))
        y = 375
        for l in lines:
            draw.text((x0 + 25, y), l, font=get_font(FONT_SEGOE, 19), fill=TEXT_MUTED)
            y += 28

        draw.line([(x0 + 25, y + 15), (x0 + cw - 25, y + 15)], fill=BORDER_COLOR, width=1)

        # Fix section
        y += 35
        draw.text((x0 + 25, y), f_lbl, font=get_font(FONT_SEGOE_BOLD, 22), fill=ACCENT_GREEN)
        y += 40
        words = f_txt.split()
        lines = []
        cur = []
        for w in words:
            if len(" ".join(cur + [w])) > 30:
                lines.append(" ".join(cur))
                cur = [w]
            else:
                cur.append(w)
        if cur:
            lines.append(" ".join(cur))
        for l in lines:
            draw.text((x0 + 25, y), l, font=get_font(FONT_SEGOE, 19), fill=TEXT_DARK)
            y += 28

    img.save(os.path.join(SLIDE_DIR, "slide_5.png"))


def make_slide_6():
    img = Image.new("RGB", (W, H), BG_LIGHT)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "Responsible Advisory & Realistic Scope", "ಜವಾಬ್ದಾರಿಯುತ ಸಲಹೆ ಮತ್ತು ಮಿತಿಗಳು")

    # Left: Safety & Referral Architecture
    draw.rounded_rectangle([(70, 240), (1050, 960)], radius=20, fill=BG_CARD, outline=BORDER_COLOR, width=2)
    draw.text((110, 280), "AGRICULTURAL SAFETY PRINCIPLES", font=get_font(FONT_SEGOE_BOLD, 20), fill=ACCENT_GREEN)
    draw.text((110, 320), "Careful Advisory Safeguards", font=get_font(FONT_SEGOE_BOLD, 36), fill=TEXT_DARK)

    safety_rules = [
        ("Non-Diagnostic Guidance",
         "The system provides general agronomic guidance, never claiming to replace an in-person plant pathology diagnosis."),
        ("Strict Chemical Gate",
         "Pesticide, fungicide, and herbicide trade names and dosages are withheld from voice synthesis unless verified by agricultural experts."),
        ("Unsupported-Crop Honesty",
         "Instead of fabricating hallucinated advice for unknown crops, Krishi Mitra explains that support is currently focused on paddy, arecanut, and coconut."),
        ("Pre-Harvest & PPE Warnings",
         "Advisories emphasize protective equipment (masks, gloves) and adherence to mandatory pre-harvest intervals.")
    ]
    sy = 400
    for title, desc in safety_rules:
        draw.text((110, sy), title, font=get_font(FONT_SEGOE_BOLD, 24), fill=TEXT_DARK)
        draw.text((110, sy + 32), desc, font=get_font(FONT_SEGOE, 20), fill=TEXT_MUTED)
        sy += 115

    # Right: Referral & Project Limits
    draw.rounded_rectangle([(1100, 240), (1850, 580)], radius=20, fill=BG_DARK)
    draw.text((1140, 280), "EXTERNAL SUPPORT REFERRAL", font=get_font(FONT_SEGOE_BOLD, 20), fill=ACCENT_GOLD)
    draw.text((1140, 320), "Kisan Call Centre: 1800-180-1551", font=get_font(FONT_SEGOE_BOLD, 34), fill=(255, 255, 255))
    
    ref_desc = [
        "• Government of India toll-free agricultural helpline referral",
        "• Clearly presented as an external referral for severe/spreading disease",
        "• NOT Krishi Mitra's phone number; never misrepresented as our service"
    ]
    ry = 385
    for r in ref_desc:
        draw.text((1140, ry), r, font=get_font(FONT_SEGOE, 20), fill=(215, 235, 225))
        ry += 42

    draw.rounded_rectangle([(1100, 620), (1850, 960)], radius=20, fill=BG_CARD, outline=BORDER_COLOR, width=2)
    draw.text((1140, 660), "TRANSPARENT SYSTEM LIMITATIONS", font=get_font(FONT_SEGOE_BOLD, 20), fill=(180, 40, 40))
    draw.text((1140, 700), "Current Prototype Status", font=get_font(FONT_SEGOE_BOLD, 34), fill=TEXT_DARK)
    
    limits = [
        "• Web App Live: /ask and /sim are fully operational and hosted on Render",
        "• Telephony Incomplete: Exotel IVR integration is in progress; marked 'Coming soon'",
        "• PWA Web Experience: Installable on Android Chrome; no offline inference claim",
        "• Human-in-the-Loop: Critical agronomic decisions always defer to local KVK officers"
    ]
    ly = 765
    for l in limits:
        draw.text((1140, ly), l, font=get_font(FONT_SEGOE, 20), fill=TEXT_MUTED)
        ly += 42

    img.save(os.path.join(SLIDE_DIR, "slide_6.png"))


def make_slide_7():
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Center hero closing
    draw.text((W // 2 - 320, 180), "ಕೃಷಿ ಮಿತ್ರ", font=get_font(FONT_NIRMALA_BOLD, 90), fill=(255, 255, 255))
    draw.text((W // 2 - 280, 310), "KRISHI MITRA", font=get_font(FONT_SEGOE_BOLD, 64), fill=ACCENT_GOLD)
    
    motto = "Speak. Understand. Take the next step."
    draw.text((W // 2 - 300, 400), motto, font=get_font(FONT_SEGOE, 34), fill=ACCENT_LIGHT)

    draw.line([(300, 480), (W - 300, 480)], fill=(50, 90, 75), width=2)

    draw.text((W // 2 - 380, 530), "Built for the Gnani AI Great Indian AI Internship Challenge", font=get_font(FONT_SEGOE_BOLD, 28), fill=(255, 255, 255))
    draw.text((W // 2 - 330, 580), "Empowering Karnataka's farmers with Kannada voice AI", font=get_font(FONT_SEGOE, 24), fill=(200, 225, 215))

    # Links card
    draw.rounded_rectangle([(400, 650), (W - 400, 870)], radius=16, fill=(28, 68, 54), outline=(70, 120, 100), width=2)
    
    draw.text((450, 690), "🌐  Live Application:", font=get_font(FONT_SEGOE_BOLD, 24), fill=ACCENT_GOLD)
    draw.text((720, 690), "https://krishi-mitra-gn3h.onrender.com/", font=get_font(FONT_SEGOE, 24), fill=(255, 255, 255))

    draw.text((450, 750), "💻  GitHub Repository:", font=get_font(FONT_SEGOE_BOLD, 24), fill=ACCENT_GOLD)
    draw.text((720, 750), "https://github.com/11DDBOY11/Gnani_ai_Competition", font=get_font(FONT_SEGOE, 24), fill=(255, 255, 255))

    draw.text((450, 810), "⚡  Core Technology:", font=get_font(FONT_SEGOE_BOLD, 24), fill=ACCENT_GOLD)
    draw.text((720, 810), "Gnani AI STT & TTS · FastAPI · Groq LLM · PWA", font=get_font(FONT_SEGOE, 24), fill=ACCENT_LIGHT)

    draw.text((W // 2 - 120, 950), "ಧನ್ಯವಾದಗಳು · Thank You", font=get_font(FONT_NIRMALA_BOLD, 28), fill=ACCENT_LIGHT)

    img.save(os.path.join(SLIDE_DIR, "slide_7.png"))


if __name__ == "__main__":
    print("Generating 7 HD slides...")
    make_slide_1()
    make_slide_2()
    make_slide_3()
    make_slide_4()
    make_slide_5()
    make_slide_6()
    make_slide_7()
    print("All slides generated in", SLIDE_DIR)

