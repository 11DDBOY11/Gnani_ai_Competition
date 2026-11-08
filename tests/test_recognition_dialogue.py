import ast
import json
import unicodedata
from pathlib import Path
import pytest

from app.dialogue import DISEASE_REGISTRY, Session, find_crop, find_problem, keyterms
from app.diseases import match_disease
from scripts.mine_transcripts import mine


YES_ANSWERS = ("ಹೌದು", "ಹೌದ್ರಿ", "ಹೂಂ", "ಸರಿ", "yes", "haudu")
NO_ANSWERS = ("ಅಲ್ಲ", "ಇಲ್ಲ", "ಬೇಡ", "no", "illa")


def test_fuzzy_disease_requires_confirmation_before_existing_advisory():
    session = Session()
    first = session.respond("ಅಡಿಕೆಗೆ ಕೊಲೆ ರೋಗ ಬಂದಿದೆ")
    assert first.meta["state"] == "confirm_disease"
    assert first.meta["candidate_ids"] == ["arecanut_koleroga"]
    assert not session.advised

    confirmed = session.respond("ಹೌದು")
    assert confirmed.meta["advisory_id"] == "arecanut_koleroga"
    assert session.advised


def test_rejecting_fuzzy_candidate_returns_to_symptom_intake():
    session = Session()
    assert session.respond("ಅಡಿಕೆಗೆ ಕೊಲೆ ರೋಗ ಬಂದಿದೆ").meta["state"] == "confirm_disease"
    reply = session.respond("ಇಲ್ಲ")
    assert reply.meta["state"] == "ask_problem"
    assert reply.meta["symptom_prompt"] is True
    assert session.pending_disease_ids == ()
    assert session.asks["problem"] == 0


def test_crop_change_clears_incompatible_pending_candidate():
    session = Session()
    session.respond("ಅಡಿಕೆಗೆ ಕೊಲೆ ರೋಗ ಬಂದಿದೆ")
    reply = session.respond("paddy")
    assert session.crop == "paddy"
    assert session.pending_disease_ids == ()
    assert reply.meta["state"] == "ask_problem"


@pytest.mark.parametrize("utterance", [
    "ಭತ್ತದಲ್ಲಿ ಮಡಚಿಕೊಂಡಿದೆ, ಇದಕ್ಕೆ ಪರಿಹಾರ ಕೊಡಿ.",
    "ಭತ್ತದಲ್ಲಿ ಎಲೆ ಮಡಚಿಕೊಂಡಿದೆ",
    "ಭತ್ತದಲ್ಲಿ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ",
    "ಭತ್ತದಲ್ಲಿ ಎಲೆ ಸುತ್ತುವ ಹುಳು",
])
def test_paddy_leaf_folder_inflections_enter_leaf_folder_flow(utterance):
    assert find_crop(utterance) == "paddy"
    assert find_problem(utterance) == "paddy_leaf_folder"

    session = Session()
    reply = session.respond(utterance)
    assert session.crop == "paddy"
    assert session.problem == "paddy_leaf_folder"
    assert reply.meta["state"] == "ask_stage"


@pytest.mark.parametrize("correction", [
    "ಅಡಿಕೆ ರೋಗ ಅಲ್ಲ, ಭತ್ತದ ಬೆಳೆ",
    "ಕ್ಷಮಿಸಿ, ಅದು ಅಡಿಕೆ ಅಲ್ಲ, ಭತ್ತದ ಬಗ್ಗೆ ಹೇಳಬೇಕಿತ್ತು.",
])
def test_explicit_crop_correction_clears_arecanut_candidates_and_then_paddy_blast_stays_active(correction):
    session = Session()
    # Start from the cross-turn state represented by the arecanut clarification.
    session.crop = "arecanut"
    session.pending_disease_ids = ("arecanut_koleroga",)
    session.pending_yes_candidates = ("arecanut_koleroga",)
    session.pending_match_method = "symptom"
    session.confirmation_pending = True
    session.pending_question_kind = "candidate_disambiguation"
    session.pending_question = "ಕಾಯಿಯಲ್ಲಿ ಕೊಳೆ ಇದೆಯೇ, ಅಥವಾ ಕಾಂಡದ ಬುಡದಲ್ಲಿ ತೊಂದರೆಯೇ?"

    corrected = session.respond(correction)
    assert session.crop == "paddy"
    assert session.pending_disease_ids == ()
    assert session.pending_yes_candidates == ()
    assert session.confirmation_pending is False
    assert corrected.meta["state"] == "ask_problem"
    assert "ಅಡಿಕೆ" not in " ".join(corrected.sentences)

    blast = session.respond("ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಬೆಂಕಿ ರೋಗ ಬಂದಿದೆ")
    assert blast.meta["state"] == "advised"
    assert session.crop == "paddy"
    assert session.problem == "paddy_blast"


def test_repeating_paddy_blast_request_in_same_session_does_not_replay_greeting():
    session = Session()
    first = session.respond("ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಬೆಂಕಿ ರೋಗ ಬಂದಿದೆ")
    assert first.meta["advisory_id"] == "paddy_blast"
    repeated_request = session.respond("ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಬೆಂಕಿ ರೋಗ ಬಂದಿದೆ")
    assert repeated_request.meta["state"] != "greeting"
    assert "ನಮಸ್ಕಾರ" not in " ".join(repeated_request.sentences)


def test_confirmed_disease_without_advisory_uses_specific_referral():
    session = Session()
    reply = session.respond("ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಕಂದು ಚುಕ್ಕೆ ರೋಗ ಬಂದಿದೆ")
    assert reply.meta["state"] == "disease_advisory_unavailable"
    assert reply.meta["problem"] == "paddy_brown_spot"
    assert reply.meta["reviewed"] is False
    assert not reply.end
    assert session.pending_question == "ಬೇರೆ ಸಮಸ್ಯೆ ಬಗ್ಗೆ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಾ?"


def test_four_turn_root_wilt_and_yellowing_sequence_keeps_dialogue_state():
    session = Session()

    first = session.respond("ಬೇರು ಸೊರಗು ರೋಗ.")
    assert first.meta["state"] == "disease_advisory_unavailable"
    assert not first.end
    assert session.active_crop == "coconut"
    assert session.active_problem == "coconut_root_wilt"
    assert session.pending_question == "ಬೇರೆ ಸಮಸ್ಯೆ ಬಗ್ಗೆ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಾ?"
    assert session.advisory_available is False
    assert session.referral_given is True

    second = session.respond("ಎಲೆ ಹಳದಿಯಾಗಿ ಹೋಗಿದೆ.")
    assert second.meta["state"] == "confirm_disease"
    assert set(session.pending_candidates) == {
        "coconut_basal_stem_rot", "coconut_root_wilt"
    }
    assert session.pending_question == second.sentences[0]
    assert "ಪರಿಶೀಲಿತ ಸಲಹೆ" not in " ".join(second.sentences)

    third = session.respond("ಎಲೆ ಹಳದಿಯಾಗಿದೆ.")
    assert third.meta["state"] == "clarify_disease_symptom"
    assert third.sentences != second.sentences
    assert session.pending_question == third.sentences[0]
    assert third.sentences != ["ಎಲೆ ಹಳದಿಯಾಗಿದೆಯೇ, ಕಾಯಿ ಉದುರುತ್ತಿವೆಯೇ, ಅಥವಾ ಮೊಗ್ಗು ಕೊಳೆಯುತ್ತಿದೆಯೇ?"]

    fourth = session.respond("ನನ್ನ ತೆಂಗಿನ ಮರದಲ್ಲಿ ಕಳೆ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?")
    assert session.active_crop == "coconut"
    assert fourth.meta["state"] == "ask_problem"
    assert fourth.meta["state"] != "greeting"
    assert "ನಮಸ್ಕಾರ" not in " ".join(fourth.sentences)
    assert session.pending_candidates == ()
    assert session.conversation_started is True


def test_new_crop_clears_only_incompatible_active_disease_state():
    session = Session()
    session.respond("ಬೇರು ಸೊರಗು ರೋಗ.")
    reply = session.respond("ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಬೆಂಕಿ ರೋಗ ಬಂದಿದೆ.")
    assert reply.meta["state"] == "advised"
    assert session.active_crop == "paddy"
    assert session.active_problem == "paddy_blast"
    assert session.advisory_available is True
    assert session.referral_given is False


def test_new_specific_disease_replaces_previous_active_candidate():
    session = Session()
    session.respond("ಬೇರು ಸೊರಗು ರೋಗ.")
    reply = session.respond("ತೆಂಗಿನ ಮರದಲ್ಲಿ ಎಲೆ ಚುಕ್ಕೆ ರೋಗ ಬಂದಿದೆ.")
    assert reply.meta["problem"] == "coconut_leaf_spot"
    assert session.active_problem == "coconut_leaf_spot"
    assert session.advisory_available is False
    assert session.referral_given is True


def test_cross_crop_disease_alias_asks_crop_then_confirmation():
    session = Session()
    first = session.respond("ಎಲೆ ಚುಕ್ಕೆ ರೋಗ")
    assert first.meta["state"] == "ask_crop"
    assert set(session.pending_disease_ids) == {"coconut_leaf_spot", "arecanut_leaf_spot"}

    second = session.respond("ತೆಂಗು")
    assert second.meta["state"] == "confirm_disease"
    assert second.meta["candidate_ids"] == ["coconut_leaf_spot"]

    confirmed = session.respond("ಹೌದು")
    assert confirmed.meta["state"] == "disease_advisory_unavailable"
    assert confirmed.meta["problem"] == "coconut_leaf_spot"


def test_symptom_candidate_is_tentative_and_does_not_spend_clarification_attempt():
    session = Session()
    reply = session.respond("my coconut leaves are turning yellow")
    assert reply.meta["state"] == "confirm_disease"
    assert set(reply.meta["candidate_ids"]) == {
        "coconut_basal_stem_rot", "coconut_root_wilt"
    }
    assert session.asks["problem"] == 0

    selected = session.respond("root wilt")
    assert selected.meta["state"] == "disease_advisory_unavailable"
    assert selected.meta["problem"] == "coconut_root_wilt"


def test_keyterms_include_single_word_kannada_disease_aliases_under_limit():
    terms = keyterms()
    assert "ತುಂಗ್ರೋ" in terms
    assert "ಮಹಾಳಿ" in terms
    assert len(terms) <= 200


def test_transcript_miner_reports_crop_recognized_without_disease(tmp_path):
    calls = tmp_path / "calls.jsonl"
    calls.write_text(json.dumps({"turns": [
        {"who": "farmer", "text": "ನನ್ನ ತೆಂಗಿನ ಮರದ ಎಲೆಗಳು ಹಳದಿಯಾಗಿವೆ"},
        {"who": "farmer", "text": "ಅದರ ಮೇಲೆ ಚುಕ್ಕೆಗಳಿವೆ"},
    ]}, ensure_ascii=False) + "\n", encoding="utf-8")

    found = mine(Path(calls))
    assert len(found) == 1
    assert found[0]["crop"] == "coconut"
    assert found[0]["turn"] == 1


def test_cleanup_removes_overbroad_exact_aliases():
    aliases = {d.id: set(d.aliases) for d in DISEASE_REGISTRY}
    assert "ಸುಳಿ" not in aliases["coconut_bud_rot"]
    assert "ದುಂಬಿ" not in aliases["coconut_rhino_beetle"]
    assert "beetle" not in aliases["coconut_rhino_beetle"]
    assert "ಕೊಂಬಿನ ದುಂಬಿ" in aliases["coconut_rhino_beetle"]
    assert "rhinoceros beetle" in aliases["coconut_rhino_beetle"]
    assert "rhino beetle" in aliases["coconut_rhino_beetle"]
    assert "ಕಣ್ಣಿನ ಆಕಾರ" not in aliases["paddy_blast"]


def test_suli_drying_does_not_select_coconut_bud_rot():
    reply = Session().respond("ತೆಂಗಿನ ಮರದ ಸುಳಿ ಒಣಗಿದೆ")
    assert reply.meta.get("advisory_id") != "coconut_bud_rot"
    assert reply.meta.get("problem") != "coconut_bud_rot"


def test_coconut_beetle_requires_confirmation_before_advisory():
    session = Session()
    reply = session.respond("coconut beetle")
    assert reply.meta["state"] == "confirm_disease"
    assert reply.meta["candidate_ids"] == ["coconut_rhino_beetle"]
    assert "advisory_id" not in reply.meta
    confirmed = session.respond("yes")
    assert confirmed.meta["advisory_id"] == "coconut_rhino_beetle"


def test_generic_rot_without_crop_asks_crop_specific_confirmation():
    match = match_disease("ಕೊಳೆ ರೋಗ", None, DISEASE_REGISTRY)
    assert match.ids == ("arecanut_koleroga",)
    assert match.needs_confirm

    reply = Session().respond("ಕೊಳೆ ರೋಗ")
    assert reply.meta["state"] == "confirm_disease"
    assert reply.sentences == [
        "ನೀವು ಅಡಿಕೆ ಬೆಳೆಯ ಕೊಳೆ ರೋಗ ಬಗ್ಗೆ ಕೇಳುತ್ತಿದ್ದೀರಾ? ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
    ]


def test_specific_koleroga_name_can_infer_arecanut_without_confirmation():
    reply = Session().respond("koleroga")
    assert reply.meta["advisory_id"] == "arecanut_koleroga"


def test_generic_arecanut_rot_alias_with_explicit_crop_is_not_weak():
    match = match_disease("ಅಡಿಕೆ ಕೊಳೆ ರೋಗ", "arecanut", DISEASE_REGISTRY,
                          crop_explicit=True)
    assert match.ids == ("arecanut_koleroga",)
    assert match.method == "exact"
    assert not match.needs_confirm


@pytest.mark.parametrize("phrase", ["ಟ್ರ್ಯಾಕ್ಟರ್ ಬಾಡಿಗೆ ಎಷ್ಟು", "ನೀರು ಕುಡಿಯುತ್ತಿಲ್ಲ", "ಹೂಡಿಕೆ ಬಗ್ಗೆ ಹೇಳಿ"])
def test_unrelated_terms_do_not_trigger_symptom_groups(phrase):
    from app.diseases import match_symptoms
    assert match_symptoms(phrase) == frozenset()


@pytest.mark.parametrize("answer", YES_ANSWERS)
def test_all_requested_yes_phrases_confirm_a_single_candidate(answer):
    session = Session()
    assert session.respond("ಅಡಿಕೆಗೆ ಕೊಲೆ ರೋಗ ಬಂದಿದೆ").meta["state"] == "confirm_disease"
    reply = session.respond(answer)
    assert reply.meta["advisory_id"] == "arecanut_koleroga"


@pytest.mark.parametrize("answer", NO_ANSWERS)
def test_all_requested_no_phrases_reject_a_single_candidate(answer):
    session = Session()
    assert session.respond("ಅಡಿಕೆಗೆ ಕೊಲೆ ರೋಗ ಬಂದಿದೆ").meta["state"] == "confirm_disease"
    reply = session.respond(answer)
    assert reply.meta["state"] == "ask_problem"
    assert reply.meta["symptom_prompt"] is True


def test_three_or_more_candidates_get_one_distinguishing_symptom_question():
    by_id = {d.id: d for d in DISEASE_REGISTRY}
    candidates = [by_id[x] for x in ("paddy_blast", "paddy_brown_spot", "paddy_leaf_folder")]
    session = Session()
    session.pending_match_method = "symptom"
    reply = session._ask_disease_confirmation(candidates)
    assert reply.sentences == ["ಎಲೆಗಳು ಒಣಗುತ್ತಿವೆಯೇ?"]
    assert all(d.name_kn not in reply.sentences[0] for d in candidates)


def test_kannada_source_literals_use_only_allowed_character_ranges():
    project = Path(__file__).resolve().parents[1]
    for relative in ("app/dialogue.py", "app/diseases.py"):
        tree = ast.parse((project / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if not any("\u0c80" <= char <= "\u0cff" for char in node.value):
                continue
            invalid = [char for char in node.value if not (
                "\u0c80" <= char <= "\u0cff" or ord(char) < 128 or char.isspace()
                or unicodedata.category(char).startswith("P")
            )]
            assert not invalid, (
                f"{relative}:{node.lineno} has disallowed characters "
                f"{[(char, f'U+{ord(char):04X}') for char in invalid]}"
            )
