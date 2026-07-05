"""Adaptive halt decision engine (V7 Task 169a)."""

from __future__ import annotations

from typing import Any

from songyan.models import (
    AdaptiveGateDataPlaneReport,
    AdaptiveGateSignalWindow,
    AdaptiveHaltDecision,
    AdaptiveHaltDecisionStatus,
    AdaptiveHaltPolicy,
    AdaptiveHaltReason,
    AdaptiveHaltReasonCode,
)


def _decision_id(report: AdaptiveGateDataPlaneReport, policy: AdaptiveHaltPolicy) -> str:
    run_key = report.run_id or "norun"
    return (
        f"ahd-{report.project_id}-{run_key}-"
        f"{report.chapter_start}-{report.chapter_end}-{policy.policy_id}"
    )


def _reason_id(code: AdaptiveHaltReasonCode, index: int) -> str:
    return f"ahr-{code}-{index:02d}"


def _present_domains(report: AdaptiveGateDataPlaneReport) -> set[str]:
    return {
        domain
        for domain, counts in report.source_status_counts.items()
        if counts.get("present", 0) > 0
    }


def _insufficient_summary(report: AdaptiveGateDataPlaneReport) -> dict[str, Any]:
    return {
        "snapshot_count": report.snapshot_count,
        "window_count": len(report.windows),
        "source_status_counts": report.source_status_counts,
    }


def _add_reason(
    reasons: list[AdaptiveHaltReason],
    *,
    code: AdaptiveHaltReasonCode,
    signal_domain: str,
    message: str,
    evidence: dict[str, Any],
) -> None:
    reasons.append(
        AdaptiveHaltReason(
            reason_id=_reason_id(code, len(reasons) + 1),
            code=code,
            severity="halt_candidate",
            signal_domain=signal_domain,
            message=message,
            evidence=evidence,
        )
    )


def _evaluate_window(
    window: AdaptiveGateSignalWindow,
    policy: AdaptiveHaltPolicy,
) -> list[AdaptiveHaltReason]:
    reasons: list[AdaptiveHaltReason] = []
    if (
        window.health_min is not None
        and window.health_min < policy.health_min_threshold
        and (
            (window.p1_median or 0.0) >= policy.p1_median_threshold
            or (window.p2_median or 0.0) >= policy.p2_median_threshold
        )
    ):
        _add_reason(
            reasons,
            code="health_p1_spike",
            signal_domain="continuity",
            message="health 低位且 P1/P2 同窗抬升",
            evidence={
                "window": [window.start_chapter, window.end_chapter],
                "health_min": window.health_min,
                "p1_median": window.p1_median,
                "p2_median": window.p2_median,
                "thresholds": {
                    "health_min": policy.health_min_threshold,
                    "p1_median": policy.p1_median_threshold,
                    "p2_median": policy.p2_median_threshold,
                },
            },
        )
    if (
        window.orphan_slope is not None
        and window.orphan_slope >= policy.orphan_slope_threshold
    ) or (
        window.orphan_delta is not None
        and window.orphan_delta >= policy.orphan_delta_threshold
    ):
        _add_reason(
            reasons,
            code="orphan_acceleration",
            signal_domain="continuity",
            message="orphan slope/delta 持续抬升",
            evidence={
                "window": [window.start_chapter, window.end_chapter],
                "orphan_slope": window.orphan_slope,
                "orphan_delta": window.orphan_delta,
                "thresholds": {
                    "orphan_slope": policy.orphan_slope_threshold,
                    "orphan_delta": policy.orphan_delta_threshold,
                },
            },
        )
    quality_values = {
        "degraded_ratio": window.degraded_ratio,
        "convergence_ratio": window.convergence_ratio,
        "qg_false_ratio": window.qg_false_ratio,
    }
    if any(
        value is not None and value >= policy.quality_debt_ratio
        for value in quality_values.values()
    ):
        _add_reason(
            reasons,
            code="quality_debt_streak",
            signal_domain="quality",
            message="质量债窗口比例偏高",
            evidence={
                "window": [window.start_chapter, window.end_chapter],
                **quality_values,
                "threshold": policy.quality_debt_ratio,
            },
        )
    if (
        window.schedule_missed_rate is not None
        and window.schedule_missed_rate >= policy.schedule_missed_rate
    ) or (
        window.schedule_overdue_rate is not None
        and window.schedule_overdue_rate >= policy.schedule_overdue_rate
    ):
        _add_reason(
            reasons,
            code="schedule_miss_spike",
            signal_domain="narrative",
            message="主动调度 missed/overdue 比例偏高",
            evidence={
                "window": [window.start_chapter, window.end_chapter],
                "missed_rate": window.schedule_missed_rate,
                "overdue_rate": window.schedule_overdue_rate,
                "thresholds": {
                    "missed_rate": policy.schedule_missed_rate,
                    "overdue_rate": policy.schedule_overdue_rate,
                },
            },
        )
    if (
        window.context_emergency_ratio is not None
        and window.context_emergency_ratio >= policy.context_pressure_ratio
    ) or (
        window.budget_used_max is not None
        and window.budget_used_max >= policy.context_budget_threshold
    ):
        _add_reason(
            reasons,
            code="context_pressure_streak",
            signal_domain="context",
            message="context emergency 或预算压力持续偏高",
            evidence={
                "window": [window.start_chapter, window.end_chapter],
                "context_emergency_ratio": window.context_emergency_ratio,
                "budget_used_max": window.budget_used_max,
                "thresholds": {
                    "context_pressure_ratio": policy.context_pressure_ratio,
                    "context_budget": policy.context_budget_threshold,
                },
            },
        )
    hard_cleanliness_count = (
        window.meta_tag_leak_total + window.duplicate_paragraph_total
    )
    if hard_cleanliness_count >= policy.cleanliness_hard_count_threshold:
        _add_reason(
            reasons,
            code="cleanliness_regression",
            signal_domain="cleanliness",
            message="T9 hard cleanliness 信号回归",
            evidence={
                "window": [window.start_chapter, window.end_chapter],
                "meta_tag_leak_total": window.meta_tag_leak_total,
                "duplicate_paragraph_total": window.duplicate_paragraph_total,
                "timeline_conflict_total_observation": window.timeline_conflict_total,
                "threshold": policy.cleanliness_hard_count_threshold,
            },
        )
    return reasons


def _status_from_reasons(
    report: AdaptiveGateDataPlaneReport,
    policy: AdaptiveHaltPolicy,
    reasons: list[AdaptiveHaltReason],
) -> AdaptiveHaltDecisionStatus:
    if not reasons:
        return "continue"
    if report.chapter_end <= policy.warmup_chapters:
        return "warn"
    domains = {reason.signal_domain for reason in reasons}
    if policy.require_multi_signal and len(domains) < 2:
        return "warn"
    return "halt" if policy.mode == "enforce" else "halt_candidate"


def evaluate_adaptive_halt(
    report: AdaptiveGateDataPlaneReport,
    policy: AdaptiveHaltPolicy | None = None,
) -> AdaptiveHaltDecision:
    """Evaluate one data-plane report without touching workflow or SQLite."""
    policy = policy or AdaptiveHaltPolicy()
    evidence: dict[str, Any] = {
        "window_count": len(report.windows),
        "snapshot_count": report.snapshot_count,
        "source_status_counts": report.source_status_counts,
    }
    if len(report.windows) < policy.min_window_count:
        reason = AdaptiveHaltReason(
            reason_id="ahr-insufficient_samples-01",
            code="insufficient_samples",
            severity="observe",
            signal_domain="data_plane",
            message="窗口样本不足，不能进行 halt 判定",
            evidence=_insufficient_summary(report),
        )
        return AdaptiveHaltDecision(
            decision_id=_decision_id(report, policy),
            project_id=report.project_id,
            run_id=report.run_id,
            chapter_start=report.chapter_start,
            chapter_end=report.chapter_end,
            evaluated_at_chapter=report.chapter_end,
            status="observe",
            reasons=[reason],
            evidence=evidence,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
        )

    if not _present_domains(report):
        reason = AdaptiveHaltReason(
            reason_id="ahr-insufficient_samples-01",
            code="insufficient_samples",
            severity="observe",
            signal_domain="data_plane",
            message="所有信号域均缺失或不足，不能进行 halt 判定",
            evidence=_insufficient_summary(report),
        )
        return AdaptiveHaltDecision(
            decision_id=_decision_id(report, policy),
            project_id=report.project_id,
            run_id=report.run_id,
            chapter_start=report.chapter_start,
            chapter_end=report.chapter_end,
            evaluated_at_chapter=report.chapter_end,
            status="observe",
            reasons=[reason],
            evidence=evidence,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
        )

    reasons = _evaluate_window(report.windows[-1], policy)
    status = _status_from_reasons(report, policy, reasons)
    if status == "warn" and report.chapter_end <= policy.warmup_chapters and reasons:
        reasons.append(
            AdaptiveHaltReason(
                reason_id=_reason_id("warmup_protection", len(reasons) + 1),
                code="warmup_protection",
                severity="warn",
                signal_domain="policy",
                message="开局保护期内异常最多升级为 warn",
                evidence={
                    "chapter_end": report.chapter_end,
                    "warmup_chapters": policy.warmup_chapters,
                },
            )
        )
    return AdaptiveHaltDecision(
        decision_id=_decision_id(report, policy),
        project_id=report.project_id,
        run_id=report.run_id,
        chapter_start=report.chapter_start,
        chapter_end=report.chapter_end,
        evaluated_at_chapter=report.chapter_end,
        status=status,
        reasons=reasons,
        evidence=evidence,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
    )
