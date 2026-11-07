"""Regression tests for dialogue repair based on live conversation failure."""
from app.dialogue import Session, find_problem, find_crop, is_disease_negated, is_low_yield, KB, usable_crops, T


def test_incomplete_crop_generic_rot_clarifies_not_arecanut():
    """Incomplete crop + generic rot asks for crop confirmation, does not assume arecanut."""
    s = Session()
    # "ಕ್ಕೆ" is merely a dative case marker, not a crop. "ಕೊಳೆ" alone is generic rot.
    r = s.respond("ಕ್ಕೆ ಕೊಳೆ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?")
    assert r.meta["state"] == "ask_crop"
    assert s.crop is None
    assert s.problem is None
    assert not r.end
    assert "ಅಡಿಕೆ" not in r.meta.get("advisory_id", "")
    assert "ಕೊಳೆತ ಕಾಯಿಗಳನ್ನು" not in " ".join(r.sentences)


def test_generic_arecanut_disease_clarifies_symptoms_not_rot():
    """Generic arecanut disease asks to clarify symptoms, does not assume rot."""
    s = Session()
    # Crop is known ("ಅಡಿಕೆ"), but problem is generic ("ರೋಗಕ್ಕೆ")
    r = s.respond("ಅಡಿಕೆ ರೋಗಕ್ಕೆ ಏನು ಮಾಡಬೇಕಿವಾಗ? ಪರಿಹಾರ ಕೊಡಿ.")
    assert s.crop == "arecanut"
    assert s.problem is None
    assert r.meta["state"] == "ask_problem"
    assert "ಕೊಳೆತ ಕಾಯಿಗಳನ್ನು" not in " ".join(r.sentences)


def test_explicit_disease_negation_plus_low_yield_no_rot_advice():
    """Explicit disease negation + low-yield question clears rot and gives safe referral."""
    s = Session()
    r1 = s.respond("ಅಡಿಕೆ ಕೊಳೆ ರೋಗ ಬಂದಿದೆ")
    assert r1.meta["state"] == "advised"
    assert s.crop == "arecanut"
    assert s.problem == "arecanut_koleroga"

    # Farmer clarifies: no disease, but low fruit bearing
    r2 = s.respond("ಅಡಿಕೆಗೆ ರೋಗ ಬಂದಿಲ್ಲ, ಆದರೆ ಕಾಯಿ ತುಂಬ ಬಿಡ್ತಾ ಇಲ್ಲ ಗಿಡದಲ್ಲಿ. ಅದನ್ನ ಹೇಗೆ ಇಂಪ್ರೂವ್ ಮಾಡಬೇಕು?")
    assert r2.meta["state"] == "unsupported_yield"
    assert s.problem is None
    assert s.advised is False
    text = " ".join(r2.sentences)
    assert "ಕೊಳೆತ ಕಾಯಿಗಳನ್ನು" not in text
    assert "ಇಳುವರಿ" in text or "ಕಾಯಿ ಬಿಡದಿರುವ" in text
    assert "ಕೃಷಿ ಅಧಿಕಾರಿ" in text or "ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರ" in text


def test_arecanut_to_paddy_change_clears_old_problem():
    """Switching crop from arecanut to paddy clears old problem, stage, and advised state."""
    s = Session()
    s.respond("ಅಡಿಕೆ ಕೊಳೆ ರೋಗ ಬಂದಿದೆ")
    assert s.crop == "arecanut"
    assert s.problem == "arecanut_koleroga"

    # User switches to paddy with leaf folder symptom
    r2 = s.respond("ನಮ್ಮ ಭತ್ತದ ಗದ್ದೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ")
    assert s.crop == "paddy"
    assert s.problem == "paddy_leaf_folder"
    assert s.stage is None
    assert r2.meta["state"] == "ask_stage"


def test_generic_followup_does_not_repeat_full_advisory():
    """Generic follow-up query after advisory does not replay full multi-sentence advisory."""
    s = Session()
    r1 = s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert r1.meta["state"] == "advised"
    full_advice = " ".join(r1.sentences)

    # Generic follow-up without explicit repeat keyword
    r2 = s.respond("ಏನು ಮಾಡಬೇಕು?")
    assert r2.meta["state"] == "followup_options"
    followup_text = " ".join(r2.sentences)
    assert followup_text != full_advice
    assert "ಮತ್ತೆ ಕೇಳಬೇಕೆ" in followup_text


def test_explicit_repeat_request_replays_advisory():
    """Explicit repeat request replays the previous advisory."""
    s = Session()
    r1 = s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert r1.meta["state"] == "advised"

    r2 = s.respond("ಮತ್ತೆ ಹೇಳಿ")
    assert r2.meta["state"] == "advised"
    assert r2.meta.get("repeated") is True
    assert "ಬೆಂಕಿ ರೋಗ" in " ".join(r2.sentences)


def test_supported_paddy_leaf_folder_stage_question_still_works():
    """Supported paddy leaf folder symptom still triggers stage question and completes advisory."""
    s = Session()
    r1 = s.respond("ನಮ್ಮ ಭತ್ತದ ಗದ್ದೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ")
    assert r1.meta["state"] == "ask_stage"
    assert s.crop == "paddy"
    assert s.problem == "paddy_leaf_folder"

    r2 = s.respond("ಚಿಕ್ಕ ಗಿಡ")
    assert r2.meta["state"] == "advised"
    assert r2.meta["safety"] == "chemical_blocked_stage"
    assert s.stage == "seedling"


def test_disease_negation_helper_does_not_globally_negate():
    """Verify is_disease_negated requires association with disease/pest terms."""
    assert is_disease_negated("ರೋಗ ಬಂದಿಲ್ಲ") is True
    assert is_disease_negated("ಅಡಿಕೆಗೆ ರೋಗವಿಲ್ಲ") is True
    assert is_disease_negated("ಕೊಳೆ ಇಲ್ಲ") is True
    assert is_disease_negated("ಯಾವುದೇ ಕೀಟ ಇಲ್ಲ") is True
    assert is_disease_negated("no disease in paddy") is True

    # Global "ಇಲ್ಲ" or "ಬೇಡ" without disease must NOT negate disease
    assert is_disease_negated("ಕಾಯಿ ತುಂಬ ಬಿಡ್ತಾ ಇಲ್ಲ") is False
    assert is_disease_negated("ನಮ್ಮಲ್ಲಿ ನೀರು ಇಲ್ಲ") is False
    assert is_disease_negated("ಈಗ ಔಷಧ ಬೇಡ") is False


def test_known_crop_never_returns_another_crops_problem():
    """When crop is explicitly known, find_problem must never return another crop's problem."""
    # leaf folder belongs to paddy, not arecanut
    assert find_problem("ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ", crop="arecanut") is None
    # rhino beetle belongs to coconut, not paddy
    assert find_problem("ಕೊಂಬಿನ ದುಂಬಿ", crop="paddy") is None


def test_negated_arecanut_rot_no_low_yield_gives_no_rot_advisory():
    """Bug A: 'ಅಡಿಕೆಗೆ ಕೊಳೆ ರೋಗ ಇಲ್ಲ.' must not re-match rot and must ask for symptoms."""
    s = Session()
    r = s.respond("ಅಡಿಕೆಗೆ ಕೊಳೆ ರೋಗ ಇಲ್ಲ.")
    assert s.crop == "arecanut"
    assert s.problem is None
    assert r.meta["state"] == "ask_problem"
    assert "ಕೊಳೆತ ಕಾಯಿಗಳನ್ನು" not in " ".join(r.sentences)


def test_after_rot_advice_same_crop_different_problem_clarifies_no_stale_rot():
    """Bug B: After rot advice, 'ಅಡಿಕೆಗೆ ಬೇರೆ ಸಮಸ್ಯೆ ಇದೆ.' asks clarification without stale rot."""
    s = Session()
    r1 = s.respond("ಅಡಿಕೆ ಕೊಳೆ ರೋಗ ಬಂದಿದೆ")
    assert r1.meta["state"] == "advised"
    assert s.crop == "arecanut"
    assert s.problem == "arecanut_koleroga"

    r2 = s.respond("ಅಡಿಕೆಗೆ ಬೇರೆ ಸಮಸ್ಯೆ ಇದೆ.")
    assert r2.meta["state"] == "ask_problem"
    assert s.problem is None
    assert s.advised is False
    assert "ಕೊಳೆತ ಕಾಯಿಗಳನ್ನು" not in " ".join(r2.sentences)


def test_after_rot_advice_same_crop_generic_disease_no_automatic_replay():
    """Bug B: After rot advice, 'ಅಡಿಕೆ ರೋಗಕ್ಕೆ ಇನ್ನೇನು ಮಾಡಬೇಕು?' offers options, no auto replay."""
    s = Session()
    r1 = s.respond("ಅಡಿಕೆ ಕೊಳೆ ರೋಗ ಬಂದಿದೆ")
    assert r1.meta["state"] == "advised"

    r2 = s.respond("ಅಡಿಕೆ ರೋಗಕ್ಕೆ ಇನ್ನೇನು ಮಾಡಬೇಕು?")
    assert r2.meta["state"] == "followup_options"
    assert r2.sentences != r1.sentences
    assert "ಕೊಳೆತ ಕಾಯಿಗಳನ್ನು" not in " ".join(r2.sentences)


def test_mixed_negation_and_affirmation_preserves_affirmative_issue():
    """Mixed negation/affirmation: preserve affirmative issue and never advise negated one."""
    s = Session()
    # Paddy: blast is explicitly negated, leaf folder is affirmative
    r = s.respond("ಭತ್ತದಲ್ಲಿ ಬೆಂಕಿ ರೋಗ ಇಲ್ಲ, ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ.")
    assert s.crop == "paddy"
    assert s.problem == "paddy_leaf_folder"
    assert r.meta["state"] == "ask_stage"
    assert "ಬೆಂಕಿ ರೋಗ" not in r.meta.get("advisory_id", "")


def test_coconut_beetle_advisory_then_coconut_bud_rot_handles_bud_rot():
    """Coconut beetle advisory -> coconut bud rot -> handles bud rot correctly."""
    s = Session()
    r1 = s.respond("ತೆಂಗಿನ ಮರದಲ್ಲಿ ದುಂಬಿ ಕಾಟ ಇದೆ.")
    assert s.crop == "coconut"
    assert s.problem == "coconut_rhino_beetle"
    assert r1.meta["state"] == "advised"

    # User then states bud rot on the same coconut crop
    r2 = s.respond("ತೆಂಗಿನ ಸುಳಿ ಕೊಳೆತಿದೆ.")
    assert s.crop == "coconut"
    assert s.problem == "coconut_bud_rot"
    assert r2.meta["state"] == "advised"
    assert r2.meta["advisory_id"] == "coconut_bud_rot"
    assert "ಸುಳಿ ಕೊಳೆ" in " ".join(r2.sentences)


def test_paddy_blast_advisory_then_leaf_folder_asks_for_new_stage():
    """Paddy blast advisory -> leaf-folder symptoms -> asks for the new stage."""
    s = Session()
    r1 = s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ ಬಂದಿದೆ.")
    assert s.crop == "paddy"
    assert s.problem == "paddy_blast"
    assert r1.meta["state"] == "advised"

    # User mentions leaf-folder for paddy
    r2 = s.respond("ಭತ್ತದ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ.")
    assert s.crop == "paddy"
    assert s.problem == "paddy_leaf_folder"
    assert s.stage is None
    assert r2.meta["state"] == "ask_stage"


def test_old_stage_is_not_reused_for_different_problem():
    """Old stage from a previous problem is not reused for a different problem."""
    s = Session()
    s.respond("ನಮ್ಮ ಭತ್ತದ ಗದ್ದೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ")
    r2 = s.respond("ಚಿಕ್ಕ ಗಿಡ")
    assert s.stage == "seedling"
    assert r2.meta["state"] == "advised"

    # Farmer now states blast on paddy
    r3 = s.respond("ಗದ್ದೆಯಲ್ಲಿ ಬೆಂಕಿ ರೋಗ ಕೂಡ ಕಾಣ್ತಾ ಇದೆ.")
    assert s.problem == "paddy_blast"
    assert s.stage is None
    assert r3.meta["state"] == "advised"
    assert r3.meta["advisory_id"] == "paddy_blast"


def test_repeated_same_problem_gives_followup_options_not_full_replay():
    """Repeating the same problem gives follow-up options, not an automatic full advisory replay."""
    s = Session()
    r1 = s.respond("ಅಡಿಕೆ ಕೊಳೆ ರೋಗ ಬಂದಿದೆ.")
    assert r1.meta["state"] == "advised"
    full_text = " ".join(r1.sentences)

    # Repeating same problem with question
    r2 = s.respond("ಅಡಿಕೆ ಕೊಳೆ ರೋಗಕ್ಕೆ ಏನು ಮಾಡಬೇಕು?")
    assert r2.meta["state"] == "followup_options"
    assert " ".join(r2.sentences) != full_text
    assert "ಹಿಂದಿನ ಸಲಹೆಯನ್ನು ಮತ್ತೆ ಕೇಳಬೇಕೆ" in " ".join(r2.sentences)


def test_crop_with_no_registered_problems_has_no_cross_crop_match():
    """A crop with no registered problems never falls through to cross-crop problems."""
    # Wheat has no problems in PROBLEMS; passing wheat must return None, not paddy/coconut problems
    assert find_problem("ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ", crop="wheat") is None
    assert find_problem("ಸುಳಿ ಕೊಳೆತಿದೆ", crop="unknown_crop") is None
    assert find_problem("ದುಂಬಿ", crop="") is None


def test_capabilities_before_crop_identification():
    """Turn 1 capabilities request lists supported crops and prototype scope without ending."""
    s = Session()
    r = s.respond("ನಿಮ್ಮ ಬಳಿ ಯಾವ ಬೆಳೆಗಳಿಗೆ ಸಹಾಯ ಲಭ್ಯವಿದೆ?")
    assert r.meta["state"] == "capabilities"
    assert not r.end
    assert s.crop is None
    assert s.problem is None
    text = " ".join(r.sentences)
    assert "ಭತ್ತ" in text
    assert "ಅಡಿಕೆ" in text
    assert "ತೆಂಗು" in text
    assert "ಪ್ರಾಯೋಗಿಕ" in text


def test_capabilities_after_advisory():
    """Capabilities query after advisory does not erase last_advisory or dialogue state."""
    s = Session()
    r1 = s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert r1.meta["state"] == "advised"
    saved_adv = s.last_advisory
    assert saved_adv is not None

    r2 = s.respond("ಯಾವ ಬೆಳೆಗಳಿಗೆ ಸಲಹೆ ಕೊಡುತ್ತೀರಿ?")
    assert r2.meta["state"] == "capabilities"
    assert not r2.end
    assert s.last_advisory == saved_adv


def test_capabilities_while_awaiting_stage_then_stage_continues():
    """Capabilities in the middle of stage clarification preserves pending problem and allows continuation."""
    s = Session()
    r1 = s.respond("ಭತ್ತಕ್ಕೆ ಎಲೆ ಸುತ್ತು ಬಂದಿದೆ")
    assert r1.meta["state"] == "ask_stage"
    assert s.crop == "paddy"
    assert s.problem == "paddy_leaf_folder"

    r2 = s.respond("ನೀವು ಏನು ಮಾಡಬಹುದು?")
    assert r2.meta["state"] == "capabilities"
    assert not r2.end
    assert s.crop == "paddy"
    assert s.problem == "paddy_leaf_folder"

    # Farmer now provides stage
    r3 = s.respond("ಚಿಕ್ಕ ಗಿಡ")
    assert r3.meta["state"] == "advised"
    assert r3.meta["stage"] == "seedling"
    assert "ಸಸಿ ಹಂತ" in " ".join(r3.sentences)


def test_supported_coverage_does_not_overclaim_stub_crops():
    """Usable crops only includes crops with real non-stub entries."""
    crops = usable_crops()
    assert set(crops) == {"paddy", "arecanut", "coconut"}
    assert "sugarcane" not in crops
    assert "wheat" not in crops
    assert "grapes" not in crops

    s = Session()
    r = s.respond("what can you help with?")
    assert r.meta["state"] == "capabilities"
    text = " ".join(r.sentences)
    assert "ಕಬ್ಬು" not in text
    assert "ಗೋಧಿ" not in text


def test_natural_repeat_variant():
    """'ಮತ್ತೆ ಹೇಳ್ತೀರಾ ಇದನ್ನು?' repeats the last advisory."""
    s = Session()
    r1 = s.respond("ಅಡಿಕೆ ಕೊಳೆ ರೋಗ ಬಂದಿದೆ")
    assert r1.meta["state"] == "advised"

    r2 = s.respond("ಮತ್ತೆ ಹೇಳ್ತೀರಾ ಇದನ್ನು?")
    assert r2.meta.get("repeated") is True
    assert r2.sentences == r1.sentences


def test_repeating_pending_question():
    """'ಸರಿಯಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ, ಮತ್ತೆ ಹೇಳಿ' repeats a pending question."""
    s = Session()
    r1 = s.respond("ನನಗೆ ಸಹಾಯ ಬೇಕು")
    assert r1.meta["state"] == "ask_crop"

    r2 = s.respond("ಸರಿಯಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ, ಮತ್ತೆ ಹೇಳಿ")
    assert r2.meta.get("repeated") is True
    assert r2.meta["state"] == "ask_crop"
    assert r2.sentences == r1.sentences


def test_explicit_previous_advisory_repeat():
    """'ಹಿಂದಿನ ಸಲಹೆಯನ್ನು ಮತ್ತೆ ಹೇಳಿ' repeats previous advisory or explains if none exists."""
    # When advisory exists
    s1 = Session()
    r1 = s1.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert r1.meta["state"] == "advised"

    # Farmer asks generic follow-up
    r2 = s1.respond("ಏನು ಮಾಡಬೇಕು?")
    assert r2.meta["state"] == "followup_options"

    # Explicit previous advisory request
    r3 = s1.respond("ಹಿಂದಿನ ಸಲಹೆಯನ್ನು ಮತ್ತೆ ಹೇಳಿ")
    assert r3.meta.get("repeated") is True
    assert r3.sentences == r1.sentences

    # When no advisory exists yet
    s2 = Session()
    r4 = s2.respond("ಹಿಂದಿನ ಸಲಹೆಯನ್ನು ಮತ್ತೆ ಹೇಳಿ")
    assert r4.meta["state"] == "no_previous_advisory"
    assert "ಯಾವುದೇ ಹಿಂದಿನ ಸಲಹೆ ಲಭ್ಯವಿಲ್ಲ" in " ".join(r4.sentences)


def test_explicit_end_after_unsupported_yield():
    """Explicit end request after unsupported yield ends the call with bye state."""
    s = Session()
    r1 = s.respond("ಅಡಿಕೆಗೆ ರೋಗ ಬಂದಿಲ್ಲ, ಆದರೆ ಕಾಯಿ ತುಂಬ ಬಿಡ್ತಾ ಇಲ್ಲ ಗಿಡದಲ್ಲಿ. ಅದನ್ನ ಹೇಗೆ ಇಂಪ್ರೂವ್ ಮಾಡಬೇಕು?")
    assert r1.meta["state"] == "unsupported_yield"

    r2 = s.respond("ಧನ್ಯವಾದಗಳು, ನೀವು ಕರೆಯನ್ನು ಕಟ್ ಮಾಡಬಹುದು.")
    assert r2.end is True
    assert r2.meta["state"] == "bye"
    assert "ಧನ್ಯವಾದ" in " ".join(r2.sentences) or "ಕರೆ ಕೊನೆಗೊಳಿಸುತ್ತಿದ್ದೇನೆ" in " ".join(r2.sentences)


def test_explicit_end_while_awaiting_symptoms():
    """Explicit end request while in ask_problem terminates the session cleanly."""
    s = Session()
    r1 = s.respond("ಅಡಿಕೆ")
    assert r1.meta["state"] == "ask_problem"

    r2 = s.respond("ಕರೆ ಕಟ್ ಮಾಡಿ")
    assert r2.end is True
    assert r2.meta["state"] == "bye"


def test_negative_end_request_does_not_terminate():
    """Negative end request like 'ಕರೆ ಕಟ್ ಮಾಡಬೇಡಿ' does not end the call."""
    s = Session()
    r = s.respond("ಕರೆ ಕಟ್ ಮಾಡಬೇಡಿ, ನಮಗೆ ಭತ್ತದ ಬಗ್ಗೆ ಮಾಹಿತಿ ಬೇಕು")
    assert not r.end
    assert s.crop == "paddy"


def test_negative_repeat_request_does_not_replay():
    """Negative repeat request like 'ಮತ್ತೆ ಹೇಳಬೇಡಿ' does not replay."""
    s = Session()
    r1 = s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert r1.meta["state"] == "advised"

    r2 = s.respond("ಮತ್ತೆ ಹೇಳಬೇಡಿ, ಬೇರೆ ವಿಷಯ ಹೇಳಿ")
    assert not r2.meta.get("repeated", False)


def test_advisory_then_capabilities_then_general_repeat_repeats_capabilities():
    """Advisory followed by capabilities followed by general repeat repeats capabilities."""
    s = Session()
    r1 = s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert r1.meta["state"] == "advised"

    r2 = s.respond("ನಿಮ್ಮ ಬಳಿ ಯಾವ ಬೆಳೆಗಳಿಗೆ ಸಹಾಯ ಲಭ್ಯವಿದೆ?")
    assert r2.meta["state"] == "capabilities"

    # General repeat must repeat capabilities, not the older advisory
    r3 = s.respond("ಮತ್ತೆ ಹೇಳಿ")
    assert r3.meta.get("repeated") is True
    assert r3.meta["state"] == "capabilities"
    assert r3.sentences == r2.sentences
    assert r3.sms is None


def test_advisory_then_capabilities_then_explicit_advisory_repeat_repeats_advisory():
    """Advisory followed by capabilities followed by explicit repeat repeats previous advisory."""
    s = Session()
    r1 = s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert r1.meta["state"] == "advised"

    r2 = s.respond("ನೀವು ಏನು ಮಾಡಬಹುದು?")
    assert r2.meta["state"] == "capabilities"

    # Explicit previous-advisory repeat must repeat the advisory
    r3 = s.respond("ಹಿಂದಿನ ಸಲಹೆಯನ್ನು ಮತ್ತೆ ಹೇಳಿ")
    assert r3.meta.get("repeated") is True
    assert r3.meta["state"] == "advised"
    assert r3.sentences == r1.sentences
    assert r3.sms is None


def test_unsupported_yield_then_general_repeat_repeats_yield_guidance():
    """Unsupported-yield response followed by general repeat repeats the yield guidance."""
    s = Session()
    r1 = s.respond("ಅಡಿಕೆಗೆ ರೋಗ ಬಂದಿಲ್ಲ, ಆದರೆ ಕಾಯಿ ತುಂಬ ಬಿಡ್ತಾ ಇಲ್ಲ ಗಿಡದಲ್ಲಿ. ಅದನ್ನ ಹೇಗೆ ಇಂಪ್ರೂವ್ ಮಾಡಬೇಕು?")
    assert r1.meta["state"] == "unsupported_yield"

    r2 = s.respond("ಮತ್ತೆ ಹೇಳ್ತೀರಾ ಇದನ್ನು?")
    assert r2.meta.get("repeated") is True
    assert r2.meta["state"] == "unsupported_yield"
    assert r2.sentences == r1.sentences
    assert r2.sms is None


def test_repeated_pending_question_leaves_clarification_count_unchanged():
    """Repeating a pending question repeats question without increasing clarification attempts."""
    s = Session()
    r1 = s.respond("ನನಗೆ ಸಹಾಯ ಬೇಕು")
    assert r1.meta["state"] == "ask_crop"
    assert s.asks["crop"] == 1

    r2 = s.respond("ಮತ್ತೆ ಹೇಳಿ")
    assert r2.meta.get("repeated") is True
    assert r2.meta["state"] == "ask_crop"
    assert s.asks["crop"] == 1

    r3 = s.respond("ಸರಿಯಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ, ಮತ್ತೆ ಹೇಳಿ")
    assert r3.meta.get("repeated") is True
    assert r3.meta["state"] == "ask_crop"
    assert s.asks["crop"] == 1

    r4 = s.respond("ಮತ್ತೆ ಹೇಳ್ತೀರಾ?")
    assert r4.meta.get("repeated") is True
    assert r4.meta["state"] == "ask_crop"
    assert s.asks["crop"] == 1
    assert not r4.end


def test_capabilities_recognition_three_phrases_and_concrete_issue_guard():
    """Test the three capabilities phrases and protect against swallowing concrete issues."""
    # 1. "ನೀವು ಏನು ಮಾಡಬಹುದು?"
    s1 = Session()
    r1 = s1.respond("ನೀವು ಏನು ಮಾಡಬಹುದು?")
    assert r1.meta["state"] == "capabilities"
    assert "ಪ್ರಾಯೋಗಿಕ" in " ".join(r1.sentences)

    # 2. "ನಿಮ್ಮ ಬಳಿ ಯಾವ ಬೆಳೆಗಳಿಗೆ ಸಹಾಯ ಲಭ್ಯವಿದೆ?"
    s2 = Session()
    r2 = s2.respond("ನಿಮ್ಮ ಬಳಿ ಯಾವ ಬೆಳೆಗಳಿಗೆ ಸಹಾಯ ಲಭ್ಯವಿದೆ?")
    assert r2.meta["state"] == "capabilities"
    assert "ಭತ್ತ" in " ".join(r2.sentences)

    # 3. "ಯಾವ ಸಮಸ್ಯೆಗಳಿಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?"
    s3 = Session()
    r3 = s3.respond("ಯಾವ ಸಮಸ್ಯೆಗಳಿಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?")
    assert r3.meta["state"] == "capabilities"

    # Concrete crop issue protection: must NOT be swallowed by capabilities
    s4 = Session()
    r4 = s4.respond("ಭತ್ತದಲ್ಲಿ ಬೆಂಕಿ ರೋಗಕ್ಕೆ ನೀವು ಏನು ಮಾಡಬಹುದು?")
    assert r4.meta["state"] == "advised"
    assert "ಬೆಂಕಿ ರೋಗ" in " ".join(r4.sentences)


def test_general_repeat_when_last_is_none_uses_last_advisory_meta_and_no_sms():
    """When session.last is None and session.last_advisory exists, general repeat succeeds with sms=None and advisory meta."""
    s = Session()
    r1 = s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert r1.meta["state"] == "advised"
    assert s.last_advisory is not None

    # Explicitly clear session.last to simulate absent latest turn
    s.last = None

    r2 = s.respond("ಮತ್ತೆ ಹೇಳಿ")
    assert r2.meta.get("repeated") is True
    assert r2.meta["state"] == "advised"
    assert r2.meta["advisory_id"] == "paddy_blast"
    assert r2.sentences == r1.sentences
    assert r2.sms is None


def test_capabilities_content_and_placeholder_resolution():
    """Verify capabilities response resolves {crops}, lists usable crops, excludes stub crops, and preserves pending state."""
    s = Session()
    # Establish pending crop and problem state
    s.respond("ಭತ್ತಕ್ಕೆ ಎಲೆ ಸುತ್ತು ಬಂದಿದೆ")
    assert s.crop == "paddy"
    assert s.problem == "paddy_leaf_folder"
    assert s.stage is None

    # Farmer queries capabilities while pending
    r = s.respond("ನೀವು ಏನು ಮಾಡಬಹುದು?")
    assert r.meta["state"] == "capabilities"
    full_text = " ".join(r.sentences)

    # 1. No unresolved placeholders
    assert "{crops}" not in full_text
    assert "{" not in full_text and "}" not in full_text

    # 2. Lists actual usable KB crop names
    assert "ಭತ್ತ" in full_text
    assert "ಅಡಿಕೆ" in full_text
    assert "ತೆಂಗು" in full_text

    # 3. Does not overclaim stub-only coverage
    for stub_crop in ["ಕಬ್ಬು", "ದ್ರಾಕ್ಷಿ", "ದಾಳಿಂಬೆ", "ಮೆಕ್ಕೆಜೋಳ", "ಗೋಧಿ", "ರೇಷ್ಮೆ", "ಹತ್ತಿ"]:
        assert stub_crop not in full_text

    # 4. Preserves pending crop/problem/stage state
    assert s.crop == "paddy"
    assert s.problem == "paddy_leaf_folder"
    assert s.stage is None


def test_paddy_leaf_folder_draft_intake_workflow_seven_turns():
    """Verify bounded 7-turn intake for paddy_leaf_folder, safety warnings, and gate preservation."""
    s = Session()
    # Initial statement sets paddy + leaf folder
    r0 = s.respond("ಭತ್ತಕ್ಕೆ ಎಲೆ ಸುತ್ತು ಬಂದಿದೆ")
    assert r0.meta["state"] == "ask_stage"

    # Farmer asks about chemical spray, triggering intake start
    r1 = s.respond("ಇದಕ್ಕೆ ಯಾವ ಔಷಧ ಸಿಂಪಡಿಸಬೇಕು?")
    assert r1.meta["state"] == "ask_intake_symptoms"
    assert r1.meta["step"] == "symptoms"
    assert "ಬಿಳಿಯ ಪಾರದರ್ಶಕ ಪಟ್ಟಿಗಳು" in " ".join(r1.sentences)

    # Step 1 -> Step 2: symptoms affirmative
    r2 = s.respond("ಹೌದು ಬಿಳಿ ಗೆರೆ ಕಂಡಿದೆ")
    assert r2.meta["step"] == "live_larvae"
    assert s.leaf_folder_intake["symptoms"] is True
    assert "ಜೀವಂತ ಹಸಿರು ಹುಳುಗಳು" in " ".join(r2.sentences)

    # Step 2 -> Step 3: live larvae answer "don't know" - must NOT turn into affirmative True
    r3 = s.respond("ಗೊತ್ತಿಲ್ಲ, ನೋಡಿಲ್ಲ")
    assert r3.meta["step"] == "stage"
    assert s.leaf_folder_intake["live_larvae"] == "unknown"
    assert "ಹಂತದಲ್ಲಿದೆ" in " ".join(r3.sentences)

    # Step 3 -> Step 4: stage (tillering / ಕವಲೊಡೆಯುವ)
    r4 = s.respond("ಕವಲೊಡೆಯುವ ಹಂತದಲ್ಲಿದೆ")
    assert r4.meta["step"] == "leaf_counts"
    assert s.leaf_folder_intake["stage"] == "tillering"
    assert "ಪರಿಶೀಲಿಸಿದ ಒಟ್ಟು ಎಲೆಗಳಲ್ಲಿ" in " ".join(r4.sentences)

    # Step 4 -> Step 5: leaf counts (affected and total)
    r5 = s.respond("ನೂರು ಎಲೆಗಳಲ್ಲಿ ಹದಿನೈದು ಎಲೆಗಳು ಸುತ್ತಿಕೊಂಡಿವೆ")
    assert r5.meta["step"] == "harvest_days"
    assert "ನೂರು ಎಲೆಗಳಲ್ಲಿ ಹದಿನೈದು" in s.leaf_folder_intake["leaf_counts"]
    assert "ಬೆಳೆ ಕಟಾವಿಗೆ ಇನ್ನೂ" in " ".join(r5.sentences)

    # Step 5 -> Step 6: harvest days (30 days - below PHI of 47 days)
    r6 = s.respond("ಕಟಾವಿಗೆ ಮೂವತ್ತು ದಿನಗಳಿವೆ")
    assert r6.meta["step"] == "nearby_mulberry"
    assert s.leaf_folder_intake["harvest_days"] == 30
    assert "ಹಿಪ್ಪುನೇರಳೆ" in " ".join(r6.sentences)

    # Step 6 -> Step 7: nearby mulberry (yes, silkworm nearby)
    r7 = s.respond("ಹೌದು, ಪಕ್ಕದಲ್ಲೇ ರೇಷ್ಮೆ ತೋಟ ಇದೆ")
    assert r7.meta["step"] == "recent_pesticides"
    assert s.leaf_folder_intake["nearby_mulberry"] is True
    assert "ಯಾವುದಾದರೂ ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸಿದ್ದೀರಾ" in " ".join(r7.sentences)

    # Step 7 -> Summary: recent pesticides (unknown product)
    r8 = s.respond("ಹೌದು ಸಿಂಪಡಿಸಿದ್ದೆ ಆದರೆ ಔಷಧ ಹೆಸರು ನೆನಪಿಲ್ಲ")
    assert r8.meta["state"] == "leaf_folder_intake_complete"
    assert "ಔಷಧ ಹೆಸರು ನೆನಪಿಲ್ಲ" in s.leaf_folder_intake["recent_pesticides"]

    full_reply = " ".join(r8.sentences)
    # Check mulberry hazard warning is triggered (identifying conservative app policy)
    assert "ರೇಷ್ಮೆ ಹುಳುಗಳಿಗೆ ವಿಷಕಾರಿ" in full_reply
    assert "ಔಷಧ ಹರಡದಂತೆ ತಡೆಯುವುದು ಕಡ್ಡಾಯ" in full_reply
    assert "ನಮ್ಮ ವ್ಯವಸ್ಥೆಯ ಸುರಕ್ಷತಾ ನೀತಿಯಂತೆ" in full_reply
    # Check preharvest days hazard warning is triggered (30 < 47)
    assert "ಕಟಾವಿನ ಕಾಯುವ ಅವಧಿ ನಲವತ್ತೇಳು ದಿನಗಳಾಗಿದ್ದು" in full_reply
    # Check PPE and re-entry wording: at least 24 hours AND until sprays dried
    assert "ರಕ್ಷಣಾ ಉಡುಪು" in full_reply
    assert "ಕನಿಷ್ಠ ಇಪ್ಪತ್ನಾಲ್ಕು ಗಂಟೆಗಳು ಹಾಗೂ ಔಷಧ ಸಂಪೂರ್ಣ ಒಣಗುವವರೆಗೆ" in full_reply
    # Check truthful product-status statement (not universal legal rule)
    assert "ಈ ಮಾದರಿಯ ರಾಸಾಯನಿಕ ಸಲಹೆಯನ್ನು ಇನ್ನೂ ವೃತ್ತಿಪರವಾಗಿ ಪರಿಶೀಲಿಸಿಲ್ಲ" in full_reply
    assert "ಆದ್ದರಿಂದ ಇದನ್ನು ಸಕ್ರಿಯಗೊಳಿಸಲಾಗಿಲ್ಲ" in full_reply

    # Critical safety assertion: chemical recommendation MUST NOT be spoken, reviewed MUST be False
    assert r8.meta["safety"] == "chemical_unreviewed"
    assert r8.meta["reviewed"] is False
    assert "ಶಿಫಾರಸು ಮಾಡಿದ ಔಷಧ" not in full_reply


def test_intake_unknown_answers_do_not_become_affirmative():
    """Answering unknown or uncertain across intake must not flip into affirmative True."""
    s = Session()
    s.respond("ಭತ್ತ")
    s.respond("ಎಲೆ ಸುತ್ತು")
    s.respond("ಔಷಧ ಸಿಂಪರಣೆ")

    # Symptoms step: answer unknown
    r1 = s.respond("ತಿಳಿದಿಲ್ಲ")
    assert s.leaf_folder_intake["symptoms"] == "unknown"

    # Larvae step: answer unknown
    r2 = s.respond("ಗೊತ್ತಿಲ್ಲ")
    assert s.leaf_folder_intake["live_larvae"] == "unknown"

    # Stage step: answer unknown
    r3 = s.respond("ಗೊತ್ತಿಲ್ಲ ಹಂತ")
    assert s.leaf_folder_intake["stage"] == "unknown"

    # Leaf counts: answer unknown
    r4 = s.respond("ಎಣಿಸಿಲ್ಲ")
    assert s.leaf_folder_intake["leaf_counts"] == "unknown"

    # Harvest days: answer unknown
    r5 = s.respond("ಗೊತ್ತಿಲ್ಲ ಎಷ್ಟು ದಿನ ಅಂತ")
    assert s.leaf_folder_intake["harvest_days"] == "unknown"

    # Nearby mulberry: answer negative
    r6 = s.respond("ಇಲ್ಲ ಯಾವುದೇ ರೇಷ್ಮೆ ತೋಟ ಇಲ್ಲ")
    assert s.leaf_folder_intake["nearby_mulberry"] is False

    # Recent pesticides: answer negative
    r7 = s.respond("ಯಾವುದೂ ಸಿಂಪಡಿಸಿಲ್ಲ")
    assert s.leaf_folder_intake["recent_pesticides"] is False

    assert r7.meta["state"] == "leaf_folder_intake_complete"
    assert r7.meta["safety"] == "chemical_unreviewed"
    assert r7.meta["reviewed"] is False
    # When mulberry is False and harvest is unknown, specific hazard triggers should not fire
    full_text = " ".join(r7.sentences)
    assert "ಹಿಪ್ಪುನೇರಳೆ ತೋಟ ಮತ್ತು ರೇಷ್ಮೆ ಹುಳು ಕೇಂದ್ರಗಳಿಗೆ" not in full_text
    # But general PPE / re-entry and truthful product-status notice must remain
    assert "ರಕ್ಷಣಾ ಉಡುಪು" in full_text
    assert "ಕನಿಷ್ಠ ಇಪ್ಪತ್ನಾಲ್ಕು ಗಂಟೆಗಳು ಹಾಗೂ ಔಷಧ ಸಂಪೂರ್ಣ ಒಣಗುವವರೆಗೆ" in full_text
    assert "ಈ ಮಾದರಿಯ ರಾಸಾಯನಿಕ ಸಲಹೆಯನ್ನು ಇನ್ನೂ ವೃತ್ತಿಪರವಾಗಿ ಪರಿಶೀಲಿಸಿಲ್ಲ" in full_text


def test_kb_paddy_leaf_folder_draft_evidence_record_structure():
    """Verify structured draft evidence record in app/kb.json with PPQS label details and reviewed=False."""
    adv = KB["paddy_leaf_folder"]
    chem = adv["chemical"]
    assert chem["reviewed"] is False
    assert chem["product"] == "ಕ್ಲೋರಾಂಟ್ರಾನಿಲಿಪ್ರೋಲ್ ೧೮.೫% ಎಸ್.ಸಿ."
    assert chem["dose"] == "೧೫೦ ಮಿಲಿ/ಹೆಕ್ಟೇರ್"
    assert chem["water"] == "೫೦೦ ಲೀಟರ್/ಹೆಕ್ಟೇರ್"
    assert chem["preharvest_days"] == "೪೭"
    assert "ppqs.gov.in" in chem["source"]

    draft = chem["draft_evidence"]
    assert draft["status"] == "DRAFT - NOT ENABLED - PROFESSIONAL REVIEW PENDING"
    assert draft["active_ingredient"] == "Chlorantraniliprole"
    assert draft["formulation"] == "18.5% w/w SC"
    assert draft["dose_original_units"] == "150 ml/ha (30 g a.i./ha)"
    assert draft["dilution_original_units"] == "500 L water/ha"
    assert draft["preharvest_interval_days"] == 47
    assert "https://ppqs.gov.in/sites/default/files/chlorantraniliprole_18.5_sc93ffmc_india_private_limited_1.pdf" == draft["source_url"]
    assert "at least 24 hours AND until sprays have dried" in draft["re_entry_conditions"]
    assert draft["ppe_requirements"] == [
        "Protective clothing (long-sleeved shirt and long pants)",
        "Chemical-resistant gloves",
        "Mask",
        "Goggles",
        "Covered shoes",
    ]
    assert "toxic to silkworms" in draft["silkworm_mulberry_warning"].lower()
    assert "prevent drift" in draft["silkworm_mulberry_warning"].lower()
    assert "application policy" in draft["silkworm_mulberry_warning"].lower()


def test_unsupported_crop_four_utterances_diagnosis():
    """Verify the exact four-utterance sequence from diagnosis handles unsupported crop gracefully without symptom loops or auto-escalation."""
    s = Session()
    # Turn 1: "ನಾನು ಕಬ್ಬಿಗೆ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?"
    r1 = s.respond("ನಾನು ಕಬ್ಬಿಗೆ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?")
    assert r1.meta["state"] == "unsupported_crop"
    assert s.crop == "sugarcane"
    assert not r1.end
    t1 = " ".join(r1.sentences)
    assert "ಕಬ್ಬು ಬೆಳೆಗೆ ಪರಿಹಾರ ಅಥವಾ ಚಿಕಿತ್ಸಾ ಸಲಹೆ ಸದ್ಯಕ್ಕೆ ನನ್ನಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ" in t1
    assert "ಕೃಷಿ ಅಧಿಕಾರಿ ಅಥವಾ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರವನ್ನು ಸಂಪರ್ಕಿಸಿ" in t1
    assert "ಭತ್ತ, ಅಡಿಕೆ ಮತ್ತು ತೆಂಗು" in t1
    assert "ಬೆಳೆಯಲ್ಲಿ ಏನು ಸಮಸ್ಯೆ ಕಾಣುತ್ತಿದೆ" not in t1

    # Turn 2: "ನಮ್ಮದು ಕಬ್ಬು."
    r2 = s.respond("ನಮ್ಮದು ಕಬ್ಬು.")
    assert r2.meta["state"] == "unsupported_crop"
    assert not r2.end
    assert "ಕಬ್ಬು ಬೆಳೆಗೆ ಪರಿಹಾರ" in " ".join(r2.sentences)
    assert "ಬೆಳೆಯಲ್ಲಿ ಏನು ಸಮಸ್ಯೆ ಕಾಣುತ್ತಿದೆ" not in " ".join(r2.sentences)

    # Turn 3: "ನನ್ನ ಕಬ್ಬಿನ ಬೆಳೆಯಲ್ಲಿ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಲಿ?"
    r3 = s.respond("ನನ್ನ ಕಬ್ಬಿನ ಬೆಳೆಯಲ್ಲಿ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಲಿ?")
    assert r3.meta["state"] == "unsupported_crop"
    assert not r3.end
    assert "ಬೆಳೆಯಲ್ಲಿ ಏನು ಸಮಸ್ಯೆ ಕಾಣುತ್ತಿದೆ" not in " ".join(r3.sentences)

    # Turn 4: "ಕಬ್ಬಿನ ಬೇರಿಗೆ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?"
    r4 = s.respond("ಕಬ್ಬಿನ ಬೇರಿಗೆ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?")
    assert r4.meta["state"] == "unsupported_crop"
    assert not r4.end
    assert r4.meta.get("safety") != "escalated"
    assert s.asks["problem"] == 0


def test_unsupported_crop_to_supported_crop_continuation():
    """Farmer can freely switch from unsupported crop (sugarcane) to supported crop (paddy)."""
    s = Session()
    r1 = s.respond("ಕಬ್ಬಿಗೆ ರೋಗ ಬಂದಿದೆ")
    assert r1.meta["state"] == "unsupported_crop"
    assert s.crop == "sugarcane"

    # Switch to supported crop with specific problem
    r2 = s.respond("ನನ್ನ ಭತ್ತದ ಗದ್ದೆಯಲ್ಲಿ ಬೆಂಕಿ ರೋಗ ಬಂದಿದೆ")
    assert r2.meta["state"] == "advised"
    assert s.crop == "paddy"
    assert s.problem == "paddy_blast"
    assert "ಭತ್ತ ಬೆಳೆಯ ಬೆಂಕಿ ರೋಗ ಬಗ್ಗೆ ಕೇಳುತ್ತಿದ್ದೀರಿ" in " ".join(r2.sentences)


def test_explicit_end_after_unsupported_response():
    """Farmer can explicitly end call after receiving unsupported crop response."""
    s = Session()
    r1 = s.respond("ಕಬ್ಬಿಗೆ ರೋಗ ಬಂದಿದೆ")
    assert r1.meta["state"] == "unsupported_crop"
    assert not r1.end

    r2 = s.respond("ಧನ್ಯವಾದಗಳು, ನೀವು ಕರೆಯನ್ನು ಕಟ್ ಮಾಡಬಹುದು.")
    assert r2.meta["state"] == "bye"
    assert r2.end is True


def test_unsupported_crop_switch_has_no_stale_previous_crop_advice():
    """Switching to unsupported crop clears earlier advice reference and prevents stale advisory replay."""
    s = Session()
    r1 = s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert r1.meta["state"] == "advised"
    assert s.last_advisory is not None

    # Switch to unsupported crop
    r2 = s.respond("ಕಬ್ಬಿಗೆ ರೋಗ ಬಂದಿದೆ")
    assert r2.meta["state"] == "unsupported_crop"
    assert s.crop == "sugarcane"
    assert s.last_advisory is None

    # General repeat repeats the unsupported crop message, NOT blast advice
    r3 = s.respond("ಮತ್ತೆ ಹೇಳಿ")
    assert r3.meta["state"] == "unsupported_crop"
    assert r3.sentences == r2.sentences
    assert "ಬೆಂಕಿ ರೋಗ" not in " ".join(r3.sentences)

    # Specific previous advisory replay states no advisory exists
    r4 = s.respond("ಹಿಂದಿನ ಸಲಹೆಯನ್ನು ಮತ್ತೆ ಹೇಳಿ")
    assert r4.meta["state"] == "no_previous_advisory"
    assert "ಬೆಂಕಿ ರೋಗ" not in " ".join(r4.sentences)


def test_greeting_privacy_statement_audio_not_recorded_text_logged():
    """Initial greeting accurately reflects that audio is not recorded and conversation text is logged."""
    assert "ಧ್ವನಿಯನ್ನು ರೆಕಾರ್ಡ್ ಮಾಡುವುದಿಲ್ಲ" in T["greeting"][1]
    assert "ಸಂಭಾಷಣೆಯ ಪಠ್ಯವನ್ನು ದಾಖಲಿಸಿಕೊಳ್ಳಲಾಗುತ್ತದೆ" in T["greeting"][1]






