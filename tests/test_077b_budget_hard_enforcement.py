"""Task 077b: BudgetPruner 硬断言 — 单元测试."""

from __future__ import annotations

from songyan.agents.context_manager import HARD_ENFORCE_THRESHOLD, BudgetPruner
from songyan.models import (
    ArcSummary,
    ChapterGoal,
    CharacterStateSnapshot,
    ContextPackage,
    ForeshadowingItem,
    HardConstraint,
    OpenThread,
    RecentPlot,
    SoftReference,
    VolumeSummary,
)
from songyan.models.character import DialogueStyleCard

# =============================================================================
# Helper: build test ContextPackage with configurable partitions
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
                type="world_setting", content=f"设定{i}: 第{i}个",
                relevance_score=0.7, last_mentioned_chapter=i,
            )
            for i in range(n_soft_refs)
        ]
    if n_open_threads > 0:
        ctx.open_threads = [
            OpenThread(
                thread_id=f"t-{i}", description=f"线程{i}",
                source_type="setting", source_chapter=i,
                priority=0.5 + (i * 0.1),
            )
            for i in range(n_open_threads)
        ]
    if n_foreshadowing > 0:
        ctx.foreshadowing = [
            ForeshadowingItem(
                foreshadowing_id=f"f-{i}", description=f"伏笔{i}",
                planted_in_chapter=i, status="planted",
            )
            for i in range(n_foreshadowing)
        ]
    if n_character_states > 0:
        ctx.character_states = [
            CharacterStateSnapshot(
                character_id=f"c-{i}", name=f"角色{i}",
                importance_score=max(0.1, 1.0 - (i * 0.2)),
            )
            for i in range(n_character_states)
        ]
    if n_dialogue_cards > 0:
        from songyan.models.character import DialogueStyleCard
        ctx.dialogue_style_cards = [
            DialogueStyleCard(character_id=f"dc-{i}", project_id="test")
            for i in range(n_dialogue_cards)
        ]
    if n_summaries > 0:
        from songyan.models.context import ChapterSummary
        ctx.recent_plot = RecentPlot(summaries=[
            ChapterSummary(
                chapter_number=i, summary="摘要" * 30,
                key_events=[f"事件{i}"],
            )
            for i in range(n_summaries)
        ])
    if with_arc_volume:
        ctx.arc_context = ArcSummary(
            arc_id="a1", project_id="test", start_chapter=1, end_chapter=50,
            arc_summary="A" * 500, key_events=["A", "B", "C", "D", "E"],
        )
        ctx.volume_context = VolumeSummary(
            volume_id="v1", project_id="test", start_chapter=1, end_chapter=50,
            volume_summary="V" * 500, major_revelations=["R1", "R2", "R3", "R4"],
        )
    return ctx


# =============================================================================
# Trigger condition
# =============================================================================

class TestTriggerCondition:
    def test_triggers_when_over_threshold(self) -> None:
        # Task 110c: 分区预算制先压缩，需更大数据量才能触发硬断言
        ctx = _make_ctx(
            n_soft_refs=50,
            n_open_threads=20,
            n_foreshadowing=20,
            n_character_states=10,
            n_dialogue_cards=10,
            n_summaries=20,
            with_arc_volume=True,
        )
        pruner = BudgetPruner()
        result = pruner.prune(ctx, budget_tokens=100)
        assert result._budget_enforced is True

    def test_no_trigger_when_under_threshold(self) -> None:
        ctx = _make_ctx(n_soft_refs=0)
        pruner = BudgetPruner()
        result = pruner.prune(ctx, budget_tokens=100000)
        assert result._budget_enforced is False

    def test_constant_value(self) -> None:
        assert HARD_ENFORCE_THRESHOLD == 1.3


# =============================================================================
# Dropping order
# =============================================================================

class TestDroppingOrder:
    def test_drops_dialogue_cards_first(self) -> None:
        ctx = _make_ctx(n_dialogue_cards=5, n_soft_refs=15)
        result = BudgetPruner().prune(ctx, budget_tokens=500)
        if result._budget_enforced:
            assert len(result.dialogue_style_cards) == 0

    def test_open_threads_pruned(self) -> None:
        ctx = _make_ctx(n_open_threads=10, n_soft_refs=10)
        result = BudgetPruner().prune(ctx, budget_tokens=500)
        if result._budget_enforced:
            assert len(result.open_threads) <= 2
            for t in result.open_threads:
                assert t.priority > 0.8

    def test_soft_refs_cut_to_top4(self) -> None:
        ctx = _make_ctx(n_soft_refs=20)
        result = BudgetPruner().prune(ctx, budget_tokens=500)
        if result._budget_enforced:
            assert len(result.soft_references) <= 4

    def test_foreshadowing_cut_to_due_overdue(self) -> None:
        # 混合伏笔状态：8 planted + 4 due + 4 overdue，用低预算确保 step 4 触发
        ctx = _make_ctx(n_soft_refs=30)
        for i in range(16):
            status = "planted" if i < 8 else ("due" if i < 12 else "overdue")
            ctx.foreshadowing.append(
                ForeshadowingItem(
                    foreshadowing_id=f"f-{i}", description=f"伏笔{i}",
                    planted_in_chapter=i, status=status,
                )
            )
        result = BudgetPruner().prune(ctx, budget_tokens=300)
        if result._budget_enforced:
            for f in result.foreshadowing:
                assert f.status in ("due", "overdue")

    def test_character_states_cut_by_importance(self) -> None:
        # 手动添加 importance 梯度 1.0 → 0.1，用低预算确保 step 5 触发
        ctx = _make_ctx(n_soft_refs=30, n_foreshadowing=10)
        for i in range(10):
            ctx.character_states.append(
                CharacterStateSnapshot(
                    character_id=f"c-{i}", name=f"角色{i}",
                    importance_score=max(0.1, 1.0 - (i * 0.1)),
                )
            )
        result = BudgetPruner().prune(ctx, budget_tokens=300)
        if result._budget_enforced:
            assert all(s.importance_score >= 0.9 for s in result.character_states)


    def test_nuclear_fallback_executes(self) -> None:
        ctx = _make_ctx(
            n_dialogue_cards=3, n_open_threads=8, n_soft_refs=30,
            n_foreshadowing=15, n_character_states=12, n_summaries=10,
            with_arc_volume=True,
        )
        result = BudgetPruner().prune(ctx, budget_tokens=50)
        assert result._budget_enforced is True


# =============================================================================
# Never-drop partitions
# =============================================================================

class TestProtectedPartitions:
    def test_hard_constraints_preserved(self) -> None:
        ctx = _make_ctx(n_soft_refs=30, n_foreshadowing=15, n_character_states=12)
        ctx.dialogue_style_cards = [
            DialogueStyleCard(character_id=f"dc-{i}", project_id="test")
            for i in range(10)
        ]
        before = len(ctx.hard_constraints)
        result = BudgetPruner().prune(ctx, budget_tokens=50)
        assert len(result.hard_constraints) == before


# =============================================================================
# Budget_enforced flag
# =============================================================================

class TestBudgetEnforcedFlag:
    def test_flag_true_after_enforcement(self) -> None:
        ctx = _make_ctx(n_soft_refs=30)
        result = BudgetPruner().prune(ctx, budget_tokens=100)
        assert result._budget_enforced is True

    def test_flag_false_no_enforcement(self) -> None:
        ctx = _make_ctx(n_soft_refs=0)
        result = BudgetPruner().prune(ctx, budget_tokens=100000)
        assert result._budget_enforced is False

    def test_flag_is_bool(self) -> None:
        ctx = _make_ctx(n_soft_refs=20)
        result = BudgetPruner().prune(ctx, budget_tokens=500)
        assert isinstance(result._budget_enforced, bool)


# =============================================================================
# Edge cases
# =============================================================================

class TestEdgeCases:
    def test_empty_context_package(self) -> None:
        ctx = ContextPackage(chapter_goal=_make_goal())
        result = BudgetPruner().prune(ctx, budget_tokens=1000)
        assert result._budget_enforced is False

    def test_zero_budget_safety(self) -> None:
        ctx = _make_ctx(n_soft_refs=5)
        result = BudgetPruner().prune(ctx, budget_tokens=0)
        assert result is not None
        assert isinstance(result._budget_enforced, bool)

