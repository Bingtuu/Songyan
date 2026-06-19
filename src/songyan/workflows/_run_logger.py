"""单章运行日志收集与写入 — Task 058a 监控基础设施.

在 phase2_graph 的 _run_single_chapter 完成后调用，
从数据库查询指标并写入 JSONL，不阻塞主流程。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import structlog

from songyan.db.repository import ChapterVersionRepository
from songyan.db.review_repo import ReviewReportRepository
from songyan.models import ChapterRunLog
from songyan.workflows._helpers import new_id

logger = structlog.get_logger(__name__)

_LOGS_DIR = Path("logs/chapter_runs")


def _ensure_logs_dir() -> None:
    """确保日志目录存在."""
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _compute_rule_score(rule_audit) -> float:
    """从 RuleAuditResult 计算 0-1 质量分."""
    if rule_audit is None:
        return 0.0
    penalty = 0.0
    penalty += min(rule_audit.ai_tell_count * 0.05, 0.3)
    penalty += min(rule_audit.fatigue_word_count * 0.02, 0.2)
    if not rule_audit.has_opening_hook:
        penalty += 0.1
    if not rule_audit.has_ending_hook:
        penalty += 0.05
    return max(0.0, round(1.0 - penalty, 2))


async def _query_version_metrics(version_id: str) -> dict:
    """查询版本基础指标."""
    version = await ChapterVersionRepository().get(version_id)
    if version is None:
        return {"word_count": 0}
    return {"word_count": version.word_count}


async def _query_review_metrics(version_id: str) -> dict:
    """查询审查指标."""
    report = await ReviewReportRepository().get_by_version(version_id)
    if report is None:
        return {
            "rule_violations": 0,
            "rule_audit_score": 0.0,
            "llm_audit_issues": 0,
            "llm_audit_critical": 0,
        }

    llm_issues = report.llm_audit.issues if report.llm_audit else []
    llm_critical = sum(1 for i in llm_issues if i.severity == "critical")

    return {
        "rule_violations": report.ai_tell_count + report.fatigue_word_count,
        "rule_audit_score": _compute_rule_score(report.rule_audit),
        "llm_audit_issues": len(llm_issues),
        "llm_audit_critical": llm_critical,
    }


async def _query_context_metrics(version_id: str) -> dict:
    """从版本链回溯 writer 写入的上下文指标."""
    chain = await ChapterVersionRepository().get_chain(version_id)
    for version in reversed(chain):
        metadata = version.generation_metadata or {}
        snapshot = metadata.get("context_snapshot") or {}
        context_pressure = metadata.get("context_pressure") or {}
        if snapshot or context_pressure:
            return {
                "budget_used": snapshot.get("budget_used"),
                "character_states_loaded": snapshot.get("character_states_loaded"),
                "soft_refs_loaded": snapshot.get("soft_refs_loaded"),
                "context_emergency": snapshot.get("context_emergency", False),
                "context_pressure": context_pressure,
            }
    return {}


async def collect_chapter_metrics(
    project_id: str,
    chapter_number: int,
    final_version_id: str | None,
) -> dict:
    """收集单章指标 — 从数据库查询.

    Returns:
        dict 包含 word_count, rule_violations, rule_audit_score,
        llm_audit_issues, llm_audit_critical
    """
    metrics: dict = {}
    if final_version_id:
        version_metrics = await _query_version_metrics(final_version_id)
        review_metrics = await _query_review_metrics(final_version_id)
        context_metrics = await _query_context_metrics(final_version_id)
        metrics.update(version_metrics)
        metrics.update(review_metrics)
        metrics["_context_metrics"] = context_metrics
    return metrics


def build_chapter_run_log(
    *,
    run_id: str | None,
    project_id: str,
    chapter_number: int,
    started_at: datetime,
    finished_at: datetime,
    success: bool,
    error: str | None = None,
    error_stage: str | None = None,
    final_state: dict | None = None,
    metrics: dict | None = None,
    continuity_health_score: float | None = None,
    duration_sec: float = 0.0,
) -> ChapterRunLog:
    """构建 ChapterRunLog.

    Args:
        final_state: LangGraph 最终 state（用于提取 revision_rounds,
                     content_preservation_ratio, settlement_needs_human_review）
        metrics: 从数据库查询的指标
    """
    state = final_state or {}
    m = metrics or {}

    # Task 105: 提取 V5.0 上下文指标
    _ctx_metrics = state.get("_context_metrics") or m.get("_context_metrics", {})
    summary_id = state.get("summary_id")

    # Task 106: 提取 score_card（含 details 子指标）
    _score_card_raw = state.get("_score_card")
    _score_card: dict = {}
    if isinstance(_score_card_raw, dict):
        _allowed_keys = (
            "overall_score",
            "length",
            "budget",
            "coherence",
            "momentum",
            "readability",
            "flags",
        )
        _score_card = {
            k: v for k, v in _score_card_raw.items() if k in _allowed_keys
        }

    return ChapterRunLog(
        log_id=new_id("log"),
        run_id=run_id,
        project_id=project_id,
        chapter_number=chapter_number,
        started_at=started_at,
        finished_at=finished_at,
        success=success,
        error=error,
        error_stage=error_stage,
        word_count=m.get("word_count", 0),
        rule_violations=m.get("rule_violations", 0),
        rule_audit_score=m.get("rule_audit_score", 0.0),
        llm_audit_issues=m.get("llm_audit_issues", 0),
        llm_audit_critical=m.get("llm_audit_critical", 0),
        revision_rounds=state.get("_total_revision_count", state.get("revision_round", 0)),
        content_preservation_ratio=state.get("_content_preservation_ratio"),
        continuity_health_score=continuity_health_score,
        settlement_success=not state.get("_settlement_needs_human_review", False),
        settlement_needs_human_review=state.get("_settlement_needs_human_review", False),
        summary_id=summary_id,
        summary_success=summary_id is not None,
        budget_used=_ctx_metrics.get("budget_used"),
        character_states_loaded=_ctx_metrics.get("character_states_loaded"),
        soft_refs_loaded=_ctx_metrics.get("soft_refs_loaded"),
        context_emergency=_ctx_metrics.get("context_emergency", False),
        context_pressure=_ctx_metrics.get("context_pressure", {}),
        quality_gate_passed=state.get("_quality_gate_passed", False),
        score_card=_score_card,
        convergence_failed=state.get("_convergence_failed", False),
        skip_settlement=state.get("_skip_settlement", False),
        duration_sec=round(duration_sec, 2),
    )


def write_run_log(log: ChapterRunLog, run_id: str | None = None) -> str:
    """将 ChapterRunLog 追加写入 JSONL.

    Returns:
        写入的文件路径
    """
    _ensure_logs_dir()
    file_run_id = run_id or log.run_id or "unknown"
    filepath = _LOGS_DIR / f"{file_run_id}.jsonl"

    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(log.to_jsonl() + "\n")
    except OSError as exc:
        logger.warning(
            "run_logger.write_failed",
            filepath=str(filepath),
            error=str(exc),
        )
    return str(filepath)


async def log_chapter_run(
    *,
    run_id: str | None,
    project_id: str,
    chapter_number: int,
    started_at: datetime,
    finished_at: datetime,
    success: bool,
    error: str | None = None,
    error_stage: str | None = None,
    final_state: dict | None = None,
    final_version_id: str | None = None,
    continuity_health_score: float | None = None,
    duration_sec: float = 0.0,
) -> ChapterRunLog:
    """一站式单章运行日志记录.

    先收集指标，再构建日志，最后写入 JSONL。
    所有数据库查询在本函数内完成，调用方可 await 但不阻塞主线逻辑。
    """
    # 收集数据库指标
    metrics = await collect_chapter_metrics(
        project_id=project_id,
        chapter_number=chapter_number,
        final_version_id=final_version_id,
    )

    log = build_chapter_run_log(
        run_id=run_id,
        project_id=project_id,
        chapter_number=chapter_number,
        started_at=started_at,
        finished_at=finished_at,
        success=success,
        error=error,
        error_stage=error_stage,
        final_state=final_state,
        metrics=metrics,
        continuity_health_score=continuity_health_score,
        duration_sec=duration_sec,
    )

    write_run_log(log, run_id=run_id)
    logger.info(
        "run_logger.chapter_logged",
        log_id=log.log_id,
        run_id=log.run_id,
        chapter_number=chapter_number,
        success=success,
        word_count=log.word_count,
        duration_sec=log.duration_sec,
    )
    return log

