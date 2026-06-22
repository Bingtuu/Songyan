"""Phase 2 多章编排层 — 顺序调度 Phase1Graph，自动跨章状态传递."""

from __future__ import annotations

import time
from datetime import datetime
from sqlite3 import Row
from typing import Any

import structlog

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.db.connection import get_db
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.exceptions import AutoHaltException
from songyan.models import ProjectRunResult, ProjectRunState
from songyan.workflows._helpers import new_id
from songyan.workflows._run_logger import log_chapter_run
from songyan.workflows.phase1_graph import (
    reset_checkpointer,
    resume_human_confirm,
    run_chapter_pipeline,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# 内部辅助函数
# =============================================================================


async def _get_previous_summary(project_id: str, chapter_number: int) -> str:
    """获取上一章的 plot_summary（用于注入下一章的 previous_summary）."""
    if chapter_number <= 1:
        return ""
    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            """SELECT plot_summary FROM summaries
            WHERE project_id = ? AND chapter_number = ?
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, chapter_number - 1),
        )
        row = await cursor.fetchone()
    text = row["plot_summary"] if row else ""
    # V3.1 Layer 2: 防止长尺度 previous_summary 膨胀（Ch49 已达 244 字符）
    max_previous_summary_len = 120
    if len(text) > max_previous_summary_len:
        text = text[:max_previous_summary_len] + "..."
    return text


async def _save_run_state(run_state: ProjectRunState) -> None:
    """保存或更新运行状态."""
    repo = ProjectRunRepository()
    existing = await repo.get(run_state.run_id)
    if existing is None:
        await repo.create(run_state)
    else:
        await repo.update(run_state)


async def _persist_run_progress(
    run_state: ProjectRunState,
    completed: list[int],
    failed: list[int],
    persisted_summary: str,
    *,
    status: str | None = None,
) -> None:
    """持久化当前批量运行进度，避免长跑中途异常丢失恢复信息."""
    run_state.completed_chapters = completed
    run_state.failed_chapters = failed
    run_state.accumulated_summary = persisted_summary
    if status is not None:
        run_state.status = status
    await _save_run_state(run_state)


async def _pause_run_for_auto_halt(
    run_state: ProjectRunState,
    completed: list[int],
    failed: list[int],
    persisted_summary: str,
) -> None:
    """自动熔断前持久化项目级运行状态，保留已完成章节."""
    await _persist_run_progress(
        run_state,
        completed,
        failed,
        persisted_summary,
        status="paused",
    )


def _format_chapter_summary(chapter_number: int, summary_text: str) -> str:
    """格式化单章摘要条目，供运行结果和轻量持久化状态复用."""
    return f"第{chapter_number}章：{summary_text}"


def _is_terminal_success_state(state: dict[str, Any]) -> bool:
    """判断章节是否已完成可结算终态，防止前置非致命错误污染结果."""
    return (
        state.get("status") == "done"
        and state.get("current_version_id") is not None
        and state.get("settlement_id") is not None
        and state.get("summary_id") is not None
    )


def _has_context_emergency_degradation(recent_results: list[dict[str, Any]]) -> bool:
    """判断连续 ContextEmergency 是否伴随真实降级，避免成功降级被误熔断."""
    for result in recent_results:
        if not result.get("success", False):
            return True
        if result.get("quality_gate_passed") is False:
            return True
        if result.get("settlement_success") is False:
            return True
        if result.get("summary_success") is False:
            return True
    return False


def _append_recent_result(
    recent_results: list[dict[str, Any]],
    chapter_number: int,
    chapter_result: dict[str, Any],
) -> None:
    """记录最近章节指标，供项目级自动熔断使用."""
    recent_results.append({
        "chapter_number": chapter_number,
        "success": chapter_result["success"],
        "quality_gate_passed": chapter_result.get("quality_gate_passed", False),
        "context_emergency": chapter_result.get("context_emergency", False),
        "settlement_success": chapter_result.get("settlement_success"),
        "summary_success": chapter_result.get("summary_success"),
    })
    if len(recent_results) > 3:
        recent_results.pop(0)


async def _check_auto_halt_window(
    run_state: ProjectRunState,
    recent_results: list[dict[str, Any]],
    completed: list[int],
    failed: list[int],
    persisted_summary: str,
    *,
    run_id: str,
    chapter_number: int,
) -> None:
    """检查项目级自动熔断窗口."""
    if len(recent_results) < 3:
        return

    # Task 105: 自动熔断检查（跳过 quality_gate_passed=None 的章节）
    _qg_known = [r for r in recent_results if r["quality_gate_passed"] is not None]
    _emergencies = sum(1 for r in recent_results if r["context_emergency"])
    if len(_qg_known) >= 3:
        _qg_fails = sum(1 for r in _qg_known if not r["quality_gate_passed"])
        if _qg_fails >= 3:
            _ch_start = _qg_known[0]["chapter_number"]
            await _pause_run_for_auto_halt(
                run_state,
                completed,
                failed,
                persisted_summary,
            )
            raise AutoHaltException(
                message=f"连续 3 章质量门未通过（Ch{_ch_start}-Ch{chapter_number}）",
                last_chapter=chapter_number,
                reason="quality_gate_fail_streak",
            )
    if _emergencies >= 3:
        _ch_start = recent_results[0]["chapter_number"]
        if _has_context_emergency_degradation(recent_results):
            await _pause_run_for_auto_halt(
                run_state,
                completed,
                failed,
                persisted_summary,
            )
            raise AutoHaltException(
                message=(
                    "连续 3 章触发 ContextEmergency 且伴随章节失败或质量异常"
                    f"（Ch{_ch_start}-Ch{chapter_number}）"
                ),
                last_chapter=chapter_number,
                reason="context_emergency_degraded_streak",
            )
        logger.warning(
            "project_pipeline.context_emergency_success_streak",
            run_id=run_id,
            chapter_start=_ch_start,
            chapter_end=chapter_number,
            message="连续 ContextEmergency 但章节均成功完成，记录 warning 并继续",
        )


# =============================================================================
# 公共 API
# =============================================================================


async def run_project_pipeline(
    project_id: str,
    chapter_range: tuple[int, int],
    mode_id: str = "webnovel",
    *,
    auto_confirm: bool = False,
    max_revision_rounds: int = 2,
    on_failure: str = "abort",  # "abort" | "retry"
    continuity_health_threshold: float = 7.0,
) -> ProjectRunResult:
    """运行多章流水线，逐章调用 Phase1Graph，自动传递上下文.

    Args:
        project_id: 项目唯一标识
        chapter_range: (start, end) 章节范围，如 (1, 3)
        mode_id: 创作模式 ID
        auto_confirm: 是否自动接受每章（跳过 human_confirm 中断）
        max_revision_rounds: 单章最大 revision 轮数（透传给 Phase1Graph）
        on_failure: 单章失败策略："abort" 终止整批，"retry" 重试 1 次
        continuity_health_threshold: 连续性健康分阈值，低于此值触发警告

    Returns:
        ProjectRunResult: 运行结果统计

    Raises:
        ValueError: chapter_range 非法 或 auto_confirm=False（批量模式不支持人工确认）
    """
    start_time = time.monotonic()
    start, end = chapter_range

    # ---- 参数校验 ----
    if start > end:
        raise ValueError(f"chapter_range start ({start}) must be <= end ({end})")
    if start < 1:
        raise ValueError(f"chapter_range start ({start}) must be >= 1")
    if not auto_confirm:
        raise ValueError(
            "auto_confirm=False is not supported in batch mode. "
            "Set auto_confirm=True to run chapters automatically."
        )

    run_id = new_id("run")
    run_state = ProjectRunState(
        run_id=run_id,
        project_id=project_id,
        chapter_range_start=start,
        chapter_range_end=end,
        current_chapter=start,
        status="running",
    )
    await _save_run_state(run_state)

    logger.info(
        "project_pipeline.start",
        run_id=run_id,
        project_id=project_id,
        chapter_range=chapter_range,
        mode_id=mode_id,
        auto_confirm=auto_confirm,
    )

    completed: list[int] = []
    failed: list[int] = []
    accumulated_summary_parts: list[str] = []
    persisted_summary = ""

    # Task 105: 熔断历史窗口（最近 3 章的指标）
    _recent_results: list[dict] = []

    # 重置检查指针，消除冷启动导致的首章 WAL 读一致性窗口问题
    await reset_checkpointer()

    for chapter_number in range(start, end + 1):
        run_state.current_chapter = chapter_number
        await _save_run_state(run_state)

        # 获取上一章 summary 作为当前章的 previous_summary
        previous_summary = await _get_previous_summary(project_id, chapter_number)

        logger.info(
            "project_pipeline.chapter_start",
            run_id=run_id,
            chapter_number=chapter_number,
            previous_summary_length=len(previous_summary),
        )

        # ---- 执行单章 ----
        chapter_result = await _run_single_chapter(
            project_id=project_id,
            chapter_number=chapter_number,
            mode_id=mode_id,
            previous_summary=previous_summary,
            auto_confirm=auto_confirm,
            on_failure=on_failure,
            continuity_health_threshold=continuity_health_threshold,
            run_id=run_id,
        )

        _append_recent_result(_recent_results, chapter_number, chapter_result)

        if chapter_result["success"]:
            completed.append(chapter_number)
            # 累加 summary
            summary_text = chapter_result.get("summary_text", "")
            if summary_text:
                persisted_summary = _format_chapter_summary(
                    chapter_number, summary_text
                )
                accumulated_summary_parts.append(persisted_summary)
            logger.info(
                "project_pipeline.chapter_success",
                run_id=run_id,
                chapter_number=chapter_number,
            )
            await _persist_run_progress(
                run_state,
                completed,
                failed,
                persisted_summary,
                status="running",
            )

        else:
            failed.append(chapter_number)
            logger.warning(
                "project_pipeline.chapter_failed",
                run_id=run_id,
                chapter_number=chapter_number,
                error=chapter_result.get("error"),
            )
            await _persist_run_progress(
                run_state,
                completed,
                failed,
                persisted_summary,
                status="running",
            )
            await _check_auto_halt_window(
                run_state,
                _recent_results,
                completed,
                failed,
                persisted_summary,
                run_id=run_id,
                chapter_number=chapter_number,
            )
            if on_failure == "abort":
                break
            # on_failure == "retry" 已在 _run_single_chapter 中处理，
            # 如果 retry 仍失败，则记录失败并继续（还是终止取决于策略）
            # 当前策略：retry 一次后仍失败则终止
            break

        await _check_auto_halt_window(
            run_state,
            _recent_results,
            completed,
            failed,
            persisted_summary,
            run_id=run_id,
            chapter_number=chapter_number,
        )

    # ---- 收尾 ----
    duration = time.monotonic() - start_time
    final_status = "completed" if not failed else ("partial" if completed else "failed")

    await _persist_run_progress(
        run_state,
        completed,
        failed,
        persisted_summary,
        status=final_status,
    )

    accumulated_summary = "\n\n".join(accumulated_summary_parts)
    result = ProjectRunResult(
        project_id=project_id,
        run_id=run_id,
        chapters_completed=completed,
        chapters_failed=failed,
        total_cost=0.0,  # TODO: Task 025 中接入精确成本追踪
        total_duration_sec=duration,
        final_status=final_status,
        accumulated_summary=accumulated_summary,
    )

    logger.info(
        "project_pipeline.end",
        run_id=run_id,
        final_status=final_status,
        completed=completed,
        failed=failed,
        duration_sec=duration,
    )
    return result


async def _run_single_chapter(
    project_id: str,
    chapter_number: int,
    mode_id: str,
    previous_summary: str,
    auto_confirm: bool,
    on_failure: str,
    max_revision_rounds: int = 2,
    continuity_health_threshold: float = 7.0,
    *,
    run_id: str | None = None,
) -> dict:
    """运行单章，含 auto_confirm 处理和失败重试.

    Returns:
        {
            "success": bool,
            "summary_text": str,
            "error": str | None,
            "final_state": dict | None,
            "final_version_id": str | None,
        }
    """
    started_at = datetime.now()
    chapter_start = time.monotonic()
    thread_id = new_id("thread")
    attempts = 0
    max_attempts = 2 if on_failure == "retry" else 1
    final_state: dict | None = None
    error_stage: str | None = None
    _stage: str = "init"  # 跟踪当前阶段，用于异常时 error_stage

    while attempts < max_attempts:
        attempts += 1
        try:
            _stage = "pipeline"  # 跟踪当前阶段
            state = await run_chapter_pipeline(
                project_id=project_id,
                chapter_number=chapter_number,
                mode_id=mode_id,
                thread_id=thread_id,
                previous_summary=previous_summary,
                max_revision_rounds=max_revision_rounds,
            )
            final_state = state

            # 处理 human_confirm 中断
            if "__interrupt__" in state:
                if auto_confirm:
                    _stage = "human_confirm"  # 跟踪当前阶段
                    state = await resume_human_confirm(thread_id, "accept")
                    final_state = state
                else:
                    error_stage = "human_confirm"
                    break

            # 检查最终状态。Task 121f: 若章节已经完成正文、settlement 与
            # summary，前置 CreativeDirector 等非致命解析错误只能作为诊断，
            # 不能污染最终章节成功判定。
            if _is_terminal_success_state(state):
                if state.get("error"):
                    logger.info(
                        "project_pipeline.stale_error_ignored_after_terminal_success",
                        chapter_number=chapter_number,
                        status=state.get("status"),
                        error=state.get("error"),
                    )
            elif state.get("error"):
                error_stage = state.get("status", "unknown")
                if attempts < max_attempts:
                    logger.info(
                        "project_pipeline.chapter_retry",
                        chapter_number=chapter_number,
                        attempt=attempts,
                        error=state["error"],
                    )
                    thread_id = new_id("thread")  # 新 thread 重试
                    continue
                break

            if state.get("status") != "done":
                error_stage = state.get("status", "unknown")
                if attempts < max_attempts:
                    logger.info(
                        "project_pipeline.chapter_retry_unexpected_status",
                        chapter_number=chapter_number,
                        attempt=attempts,
                        status=state.get("status"),
                    )
                    thread_id = new_id("thread")
                    continue
                break

            # 成功：尝试获取 summary
            # 防御性说明：即使 _skip_settlement=True 且 _convergence_failed=True，
            # 只要 status=="done" 就视为成功路径，不会进入失败分支。
            _stage = "summary_writer"  # 跟踪当前阶段
            summary_text = await _get_summary_text(project_id, chapter_number)
            duration_sec = time.monotonic() - chapter_start
            final_version_id = state.get("current_version_id")

            _stage = "continuity_audit"
            # ---- 每 3 章运行 ContinuityAuditor ----
            continuity_health_score: float | None = None
            if chapter_number % 3 == 0:
                try:
                    auditor = ContinuityAuditor()
                    report = await auditor.audit(
                        project_id=project_id,
                        up_to_chapter=chapter_number,
                    )
                    await auditor.write_constraints(report, version_id=final_version_id)
                    continuity_health_score = report.overall_health_score
                    if report.overall_health_score < continuity_health_threshold:
                        logger.warning(
                            "continuity.health_low",
                            run_id=run_id,
                            chapter_number=chapter_number,
                            score=report.overall_health_score,
                            threshold=continuity_health_threshold,
                            orphaned=len(report.orphaned_settings),
                            overdue=len(report.overdue_foreshadowings),
                        )
                except Exception as exc:
                    logger.warning(
                        "continuity.audit_failed",
                        run_id=run_id,
                        chapter_number=chapter_number,
                        error=str(exc),
                    )

            _stage = "run_logger"  # 跟踪当前阶段
            chapter_log = await log_chapter_run(
                run_id=run_id,
                project_id=project_id,
                chapter_number=chapter_number,
                started_at=started_at,
                finished_at=datetime.now(),
                success=True,
                final_state=final_state,
                final_version_id=final_version_id,
                continuity_health_score=continuity_health_score,
                duration_sec=duration_sec,
            )
            # Task 105: 透传上下文指标供外层熔断检查
            _ctx_metrics = final_state.get("_context_metrics", {}) if final_state else {}
            _qg_passed = final_state.get("_quality_gate_passed") if final_state else None
            logged_budget = getattr(chapter_log, "budget_used", None)
            logged_context_emergency = getattr(chapter_log, "context_emergency", None)
            logged_qg_passed = getattr(chapter_log, "quality_gate_passed", None)
            logged_settlement_success = getattr(chapter_log, "settlement_success", None)
            logged_summary_success = getattr(chapter_log, "summary_success", None)
            if not isinstance(logged_context_emergency, bool):
                logged_context_emergency = _ctx_metrics.get("context_emergency", False)
            if logged_qg_passed not in (True, False, None):
                logged_qg_passed = _qg_passed
            return {
                "success": True,
                "summary_text": summary_text,
                "error": None,
                "final_state": final_state,
                "final_version_id": final_version_id,
                "budget_used": logged_budget
                if logged_budget is not None
                else _ctx_metrics.get("budget_used"),
                "context_emergency": logged_context_emergency,
                "quality_gate_passed": logged_qg_passed,
                "settlement_success": logged_settlement_success,
                "summary_success": logged_summary_success,
            }

        except Exception:
            logger.exception("project_pipeline.chapter_exception", chapter_number=chapter_number)
            error_stage = error_stage or _stage or "exception"
            if attempts < max_attempts:
                thread_id = new_id("thread")
                continue
            final_state = final_state or {}
            break

    # 失败路径
    duration_sec = time.monotonic() - chapter_start
    _ctx_metrics = final_state.get("_context_metrics", {}) if final_state else {}
    _qg_passed = final_state.get("_quality_gate_passed") if final_state else False
    _settlement_success = final_state.get("settlement_id") is not None if final_state else False
    _summary_success = final_state.get("summary_id") is not None if final_state else False
    error_msg = (
        final_state.get("error")
        if final_state
        else "Max attempts exceeded"
    )
    await log_chapter_run(
        run_id=run_id,
        project_id=project_id,
        chapter_number=chapter_number,
        started_at=started_at,
        finished_at=datetime.now(),
        success=False,
        error=error_msg,
        error_stage=error_stage,
        final_state=final_state,
        final_version_id=final_state.get("current_version_id") if final_state else None,
        duration_sec=duration_sec,
    )
    return {
        "success": False,
        "summary_text": "",
        "error": error_msg,
        "final_state": final_state,
        "final_version_id": final_state.get("current_version_id") if final_state else None,
        "budget_used": _ctx_metrics.get("budget_used"),
        "context_emergency": _ctx_metrics.get("context_emergency", False),
        "quality_gate_passed": _qg_passed,
        "settlement_success": _settlement_success,
        "summary_success": _summary_success,
    }


async def _get_summary_text(project_id: str, chapter_number: int) -> str:
    """从 summaries 表读取指定章节的 plot_summary."""
    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            """SELECT plot_summary FROM summaries
            WHERE project_id = ? AND chapter_number = ?
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, chapter_number),
        )
        row = await cursor.fetchone()
    return row["plot_summary"] if row else ""
