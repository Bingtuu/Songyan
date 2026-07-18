"""Task 123/125: ContextEmergency / health_low 候选硬门禁判断函数.

所有函数均为纯逻辑，不依赖数据库或 LangGraph state，便于单元测试。
默认行为与 V5.0 兼容：当 GateConfig 未提供或全部开关关闭时，不触发任何门禁。
Task 125 新增：支持基于滚动中位数的 P1 异常检测和 health_score 相对跌幅检测，
避免对长篇叙事中正常累积的未回收设定过度敏感。
"""

from __future__ import annotations

import statistics
from typing import Any

from songyan.agents.continuity_auditor.continuity_health import (
    count_hard_p1_for_halt,
)
from songyan.models import ContinuityReport, GateConfig


def _default_gate_config() -> GateConfig:
    """返回默认关闭的 GateConfig，用于兼容未显式传参的调用方."""
    return GateConfig()


def _median(values: list[int]) -> float:
    """返回整数列表的中位数；空列表返回 0.0."""
    if not values:
        return 0.0
    return float(statistics.median(values))


def _is_health_low_result(result: dict[str, Any]) -> bool:
    """Return whether a recent result should count toward health-low streak.

    Older tests/runs did not persist the score in recent_results, so absence of
    the field preserves legacy severity-only behavior. New runs include the
    score and only count audit points below the V-gate health floor.
    """
    score = result.get("continuity_health_score")
    if score is None:
        return result.get("continuity_health_severity") is not None
    try:
        return float(score) < 8.0
    except (TypeError, ValueError):
        return result.get("continuity_health_severity") is not None


def check_health_low_single_gate(
    report: ContinuityReport,
    config: GateConfig | None = None,
    previous_p1_counts: list[int] | None = None,
    previous_report: ContinuityReport | None = None,
    min_health_score_so_far: float | None = None,
) -> tuple[bool, list[str], float | None]:
    """单章 health_low 即时门禁判断.

    Task 125 扩展：
    - 当 `health_low_p1_anomaly_factor` 配置时，P1 需同时满足最小绝对数量
      并超过最近审计点 P1 计数滚动中位数的指定倍数才触发。

    Task 127 扩展：
    - `health_low_score_halt_enabled` 改用"历史新低 + P1 同步激增"复合条件，
      仅当当前 overall_health_score 低于历史最低值且同章 P1 超过近期中位数
      倍数时才触发，避免开局期正常回落误伤。

    Args:
        report: 当前章节的 ContinuityReport。
        config: GateConfig。
        previous_p1_counts: 之前审计点章节的 P1 计数列表，用于 P1 异常检测。
        previous_report: 上一次审计点的 ContinuityReport（保留参数以保持调用
            兼容，当前复合条件不再使用相对跌幅）。
        min_health_score_so_far: 截至目前见过的最低 overall_health_score，
            None 表示尚未有历史最低值（开局第一章）。

    Returns:
        (triggered, reasons, updated_min_health_score)
    """
    config = config or _default_gate_config()
    reasons: list[str] = []

    current_score = report.overall_health_score
    updated_min_score: float | None = (
        current_score if current_score is not None else min_health_score_so_far
    )
    if min_health_score_so_far is not None and current_score is not None:
        updated_min_score = min(min_health_score_so_far, current_score)

    if not config.health_low_gate_enabled:
        return False, reasons, updated_min_score

    # Task 171p2: 硬 halt 只看"硬 P1"（critical orphaned setting），排除 state_mismatch
    # （启发式假阳性，真实矛盾由 LLM coherence 章级阻断）。
    hard_p1 = count_hard_p1_for_halt(report)

    if config.health_low_p1_halt and hard_p1 > 0:
        p1_count = hard_p1
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
                f"(critical orphaned setting)"
            )

    if (
        config.health_low_score_halt_enabled
        and current_score is not None
        and min_health_score_so_far is not None
        and current_score < min_health_score_so_far
    ):
        p1_count = hard_p1
        window = config.health_low_score_halt_window
        recent = (previous_p1_counts or [])[-window:] if previous_p1_counts else []
        baseline = _median(recent) * config.health_low_score_halt_anomaly_factor
        if p1_count >= config.health_low_score_halt_min_p1 and p1_count > baseline:
            reasons.append(
                f"health_low_score_halt: score={current_score} < "
                f"min_so_far={min_health_score_so_far} and "
                f"P1_count={p1_count} >= min_p1={config.health_low_score_halt_min_p1} and "
                f"> baseline*factor={baseline:.1f}"
            )

    return bool(reasons), reasons, updated_min_score


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
            r for r in recent_results if _is_health_low_result(r)
        ]
        if len(audit_results) < audit_window:
            return False, reasons
        recent = audit_results[-audit_window:]
        window = audit_window
    else:
        window = config.health_low_streak_window
        recent = recent_results[-window:] if len(recent_results) >= window else recent_results
        recent = [r for r in recent if _is_health_low_result(r)]
        if not recent:
            return False, reasons

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
    min_health_score_so_far: float | None = None,
) -> tuple[bool, list[str], float | None]:
    """汇总全部候选门禁判断.

    Args:
        health_low_report: 当前章节连续性审计报告（审计点章节有值）。
        context_metrics: ContextEmergency 相关指标。
        chapter_result: 单章运行结果。
        recent_results: 最近章节结果列表，供 streak gate 使用。
        config: GateConfig。
        previous_health_low_report: 上一次审计点的连续性审计报告。
        previous_p1_counts: 之前审计点章节的 P1 计数列表。
        min_health_score_so_far: 截至目前见过的最低 overall_health_score。

    Returns:
        (any_triggered, all_reasons, updated_min_health_score)
    """
    config = config or _default_gate_config()
    all_reasons: list[str] = []
    updated_min_score: float | None = min_health_score_so_far

    if health_low_report is not None:
        triggered, reasons, updated_min_score = check_health_low_single_gate(
            health_low_report,
            config,
            previous_p1_counts=previous_p1_counts,
            previous_report=previous_health_low_report,
            min_health_score_so_far=min_health_score_so_far,
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

    return bool(all_reasons), all_reasons, updated_min_score
