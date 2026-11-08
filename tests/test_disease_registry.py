from app.dialogue import DISEASE_REGISTRY, KB, PROBLEMS, find_problem
from app.diseases import match_disease, match_symptoms, rank_disease_candidates


def test_registry_advisory_flags_follow_existing_nonempty_kb_advice():
    expected = {"paddy_leaf_folder", "paddy_blast", "arecanut_koleroga",
                "coconut_rhino_beetle", "coconut_bud_rot"}
    assert {d.id for d in DISEASE_REGISTRY if d.has_advisory} == expected
    assert all(d.id in KB for d in DISEASE_REGISTRY if d.has_advisory)
    assert all(not d.has_advisory for d in DISEASE_REGISTRY if d.id not in KB)


def test_registry_carries_existing_aliases_and_corrects_brown_spot_label():
    aliases = {d.id: set(d.aliases) for d in DISEASE_REGISTRY}
    confirm_aliases = {d.id: set(d.confirmation_aliases) for d in DISEASE_REGISTRY}
    assert {"ಎಲೆ ಸುತ್ತ", "ಎಲೆ ಮಡಚ", "ಸುತ್ತಿಕೊಂಡ", "ಸುತ್ತಿಕೊಳ್ಳ", "leaf folder", "leaf roll", "leaf fold"} <= aliases["paddy_leaf_folder"]
    assert {"ಕೊಂಬಿನ ದುಂಬಿ", "rhinoceros beetle", "rhino beetle"} <= aliases["coconut_rhino_beetle"]
    assert {"ದುಂಬಿ", "beetle"} <= confirm_aliases["coconut_rhino_beetle"]
    assert "ಕಂದು ಚುಕ್ಕೆ" not in aliases["paddy_blast"]
    assert "ಕಂದು ಚುಕ್ಕೆ" in aliases["paddy_brown_spot"]
    assert set(PROBLEMS) == {d.id for d in DISEASE_REGISTRY if d.has_advisory}


def test_exact_disease_matching_handles_roman_kannada_and_crop_scope():
    result = match_disease("bhatta ge benki roga", "paddy", DISEASE_REGISTRY)
    assert result.ids == ("paddy_blast",)
    assert result.method == "exact" and result.score > 0 and not result.needs_confirm
    assert result.crops_involved == ("paddy",)

    brown_spot = match_disease("ಭತ್ತದಲ್ಲಿ ಕಂದು ಚುಕ್ಕೆ ರೋಗ ಬಂದಿದೆ", "paddy", DISEASE_REGISTRY)
    assert brown_spot.ids == ("paddy_brown_spot",)
    assert brown_spot.ids != ("paddy_blast",)


def test_exact_ambiguous_aliases_and_ascii_word_boundaries():
    leaf_spot = match_disease("ಎಲೆ ಚುಕ್ಕೆ ರೋಗ", None, DISEASE_REGISTRY)
    assert set(leaf_spot.ids) == {"coconut_leaf_spot", "arecanut_leaf_spot"}
    assert leaf_spot.ambiguous and leaf_spot.needs_confirm
    assert set(leaf_spot.crops_involved) == {"coconut", "arecanut"}

    bud_rot_arecanut = match_disease("ಮೊಗ್ಗು ಕೊಳೆ ರೋಗ", "arecanut", DISEASE_REGISTRY)
    assert bud_rot_arecanut.ids == ("arecanut_bud_rot",)
    assert match_disease("budget for next year", None, DISEASE_REGISTRY).ids == ()


def test_fuzzy_match_is_returned_for_confirmation_and_never_from_wrapper():
    result = match_disease("ಅಡಿಕೆಗೆ ಕೊಲೆ ರೋಗ ಬಂದಿದೆ", "arecanut", DISEASE_REGISTRY)
    assert result.method == "fuzzy"
    assert result.ids == ("arecanut_koleroga",)
    assert result.needs_confirm
    assert find_problem("ಅಡಿಕೆಗೆ ಕೊಲೆ ರೋಗ ಬಂದಿದೆ", "arecanut") is None


def test_symptom_groups_and_crop_scoped_candidate_ranking():
    yellowing = match_symptoms("my coconut leaves are turning yellow")
    assert yellowing == frozenset({"yellowing"})
    candidates = rank_disease_candidates(yellowing, "coconut", DISEASE_REGISTRY)
    assert [(c.id, c.score) for c in candidates[:2]] == [
        ("coconut_basal_stem_rot", 1),
        ("coconut_root_wilt", 1),
    ]

    combined = match_symptoms("yellow leaves and oozing trunk")
    ranked = rank_disease_candidates(combined, "coconut", DISEASE_REGISTRY)
    assert ranked[0].id == "coconut_basal_stem_rot"
    assert ranked[0].score == 2

    brown_spot_symptoms = match_symptoms("brown spots on leaves and grain damage")
    ranked = rank_disease_candidates(brown_spot_symptoms, "paddy", DISEASE_REGISTRY)
    assert ranked[0].id == "paddy_brown_spot"


def test_symptom_matcher_avoids_short_or_unrelated_text():
    for text in ("", "what is the weather today", "budget for next year", "ನಮಸ್ಕಾರ", "ರೋಗ"):
        assert match_symptoms(text) == frozenset()
    assert rank_disease_candidates({"yellowing"}, None, DISEASE_REGISTRY) == ()
