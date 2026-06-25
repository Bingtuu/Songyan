"""Task 122b: Integration Test — Pipeline Scenarios.

Covers degraded_accept routing, safe-best rollback on rewrite,
human_review_required gate, and AutoHalt streak logic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.exceptions import AutoHaltException
from songyan.workflows._nodes import (
    _score_card_is_safe_best,
    quality_gate_node,
)
from songyan.workflows.phase1_graph import quality_gate_router
from songyan.workflows.phase2_graph import _check_auto_halt_window


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


# =============================================================================
# 1. Degraded Accept Router
# =============================================================================


class TestQualityGateDegradedAcceptRouter:
    """QG false + score >= 0.70 -> degraded_accept routing."""

    @pytest.mark.asyncio
    async def test_degraded_accept_routes_to_human_confirm(self) -> None:
        """quality_gate_node with degraded-acceptable best -> _degraded_accept=True."""
        version = MagicMock()
        version.version_id = "v-current"
        version.word_count = 3000

        goal = MagicMock()
        goal.word_count_target = 3000

        current_score_card = _make_score_card(
            overall_score=0.65,
            coherence_major=True,
            momentum_present=False,
        )
        best_score_card = _make_score_card(
            overall_score=0.72,
            coherence_major=True,
            momentum_present=False,
        )

        best_version = MagicMock()
        best_version.version_id = "v-current"
        best_version.project_id = "p1"
        best_version.chapter_number = 1
        best_version.is_abandoned = False

        with (
            patch(
                "songyan.workflows._nodes.load_version", new_callable=AsyncMock
            ) as mock_ver,
            patch(
                "songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock
            ) as mock_goal,
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
            patch(
                "songyan.workflows._nodes.ChapterHeadRepository", autospec=True
            ) as mock_head_cls,
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

    def test_quality_gate_router_passes_degraded_accept(self) -> None:
        """quality_gate_router sees human_confirm status -> 'pass'."""
        state = {
            "project_id": "p1",
            "chapter_number": 1,
            "status": "human_confirm",
            "_degraded_accept": True,
            "_quality_gate_passed": False,
            "error": None,
        }
        assert quality_gate_router(state) == "pass"


# =============================================================================
# 2. Safe Best Preserve on Rewrite
# =============================================================================


class TestSafeBestPreserveOnRewrite:
    """Rewrite result score < best - 0.08 -> rollback to safe best."""

    def test_safe_best_true_for_high_score(self) -> None:
        """Best score 0.85 at Ch30 (>0.78 threshold) -> safe best."""
        card = _make_score_card(
            overall_score=0.85,
            coherence_major=False,
            momentum_present=True,
            readability_ok=True,
        )
        assert _score_card_is_safe_best(card, chapter_number=30) is True

    def test_safe_best_false_below_threshold(self) -> None:
        """Best score 0.76 at Ch30 (threshold 0.78) -> not safe."""
        card = _make_score_card(
            overall_score=0.76,
            coherence_major=False,
            momentum_present=True,
            readability_ok=True,
        )
        assert _score_card_is_safe_best(card, chapter_number=30) is False

    def test_safe_best_false_due_to_coherence_critical(self) -> None:
        """Score high but coherence_critical -> not safe."""
        card = _make_score_card(
            overall_score=0.90,
            coherence_critical=True,
            momentum_present=True,
            readability_ok=True,
        )
        assert _score_card_is_safe_best(card, chapter_number=30) is False


# =============================================================================
# 3. Human Review Required Gate
# =============================================================================


class TestHumanReviewRequiredGate:
    """QG false + score < 0.70 + no best -> human_review_required."""

    @pytest.mark.asyncio
    async def test_no_best_score_card_needs_human_review(self) -> None:
        """Repair exhausted but no active best -> _settlement_needs_human_review=True."""
        version = MagicMock()
        version.version_id = "v-current"
        version.word_count = 3000

        goal = MagicMock()
        goal.word_count_target = 3000

        current_score_card = _make_score_card(
            overall_score=0.65,
            coherence_major=True,
            momentum_present=False,
        )

        with (
            patch(
                "songyan.workflows._nodes.load_version", new_callable=AsyncMock
            ) as mock_ver,
            patch(
                "songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock
            ) as mock_goal,
            patch(
                "songyan.workflows._nodes._load_chapter_repair_state",
                new_callable=AsyncMock,
                return_value=(2, False),
            ),
            patch(
                "songyan.workflows._nodes._load_active_best_version",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            mock_ver.return_value = version
            mock_goal.return_value = goal

            result = await quality_gate_node({
                "project_id": "p1",
                "chapter_number": 1,
                "current_version_id": "v-current",
                "_score_card": current_score_card,
                "_best_version_id": None,
                "_best_score_card": None,
            })

        assert result.get("status") == "human_confirm"
        assert result.get("_quality_gate_passed") is False
        assert result.get("_convergence_failed") is True
        assert result.get("_skip_settlement") is True
        assert result.get("_settlement_needs_human_review") is True
        assert result.get("_degraded_accept") is None

    @pytest.mark.asyncio
    async def test_best_below_degraded_floor_needs_human_review(self) -> None:
        """Active best exists but score 0.69 (<0.70) -> not degraded_acceptable."""
        version = MagicMock()
        version.version_id = "v-current"
        version.word_count = 3000

        goal = MagicMock()
        goal.word_count_target = 3000

        current_score_card = _make_score_card(
            overall_score=0.65,
            coherence_major=True,
            momentum_present=False,
        )
        best_score_card = _make_score_card(
            overall_score=0.69,
            coherence_major=True,
            momentum_present=False,
        )

        best_version = MagicMock()
        best_version.version_id = "v-best"
        best_version.project_id = "p1"
        best_version.chapter_number = 1
        best_version.is_abandoned = False

        with (
            patch(
                "songyan.workflows._nodes.load_version", new_callable=AsyncMock
            ) as mock_ver,
            patch(
                "songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock
            ) as mock_goal,
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
            patch(
                "songyan.workflows._nodes.ChapterHeadRepository", autospec=True
            ) as mock_head_cls,
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
                "_best_version_id": "v-best",
                "_best_score_card": best_score_card,
            })

        assert result.get("status") == "human_confirm"
        assert result.get("_quality_gate_passed") is False
        assert result.get("_convergence_failed") is True
        assert result.get("_skip_settlement") is True
        assert result.get("_settlement_needs_human_review") is True
        assert result.get("_degraded_accept") is None


# =============================================================================
# 4. AutoHalt Streak Logic
# =============================================================================


def _make_run_state() -> MagicMock:
    return MagicMock()


class TestAutoHaltWindow:
    """_check_auto_halt_window streak detection."""

    @pytest.mark.asyncio
    async def test_context_emergency_degraded_streak_triggers_autohalt(self) -> None:
        """连续 3 章 emergency + 至少 1 章降级 -> AutoHaltException.

        注意：QG fail streak 检查在 emergency streak 之前，因此测试数据必须
        避免触发 QG fail streak（即 QG fail 数量 < 3）。
        """
        recent_results = [
            {
                "chapter_number": 18,
                "context_emergency": True,
                "quality_gate_passed": True,
                "success": True,
                "settlement_success": True,
                "summary_success": True,
            },
            {
                "chapter_number": 19,
                "context_emergency": True,
                "quality_gate_passed": True,
                "success": True,
                "settlement_success": True,
                "summary_success": True,
            },
            {
                "chapter_number": 20,
                "context_emergency": True,
                "quality_gate_passed": False,
                "success": False,
                "settlement_success": False,
                "summary_success": True,
            },
        ]
        run_state = _make_run_state()
        completed: list[int] = []
        failed: list[int] = []
        persisted_summary = ""

        with (
            pytest.raises(AutoHaltException) as exc_info,
            patch(
                "songyan.workflows.phase2_graph._pause_run_for_auto_halt",
                new_callable=AsyncMock,
            ),
        ):
            await _check_auto_halt_window(
                run_state,
                recent_results,
                completed,
                failed,
                persisted_summary,
                run_id="run-001",
                chapter_number=20,
            )

        assert exc_info.value.reason == "context_emergency_degraded_streak"
        assert "连续 3 章触发 ContextEmergency" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_context_emergency_single_fail_does_not_trigger_autohalt(self) -> None:
        """连续 3 章 emergency 但 QG 均通过 -> 不触发 AutoHalt，只记录 warning."""
        recent_results = [
            {
                "chapter_number": 18,
                "context_emergency": True,
                "quality_gate_passed": True,
                "success": True,
                "settlement_success": True,
                "summary_success": True,
            },
            {
                "chapter_number": 19,
                "context_emergency": True,
                "quality_gate_passed": True,
                "success": True,
                "settlement_success": True,
                "summary_success": True,
            },
            {
                "chapter_number": 20,
                "context_emergency": True,
                "quality_gate_passed": True,
                "success": True,
                "settlement_success": True,
                "summary_success": True,
            },
        ]
        run_state = _make_run_state()
        completed: list[int] = []
        failed: list[int] = []
        persisted_summary = ""

        # Should NOT raise
        await _check_auto_halt_window(
            run_state,
            recent_results,
            completed,
            failed,
            persisted_summary,
            run_id="run-002",
            chapter_number=20,
        )

        # Verify no exception was raised by reaching this point
        assert True

    @pytest.mark.asyncio
    async def test_quality_gate_fail_streak_triggers_autohalt(self) -> None:
        """连续 3 章 QG 未通过（无 emergency）-> AutoHaltException."""
        recent_results = [
            {
                "chapter_number": 10,
                "context_emergency": False,
                "quality_gate_passed": False,
                "success": False,
            },
            {
                "chapter_number": 11,
                "context_emergency": False,
                "quality_gate_passed": False,
                "success": False,
            },
            {
                "chapter_number": 12,
                "context_emergency": False,
                "quality_gate_passed": False,
                "success": False,
            },
        ]
        run_state = _make_run_state()
        completed: list[int] = []
        failed: list[int] = []
        persisted_summary = ""

        with (
            pytest.raises(AutoHaltException) as exc_info,
            patch(
                "songyan.workflows.phase2_graph._pause_run_for_auto_halt",
                new_callable=AsyncMock,
            ),
        ):
            await _check_auto_halt_window(
                run_state,
                recent_results,
                completed,
                failed,
                persisted_summary,
                run_id="run-003",
                chapter_number=12,
            )

        assert exc_info.value.reason == "quality_gate_fail_streak"
        assert "连续 3 章质量门未通过" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mixed_streak_no_autohalt(self) -> None:
        """2 章 emergency + 1 章正常 -> 不触发 AutoHalt."""
        recent_results = [
            {
                "chapter_number": 18,
                "context_emergency": True,
                "quality_gate_passed": True,
                "success": True,
            },
            {
                "chapter_number": 19,
                "context_emergency": False,
                "quality_gate_passed": True,
                "success": True,
            },
            {
                "chapter_number": 20,
                "context_emergency": True,
                "quality_gate_passed": False,
                "success": False,
            },
        ]
        run_state = _make_run_state()
        completed: list[int] = []
        failed: list[int] = []
        persisted_summary = ""

        await _check_auto_halt_window(
            run_state,
            recent_results,
            completed,
            failed,
            persisted_summary,
            run_id="run-004",
            chapter_number=20,
        )
        assert True

    @pytest.mark.asyncio
    async def test_insufficient_window_no_autohalt(self) -> None:
        """recent_results < 3 -> 不触发 AutoHalt."""
        recent_results = [
            {
                "chapter_number": 19,
                "context_emergency": True,
                "quality_gate_passed": False,
                "success": False,
            },
            {
                "chapter_number": 20,
                "context_emergency": True,
                "quality_gate_passed": False,
                "success": False,
            },
        ]
        run_state = _make_run_state()
        completed: list[int] = []
        failed: list[int] = []
        persisted_summary = ""

        await _check_auto_halt_window(
            run_state,
            recent_results,
            completed,
            failed,
            persisted_summary,
            run_id="run-005",
            chapter_number=20,
        )
        assert True
