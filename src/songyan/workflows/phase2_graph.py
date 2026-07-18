"""Phase 2 多章编排层 — 顺序调度 Phase1Graph，自动跨章状态传递."""

from __future__ import annotations

import time
from datetime import datetime
from sqlite3 import OperationalError, Row
from typing import Any, cast

import structlog

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.agents.continuity_auditor.continuity_health import classify_report
from songyan.db.adaptive_halt_repo import AdaptiveHaltDecisionRepository
from songyan.db.connection import get_db
from songyan.db.genre_runtime_profile_repo import load_profile as _load_runtime_profile
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ChapterHeadRepository
from songyan.db.run_db_metrics_repo import RunDbMetricsRepository
from songyan.evals.adaptive_gate import (
    build_adaptive_gate_data_plane_report,
    refresh_adaptive_gate_signal_snapshots,
)
from songyan.evals.adaptive_halt import evaluate_adaptive_halt
from songyan.evals.db_maintenance_metrics import (
    check_t5_size_redline,
    collect_db_size_metrics,
    measure_continuity_scan_latency,
)
from songyan.exceptions import AutoHaltException, LLMBudgetExceededError, SongyanError
from songyan.models import (
    AdaptiveHaltDecision,
    AdaptiveHaltPolicy,
    GateConfig,
    ProjectRunResult,
    ProjectRunState,
)
from songyan.workflows._gates import (
    check_health_low_streak_gate,
    evaluate_all_gates,
)
from songyan.workflows._helpers import (
    ensure_protagonist_character,
    new_id,
)
from songyan.workflows._helpers import (
    load_project as _load_project_for_audit,
)
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


async def _get_previous_summary(
    project_id: str,
    chapter_number: int,
    *,
    latest_successful_chapter: int | None = None,
) -> str:
    """获取上一章的 plot_summary（用于注入下一章的 previous_summary）.

    失败隔离模式下，通过 latest_successful_chapter 回退到最近成功章的摘要。
    """
    if chapter_number <= 1:
        return ""
    source_chapter = (
        latest_successful_chapter
        if latest_successful_chapter is not None
        else chapter_number - 1
    )
    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            """SELECT plot_summary FROM summaries
            WHERE project_id = ? AND chapter_number = ?
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, source_chapter),
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


async def _upsert_quality_debt(run_id: str, project_id: str) -> None:
    """读取本 run 的 JSONL 日志聚合质量债并 upsert run_quality_debt（V6 Task 146，非阻塞）.

    质量债由整份 run 日志聚合而来，故本函数每次会全量重读日志。为避免 150 章长跑中
    每章重读造成的 O(n²)（#2 修复），调用方按周期（每 N 章）+ run 收尾各调用一次，
    而非逐章调用；被 kill 的 run 仍留有截至最近一次周期点的质量债汇总。
    """
    try:
        from json import JSONDecodeError

        from songyan.db.run_quality_debt_repo import RunQualityDebtRepository
        from songyan.evals.db_metrics import compute_quality_debt, quality_debt_row
        from songyan.evals.streaming_report import read_run_logs

        logs = read_run_logs(run_id)
        if not logs:
            return
        report = compute_quality_debt(logs)
        await RunQualityDebtRepository().upsert(
            quality_debt_row(run_id, project_id, report)
        )
    except (
        RuntimeError,
        OSError,
        ConnectionError,
        OperationalError,
        ValueError,
        JSONDecodeError,
    ) as exc:
        logger.warning(
            "project_pipeline.quality_debt_upsert_failed",
            run_id=run_id,
            error=str(exc),
        )


async def _evaluate_adaptive_halt_for_run(
    *,
    project_id: str,
    run_id: str,
    chapter_start: int,
    chapter_number: int,
    gate_config: GateConfig,
) -> AdaptiveHaltDecision | None:
    """Evaluate Task 169 adaptive halt in phase2 post-processing.

    The helper is non-invasive by default: it only runs when explicitly enabled.
    Ledger write failures are logged and do not affect accepted/current heads.
    """
    if not gate_config.adaptive_halt_enabled:
        return None
    try:
        await refresh_adaptive_gate_signal_snapshots(
            project_id,
            chapter_start,
            chapter_number,
            run_id=run_id,
        )
        report = await build_adaptive_gate_data_plane_report(
            project_id,
            chapter_start,
            chapter_number,
            run_id=run_id,
            window=gate_config.adaptive_halt_window,
        )
        policy = AdaptiveHaltPolicy(
            policy_id=gate_config.adaptive_halt_policy_id,
            mode=gate_config.adaptive_halt_action_mode,
            warmup_chapters=gate_config.adaptive_halt_warmup_chapters,
        )
        decision = evaluate_adaptive_halt(report, policy)
        await AdaptiveHaltDecisionRepository().create(decision)
        logger.info(
            "project_pipeline.adaptive_halt_decision",
            run_id=run_id,
            chapter_number=chapter_number,
            status=decision.status,
            reasons=[reason.code for reason in decision.reasons],
        )
        return decision
    except (
        RuntimeError,
        OSError,
        ConnectionError,
        OperationalError,
        ValueError,
        SongyanError,
    ) as exc:
        logger.warning(
            "project_pipeline.adaptive_halt_decision_failed",
            run_id=run_id,
            chapter_number=chapter_number,
            error=str(exc),
        )
        return None


# 质量债增量刷新周期（章）：避免每章全量重读日志的 O(n²)（#2）。
_QUALITY_DEBT_FLUSH_INTERVAL = 10

# Task 156: DB 物理维护周期（章）：wal_checkpoint + optimize；VACUUM 按遥测触发。
_DB_MAINTENANCE_INTERVAL = 10
_DB_VACUUM_SIZE_THRESHOLD_BYTES = 200 * 1024 * 1024  # 200MB，T5 预留缓冲


async def _run_db_maintenance(
    run_id: str,
    project_id: str,
    chapter_number: int,
    *,
    final: bool = False,
) -> None:
    """章节边界的物理层维护（非阻塞）：采样遥测 + wal_checkpoint(TRUNCATE) + optimize.

    用独立短连接，避开写事务；失败仅告警不中断 run。VACUUM 仅在收尾且尺寸超阈时
    尝试，避免长跑中途做整库重写。
    """
    try:
        # 1) 采样 DB 尺寸与连续性扫描耗时遥测
        size_metrics = await collect_db_size_metrics()
        scan_latency_ms = await measure_continuity_scan_latency(
            project_id, chapter_number
        )
        await RunDbMetricsRepository().create(
            run_id=run_id,
            project_id=project_id,
            chapter_number=chapter_number,
            db_size_bytes=size_metrics.db_size_bytes,
            wal_size_bytes=size_metrics.wal_size_bytes,
            page_count=size_metrics.page_count,
            page_size=size_metrics.page_size,
            scan_latency_ms=scan_latency_ms,
        )

        logger.info(
            "project_pipeline.db_telemetry_sampled",
            run_id=run_id,
            chapter_number=chapter_number,
            db_size_bytes=size_metrics.db_size_bytes,
            wal_size_bytes=size_metrics.wal_size_bytes,
            scan_latency_ms=round(scan_latency_ms, 3),
            t5_size_redline=check_t5_size_redline(size_metrics),
        )

        # 2) 物理维护：截断 WAL + 优化查询计划
        async with get_db() as conn:
            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            await conn.execute("PRAGMA optimize")

        # 3) 收尾阶段且尺寸超阈时尝试整库 VACUUM（不在中途执行）
        if final and check_t5_size_redline(
            size_metrics, max_db_bytes=_DB_VACUUM_SIZE_THRESHOLD_BYTES
        ):
            async with get_db() as conn:
                await conn.execute("VACUUM")
            logger.info(
                "project_pipeline.db_vacuum_executed",
                run_id=run_id,
                db_size_bytes=size_metrics.db_size_bytes,
            )
    except (
        RuntimeError,
        OSError,
        ConnectionError,
        OperationalError,
        ValueError,
    ) as exc:
        logger.warning(
            "project_pipeline.db_maintenance_failed",
            run_id=run_id,
            chapter_number=chapter_number,
            final=final,
            error=str(exc),
        )


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
    """判断章节是否已完成可结算终态，防止前置非致命错误污染结果.

    Task 128a: degraded_accept 章节跳过 settlement/summary，但仍视为成功终态，
    使 run 能继续下一章而不因 QG false 终止。
    """
    if state.get("status") != "done":
        return False
    if state.get("current_version_id") is None:
        return False
    if state.get("_degraded_accept"):
        return True
    return (
        state.get("settlement_id") is not None
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
    gate_config: GateConfig | None = None,
) -> None:
    """记录最近章节指标，供项目级自动熔断使用."""
    gate_config = gate_config or GateConfig()
    _severity = chapter_result.get("continuity_health_severity") or {}
    recent_results.append({
        "chapter_number": chapter_number,
        "success": chapter_result["success"],
        "quality_gate_passed": chapter_result.get("quality_gate_passed", False),
        "context_emergency": chapter_result.get("context_emergency", False),
        "settlement_success": chapter_result.get("settlement_success"),
        "summary_success": chapter_result.get("summary_success"),
        "continuity_health_score": chapter_result.get("continuity_health_score"),
        "continuity_health_severity": _severity,
        "gate_triggered": chapter_result.get("gate_triggered", False),
        "gate_reasons": chapter_result.get("gate_reasons", []),
    })
    # Task 125: 若使用审计点 streak 窗口，需保留足够历史以覆盖 audit_window 个审计点
    _audit_window = gate_config.health_low_streak_audit_window
    _cap = 3 if _audit_window is None else max(3, _audit_window * 3)
    if len(recent_results) > _cap:
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
    gate_config: GateConfig | None = None,
    previous_p1_counts: list[int] | None = None,
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

    # Task 123: health_low streak 门禁
    _hl_triggered, _hl_reasons = check_health_low_streak_gate(
        recent_results, gate_config, previous_p1_counts=previous_p1_counts
    )
    if _hl_triggered:
        _ch_start = recent_results[0]["chapter_number"]
        await _pause_run_for_auto_halt(
            run_state,
            completed,
            failed,
            persisted_summary,
        )
        raise AutoHaltException(
            message=(
                f"连续 health_low 触发候选硬门禁（Ch{_ch_start}-Ch{chapter_number}）: "
                f"{_hl_reasons}"
            ),
            last_chapter=chapter_number,
            reason="health_low_streak_halt",
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
# Resume helpers
# =============================================================================


async def _find_resume_run(
    project_id: str,
    *,
    resume: bool = False,
    run_id: str | None = None,
) -> ProjectRunState | None:
    """根据 resume/run_id 找到待恢复的运行记录."""
    repo = ProjectRunRepository()
    if run_id:
        existing = await repo.get(run_id)
        if existing is None:
            raise ValueError(f"指定的 run_id 不存在: {run_id}")
        if existing.project_id != project_id:
            raise ValueError(
                f"run_id {run_id} 不属于项目 {project_id}"
            )
        return existing
    if resume:
        runs = await repo.list_by_project(project_id)
        if not runs:
            return None
        return runs[0]
    return None


def _compute_resume_start(
    start: int,
    end: int,
    accepted_chapters: set[int],
) -> int:
    """以 accepted head 为唯一完成事实源，计算 resume 起点.

    返回原始范围内第一个不在 accepted 集合的章号；若全部已完成则返回 end+1。
    """
    for chapter_number in range(start, end + 1):
        if chapter_number not in accepted_chapters:
            return chapter_number
    return end + 1


async def _rebuild_accumulated_summary(
    project_id: str,
    accepted_chapters: set[int],
) -> tuple[str, list[str]]:
    """从 summaries 表逐章重建已 accept 章的累积摘要.

    返回 (最近单章摘要, 按章号排序的格式化摘要片段列表)。
    """
    parts: list[str] = []
    persisted = ""
    for chapter_number in sorted(accepted_chapters):
        summary_text = await _get_summary_text(project_id, chapter_number)
        if summary_text:
            formatted = _format_chapter_summary(chapter_number, summary_text)
            parts.append(formatted)
            persisted = formatted
    return persisted, parts


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
    on_failure: str = "isolate",  # "abort" | "retry" | "isolate"
    continuity_health_threshold: float = 7.0,
    gate_config: GateConfig | None = None,
    resume: bool = False,
    run_id: str | None = None,
) -> ProjectRunResult:
    """运行多章流水线，逐章调用 Phase1Graph，自动传递上下文.

    Args:
        project_id: 项目唯一标识
        chapter_range: (start, end) 章节范围，如 (1, 3)
        mode_id: 创作模式 ID
        auto_confirm: 是否自动接受每章（跳过 human_confirm 中断）
        max_revision_rounds: 单章最大 revision 轮数（透传给 Phase1Graph）
        on_failure: 单章失败策略："isolate" 隔离并继续（默认），"abort" 终止整批，"retry" 重试 1 次
        continuity_health_threshold: 连续性健康分阈值，低于此值触发警告
        gate_config: Task 123 候选硬门禁配置，None 时使用默认关闭配置
        resume: 复用该项目最近一次未完成的 run 进行断点续跑
        run_id: 显式指定要续跑的 run_id（优先级高于 resume）

    Returns:
        ProjectRunResult: 运行结果统计

    Raises:
        ValueError: chapter_range 非法 或 auto_confirm=False（批量模式不支持人工确认）
    """
    gate_config = gate_config or GateConfig()
    start_time = time.monotonic()
    start, end = chapter_range

    # V8 Task 172a.5: 修复 GateConfig 构建时序 —— CLI 在 genre 已知前就构建了全局
    # GateConfig。此处 genre 已确定，按体裁运行时画像覆盖门禁阈值（emergency_halt_ratio）。
    # 无匹配 profile 时 load_profile 回退 scifi baseline（阈值 1.3），行为不变。
    try:
        from songyan.db.genre_runtime_profile_repo import load_profile as _load_rt_profile
        from songyan.workflows._helpers import load_project as _load_project_for_gate

        _project_for_gate = await _load_project_for_gate(project_id)
        if _project_for_gate is not None:
            _rt_profile = await _load_rt_profile(_project_for_gate.genre_id)
            if (
                _rt_profile.emergency_halt_ratio
                != gate_config.context_emergency_budget_ratio_threshold
            ):
                gate_config = gate_config.model_copy(
                    update={
                        "context_emergency_budget_ratio_threshold": _rt_profile.emergency_halt_ratio
                    }
                )
                logger.info(
                    "project_pipeline.gate_config_profile_override",
                    project_id=project_id,
                    genre=_project_for_gate.genre_id,
                    emergency_halt_ratio=_rt_profile.emergency_halt_ratio,
                )
    except Exception as exc:  # noqa: BLE001 - profile 加载失败不阻断运行，用原 gate_config
        logger.warning(
            "project_pipeline.gate_config_profile_skip",
            project_id=project_id,
            error=str(exc),
        )

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
    if run_id is not None and resume:
        # run_id 已显式指定时，resume 标志冗余但不冲突
        resume = False

    # Bug A 修复：查询已有 accepted 章节并跳过（以 accepted head 为唯一完成事实源）
    chapter_head_repo = ChapterHeadRepository()
    all_heads = await chapter_head_repo.list_by_project(project_id)
    accepted_chapters = {
        h.chapter_number for h in all_heads if h.accepted_version_id
    }
    if accepted_chapters:
        logger.info(
            "project_pipeline.skip_accepted_chapters",
            project_id=project_id,
            accepted_chapters=sorted(accepted_chapters),
        )

    # Task 170e: 兜底补建 protagonist Character（脚本/harness 直接建项目、绕过
    # songyan create 时也覆盖）。幂等：项目不存在或已有 protagonist 则 no-op。
    await ensure_protagonist_character(project_id)

    # ---- run 级断点续跑 ----
    existing_run = await _find_resume_run(
        project_id, resume=resume, run_id=run_id
    )
    # Bug B 修复（V8 172b）：completed run 的幂等短路只在「请求范围已全部 accepted」时成立。
    # 分段爬坡逐段扩大 end（25→50→75→100）并 resume 复用最近 run；若该 run 上一段已
    # completed 但本段请求 end 超出已 accepted 范围，则仍有 Ch(resume_start..end) 待生成，
    # 绝不能短路返回，否则后续段 0 生成直接返回（曾致 Ch26-100 从未产出）。
    if (
        existing_run is not None
        and existing_run.status == "completed"
        and _compute_resume_start(start, end, accepted_chapters) > end
    ):
        logger.info(
            "project_pipeline.resume_already_completed",
            run_id=existing_run.run_id,
            project_id=project_id,
        )
        return ProjectRunResult(
            project_id=project_id,
            run_id=existing_run.run_id,
            chapters_completed=existing_run.completed_chapters,
            chapters_failed=existing_run.failed_chapters,
            total_duration_sec=0.0,
            final_status="completed",
            accumulated_summary=existing_run.accumulated_summary,
        )

    # 公共初始化：新 run 默认值；resume 分支在下面被覆盖
    failed: list[int] = []
    accumulated_summary_parts: list[str] = []
    persisted_summary = ""
    resume_start = start

    if existing_run is not None:
        run_id = existing_run.run_id
        run_state = existing_run
        previous_status = run_state.status
        run_state.status = "running"
        run_state.chapter_range_start = start
        run_state.chapter_range_end = end
        resume_start = _compute_resume_start(start, end, accepted_chapters)
        persisted_summary, accumulated_summary_parts = (
            await _rebuild_accumulated_summary(project_id, accepted_chapters)
        )
        # 范围内失败章会被重跑，故从失败清单中移除；范围外保留
        failed = [
            c
            for c in existing_run.failed_chapters
            if not (start <= c <= end)
        ]
        logger.info(
            "project_pipeline.resume",
            run_id=run_id,
            project_id=project_id,
            previous_status=previous_status,
            completed_count=len(accepted_chapters),
            resume_start=resume_start,
        )
        if previous_status == "paused":
            logger.warning(
                "project_pipeline.resume_from_paused",
                run_id=run_id,
                reason="上次运行因质量熔断被暂停；resume 将续跑，门禁仍会生效",
            )
    else:
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

    # 以 accepted head 为完成事实源，预填充 completed；循环内遇到已 accept 章直接跳过
    completed: list[int] = sorted(
        c for c in accepted_chapters if start <= c <= end
    )

    # Task 105: 熔断历史窗口（最近 3 章的指标）
    _recent_results: list[dict[str, Any]] = []

    # Task 125: 保存历史审计数据，供 health_low 异常检测使用
    _previous_health_low_report: Any | None = None
    _previous_p1_counts: list[int] = []

    # Task 127: 保存截至目前最低 health_score，供 score halt 复合条件使用
    _min_health_score_so_far: float | None = None

    # 重置检查指针，消除冷启动导致的首章 WAL 读一致性窗口问题
    await reset_checkpointer()

    # Task 154: 每 run 开始时重置 LLM 调用计数，使预算熔断按 run 隔离
    from songyan.llm.client import reset_llm_call_count

    reset_llm_call_count()

    # resume 时清理该项目孤儿 checkpoint；in-flight 章会在重算前获得新 thread_id
    if existing_run is not None:
        from songyan.workflows.checkpointer import prune_orphan_checkpoints

        pruned = await prune_orphan_checkpoints(project_id, active_thread_ids=set())
        logger.info(
            "project_pipeline.pruned_orphan_checkpoints",
            run_id=run_id,
            pruned_count=pruned,
        )

    # Task 155: 维护"最近成功摘要"游标，失败章不推进游标
    _latest_successful_chapter: int | None = None

    for chapter_number in range(resume_start, end + 1):
        if chapter_number in accepted_chapters:
            logger.info(
                "project_pipeline.skipping_already_accepted",
                run_id=run_id,
                chapter_number=chapter_number,
            )
            continue
        run_state.current_chapter = chapter_number
        await _save_run_state(run_state)

        # 获取上一章 summary 作为当前章的 previous_summary
        # isolate 模式下失败章不推进游标，回退到最近成功章摘要
        if on_failure == "isolate" and _latest_successful_chapter is not None:
            previous_summary = await _get_previous_summary(
                project_id,
                chapter_number,
                latest_successful_chapter=_latest_successful_chapter,
            )
        else:
            previous_summary = await _get_previous_summary(project_id, chapter_number)

        logger.info(
            "project_pipeline.chapter_start",
            run_id=run_id,
            chapter_number=chapter_number,
            previous_summary_length=len(previous_summary),
        )

        # Task 154: 预算熔断异常记录当前章号
        from songyan.llm.client import set_llm_budget_last_chapter

        set_llm_budget_last_chapter(chapter_number)

        # ---- 执行单章 ----
        try:
            chapter_result = await _run_single_chapter(
                project_id=project_id,
                chapter_number=chapter_number,
                mode_id=mode_id,
                previous_summary=previous_summary,
                auto_confirm=auto_confirm,
                on_failure=on_failure,
                continuity_health_threshold=continuity_health_threshold,
                gate_config=gate_config,
                run_id=run_id,
                previous_health_low_report=_previous_health_low_report,
                previous_p1_counts=_previous_p1_counts,
                min_health_score_so_far=_min_health_score_so_far,
            )
        except LLMBudgetExceededError as exc:
            await _pause_run_for_auto_halt(
                run_state,
                completed,
                failed,
                persisted_summary,
            )
            logger.error(
                "project_pipeline.budget_exceeded",
                run_id=run_id,
                used_calls=exc.used_calls,
                budget=exc.budget,
                last_chapter=exc.last_chapter,
            )
            raise

        _append_recent_result(_recent_results, chapter_number, chapter_result, gate_config)

        # V6 Task 146: 周期性刷新 run 级质量债账本（非阻塞）。
        # 质量债由整份 run 日志聚合，逐章全量重读会造成 O(n²)（#2）；此处按
        # _QUALITY_DEBT_FLUSH_INTERVAL 章刷新一次，run 收尾再兜底刷新一次。
        if chapter_number % _QUALITY_DEBT_FLUSH_INTERVAL == 0:
            await _upsert_quality_debt(run_id, project_id)

        # Task 156: 章节边界物理层维护 + 遥测采样（非阻塞）。
        if chapter_number % _DB_MAINTENANCE_INTERVAL == 0:
            await _run_db_maintenance(run_id, project_id, chapter_number)

        # Task 127: 每章运行后更新最低 health_score
        _updated_min_score = chapter_result.get("updated_min_health_score")
        if _updated_min_score is not None:
            _min_health_score_so_far = _updated_min_score

        # Task 125: 审计点章节更新历史数据，供后续 health_low 异常检测使用
        _health_low_report = chapter_result.get("health_low_report")
        if _health_low_report is not None:
            _previous_health_low_report = _health_low_report
            _severity = chapter_result.get("continuity_health_severity") or {}
            _previous_p1_counts.append(_severity.get("P1", 0))

        if chapter_result["success"]:
            completed.append(chapter_number)
            _latest_successful_chapter = chapter_number
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
            adaptive_decision = (
                await _evaluate_adaptive_halt_for_run(
                    project_id=project_id,
                    run_id=run_id,
                    chapter_start=start,
                    chapter_number=chapter_number,
                    gate_config=gate_config,
                )
                if gate_config.adaptive_halt_enabled
                else None
            )
            if adaptive_decision is not None and adaptive_decision.status == "halt":
                await _pause_run_for_auto_halt(
                    run_state,
                    completed,
                    failed,
                    persisted_summary,
                )
                raise AutoHaltException(
                    message=(
                        f"Ch{chapter_number} 触发自适应 halt: "
                        f"{[reason.code for reason in adaptive_decision.reasons]}"
                    ),
                    last_chapter=chapter_number,
                    reason="adaptive_halt_decision",
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
            adaptive_decision = (
                await _evaluate_adaptive_halt_for_run(
                    project_id=project_id,
                    run_id=run_id,
                    chapter_start=start,
                    chapter_number=chapter_number,
                    gate_config=gate_config,
                )
                if gate_config.adaptive_halt_enabled
                else None
            )
            if adaptive_decision is not None and adaptive_decision.status == "halt":
                await _pause_run_for_auto_halt(
                    run_state,
                    completed,
                    failed,
                    persisted_summary,
                )
                raise AutoHaltException(
                    message=(
                        f"Ch{chapter_number} 触发自适应 halt: "
                        f"{[reason.code for reason in adaptive_decision.reasons]}"
                    ),
                    last_chapter=chapter_number,
                    reason="adaptive_halt_decision",
                )
            await _check_auto_halt_window(
                run_state,
                _recent_results,
                completed,
                failed,
                persisted_summary,
                run_id=run_id,
                chapter_number=chapter_number,
                gate_config=gate_config,
                previous_p1_counts=_previous_p1_counts,
            )
            if on_failure == "abort":
                break
            if on_failure == "isolate":
                # 失败章不推进"最近成功摘要"游标
                continue
            # on_failure == "retry" 已在 _run_single_chapter 中处理，
            # 如果 retry 仍失败，则记录失败并终止（与 abort 同效）
            break

        # Task 123: 单章即时门禁在日志记录后由 _run_single_chapter 返回标记，
        # 这里统一处理 enforce 模式下的 pause。
        if chapter_result.get("gate_triggered") and gate_config.is_enforce():
            await _pause_run_for_auto_halt(
                run_state,
                completed,
                failed,
                persisted_summary,
            )
            raise AutoHaltException(
                message=(
                    f"Ch{chapter_number} 触发候选硬门禁: "
                    f"{chapter_result.get('gate_reasons', [])}"
                ),
                last_chapter=chapter_number,
                reason=chapter_result.get("gate_reasons", ["unknown"])[0],
            )

        await _check_auto_halt_window(
            run_state,
            _recent_results,
            completed,
            failed,
            persisted_summary,
            run_id=run_id,
            chapter_number=chapter_number,
            gate_config=gate_config,
            previous_p1_counts=_previous_p1_counts,
        )

    # ---- 收尾 ----
    duration = time.monotonic() - start_time
    final_status = "completed" if not failed else ("partial" if completed else "failed")

    # #2 兜底：run 结束时刷新一次质量债，保证 completed/partial run 均有完整汇总
    # （周期刷新可能未覆盖最后不足 _QUALITY_DEBT_FLUSH_INTERVAL 章的尾段）。
    await _upsert_quality_debt(run_id, project_id)

    # Task 156: run 收尾再执行一次 DB 维护 + 遥测采样；尺寸超阈时尝试 VACUUM。
    await _run_db_maintenance(
        run_id, project_id, run_state.current_chapter or end, final=True
    )

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
    gate_config: GateConfig | None = None,
    *,
    run_id: str | None = None,
    previous_health_low_report: Any | None = None,
    previous_p1_counts: list[int] | None = None,
    min_health_score_so_far: float | None = None,
) -> dict[str, Any]:
    """运行单章，含 auto_confirm 处理和失败重试.

    Returns:
        {
            "success": bool,
            "summary_text": str,
            "error": str | None,
            "final_state": dict | None,
            "final_version_id": str | None,
            "continuity_health_severity": dict | None,
            "gate_triggered": bool,
            "gate_reasons": list[str],
            "updated_min_health_score": float | None,
        }
    """
    gate_config = gate_config or GateConfig()
    started_at = datetime.now()
    chapter_start = time.monotonic()
    thread_id = new_id("thread")
    attempts = 0
    max_attempts = 2 if on_failure == "retry" else 1
    final_state: dict[str, Any] | None = None
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
            final_state = cast(dict[str, Any], state)

            # 处理 human_confirm 中断
            if "__interrupt__" in state:
                if auto_confirm:
                    _stage = "human_confirm"  # 跟踪当前阶段
                    state = await resume_human_confirm(thread_id, "accept")
                    final_state = cast(dict[str, Any], state)
                else:
                    error_stage = "human_confirm"
                    break

            # 检查最终状态。Task 121f: 若章节已经完成正文、settlement 与
            # summary，前置 CreativeDirector 等非致命解析错误只能作为诊断，
            # 不能污染最终章节成功判定。
            if _is_terminal_success_state(cast(dict[str, Any], state)):
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
            continuity_health_severity: dict[str, int] | None = None
            health_low_report: Any | None = None
            assert final_state is not None
            if chapter_number % 3 == 0:
                try:
                    project_for_audit = await _load_project_for_audit(project_id)
                    runtime_profile = None
                    if project_for_audit is not None:
                        runtime_profile = await _load_runtime_profile(
                            project_for_audit.genre_id
                        )

                    auditor = ContinuityAuditor(runtime_profile=runtime_profile)
                    report = await auditor.audit(
                        project_id=project_id,
                        up_to_chapter=chapter_number,
                    )
                    await auditor.write_constraints(report, version_id=final_version_id)
                    continuity_health_score = report.overall_health_score
                    continuity_health_severity = cast(dict[str, int], classify_report(report))
                    health_low_report = report
                    if report.overall_health_score < continuity_health_threshold:
                        logger.warning(
                            "continuity.health_low",
                            run_id=run_id,
                            chapter_number=chapter_number,
                            score=report.overall_health_score,
                            threshold=continuity_health_threshold,
                            orphaned=len(report.orphaned_settings),
                            overdue=len(report.overdue_foreshadowings),
                            severity=continuity_health_severity,
                        )
                except Exception as exc:
                    logger.warning(
                        "continuity.audit_failed",
                        run_id=run_id,
                        chapter_number=chapter_number,
                        error=str(exc),
                    )

            _stage = "run_logger"  # 跟踪当前阶段
            # Task 105: 透传上下文指标供外层熔断检查
            _ctx_metrics = final_state.get("_context_metrics", {}) if final_state else {}
            _qg_passed = final_state.get("_quality_gate_passed") if final_state else None

            # Task 123: 先构造 preliminary chapter_result，用于单章门禁判断
            _preliminary_result: dict[str, Any] = {
                "success": True,
                "quality_gate_passed": _qg_passed,
                "context_emergency": _ctx_metrics.get("context_emergency", False),
                "settlement_success": (
                    not final_state.get("_settlement_needs_human_review", False)
                    and not final_state.get("_skip_settlement", False)
                    and final_state.get("settlement_id") is not None
                ),
                "summary_success": final_state.get("summary_id") is not None,
            }

            # Task 123: 单章候选硬门禁判断（在写日志前完成，使日志包含 gate 信息）
            _gate_triggered, _gate_reasons, _updated_min_score = evaluate_all_gates(
                health_low_report=health_low_report,
                context_metrics=_ctx_metrics,
                chapter_result=_preliminary_result,
                recent_results=[],
                config=gate_config,
                previous_health_low_report=previous_health_low_report,
                previous_p1_counts=previous_p1_counts,
                min_health_score_so_far=min_health_score_so_far,
            )

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
                continuity_health_severity=continuity_health_severity,
                gate_triggered=_gate_triggered,
                gate_reasons=_gate_reasons,
                gate_mode=gate_config.gate_mode,
                duration_sec=duration_sec,
            )
            logged_budget = getattr(chapter_log, "budget_used", None)
            logged_context_emergency = getattr(chapter_log, "context_emergency", None)
            logged_qg_passed = getattr(chapter_log, "quality_gate_passed", None)
            logged_settlement_success = getattr(chapter_log, "settlement_success", None)
            logged_summary_success = getattr(chapter_log, "summary_success", None)
            if not isinstance(logged_context_emergency, bool):
                logged_context_emergency = _ctx_metrics.get("context_emergency", False)
            if logged_qg_passed not in (True, False, None):
                logged_qg_passed = _qg_passed

            if _gate_triggered:
                logger.warning(
                    "project_pipeline.gate_triggered",
                    run_id=run_id,
                    chapter_number=chapter_number,
                    gate_mode=gate_config.gate_mode,
                    reasons=_gate_reasons,
                )

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
                "continuity_health_score": continuity_health_score,
                "continuity_health_severity": continuity_health_severity,
                "health_low_report": health_low_report,
                "gate_triggered": _gate_triggered,
                "gate_reasons": _gate_reasons,
                "updated_min_health_score": _updated_min_score,
            }


        except LLMBudgetExceededError:
            raise
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
        "continuity_health_score": None,
        "continuity_health_severity": None,
        "gate_triggered": False,
        "gate_reasons": [],
        "updated_min_health_score": min_health_score_so_far,
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
