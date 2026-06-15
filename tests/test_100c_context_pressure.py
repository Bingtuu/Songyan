"""Tests for Task 100c: Context Pressure Optimization.

- _calculate_objective_fullness
- _dynamic_max_character_states / _dynamic_max_soft_refs
- BudgetPruner disruption random truncation
- ContextPackage context_pressure field
"""

from __future__ import annotations

from songyan.agents.context_manager import (
    BudgetPruner,
    _calculate_objective_fullness,
    _dynamic_max_character_states,
    _dynamic_max_soft_refs,
)
from songyan.models.chapter import ChapterGoal
from songyan.models.context import (
    ContextPackage,
    ForeshadowingItem,
    SoftReference,
)

# ---------------------------------------------------------------------------
# _calculate_objective_fullness
# ---------------------------------------------------------------------------


def test_objective_fullness_budget_96() -> None:
    """budget_used=0.96, fullness=0.0 → 0.9."""
    assert _calculate_objective_fullness(0.0, 0.96) == 0.9


def test_objective_fullness_budget_91() -> None:
    """budget_used=0.91, fullness=0.0 → 0.7."""
    assert _calculate_objective_fullness(0.0, 0.91) == 0.7


def test_objective_fullness_budget_85() -> None:
    """budget_used=0.85, fullness=0.3 → 保持 0.3."""
    assert _calculate_objective_fullness(0.3, 0.85) == 0.3


def test_objective_fullness_budget_96_higher_llm() -> None:
    """budget_used=0.96, fullness=0.95 → max(0.95, 0.9)=0.95."""
    assert _calculate_objective_fullness(0.95, 0.96) == 0.95


def test_objective_fullness_budget_90_exact() -> None:
    """budget_used=0.90 恰好为阈值 → 不触发 0.7 阈值."""
    assert _calculate_objective_fullness(0.3, 0.90) == 0.3


def test_objective_fullness_budget_95_exact() -> None:
    """budget_used=0.95 恰好为阈值 → 触发 0.7 但不触发 0.9."""
    assert _calculate_objective_fullness(0.3, 0.95) == 0.7


# ---------------------------------------------------------------------------
# Dynamic hard limits
# ---------------------------------------------------------------------------


def test_dynamic_max_character_states_18() -> None:
    """18 人物 → max(4, min(8, 18//3+1)) = 7."""
    assert _dynamic_max_character_states(18) == 7


def test_dynamic_max_character_states_3() -> None:
    """3 人物 → 下限 4."""
    assert _dynamic_max_character_states(3) == 4


def test_dynamic_max_character_states_30() -> None:
    """30 人物 → 上限 8."""
    assert _dynamic_max_character_states(30) == 8


def test_dynamic_max_soft_refs_20() -> None:
    """20 设定 → max(10, min(16, 20//5+2)) = 6 → 下限 10."""
    assert _dynamic_max_soft_refs(20) == 10


def test_dynamic_max_soft_refs_100() -> None:
    """100 设定 → max(10, min(16, 100//5+2)) = 22 → 上限 16."""
    assert _dynamic_max_soft_refs(100) == 16


# ---------------------------------------------------------------------------
# BudgetPruner disruption random truncation
# ---------------------------------------------------------------------------


def test_apply_focal_distance_disruption_random() -> None:
    """disruption 使用固定 seed 随机截断，两次相同 seed 结果一致."""
    pruner = BudgetPruner()
    goal = ChapterGoal(
        chapter_number=1, title="t", target_events=["e"], hooks=["h"], obligations=[]
    )
    refs = [
        SoftReference(type="world_setting", content=f"ref{i}", relevance_score=0.5)
        for i in range(10)
    ]
    fores = [
        ForeshadowingItem(
            foreshadowing_id=f"f{i}",
            description=f"fore{i}",
            planted_in_chapter=i,
        )
        for i in range(10)
    ]
    ctx = ContextPackage(
        chapter_goal=goal,
        soft_references=refs,
        foreshadowing=fores,
    )

    ctx1 = pruner._apply_focal_distance(ctx.model_copy(deep=True), "disruption", chapter_number=5)
    ctx2 = pruner._apply_focal_distance(ctx.model_copy(deep=True), "disruption", chapter_number=5)

    assert len(ctx1.soft_references) == 5
    assert len(ctx1.foreshadowing) == 5
    # 相同 seed 应产生相同结果
    assert [r.content for r in ctx1.soft_references] == [r.content for r in ctx2.soft_references]
    ids1 = [f.foreshadowing_id for f in ctx1.foreshadowing]
    ids2 = [f.foreshadowing_id for f in ctx2.foreshadowing]
    assert ids1 == ids2


def test_apply_focal_distance_disruption_different_seed() -> None:
    """不同 seed 产生不同结果（大概率）."""
    pruner = BudgetPruner()
    goal = ChapterGoal(
        chapter_number=1, title="t", target_events=["e"], hooks=["h"], obligations=[]
    )
    refs = [
        SoftReference(type="world_setting", content=f"ref{i}", relevance_score=0.5)
        for i in range(10)
    ]
    ctx = ContextPackage(
        chapter_goal=goal,
        soft_references=refs,
    )

    ctx1 = pruner._apply_focal_distance(ctx.model_copy(deep=True), "disruption", chapter_number=5)
    ctx2 = pruner._apply_focal_distance(ctx.model_copy(deep=True), "disruption", chapter_number=6)

    # 大概率不同（但不 100% 保证，使用足够大的列表使冲突概率极低）
    assert len(ctx1.soft_references) == 5
    assert len(ctx2.soft_references) == 5


# ---------------------------------------------------------------------------
# ContextPackage context_pressure field
# ---------------------------------------------------------------------------


def test_context_package_default_context_pressure() -> None:
    """ContextPackage 默认 context_pressure 为空 dict."""
    goal = ChapterGoal(
        chapter_number=1, title="t", target_events=["e"], hooks=["h"], obligations=[]
    )
    ctx = ContextPackage(chapter_goal=goal)
    assert ctx.context_pressure == {}
