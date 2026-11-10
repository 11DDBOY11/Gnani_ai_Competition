"""Solution Hub: Evidence-backed agricultural guidance engine.

Implements deterministic, verifiable retrieval from stored official advisories
with strict separation between candidate inspection and public release approval.
"""

import json
import logging
import os
import pathlib
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .config import cfg

log = logging.getLogger("krishi.solution_hub")

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
RECORDS_FILE = pathlib.Path(__file__).resolve().parent.parent / "data" / "solution_hub" / "records.json"

KISAN_CALL_CENTRE = "1800-180-1551"
DISCLAIMER_TEXT = "Server-assembled guidance from eligible stored actions; selection and context still require validation."

# Reviewed static clarification / referral templates
KANNADA_REVIEW_UNAVAILABLE = (
    f"ಈ ವಿಷಯಕ್ಕೆ ಪರಿಶೀಲಿಸಲಾದ ಕನ್ನಡ ಮಾರ್ಗದರ್ಶನ ಲಭ್ಯವಿಲ್ಲ. "
    f"ದೃಢಪಡಿಸಿದ ಸಲಹೆಗಾಗಿ ದಯವಿಟ್ಟು ಕಿಸಾನ್ ಕಾಲ್ ಸೆಂಟರ್ {KISAN_CALL_CENTRE} ಅಥವಾ "
    f"ಸ್ಥಳೀಯ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ."
)

KANNADA_SOURCE_UNVERIFIED = (
    f"ಈ ಬೆಳೆಗೆ ಅಧಿಕೃತವಾಗಿ ಪರಿಶೀಲಿಸಲಾದ ದಾಖಲೆಗಳು ನಮ್ಮಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ. "
    f"ಅಪೂರ್ಣ ಮಾಹಿತಿಯಿಂದ ಸಲಹೆ ನೀಡುವುದಿಲ್ಲ. ದಯವಿಟ್ಟು ಕಿಸಾನ್ ಕಾಲ್ ಸೆಂಟರ್ {KISAN_CALL_CENTRE} "
    f"ಅಥವಾ ಸ್ಥಳೀಯ ತೋಟಗಾರಿಕಾ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ."
)

KANNADA_GAP_PADDY_YELLOW = (
    f"ಭತ್ತದಲ್ಲಿ ಎಲೆಗಳು ಹಳದಿಯಾಗುವುದಕ್ಕೆ ಸಾರಜನಕ ಕೊರತೆ, ನೀರು ನಿಲ್ಲುವುದು ಅಥವಾ ರೋಗ ಹೀಗೆ ಹಲವು ಕಾರಣಗಳಿರಬಹುದು. "
    f"ಇದು ಖಚಿತ ರೋಗನಿರ್ಣಯವಲ್ಲ. ಕೆಳಗಿನ ವಿವರಗಳನ್ನು ಗಮನಿಸಿ:\n"
    f"1. ಕೆಳಗಿನ ಎಲೆಗಳು ಪೂರ್ಣ ಹಳದಿಯಾಗುತ್ತಿವೆಯೇ ಅಥವಾ ಕಂದು ಅಂಚಿನ ಚುಕ್ಕೆಗಳಿವೆಯೇ?\n"
    f"2. ಗದ್ದೆಯಲ್ಲಿ ನೀರು ಹೆಚ್ಚಾಗಿ ನಿಂತಿದೆಯೇ?\n"
    f"ಹೆಚ್ಚಿನ ಮಾಹಿತಿಗೆ ಕಿಸಾನ್ ಕಾಲ್ ಸೆಂಟರ್ {KISAN_CALL_CENTRE} ಗೆ ಕರೆ ಮಾಡಿ."
)

KANNADA_GAP_ARECANUT_DROP = (
    f"ಅಡಿಕೆ ಕಾಯಿ ಉದುರುವುದು ನೀರಿನ ಕೊರತೆ ಅಥವಾ ಕೊಳೆ ರೋಗ ಹೀಗೆ ವಿವಿಧ ಕಾರಣಗಳಿಂದ ಇರಬಹುದು. "
    f"ಇದು ಖಚಿತ ರೋಗನಿರ್ಣಯವಲ್ಲ. ಉದುರಿದ ಕಾಯಿಗಳಲ್ಲಿ ಕಪ್ಪು ಕಲೆಗಳಿವೆಯೇ ಎಂದು ಪರೀಕ್ಷಿಸಿ. "
    f"ಔಷಧ ಬಳಸುವ ಮೊದಲು ಸ್ಥಳೀಯ ಕೃಷಿ/ತೋಟಗಾರಿಕಾ ಅಧಿಕಾರಿಯನ್ನು ಅಥವಾ ಕಿಸಾನ್ ಕಾಲ್ ಸೆಂಟರ್ {KISAN_CALL_CENTRE} ಸಂಪರ್ಕಿಸಿ."
)

KANNADA_GAP_COCONUT_SPOTS = (
    f"ತೆಂಗಿನ ಎಲೆಗಳಲ್ಲಿ ಕಂದು ಚುಕ್ಕೆಗಳು ಪೋಷಕಾಂಶ ಕೊರತೆ ಅಥವಾ ಶಿಲೀಂಧ್ರದಿಂದ ಉಂಟಾಗಬಹುದು. "
    f"ಇದು ಖಚಿತ ರೋಗನಿರ್ಣಯವಲ್ಲ. ಕಲೆಗಳು ಹಳೆಯ ಎಲೆಗಳಲ್ಲಿವೆಯೇ ಅಥವಾ ಹೊಸ ಗರಿಗಳಲ್ಲಿದೆಯೇ ಗಮನಿಸಿ. "
    f"ಸೂಕ್ತ ಸಲಹೆಗೆ ತೋಟಗಾರಿಕಾ ಅಧಿಕಾರಿಗಳನ್ನು ಅಥವಾ ಕಿಸಾನ್ ಕಾಲ್ ಸೆಂಟರ್ {KISAN_CALL_CENTRE} ಸಂಪರ್ಕಿಸಿ."
)

KANNADA_GAP_GENERIC = (
    f"ದಯವಿಟ್ಟು ಬೆಳೆಯ ಹೆಸರು (ಉದಾಹರಣೆಗೆ ಭತ್ತ, ಅಡಿಕೆ, ತೆಂಗು) ಮತ್ತು ಎಲೆ ಅಥವಾ ಕಾಂಡದಲ್ಲಿ "
    f"ಕಂಡುಬರುವ ಲಕ್ಷಣಗಳನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ತಿಳಿಸಿ. ಕಿಸಾನ್ ಕಾಲ್ ಸೆಂಟರ್ {KISAN_CALL_CENTRE} ಗೂ ಸಂಪರ್ಕಿಸಬಹುದು."
)


def load_records() -> Dict[str, Any]:
    """Load the verified records repository."""
    if not RECORDS_FILE.exists():
        raise FileNotFoundError(f"Solution Hub repository not found at {RECORDS_FILE}")
    with open(RECORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_source_map(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {s["source_id"]: s for s in data.get("sources", [])}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def detect_crop_and_issue(question: str, explicit_crop: Optional[str] = None) -> Dict[str, Any]:
    """Classify the crop, issue, and diagnostic certainty of the query.
    
    A match is strictly separated into:
    - farmer_reported: Farmer explicitly named the disease.
    - symptom_match_candidate: Symptoms match a candidate condition.
    - ambiguous_symptom: Symptoms match an evidence gap (e.g. yellow leaves).
    - unverified_source: Issue matches a known disease whose sources are unverified.
    - generic: Crop or issue not identifiable.
    """
    q_norm = normalize_text(question)
    
    # 1. Determine crop
    crop = (explicit_crop or "").lower().strip() or None
    if not crop:
        if any(w in q_norm for w in ["paddy", "rice", "ಭತ್ತ"]):
            crop = "paddy"
        elif any(w in q_norm for w in ["arecanut", "areca", "betel nut", "ಅಡಿಕೆ"]):
            crop = "arecanut"
        elif any(w in q_norm for w in ["coconut", "ತೆಂಗು", "ತೆಂಗಿನ"]):
            crop = "coconut"

    # 2. Check for ambiguous evidence gaps first (symptom-only questions)
    # Paddy yellow leaves
    if crop == "paddy" and any(w in q_norm for w in ["yellow", "yellowing", "ಹಳದಿ", "chlorosis"]):
        # Check if farmer explicitly named blast or leaf folder
        if not any(w in q_norm for w in ["blast", "ಬೆಂಕಿ", "folder", "ಸುರುಳಿ", "roller"]):
            return {
                "crop": "paddy",
                "diagnosis_type": "ambiguous_symptom",
                "gap_id": "GAP-PADDY-YELLOW-LEAF",
                "record": None,
                "candidate_issue": None,
            }

    # Arecanut nut drop
    if crop == "arecanut" and any(w in q_norm for w in ["drop", "falling", "shedding", "ಉದುರು"]):
        if not any(w in q_norm for w in ["koleroga", "mahali", "ಕೊಳೆ"]):
            return {
                "crop": "arecanut",
                "diagnosis_type": "ambiguous_symptom",
                "gap_id": "GAP-ARECANUT-FRUIT-DROP",
                "record": None,
                "candidate_issue": None,
            }

    # Coconut leaf spots
    if crop == "coconut" and any(w in q_norm for w in ["spot", "spots", "ಚುಕ್ಕೆ", "blight"]):
        if not any(w in q_norm for w in ["bud rot", "ಕುಳೆ"]):
            return {
                "crop": "coconut",
                "diagnosis_type": "ambiguous_symptom",
                "gap_id": "GAP-COCONUT-LEAF-SPOTS",
                "record": None,
                "candidate_issue": None,
            }

    # Generic or unspecified
    if not crop or (crop == "other" and not any(k in q_norm for k in ["paddy", "rice", "blast", "folder"])):
        return {
            "crop": crop or "unspecified",
            "diagnosis_type": "ambiguous_symptom",
            "gap_id": "GAP-UNSPECIFIED-CROP",
            "record": None,
            "candidate_issue": None,
        }

    # 3. Check for unverified source diseases (Coconut Bud Rot, Arecanut Koleroga)
    if crop == "coconut" and any(w in q_norm for w in ["bud rot", "ಬುಡ್ ರಾಟ್", "ಕುಳೆ ರೋಗ", "ಸುಳಿ ಕೊಳೆ"]):
        return {
            "crop": "coconut",
            "diagnosis_type": "unverified_source",
            "record_id": "REC-COCONUT-BUD-ROT-03-EXCLUDED",
            "candidate_issue": "coconut_bud_rot",
            "farmer_reported": any(w in q_norm for w in ["bud rot", "ಕುಳೆ"]),
        }
    if crop == "arecanut" and any(w in q_norm for w in ["koleroga", "mahali", "ಕೊಳೆರೋಗ", "ಕೊಳೆ ರೋಗ"]):
        return {
            "crop": "arecanut",
            "diagnosis_type": "unverified_source",
            "record_id": "REC-ARECANUT-KOLEROGA-04-EXCLUDED",
            "candidate_issue": "arecanut_koleroga",
            "farmer_reported": any(w in q_norm for w in ["koleroga", "mahali", "ಕೊಳೆರೋಗ", "ಕೊಳೆ ರೋಗ"]),
        }

    # 4. Check for supported candidate issues in Paddy
    if crop == "paddy":
        # Leaf folder
        if any(w in q_norm for w in ["leaf folder", "folder", "roller", "ಎಲೆ ಸುರುಳಿ", "ಸುರುಳಿ", "ಮಡಚಿದ"]):
            return {
                "crop": "paddy",
                "diagnosis_type": "candidate_issue",
                "record_id": "REC-PADDY-LEAF-FOLDER-02",
                "candidate_issue": "rice_leaf_folder",
                "farmer_reported": any(w in q_norm for w in ["leaf folder", "folder", "ಸುರುಳಿ"]),
            }
        # Rice blast
        if any(w in q_norm for w in ["blast", "ಬೆಂಕಿ ರೋಗ", "ಬೆಂಕಿ", "spindle", "diamond", "neck blast"]):
            return {
                "crop": "paddy",
                "diagnosis_type": "candidate_issue",
                "record_id": "REC-PADDY-BLAST-01",
                "candidate_issue": "rice_blast",
                "farmer_reported": any(w in q_norm for w in ["blast", "ಬೆಂಕಿ"]),
            }

    # If crop is known but no specific issue matched
    if crop == "paddy":
        return {
            "crop": "paddy",
            "diagnosis_type": "ambiguous_symptom",
            "gap_id": "GAP-PADDY-YELLOW-LEAF",
            "record": None,
            "candidate_issue": None,
        }
    if crop == "arecanut":
        return {
            "crop": "arecanut",
            "diagnosis_type": "ambiguous_symptom",
            "gap_id": "GAP-ARECANUT-FRUIT-DROP",
            "record": None,
            "candidate_issue": None,
        }
    if crop == "coconut":
        return {
            "crop": "coconut",
            "diagnosis_type": "ambiguous_symptom",
            "gap_id": "GAP-COCONUT-LEAF-SPOTS",
            "record": None,
            "candidate_issue": None,
        }

    return {
        "crop": "unspecified",
        "diagnosis_type": "ambiguous_symptom",
        "gap_id": "GAP-UNSPECIFIED-CROP",
        "record": None,
        "candidate_issue": None,
    }


def handle_ambiguous_symptom(gap_id: str, language: str) -> Dict[str, Any]:
    """Return safe clarification questions for ambiguous symptoms without treatments."""
    data = load_records()
    gaps = {g["gap_id"]: g for g in data.get("evidence_gaps", [])}
    gap = gaps.get(gap_id)

    if language == "kn":
        if gap_id == "GAP-PADDY-YELLOW-LEAF":
            ans = KANNADA_GAP_PADDY_YELLOW
        elif gap_id == "GAP-ARECANUT-FRUIT-DROP":
            ans = KANNADA_GAP_ARECANUT_DROP
        elif gap_id == "GAP-COCONUT-LEAF-SPOTS":
            ans = KANNADA_GAP_COCONUT_SPOTS
        else:
            ans = KANNADA_GAP_GENERIC
    else:
        questions_str = "\n".join(f"- {q}" for q in gap.get("clarification_questions", [])) if gap else ""
        ans = (
            f"The observed symptoms are ambiguous and can indicate multiple different causes "
            f"(nutritional, physiological, or pathological). A match is not a confirmed diagnosis.\n\n"
            f"Please clarify the following:\n{questions_str}\n\n"
            f"For an on-site diagnosis and confirmation, please contact the Kisan Call Centre at "
            f"{KISAN_CALL_CENTRE} or your local agriculture/horticulture officer before applying any treatment."
        )

    return {
        "answer": ans,
        "confidence": "low",
        "needs_expert_review": True,
        "sources": [],
    }


def handle_unverified_source(language: str) -> Dict[str, Any]:
    """Total abstention for conditions whose source documents are not verified."""
    if language == "kn":
        ans = KANNADA_SOURCE_UNVERIFIED
    else:
        ans = (
            f"Primary official publications for this condition are currently unverified in our repository. "
            f"Krishi Mitra does not generate unverified management recommendations.\n\n"
            f"Please consult your local horticulture officer, Krishi Vigyan Kendra (KVK), or call the "
            f"Kisan Call Centre at {KISAN_CALL_CENTRE}."
        )
    return {
        "answer": ans,
        "confidence": "low",
        "needs_expert_review": True,
        "sources": [],
    }


async def select_action_ids_via_groq(
    question: str,
    candidate_actions: List[Dict[str, Any]],
    candidate_issue: str,
) -> List[str]:
    """Call Groq to select ONLY candidate action IDs from the eligible set."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return []

    action_summaries = [
        {"action_id": a["action_id"], "description": a["display_text"]}
        for a in candidate_actions
    ]
    prompt_content = json.dumps({
        "question": question,
        "candidate_issue": candidate_issue,
        "eligible_actions": action_summaries,
    }, ensure_ascii=False)

    selector_system_prompt = (
        "You are a strict action ID selector for an agricultural expert system. "
        "Given the farmer question and the list of eligible actions, select 1 to 3 "
        "action IDs that are directly relevant. Return JSON only with key 'selected_action_ids'. "
        "Select ONLY from the provided eligible action IDs. Do NOT create or invent action IDs. "
        "Do NOT author any treatment advice or chemical recommendations."
    )

    payload = {
        "model": os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL,
        "messages": [
            {"role": "system", "content": selector_system_prompt},
            {"role": "user", "content": prompt_content},
        ],
        "response_format": {"type": "json_object"},
        "max_completion_tokens": 300,
        "temperature": 0.0,
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            resp = await client.post(
                GROQ_CHAT_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            ids = parsed.get("selected_action_ids", [])
            if isinstance(ids, list):
                return [str(i) for i in ids]
    except Exception as exc:
        log.warning("Groq action selection failed or timed out: %s", exc)

    return []


async def generate_solution_hub_answer(
    question: str,
    language: str = "kn",
    crop: Optional[str] = None,
    district: Optional[str] = None,
    allow_inspection: bool = False,
) -> Dict[str, Any]:
    """Main Solution Hub entry point.
    
    Adheres strictly to:
    - Crop isolation
    - Symptom vs. confirmed diagnosis separation
    - Deterministic ID validation
    - Zero chemical leakage
    - Mandatory review status enforcement (public vs internal candidate inspection)
    - Reviewed Kannada text enforcement
    """
    data = load_records()
    source_map = get_source_map(data)
    record_map = {r["record_id"]: r for r in data.get("records", [])}

    intent = detect_crop_and_issue(question, explicit_crop=crop)
    diagnosis_type = intent["diagnosis_type"]

    # 1. Ambiguous symptoms -> clarification only
    if diagnosis_type == "ambiguous_symptom":
        return handle_ambiguous_symptom(intent["gap_id"], language)

    # 2. Unverified source -> total abstention
    if diagnosis_type == "unverified_source":
        return handle_unverified_source(language)

    # 3. Candidate issue
    rec_id = intent.get("record_id")
    record = record_map.get(rec_id)
    if not record or not record.get("source_verified"):
        return handle_unverified_source(language)

    # Check language review status: if Kannada is requested, check if approved Kannada text exists
    if language == "kn":
        # Check if any action has approved Kannada wording
        actions_with_approved_kannada = [
            a for a in record.get("supported_actions", [])
            if a.get("kannada_review_status") == "approved" and a.get("kannada_display_text")
        ]
        if not actions_with_approved_kannada:
            # Verified Kannada wording is unavailable: explain clearly, do not fake translation
            return {
                "answer": KANNADA_REVIEW_UNAVAILABLE,
                "confidence": "low",
                "needs_expert_review": True,
                "sources": [
                    {
                        "source_id": s_id,
                        "title": source_map[s_id]["title"],
                        "publisher": source_map[s_id]["publisher"],
                        "url": source_map[s_id]["url"],
                    }
                    for s_id in {a["source_id"] for a in record.get("supported_actions", [])}
                    if s_id in source_map
                ],
            }

    # Filter actions by eligibility
    all_actions = record.get("supported_actions", [])
    if allow_inspection:
        # Developer / local inspection mode: candidate inspection eligible actions
        eligible_actions = [a for a in all_actions if a.get("candidate_inspection_eligible")]
    else:
        # Public release mode: only agronomy-approved actions
        eligible_actions = [a for a in all_actions if a.get("public_release_approved")]

    # If no actions are approved for this mode:
    if not eligible_actions:
        issue_name = record.get("candidate_issue", "the issue").replace("_", " ").title()
        crop_name = record.get("crop_names", {}).get("en", "crop")
        src_ids = {a["source_id"] for a in all_actions}
        sources = [
            {
                "source_id": s_id,
                "title": source_map[s_id]["title"],
                "publisher": source_map[s_id]["publisher"],
                "url": source_map[s_id]["url"],
            }
            for s_id in src_ids if s_id in source_map
        ]
        ans = (
            f"Official advisories for {issue_name} on {crop_name} are cataloged from official sources, "
            f"but practical recommendations are currently pending expert agronomy and safety review. "
            f"Unreviewed actions are not released as public advice.\n\n"
            f"Please contact the Kisan Call Centre at {KISAN_CALL_CENTRE} or your local agriculture officer "
            f"for verified field advice."
        )
        return {
            "answer": ans,
            "confidence": "medium",
            "needs_expert_review": True,
            "sources": sources,
        }

    # Have Groq select IDs from the eligible subset
    valid_id_map = {a["action_id"]: a for a in eligible_actions}
    selected_ids = await select_action_ids_via_groq(
        question=question,
        candidate_actions=eligible_actions,
        candidate_issue=record.get("candidate_issue", ""),
    )

    # Server validates selected IDs strictly against the candidate set
    validated_actions = [valid_id_map[i] for i in selected_ids if i in valid_id_map]

    # If Groq failed, hallucinated invalid IDs, or returned none, take top safe default from eligible
    if not validated_actions:
        # Take up to 2 safe non-context-sensitive eligible actions
        safe_defaults = [a for a in eligible_actions if not a.get("context_sensitive")]
        validated_actions = safe_defaults[:2] if safe_defaults else eligible_actions[:1]

    # Server deterministically formats approved display text from stored records
    diagnosis_note = (
        "Farmer reported issue: " if intent.get("farmer_reported")
        else "Symptoms reported are consistent with candidate issue: "
    )
    issue_label = record.get("candidate_issue", "").replace("_", " ").title()
    crop_label = record.get("crop_names", {}).get("en", "crop")

    action_bullets = "\n".join(f"• {a['display_text']}" for a in validated_actions)

    inspection_notice = (
        "\n\n[INTERNAL INSPECTION ONLY - PENDING AGRONOMY & KANNADA REVIEW]"
        if allow_inspection and any(not a.get("public_release_approved") for a in validated_actions)
        else ""
    )

    assembled_answer = (
        f"{DISCLAIMER_TEXT}\n\n"
        f"{diagnosis_note}{issue_label} on {crop_label}. A match is not a confirmed diagnosis.\n\n"
        f"Supported advisory actions from official guidance:\n"
        f"{action_bullets}\n\n"
        f"For diagnosis confirmation and product advice, contact the Kisan Call Centre at "
        f"{KISAN_CALL_CENTRE} or your local agricultural officer.{inspection_notice}"
    )

    # Assemble sources exclusively from stored metadata
    selected_source_ids = {a["source_id"] for a in validated_actions}
    sources = [
        {
            "source_id": s_id,
            "title": source_map[s_id]["title"],
            "publisher": source_map[s_id]["publisher"],
            "url": source_map[s_id]["url"],
        }
        for s_id in selected_source_ids if s_id in source_map
    ]

    return {
        "answer": assembled_answer,
        "confidence": "medium",
        "needs_expert_review": True,
        "sources": sources,
    }

