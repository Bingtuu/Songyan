"""ScoreAggregator — Task 106: 五维评分聚合器.

将 RuleAuditor + LLMAuditor + LiteraryAuditor + 上下文指标
聚合为统一的 ChapterScoreCard。
"""

from __future__ import annotations

import structlog

from songyan.models import (
    ChapterScoreCard,
    DimensionScore,
    LiteraryAuditResult,
    LLMAuditResult,
    ReviewCategory,
    RuleAuditResult,
    ScoreFlags,
)

logger = structlog.get_logger(__name__)

# 五维权重（固定）
_DIMENSION_WEIGHTS: dict[str, float] = {
    "length": 0.15,
    "budget": 0.10,
    "coherence": 0.30,
    "momentum": 0.20,
    "readability": 0.25,
}

# consistency 类 issue 的 category
_COHERENCE_CATEGORIES: set[str] = {
    ReviewCategory.WORLD_CONSISTENCY,
    ReviewCategory.CHARACTER_BEHAVIOR,
    ReviewCategory.TIMELINE,
    ReviewCategory.NEW_SETTING_UNREGISTERED,
}


def _score_length(rule_result: RuleAuditResult) -> tuple[float, dict[str, float]]:
    """长度合规评分.

    - ratio in [0.90, 1.10] -> 1.0
    - ratio in [0.80, 0.90) or (1.10, 1.20] -> 线性下降
    - ratio in [0.50, 0.80) or (1.20, 1.50] -> 继续线性下降
    - ratio < 0.50 or > 1.50 -> 0.0
    """
    ratio = rule_result.word_count_ratio
    if ratio <= 0.0:
        ratio = (
            rule_result.word_count / rule_result.word_count_target
            if rule_result.word_count_target > 0
            else 1.0
        )

    details = {"word_count_ratio": round(ratio, 3)}

    if 0.90 <= ratio <= 1.10:
        return 1.0, details
    if 0.80 <= ratio < 0.90:
        return 1.0 - (0.90 - ratio) / 0.10 * 0.4, details
    if 1.10 < ratio <= 1.20:
        return 1.0 - (ratio - 1.10) / 0.10 * 0.4, details
    if 0.50 <= ratio < 0.80:
        return 0.6 - (0.80 - ratio) / 0.30 * 0.6, details
    if 1.20 < ratio <= 1.50:
        return 0.6 - (ratio - 1.20) / 0.30 * 0.6, details
    return 0.0, details


def _score_budget(budget_used: float | None) -> tuple[float, dict[str, float]]:
    """Token 成本评分.

    - budget_used <= 0.80 -> 1.0
    - 0.80 ~ 1.00 -> 线性下降到 0.0
    - > 1.00 -> 0.0

    评分用于排序和总分加权；硬门禁以 budget_used <= 1.0 为准。
    """
    bu = budget_used if budget_used is not None else 0.0
    details = {"budget_used": round(bu, 3)}
    if bu <= 0.80:
        return 1.0, details
    if bu <= 1.00:
        return 1.0 - (bu - 0.80) / 0.20, details
    return 0.0, details


def _score_coherence(llm_result: LLMAuditResult) -> tuple[float, dict[str, float], bool, bool]:
    """一致性+逻辑评分.

    基于 consistency 类 issues 的数量和 severity 扣分。
    Returns: (score, details, has_critical, has_major)
    """
    consistency_issues = [
        i for i in llm_result.issues
        if i.category in _COHERENCE_CATEGORIES
    ]

    critical = sum(1 for i in consistency_issues if i.severity == "critical")
    major = sum(1 for i in consistency_issues if i.severity == "major")
    minor = sum(1 for i in consistency_issues if i.severity == "minor")

    score = 1.0 - critical * 0.40 - major * 0.15 - minor * 0.10
    score = max(0.0, min(1.0, score))

    details = {
        "consistency_issues": float(len(consistency_issues)),
        "critical": float(critical),
        "major": float(major),
        "minor": float(minor),
    }
    return score, details, critical > 0, major >= 2


def _score_momentum(rule_result: RuleAuditResult) -> tuple[float, dict[str, float]]:
    """推动力+爆点评分.

    - 无 punch_points 预期 -> -1.0（未评估）
    - 基于 hooks + punch_density + emotion_switch
    """
    punch = rule_result.punch_check
    if punch.expected_punch_count <= 0:
        return -1.0, {"evaluated": 0.0}

    score = 0.0
    if rule_result.has_opening_hook:
        score += 0.2
    if rule_result.has_ending_hook:
        score += 0.3
    if punch.punch_density_ok:
        score += 0.3
    if punch.emotion_switch_ok:
        score += 0.2

    details = {
        "evaluated": 1.0,
        "opening_hook": 1.0 if rule_result.has_opening_hook else 0.0,
        "ending_hook": 1.0 if rule_result.has_ending_hook else 0.0,
        "punch_density_ok": 1.0 if punch.punch_density_ok else 0.0,
        "emotion_switch_ok": 1.0 if punch.emotion_switch_ok else 0.0,
    }
    return score, details


def _score_readability(rule_result: RuleAuditResult) -> tuple[float, dict[str, float]]:
    """可读性评分.

    基于 AI腔、疲劳词、段落节奏扣分。
    """
    base = 1.0
    if rule_result.ai_tell_count > 0:
        base -= min(rule_result.ai_tell_count * 0.15, 0.5)
    if rule_result.fatigue_word_count > 0:
        base -= min(rule_result.fatigue_word_count * 0.08, 0.3)
    if rule_result.paragraph_rhythm_score < 5.0:
        base -= (5.0 - rule_result.paragraph_rhythm_score) * 0.05

    score = max(0.0, min(1.0, base))
    details = {
        "ai_tell_count": float(rule_result.ai_tell_count),
        "fatigue_word_count": float(rule_result.fatigue_word_count),
        "paragraph_rhythm_score": rule_result.paragraph_rhythm_score,
    }
    return score, details


def _compute_overall(card: ChapterScoreCard) -> float:
    """计算加权总分，未评估维度排除并重新归一化权重."""
    total_weight = 0.0
    weighted_sum = 0.0
    for dim_name, weight in _DIMENSION_WEIGHTS.items():
        dim: DimensionScore = getattr(card, dim_name)
        if dim.score >= 0.0:
            weighted_sum += dim.score * weight
            total_weight += weight
    if total_weight <= 0.0:
        return 0.0
    return round(weighted_sum / total_weight, 4)


def _quality_ramp_thresholds(
    chapter_number: int, quality_ramp_chapters: int = 10
) -> tuple[float, float]:
    """返回质量爬坡阈值 (readability_threshold, momentum_threshold).

    Task 128b: Ch1–quality_ramp_chapters 使用更宽松阈值，帮助新项目开局期
    在约束真空下逐步爬坡；Ch11+ 恢复严格阈值。
    """
    if 1 <= chapter_number <= quality_ramp_chapters:
        return 0.3, 0.3
    return 0.6, 0.5


class ScoreAggregator:
    """评分聚合器 — 从 Auditor 结果产出 ChapterScoreCard."""

    @staticmethod
    def aggregate(
        version_id: str,
        rule_result: RuleAuditResult,
        llm_result: LLMAuditResult,
        budget_used: float | None = None,
        literary_result: LiteraryAuditResult | None = None,
        chapter_number: int = 0,
        quality_ramp_chapters: int = 10,
    ) -> ChapterScoreCard:
        """聚合评分.

        Args:
            version_id: 章节版本 ID
            rule_result: RuleAuditor 结果
            llm_result: LLMAuditor 结果
            budget_used: 上下文 budget_used（从 ContextPackage 获取）
            literary_result: 可选的 LiteraryAuditor 结果（当前不影响分数，预留扩展）
            chapter_number: 章节号，用于质量爬坡阈值
            quality_ramp_chapters: 质量爬坡窗口章节数
        """
        # 1. 长度
        length_score, length_details = _score_length(rule_result)
        length_score_rounded = round(length_score, 4)

        # 2. Budget
        budget_score, budget_details = _score_budget(budget_used)

        # 3. 一致性
        coherence_score, coherence_details, has_critical, has_major = _score_coherence(llm_result)
        major_count = coherence_details.get("major", 0)

        # 4. 推动力
        momentum_score, momentum_details = _score_momentum(rule_result)

        # 5. 可读性
        readability_score, readability_details = _score_readability(rule_result)

        # 预留：literary_result 的子指标可放入 details，但不影响主 score
        if literary_result is not None:
            readability_details["literary_quality_score"] = literary_result.literary_quality_score

        # Task 128b: 开局期质量爬坡阈值
        readability_threshold, momentum_threshold = _quality_ramp_thresholds(
            chapter_number, quality_ramp_chapters
        )

        card = ChapterScoreCard(
            version_id=version_id,
            length=DimensionScore(
                score=length_score_rounded, details=length_details
            ),
            budget=DimensionScore(
                score=round(budget_score, 4), details=budget_details
            ),
            coherence=DimensionScore(
                score=round(coherence_score, 4), details=coherence_details
            ),
            momentum=DimensionScore(
                score=round(momentum_score, 4), details=momentum_details
            ),
            readability=DimensionScore(
                score=round(readability_score, 4), details=readability_details
            ),
            flags=ScoreFlags(
                length_ok=length_score_rounded >= 0.5,
                budget_ok=(budget_used is None or budget_used <= 1.0),
                coherence_critical=has_critical,
                coherence_major=(
                    has_critical
                    or has_major
                    or (coherence_score < 0.6 and major_count > 0)
                ),
                momentum_present=(
                    momentum_score >= momentum_threshold or momentum_score == -1.0
                ),
                readability_ok=readability_score >= readability_threshold,
            ),
        )
        card.overall_score = _compute_overall(card)

        logger.info(
            "score_aggregator.aggregated",
            version_id=version_id,
            overall=card.overall_score,
            length=card.length.score,
            budget=card.budget.score,
            coherence=card.coherence.score,
            momentum=card.momentum.score,
            readability=card.readability.score,
        )
        return card
