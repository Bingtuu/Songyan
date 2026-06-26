"""Task 123/125: ContextEmergency / health_low 候选硬门禁判断函数.

所有函数均为纯逻辑，不依赖数据库或 LangGraph state，便于单元测试。
默认行为与 V5.0 兼容：当 GateConfig 未提供或全部开关关闭时，不触发任何门禁。
Task 125 新增：支持基于滚动中位数的 P1 异常检测和 health_score 相对跌幅检测，
避免对长篇叙事中正常累积的未回收设定过度敏感。
"""

from __future__ import annotations

import statistics
from typing import Any

from songyan.agents.continuity_auditor.continuity_health import classify_report
from songyan.models import ContinuityReport, GateConfig


def _default_gate_config() -> GateConfig:
    """返回默认关闭的 GateConfig，用于兼容未显式传参的调用方."""
    return GateConfig()


def _median(values: list[int]) -> float:
    """返回整数列表的中位数；空列表返回 0.0."""
    if not values:
        return 0.0
    return float(statistics.median(values))


def check_health_low_single_gate(
    report: ContinuityReport,
    config: GateConfig | None = None,
    previous_p1_counts: list[int] | None = None,
    previous_report: ContinuityReport | None = None,
) -> tuple[bool, list[str]]:
    """单章 health_low 即时门禁判断.

    Task 125 扩展：
    - 当 `health_low_p1_anomaly_factor` 配置时，P1 需同时满足最小绝对数量
      并超过最近审计点 P1 计数滚动中位数的指定倍数才触发。
    - 当 `health_low_score_drop_threshold` 配置时，health_score 门禁改为检测
      相对前一次审计的跌幅，而非固定绝对阈值。

    Args:
        report: 当前章节的 ContinuityReport。
        config: GateConfig。
        previous_p1_counts: 之前审计点章节的 P1 计数列表，用于异常检测。
        previous_report: 上一次审计点的 ContinuityReport，用于 score drop 检测。

    Returns:
        (triggered, reasons)
    """
    config = config or _default_gate_config()
    reasons: list[str] = []

    if not config.health_low_gate_enabled:
        return False, reasons

    severity = classify_report(report)

    if config.health_low_p1_halt and severity["P1"] > 0:
        p1_count = severity["P1"]
        if config.health_low_p1_anomaly_factor is not None:
            baseline = _median(previous_p1_counts or []) * config.health_low_p1_anomaly_factor
            min_absolute = config.health_low_p1_min_absolute or 0
            if p1_count >= min_absolute and p1_count > baseline:
                reasons.append(
                    f"health_low_p1_halt: P1_count={p1_count} "
                    f">= min_absolute={min_absolute} and "
                    f"> baseline*factor={baseline:.1f}"
                )
        else:
            reasons.append(
                f"health_low_p1_halt: P1_count={p1_count} "
                f"(state_mismatch or critical orphaned setting)"
            )

    if config.health_low_absolute_score_halt and report.overall_health_score is not None:
        current_score = report.overall_health_score
        if config.health_low_score_drop_threshold is not None:
            if (
                previous_report is not None
                and previous_report.overall_health_score is not None
                and previous_report.overall_health_score - current_score
                >= config.health_low_score_drop_threshold
            ):
                reasons.append(
                    f"health_low_absolute_score_halt: score dropped from "
                    f"{previous_report.overall_health_score} to {current_score} "
                    f">= threshold={config.health_low_score_drop_threshold}"
                )
        elif current_score < config.health_low_absolute_score_threshold:
            reasons.append(
                f"health_low_absolute_score_halt: score={current_score} "
                f"< threshold={config.health_low_absolute_score_threshold}"
            )

    return bool(reasons), reasons


def check_health_low_streak_gate(
    recent_results: list[dict[str, Any]],
    config: GateConfig | None = None,
    previous_p1_counts: list[int] | None = None,
) -> tuple[bool, list[str]]:
    """连续 health_low streak 门禁判断.

    Task 125 扩展：
    - 当 `health_low_streak_audit_window` 配置时，只对带 `continuity_health_severity`
      的审计点章节做 streak 统计，避免非审计点章节的 None severity 稀释或误触发。
    - 当 `health_low_p1_anomaly_factor` 配置时，streak 阈值基于历史审计点 P1
      中位数的倍数动态计算。

    Args:
        recent_results: 最近章节结果列表。
        config: GateConfig。
        previous_p1_counts: 之前审计点章节的 P1 计数列表，用于动态阈值。

    Returns:
        (triggered, reasons)
    """
    config = config or _default_gate_config()
    reasons: list[str] = []

    if not config.health_low_gate_enabled or not config.health_low_streak_halt:
        return False, reasons

    audit_window = config.health_low_streak_audit_window
    if audit_window is not None:
        audit_results = [
            r for r in recent_results if r.get("continuity_health_severity") is not None
        ]
        if len(audit_results) < audit_window:
            return False, reasons
        recent = audit_results[-audit_window:]
        window = audit_window
    else:
        window = config.health_low_streak_window
        recent = recent_results[-window:] if len(recent_results) >= window else recent_results

    p1_total = sum(
        (r.get("continuity_health_severity") or {}).get("P1", 0) for r in recent
    )
    p2_total = sum(
        (r.get("continuity_health_severity") or {}).get("P2", 0) for r in recent
    )

    p1_limit = config.health_low_streak_p1_limit
    if (
        audit_window is not None
        and config.health_low_p1_anomaly_factor is not None
        and previous_p1_counts
        and len(previous_p1_counts) >= 3
    ):
        baseline = (
            _median(previous_p1_counts)
            * audit_window
            * config.health_low_p1_anomaly_factor
        )
        p1_limit = int(max(baseline, p1_limit))

    if p1_total >= p1_limit and p1_limit > 0:
        reasons.append(
            f"health_low_streak_halt: window={window} P1_total={p1_total} "
            f">= limit={p1_limit}"
        )
    elif p2_total >= config.health_low_streak_p2_limit and config.health_low_streak_p2_limit > 0:
        reasons.append(
            f"health_low_streak_halt: window={window} P2_total={p2_total} "
            f">= limit={config.health_low_streak_p2_limit}"
        )

    return bool(reasons), reasons


def check_context_emergency_single_gate(
    context_metrics: dict[str, Any],
    chapter_result: dict[str, Any],
    config: GateConfig | None = None,
) -> tuple[bool, list[str]]:
    """单章 ContextEmergency 门禁判断.

    Args:
        context_metrics: 来自 _context_metrics 的字典，含 budget_used_before_emergency。
        chapter_result: 单章运行结果，含 settlement_success / summary_success。
        config: GateConfig。
    """
    config = config or _default_gate_config()
    reasons: list[str] = []

    if not config.context_emergency_gate_enabled:
        return False, reasons

    context_emergency = bool(context_metrics.get("context_emergency", False))
    if not context_emergency:
        return False, reasons

    ratio = context_metrics.get("budget_used_before_emergency")
    if (
        config.context_emergency_single_halt
        and ratio is not None
        and ratio >= config.context_emergency_budget_ratio_threshold
    ):
        reasons.append(
            f"context_emergency_budget_ratio_halt: "
            f"budget_used_before_emergency={ratio:.4f} "
            f">= threshold={config.context_emergency_budget_ratio_threshold}"
        )

    if config.context_emergency_failure_halt:
        if chapter_result.get("settlement_success") is False:
            reasons.append("context_emergency_failure_halt: settlement_success=False")
        if chapter_result.get("summary_success") is False:
            reasons.append("context_emergency_failure_halt: summary_success=False")

    return bool(reasons), reasons


def evaluate_all_gates(
    *,
    health_low_report: ContinuityReport | None,
    context_metrics: dict[str, Any],
    chapter_result: dict[str, Any],
    recent_results: list[dict[str, Any]],
    config: GateConfig | None = None,
    previous_health_low_report: ContinuityReport | None = None,
    previous_p1_counts: list[int] | None = None,
) -> tuple[bool, list[str]]:
    """汇总全部候选门禁判断.

    Args:
        health_low_report: 当前章节连续性审计报告（审计点章节有值）。
        context_metrics: ContextEmergency 相关指标。
        chapter_result: 单章运行结果。
        recent_results: 最近章节结果列表，供 streak gate 使用。
        config: GateConfig。
        previous_health_low_report: 上一次审计点的连续性审计报告。
        previous_p1_counts: 之前审计点章节的 P1 计数列表。

    Returns:
        (any_triggered, all_reasons)
    """
    config = config or _default_gate_config()
    all_reasons: list[str] = []

    if health_low_report is not None:
        triggered, reasons = check_health_low_single_gate(
            health_low_report,
            config,
            previous_p1_counts=previous_p1_counts,
            previous_report=previous_health_low_report,
        )
        if triggered:
            all_reasons.extend(reasons)

    triggered, reasons = check_health_low_streak_gate(
        recent_results, config, previous_p1_counts=previous_p1_counts
    )
    if triggered:
        all_reasons.extend(reasons)

    triggered, reasons = check_context_emergency_single_gate(
        context_metrics, chapter_result, config
    )
    if triggered:
        all_reasons.extend(reasons)

    return bool(all_reasons), all_reasons
