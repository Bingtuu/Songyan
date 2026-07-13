"""ContextManager Agent — 上下文包组装与 Token 预算裁剪."""

from __future__ import annotations

import random
from typing import Any

import structlog

from songyan.models import (
    ArcSummary,
    ChapterGoal,
    ChapterSummary,
    Character,
    CharacterState,
    ContextPackage,
    CreativeBrief,
    CreativeModeProfile,
    ForeshadowingItem,
    GenreProfile,
    HumanMark,
    NewSetting,
    OpenThread,
    PermanentScene,
    ProjectSetting,
    RetrievedChunk,
    SoftReference,
    StyleSample,
    VolumeSummary,
)
from songyan.utils.token_estimator import TokenEstimator

from ._assemblers import (
    _build_character_snapshots,
    _build_genre_rules,
    _build_hard_constraints,
    _build_mode_rules,
    _build_rag_soft_references,
    _build_recent_plot,
    _build_soft_references,
    _dynamic_budget,
    _extract_keywords,
    _is_setting_critical,
)
from ._assemblers import (
    _calculate_dynamic_relevance as _calculate_dynamic_relevance,
)

__all__ = [
    "assemble_context_package",
    "BudgetPruner",
    "_build_genre_rules",
    "_calculate_dynamic_relevance",
    "_calculate_objective_fullness",
    "_dynamic_max_for_chapter",
    "_dynamic_max_character_states",
    "_dynamic_max_soft_refs",
    "_rank_foreshadowings",
]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# V4.0: DEFAULT_BUDGET_TOKENS 作为动态预算的基数。
# 实际预算 = base + chapter_number * BUDGET_INCREMENT_PER_CHAPTER
DEFAULT_BUDGET_TOKENS: int = 8000
MIN_BUDGET_TOKENS: int = 2000
RECENT_SUMMARY_LIMIT: int = 3

# 各分区硬上限（防止长尺度上下文膨胀）
MAX_SOFT_REFS: int = 10          # 设定快照转软参考的上限
MAX_FORESHADOWING: int = 8       # 活跃伏笔上限
MAX_CHARACTER_STATES: int = 4    # 角色状态上限
MAX_PERMANENT_SCENES: int = 3    # Phase 4: 永久场景上限
MAX_OPEN_THREADS: int = 5        # Phase 4: 开放线索上限

# 077a: setting_snapshots → SoftReference 的入站硬上限
# 077a: 关键词工具函数
MAX_SETTING_INPUT: int = 10       # is_critical 不计入上限

# 077b: BudgetPruner 硬断言阈值
HARD_ENFORCE_THRESHOLD: float = 1.3  # 超过预算 130% 时触发硬断言核裁


# ---------------------------------------------------------------------------
# Task 110c: 按章节阶段动态调整硬上限
# ---------------------------------------------------------------------------
def _dynamic_max_for_chapter(chapter_number: int) -> dict[str, int]:
    """Ch80+ 收紧各分区硬上限，降低初始 token 负担."""
    if chapter_number <= 80:
        return {
            "max_setting_input": MAX_SETTING_INPUT,
            "max_foreshadowing": MAX_FORESHADOWING,
            "max_character_states": MAX_CHARACTER_STATES,
        }
    return {
        "max_setting_input": 6,
        "max_foreshadowing": 5,
        "max_character_states": 3,
    }


# ---------------------------------------------------------------------------
# Task 100c: 客观叙事充满度 + 动态硬上限
# ---------------------------------------------------------------------------
def _calculate_objective_fullness(narrative_fullness: float, budget_used: float) -> float:
    """基于 token_budget 客观计算 narrative_fullness.

    规则：
    - budget_used > 0.95 → fullness = max(fullness, 0.9)
    - budget_used > 0.90 → fullness = max(fullness, 0.7)
    - 否则保持 LLM 输出的 fullness
    """
    if budget_used > 0.95:
        return max(narrative_fullness, 0.9)
    if budget_used > 0.90:
        return max(narrative_fullness, 0.7)
    return narrative_fullness


def _dynamic_max_character_states(total_characters: int) -> int:
    """动态角色状态硬上限."""
    return max(4, min(8, total_characters // 3 + 1))


def _dynamic_max_soft_refs(total_settings: int) -> int:
    """动态软参考硬上限."""
    return max(10, min(16, total_settings // 5 + 2))

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
    "permanent_scenes": 8,   # Phase 4 新增
    "open_threads": 9,       # Phase 4 新增
    "soft_references": 10,   # 降级
}


# ---------------------------------------------------------------------------
# Budget Pruning
# ---------------------------------------------------------------------------
class BudgetPruner:
    """按 Token 预算裁剪 ContextPackage."""

    def __init__(self, estimator: TokenEstimator | None = None) -> None:
        self.estimator = estimator or TokenEstimator()

    def _log_breakdown(self, ctx: ContextPackage, budget: int, step: str) -> None:
        """诊断日志：记录各分区 token 分配."""
        est = self.estimator
        total = est.estimate_model(ctx)
        char_tok = est.estimate_model(ctx.character_states) if ctx.character_states else 0
        plot_tok = est.estimate_model(ctx.recent_plot) if ctx.recent_plot else 0
        soft_tok = est.estimate_model(ctx.soft_references) if ctx.soft_references else 0
        fore_tok = est.estimate_model(ctx.foreshadowing) if ctx.foreshadowing else 0
        hard_tok = est.estimate_model(ctx.hard_constraints) if ctx.hard_constraints else 0
        arc_tok = est.estimate_model(ctx.arc_context) if ctx.arc_context else 0
        vol_tok = est.estimate_model(ctx.volume_context) if ctx.volume_context else 0
        scene_tok = est.estimate_model(ctx.permanent_scenes) if ctx.permanent_scenes else 0
        thread_tok = est.estimate_model(ctx.open_threads) if ctx.open_threads else 0
        mark_tok = est.estimate_model(ctx.human_marks) if ctx.human_marks else 0
        logger.info(
            "context_manager.budget_breakdown",
            step=step,
            total=total,
            budget=budget,
            budget_used=round(total / budget, 3) if budget else 0,
            character_states=char_tok,
            recent_plot=plot_tok,
            soft_references=soft_tok,
            foreshadowing=fore_tok,
            hard_constraints=hard_tok,
            arc_context=arc_tok,
            volume_context=vol_tok,
            permanent_scenes=scene_tok,
            open_threads=thread_tok,
            human_marks=mark_tok,
            character_count=len(ctx.character_states) if ctx.character_states else 0,
        )

    def prune(
        self,
        ctx: ContextPackage,
        budget_tokens: int,
        *,
        narrative_fullness: float = 0.0,
        focal_distance: str = "mid",
        max_soft_refs: int | None = None,
        max_character_states: int | None = None,
        chapter_number: int = 0,
    ) -> ContextPackage:
        """裁剪 ContextPackage 到预算内.

        策略：
        1. 先计算当前总 Token
        2. 如果未超预算，直接返回
        3. 超预算时按优先级从低到高裁剪
        4. chapter_goal / creative_brief / hard_constraints / genre_rules / mode_rules 始终保留
        """
        ctx = ctx.model_copy(deep=True)

        # Task 098: 应用 narrative_fullness 动态调整上限
        fullness_factor = self._dynamic_fullness_factor(narrative_fullness)
        # Task 100c: 使用动态硬上限（若提供）否则回退到固定常量
        _max_soft = max_soft_refs if max_soft_refs is not None else MAX_SOFT_REFS
        _max_char = (
            max_character_states if max_character_states is not None else MAX_CHARACTER_STATES
        )
        dynamic_max_soft = max(1, round(_max_soft * fullness_factor))
        dynamic_max_fore = max(1, round(MAX_FORESHADOWING * fullness_factor))
        dynamic_max_char = max(1, round(_max_char * fullness_factor))

        # Task 098: 应用 focal_distance 调整上下文包
        # Task 100c: 传入 chapter_number 用于 disruption 随机 seed
        ctx = self._apply_focal_distance(ctx, focal_distance, chapter_number=chapter_number)
        self._log_breakdown(ctx, budget_tokens, step="after_focal_distance")

        # Task 098: 即使未超预算，也应用动态上限防止上下文膨胀
        ctx = self._prune_soft_references(ctx, budget_tokens, max_refs=dynamic_max_soft)
        ctx = self._prune_foreshadowing(ctx, budget_tokens, max_items=dynamic_max_fore)
        ctx = self._prune_character_states(ctx, budget_tokens, max_states=dynamic_max_char)
        self._log_breakdown(ctx, budget_tokens, step="after_character_prune")

        # Task 110c: 分区预算制 — 各分区先内部压缩到预算比例
        ctx = self._apply_partition_budgets(ctx, budget_tokens)
        self._log_breakdown(ctx, budget_tokens, step="after_partition_budgets")

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
            fullness_factor=fullness_factor,
            focal_distance=focal_distance,
        )

        # 逐层裁剪（从最低优先级开始）
        # 注：soft_references / foreshadowing / character_states 已在预算检查前应用动态上限
        ctx = self._prune_open_threads(ctx, budget_tokens)
        current = self._estimate_package(ctx)
        if current <= budget_tokens:
            ctx.estimated_tokens = current
            ctx.budget_used = current / budget_tokens
            return ctx

        ctx = self._prune_permanent_scenes(ctx, budget_tokens)
        current = self._estimate_package(ctx)
        if current <= budget_tokens:
            ctx.estimated_tokens = current
            ctx.budget_used = current / budget_tokens
            return ctx

        # foreshadowing 已在预算检查前应用动态上限，跳过重复裁剪
        ctx = self._prune_recent_plot(ctx, budget_tokens)
        current = self._estimate_package(ctx)
        if current <= budget_tokens:
            ctx.estimated_tokens = current
            ctx.budget_used = current / budget_tokens
            return ctx

        # character_states 已在预算检查前应用动态上限，跳过重复裁剪

        # V3.1 Layer 2: 当所有可裁剪分区都已压缩后仍超预算，
        # 开始裁剪硬约束中的 human_marks（非核心）
        ctx = self._prune_hard_constraints(ctx, budget_tokens)
        current = self._estimate_package(ctx)
        if current <= budget_tokens:
            ctx.estimated_tokens = current
            ctx.budget_used = current / budget_tokens
            return ctx

        # V3.1 Layer 2: 最后手段 — 压缩 arc/volume 摘要长度
        ctx = self._prune_arc_volume_context(ctx, budget_tokens)
        current = self._estimate_package(ctx)

        # 077b: 硬断言 — 逐层裁剪后仍超预算时启动核裁
        if current > int(budget_tokens * HARD_ENFORCE_THRESHOLD):
            ctx = self._enforce_budget_hard(ctx, budget_tokens)
            current = self._estimate_package(ctx)
            ctx._budget_enforced = True
            self._log_breakdown(ctx, budget_tokens, step="after_hard_enforce")

        ctx.estimated_tokens = current
        ctx.budget_used = current / budget_tokens if budget_tokens > 0 else 0.0

        # Task 104: ContextEmergency — 硬天花板最后防线
        if ctx.budget_used > 1.0:
            ctx = self._context_emergency(ctx, budget_tokens)
            current = self._estimate_package(ctx)
            ctx.estimated_tokens = current
            ctx.budget_used = current / budget_tokens if budget_tokens > 0 else 0.0

        if current > budget_tokens:
            logger.warning(
                "context_manager.prune_failed_hard_limit",
                final_tokens=current,
                budget=budget_tokens,
                overage=current - budget_tokens,
                budget_enforced=ctx._budget_enforced,
                context_emergency=ctx.context_emergency,
            )

        logger.info(
            "context_manager.prune_done",
            final_tokens=current,
            budget=budget_tokens,
            budget_used=ctx.budget_used,
            budget_enforced=ctx._budget_enforced,
            context_emergency=ctx.context_emergency,
        )
        return ctx

    def _apply_partition_budgets(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """Task 110c: 分区预算制 — 各分区先内部压缩到预算比例.

        分区比例：
        - character_states: 30%
        - recent_plot: 20%
        - soft_references: 15%
        - foreshadowing: 10%
        """
        if budget <= 0:
            return ctx

        partitions: dict[str, tuple[Any, float]] = {
            "character_states": (ctx.character_states, 0.30),
            "recent_plot": (ctx.recent_plot, 0.20),
            "soft_references": (ctx.soft_references, 0.15),
            "foreshadowing": (ctx.foreshadowing, 0.10),
        }

        for name, (data, ratio) in partitions.items():
            if not data:
                continue
            max_tokens = int(budget * ratio)
            current = self.estimator.estimate_model(data)
            logger.info(
                "context_manager.partition_budget_check",
                partition=name,
                current_tokens=current,
                max_tokens=max_tokens,
                ratio=ratio,
                exceeded=current > max_tokens,
            )
            if current > max_tokens:
                logger.info(
                    "context_manager.partition_budget_exceeded",
                    partition=name,
                    current_tokens=current,
                    max_tokens=max_tokens,
                )
                if name == "character_states":
                    keep = max(1, int(len(ctx.character_states) * 0.7))
                    # Task 110d fix: 确保 protagonist + antagonist 至少保留 2 个
                    if len(ctx.character_states) >= 2:
                        keep = max(2, keep)
                    ctx.character_states = sorted(
                        ctx.character_states,
                        key=lambda s: s.importance_score,
                        reverse=True,
                    )[:keep]
                elif name == "recent_plot":
                    if ctx.recent_plot and ctx.recent_plot.summaries:
                        keep = max(1, len(ctx.recent_plot.summaries) // 2)
                        ctx.recent_plot.summaries = ctx.recent_plot.summaries[-keep:]
                elif name == "soft_references":
                    keep = max(1, int(len(ctx.soft_references) * 0.6))
                    sorted_refs = sorted(
                        ctx.soft_references,
                        key=lambda r: r.relevance_score,
                        reverse=True,
                    )
                    ctx.soft_references = sorted_refs[:keep]
                elif name == "foreshadowing":
                    high = [f for f in ctx.foreshadowing if f.status in ("due", "overdue")]
                    rest = [f for f in ctx.foreshadowing if f.status not in ("due", "overdue")]
                    keep_rest = max(0, int(len(rest) * 0.5))
                    ctx.foreshadowing = high + rest[:keep_rest]

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
        # Phase 4 新增分区
        total += self.estimator.estimate_model(ctx.arc_context)
        total += self.estimator.estimate_model(ctx.volume_context)
        total += self.estimator.estimate_model(ctx.permanent_scenes)
        total += self.estimator.estimate_model(ctx.open_threads)
        # Phase 7 新增
        total += self.estimator.estimate_model(ctx.human_marks)
        total += self.estimator.estimate_model(ctx.dialogue_style_cards)
        return total

    def _prune_soft_references(
        self, ctx: ContextPackage, budget: int, max_refs: int | None = None
    ) -> ContextPackage:
        """裁剪 soft_references — 按 relevance_score 排序保留高分，有硬上限."""
        _max = max_refs if max_refs is not None else MAX_SOFT_REFS
        if not ctx.soft_references:
            return ctx
        current = self._estimate_package(ctx)
        if current <= budget:
            # 即使未超预算，也应用硬上限防止膨胀
            if len(ctx.soft_references) > _max:
                sorted_refs = sorted(
                    ctx.soft_references, key=lambda r: r.relevance_score, reverse=True
                )
                ctx.soft_references = sorted_refs[:_max]
            return ctx
        # 按 relevance_score 降序，保留前一半但不超硬上限
        sorted_refs = sorted(
            ctx.soft_references, key=lambda r: r.relevance_score, reverse=True
        )
        keep_count = min(max(1, len(sorted_refs) // 2), _max)
        ctx.soft_references = sorted_refs[:keep_count]
        return ctx

    def _prune_foreshadowing(
        self, ctx: ContextPackage, budget: int, max_items: int | None = None
    ) -> ContextPackage:
        """裁剪 foreshadowing — 保留 due/overdue，再按 planted_in_chapter 保留新的."""
        _max = max_items if max_items is not None else MAX_FORESHADOWING
        if not ctx.foreshadowing:
            return ctx
        current = self._estimate_package(ctx)
        if current <= budget:
            if len(ctx.foreshadowing) > _max:
                ctx.foreshadowing = ctx.foreshadowing[:_max]
            return ctx
        # 优先保留 due/overdue
        high_priority = [
            f for f in ctx.foreshadowing if f.status in ("due", "overdue")
        ]
        rest = [f for f in ctx.foreshadowing if f.status not in ("due", "overdue")]
        # 按 planted_in_chapter 降序（新的优先）
        rest_sorted = sorted(rest, key=lambda f: f.planted_in_chapter, reverse=True)
        # 先保留高优先级，再保留一半 rest，但不超总上限
        keep_rest = min(max(0, len(rest_sorted) // 2), max(0, _max - len(high_priority)))
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
        self, ctx: ContextPackage, budget: int, max_states: int | None = None
    ) -> ContextPackage:
        """裁剪 character_states — 只保留主角和重要角色，有硬上限."""
        _max = max_states if max_states is not None else MAX_CHARACTER_STATES
        if not ctx.character_states:
            return ctx
        current = self._estimate_package(ctx)
        char_tokens = self.estimator.estimate_model(ctx.character_states)
        if current <= budget:
            # 即使未超预算，也应用硬上限防止膨胀
            if len(ctx.character_states) > _max:
                sorted_states = sorted(
                    ctx.character_states,
                    key=lambda s: s.importance_score,
                    reverse=True,
                )
                ctx.character_states = sorted_states[:_max]
                logger.info(
                    "context_manager.character_states_hard_cap",
                    before_count=len(sorted_states),
                    after_count=_max,
                    characters=[(s.name, s.importance_score) for s in sorted_states[:_max]],
                    char_tokens=char_tokens,
                )
            return ctx
        # 保留主角和重要角色，按 importance_score 排序
        sorted_states = sorted(
            ctx.character_states, key=lambda s: s.importance_score, reverse=True
        )
        keep_count = min(max(2, len(sorted_states) // 2), _max)
        kept = sorted_states[:keep_count]
        dropped = sorted_states[keep_count:]
        ctx.character_states = kept
        logger.info(
            "context_manager.character_states_pruned",
            before_count=len(sorted_states),
            after_count=keep_count,
            kept=[(s.name, s.importance_score) for s in kept],
            dropped=[(s.name, s.importance_score) for s in dropped],
            char_tokens=char_tokens,
            total_tokens=current,
            budget=budget,
        )
        return ctx

    # Phase 4 新增裁剪方法
    def _prune_permanent_scenes(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """裁剪 permanent_scenes — 硬上限 3."""
        if not ctx.permanent_scenes:
            return ctx
        current = self._estimate_package(ctx)
        if current <= budget:
            if len(ctx.permanent_scenes) > MAX_PERMANENT_SCENES:
                ctx.permanent_scenes = ctx.permanent_scenes[:MAX_PERMANENT_SCENES]
            return ctx
        keep = min(max(1, len(ctx.permanent_scenes) // 2), MAX_PERMANENT_SCENES)
        ctx.permanent_scenes = ctx.permanent_scenes[:keep]
        return ctx

    def _prune_open_threads(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """裁剪 open_threads — 按 priority 排序，硬上限 5."""
        if not ctx.open_threads:
            return ctx
        current = self._estimate_package(ctx)
        if current <= budget:
            if len(ctx.open_threads) > MAX_OPEN_THREADS:
                sorted_threads = sorted(
                    ctx.open_threads, key=lambda t: t.priority, reverse=True
                )
                ctx.open_threads = sorted_threads[:MAX_OPEN_THREADS]
            return ctx
        sorted_threads = sorted(
            ctx.open_threads, key=lambda t: t.priority, reverse=True
        )
        keep = min(max(1, len(sorted_threads) // 2), MAX_OPEN_THREADS)
        ctx.open_threads = sorted_threads[:keep]
        return ctx

    # V3.1 Layer 2 新增：硬约束中的人为标记可裁剪
    def _prune_hard_constraints(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """Task 111c: hard_constraints 不裁剪；human_marks 使用独立分区."""
        _ = budget
        return ctx

    # V3.1 Layer 2 新增：arc/volume 摘要最后手段截断
    def _prune_arc_volume_context(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """截断 arc_context 和 volume_context 的摘要长度（最后手段）."""
        current = self._estimate_package(ctx)
        if current <= budget:
            return ctx

        if ctx.arc_context is not None and ctx.arc_context.arc_summary:
            arc = ctx.arc_context.model_copy(deep=True)
            max_arc = 200
            if len(arc.arc_summary) > max_arc:
                arc.arc_summary = arc.arc_summary[:max_arc] + "..."
            if len(arc.key_events) > 3:
                arc.key_events = arc.key_events[:3]
            if len(arc.character_arcs) > 3:
                keep = sorted(
                    arc.character_arcs.items(),
                    key=lambda kv: len(kv[1]),
                    reverse=True,
                )[:3]
                arc.character_arcs = dict(keep)
            ctx.arc_context = arc

        if ctx.volume_context is not None and ctx.volume_context.volume_summary:
            vol = ctx.volume_context.model_copy(deep=True)
            max_vol = 150
            if len(vol.volume_summary) > max_vol:
                vol.volume_summary = vol.volume_summary[:max_vol] + "..."
            if len(vol.major_revelations) > 3:
                vol.major_revelations = vol.major_revelations[:3]
            ctx.volume_context = vol

        return ctx

    @staticmethod
    def _dynamic_fullness_factor(narrative_fullness: float) -> float:
        """叙事充满度 → 上下文包紧凑度乘数.

        Task 104: 0.5 → 0.7，更 aggressive 地收紧上下文上限。
        """
        return 1.0 - (narrative_fullness * 0.7)

    def _apply_focal_distance(
        self, ctx: ContextPackage, focal_distance: str, chapter_number: int = 0
    ) -> ContextPackage:
        """根据景深调整上下文包配置.

        close:  极致聚焦 — 极少量上下文，高感官密度
        mid:    标准叙事 — 默认配置（不修改）
        wide:   广角呼吸 — 更多设定/场景，减少角色细节
        disruption: 打破常规 — 随机裁剪制造叙事断裂感
        """
        if focal_distance == "close":
            if ctx.soft_references:
                ctx.soft_references = ctx.soft_references[:3]
            if ctx.permanent_scenes:
                ctx.permanent_scenes = ctx.permanent_scenes[:1]
            if ctx.open_threads:
                ctx.open_threads = ctx.open_threads[:1]
        elif focal_distance == "wide":
            # 广角：保留更多软参考和开放线索，压缩角色状态
            if ctx.character_states:
                # 只保留主角 + 1 个重要角色
                sorted_states = sorted(
                    ctx.character_states, key=lambda s: s.importance_score, reverse=True
                )
                ctx.character_states = sorted_states[:2]
            # 软参考和线索上限由动态预算处理，这里不做硬截断
        elif focal_distance == "disruption":
            # Task 100c: 随机截断（固定 seed 保证可复现）
            if ctx.soft_references and len(ctx.soft_references) > 2:
                rng = random.Random(chapter_number)
                rng.shuffle(ctx.soft_references)
                keep = max(1, len(ctx.soft_references) // 2)
                ctx.soft_references = ctx.soft_references[:keep]
            if ctx.foreshadowing and len(ctx.foreshadowing) > 2:
                rng = random.Random(chapter_number + 1)
                fore_list = list(ctx.foreshadowing)
                rng.shuffle(fore_list)
                keep = max(1, len(fore_list) // 2)
                ctx.foreshadowing = fore_list[:keep]
        return ctx


    def _enforce_budget_hard(
        self, ctx: ContextPackage, budget: int
    ) -> ContextPackage:
        """硬断言：逐级丢弃低优先级分区，直到预算达标或无可裁分区.

        在 prune() 逐层裁剪全部完成后调用.
        从不裁剪: hard_constraints, genre_rules, mode_rules
        """
        # 辅助检查：当前是否仍超预算（使用原始预算值，非阈值）
        def _over() -> bool:
            return self._estimate_package(ctx) > budget

        # Step 1: 丢弃 dialogue_style_cards（全部）
        if _over() and ctx.dialogue_style_cards:
            before = self._estimate_package(ctx)
            ctx.dialogue_style_cards = []
            after = self._estimate_package(ctx)
            logger.info(
                "context_manager.hard_enforce", step=1,
                from_partition="dialogue_style_cards",
                dropped=before - after, left=0,
                current_total=after, budget=budget,
            )

        # Step 2: 裁剪 open_threads（只保留 priority > 0.8，上限 2）
        if _over() and ctx.open_threads:
            before = self._estimate_package(ctx)
            ctx.open_threads = [t for t in ctx.open_threads if t.priority > 0.8][:2]
            after = self._estimate_package(ctx)
            logger.info(
                "context_manager.hard_enforce", step=2,
                from_partition="open_threads",
                dropped=before - after, left=len(ctx.open_threads),
                current_total=after, budget=budget,
            )

        # Step 3: 裁剪 soft_references（保留 Top-4）
        if _over() and ctx.soft_references:
            before = self._estimate_package(ctx)
            ctx.soft_references = sorted(
                ctx.soft_references, key=lambda r: r.relevance_score, reverse=True
            )[:4]
            after = self._estimate_package(ctx)
            logger.info(
                "context_manager.hard_enforce", step=3,
                from_partition="soft_references",
                dropped=before - after, left=len(ctx.soft_references),
                current_total=after, budget=budget,
            )

        # Step 4: 裁剪 foreshadowing（只保留 due/overdue）
        if _over() and ctx.foreshadowing:
            before = self._estimate_package(ctx)
            ctx.foreshadowing = [f for f in ctx.foreshadowing if f.status in ("due", "overdue")]
            after = self._estimate_package(ctx)
            logger.info(
                "context_manager.hard_enforce", step=4,
                from_partition="foreshadowing",
                dropped=before - after, left=len(ctx.foreshadowing),
                current_total=after, budget=budget,
            )

        # Step 5: 裁剪 character_states（只保留 importance >= 0.9）
        if _over() and ctx.character_states:
            before = self._estimate_package(ctx)
            ctx.character_states = [
                s for s in ctx.character_states if s.importance_score >= 0.9
            ]
            after = self._estimate_package(ctx)
            logger.info(
                "context_manager.hard_enforce", step=5,
                from_partition="character_states",
                dropped=before - after, left=len(ctx.character_states),
                current_total=after, budget=budget,
            )

        # Step 6: 终极兜底 — arc/volume 摘要截断 + recent_plot 最小化
        if _over():
            before = self._estimate_package(ctx)
            # 截断 arc_summary
            if ctx.arc_context and ctx.arc_context.arc_summary:
                arc = ctx.arc_context.model_copy(deep=True)
                if len(arc.arc_summary) > 100:
                    arc.arc_summary = arc.arc_summary[:100] + "..."
                if len(arc.key_events) > 2:
                    arc.key_events = arc.key_events[:2]
                ctx.arc_context = arc
            # 截断 volume_summary
            if ctx.volume_context and ctx.volume_context.volume_summary:
                vol = ctx.volume_context.model_copy(deep=True)
                if len(vol.volume_summary) > 80:
                    vol.volume_summary = vol.volume_summary[:80] + "..."
                if len(vol.major_revelations) > 1:
                    vol.major_revelations = vol.major_revelations[:1]
                ctx.volume_context = vol
            # 只保留最近 1 章摘要
            if ctx.recent_plot and len(ctx.recent_plot.summaries) > 1:
                ctx.recent_plot.summaries = ctx.recent_plot.summaries[-1:]
            after = self._estimate_package(ctx)
            logger.info(
                "context_manager.hard_enforce", step=6,
                from_partition="nuclear_fallback",
                dropped=before - after,
                current_total=after, budget=budget,
            )

        return ctx

    def _context_emergency(self, ctx: ContextPackage, budget: int) -> ContextPackage:
        """ContextEmergency — 真正超预算后的最终硬裁。

        Task 111c: pre-emergency / soft-degrade 不再使用 context_emergency 表示。
        一旦 budget_used > 1.0，最终形态只保留硬约束、规则、章节目标、
        creative_brief 和主角/最高优先级角色状态。
        """
        before = self._estimate_package(ctx)
        level = 3
        ctx.budget_used_before_emergency = before / budget if budget > 0 else None

        ctx.dialogue_style_cards = []
        ctx.human_marks = []
        ctx.soft_references = []
        ctx.foreshadowing = []
        ctx.open_threads = []
        ctx.permanent_scenes = []
        ctx.arc_context = None
        ctx.volume_context = None
        if ctx.character_states:
            top_char = max(ctx.character_states, key=lambda s: s.importance_score)
            ctx.character_states = [top_char]
        if ctx.recent_plot:
            rp = ctx.recent_plot.model_copy(deep=True)
            rp.summaries = []
            rp.last_chapter_ending = ""
            rp.open_threads = []
            ctx.recent_plot = rp

        ctx.context_emergency = True
        ctx.context_emergency_level = level
        after = self._estimate_package(ctx)
        if after > budget:
            logger.warning(
                "context_manager.context_emergency_irreducible",
                after_tokens=after,
                budget=budget,
                reason="hard_partitions_exceed_budget",
            )

        logger.warning(
            "context_manager.context_emergency_triggered",
            level=level,
            before_tokens=before,
            after_tokens=after,
            budget=budget,
            budget_used_before_emergency=ctx.budget_used_before_emergency,
            budget_used_after_emergency=after / budget if budget > 0 else 0.0,
        )
        return ctx

# ---------------------------------------------------------------------------
# Task 098: 伏笔紧迫性排序
# ---------------------------------------------------------------------------
def _rank_foreshadowings(
    items: list[ForeshadowingItem],
    *,
    foreshadowing_due: list[str],
    current_chapter: int,
) -> list[ForeshadowingItem]:
    """按紧迫性对伏笔排序.

    规则：
    1. foreshadowing_due 列表中的 → 最高优先级（urgency +3.0）
    2. expected_resolve_chapter 在 2 章之内 → 高紧迫（urgency +2.0）
    3. status 为 overdue → 高紧迫（urgency +2.5）
    4. 与当前章出场角色相关 → 中等紧迫（urgency +1.0）
    5. 按 planted_in_chapter 降序（新的优先）
    """
    ranked: list[tuple[ForeshadowingItem, float]] = []
    due_set = set(foreshadowing_due)

    for item in items:
        urgency = 0.0
        if item.foreshadowing_id in due_set:
            urgency += 3.0
        if item.status == "overdue":
            urgency += 2.5
        elif (
            item.expected_resolve_chapter
            and (item.expected_resolve_chapter - current_chapter) <= 2
        ):
            urgency += 2.0
        if item.status == "due":
            urgency += 1.5
        # 新的伏笔优先级略高
        if item.planted_in_chapter:
            urgency += item.planted_in_chapter * 0.01
        ranked.append((item, urgency))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return [item for item, _ in ranked]

# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
def assemble_context_package(
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
    recent_plot_threads: list[str] | None = None,
    open_threads: list[OpenThread] | None = None,
    arc_context: ArcSummary | None = None,
    volume_context: VolumeSummary | None = None,
    permanent_scenes: list[PermanentScene] | None = None,
    style_samples: list[StyleSample] | None = None,
    human_marks: list[HumanMark] | None = None,
    rag_chunks: list[RetrievedChunk] | None = None,
    dialogue_style_cards: list[Any] | None = None,
    *,
    narrative_fullness: float = 0.0,
    character_focus: list[dict[str, Any]] | None = None,
    foreshadowing_due: list[str] | None = None,
    focal_distance: str = "mid",
    last_appeared_chapters: dict[str, int] | None = None,
    mandatory_references: list[dict[str, Any]] | None = None,
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
        recent_plot_threads: 未完结线索（用于 RecentPlot）
        open_threads: 未完结线索（OpenThread 对象列表）
        arc_context: 当前 Arc 摘要
        volume_context: 本卷摘要
        permanent_scenes: 关键场景永久保留
        rag_chunks: RAG 检索结果（Phase 8b）

    Returns:
        组装并裁剪后的 ContextPackage
    """
    # Phase 4: 动态预算调整
    budget_tokens = _dynamic_budget(chapter_goal.chapter_number, budget_tokens)

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

    # Phase 7: 过滤 human marks
    hm_config = mode_profile.human_memory
    filtered_marks: list[HumanMark] = []
    if human_marks:
        # 078: 时间窗口过滤 — 只保留最近 N 章写入的 + priority=10 的不受窗口限制
        window_start = chapter_goal.chapter_number - hm_config.chapter_window
        filtered_marks = [
            m for m in human_marks
            if m.priority >= hm_config.priority_threshold
            and (
                m.priority >= 10  # 最高优先级始终保留
                or (m.created_at_chapter or 0) >= window_start
            )
        ]
        filtered_marks = filtered_marks[: hm_config.max_marks_in_context]

    # 构建各分区
    hard_constraints = _build_hard_constraints(
        chapter_goal,
        genre_profile,
        project,
        filtered_marks,
        chapter_number=chapter_goal.chapter_number,
    )
    # 080: 按 arc 出场窗口过滤角色
    arc_boundaries = getattr(project, "arc_boundaries", None) or []
    character_snapshots = _build_character_snapshots(
        characters,
        character_states,
        recent_summaries=recent_summaries,
        arc_boundaries=arc_boundaries,
        current_chapter=chapter_goal.chapter_number,
        character_focus=character_focus,
        last_appeared_chapters=last_appeared_chapters,
    )
    recent_plot = _build_recent_plot(
        recent_summaries, last_chapter_ending, recent_plot_threads
    )
    recent_chapters = [s.chapter_number for s in recent_summaries]

    # Task 110c: 按章节阶段获取动态硬上限
    _dyn_caps = _dynamic_max_for_chapter(chapter_goal.chapter_number)

    # 077a + Task 110c: setting_snapshots 去重 + Top-N 入站过滤（动态上限）
    if setting_snapshots:
        seen: dict[str, NewSetting] = {}
        for s in setting_snapshots:
            key = s.setting_key or s.setting_name
            seen[key] = s
        deduped = list(seen.values())
        critical: list[NewSetting] = []
        non_critical: list[NewSetting] = []
        for s in deduped:
            if _is_setting_critical(s, chapter_goal):
                critical.append(s)
            else:
                non_critical.append(s)
        _max_setting_input = _dyn_caps["max_setting_input"]
        if len(non_critical) > _max_setting_input:
            non_critical = non_critical[-_max_setting_input:]
        limited = sorted(critical + non_critical, key=lambda s: s.chapter_number)
        logger.info(
            "context_manager.setting_input_filter",
            before=len(setting_snapshots),
            after=len(limited),
            critical=len(critical),
            max_setting_input=_max_setting_input,
        )
        setting_snapshots = limited

    soft_refs = _build_soft_references(
        setting_snapshots,
        current_chapter=chapter_goal.chapter_number,
        recent_chapters=recent_chapters,
        chapter_goal=chapter_goal,
    )
    # Task 110c: soft_references 按 chapter_goal 关键词过滤
    if soft_refs and chapter_goal.target_events:
        keywords = _extract_keywords(chapter_goal)
        if keywords:
            filtered_refs: list[SoftReference] = []
            for ref in soft_refs:
                if ref.is_critical:
                    filtered_refs.append(ref)
                    continue
                # 检查 content 中是否包含任一关键词
                content_lower = ref.content.lower()
                if any(kw.lower() in content_lower for kw in keywords):
                    filtered_refs.append(ref)
            logger.info(
                "context_manager.soft_ref_keyword_filter",
                before=len(soft_refs),
                after=len(filtered_refs),
                keywords=keywords,
            )
            soft_refs = filtered_refs

    # Phase 8b: 合并 RAG 检索结果到 soft_references
    if rag_chunks:
        rag_refs = _build_rag_soft_references(rag_chunks)
        soft_refs = rag_refs + soft_refs
        # 按 relevance_score 降序统一排序
        soft_refs.sort(key=lambda r: r.relevance_score, reverse=True)
    genre_rules = _build_genre_rules(genre_profile, project, chapter_goal)
    mode_rules = _build_mode_rules(mode_profile)

    # Task 098 + Task 110c: 按紧迫性排序伏笔，并过滤非相关项
    _foreshadowings = list(active_foreshadowings)
    if foreshadowing_due:
        _foreshadowings = _rank_foreshadowings(
            _foreshadowings,
            foreshadowing_due=foreshadowing_due,
            current_chapter=chapter_goal.chapter_number,
        )
    # Task 110c: 只保留 due/overdue + 最近 planted 的 N 个
    _max_fs = _dyn_caps["max_foreshadowing"]
    high_priority_fs = [f for f in _foreshadowings if f.status in ("due", "overdue")]
    rest_fs = [f for f in _foreshadowings if f.status not in ("due", "overdue")]
    # 保留所有 due/overdue + 最近 planted 的补充到上限
    keep_rest = min(max(0, _max_fs - len(high_priority_fs)), len(rest_fs))
    _foreshadowings = high_priority_fs + rest_fs[:keep_rest]

    ctx = ContextPackage(
        chapter_goal=chapter_goal,
        creative_brief=creative_brief,
        mode_profile=mode_profile,
        hard_constraints=hard_constraints,
        character_states=character_snapshots,
        recent_plot=recent_plot,
        foreshadowing=_foreshadowings,
        soft_references=soft_refs,
        genre_rules=genre_rules,
        mode_rules=mode_rules,
        # Phase 4 新增
        arc_context=arc_context,
        volume_context=volume_context,
        permanent_scenes=list(permanent_scenes or []),
        open_threads=list(open_threads or []),
        # Phase 7 新增
        human_marks=filtered_marks,
        # Task 074: 对话风格卡
        dialogue_style_cards=list(dialogue_style_cards or []),
        # 080: 监控字段
        character_states_total=len(character_states),
        # Task 138h: 强制连续性约束
        mandatory_references=list(mandatory_references or []),
    )

    # Phase 5: 注入风格样本（如果提供）
    if style_samples:
        from songyan.agents.style_mimicry_engine import StyleMimicryEngine

        engine = StyleMimicryEngine()
        ctx = engine.inject_multiple(style_samples, ctx)

    # Task 100c + Task 110c: 计算动态硬上限（章节阶段优先）
    _dyn_max_char = _dyn_caps["max_character_states"]
    _dyn_max_soft = _dynamic_max_soft_refs(len(setting_snapshots))

    # Task 098 + Task 110c: Token 预算裁剪（集成 narrative_fullness + focal_distance）
    pruner = BudgetPruner()
    ctx = pruner.prune(
        ctx,
        budget_tokens,
        narrative_fullness=narrative_fullness,
        focal_distance=focal_distance,
        max_soft_refs=_dyn_max_soft,
        max_character_states=_dyn_max_char,
        chapter_number=chapter_goal.chapter_number,
    )

    # Task 100c: 客观 narrative_fullness 计算
    obj_fullness = _calculate_objective_fullness(narrative_fullness, ctx.budget_used)
    final_focal = focal_distance
    if obj_fullness >= 0.9:
        # 强制 close 焦段以压缩上下文
        final_focal = "close"
    if obj_fullness > narrative_fullness or final_focal != focal_distance:
        # 需要重新 prune
        ctx = pruner.prune(
            ctx,
            budget_tokens,
            narrative_fullness=obj_fullness,
            focal_distance=final_focal,
            max_soft_refs=_dyn_max_soft,
            max_character_states=_dyn_max_char,
            chapter_number=chapter_goal.chapter_number,
        )

    # Task 100c: 记录 context_pressure 指标
    # Task 104: 增加 context_emergency 标记
    ctx.context_pressure = {
        "token_budget": round(ctx.budget_used, 4),
        "narrative_fullness_llm": round(narrative_fullness, 4),
        "narrative_fullness_objective": round(obj_fullness, 4),
        "focal_distance": final_focal,
        "fullness_factor": round(pruner._dynamic_fullness_factor(obj_fullness), 4),
        "max_character_states": _dyn_max_char,
        "max_soft_refs": _dyn_max_soft,
        "context_emergency": ctx.context_emergency,
    }

    logger.info(
        "context_manager.assemble_done",
        chapter_number=chapter_goal.chapter_number,
        estimated_tokens=ctx.estimated_tokens,
        budget_used=ctx.budget_used,
        narrative_fullness=narrative_fullness,
        narrative_fullness_objective=obj_fullness,
        focal_distance=final_focal,
    )
    return ctx
