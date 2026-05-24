"""ContextManager Agent — 上下文包组装与 Token 预算裁剪."""

from __future__ import annotations

import json
from typing import Any

import structlog
from pydantic import BaseModel

from songyan.models import (
    ChapterGoal,
    ChapterSummary,
    Character,
    CharacterState,
    CharacterStateSnapshot,
    ContextPackage,
    CreativeBrief,
    CreativeModeProfile,
    ForeshadowingItem,
    GenreProfile,
    GenreRules,
    HardConstraint,
    ModeRules,
    NewSetting,
    ProjectSetting,
    RecentPlot,
    SoftReference,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_BUDGET_TOKENS: int = 8000
MIN_BUDGET_TOKENS: int = 2000
RECENT_SUMMARY_LIMIT: int = 3

# 分区优先级（数值越小优先级越高，裁剪时从低到高裁）
PARTITION_PRIORITY: dict[str, int] = {
    "chapter_goal": 0,
    "creative_brief": 1,
    "hard_constraints": 2,
    "genre_rules": 3,
    "mode_rules": 4,
    "character_states": 5,
    "recent_plot": 6,
    "foreshadowing": 7,
    "soft_references": 8,
}


# ---------------------------------------------------------------------------
# Token Estimation
# ---------------------------------------------------------------------------
class TokenEstimator:
    """Token 估算器 — tiktoken 为主，字符数/4 为回退."""

    def __init__(self) -> None:
        self._encoder: Any | None = None
        self._fallback: bool = False
        try:
            import tiktoken

            self._encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._fallback = True
            logger.warning("token_estimator.fallback", reason="tiktoken_unavailable")

    def estimate(self, text: str) -> int:
        """估算文本的 Token 数."""
        if not text:
            return 0
        if self._encoder is not None and not self._fallback:
            try:
                return len(self._encoder.encode(text))
            except Exception:
                pass
        # 回退：中文字符 ≈ 1 token，ASCII ≈ 0.25 token，平均按 len/2
        return max(1, len(text) // 2)

    def estimate_model(self, obj: BaseModel | dict | list | None) -> int:
        """估算 Pydantic 模型 / dict / list 的 Token 数."""
        if obj is None:
            return 0
        if isinstance(obj, BaseModel):
            text = json.dumps(obj.model_dump(mode="json"), ensure_ascii=False, default=str)
        elif isinstance(obj, (dict, list)):
            text = json.dumps(obj, ensure_ascii=False, default=str)
        else:
            text = str(obj)
        return self.estimate(text)


# ---------------------------------------------------------------------------
# Budget Pruning
# ---------------------------------------------------------------------------
class BudgetPruner:
    """按 Token 预算裁剪 ContextPackage."""

    def __init__(self, estimator: TokenEstimator | None = None) -> None:
        self.estimator = estimator or TokenEstimator()

    def prune(
        self,
        ctx: ContextPackage,
        budget_tokens: int,
    ) -> ContextPackage:
        """裁剪 ContextPackage 到预算内.

        策略：
        1. 先计算当前总 Token
        2. 如果未超预算，直接返回
        3. 超预算时按优先级从低到高裁剪：
           - soft_references → 按 relevance_score 保留高分
           - foreshadowing → 保留 status="due/overdue" 的，再按 planted_in_chapter 保留新的
           - recent_plot → 减少 summaries 数量
           - character_states → 只保留主角（importance_score=1.0）
        4. chapter_goal / creative_brief / hard_constraints / genre_rules / mode_rules 始终保留
        """
        current = self._estimate_package(ctx)
        if current <= budget_tokens:
            ctx.estimated_tokens = current
            ctx.budget_used = current / budget_tokens if budget_tokens > 0 else 0.0
            return ctx

        logger.info(
            "context_manager.prune_start",
            current_tokens=current,
            budget=budget_tokens,
            overage=current - budget_tokens,
        )

        # 逐层裁剪（从最低优先级开始）
        ctx = self._prune_soft_references(ctx, budget_tokens)
        current = self._estimate_package(ctx)
        if current <= budget_tokens:
            ctx.estimated_tokens = current
            ctx.budget_used = current / budget_tokens
            return ctx

        ctx = self._prune_foreshadowing(ctx, budget_tokens)
        current = self._estimate_package(ctx)
        if current <= budget_tokens:
            ctx.estimated_tokens = current
            ctx.budget_used = current / budget_tokens
            return ctx

        ctx = self._prune_recent_plot(ctx, budget_tokens)
        current = self._estimate_package(ctx)
        if current <= budget_tokens:
            ctx.estimated_tokens = current
            ctx.budget_used = current / budget_tokens
            return ctx

        ctx = self._prune_character_states(ctx, budget_tokens)
        current = self._estimate_package(ctx)
        ctx.estimated_tokens = current
        ctx.budget_used = current / budget_tokens

        logger.info(
            "context_manager.prune_done",
            final_tokens=current,
            budget=budget_tokens,
            budget_used=ctx.budget_used,
        )
        return ctx

    def _estimate_package(self, ctx: ContextPackage) -> int:
        """估算整个 ContextPackage 的 Token 数."""
        total = 0
        total += self.estimator.estimate_model(ctx.chapter_goal)
        if ctx.creative_brief:
            total += self.estimator.estimate_model(ctx.creative_brief)
        total += self.estimator.estimate_model(ctx.hard_constraints)
        total += self.estimator.estimate_model(ctx.character_states)
        total += self.estimator.estimate_model(ctx.recent_plot)
        total += self.estimator.estimate_model(ctx.foreshadowing)
        total += self.estimator.estimate_model(ctx.soft_references)
        total += self.estimator.estimate_model(ctx.genre_rules)
        total += self.estimator.estimate_model(ctx.mode_rules)
        return total

    def _prune_soft_references(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """裁剪 soft_references — 按 relevance_score 排序保留高分."""
        if not ctx.soft_references:
            return ctx
        current = self._estimate_package(ctx)
        if current <= budget:
            return ctx
        # 按 relevance_score 降序，保留前一半
        sorted_refs = sorted(
            ctx.soft_references, key=lambda r: r.relevance_score, reverse=True
        )
        keep_count = max(1, len(sorted_refs) // 2)
        ctx.soft_references = sorted_refs[:keep_count]
        return ctx

    def _prune_foreshadowing(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """裁剪 foreshadowing — 保留 due/overdue，再按 planted_in_chapter 保留新的."""
        if not ctx.foreshadowing:
            return ctx
        current = self._estimate_package(ctx)
        if current <= budget:
            return ctx
        # 优先保留 due/overdue
        high_priority = [
            f for f in ctx.foreshadowing if f.status in ("due", "overdue")
        ]
        rest = [f for f in ctx.foreshadowing if f.status not in ("due", "overdue")]
        # 按 planted_in_chapter 降序（新的优先）
        rest_sorted = sorted(rest, key=lambda f: f.planted_in_chapter, reverse=True)
        # 先保留高优先级，再保留一半 rest
        keep_rest = max(0, len(rest_sorted) // 2)
        ctx.foreshadowing = high_priority + rest_sorted[:keep_rest]
        return ctx

    def _prune_recent_plot(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """裁剪 recent_plot — 减少 summaries 数量."""
        if not ctx.recent_plot.summaries:
            return ctx
        current = self._estimate_package(ctx)
        if current <= budget:
            return ctx
        # 保留最近的一半 summaries
        summaries = ctx.recent_plot.summaries
        keep_count = max(1, len(summaries) // 2)
        ctx.recent_plot.summaries = summaries[-keep_count:]
        return ctx

    def _prune_character_states(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """裁剪 character_states — 只保留主角（importance_score=1.0）."""
        if not ctx.character_states:
            return ctx
        current = self._estimate_package(ctx)
        if current <= budget:
            return ctx
        # 保留主角（importance_score == 1.0）和出场角色（>= 0.8）
        ctx.character_states = [
            s for s in ctx.character_states if s.importance_score >= 0.8
        ]
        return ctx


# ---------------------------------------------------------------------------
# Partition Builders
# ---------------------------------------------------------------------------
def _build_hard_constraints(
    chapter_goal: ChapterGoal,
    genre_profile: GenreProfile,
    project: ProjectSetting,
) -> list[HardConstraint]:
    """构建硬约束 — obligations + taboos."""
    constraints: list[HardConstraint] = []
    for obligation in chapter_goal.obligations:
        constraints.append(
            HardConstraint(
                type="obligation",
                description=obligation,
                source="chapter_goal",
            )
        )
    for taboo in genre_profile.taboos:
        constraints.append(
            HardConstraint(
                type="taboo",
                description=taboo,
                source="genre_profile",
            )
        )
    for taboo in project.taboos:
        constraints.append(
            HardConstraint(
                type="taboo",
                description=taboo,
                source="project_setting",
            )
        )
    return constraints


def _build_character_snapshots(
    characters: list[Character],
    character_states: list[CharacterState],
) -> list[CharacterStateSnapshot]:
    """构建角色状态快照 — 合并角色档案和最新状态."""
    # 按角色 ID 分组状态
    state_map: dict[str, list[CharacterState]] = {}
    for state in character_states:
        state_map.setdefault(state.character_id, []).append(state)

    snapshots: list[CharacterStateSnapshot] = []
    for char in characters:
        states = state_map.get(char.character_id, [])
        # 按 field 取最新状态
        latest_by_field: dict[str, str] = {}
        for state in states:
            # 简单策略：后面的覆盖前面的（假设按时间排序传入）
            latest_by_field[state.field] = state.value

        importance = 1.0 if char.role_type == "protagonist" else 0.8
        snapshot = CharacterStateSnapshot(
            character_id=char.character_id,
            name=char.name,
            current_location=latest_by_field.get("location"),
            current_cultivation=latest_by_field.get("cultivation"),
            emotional_state=latest_by_field.get("emotional_state"),
            active_relationships=list(char.relationships.keys()),
            unresolved_issues=char.goals.copy(),
            importance_score=importance,
        )
        snapshots.append(snapshot)
    return snapshots


def _build_recent_plot(
    summaries: list[ChapterSummary],
    last_chapter_ending: str = "",
    open_threads: list[str] | None = None,
) -> RecentPlot:
    """构建最近剧情."""
    return RecentPlot(
        summaries=summaries,
        last_chapter_ending=last_chapter_ending,
        open_threads=open_threads or [],
    )


def _build_soft_references(
    settings: list[NewSetting],
) -> list[SoftReference]:
    """构建软参考 — 从设定快照转换."""
    refs: list[SoftReference] = []
    for setting in settings:
        refs.append(
            SoftReference(
                type="world_setting",
                content=f"{setting.setting_name}: {setting.description}",
                relevance_score=0.7,
            )
        )
    return refs


def _build_genre_rules(genre_profile: GenreProfile) -> GenreRules:
    """从 GenreProfile 构建 GenreRules."""
    return GenreRules(
        genre_id=genre_profile.id,
        writer_rules=genre_profile.writer_rules,
        fatigue_words=genre_profile.fatigue_words,
        satisfaction_types=genre_profile.satisfaction_types,
        pacing_rule=genre_profile.pacing_rule,
        taboos=genre_profile.taboos,
    )


def _build_mode_rules(mode_profile: CreativeModeProfile) -> ModeRules:
    """从 CreativeModeProfile 构建 ModeRules."""
    tolerance = mode_profile.tolerance or {}
    return ModeRules(
        mode_id=mode_profile.id,
        revision_policy=mode_profile.revision_policy,
        tolerance_max_ai_tells=tolerance.get("max_ai_tells", 2.0),
        tolerance_max_fatigue_words=tolerance.get("max_fatigue_words", 3.0),
        tolerance_max_cliche_risk=tolerance.get("max_cliche_risk", 2.0),
        context_pruning_strategy=mode_profile.context_pruning_strategy,
    )


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
async def assemble_context_package(
    chapter_goal: ChapterGoal,
    creative_brief: CreativeBrief | None,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    project: ProjectSetting,
    characters: list[Character],
    character_states: list[CharacterState],
    recent_summaries: list[ChapterSummary],
    active_foreshadowings: list[ForeshadowingItem],
    setting_snapshots: list[NewSetting],
    budget_tokens: int = DEFAULT_BUDGET_TOKENS,
    last_chapter_ending: str = "",
    open_threads: list[str] | None = None,
) -> ContextPackage:
    """组装上下文包并按 Token 预算裁剪.

    Args:
        chapter_goal: 章节目标（GoalPlanner 输出）
        creative_brief: 创作导演简报（CreativeDirector 输出）
        genre_profile: 题材配置
        mode_profile: 创作模式配置
        project: 项目设定
        characters: 角色列表
        character_states: 角色状态快照列表
        recent_summaries: 最近章节摘要列表
        active_foreshadowings: 活跃伏笔列表
        setting_snapshots: 设定快照列表
        budget_tokens: Token 预算（默认 8000）
        last_chapter_ending: 上一章结尾内容
        open_threads: 未完结线索

    Returns:
        组装并裁剪后的 ContextPackage
    """
    if budget_tokens < MIN_BUDGET_TOKENS:
        logger.warning(
            "context_manager.low_budget",
            budget=budget_tokens,
            min_budget=MIN_BUDGET_TOKENS,
        )
        budget_tokens = MIN_BUDGET_TOKENS

    logger.info(
        "context_manager.assemble_start",
        chapter_number=chapter_goal.chapter_number,
        budget=budget_tokens,
    )

    # 构建各分区
    hard_constraints = _build_hard_constraints(chapter_goal, genre_profile, project)
    character_snapshots = _build_character_snapshots(characters, character_states)
    recent_plot = _build_recent_plot(
        recent_summaries, last_chapter_ending, open_threads
    )
    soft_refs = _build_soft_references(setting_snapshots)
    genre_rules = _build_genre_rules(genre_profile)
    mode_rules = _build_mode_rules(mode_profile)

    ctx = ContextPackage(
        chapter_goal=chapter_goal,
        creative_brief=creative_brief,
        hard_constraints=hard_constraints,
        character_states=character_snapshots,
        recent_plot=recent_plot,
        foreshadowing=list(active_foreshadowings),
        soft_references=soft_refs,
        genre_rules=genre_rules,
        mode_rules=mode_rules,
    )

    # Token 预算裁剪
    pruner = BudgetPruner()
    ctx = pruner.prune(ctx, budget_tokens)

    logger.info(
        "context_manager.assemble_done",
        chapter_number=chapter_goal.chapter_number,
        estimated_tokens=ctx.estimated_tokens,
        budget_used=ctx.budget_used,
    )
    return ctx
