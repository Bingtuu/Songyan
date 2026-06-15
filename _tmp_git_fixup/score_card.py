"""Unified scoring models — Task 106: 5-dimension score card."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    """单个维度的评分结果."""

    score: float = 0.0
    """维度得分 0.0~1.0；-1.0 表示未评估."""

    details: dict[str, float] = Field(default_factory=dict)
    """维度内部子指标，用于扩展（不新增维度）."""


class ScoreFlags(BaseModel):
    """评分标志 — 1/0 布尔，用于快速决策."""

    length_ok: bool = True
    budget_ok: bool = True
    coherence_critical: bool = False
    coherence_major: bool = False
    momentum_present: bool = True
    readability_ok: bool = True

    @property
    def has_blocking_issue(self) -> bool:
        """是否存在阻塞级问题（critical 或 budget 超标）."""
        return self.coherence_critical or not self.budget_ok

    @property
    def needs_revision(self) -> bool:
        """是否需要自动修订."""
        return self.coherence_critical or self.coherence_major


class ChapterScoreCard(BaseModel):
    """章节综合评分卡 — 五维固定结构.

    后续扩展只增加 dimension_details 中的子指标，不新增第 6 个维度。
    """

    version_id: str = ""
    """关联的章节版本 ID."""

    # 五维评分（固定不变）
    length: DimensionScore = Field(default_factory=DimensionScore)
    budget: DimensionScore = Field(default_factory=DimensionScore)
    coherence: DimensionScore = Field(default_factory=DimensionScore)
    momentum: DimensionScore = Field(default_factory=DimensionScore)
    readability: DimensionScore = Field(default_factory=DimensionScore)

    flags: ScoreFlags = Field(default_factory=ScoreFlags)

    overall_score: float = 0.0
    """加权总分 0.0~1.0."""

    @property
    def dimension_scores(self) -> dict[str, float]:
        """返回维度名 -> score 的映射（排除未评估维度）."""
        result: dict[str, float] = {}
        for name in ("length", "budget", "coherence", "momentum", "readability"):
            dim: DimensionScore = getattr(self, name)
            if dim.score >= 0.0:
                result[name] = dim.score
        return result
