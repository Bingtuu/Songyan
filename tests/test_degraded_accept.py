"""Tests for Task TS-02: degraded_accept acceptance path.

Covers:
- _score_card_is_degraded_acceptable threshold logic
- QualityGate routing to degraded_accept
- SettlementExtractor allowing settlement for degraded_accept chapters
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.workflows._nodes import (
    _score_card_is_degraded_acceptable,
    quality_gate_node,
    settlement_extractor_node,
)

# ---------------------------------------------------------------------------
# _score_card_is_degraded_acceptable
# ---------------------------------------------------------------------------


def _make_score_card(
    *,
    overall_score: float = 0.75,
    length_ok: bool = True,
    budget_ok: bool = True,
    coherence_critical: bool = False,
    coherence_major: bool = False,
    momentum_present: bool = False,
    readability_ok: bool = False,
) -> dict:
    return {
        "version_id": "v-current",
        "overall_score": overall_score,
        "length": {"score": 0.8 if length_ok else 0.5},
        "budget": {"score": 0.8 if budget_ok else 0.5},
        "coherence": {"score": 0.6},
        "momentum": {"score": 0.6 if momentum_present else 0.5},
        "readability": {"score": 0.6 if readability_ok else 0.5},
        "flags": {
            "length_ok": length_ok,
            "budget_ok": budget_ok,
            "coherence_critical": coherence_critical,
            "coherence_major": coherence_major,
            "momentum_present": momentum_present,
            "readability_ok": readability_ok,
        },
    }


def test_degraded_acceptable_true_when_below_normal_but_above_floor() -> None:
    """a. Dimensions below normal threshold but above degraded floor → True."""
    # coherence_major / momentum_present=False / readability_ok=False
    # cause _score_card_passes_quality_gate to fail,
    # but overall_score >= 0.70 and hard constraints met → degraded accept
    card = _make_score_card(
        overall_score=0.72,
        coherence_major=True,
        momentum_present=False,
        readability_ok=False,
    )
    assert _score_card_is_degraded_acceptable(card) is True


def test_degraded_acceptable_true_boundary_score() -> None:
    """overall_score exactly 0.70 is acceptable."""
    card = _make_score_card(overall_score=0.70, coherence_major=True)
    assert _score_card_is_degraded_acceptable(card) is True


def test_degraded_acceptable_false_when_score_too_low() -> None:
    """b. overall_score < 0.70 → False even if hard constraints are fine."""
    card = _make_score_card(overall_score=0.69, coherence_major=True)
    assert _score_card_is_degraded_acceptable(card) is False


def test_degraded_acceptable_false_when_length_fails() -> None:
    """length_ok=False → False."""
    card = _make_score_card(length_ok=False)
    assert _score_card_is_degraded_acceptable(card) is False


def test_degraded_acceptable_false_when_budget_fails() -> None:
    """budget_ok=False → False."""
    card = _make_score_card(budget_ok=False)
    assert _score_card_is_degraded_acceptable(card) is False


def test_degraded_acceptable_false_when_coherence_critical() -> None:
    """coherence_critical=True → False."""
    card = _make_score_card(coherence_critical=True)
    assert _score_card_is_degraded_acceptable(card) is False


def test_degraded_acceptable_false_for_none() -> None:
    """None input → False."""
    assert _score_card_is_degraded_acceptable(None) is False


def test_degraded_acceptable_false_for_invalid_dict() -> None:
    """Invalid dict (missing required keys) → False."""
    assert _score_card_is_degraded_acceptable({"foo": "bar"}) is False


# ---------------------------------------------------------------------------
# QualityGate degraded_accept routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quality_gate_routes_degraded_accept() -> None:
    """c. When repair is exhausted and best score card is degraded-acceptable,
    QualityGate routes to degraded_accept state.
    """
    version = MagicMock()
    version.version_id = "v-current"
    version.word_count = 3000

    goal = MagicMock()
    goal.word_count_target = 3000

    # Current version score card causes failures (coherence_major)
    current_score_card = _make_score_card(
        overall_score=0.65,
        coherence_major=True,
        momentum_present=False,
    )

    # Best version score card is degraded-acceptable
    best_score_card = _make_score_card(
        overall_score=0.72,
        coherence_major=True,
        momentum_present=False,
    )

    best_version = MagicMock()
    best_version.version_id = "v-current"  # same as current for simplicity
    best_version.project_id = "p1"
    best_version.chapter_number = 1
    best_version.is_abandoned = False

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(2, False),  # exhausted, not rewritten
        ),
        patch(
            "songyan.workflows._nodes._load_active_best_version",
            new_callable=AsyncMock,
            return_value=best_version,
        ),
        patch("songyan.workflows._nodes.ChapterHeadRepository", autospec=True) as mock_head_cls,
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        mock_head = mock_head_cls.return_value
        mock_head.update = AsyncMock()

        result = await quality_gate_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-current",
            "_score_card": current_score_card,
            "_best_version_id": "v-current",
            "_best_score_card": best_score_card,
        })

    assert result.get("_degraded_accept") is True
    assert result.get("_quality_gate_passed") is False
    assert result.get("_convergence_failed") is True
    assert result.get("_skip_settlement") is False
    assert result.get("_settlement_needs_human_review") is False
    assert result.get("status") == "human_confirm"


@pytest.mark.asyncio
async def test_quality_gate_recovered_by_best_when_passes_qg() -> None:
    """If best passes quality gate, it should recover (not degraded_accept)."""
    version = MagicMock()
    version.version_id = "v-current"
    version.word_count = 3000

    goal = MagicMock()
    goal.word_count_target = 3000

    current_score_card = _make_score_card(
        overall_score=0.65, coherence_major=True, momentum_present=False
    )
    # Best passes everything
    best_score_card = _make_score_card(
        overall_score=0.85,
        coherence_major=False,
        momentum_present=True,
        readability_ok=True,
    )

    best_version = MagicMock()
    best_version.version_id = "v-current"
    best_version.project_id = "p1"
    best_version.chapter_number = 1
    best_version.is_abandoned = False

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(2, False),
        ),
        patch(
            "songyan.workflows._nodes._load_active_best_version",
            new_callable=AsyncMock,
            return_value=best_version,
        ),
        patch("songyan.workflows._nodes.ChapterHeadRepository", autospec=True) as mock_head_cls,
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        mock_head = mock_head_cls.return_value
        mock_head.update = AsyncMock()

        result = await quality_gate_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-current",
            "_score_card": current_score_card,
            "_best_version_id": "v-current",
            "_best_score_card": best_score_card,
        })

    assert result.get("_degraded_accept") is None
    assert result.get("_quality_gate_passed") is True
    assert result.get("_convergence_failed") is False
    assert result.get("status") == "human_confirm"


# ---------------------------------------------------------------------------
# SettlementExtractor degraded_accept allowance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settlement_extractor_allows_degraded_accept() -> None:
    """d. SettlementExtractor does not block when _degraded_accept is True."""
    version = MagicMock()
    version.version_id = "v-1"
    version.content = "test content"

    project = MagicMock()
    project.genre_id = "scifi"
    project.mode_id = "webnovel"

    goal = MagicMock()

    settlement_mock = MagicMock()
    settlement_mock.validation_status = "valid"

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_project", new_callable=AsyncMock) as mock_proj,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch("songyan.workflows._nodes.load_genre_profile", return_value=None),
        patch(
            "songyan.workflows._nodes.extract_settlement",
            new_callable=AsyncMock,
            return_value=settlement_mock,
        ),
        patch(
            "songyan.workflows._nodes.accept_with_settlement_boundary",
            new_callable=AsyncMock,
        ),
        patch(
            "songyan.workflows._nodes.write_chapter_summary",
            new_callable=AsyncMock,
            return_value=("sum-1", None),
        ),
        patch("songyan.workflows._nodes._run_lifecycle_cleanup", new_callable=AsyncMock),
        patch("songyan.workflows._nodes._index_accepted_chapter", new_callable=AsyncMock),
        patch("songyan.agents.setting_evaporator.SettingEvaporator") as mock_evap_cls,
        patch(
            "songyan.workflows._nodes.trigger_layered_summaries",
            new_callable=AsyncMock,
        ),
    ):
        mock_ver.return_value = version
        mock_proj.return_value = project
        mock_goal.return_value = goal
        mock_evap = mock_evap_cls.return_value
        mock_evap.run = AsyncMock(return_value=[])

        result = await settlement_extractor_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-1",
            "_quality_gate_passed": False,
            "_degraded_accept": True,
            "_skip_settlement": False,
        })

    # Should NOT be blocked; should proceed to settlement extraction
    assert result.get("status") != "settlement_review"
    assert result.get("_settlement_needs_human_review") is False


@pytest.mark.asyncio
async def test_settlement_extractor_blocks_qg_false_without_degraded_accept() -> None:
    """QG false without degraded_accept → blocked."""
    version = MagicMock()
    version.version_id = "v-1"
    version.content = "test content"

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
    ):
        mock_ver.return_value = version

        result = await settlement_extractor_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-1",
            "_quality_gate_passed": False,
            "_degraded_accept": False,
            "_skip_settlement": False,
        })

    assert result.get("status") == "settlement_review"
    assert result.get("_settlement_needs_human_review") is True
    assert result.get("settlement_id") is None
