"""Task 104: BudgetHardCeiling — 预算硬天花板单元测试."""

from __future__ import annotations

import pytest

from songyan.agents.context_manager import BudgetPruner
from songyan.models import (
    ArcSummary,
    ChapterGoal,
    ChapterSummary,
    CharacterStateSnapshot,
    ContextPackage,
    DialogueStyleCard,
    ForeshadowingItem,
    HardConstraint,
    OpenThread,
    RecentPlot,
    SoftReference,
    VolumeSummary,
)

# =============================================================================
# Helpers
# =============================================================================

def _make_goal(chapter_number: int = 50) -> ChapterGoal:
    return ChapterGoal(
        chapter_number=chapter_number,
        target_events=[],
        hooks=[],
        obligations=[],
        word_count_target=3200,
    )


def _make_ctx(
    n_soft_refs: int = 0,
    n_open_threads: int = 0,
    n_foreshadowing: int = 0,
    n_character_states: int = 0,
    n_dialogue_cards: int = 0,
    n_summaries: int = 0,
    with_arc_volume: bool = False,
) -> ContextPackage:
    goal = _make_goal()
    ctx = ContextPackage(
        chapter_goal=goal,
        hard_constraints=[
            HardConstraint(type="obligation", description="核心义务", source="test"),
        ],
    )
    if n_soft_refs > 0:
        ctx.soft_references = [
            SoftReference(
                type="world_setting",
                content=f"设定{i}: 第{i}个",
                relevance_score=0.7,
                last_mentioned_chapter=i,
            )
            for i in range(n_soft_refs)
        ]
    if n_open_threads > 0:
        ctx.open_threads = [
            OpenThread(
                thread_id=f"t-{i}",
                description=f"线程{i}",
                source_type="setting",
                source_chapter=i,
                priority=0.5 + (i * 0.1),
            )
            for i in range(n_open_threads)
        ]
    if n_foreshadowing > 0:
        ctx.foreshadowing = [
            ForeshadowingItem(
                foreshadowing_id=f"f-{i}",
                description=f"伏笔{i}",
                planted_in_chapter=i,
                status="planted",
            )
            for i in range(n_foreshadowing)
        ]
    if n_character_states > 0:
        ctx.character_states = [
            CharacterStateSnapshot(
                character_id=f"c-{i}",
                name=f"角色{i}",
                importance_score=max(0.1, 1.0 - (i * 0.2)),
            )
            for i in range(n_character_states)
        ]
    if n_dialogue_cards > 0:
        ctx.dialogue_style_cards = [
            DialogueStyleCard(character_id=f"dc-{i}", project_id="test")
            for i in range(n_dialogue_cards)
        ]
    if n_summaries > 0:
        ctx.recent_plot = RecentPlot(
            summaries=[
                ChapterSummary(
                    chapter_number=i,
                    summary="摘要" * 30,
                    key_events=[f"事件{i}"],
                )
                for i in range(n_summaries)
            ]
        )
    if with_arc_volume:
        ctx.arc_context = ArcSummary(
            arc_id="a1",
            project_id="test",
            start_chapter=1,
            end_chapter=50,
            arc_summary="A" * 500,
            key_events=["A", "B", "C", "D", "E"],
        )
        ctx.volume_context = VolumeSummary(
            volume_id="v1",
            project_id="test",
            start_chapter=1,
            end_chapter=50,
            volume_summary="V" * 500,
            major_revelations=["R1", "R2", "R3", "R4"],
        )
    return ctx


# =============================================================================
# Fullness Factor
# =============================================================================

class TestDynamicFullnessFactor:
    def test_zero_fullness(self) -> None:
        assert BudgetPruner._dynamic_fullness_factor(0.0) == 1.0

    def test_half_fullness(self) -> None:
        """Task 104: 0.5 * 0.7 = 0.35 → 0.65."""
        assert BudgetPruner._dynamic_fullness_factor(0.5) == pytest.approx(0.65)

    def test_full_fullness(self) -> None:
        """Task 104: 1.0 * 0.7 = 0.7 → 0.3."""
        assert BudgetPruner._dynamic_fullness_factor(1.0) == pytest.approx(0.30)

    def test_formula_uses_0_7_not_0_5(self) -> None:
        """明确验证系数是 0.7 而非旧的 0.5."""
        result = BudgetPruner._dynamic_fullness_factor(0.5)
        assert result == pytest.approx(0.65)
        assert result != pytest.approx(0.75)


# =============================================================================
# ContextEmergency Trigger
# =============================================================================

class TestContextEmergency:
    def _make_overflow_context(self) -> ContextPackage:
        """构造一个远超预算的上下文包."""
        return _make_ctx(
            n_soft_refs=20,
            n_open_threads=10,
            n_foreshadowing=15,
            n_character_states=8,
            n_dialogue_cards=5,
            n_summaries=10,
            with_arc_volume=True,
        )

    def test_emergency_triggered_when_budget_used_exceeds_1_0(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        budget = 500  # 极小的预算，强制超预算
        result = pruner.prune(ctx, budget)
        assert result.context_emergency is True
        assert result.budget_used <= 1.0

    def test_emergency_reduces_tokens_below_budget(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        budget = 500
        before = pruner._estimate_package(ctx)
        result = pruner.prune(ctx, budget)
        assert before > budget
        assert result.estimated_tokens <= budget
        assert result.budget_used <= 1.0

    def test_emergency_clears_soft_partitions(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        result = pruner.prune(ctx, 500)
        assert result.context_emergency is True
        assert result.soft_references == []
        assert result.foreshadowing == []
        assert result.open_threads == []
        assert result.permanent_scenes == []
        assert result.dialogue_style_cards == []
        assert result.human_marks == []
        assert result.arc_context is None
        assert result.volume_context is None

    def test_emergency_preserves_hard_partitions(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        result = pruner.prune(ctx, 500)
        assert result.context_emergency is True
        assert result.chapter_goal is not None
        assert result.hard_constraints
        assert result.genre_rules is not None or ctx.genre_rules is None
        assert result.mode_rules is not None or ctx.mode_rules is None

    def test_emergency_keeps_top_character_only(self) -> None:
        pruner = BudgetPruner()
        ctx = _make_ctx(n_character_states=5)
        result = pruner.prune(ctx, 500)
        if result.context_emergency:
            assert len(result.character_states) == 1
            top = max(ctx.character_states, key=lambda s: s.importance_score)
            assert result.character_states[0].character_id == top.character_id

    def test_emergency_keeps_only_last_summary(self) -> None:
        pruner = BudgetPruner()
        ctx = _make_ctx(n_summaries=5)
        result = pruner.prune(ctx, 500)
        if result.context_emergency:
            assert result.recent_plot is not None
            assert len(result.recent_plot.summaries) == 1
            assert result.recent_plot.summaries[0].chapter_number == 4

    def test_no_emergency_when_under_budget(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(chapter_goal=_make_goal())
        result = pruner.prune(ctx, 10000)
        assert result.context_emergency is False
        assert result.budget_used < 1.0

    def test_emergency_does_not_mutate_original(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        original_soft = len(ctx.soft_references)
        original_char = len(ctx.character_states)
        result = pruner.prune(ctx, 500)
        assert result.context_emergency is True
        assert len(ctx.soft_references) == original_soft
        assert len(ctx.character_states) == original_char
        assert ctx.context_emergency is False
