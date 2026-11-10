"""Focused tests for Krishi Mitra Solution Hub (Phase 2 Local Implementation).

Verifies:
1. Feature disabled preserves existing Ask path.
2. Unverified sources are excluded from retrieval.
3. Unapproved actions cannot reach public output.
4. Kannada output cannot use unreviewed Kannada action text.
5. Crop isolation is strictly enforced.
6. Ambiguous symptoms do not select disease treatment.
7. Invalid action IDs cause safe clarification/referral.
8. Citation IDs and URLs come only from stored metadata.
9. Internal chemical fields never enter model context, text, or TTS.
10. No-evidence cases do not fall back to unsourced model recommendations.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from app import agri_search, solution_hub
from app.config import cfg


@pytest.mark.asyncio
async def test_feature_flag_disabled_preserves_current_path():
    """When SOLUTION_HUB_ENABLED is false, existing Groq path is used."""
    with patch.object(cfg, "solution_hub_enabled", False):
        with patch("app.agri_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.json = lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "answer": "Existing Groq prompt response.",
                            "confidence": "high",
                            "needs_expert_review": False,
                            "sources": []
                        })
                    }
                }]
            }
            mock_response.raise_for_status = lambda: None
            mock_client.post = AsyncMock(return_value=mock_response)

            with patch.dict("os.environ", {"GROQ_API_KEY": "fake_test_key"}):
                res = await agri_search.generate_agri_answer("Test question", language="en")
                assert res["answer"] == "Existing Groq prompt response."
                assert res["sources"] == []


@pytest.mark.asyncio
async def test_unverified_sources_are_excluded():
    """Unverified sources like coconut bud rot and arecanut koleroga are excluded."""
    # Coconut Bud Rot
    res_coconut = await solution_hub.generate_solution_hub_answer(
        "My coconut trees have bud rot (ಕುಳೆ ರೋಗ). What should I do?",
        language="en",
        allow_inspection=True,
    )
    assert res_coconut["sources"] == []
    assert res_coconut["needs_expert_review"] is True
    assert "currently unverified" in res_coconut["answer"].lower()
    assert "1800-180-1551" in res_coconut["answer"]

    # Arecanut Koleroga
    res_areca = await solution_hub.generate_solution_hub_answer(
        "Arecanut koleroga ಕೊಳೆರೋಗ control",
        language="en",
        allow_inspection=True,
    )
    assert res_areca["sources"] == []
    assert "currently unverified" in res_areca["answer"].lower()


@pytest.mark.asyncio
async def test_unapproved_actions_cannot_reach_public_output():
    """In public mode (allow_inspection=False), unapproved actions are never emitted."""
    res = await solution_hub.generate_solution_hub_answer(
        "Paddy blast disease control",
        language="en",
        crop="paddy",
        allow_inspection=False,  # Public mode
    )
    # Since all current actions have public_release_approved: false
    assert "pending expert agronomy and safety review" in res["answer"].lower()
    assert "Unreviewed actions are not released as public advice." in res["answer"]
    assert "1800-180-1551" in res["answer"]


@pytest.mark.asyncio
async def test_kannada_output_cannot_use_unreviewed_kannada_action_text():
    """Kannada requests for unreviewed Kannada text return explicit explanation, not machine translation."""
    res = await solution_hub.generate_solution_hub_answer(
        "ಭತ್ತದ ಬೆಂಕಿ ರೋಗಕ್ಕೆ ಪರಿಹಾರವೇನು?",
        language="kn",
        crop="paddy",
        allow_inspection=True,
    )
    assert solution_hub.KANNADA_REVIEW_UNAVAILABLE in res["answer"]
    assert "1800-180-1551" in res["answer"]


@pytest.mark.asyncio
async def test_crop_isolation():
    """Paddy queries can only access paddy records and cannot cross into other crops."""
    records = solution_hub.load_records()
    paddy_actions = {
        a["action_id"]
        for r in records["records"] if r["crop_id"] == "paddy"
        for a in r.get("supported_actions", [])
    }
    
    with patch("app.solution_hub.select_action_ids_via_groq", AsyncMock(return_value=["ACT-BLAST-WATER-04"])):
        res = await solution_hub.generate_solution_hub_answer(
            "Paddy leaf blast symptoms",
            language="en",
            crop="paddy",
            allow_inspection=True,
        )
        assert "blast" in res["answer"].lower()
        assert "ACT-BLAST-WATER-04" not in paddy_actions or "paddy field" in res["answer"].lower()
        # Ensure sources belong to paddy
        for s in res["sources"]:
            assert "rice" in s["title"].lower() or "blast" in s["title"].lower()


@pytest.mark.asyncio
async def test_ambiguous_symptoms_do_not_select_disease_treatment():
    """Ambiguous symptoms (yellow leaves in paddy) trigger clarification, not treatments."""
    res = await solution_hub.generate_solution_hub_answer(
        "My paddy leaves are turning yellow. What should I do?",
        language="en",
        crop="paddy",
        allow_inspection=True,
    )
    # Must be clarification questions, not treatment actions or chemicals
    assert res["sources"] == []
    assert "ambiguous" in res["answer"].lower()
    assert "A match is not a confirmed diagnosis" in res["answer"]
    assert "1800-180-1551" in res["answer"]
    # Check that blast actions were NOT retrieved
    assert "Maintain recommended water levels" not in res["answer"]
    assert "certified seeds" not in res["answer"]


@pytest.mark.asyncio
async def test_invalid_action_ids_cause_safe_defaults():
    """If model returns hallucinated or invalid IDs, server drops them and selects safe non-sensitive defaults."""
    with patch("app.solution_hub.select_action_ids_via_groq", AsyncMock(return_value=["ACT-HALLUCINATED-999"])):
        res = await solution_hub.generate_solution_hub_answer(
            "Paddy leaf folder damage observed",
            language="en",
            crop="paddy",
            allow_inspection=True,
        )
        # Server must not crash or output hallucinated ID; uses safe non-context-sensitive defaults
        assert "ACT-HALLUCINATED-999" not in res["answer"]
        assert "advisory actions from official guidance" in res["answer"]
        assert len(res["sources"]) > 0


@pytest.mark.asyncio
async def test_citation_ids_and_urls_come_only_from_stored_metadata():
    """Citations are derived solely from verified stored sources."""
    records = solution_hub.load_records()
    valid_urls = {s["url"] for s in records["sources"] if s.get("url")}
    valid_source_ids = {s["source_id"] for s in records["sources"]}

    with patch("app.solution_hub.select_action_ids_via_groq", AsyncMock(return_value=["ACT-BLAST-WATER-04"])):
        res = await solution_hub.generate_solution_hub_answer(
            "How to manage paddy blast?",
            language="en",
            crop="paddy",
            allow_inspection=True,
        )
        for src in res["sources"]:
            assert src["source_id"] in valid_source_ids
            assert src["url"] in valid_urls


@pytest.mark.asyncio
async def test_internal_chemical_fields_never_enter_model_context_or_output():
    """Groq selector prompt and final answer never contain chemical tables or dosages."""
    captured_payloads = []

    async def mock_post(url, headers=None, json=None):
        captured_payloads.append(json)
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"selected_action_ids": ["ACT-BLAST-WATER-04"]}'}}]
        }
        mock_resp.raise_for_status = lambda: None
        return mock_resp

    with patch("app.solution_hub.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        with patch.dict("os.environ", {"GROQ_API_KEY": "fake_key"}):
            res = await solution_hub.generate_solution_hub_answer(
                "Paddy blast leaves",
                language="en",
                crop="paddy",
                allow_inspection=True,
            )

    # Check model input
    assert len(captured_payloads) == 1
    prompt_str = json.dumps(captured_payloads[0])
    banned_chemicals = ["tricyclazole", "hexaconazole", "carbendazim", "azoxystrobin", "kg/ha", "ml/l", "g/l"]
    for chem in banned_chemicals:
        assert chem not in prompt_str.lower(), f"Chemical '{chem}' found in Groq selector prompt!"
        assert chem not in res["answer"].lower(), f"Chemical '{chem}' found in answer output!"


@pytest.mark.asyncio
async def test_no_evidence_cases_do_not_fall_back_to_unsourced_recommendations():
    """Queries with unspecified crop or generic questions return clarification questions, never unsourced advice."""
    res = await solution_hub.generate_solution_hub_answer(
        "My crops have some pest attack. What medicine to spray?",
        language="en",
        crop=None,
        allow_inspection=True,
    )
    assert res["sources"] == []
    assert "Which crop is affected" in res["answer"]
    assert "1800-180-1551" in res["answer"]
    assert "medicine" not in res["answer"].lower()
