"""Task 105: Ch51-Ch100 流式验证报告生成器.

一键读取 JSONL 运行日志，生成 markdown 报告并触发决策门 DG-1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from songyan.models.run_log import ChapterRunLog
from songyan.utils.run_id import validate_run_id

_LOGS_DIR = Path("logs/chapter_runs")


class DecisionGateResult:
    """决策门结果 (DG-1 / DG-2)."""

    def __init__(
        self,
        passed: bool,
        reason: str,
        metrics: dict[str, Any],
        status: str | None = None,
    ) -> None:
        self.passed = passed
        self.reason = reason
        self.metrics = metrics
        self.status = status or ("passed" if passed else "failed")


def read_run_logs(run_id: str) -> list[ChapterRunLog]:
    """从 JSONL 读取指定 run_id 的运行日志."""
    run_id = validate_run_id(run_id)
    filepath = _LOGS_DIR / f"{run_id}.jsonl"
    logs: list[ChapterRunLog] = []
    if not filepath.exists():
        return logs
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                logs.append(ChapterRunLog.model_validate(data))
            except (json.JSONDecodeError, ValueError):
                continue
    return logs


def _compute_word_count_ratio(log: ChapterRunLog) -> float | None:
    """从 context_pressure 中推算字数比例（如有 word_count_target）."""
    cp = log.context_pressure or {}
    target = cp.get("word_count_target")
    if target and target > 0 and log.word_count > 0:
        return round(float(log.word_count) / float(target), 3)
    return None


def _format_float(value: float | None) -> str:
    """格式化可缺失浮点数，保留 0.000 并兼容 None."""
    if value is None:
        return "-"
    return f"{value:.3f}"


def _format_int(value: int | None) -> str:
    """格式化可缺失整数."""
    if value is None:
        return "-"
    return str(value)


def _format_bool(value: bool | None) -> str:
    """格式化可缺失布尔值."""
    if value is None:
        return "?"
    return "Y" if value else "N"


def _format_chapters(chapters: list[int]) -> str:
    """格式化章节列表."""
    if not chapters:
        return "-"
    return ", ".join(f"Ch{chapter}" for chapter in chapters)


def _decision_label(dg: DecisionGateResult) -> str:
    """返回报告中的决策门状态标签."""
    if dg.status == "passed":
        return "✅ 通过"
    if dg.status == "conditional":
        return "⚠ 条件通过"
    return "❌ 未通过"


def _failure_reason(log: ChapterRunLog) -> str:
    """生成失败章节的可读原因."""
    stage = log.error_stage or "unknown_stage"
    error = log.error or "unknown_error"
    return f"Ch{log.chapter_number}: {stage} / {error}"


def generate_report(
    logs: list[ChapterRunLog],
    chapter_range: tuple[int, int] | None = None,
) -> str:
    """生成流式验证 markdown 报告.

    Args:
        logs: ChapterRunLog 列表（按章节排序）
        chapter_range: 可选的章节范围，用于标题
    """
    if not logs:
        return "# 流式验证报告\n\n无运行日志。\n"

    total = len(logs)
    successes = [log for log in logs if log.success]
    failed = [log for log in logs if not log.success]

    # 达标率：quality_gate_passed = True 且 success = True
    passed_logs = [
        log for log in logs if log.success and log.quality_gate_passed
    ]
    pass_rate = len(passed_logs) / total if total > 0 else 0.0

    # budget_used 统计（仅统计成功的章节）
    budgets = [
        log.budget_used for log in successes if log.budget_used is not None
    ]
    avg_budget = sum(budgets) / len(budgets) if budgets else 0.0
    over_budget_ratio = (
        sum(1 for b in budgets if b > 1.0) / len(budgets) if budgets else 0.0
    )

    # character_states / soft_refs
    char_counts = [
        log.character_states_loaded
        for log in successes
        if log.character_states_loaded is not None
    ]
    soft_counts = [
        log.soft_refs_loaded
        for log in successes
        if log.soft_refs_loaded is not None
    ]
    avg_char = sum(char_counts) / len(char_counts) if char_counts else 0.0
    avg_soft = sum(soft_counts) / len(soft_counts) if soft_counts else 0.0

    # revision 统计
    rev_rounds = [log.revision_rounds for log in successes]
    avg_rev = sum(rev_rounds) / len(rev_rounds) if rev_rounds else 0.0

    # emergency 统计
    emergency_count = sum(1 for log in successes if log.context_emergency)

    # Task 130: 候选硬门禁汇总
    gate_triggered_count = sum(1 for log in logs if log.gate_triggered)
    gate_mode_counts: dict[str, int] = {}
    gate_reason_counts: dict[str, int] = {}
    for log in logs:
        gate_mode_counts[log.gate_mode] = gate_mode_counts.get(log.gate_mode, 0) + 1
        for reason in (log.gate_reasons or []):
            gate_reason_counts[reason] = gate_reason_counts.get(reason, 0) + 1

    # 字数比例
    wc_ratios: list[float] = []
    for log in successes:
        r = _compute_word_count_ratio(log)
        if r is not None:
            wc_ratios.append(r)
    under_ratio = sum(1 for r in wc_ratios if r < 0.80) / len(wc_ratios) if wc_ratios else 0.0
    over_ratio = sum(1 for r in wc_ratios if r > 1.30) / len(wc_ratios) if wc_ratios else 0.0

    # 决策门选择
    start_ch, end_ch = chapter_range or (logs[0].chapter_number, logs[-1].chapter_number)
    if end_ch >= 101:
        dg = run_decision_gate_dg2(
            pass_rate=pass_rate,
            avg_budget=avg_budget,
            total=total,
            logs=logs,
        )
        dg_label = "DG-2"
    else:
        dg = run_decision_gate_dg1(
            pass_rate=pass_rate,
            avg_budget=avg_budget,
            over_budget_ratio=over_budget_ratio,
            under_ratio=under_ratio,
            over_ratio=over_ratio,
            avg_rev=avg_rev,
            emergency_count=emergency_count,
            total=total,
        )
        dg_label = "DG-1"

    gate_mode_distribution = ", ".join(
        f"{k}={v}" for k, v in sorted(gate_mode_counts.items())
    )

    lines = [
        f"# Ch{start_ch}-Ch{end_ch} 流式验证报告",
        "",
        "## 摘要",
        "",
        f"- **章节范围**: Ch{start_ch} ~ Ch{end_ch}",
        f"- **总章节数**: {total}",
        f"- **成功**: {len(successes)} | **失败**: {len(failed)}",
        f"- **达标率**: {pass_rate:.1%} ({len(passed_logs)}/{total})",
        f"- **budget_used 均值**: {avg_budget:.3f}",
        f"- **budget_used > 1.0 占比**: {over_budget_ratio:.1%}",
        f"- **character_states 均值**: {avg_char:.1f}",
        f"- **soft_refs 均值**: {avg_soft:.1f}",
        f"- **context_emergency 次数**: {emergency_count}",
        f"- **候选硬门禁触发**: {gate_triggered_count} 章",
        f"- **gate_mode 分布**: {gate_mode_distribution}",
        f"- **平均 revision 轮数**: {avg_rev:.1f}",
        f"- **字数不足率 (<0.80x)**: {under_ratio:.1%}",
        f"- **字数超标率 (>1.30x)**: {over_ratio:.1%}",
        "",
        f"## 决策门 {dg_label}",
        "",
        f"- **结果**: {_decision_label(dg)}",
        f"- **判定理由**: {dg.reason}",
        "",
    ]

    if dg_label == "DG-2":
        metrics = dg.metrics
        lines.extend(
            [
                "### DG-2 明细",
                "",
                f"- **运行完成率**: {metrics.get('completion_rate', 0.0):.1%} "
                f"({metrics.get('success_count', 0)}/{total})",
                f"- **budget 超限章节**: "
                f"{_format_chapters(metrics.get('over_budget_chapters', []))}",
                f"- **budget 缺失章节**: "
                f"{_format_chapters(metrics.get('missing_budget_chapters', []))}",
                f"- **ContextEmergency 章节**: "
                f"{_format_chapters(metrics.get('context_emergency_chapters', []))}",
                f"- **settlement validation failed 章节**: "
                f"{_format_chapters(metrics.get('settlement_failed_chapters', []))}",
                f"- **accepted 后缺 summary 章节**: "
                f"{_format_chapters(metrics.get('missing_summary_chapters', []))}",
                f"- **失败章节**: {_format_chapters(metrics.get('failed_chapters', []))}",
                f"- **失败原因**: {metrics.get('failure_reasons_text', '-')}",
                f"- **失败可恢复性**: {metrics.get('recoverability', 'unknown')}",
                "",
            ]
        )

    # Task 130: 候选硬门禁明细
    if gate_triggered_count > 0 or gate_mode_counts:
        lines.extend(
            [
                "## 候选硬门禁明细",
                "",
                f"- **触发章节数**: {gate_triggered_count}/{total}",
                f"- **模式分布**: {gate_mode_distribution}",
            ]
        )
        if gate_reason_counts:
            lines.append("- **触发原因**: ")
            for reason, count in sorted(
                gate_reason_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  - `{reason}`: {count} 次")
        else:
            lines.append("- **触发原因**: （未记录具体原因）")
        lines.append("")

    lines.extend(
        [
        "## 详细指标",
        "",
            "| 章节 | 成功 | budget_used | char_states | soft_refs | emergency | "
            "revision | QG通过 | settlement | summary | 失败原因 |",
            "|------|------|-------------|-------------|-----------|-----------|"
            "----------|--------|------------|---------|----------|",
        ]
    )

    for log in logs:
        lines.append(
            f"| Ch{log.chapter_number} | {'Y' if log.success else 'N'} | "
            f"{_format_float(log.budget_used)} | {_format_int(log.character_states_loaded)} | "
            f"{_format_int(log.soft_refs_loaded)} | {_format_bool(log.context_emergency)} | "
            f"{log.revision_rounds} | {_format_bool(log.quality_gate_passed)} | "
            f"{_format_bool(log.settlement_success)} | {_format_bool(log.summary_success)} | "
            f"{'-' if log.success else _failure_reason(log)} |"
        )

    lines.append("")
    return "\n".join(lines)


def run_decision_gate_dg1(
    pass_rate: float,
    avg_budget: float,
    over_budget_ratio: float,
    under_ratio: float,
    over_ratio: float,
    avg_rev: float,
    emergency_count: int,
    total: int,
) -> DecisionGateResult:
    """执行决策门 DG-1 判断.

    验收标准（全部满足才算通过）：
    - 达标率 >= 75%
    - 字数不足率 <= 5%
    - 字数超标率 <= 15%
    - budget_used 均值 <= 0.95
    - budget_used > 1.0 占比 <= 10%
    - 平均 revision 轮数 <= 1.5
    - context_emergency 次数 <= 5
    """
    checks = {
        "达标率 >= 75%": pass_rate >= 0.75,
        "字数不足率 <= 5%": under_ratio <= 0.05,
        "字数超标率 <= 15%": over_ratio <= 0.15,
        "budget_used 均值 <= 0.95": avg_budget <= 0.95,
        "budget_used > 1.0 占比 <= 10%": over_budget_ratio <= 0.10,
        "平均 revision 轮数 <= 1.5": avg_rev <= 1.5,
        "context_emergency 次数 <= 5": emergency_count <= 5,
    }

    failed_checks = [name for name, ok in checks.items() if not ok]
    if not failed_checks:
        return DecisionGateResult(
            passed=True,
            reason="所有验收指标均达标，推进 V5.1（Ch101-Ch150）。",
            metrics={"checks": checks},
        )

    return DecisionGateResult(
        passed=False,
        reason=f"未达标项: {', '.join(failed_checks)}。启动 Task 109-110 活跃信息池控制。",
        metrics={"checks": checks},
    )


def run_decision_gate_dg2(
    pass_rate: float,
    avg_budget: float,
    total: int,
    logs: list[ChapterRunLog] | None = None,
) -> DecisionGateResult:
    """执行决策门 DG-2 判断 (Ch101-Ch150).

    验收标准：
    - 运行完成率 >= 95%（90%-95% 且失败可诊断为条件通过）
    - 达标率 >= 70%
    - budget_used 均值 <= 1.00 且每章 <= 1.00
    - settlement validation failed 为 0
    - accepted 后 summary 完整
    """
    if logs is None:
        checks = {
            "达标率 >= 70%": pass_rate >= 0.70,
            "budget_used 均值 <= 1.00": avg_budget <= 1.00,
        }

        failed_checks = [name for name, ok in checks.items() if not ok]
        if not failed_checks:
            return DecisionGateResult(
                passed=True,
                reason="DG-2 核心指标达标，推进后续章节验证。",
                metrics={"checks": checks},
            )

        return DecisionGateResult(
            passed=False,
            reason=f"DG-2 未达标项: {', '.join(failed_checks)}。",
            metrics={"checks": checks},
        )

    successes = [log for log in logs if log.success]
    failed_logs = [log for log in logs if not log.success]
    success_count = len(successes)
    completion_rate = success_count / total if total > 0 else 0.0
    over_budget_chapters = [
        log.chapter_number
        for log in successes
        if log.budget_used is not None and log.budget_used > 1.0
    ]
    missing_budget_chapters = [
        log.chapter_number for log in successes if log.budget_used is None
    ]
    context_emergency_chapters = [
        log.chapter_number for log in logs if log.context_emergency
    ]
    settlement_failed_chapters = [
        log.chapter_number
        for log in successes
        if (not log.settlement_success) or log.settlement_needs_human_review
    ]
    missing_summary_chapters = [
        log.chapter_number
        for log in successes
        if log.settlement_success and log.summary_success is not True
    ]
    failed_chapters = [log.chapter_number for log in failed_logs]
    failure_reasons = [_failure_reason(log) for log in failed_logs]
    failures_have_reasons = all(
        log.error is not None or log.error_stage is not None for log in failed_logs
    )

    checks = {
        "运行完成率 >= 95%": completion_rate >= 0.95,
        "达标率 >= 70%": pass_rate >= 0.70,
        "budget_used 均值 <= 1.00": avg_budget <= 1.00,
        "每章 budget_used <= 1.00 且有记录": (
            not over_budget_chapters and not missing_budget_chapters
        ),
        "ContextEmergency 次数 == 0": not context_emergency_chapters,
        "settlement validation failed == 0": not settlement_failed_chapters,
        "accepted 后 summary 100% 完整": not missing_summary_chapters,
        "失败章节有原因": failures_have_reasons,
    }
    metrics = {
        "checks": checks,
        "completion_rate": completion_rate,
        "success_count": success_count,
        "over_budget_chapters": over_budget_chapters,
        "missing_budget_chapters": missing_budget_chapters,
        "context_emergency_chapters": context_emergency_chapters,
        "settlement_failed_chapters": settlement_failed_chapters,
        "missing_summary_chapters": missing_summary_chapters,
        "failed_chapters": failed_chapters,
        "failure_reasons": failure_reasons,
        "failure_reasons_text": "; ".join(failure_reasons) or "-",
        "recoverability": "blocked",
    }

    failed_checks = [name for name, ok in checks.items() if not ok]
    if not failed_checks:
        metrics["recoverability"] = "no_failures"
        return DecisionGateResult(
            passed=True,
            reason="DG-2 核心指标达标，推进后续章节验证。",
            metrics=metrics,
        )

    conditionally_recoverable = (
        completion_rate >= 0.90
        and pass_rate >= 0.60
        and avg_budget <= 1.00
        and not over_budget_chapters
        and not missing_budget_chapters
        and not settlement_failed_chapters
        and not missing_summary_chapters
        and failures_have_reasons
    )
    if conditionally_recoverable:
        metrics["recoverability"] = "reviewable"
        return DecisionGateResult(
            passed=False,
            status="conditional",
            reason=f"DG-2 条件通过项需复核: {', '.join(failed_checks)}。",
            metrics=metrics,
        )

    return DecisionGateResult(
        passed=False,
        reason=f"DG-2 未达标项: {', '.join(failed_checks)}。",
        metrics=metrics,
    )


def write_report(report_md: str, run_id: str, output_dir: Path | None = None) -> Path:
    """将报告写入文件."""
    run_id = validate_run_id(run_id)
    out = output_dir or Path("logs/reports")
    out.mkdir(parents=True, exist_ok=True)
    filepath = out / f"report-{run_id}.md"
    filepath.write_text(report_md, encoding="utf-8")
    return filepath
