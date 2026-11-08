import json, pathlib, re, unicodedata
from dataclasses import dataclass, field
from .diseases import (match_disease, match_symptoms, rank_disease_candidates,
                       registry_for_kb)

KB_PATH = pathlib.Path(__file__).with_name("kb.json")
KB = {a["id"]: a for a in json.loads(KB_PATH.read_text(encoding="utf-8"))["advisories"]}
DISEASE_REGISTRY = registry_for_kb(KB)

CROPS = {
    "paddy": ["ಭತ್ತ", "ಬತ್ತ", "ಅಕ್ಕಿ", "ಗದ್ದೆ", "paddy", "rice", "bhatta"],
    "arecanut": ["ಅಡಿಕೆ", "ಅಡಕೆ", "ಸುಪಾರಿ", "arecanut", "areca", "adike"],
    "coconut": ["ತೆಂಗು", "ತೆಂಗಿನ", "ನಾರಿಕೇಳ", "coconut", "thengu"],
    "sugarcane": ["ಕಬ್ಬು", "ಕಬ್ಬಿನ", "ಕಬ್ಬಿಗೆ", "sugarcane", "sugar cane"],  # NEEDS NATIVE REVIEW
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
    disease.id: list(disease.aliases + disease.confirmation_aliases)
    for disease in DISEASE_REGISTRY
    if disease.has_advisory
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
    # REVIEW: Human review of Kannada wording for initial greeting with privacy notice
    "greeting": ["ನಮಸ್ಕಾರ. ಇದು ಕೃಷಿ ಮಿತ್ರ ಸೇವೆ.", "ಧ್ವನಿಯನ್ನು ರೆಕಾರ್ಡ್ ಮಾಡುವುದಿಲ್ಲ, ಆದರೆ ಸಂಭಾಷಣೆಯ ಪಠ್ಯವನ್ನು ದಾಖಲಿಸಿಕೊಳ್ಳಲಾಗುತ್ತದೆ.", "ನಿಮ್ಮ ಬೆಳೆ ಮತ್ತು ಸಮಸ್ಯೆಯನ್ನು ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ."],
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
    # REVIEW: Human review of Kannada wording when crop is unsupported in KB
    "unsupported_crop": [
        "ಕ್ಷಮಿಸಿ, {crop} ಬೆಳೆಗೆ ಪರಿಹಾರ ಅಥವಾ ಚಿಕಿತ್ಸಾ ಸಲಹೆ ಸದ್ಯಕ್ಕೆ ನನ್ನಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
        "ಹೆಚ್ಚಿನ ಮಾಹಿತಿಗಾಗಿ ದಯವಿಟ್ಟು ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿ ಅಥವಾ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರವನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "ಪ್ರಸ್ತುತ ನಮ್ಮ ಬೆಂಬಲ ಕೇವಲ {supported_crops} ಬೆಳೆಗಳಿಗೆ ಮಾತ್ರ ಸೀಮಿತವಾಗಿದೆ. ನೀವು ಇವುಗಳಲ್ಲಿ ಯಾವುದಾದರೂ ಬೆಳೆಯ ಬಗ್ಗೆ ಕೇಳಲು ಬಯಸುತ್ತೀರಾ?",
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


def _is_yes_answer(text: str) -> bool:
    return bool(re.search(r"(?:^|\s)(?:ಹೌದು|ಹೌದ್ರಿ|ಹೂಂ|ಸರಿ)(?=\s|$)", text)) or bool(
        re.search(r"\b(?:yes|haudu|correct)\b", text)
    )


def _is_no_answer(text: str) -> bool:
    return bool(re.search(r"(?:^|\s)(?:ಇಲ್ಲ|ಅಲ್ಲ|ಬೇಡ)(?=\s|$)", text)) or bool(
        re.search(r"\b(?:no|illa|wrong)\b", text)
    )


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


def find_crop_correction(text):
    """Return a newly named crop after an explicit negated prior crop."""
    t = normalize(text)
    for marker in re.finditer(r"(?:^|\s)(?:ಅಲ್ಲ|ಇಲ್ಲ|ವಲ್ಲ|not)(?=\s|$)", t):
        before = find_crop(t[:marker.start()])
        after = find_crop(t[marker.end():])
        if before and after and before != after:
            return after
    return None


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
    # An established crop is authoritative. Session.respond handles explicit
    # crop changes before this lookup, so disease matching cannot cross crops.
    match_crop = crop if crop is not None else find_crop(text)
    result = match_disease(text, match_crop, DISEASE_REGISTRY,
                           crop_explicit=bool(match_crop))
    disease_id = result.single_id
    if result.method != "exact" or result.needs_confirm or not disease_id:
        return None
    return disease_id if next(d for d in DISEASE_REGISTRY if d.id == disease_id).has_advisory else None


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
    t = normalize(text)
    if re.search(r"ಹೂ\s*ಬಿಡುವ\s*ಹಂತ", t):
        return "flowering"
    return _best(t, STAGES)


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
        or re.search(r"(?:ಭತ್ತದ|paddy)\s*ಸಲಹೆ", t)
        or re.search(r"\bprevious\s+(?:advice|advisory)\b", t)
    )

    rep_pats = [
        r"(?:ಮತ್ತೆ|ಇನ್ನೊಮ್ಮೆ|ಮತ್ತೊಮ್ಮೆ|ಪುನಃ)\s*(?:ಹೇಳಿ|ಹೇಳ್ತೀರಾ|ಹೇಳುತ್ತೀರಾ|ತಿಳಿಸಿ|ಹೇಳ್ರಿ|ಹೇಳು)",
        r"(?:ಅದನ್ನು|ಇದನ್ನು|ಸಲಹೆಯನ್ನು)\s*(?:ಮತ್ತೆ|ಇನ್ನೊಮ್ಮೆ|ಮತ್ತೊಮ್ಮೆ|ಪುನಃ)\s*(?:ಹೇಳಿ|ಹೇಳ್ತೀರಾ|ಹೇಳುತ್ತೀರಾ|ತಿಳಿಸಿ)",
        r"ಆ\s*ಸಲಹೆಯನ್ನು\s*(?:ಮತ್ತೆ|ಇನ್ನೊಮ್ಮೆ|ಮತ್ತೊಮ್ಮೆ|ಪುನಃ)?\s*(?:ಹೇಳಿ|ಕೇಳಬೇಕು|ತಿಳಿಸಿ)",
        r"(?:ಭತ್ತದ|paddy)\s*(?:ಸಲಹೆ|ಸಲಹೆಯನ್ನು)\s*(?:ಮತ್ತೆ|ಇನ್ನೊಮ್ಮೆ|ಮತ್ತೊಮ್ಮೆ|ಪುನಃ)\s*(?:ಕೊಡಿ|ಹೇಳಿ|ಕೇಳಬೇಕು)",
        r"ಹಿಂದಿನ\s*ಸಲಹೆಯನ್ನು\s*(?:ಮತ್ತೆ\s*)?ಕೇಳಬೇಕು",
        r"ಹಿಂದಿನ\s*ಸಲಹೆ\s*ಬಗ್ಗೆ\s*ಮತ್ತೆ",
        r"ಅದಕ್ಕೆ\s*ಪರಿಹಾರ\s*ಏನು\s*ಇದೆ",
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
    disease_aliases = [alias for disease in DISEASE_REGISTRY for alias in disease.aliases]
    for kws in list(CROPS.values()) + [disease_aliases]:
        for k in kws:
            if any("\u0c80" <= ch <= "\u0cff" for ch in k) and " " not in k and k not in terms:
                terms.append(k)
    return terms[:200]


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
        self.active_crop = None
        self.active_problem = None
        self.stage = None
        self.pending_question = None
        self.pending_question_kind = None
        self.pending_candidates = ()
        self.pending_yes_candidates = ()
        self.asked_distinguishing_symptoms = set()
        self.asked_questions = set()
        self.confirmation_pending = False
        self.advisory_available = None
        self.referral_given = False
        self.asks = {"crop": 0, "problem": 0, "stage": 0}
        self.advised = False
        self.last = None
        self.last_advisory = None
        self.pending_match_method = None
        self.esc = escalation_number
        self.conversation_started = False
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

    @property
    def crop(self):
        return self.active_crop

    @crop.setter
    def crop(self, value):
        self.active_crop = value

    @property
    def problem(self):
        return self.active_problem

    @problem.setter
    def problem(self, value):
        self.active_problem = value

    @property
    def pending_disease_ids(self):
        return self.pending_candidates

    @pending_disease_ids.setter
    def pending_disease_ids(self, value):
        self.pending_candidates = tuple(value or ())

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
        active = next((d for d in DISEASE_REGISTRY if d.id == self.problem), None)
        if active and active.crop != new_crop:
            self.problem = None
            self.advisory_available = None
            self.referral_given = False
            self.advised = False
            self.last_advisory = None
        old_candidates = set(self.pending_candidates)
        compatible = tuple(
            d.id for d in DISEASE_REGISTRY
            if d.id in self.pending_candidates and d.crop == new_crop
        )
        self.pending_disease_ids = compatible
        if set(compatible) != old_candidates:
            self.asked_distinguishing_symptoms.clear()
        if not compatible:
            self.pending_match_method = None
            self.pending_yes_candidates = ()
            self.confirmation_pending = False
            self.pending_question = None
            self.pending_question_kind = None
        self.stage = None
        self.asks["crop"] = 0
        self.asks["stage"] = 0

    def _ask(self, slot):
        question = T["ask_" + slot][0]
        if question in self.asked_questions:
            return self._escalate("clarification_already_asked")
        self.asks[slot] += 1
        if self.asks[slot] > 2:
            return self._escalate("too_many_clarifications")
        self.confirmation_pending = False
        self.pending_question_kind = slot
        return self._remember(Reply(T["ask_" + slot], meta={"state": "ask_" + slot}))

    def _ask_disease_confirmation(self, diseases):
        candidate_ids = tuple(d.id for d in diseases)
        if set(candidate_ids) != set(self.pending_disease_ids):
            self.asked_distinguishing_symptoms.clear()
        self.pending_disease_ids = candidate_ids
        self.pending_yes_candidates = ()
        self.confirmation_pending = True
        self.pending_question_kind = "candidate_selection"
        names = " / ".join(d.name_kn for d in diseases)
        if self.pending_match_method == "weak" and len(diseases) == 1:
            disease = diseases[0]
            if disease.id == "arecanut_koleroga":
                question = "ನೀವು ಅಡಿಕೆ ಬೆಳೆಯ ಕೊಳೆ ರೋಗ ಬಗ್ಗೆ ಕೇಳುತ್ತಿದ್ದೀರಾ? ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
            elif disease.id == "coconut_rhino_beetle":
                question = "ನೀವು ತೆಂಗಿನ ಮರದಲ್ಲಿ ದುಂಬಿ ಸಮಸ್ಯೆ ಬಗ್ಗೆ ಹೇಳುತ್ತಿದ್ದೀರಾ? ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
            elif disease.id == "coconut_button_shedding":
                question = "ನೀವು ತೆಂಗಿನ ಕಾಯಿಗಳು ಉದುರುವ ಸಮಸ್ಯೆ ಬಗ್ಗೆ ಹೇಳುತ್ತಿದ್ದೀರಾ? ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
            else:
                question = f"ನೀವು {names} ಬಗ್ಗೆ ಕೇಳುತ್ತಿದ್ದೀರಾ? ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
        elif len(diseases) >= 3:
            return self._ask_disambiguating_symptom(diseases)
        elif len(diseases) == 2:
            question = f"ಇವುಗಳಲ್ಲಿ ಯಾವುದು ನಿಮ್ಮ ಬೆಳೆಯ ಸಮಸ್ಯೆ: {names}?"
        else:
            question = f"ನೀವು ಹೇಳಿದ್ದು {names} ಆಗಿದೆಯೇ? ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
        if question == self.pending_question or question in self.asked_questions:
            return self._ask_disambiguating_symptom(diseases)
        return self._remember(Reply(
            [question],
            meta={"state": "confirm_disease", "candidate_ids": [d.id for d in diseases],
                  "match_method": self.pending_match_method},
        ))

    def _ask_disambiguating_symptom(self, diseases):
        questions = {
            "yellowing": "ಎಲೆಗಳು ಹಳದಿಯಾಗಿವೆಯೇ?",
            "leaf_spots": "ಎಲೆಗಳಲ್ಲಿ ಚುಕ್ಕೆಗಳಿವೆಯೇ?",
            "rotting": "ಕಾಯಿ ಅಥವಾ ಬುಡ ಕೊಳೆಯುತ್ತಿದೆಯೇ?",
            "nut_fall": "ಕಾಯಿಗಳು ಉದುರುತ್ತಿವೆಯೇ?",
            "drying": "ಎಲೆಗಳು ಒಣಗುತ್ತಿವೆಯೇ?",
            "oozing": "ಕಾಂಡದಿಂದ ರಸ ಸೋರುತ್ತಿದೆಯೇ?",
            "wilting": "ಗಿಡ ಬಾಡುತ್ತಿದೆಯೇ?",
            "grain_damage": "ಕಾಳುಗಳಿಗೆ ಹಾನಿಯಾಗಿದೆಯೇ?",
            "stunted": "ಗಿಡದ ಬೆಳವಣಿಗೆ ಕುಂಠಿತವಾಗಿದೆಯೇ?",
            "flower": "ಹೂಗೊಂಚಲು ಒಣಗಿದೆಯೇ?",
            "crown": "ಮರದ ಮೊಗ್ಗು ಕೊಳೆಯುತ್ತಿದೆಯೇ?",
        }
        symptom_id = self._distinguishing_symptom_id(
            diseases,
            exclude=self.asked_distinguishing_symptoms | {
                sid for sid, question in questions.items() if question in self.asked_questions
            },
        )
        if symptom_id:
            self.asked_distinguishing_symptoms.add(symptom_id)
            question = questions[symptom_id]
            self.pending_yes_candidates = tuple(
                d.id for d in diseases if symptom_id in d.symptom_ids
            )
        else:
            fallbacks = (
                "ಎಲೆ, ಕಾಯಿ ಅಥವಾ ಕಾಂಡ—ಯಾವ ಭಾಗದಲ್ಲಿ ಹೆಚ್ಚು ತೊಂದರೆ ಇದೆ?",
                "ಎಲೆ ಹಳದಿಯಾಗಿದೆಯೇ, ಚುಕ್ಕೆಗಳಿವೆಯೇ, ಅಥವಾ ಕಾಯಿ ಉದುರುತ್ತಿದೆಯೇ?",
            )
            question = next((q for q in fallbacks if q not in self.asked_questions), None)
            if question is None:
                return self._escalate("clarification_already_asked")
            self.pending_yes_candidates = tuple(d.id for d in diseases)
        self.pending_disease_ids = tuple(d.id for d in diseases)
        self.confirmation_pending = True
        self.pending_question_kind = "candidate_disambiguation"
        return self._remember(Reply(
            [question],
            meta={"state": "clarify_disease_symptom",
                  "candidate_ids": list(self.pending_disease_ids),
                  "distinguishing_symptom": symptom_id},
        ))

    @staticmethod
    def _distinguishing_symptom_id(diseases, exclude=()):
        symptom_ids = list(dict.fromkeys(
            symptom_id for disease in diseases for symptom_id in disease.symptom_ids
        ))
        separating = [
            (abs(len(diseases) / 2 - sum(s in d.symptom_ids for d in diseases)), s)
            for s in symptom_ids
            if 0 < sum(s in d.symptom_ids for d in diseases) < len(diseases)
            and s not in exclude
        ]
        return min(separating)[1] if separating else None

    @staticmethod
    def _distinguishing_symptom_question(diseases):
        symptom_questions = {
            "yellowing": "ಎಲೆಗಳು ಹಳದಿಯಾಗಿವೆಯೇ?",
            "leaf_spots": "ಎಲೆಗಳಲ್ಲಿ ಚುಕ್ಕೆಗಳಿವೆಯೇ?",
            "rotting": "ಕಾಯಿ ಅಥವಾ ಬುಡ ಕೊಳೆಯುತ್ತಿದೆಯೇ?",
            "nut_fall": "ಕಾಯಿಗಳು ಉದುರುತ್ತಿವೆಯೇ?",
            "drying": "ಎಲೆಗಳು ಒಣಗುತ್ತಿವೆಯೇ?",
            "oozing": "ಕಾಂಡದಿಂದ ರಸ ಸೋರುತ್ತಿದೆಯೇ?",
            "wilting": "ಗಿಡ ಬಾಡುತ್ತಿದೆಯೇ?",
            "grain_damage": "ಕಾಳುಗಳಿಗೆ ಹಾನಿಯಾಗಿದೆಯೇ?",
            "stunted": "ಗಿಡದ ಬೆಳವಣಿಗೆ ಕುಂಠಿತವಾಗಿದೆಯೇ?",
            "flower": "ಹೂಗೊಂಚಲು ಒಣಗಿದೆಯೇ?",
            "crown": "ಮರದ ಮೊಗ್ಗು ಕೊಳೆಯುತ್ತಿದೆಯೇ?",
        }
        symptom_id = Session._distinguishing_symptom_id(diseases)
        if symptom_id in symptom_questions:
            return symptom_questions[symptom_id]
        return "ಎಲೆ, ಕಾಯಿ ಅಥವಾ ಕಾಂಡ—ಯಾವ ಭಾಗದಲ್ಲಿ ಹೆಚ್ಚು ತೊಂದರೆ ಇದೆ?"

    def _ask_symptoms(self, progress=False):
        prompts = {
            "paddy": "ಎಲೆ ಹಳದಿಯಾಗಿದೆಯೇ, ಚುಕ್ಕೆಗಳಿವೆಯೇ, ಅಥವಾ ಕಾಳಿಗೆ ತೊಂದರೆಯಿದೆಯೇ?",
            "coconut": "ಎಲೆ ಹಳದಿಯಾಗಿದೆಯೇ, ಕಾಯಿ ಉದುರುತ್ತಿವೆಯೇ, ಅಥವಾ ಮೊಗ್ಗು ಕೊಳೆಯುತ್ತಿದೆಯೇ?",
            "arecanut": "ಕಾಯಿ ಕೊಳೆದು ಉದುರುತ್ತಿದೆಯೇ, ಎಲೆ ಹಳದಿಯಾಗಿದೆಯೇ, ಅಥವಾ ಕಾಂಡದ ಬುಡ ಕೊಳೆಯುತ್ತಿದೆಯೇ?",
        }
        if progress:
            self.asks["problem"] = 0
        else:
            self.asks["problem"] += 1
            if self.asks["problem"] > 2:
                return self._escalate("too_many_clarifications")
        self.pending_disease_ids = ()
        self.pending_yes_candidates = ()
        self.asked_distinguishing_symptoms.clear()
        self.pending_match_method = None
        self.confirmation_pending = False
        self.pending_question_kind = "symptoms"
        prompt = prompts.get(self.crop, T["ask_problem"][0])
        if prompt in self.asked_questions:
            alternatives = {
                "paddy": "ಎಲೆಗಳಲ್ಲೇ ಸಮಸ್ಯೆಯೇ, ಅಥವಾ ತೆನೆ ಮತ್ತು ಕಾಳಿನಲ್ಲೂ ತೊಂದರೆಯಿದೆಯೇ?",
                "coconut": "ಬುಡದಲ್ಲಿ ರಸ ಸೋರುತ್ತಿದೆಯೇ, ಅಥವಾ ಕಾಯಿಗಳು ಉದುರುತ್ತಿವೆಯೇ?",
                "arecanut": "ಕಾಯಿಯಲ್ಲಿ ಕೊಳೆ ಇದೆಯೇ, ಅಥವಾ ಕಾಂಡದ ಬುಡದಲ್ಲಿ ತೊಂದರೆಯೇ?",
            }
            prompt = alternatives.get(self.crop, "ಎಲೆ, ಕಾಯಿ ಅಥವಾ ಕಾಂಡದಲ್ಲಿ ಯಾವುದು ಹೆಚ್ಚು ಬಾಧಿತವಾಗಿದೆ?")
            if prompt in self.asked_questions:
                return self._escalate("clarification_already_asked")
        return self._remember(Reply([prompt],
                                    meta={"state": "ask_problem", "symptom_prompt": True,
                                          "crop": self.crop}))

    def _unavailable_disease(self, disease):
        if self.problem != disease.id:
            self.referral_given = False
            self.stage = None
            self.advised = False
            self.last_advisory = None
        self.crop = disease.crop
        self.problem = disease.id
        self.advisory_available = False
        self.advised = False
        self.pending_disease_ids = ()
        self.pending_yes_candidates = ()
        self.confirmation_pending = False
        self.pending_question_kind = "another_problem"
        if self.referral_given:
            return self._ask_another_problem()
        self.referral_given = True
        return self._remember(Reply(
            [f"ನೀವು ಹೇಳಿದ್ದು {disease.name_kn} ಎಂದು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ.",
             "ಈ ಸಮಸ್ಯೆಗೆ ಪರಿಶೀಲಿತ ಸಲಹೆ ನನ್ನಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿ ಅಥವಾ ರೈತ ಸಂಪರ್ಕ ಕೇಂದ್ರವನ್ನು ಸಂಪರ್ಕಿಸಿ.",
             "ಬೇರೆ ಸಮಸ್ಯೆ ಬಗ್ಗೆ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಾ?"],
            end=False,
            meta={"state": "disease_advisory_unavailable", "crop": disease.crop,
                  "problem": disease.id, "reviewed": False, "referral_given": True},
        ))

    def _ask_another_problem(self):
        self.pending_question_kind = "another_problem"
        self.confirmation_pending = False
        options = ("ಬೇರೆ ಸಮಸ್ಯೆ ಬಗ್ಗೆ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಾ?", "ಇನ್ನೊಂದು ಸಮಸ್ಯೆ ಇದ್ದರೆ ಹೇಳಿ.")
        question = next((candidate for candidate in options if candidate not in self.asked_questions), None)
        if question is None:
            self.pending_question_kind = None
            return self._remember(Reply(T["bye"], end=True, meta={"state": "bye"}))
        return self._remember(Reply([question],
                                    meta={"state": "ask_another_problem", "crop": self.crop,
                                          "problem": self.problem}))

    def _resolve_candidate(self, disease):
        if self.problem != disease.id:
            self.referral_given = False
            self.stage = None
            self.advised = False
            self.last_advisory = None
        self.crop = disease.crop
        self.problem = disease.id
        self.advisory_available = disease.has_advisory
        self.pending_disease_ids = ()
        self.pending_yes_candidates = ()
        self.pending_match_method = None
        self.confirmation_pending = False
        self.pending_question_kind = None
        if not disease.has_advisory:
            return self._unavailable_disease(disease)
        advisory = KB[disease.id]
        if advisory.get("needs_stage") and not self.stage:
            return self._ask("stage")
        return self._advise(advisory)

    def _escalate(self, why):
        return Reply(T["escalate"] + T["bye"], end=True,
                     sms=f"ಕೃಷಿ ಮಿತ್ರ: ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ. {self.esc}",
                     meta={"state": "escalated", "why": why, "safety": "escalated"})

    def _remember(self, r):
        if not r.meta.get("repeated"):
            self.last = r
            question_states = {
                "ask_crop", "ask_problem", "ask_stage", "confirm_disease",
                "clarify_disease_symptom", "ask_another_problem", "followup_options",
                "disease_advisory_unavailable", "repeat_clarification",
            }
            self.pending_question = (
                (str(r.sentences[-1]) if r.meta.get("state") == "disease_advisory_unavailable"
                 else " ".join(str(sentence) for sentence in r.sentences))
                if r.meta.get("state") in question_states else None
            )
            if self.pending_question:
                self.asked_questions.add(self.pending_question)
        return r

    def respond(self, text: str) -> Reply:
        self.conversation_started = True
        t = normalize(text)
        prev_crop = self.crop
        prev_problem = self.problem
        prev_stage = self.stage
        prev_advised = self.advised

        # 1. Global Intent A: End Call
        # Explicit call-ending requests must work in every dialogue state
        if is_end_call_intent(t):
            return Reply(T["bye"], end=True, meta={"state": "bye"})

        if self.pending_question_kind == "post_replay":
            self.pending_question_kind = None
            self.pending_question = None
            if _is_no_answer(t):
                return self._remember(Reply(T["bye"], end=True, meta={"state": "bye"}))
            self.problem = None
            self.advised = False
            self.advisory_available = None
            self.referral_given = False
            if _is_yes_answer(t) or not (find_crop(t) or find_problem(t, crop=self.crop)):
                return self._ask_symptoms(progress=True)

        # Resolve the explicit repeat/new-question prompt before generic
        # "already advised" handling can return that same prompt again.
        if self.pending_question_kind in ("repeat_or_new", "repeat_clarification"):
            is_rep_pending, _ = is_repeat_intent(t)
            yes = _is_yes_answer(t) and ("ಬೇರೆ" not in t or is_rep_pending)
            no = _is_no_answer(t)
            new_question = any(phrase in t for phrase in (
                "ಬೇರೆ ಪ್ರಶ್ನೆ", "ಹೊಸ ಪ್ರಶ್ನೆ", "ಇನ್ನೊಂದು ಪ್ರಶ್ನೆ", "ಬೇರೆ ಬೆಳೆಯ ಬಗ್ಗೆ",
                "another question", "new question", "different crop",
            ))
            # Explicit repeat language wins over the "different crop" substring
            # in answers such as "not another crop, repeat the advice".
            if self.last_advisory and (yes or is_rep_pending):
                self.pending_question = None
                self.pending_question_kind = "post_replay"
                return self._remember(Reply(
                    self.last_advisory.sentences,
                    sms=None,
                    meta={**self.last_advisory.meta, "repeated": True},
                ))
            if no:
                self.pending_question = None
                self.pending_question_kind = None
                self.advised = False
            elif new_question and not is_rep_pending:
                self.pending_question = None
                self.pending_question_kind = None
                self.advised = False
                self.problem = None
                self.advisory_available = None
                self.referral_given = False
            elif find_crop(t) or find_problem(t, crop=self.crop):
                self.pending_question = None
                self.pending_question_kind = None
                self.advised = False
            elif self.pending_question_kind == "repeat_clarification":
                # A second unclear answer leaves repeat mode instead of looping.
                self.pending_question = None
                self.pending_question_kind = None
                self.advised = False
                return self._ask_symptoms(progress=True)
            else:
                self.pending_question_kind = "repeat_clarification"
                clarification = Reply(
                    ["ಹಿಂದಿನ ಸಲಹೆ ಮತ್ತೆ ಬೇಕೇ, ಅಥವಾ ಹೊಸ ಪ್ರಶ್ನೆಯೇ?"],
                    meta={"state": "repeat_clarification", "crop": self.crop},
                )
                return self._remember(clarification)

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

        # A referral leaves the call open. Treat the next substantive utterance
        # as a new issue, while yes/no answers resolve the explicit follow-up.
        if self.pending_question_kind == "another_problem":
            if _is_no_answer(t):
                self.pending_question = None
                self.pending_question_kind = None
                return self._remember(Reply(T["bye"], end=True, meta={"state": "bye"}))
            if _is_yes_answer(t):
                self.problem = None
                self.advisory_available = None
                self.referral_given = False
                self.advised = False
                self.pending_question_kind = None
                return self._ask_symptoms(progress=True)
            self.pending_disease_ids = ()
            self.pending_yes_candidates = ()
            self.pending_match_method = None
            self.confirmation_pending = False
            self.pending_question = None
            self.pending_question_kind = None

        # 4. Check explicit new issue (Bug B)
        new_issue = is_new_issue(t)
        if new_issue:
            self.problem = None
            self.advisory_available = None
            self.referral_given = False
            self.pending_disease_ids = ()
            self.pending_yes_candidates = ()
            self.pending_match_method = None
            self.confirmation_pending = False
            self.pending_question = None
            self.pending_question_kind = None
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

        # 6. Extract crop, problem, stage. A crop after an explicit correction
        # takes precedence over the crop being rejected earlier in the sentence.
        crop = find_crop_correction(t) or find_crop(t)
        if crop:
            self.asks["crop"] = 0
            if self.crop != crop:
                self._reset_crop(crop)
            else:
                self.crop = crop
                # If a problem was provided before crop was known, verify compatibility
                if self.problem and KB.get(self.problem, {}).get("crop") != self.crop:
                    self.problem = None
                    self.advisory_available = None
                    self.referral_given = False
                    self.stage = None
                    self.advised = False
                    self.last_advisory = None
                    self.asks["problem"] = 0
                    self.asks["stage"] = 0

        match = match_disease(
            t, self.crop, DISEASE_REGISTRY,
            crop_explicit=bool(crop or self.crop),
        )
        prob = None
        negated_match_ids = {
            disease.id for disease in DISEASE_REGISTRY
            if any(_is_kw_negated(t, alias)
                   for alias in disease.aliases + disease.confirmation_aliases)
        }
        if match.ids and set(match.ids) <= negated_match_ids:
            match = type(match)((), None, 0.0, ())

        # A new, unrecognized disease statement starts fresh symptom intake;
        # it must not replay a stale disease-choice prompt.
        if (self.pending_disease_ids and not match.ids
                and any(marker in t for marker in ("ರೋಗ", "disease", "problem"))):
            self.pending_disease_ids = ()
            self.pending_yes_candidates = ()
            self.pending_match_method = None
            self.confirmation_pending = False
            self.pending_question = None
            self.pending_question_kind = None
            self.problem = None
            self.advisory_available = None
            self.referral_given = False
            self.advised = False

        # Resolve, narrow, or distinguish the saved candidates before starting
        # another generic question.
        if self.pending_disease_ids:
            positive = _is_yes_answer(t)
            negative = _is_no_answer(t)
            pending = [d for d in DISEASE_REGISTRY if d.id in self.pending_disease_ids]
            # Never carry a candidate from another crop across turns. An
            # explicitly named crop was already applied above via _reset_crop.
            if self.crop:
                pending = [d for d in pending if d.crop == self.crop]
                self.pending_disease_ids = tuple(d.id for d in pending)
            if not pending:
                self.pending_disease_ids = ()
                self.pending_yes_candidates = ()
                self.pending_match_method = None
                self.confirmation_pending = False
                self.pending_question = None
                self.pending_question_kind = None
            else:
                named_pending = [d for d in pending if match.method == "exact" and d.id in match.ids]
                if len(named_pending) == 1:
                    return self._resolve_candidate(named_pending[0])

                if self.pending_question_kind == "candidate_disambiguation" and (positive or negative):
                    yes_ids = set(self.pending_yes_candidates)
                    selected_ids = yes_ids if positive else {d.id for d in pending} - yes_ids
                    selected = [d for d in pending if d.id in selected_ids]
                    if len(selected) == 1:
                        return self._resolve_candidate(selected[0])
                    if selected:
                        if set(d.id for d in selected) != set(self.pending_disease_ids):
                            self.asked_distinguishing_symptoms.clear()
                        self.pending_disease_ids = tuple(d.id for d in selected)
                        return self._ask_disambiguating_symptom(selected)

                if positive and len(pending) == 1:
                    return self._resolve_candidate(pending[0])
                if negative:
                    self.pending_disease_ids = ()
                    self.pending_yes_candidates = ()
                    self.pending_match_method = None
                    self.confirmation_pending = False
                    self.pending_question_kind = None
                    return self._ask_symptoms(progress=True)

                if crop and len(pending) == 1 and self.pending_match_method == "exact":
                    return self._resolve_candidate(pending[0])

                symptoms = match_symptoms(t)
                if symptoms:
                    narrowed = [d for d in pending if symptoms.intersection(d.symptom_ids)]
                    if len(narrowed) == 1:
                        return self._resolve_candidate(narrowed[0])
                    if narrowed and {d.id for d in narrowed} != {d.id for d in pending}:
                        self.asked_distinguishing_symptoms.clear()
                        self.pending_disease_ids = tuple(d.id for d in narrowed)
                        if len(narrowed) >= 3:
                            return self._ask_disambiguating_symptom(narrowed)
                        return self._ask_disease_confirmation(narrowed)

                if len(pending) >= 3 or self.pending_question_kind == "candidate_disambiguation":
                    return self._ask_disambiguating_symptom(pending)
                if len(pending) == 2 and symptoms:
                    return self._ask_disambiguating_symptom(pending)
                if len({d.crop for d in pending}) > 1 and not self.crop:
                    return self._ask("crop")
                return self._ask_disease_confirmation(pending)

        if match.ids:
            matched = [d for d in DISEASE_REGISTRY if d.id in match.ids]
            if match.method == "weak":
                self.pending_disease_ids = tuple(d.id for d in matched)
                self.pending_match_method = "weak"
                return self._ask_disease_confirmation(matched)
            if len(matched) == 1 and self.crop is None:
                if (matched[0].id == "arecanut_koleroga" and any(
                    alias in t for alias in ("ಮಹಾಳಿ", "ಮಹಾಲಿ", "koleroga", "mahali")
                )):
                    self.crop = "arecanut"
                    self.asks["crop"] = 0
                elif matched[0].id == "coconut_root_wilt":
                    self.crop = "coconut"
                    self.asks["crop"] = 0
                elif matched[0].id == "coconut_bud_rot" and "ಸುಳಿ" in t:
                    self.crop = "coconut"
                else:
                    self.problem = matched[0].id
                self.pending_disease_ids = (matched[0].id,)
                self.pending_match_method = match.method
                if self.crop is None:
                    return self._ask("crop")
            if len({d.crop for d in matched}) > 1 and self.crop is None:
                self.pending_disease_ids = tuple(d.id for d in matched)
                self.pending_match_method = "ambiguous" if len(matched) > 1 else match.method
                return self._ask("crop")
            if match.method == "fuzzy" or len(matched) > 1:
                self.pending_disease_ids = tuple(d.id for d in matched)
                self.pending_match_method = match.method
                return self._ask_disease_confirmation(matched)
            selected = matched[0]
            if not selected.has_advisory:
                return self._unavailable_disease(selected)
            prob = selected.id

        # A symptom match is a tentative candidate only. It must be confirmed
        # and never enters the advisory path on its own.
        if not prob and self.crop and not is_disease_negated(t) and not neg_probs:
            symptoms = match_symptoms(t)
            candidates = rank_disease_candidates(symptoms, self.crop, DISEASE_REGISTRY)
            if candidates:
                best_score = candidates[0].score
                tied = [c for c in candidates if c.score == best_score]
                self.pending_disease_ids = tuple(c.id for c in tied)
                self.pending_match_method = "symptom"
                return self._ask_disease_confirmation(
                    [d for d in DISEASE_REGISTRY if d.id in self.pending_disease_ids]
                )

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
            self.advisory_available = True
            self.referral_given = False
            self.stage = None
            self.advised = False
            self.last_advisory = None
            self.asks["problem"] = 0
            self.asks["stage"] = 0
        elif prob:
            if self.problem != prob:
                self.referral_given = False
            self.problem = prob
            self.advisory_available = True
            self.asks["problem"] = 0
            if not self.crop:
                if prob == "coconut_bud_rot" and "ಸುಳಿ" in t:
                    self.crop = "coconut"
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
            self.pending_question_kind = "repeat_or_new"
            return self._remember(Reply(
                T["followup_options"],
                meta={"state": "followup_options", "crop": self.crop}
            ))

        # 8. Unsupported crop check or slot clarification / advisory
        if not self.crop:
            return self._ask("crop")

        if self.crop not in usable_crops():
            active_crops_kn = [CROP_KN.get(c, c) for c in usable_crops()]
            supp_str = " ಮತ್ತು ".join([", ".join(active_crops_kn[:-1]), active_crops_kn[-1]]) if len(active_crops_kn) > 1 else "".join(active_crops_kn)
            crop_name_kn = CROP_KN.get(self.crop, self.crop)
            sentences = [
                T["unsupported_crop"][0].format(crop=crop_name_kn),
                T["unsupported_crop"][1],
                T["unsupported_crop"][2].format(supported_crops=supp_str),
            ]
            sms_crop = crop_name_kn or "ಬೆಳೆ"
            return self._remember(Reply(
                sentences,
                sms=f"ಕೃಷಿ ಮಿತ್ರ: {sms_crop} ಬೆಳೆಗೆ ಸಲಹೆ ಸದ್ಯಕ್ಕೆ ಲಭ್ಯವಿಲ್ಲ. ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ. {self.esc}",
                meta={"state": "unsupported_crop", "crop": self.crop}
            ))

        if self.problem and self.advisory_available is False:
            return self._ask_symptoms(progress=bool(match_symptoms(t)))

        if not self.problem:
            return self._ask_symptoms(progress=bool(match_symptoms(t)))
        if self.problem == "paddy_leaf_folder" and any(k in t for k in ["ಔಷಧ", "ಔಷಧಿ", "ಸಿಂಪಡಿಸ", "ರಾಸಾಯನಿಕ", "chemical", "spray", "pesticide"]):
            return self.start_leaf_folder_intake()
        adv = KB[self.problem]
        if adv["needs_stage"] and not self.stage:
            return self._ask("stage")
        return self._advise(adv)

    def _advise(self, adv):
        self.advisory_available = True
        self.referral_given = False
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
