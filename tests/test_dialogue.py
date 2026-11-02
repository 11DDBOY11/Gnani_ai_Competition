import copy
from app import dialogue as d
from app.dialogue import Session, chemical_allowed, KB, T


def test_full_paddy_flow_blocks_chemical_for_seedling():
    s = Session()
    assert s.respond("ನಮ್ಮ ಭತ್ತದ ಗದ್ದೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತಿಕೊಂಡಿದೆ").meta["state"] == "ask_stage"
    r2 = s.respond("ಚಿಕ್ಕ ಗಿಡ")
    assert r2.meta["state"] == "advised" and r2.meta["safety"] == "chemical_blocked_stage"


def test_asks_crop_then_problem():
    s = Session()
    assert s.respond("ಸಹಾಯ ಬೇಕು").meta["state"] == "ask_crop"
    assert s.respond("ಅಡಿಕೆ").meta["state"] == "ask_problem"
    assert s.respond("ಕಾಯಿ ಕೊಳೆತಿದೆ").meta["advisory_id"] == "arecanut_koleroga"


def test_problem_alone_infers_crop():
    assert Session().respond("ಸುಳಿ ಕೊಳೆತಿದೆ").meta["advisory_id"] == "coconut_bud_rot"


def test_bud_rot_not_confused_with_koleroga():
    assert d.find_problem("ತೆಂಗಿನ ಸುಳಿ ಕೊಳೆತಿದೆ") == "coconut_bud_rot"
    assert d.find_problem("ಅಡಿಕೆ ಕೊಳೆ ರೋಗ ಬಂದಿದೆ") == "arecanut_koleroga"


def test_escalates_after_two_failed_clarifications():
    s = Session()
    assert s.respond("ಹ್ಞೂಂ").meta["state"] == "ask_crop"
    assert s.respond("ಗೊತ್ತಿಲ್ಲ").meta["state"] == "ask_crop"
    r = s.respond("ಏನೋ")
    assert r.end and r.meta["state"] == "escalated"


def test_english_and_codemix():
    assert d.find_crop("my paddy has leaf folder") == "paddy"
    assert d.find_problem("ಭತ್ತ leaf folder") == "paddy_leaf_folder"


def test_goodbye_and_repeat():
    s = Session()
    s.respond("ಭತ್ತ ಬೆಂಕಿ ರೋಗ")
    assert s.respond("ಮತ್ತೆ ಹೇಳಿ").meta["state"] == "advised"
    assert s.respond("ಧನ್ಯವಾದ").end


def test_no_shipped_advisory_speaks_chemicals():
    for aid, adv in KB.items():
        assert chemical_allowed(adv, None) is False, aid
        for stage in (None, "seedling", "flowering"):
            s = Session(); s.crop, s.problem, s.stage = adv["crop"], aid, stage
            assert "ಶಿಫಾರಸು ಮಾಡಿದ ಔಷಧ" not in " ".join(s._advise(adv).sentences)


def test_chemical_requires_every_field_and_reviewed_flag():
    adv = copy.deepcopy(KB["paddy_blast"])
    full = {"reviewed": True, "product": "X", "dose": "y", "water": "z", "preharvest_days": "ಹತ್ತು",
            "source": "UAS", "reviewed_by": "Dr A", "review_date": "2026-11-05"}
    adv["chemical"] = dict(full)
    assert chemical_allowed(adv, None) is True
    for k in full:
        a = copy.deepcopy(adv); a["chemical"][k] = None if k != "reviewed" else False
        assert chemical_allowed(a, None) is False, k


def test_chemical_blocked_in_blocked_stage_even_if_reviewed():
    adv = copy.deepcopy(KB["paddy_leaf_folder"])
    adv["chemical"] = {"reviewed": True, "product": "X", "dose": "y", "water": "z", "preharvest_days": "a",
                       "source": "s", "reviewed_by": "r", "review_date": "d"}
    assert chemical_allowed(adv, "seedling") is False
    assert chemical_allowed(adv, "flowering") is True


def test_all_prompts_have_no_ascii_digits_for_tts():
    import re
    texts = [s for v in T.values() for s in v] + [s for a in KB.values() for v in a["advice_kn"].values() for s in v]
    assert not [t for t in texts if re.search(r"\d", t)]
