"""Review and audit models — RuleAuditor + LLMAuditor + MergedReviewReport."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ReviewCategory(StrEnum):
    """LLMAuditor 审查维度 — 12 个维度."""

    # === 一致性维度（4 个）===
    WORLD_CONSISTENCY = "world_consistency"
    CHARACTER_BEHAVIOR = "character_behavior"
    TIMELINE = "timeline"
    NEW_SETTING_UNREGISTERED = "new_setting_unregistered"

    # === 叙事质量（3 个）===
    NARRATIVE_PACING = "narrative_pacing"
    NARRATIVE_HOOK = "narrative_hook"
    INFO_DUMP = "info_dump"

    # === 对话质量（2 个）===
    DIALOGUE_DISTINCTNESS = "dialogue_distinctness"
    DIALOGUE_SUBTEXT = "dialogue_subtext"

    # === 描写质量（2 个）===
    DESCRIPTION_SENSORY = "description_sensory"
    SHOW_DONT_TELL = "show_dont_tell"

    # === 题材专项（1 个）===
    GENRE_NUMERICAL = "genre_numerical"


class ReviewIssue(BaseModel):
    """审查问题 — critical/major 必须有 evidence_quote."""

    issue_id: str
    category: ReviewCategory
    severity: Literal["critical", "major", "minor", "info"]

    # 证据（必须有）
    evidence_quote: str
    evidence_location: str

    # 关联
    related_setting_id: str | None = None
    related_character_id: str | None = None

    # 问题说明
    issue_description: str
    expected: str | None = None
    actual: str | None = None

    # 修复建议
    suggested_fix: str | None = None
    fix_type: Literal["patch", "rewrite_scene", "confirm", "register_setting"] = "patch"

    # 置信度
    confidence: float = 1.0


class AiTellMatch(BaseModel):
    """AI 腔命中."""

    pattern: str
    matched_text: str
    location: str  # "第3段第2句"


class FatigueWordMatch(BaseModel):
    """疲劳词命中."""

    word: str
    count: int
    locations: list[str] = Field(default_factory=list)


class RuleAuditResult(BaseModel):
    """规则检测结果 — 全部由代码执行，不调用 LLM."""

    auditor_id: str = "rule_auditor"

    # AI 腔检测
    ai_tell_matches: list[AiTellMatch] = Field(default_factory=list)
    ai_tell_count: int = 0

    # 疲劳词检测
    fatigue_word_matches: list[FatigueWordMatch] = Field(default_factory=list)
    fatigue_word_count: int = 0

    # 首屏钩子
    has_opening_hook: bool = False

    # 章末钩子
    has_ending_hook: bool = False

    # 段落节奏
    paragraph_rhythm_score: float = 0.0  # 0-10
    rhythm_issues: list[str] = Field(default_factory=list)

    # 字数统计
    word_count: int = 0
    word_count_target: int = 3000
    word_count_ok: bool = True

    # 数值公式检测（玄幻）
    numerical_issues: list[str] = Field(default_factory=list)

    # 处理时长
    duration_ms: int = 0


class LLMAuditResult(BaseModel):
    """LLM 语义审查结果 — 需要调用 LLM."""

    auditor_id: str = "llm_auditor"
    issues: list[ReviewIssue] = Field(default_factory=list)

    # 各维度评分
    dimension_scores: dict[str, float] = Field(default_factory=dict)

    # 文学性维度
    cliche_risk_score: float = 0.0  # 套路化风险 0-10
    character_autonomy_score: float = 0.0  # 人物自治度 0-10
    conceptual_idling_score: float = 0.0  # 概念空转度 0-10

    summary: str = ""
    duration_ms: int = 0


class MergedReviewReport(BaseModel):
    """合并审查报告 — RuleAuditor + LLMAuditor 的统一输出."""

    chapter_version_id: str

    # RuleAuditor 结果
    rule_audit: RuleAuditResult | None = None

    # LLMAuditor 结果
    llm_audit: LLMAuditResult | None = None

    # 合并后的 issues（用于 RevisionHandler）
    issues: list[ReviewIssue] = Field(default_factory=list)

    # 关键指标
    overall_score: float = 0.0
    ai_tell_count: int = 0
    fatigue_word_count: int = 0
    has_opening_hook: bool = False
    has_ending_hook: bool = False

    # 各维度评分（合并）
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    summary: str = ""

    @property
    def has_critical(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)

    @property
    def has_major(self) -> bool:
        return any(i.severity == "major" for i in self.issues)

    @property
    def patchable_issues(self) -> list[ReviewIssue]:
        return [
            i
            for i in self.issues
            if i.severity in ("critical", "major") and i.fix_type == "patch"
        ]
