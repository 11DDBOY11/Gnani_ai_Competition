import json, pathlib, re, unicodedata
from dataclasses import dataclass, field

KB_PATH = pathlib.Path(__file__).with_name("kb.json")
KB = {a["id"]: a for a in json.loads(KB_PATH.read_text(encoding="utf-8"))["advisories"]}

CROPS = {
    "paddy": ["ಭತ್ತ", "ಬತ್ತ", "ಅಕ್ಕಿ", "ಗದ್ದೆ", "paddy", "rice", "bhatta"],
    "arecanut": ["ಅಡಿಕೆ", "ಅಡಕೆ", "ಸುಪಾರಿ", "arecanut", "areca", "adike"],
    "coconut": ["ತೆಂಗು", "ತೆಂಗಿನ", "ನಾರಿಕೇಳ", "coconut", "thengu"],
    "sugarcane": ["ಕಬ್ಬು", "ಕಬ್ಬಿನ", "sugarcane", "sugar cane"],  # NEEDS NATIVE REVIEW
    "grapes": ["ದ್ರಾಕ್ಷಿ", "ದ್ರಾಕ್ಷಿಯ", "grapes", "grape"],  # NEEDS NATIVE REVIEW
    "pomegranate": ["ದಾಳಿಂಬೆ", "ಅನಾರ್", "pomegranate", "anar"],  # NEEDS NATIVE REVIEW
    "maize": ["ಮೆಕ್ಕೆಜೋಳ", "ಮುಸುಕಿನ", "maize", "corn", "makka"],  # NEEDS NATIVE REVIEW
    "jowar": ["ಜೋಳ", "ಸಜ್ಜೆ", "jowar", "sorghum"],  # NEEDS NATIVE REVIEW
    "wheat": ["ಗೋಧಿ", "wheat"],  # NEEDS NATIVE REVIEW
    "silk": ["ರೇಷ್ಮೆ", "ರೇಶ್ಮೆ", "silk", "sericulture"],  # NEEDS NATIVE REVIEW
    "cotton": ["ಹತ್ತಿ", "cotton"],  # NEEDS NATIVE REVIEW
}
CROP_KN = {
    "paddy": "ಭತ್ತ",
    "arecanut": "ಅಡಿಕೆ",
    "coconut": "ತೆಂಗು",
    "sugarcane": "ಕಬ್ಬು",       # NEEDS NATIVE REVIEW
    "grapes": "ದ್ರಾಕ್ಷಿ",        # NEEDS NATIVE REVIEW
    "pomegranate": "ದಾಳಿಂಬೆ",   # NEEDS NATIVE REVIEW
    "maize": "ಮೆಕ್ಕೆಜೋಳ",       # NEEDS NATIVE REVIEW
    "jowar": "ಜೋಳ",             # NEEDS NATIVE REVIEW
    "wheat": "ಗೋಧಿ",            # NEEDS NATIVE REVIEW
    "silk": "ರೇಷ್ಮೆ",            # NEEDS NATIVE REVIEW
    "cotton": "ಹತ್ತಿ",           # NEEDS NATIVE REVIEW
}

PROBLEMS = {
    "paddy_leaf_folder": ["ಎಲೆ ಸುತ್ತ", "ಎಲೆ ಮಡಚ", "ಸುತ್ತಿಕೊಂಡ", "ಸುತ್ತಿಕೊಳ್ಳ", "leaf folder", "leaf roll", "leaf fold"],
    "paddy_blast": ["ಬೆಂಕಿ ರೋಗ", "ಬೆಂಕಿರೋಗ", "ಕಣ್ಣಿನ ಆಕಾರ", "ಕಂದು ಚುಕ್ಕೆ", "blast"],
    "arecanut_koleroga": ["ಕಾಯಿ ಕೊಳೆ", "ಕಾಯಿ ಕೊಳೆತ", "ಕೊಳೆ ರೋಗ", "ಕೊಳೆರೋಗ", "ಮಹಾಲಿ", "koleroga", "fruit rot"],
    "coconut_rhino_beetle": ["ಕೊಂಬಿನ ದುಂಬಿ", "ದುಂಬಿ", "beetle"],
    "coconut_bud_rot": ["ಸುಳಿ ಕೊಳೆ", "ಸುಳಿ", "bud rot"],
    "sugarcane_stem_rot": ["ಕಾಂಡ ಕೊಳೆ", "ಕಬ್ಬು ಕೊಳೆ", "stem rot"],  # NEEDS NATIVE REVIEW
    "grapes_vine_rot": ["ಬಳ್ಳಿ ಕೊಳೆ", "ದ್ರಾಕ್ಷಿ ಕೊಳೆ", "vine rot", "downy mildew"],  # NEEDS NATIVE REVIEW
    "pomegranate_fruit_rot": ["ಅನಾರ್ ಕಾಯಿ", "ದಾಳಿಂಬೆ ಕೊಳೆ", "pomegranate rot"],  # NEEDS NATIVE REVIEW
    "maize_grain_pest": ["ಮೆಕ್ಕೆಜೋಳ ಕಾಳು", "ಕಾಳು ಕೀಟ", "fall armyworm", "stem borer"],  # NEEDS NATIVE REVIEW
    "jowar_pest": ["ಜೋಳದ ಕೀಟ", "ಜೋಳ ಕೀಟ", "jowar pest", "shoot fly"],  # NEEDS NATIVE REVIEW
    "wheat_rust": ["ಗೋಧಿ ರತ್ತು", "ರಸ್ಟ್", "wheat rust", "rust"],  # NEEDS NATIVE REVIEW
    "silk_worm_disease": ["ರೇಷ್ಮೆ ಹುಳು", "ರೇಷ್ಮೆ ರೋಗ", "silkworm disease", "pebrine"],  # NEEDS NATIVE REVIEW
    "cotton_whitefly": ["ಬಿಳಿ ನೊಣ", "ಹತ್ತಿ ನೊಣ", "whitefly", "cotton pest"],  # NEEDS NATIVE REVIEW
}

STAGES = {
    "seedling": ["ಸಸಿ", "ಚಿಕ್ಕ", "ಸಣ್ಣ", "ನಾಟಿ", "seedling", "small"],
    "tillering": ["ಕವಲು", "ಕವಲೊಡೆಯುವ", "tillering", "vegetative"],
    "flowering": ["ಹೂ", "ಹೊರಬ", "flower"],
    "grain": ["ಕಾಳು", "ತೆನೆ", "ಕಾಯಿ ಕಟ್ಟ", "ಕಟಾವು", "grain"],
}

GOODBYE = ["ಧನ್ಯವಾದ", "ಸಾಕು", "ಇಷ್ಟೇ", "thank", "bye"]
REPEAT = ["ಮತ್ತೆ ಹೇಳಿ", "ಇನ್ನೊಮ್ಮೆ", "ಪುನಃ", "repeat"]

T = {
    "greeting": ["ನಮಸ್ಕಾರ. ಇದು ಕೃಷಿ ಮಿತ್ರ ಸೇವೆ.", "ಸೇವೆ ಸುಧಾರಿಸಲು ಈ ಕರೆಯನ್ನು ದಾಖಲಿಸಲಾಗುತ್ತದೆ.", "ನಿಮ್ಮ ಬೆಳೆ ಮತ್ತು ಸಮಸ್ಯೆಯನ್ನು ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ."],
    "ask_crop": ["ನಿಮ್ಮ ಬೆಳೆ ಯಾವುದು? ಭತ್ತ, ಅಡಿಕೆ, ಅಥವಾ ತೆಂಗು?"],
    "ask_problem": ["ಬೆಳೆಯಲ್ಲಿ ಏನು ಸಮಸ್ಯೆ ಕಾಣುತ್ತಿದೆ? ಎಲೆ, ಕಾಯಿ, ಅಥವಾ ಗಿಡದ ಬಗ್ಗೆ ಹೇಳಿ."],
    "ask_stage": ["ಬೆಳೆ ಯಾವ ಹಂತದಲ್ಲಿದೆ? ಸಸಿ, ಹೂ ಬಿಡುವ ಹಂತ, ಅಥವಾ ಕಾಳು ಕಟ್ಟುವ ಹಂತ?"],
    "reprompt": ["ಕ್ಷಮಿಸಿ, ಸರಿಯಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಹೇಳಿ."],
    "escalate": ["ಈ ಬಗ್ಗೆ ನಿಖರವಾದ ಸಲಹೆ ನೀಡಲು ನನಗೆ ಸಾಧ್ಯವಿಲ್ಲ.", "ದಯವಿಟ್ಟು ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿ ಅಥವಾ ರೈತ ಸಂಪರ್ಕ ಕೇಂದ್ರವನ್ನು ಸಂಪರ್ಕಿಸಿ."],
    "no_chem": ["ಔಷಧದ ಹೆಸರು ಮತ್ತು ಪ್ರಮಾಣಕ್ಕಾಗಿ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ."],
    "safety": ["ಸಿಂಪಡಿಸುವಾಗ ಕೈಗವಸು ಮತ್ತು ಮುಖಕ್ಕೆ ಮಾಸ್ಕ್ ಧರಿಸಿ. ಲೇಬಲ್ ಓದಿ."],
    "bye": ["ಧನ್ಯವಾದಗಳು. ಮತ್ತೆ ಬೇಕಾದರೆ ಕರೆ ಮಾಡಿ."],
    # REVIEW: Human review of Kannada wording for advisory follow-up
    "advisory_followup": ["ಇದನ್ನು ಮತ್ತೆ ಕೇಳಬೇಕೆ, ಅಥವಾ ಬೇರೆ ಪ್ರಶ್ನೆ ಇದೆಯೇ?"],
    # REVIEW: Human review of Kannada wording for generic follow-up options
    "followup_options": ["ಹಿಂದಿನ ಸಲಹೆಯನ್ನು ಮತ್ತೆ ಕೇಳಬೇಕೆ, ಅಥವಾ ಬೇರೆ ಬೆಳೆಯ ಬಗ್ಗೆ ಪ್ರಶ್ನೆ ಇದೆಯೇ?"],
    # REVIEW: Human review of Kannada wording for unsupported low-yield query
    "unsupported_yield_body": [
        "ಕಾಯಿ ಬಿಡದಿರುವ ಅಥವಾ ಇಳುವರಿ ಸಮಸ್ಯೆಗೆ ಸದ್ಯಕ್ಕೆ ನನ್ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿದ ಸಲಹೆ ಲಭ್ಯವಿಲ್ಲ.",
        "ಹೆಚ್ಚಿನ ಮಾಹಿತಿ ಮತ್ತು ಸೂಕ್ತ ಪೋಷಕಾಂಶ ನಿರ್ವಹಣೆಗೆ ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿ ಅಥವಾ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರವನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "ಬೇರೆ ಬೆಳೆಯ ಬಗ್ಗೆ ಅಥವಾ ಸಮಸ್ಯೆಯ ಬಗ್ಗೆ ಪ್ರಶ್ನೆ ಇದೆಯೇ?",
    ],
    # REVIEW: Human review of Kannada wording for capabilities overview
    "capabilities_overview": [
        "ಕೃಷಿ ಮಿತ್ರ ಪ್ರಸ್ತುತ ಪ್ರಾಯೋಗಿಕ ಹಂತದಲ್ಲಿದ್ದು, ಭತ್ತ, ಅಡಿಕೆ ಮತ್ತು ತೆಂಗು ಬೆಳೆಗಳ ಆಯ್ದ ಸಮಸ್ಯೆಗಳಿಗೆ ಪ್ರಾಥಮಿಕ ಮಾಹಿತಿ ನೀಡಬಲ್ಲದು.",
        "ಇದು ತಜ್ಞರು ಪರಿಶೀಲಿಸಿದ ಪೂರ್ಣ ಸಲಹೆ ಅಲ್ಲ, ಮತ್ತು ರಾಸಾಯನಿಕ ಔಷಧಗಳ ಶಿಫಾರಸು ಸದ್ಯಕ್ಕೆ ಲಭ್ಯವಿಲ್ಲ.",
        "ನಿಮ್ಮ ಬೆಳೆ ಮತ್ತು ಕಾಣುತ್ತಿರುವ ಲಕ್ಷಣಗಳನ್ನು ಹೇಳಿ, ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
    ],
    # REVIEW: Human review of Kannada wording when no previous advisory exists to replay
    "no_previous_advisory": [
        "ಸದ್ಯಕ್ಕೆ ಯಾವುದೇ ಹಿಂದಿನ ಸಲಹೆ ಲಭ್ಯವಿಲ್ಲ. ನಿಮ್ಮ ಬೆಳೆ ಮತ್ತು ಸಮಸ್ಯೆಯನ್ನು ತಿಳಿಸಿ.",
    ],
    # REVIEW: Human review of Kannada wording for leaf-folder intake: symptoms
    "lf_intake_symptoms": [
        "ಗದ್ದೆಯಲ್ಲಿ ಎಲೆಗಳು ಉದ್ದಕ್ಕೆ ಮಡಚಿಕೊಂಡು, ಒಳಭಾಗದಲ್ಲಿ ಬಿಳಿಯ ಪಾರದರ್ಶಕ ಪಟ್ಟಿಗಳು ಕಾಣಿಸುತ್ತಿವೆಯೇ?"
    ],
    # REVIEW: Human review of Kannada wording for leaf-folder intake: live larvae
    "lf_intake_live_larvae": [
        "ಮಡಚಿದ ಎಲೆಯನ್ನು ಬಿಡಿಸಿ ನೋಡಿದಾಗ ಒಳಗೆ ಜೀವಂತ ಹಸಿರು ಹುಳುಗಳು ಕಂಡುಬಂದಿವೆಯೇ?"
    ],
    # REVIEW: Human review of Kannada wording for leaf-folder intake: stage
    "lf_intake_stage": [
        "ನಿಮ್ಮ ಭತ್ತದ ಬೆಳೆ ಯಾವ ಹಂತದಲ್ಲಿದೆ? ಸಸಿ ಹಂತ, ಕವಲು ಒಡೆಯುವ ಹಂತ, ತೆನೆ ಹಂತ ಅಥವಾ ಗೊತ್ತಿಲ್ಲವೇ?"
    ],
    # REVIEW: Human review of Kannada wording for leaf-folder intake: counts
    "lf_intake_leaf_counts": [
        "ಪರಿಶೀಲಿಸಿದ ಒಟ್ಟು ಎಲೆಗಳಲ್ಲಿ ಸರಿಸುಮಾರು ಎಷ್ಟು ಎಲೆಗಳು ಮಡಚಿಕೊಂಡಿವೆ? ಉದಾಹರಣೆಗೆ ನೂರು ಎಲೆಗಳಲ್ಲಿ ಎಷ್ಟು?"
    ],
    # REVIEW: Human review of Kannada wording for leaf-folder intake: harvest days
    "lf_intake_harvest_days": [
        "ಬೆಳೆ ಕಟಾವಿಗೆ ಇನ್ನೂ ಸರಿಸುಮಾರು ಎಷ್ಟು ದಿನಗಳು ಬಾಕಿ ಇವೆ?"
    ],
    # REVIEW: Human review of Kannada wording for leaf-folder intake: mulberry warning
    "lf_intake_nearby_mulberry": [
        "ನಿಮ್ಮ ಗದ್ದೆಯ ಸಮೀಪದಲ್ಲಿ ರೇಷ್ಮೆ ಸಾಕಾಣಿಕೆ ಅಥವಾ ಹಿಪ್ಪುನೇರಳೆ ತೋಟ ಇದೆಯೇ?"
    ],
    # REVIEW: Human review of Kannada wording for leaf-folder intake: recent pesticides
    "lf_intake_recent_pesticides": [
        "ಕಳೆದ ಹದಿನೈದು ದಿನಗಳಲ್ಲಿ ಗದ್ದೆಗೆ ಯಾವುದಾದರೂ ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸಿದ್ದೀರಾ? ಸಿಂಪಡಿಸಿದ್ದರೆ ಔಷಧದ ಹೆಸರು ತಿಳಿದಿದೆಯೇ?"
    ],
    # REVIEW: Human review of Kannada wording for leaf-folder intake completion acknowledgment
    "lf_intake_complete_ack": [
        "ಎಲೆ ಸುತ್ತುವ ಹುಳುವಿನ ಸಮಗ್ರ ಮಾಹಿತಿಯನ್ನು ಪರಿಶೀಲನೆಗಾಗಿ ದಾಖಲಿಸಿಕೊಳ್ಳಲಾಗಿದೆ."
    ],
    # REVIEW: Human review of Kannada wording for leaf-folder mulberry hazard warning
    "lf_mulberry_hazard": [
        "ಎಚ್ಚರಿಕೆ: ಪಿ.ಪಿ.ಕ್ಯೂ.ಎಸ್. ಲೇಬಲ್ ಪ್ರಕಾರ ಕ್ಲೋರಾಂಟ್ರಾನಿಲಿಪ್ರೋಲ್ ರೇಷ್ಮೆ ಹುಳುಗಳಿಗೆ ವಿಷಕಾರಿ. ಸಮೀಪದ ಹಿಪ್ಪುನೇರಳೆ ತೋಟ ಮತ್ತು ರೇಷ್ಮೆ ಹುಳು ಕೇಂದ್ರಗಳಿಗೆ ಔಷಧ ಹರಡದಂತೆ ತಡೆಯುವುದು ಕಡ್ಡಾಯ. ನಮ್ಮ ವ್ಯವಸ್ಥೆಯ ಸುರಕ್ಷತಾ ನೀತಿಯಂತೆ ಇಂತಹ ಪ್ರದೇಶಗಳ ಸಮೀಪ ಈ ಔಷಧವನ್ನು ಶಿಫಾರಸು ಮಾಡುವುದಿಲ್ಲ."
    ],
    # REVIEW: Human review of Kannada wording for pre-harvest interval hazard warning
    "lf_harvest_hazard": [
        "ಎಚ್ಚರಿಕೆ: ಈ ಔಷಧಕ್ಕೆ ಕಟಾವಿನ ಕಾಯುವ ಅವಧಿ ನಲವತ್ತೇಳು ದಿನಗಳಾಗಿದ್ದು, ನಿಮ್ಮ ಕಟಾವಿನ ಅವಧಿ ಇದಕ್ಕಿಂತ ಕಡಿಮೆಯಿದೆ."
    ],
    # REVIEW: Human review of Kannada wording for PPE and re-entry reminder from label
    "lf_safety_ppe_reentry": [
        "ಕೀಟನಾಶಕ ಬಳಸುವಾಗ ರಕ್ಷಣಾ ಉಡುಪು, ಕೈಗವಸು, ಮಾಸ್ಕ್, ಕನ್ನಡಕ ಮತ್ತು ಕಾಲಿಗೆ ಶೂ ಧರಿಸಬೇಕು. ಸಿಂಪಡಿಸಿದ ನಂತರ ಕನಿಷ್ಠ ಇಪ್ಪತ್ನಾಲ್ಕು ಗಂಟೆಗಳು ಹಾಗೂ ಔಷಧ ಸಂಪೂರ್ಣ ಒಣಗುವವರೆಗೆ ಗದ್ದೆಗೆ ಪ್ರವೇಶಿಸಬಾರದು."
    ],
    # REVIEW: Human review of Kannada wording for professional review gate notice
    "lf_expert_gate_notice": [
        "ಈ ಮಾದರಿಯ ರಾಸಾಯನಿಕ ಸಲಹೆಯನ್ನು ಇನ್ನೂ ವೃತ್ತಿಪರವಾಗಿ ಪರಿಶೀಲಿಸಿಲ್ಲ, ಆದ್ದರಿಂದ ಇದನ್ನು ಸಕ್ರಿಯಗೊಳಿಸಲಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿ ಅಥವಾ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರವನ್ನು ಸಂಪರ್ಕಿಸಿ."
    ],
}

CHEM_FIELDS = ["product", "dose", "water", "preharvest_days", "source", "reviewed_by", "review_date"]


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").replace("\u200c", "").replace("\u200d", "")
    s = re.sub(r"[.,!?;:'()\"-]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def _best(text, table, only=None):
    best, score = None, 0
    for key, kws in table.items():
        if only and key not in only:
            continue
        sc = sum(len(normalize(k)) for k in kws if normalize(k) in text)
        if sc > score:
            best, score = key, sc
    return best


def find_crop(text):
    return _best(normalize(text), CROPS)


def _is_kw_negated(text: str, kw: str) -> bool:
    """Return True if kw in text is directly accompanied by negation words."""
    t = normalize(text)
    k = normalize(kw)
    if k not in t:
        return False
    # Check if keyword is followed by negation words (allowing optional light particles):
    post_pat = rf"(?:^|\s){re.escape(k)}\s*(?:ಏನೂ\s*|ಯಾವುದೂ\s*|ಕೂಡ\s*|ಅಷ್ಟಾಗಿ\s*|ಹೆಚ್ಚಾಗಿ\s*|ತುಂಬ\s*)?(?:ಬಂದಿಲ್ಲ|ಇಲ್ಲ|ವಿಲ್ಲ|ಆಗಿಲ್ಲ|ಕಂಡಿಲ್ಲ|ಕಾಣಿಸಿಲ್ಲ|ಇಲ್ಲವೇ|ಇಲ್ಲವೆ)(?:\s|$)"
    if re.search(post_pat, t):
        return True
    if re.search(rf"(?:^|\s){re.escape(k)}(?:ವಿಲ್ಲ|ವಿಲ್ಲವೇ|ವಿಲ್ಲವೆ)(?:\s|$)", t):
        return True
    # English/codemix: "no leaf folder", "not blast"
    pre_pat = rf"\b(?:no|not)\s+(?:a\s+)?{re.escape(k)}\b"
    if re.search(pre_pat, t):
        return True
    return False


def find_problem(text, crop=None):
    t = normalize(text)
    best, score = None, 0
    for key, kws in PROBLEMS.items():
        if crop is not None and (key not in KB or KB[key]["crop"] != crop):
            continue
        sc = sum(
            len(normalize(k))
            for k in kws
            if normalize(k) in t and not _is_kw_negated(t, k)
        )
        if sc > score:
            best, score = key, sc
    return best


def find_negated_problems(text, crop=None):
    """Return set of problems whose symptoms are explicitly negated in text."""
    t = normalize(text)
    negated = set()
    for key, kws in PROBLEMS.items():
        if crop is not None and (key not in KB or KB[key]["crop"] != crop):
            continue
        for k in kws:
            if normalize(k) in t and _is_kw_negated(t, k):
                negated.add(key)
    return negated


def is_new_issue(text: str) -> bool:
    """Return True if user explicitly mentions a different/another/new issue."""
    t = normalize(text)
    kn_patterns = [
        r"(?:^|\s)(?:ಬೇರೆ|ಇನ್ನೊಂದು|ಮತ್ತೊಂದು|ಹೊಸ)\s*(?:ಸಮಸ್ಯೆ|ರೋಗ|ಕೀಟ|ಹುಳು|ತೊಂದರೆ)(?:\s|$)",
        r"(?:^|\s)(?:ಬೇರೆ|ಇನ್ನೊಂದು|ಮತ್ತೊಂದು)\s+(?:ಇದೆ|ಆಗಿದೆ|ಕಾಣ್ತಾ\s*ಇದೆ)(?:\s|$)",
    ]
    for p in kn_patterns:
        if re.search(p, t):
            return True
    if re.search(r"\b(?:different|another|other|new)\s+(?:problem|issue|disease|pest)\b", t):
        return True
    return False


def find_stage(text):
    return _best(normalize(text), STAGES)


# Helpers for disease negation and unsupported issues
def is_disease_negated(text: str) -> bool:
    """Return True if disease/pest/rot is explicitly negated (not global negation)."""
    t = normalize(text)
    kn_patterns = [
        r"(?:ರೋಗ|ಕೊಳೆ|ಕೀಟ|ಹುಳು)\s*(?:ಏನೂ\s*|ಯಾವುದೂ\s*)?(?:ಬಂದಿಲ್ಲ|ಇಲ್ಲ|ವಿಲ್ಲ|ಆಗಿಲ್ಲ|ಇಲ್ಲವೇ|ಇಲ್ಲವೆ|ಕಂಡಿಲ್ಲ)",
        r"(?:ರೋಗವಿಲ್ಲ|ರೋಗವಿಲ್ಲವೇ)",
    ]
    for p in kn_patterns:
        if re.search(p, t):
            return True
    if re.search(r"\b(?:no|not)\s+(?:a\s+)?(?:disease|rot|pest)\b", t):
        return True
    return False


def is_low_yield(text: str) -> bool:
    """Return True if user asks about poor fruit setting, low yield, or yield improvement."""
    t = normalize(text)
    kn_patterns = [
        r"ಕಾಯಿ\s*(?:ತುಂಬ\s*|ಹೆಚ್ಚು\s*|ಸರಿಯಾಗಿ\s*)?(?:ಬಿಡ್ತಾ\s*ಇಲ್ಲ|ಬಿಡುತ್ತಿಲ್ಲ|ಕಟ್ಟುತ್ತಿಲ್ಲ|ಬರ್ತಾ\s*ಇಲ್ಲ|ಇಲ್ಲ|ಕಡಿಮೆ)",
        r"ಇಳುವರಿ\s*(?:ಕಡಿಮೆ|ಬರ್ತಾ\s*ಇಲ್ಲ|ಬರುತ್ತಿಲ್ಲ|ಹೆಚ್ಚಿಸ|ಇಂಪ್ರೂವ್)",
        r"\bಇಳುವರಿ\b",
        r"ಕಾಯಿ\s*ಕಡಿಮೆ",
        r"ಹೂ\s*(?:ಉದುರ|ಬಿಡ್ತಾ\s*ಇಲ್ಲ)",
    ]
    for p in kn_patterns:
        if re.search(p, t):
            return True
    if re.search(r"\b(?:low\s+yield|not\s+bearing|improve\s+yield|poor\s+yield)\b", t):
        return True
    return False


def usable_crops() -> list[str]:
    """Return list of crops that have usable, non-stub advisories in KB."""
    crops = []
    for adv in KB.values():
        c = adv.get("crop")
        if not c or c in crops or "_stub" in adv.get("id", ""):
            continue
        advice_texts = " ".join(adv.get("advice_kn", {}).get("default", []))
        if "ನಿಖರವಾದ ಸಲಹೆ ನಮ್ಮ ಡೇಟಾಬೇಸಿನಲ್ಲಿ ಇಲ್ಲ" in advice_texts:
            continue
        crops.append(c)
    return crops


def is_end_call_intent(text: str) -> bool:
    """Return True if user explicitly requests to end/hang up the call."""
    t = normalize(text)
    # Check negative end request (e.g. "don't hang up")
    neg_pats = [
        r"(?:ಕರೆ|ಕರೆಯನ್ನು|ಕಾಲ್|ಫೋನ್)?\s*(?:ಕಟ್\s*ಮಾಡಬೇಡಿ|ಕಟ್\s*ಮಾಡ್ಬೇಡಿ|ಮುಗಿಸಬೇಡಿ|ಕೊನೆಗೊಳಿಸಬೇಡಿ)",
        r"\b(?:don'?t|do\s+not)\s+(?:hang\s+up|end|disconnect)\b",
    ]
    for p in neg_pats:
        if re.search(p, t):
            return False

    # Explicit end requests
    explicit_pats = [
        r"(?:ಕರೆ|ಕರೆಯನ್ನು|ಕಾಲ್|ಫೋನ್)\s*(?:ಕಟ್\s*ಮಾಡಬಹುದು|ಕಟ್\s*ಮಾಡಿ|ಮುಗಿಸಿ|ಕೊನೆಗೊಳಿಸಿ|ಮುಗಿಸಬಹುದು)",
        r"(?:ಕಟ್\s*ಮಾಡಬಹುದು|ಕಟ್\s*ಮಾಡಿ|ಕರೆಯನ್ನು\s*ಮುಗಿಸಿ|ಕರೆ\s*ಮುಗಿಸಿ)",
        r"(?:ಇಷ್ಟೇ\s*ಸಾಕು|ಸಾಕು\s*ಧನ್ಯವಾದ|ಸಾಕು\s*ರೀ)",
        r"\b(?:end\s+the\s+call|hang\s+up|disconnect\s+the\s+call)\b",
    ]
    for p in explicit_pats:
        if re.search(p, t):
            return True

    # Standalone thank you / goodbye without a substantive question
    if any(k in t for k in ["ಧನ್ಯವಾದ", "ಧನ್ಯವಾದಗಳು", "ಸಾಕು", "thank you", "bye", "goodbye"]):
        crop = find_crop(t)
        prob = find_problem(t, crop=crop)
        question_words = ["ಏನು", "ಹೇಗೆ", "ಯಾವ", "ಔಷಧ", "ಪರಿಹಾರ", "ಬೇಕಿತ್ತು", "ತಿಳಿಸಿ", "ಕೊಡಿ", "ಹೇಳಿ"]
        has_question = any(w in t for w in question_words)
        if (crop or prob) and has_question:
            return False
        return True

    return False


def is_repeat_intent(text: str) -> tuple[bool, bool]:
    """Return (is_repeat, is_specific_advisory_repeat)."""
    t = normalize(text)
    # Check negative repeat (e.g. "don't repeat")
    neg_pats = [
        r"(?:ಮತ್ತೆ|ಇನ್ನೊಮ್ಮೆ|ಮತ್ತೊಮ್ಮೆ|ಪುನಃ)\s*(?:ಹೇಳಬೇಡಿ|ಹೇಳ್ಬೇಡಿ|ತಿಳಿಸಬೇಡಿ)",
        r"\b(?:don'?t|do\s+not)\s+repeat\b",
    ]
    for p in neg_pats:
        if re.search(p, t):
            return False, False

    is_specific_advisory = bool(
        re.search(r"(?:ಹಿಂದಿನ|ಹಳೆ|ಮೊದಲ)\s*(?:ಸಲಹೆ|ಮಾಹಿತಿ)", t)
        or re.search(r"\bprevious\s+(?:advice|advisory)\b", t)
    )

    rep_pats = [
        r"(?:ಮತ್ತೆ|ಇನ್ನೊಮ್ಮೆ|ಮತ್ತೊಮ್ಮೆ|ಪುನಃ)\s*(?:ಹೇಳಿ|ಹೇಳ್ತೀರಾ|ಹೇಳುತ್ತೀರಾ|ತಿಳಿಸಿ|ಹೇಳ್ರಿ|ಹೇಳು)",
        r"(?:ಅದನ್ನು|ಇದನ್ನು|ಸಲಹೆಯನ್ನು)\s*(?:ಮತ್ತೆ|ಇನ್ನೊಮ್ಮೆ|ಮತ್ತೊಮ್ಮೆ|ಪುನಃ)\s*(?:ಹೇಳಿ|ಹೇಳ್ತೀರಾ|ಹೇಳುತ್ತೀರಾ|ತಿಳಿಸಿ)",
        r"(?:ಮತ್ತೆ|ಇನ್ನೊಮ್ಮೆ|ಮತ್ತೊಮ್ಮೆ)\s+ಹೇಳಿ",
        r"ಸರಿಯಾಗಿ\s*ಕೇಳಿಸಲಿಲ್ಲ",
        r"\b(?:repeat|say\s+that\s+again|say\s+again|repeat\s+that)\b",
    ]
    for p in rep_pats:
        if re.search(p, t):
            return True, is_specific_advisory

    if is_specific_advisory and any(k in t for k in ["ಹೇಳಿ", "ತಿಳಿಸಿ", "repeat", "ಹೇಳ್ತೀರಾ", "ಹೇಳುತ್ತೀರಾ"]):
        return True, True

    return False, False


def is_capabilities_intent(text: str) -> bool:
    """Return True if user asks about capabilities, what crops/problems are supported."""
    t = normalize(text)
    cap_pats = [
        r"ಯಾವ\s*(?:ಬೆಳೆಗಳಿಗೆ|ಬೆಳೆಗೆ|ಬೆಳೆಗಳ|ಸಮಸ್ಯೆಗಳಿಗೆ|ರೋಗಗಳಿಗೆ)\s*(?:ಸಹಾಯ|ಸಲಹೆ|ಮಾಹಿತಿ)",
        r"(?:ಯಾವ\s*ಬೆಳೆ|ಯಾವ\s*ಯಾವ\s*ಬೆಳೆ)",
        r"(?:ಸಹಾಯ|ಸಲಹೆ|ಮಾಹಿತಿ)\s*(?:ಲಭ್ಯವಿದೆ|ಸಿಗುತ್ತದೆ|ಕೊಡುತ್ತೀರಿ|ಮಾಡಬಹುದು|ನೀಡುತ್ತೀರಿ)",
        r"(?:ನೀವು\s*)?ಏನು\s*(?:ಮಾಡಬಹುದು|ಸಹಾಯ\s*ಮಾಡಬಹುದು|ಮಾಡಲು\s*ಸಾಧ್ಯ)",
        r"\b(?:which\s+crops|what\s+crops|what\s+can\s+you\s+(?:do|help)|support(?:ed)?\s+crops)\b",
    ]
    for p in cap_pats:
        if re.search(p, t):
            return True
    return False


def chemical_allowed(adv: dict, stage) -> bool:
    c = adv.get("chemical") or {}
    if c.get("reviewed") is not True:
        return False
    if any(c.get(f) in (None, "") for f in CHEM_FIELDS):
        return False
    return stage not in adv.get("block_chemical_stages", [])


def keyterms():
    terms = []
    for kws in list(CROPS.values()) + list(PROBLEMS.values()):
        for k in kws:
            if any("\u0c80" <= ch <= "\u0cff" for ch in k) and " " not in k and k not in terms:
                terms.append(k)
    return terms


@dataclass
class Reply:
    sentences: list
    end: bool = False
    sms: str = None
    meta: dict = field(default_factory=dict)


LF_INTAKE_STEPS = [
    "symptoms",
    "live_larvae",
    "stage",
    "leaf_counts",
    "harvest_days",
    "nearby_mulberry",
    "recent_pesticides",
]


def _parse_intake_answer(step: str, raw_text: str):
    t = normalize(raw_text)
    is_unknown = any(k in t for k in ["ಗೊತ್ತಿಲ್ಲ", "ತಿಳಿದಿಲ್ಲ", "ನೋಡಿಲ್ಲ", "ಎಣಿಸಿಲ್ಲ", "dont know", "don't know", "not sure", "unknown", "ಏನೋ"])

    if step == "symptoms":
        if is_unknown:
            return "unknown"
        if any(k in t for k in ["ಹೌದು", "ಇದೆ", "ಕಾಣಿಸುತ್ತಿದೆ", "ಕಾಣ್ತಾ ಇದೆ", "yes", "true"]):
            return True
        if any(k in t for k in ["ಇಲ್ಲ", "ಕಾಣುತ್ತಿಲ್ಲ", "ಕಾಣ್ತಿಲ್ಲ", "no", "false"]):
            return False
        return "unknown"

    elif step == "live_larvae":
        if is_unknown:
            return "unknown"
        if any(k in t for k in ["ಹೌದು", "ಇವೆ", "ಇದೆ", "ಕಂಡಿವೆ", "ಕಂಡಿದೆ", "yes", "live"]):
            return True
        if any(k in t for k in ["ಇಲ್ಲ", "ಕಂಡಿಲ್ಲ", "ಸತ್ತಿವೆ", "no", "dead"]):
            return False
        return "unknown"

    elif step == "stage":
        if is_unknown:
            return "unknown"
        st = find_stage(t)
        if st:
            return st
        if any(k in t for k in ["ಕವಲು", "tillering", "vegetative"]):
            return "tillering"
        return "unknown"

    elif step == "leaf_counts":
        if is_unknown:
            return "unknown"
        return raw_text.strip()

    elif step == "harvest_days":
        if is_unknown:
            return "unknown"
        m = re.search(r"(\d+)", raw_text)
        if m:
            return int(m.group(1))
        kn_digits = {"೦": 0, "೧": 1, "೨": 2, "೩": 3, "೪": 4, "೫": 5, "೬": 6, "೭": 7, "೮": 8, "೯": 9}
        kn_num_str = "".join([str(kn_digits[c]) for c in raw_text if c in kn_digits])
        if kn_num_str:
            return int(kn_num_str)
        kn_words = {"ಹತ್ತು": 10, "ಇಪ್ಪತ್ತು": 20, "ಮೂವತ್ತು": 30, "ನಲವತ್ತು": 40, "ಐವತ್ತು": 50, "ಅರವತ್ತು": 60, "ತಿಂಗಳು": 30}
        for word, val in kn_words.items():
            if word in t:
                return val
        return raw_text.strip()

    elif step == "nearby_mulberry":
        if is_unknown:
            return "unknown"
        if any(k in t for k in ["ಹೌದು", "ಇದೆ", "ಸಮೀಪದಲ್ಲಿದೆ", "yes", "true"]):
            return True
        if any(k in t for k in ["ಇಲ್ಲ", "ಯಾವುದೂ ಇಲ್ಲ", "ಯಾವುದಿಲ್ಲ", "no", "false"]):
            return False
        return "unknown"

    elif step == "recent_pesticides":
        if is_unknown or any(k in t for k in ["ಹೆಸರು ಗೊತ್ತಿಲ್ಲ", "unknown"]):
            return "unknown_product"
        if any(k in t for k in ["ಇಲ್ಲ", "ಯಾವುದೂ ಇಲ್ಲ", "ಯಾವುದಿಲ್ಲ", "ಮಾಡಲಿಲ್ಲ", "ಸಿಂಪಡಿಸಿಲ್ಲ", "no"]):
            return False
        return raw_text.strip()


class Session:
    def __init__(self, escalation_number="1800-180-1551"):
        self.crop = self.problem = self.stage = None
        self.asks = {"crop": 0, "problem": 0, "stage": 0}
        self.advised = False
        self.last = None
        self.last_advisory = None
        self.esc = escalation_number
        self.leaf_folder_intake = {
            "symptoms": None,
            "live_larvae": None,
            "stage": None,
            "leaf_counts": None,
            "harvest_days": None,
            "nearby_mulberry": None,
            "recent_pesticides": None,
        }
        self.intake_step = None
        self.intake_completed = False

    def start_leaf_folder_intake(self) -> Reply:
        self.crop = "paddy"
        self.problem = "paddy_leaf_folder"
        self.intake_step = LF_INTAKE_STEPS[0]
        self.intake_completed = False
        return self._remember(Reply(
            T[f"lf_intake_{self.intake_step}"],
            meta={
                "state": f"ask_intake_{self.intake_step}",
                "step": self.intake_step,
                "crop": "paddy",
                "problem": "paddy_leaf_folder",
            }
        ))

    def _handle_leaf_folder_intake_step(self, t: str, raw_text: str) -> Reply:
        current_step = self.intake_step
        ans = _parse_intake_answer(current_step, raw_text)
        self.leaf_folder_intake[current_step] = ans
        if current_step == "stage" and ans in ("seedling", "tillering", "flowering"):
            self.stage = ans

        idx = LF_INTAKE_STEPS.index(current_step)
        if idx + 1 < len(LF_INTAKE_STEPS):
            next_step = LF_INTAKE_STEPS[idx + 1]
            self.intake_step = next_step
            return self._remember(Reply(
                T[f"lf_intake_{next_step}"],
                meta={
                    "state": f"ask_intake_{next_step}",
                    "step": next_step,
                    "crop": "paddy",
                    "problem": "paddy_leaf_folder",
                    "intake": dict(self.leaf_folder_intake),
                }
            ))
        else:
            self.intake_step = None
            self.intake_completed = True
            sentences = list(T["lf_intake_complete_ack"])
            if self.leaf_folder_intake.get("nearby_mulberry") is True:
                sentences.extend(T["lf_mulberry_hazard"])
            h_days = self.leaf_folder_intake.get("harvest_days")
            if isinstance(h_days, (int, float)) and h_days < 47:
                sentences.extend(T["lf_harvest_hazard"])
            sentences.extend(T["lf_safety_ppe_reentry"])
            sentences.extend(T["lf_expert_gate_notice"])
            sentences.extend(T["advisory_followup"])
            return self._remember(Reply(
                sentences,
                meta={
                    "state": "leaf_folder_intake_complete",
                    "intake": dict(self.leaf_folder_intake),
                    "safety": "chemical_unreviewed",
                    "reviewed": False,
                    "crop": "paddy",
                    "problem": "paddy_leaf_folder",
                }
            ))

    def _reset_crop(self, new_crop):
        self.crop = new_crop
        self.problem = None
        self.stage = None
        self.advised = False
        self.last_advisory = None
        self.asks = {"crop": 0, "problem": 0, "stage": 0}

    def _ask(self, slot):
        self.asks[slot] += 1
        if self.asks[slot] > 2:
            return self._escalate("too_many_clarifications")
        return self._remember(Reply(T["ask_" + slot], meta={"state": "ask_" + slot}))

    def _escalate(self, why):
        return Reply(T["escalate"] + T["bye"], end=True,
                     sms=f"ಕೃಷಿ ಮಿತ್ರ: ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ. {self.esc}",
                     meta={"state": "escalated", "why": why, "safety": "escalated"})

    def _remember(self, r):
        if not r.meta.get("repeated"):
            self.last = r
        return r

    def respond(self, text: str) -> Reply:
        t = normalize(text)
        prev_crop = self.crop
        prev_problem = self.problem
        prev_stage = self.stage
        prev_advised = self.advised

        # 1. Global Intent A: End Call
        # Explicit call-ending requests must work in every dialogue state
        if is_end_call_intent(t):
            return Reply(T["bye"], end=True, meta={"state": "bye"})

        # 2. Global Intent C: Repeat
        # Supports natural variations, pending question repetition, and specific advisory replay
        is_rep, is_spec_adv = is_repeat_intent(t)
        if is_rep:
            if is_spec_adv:
                if self.last_advisory:
                    return self._remember(Reply(
                        self.last_advisory.sentences,
                        sms=None,
                        meta={**self.last_advisory.meta, "repeated": True}
                    ))
                else:
                    return self._remember(Reply(
                        T["no_previous_advisory"],
                        meta={"state": "no_previous_advisory"}
                    ))
            # General repeat:
            # Repeats the latest relevant bot response, including capabilities or unsupported-yield
            # guidance, rather than an older advisory.
            if self.last:
                return self._remember(Reply(
                    self.last.sentences,
                    sms=None,
                    meta={**self.last.meta, "repeated": True}
                ))
            if self.last_advisory:
                return self._remember(Reply(
                    self.last_advisory.sentences,
                    sms=None,
                    meta={**self.last_advisory.meta, "repeated": True}
                ))
            return self._remember(Reply(T["reprompt"], meta={"state": "reprompt"}))

        # 3. Global Intent B: Capabilities / Supported Crops
        # Evaluated before slot filling and generic advisory-followup handling.
        # Do not swallow if user specifies both crop and problem (e.g. "ಭತ್ತದಲ್ಲಿ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ, ಏನು ಮಾಡಬಹುದು?")
        crop_tentative = find_crop(t)
        prob_tentative = find_problem(t, crop=crop_tentative or self.crop)
        has_concrete_issue = bool((crop_tentative or self.crop) and prob_tentative)
        if is_capabilities_intent(t) and not has_concrete_issue:
            active_crops_kn = [CROP_KN.get(c, c) for c in usable_crops()]
            crops_str = " ಮತ್ತು ".join([", ".join(active_crops_kn[:-1]), active_crops_kn[-1]]) if len(active_crops_kn) > 1 else "".join(active_crops_kn)
            sentences = [
                T["capabilities_overview"][0].format(crops=crops_str),
                T["capabilities_overview"][1],
                T["capabilities_overview"][2],
            ]
            return self._remember(Reply(
                sentences,
                meta={"state": "capabilities", "crop": self.crop, "problem": self.problem}
            ))

        # Check active leaf-folder intake workflow
        if self.intake_step is not None:
            return self._handle_leaf_folder_intake_step(t, text)

        # 4. Check explicit new issue (Bug B)
        new_issue = is_new_issue(t)
        if new_issue:
            self.problem = None
            self.stage = None
            self.advised = False
            self.last_advisory = None
            self.asks["problem"] = 0
            self.asks["stage"] = 0

        # 4. Check disease negation (Bug A)
        neg_probs = find_negated_problems(t, crop=self.crop)
        if is_disease_negated(t) or neg_probs:
            # If current problem was negated or any disease was negated, clear stale diagnosis
            if is_disease_negated(t) or (self.problem and self.problem in neg_probs):
                self.problem = None
                self.advised = False
                self.last_advisory = None

        # 5. Check unsupported low-yield question
        if is_low_yield(t):
            self.problem = None
            self.advised = False
            self.last_advisory = None
            c = find_crop(t)
            if c:
                if self.crop and self.crop != c:
                    self._reset_crop(c)
                else:
                    self.crop = c
            crop_kn = CROP_KN.get(self.crop)
            prefix = f"{crop_kn} ಬೆಳೆಯಲ್ಲಿ " if crop_kn else "ಬೆಳೆಯಲ್ಲಿ "
            sentences = [
                f"{prefix}{T['unsupported_yield_body'][0]}",
                T["unsupported_yield_body"][1],
                T["unsupported_yield_body"][2],
            ]
            sms_crop = crop_kn or "ಬೆಳೆ"
            return self._remember(Reply(
                sentences,
                sms=f"ಕೃಷಿ ಮಿತ್ರ: {sms_crop} ಇಳುವರಿ ಸಮಸ್ಯೆಗೆ ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ. {self.esc}",
                meta={"state": "unsupported_yield", "crop": self.crop}
            ))

        # 6. Extract crop, problem, stage
        crop = find_crop(t)
        if crop:
            self.asks["crop"] = 0
            if self.crop and self.crop != crop:
                self._reset_crop(crop)
            else:
                self.crop = crop

        prob = find_problem(t, crop=self.crop)

        # Conservative guard: if crop is unknown, generic rot must not silently infer arecanut
        if self.crop is None and crop is None:
            if prob == "arecanut_koleroga" and not any(k in t for k in ["ಅಡಿಕೆ", "ಮಹಾಲಿ", "adike", "areca"]):
                prob = None

        # A negated diagnosis must not be restored from the same negated phrase
        if prob and prob in neg_probs:
            prob = None

        # Check if farmer stated a different supported problem on the same crop
        is_diff_problem = bool(prob and prev_problem and prob != prev_problem)

        if is_diff_problem:
            # Clear previous problem's stage, advisory-completion state, stale repeat reference, and reset clarification counters
            self.problem = prob
            self.stage = None
            self.advised = False
            self.last_advisory = None
            self.asks["problem"] = 0
            self.asks["stage"] = 0
        elif prob:
            self.problem = prob
            self.asks["problem"] = 0
            if not self.crop:
                self.crop = KB[prob]["crop"]
                self.asks["crop"] = 0

        st = find_stage(t)
        if st:
            self.stage = st
            self.asks["stage"] = 0

        # 7. Check generic follow-up or repeating same problem when already advised
        # Repeating the same problem must not automatically replay the full advisory
        # Generic follow-ups still offer follow-up options
        if self.advised and not is_diff_problem and not st and not new_issue:
            if self.problem == "paddy_leaf_folder" and any(k in t for k in ["ಔಷಧ", "ಔಷಧಿ", "ಸಿಂಪಡಿಸ", "ರಾಸಾಯನಿಕ", "chemical", "spray", "pesticide"]):
                return self.start_leaf_folder_intake()
            return self._remember(Reply(
                T["followup_options"],
                meta={"state": "followup_options", "crop": self.crop}
            ))

        # 8. Slot clarification or advisory
        if not self.crop:
            return self._ask("crop")
        if not self.problem:
            return self._ask("problem")
        if self.problem == "paddy_leaf_folder" and any(k in t for k in ["ಔಷಧ", "ಔಷಧಿ", "ಸಿಂಪಡಿಸ", "ರಾಸಾಯನಿಕ", "chemical", "spray", "pesticide"]):
            return self.start_leaf_folder_intake()
        adv = KB[self.problem]
        if adv["needs_stage"] and not self.stage:
            return self._ask("stage")
        return self._advise(adv)

    def _advise(self, adv):
        stage_key = self.stage if self.stage in adv["advice_kn"] else "default"
        s = [f"ನೀವು {CROP_KN[adv['crop']]} ಬೆಳೆಯ {adv['name_kn']} ಬಗ್ಗೆ ಕೇಳುತ್ತಿದ್ದೀರಿ ಎಂದು ಅರ್ಥವಾಯಿತು."]
        s += adv["advice_kn"][stage_key]
        if self.stage in adv.get("block_chemical_stages", []):
            safety = "chemical_blocked_stage"
        elif chemical_allowed(adv, self.stage):
            c = adv["chemical"]
            s += [f"ಶಿಫಾರಸು ಮಾಡಿದ ಔಷಧ {c['product']}. ಪ್ರಮಾಣ {c['dose']}. ನೀರಿನ ಪ್ರಮಾಣ {c['water']}.",
                  f"ಕೊಯ್ಲಿಗೆ ಮೊದಲು {c['preharvest_days']} ದಿನ ಕಾಯಿರಿ."] + T["safety"]
            safety = "chemical_approved"
        else:
            s += T["no_chem"]
            safety = "chemical_unreviewed"
        # Offer repeat or another question; DO NOT append goodbye while call is open
        s += T["advisory_followup"]
        self.advised = True
        sms = (f"ಕೃಷಿ ಮಿತ್ರ ಸಲಹೆ\nಬೆಳೆ: {CROP_KN[adv['crop']]}\nಸಮಸ್ಯೆ: {adv['name_kn']}\n"
               + " ".join(adv["advice_kn"][stage_key]))
        reply = Reply(s, sms=sms, meta={"state": "advised", "advisory_id": adv["id"], "safety": safety,
                                         "crop": self.crop, "stage": self.stage})
        self.last_advisory = reply
        return self._remember(reply)
