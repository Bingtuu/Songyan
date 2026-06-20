"""Chapter run log models — per-chapter execution metrics."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChapterRunLog(BaseModel):
    """单章运行日志 — 每章运行完成后记录一次.

    由 phase2_graph 的 _run_single_chapter 在成功/失败后统一写入，
    指标从数据库 + LangGraph state 收集，不阻塞主流程。
    """

    log_id: str
    run_id: str | None = None
    project_id: str
    chapter_number: int

    # 时间
    started_at: datetime
    finished_at: datetime

    # 结果
    success: bool
    error: str | None = None
    error_stage: str | None = None  # 失败发生的阶段，如 "settlement" | "revision" | "writing"

    # 质量指标（从数据库查询）
    word_count: int = 0
    rule_violations: int = 0  # ai_tell_count + fatigue_word_count
    rule_audit_score: float = 0.0  # 0-1，从 RuleAuditResult 计算
    llm_audit_issues: int = 0
    llm_audit_critical: int = 0
    revision_rounds: int = 0
    content_preservation_ratio: float | None = None  # 修订后内容保留比例

    # 连续性（每3章运行一次，可能为 None）
    continuity_health_score: float | None = None

    # Settlement 状态
    settlement_success: bool = True
    settlement_needs_human_review: bool = False
    summary_id: str | None = None
    summary_success: bool | None = None

    # V5.0 Context Diet 2.0 指标（Task 105）
    budget_used: float | None = None
    character_states_loaded: int | None = None
    soft_refs_loaded: int | None = None
    context_emergency: bool = False
    budget_used_before_emergency: float | None = None
    context_pressure: dict = Field(default_factory=dict)
    quality_gate_passed: bool | None = None

    # Task 106: 统一评分体系
    score_card: dict = Field(default_factory=dict)

    # Task 107: 收敛护栏
    convergence_failed: bool = False
    skip_settlement: bool = False

    # 资源
    duration_sec: float = 0.0

    # 指标采集版本号，用于区分字段词义变化（"版本不支持" vs "采集失败"）
    metrics_version: str = Field(default="v5.0", alias="_metrics_version")

    def to_jsonl(self) -> str:
        """序列化为单行 JSON（用于 JSONL 写入）."""
        return self.model_dump_json(by_alias=True)
