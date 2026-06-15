"""Task 105: Ch51-Ch100 流式验证报告生成器.

一键读取 JSONL 运行日志，生成 markdown 报告并触发决策门 DG-1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from songyan.models.run_log import ChapterRunLog

_LOGS_DIR = Path("logs/chapter_runs")


class DecisionGateResult:
    """决策门结果 (DG-1 / DG-2)."""

    def __init__(self, passed: bool, reason: str, metrics: dict[str, Any]) -> None:
        self.passed = passed
        self.reason = reason
        self.metrics = metrics


def read_run_logs(run_id: str) -> list[ChapterRunLog]:
    """从 JSONL 读取指定 run_id 的运行日志."""
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
        return round(log.word_count / target, 3)
    return None


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
        f"- **平均 revision 轮数**: {avg_rev:.1f}",
        f"- **字数不足率 (<0.80x)**: {under_ratio:.1%}",
        f"- **字数超标率 (>1.30x)**: {over_ratio:.1%}",
        "",
        f"## 决策门 {dg_label}",
        "",
        f"- **结果**: {'✅ 通过' if dg.passed else '❌ 未通过'}",
        f"- **判定理由**: {dg.reason}",
        "",
        "## 详细指标",
        "",
        "| 章节 | 成功 | budget_used | char_states | soft_refs | emergency | revision | QG通过 |",
        "|------|------|-------------|-------------|-----------|-----------|----------|--------|",
    ]

    for log in logs:
        lines.append(
            f"| Ch{log.chapter_number} | {'Y' if log.success else 'N'} | "
            f"{log.budget_used or '-':.3f} | {log.character_states_loaded or '-'} | "
            f"{log.soft_refs_loaded or '-'} | {'Y' if log.context_emergency else 'N'} | "
            f"{log.revision_rounds} | {'Y' if log.quality_gate_passed else 'N'} |"
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
) -> DecisionGateResult:
    """执行决策门 DG-2 判断 (Ch101-Ch150).

    验收标准（核心指标通过即可推进）：
    - 达标率 >= 70%
    - budget_used 均值 <= 1.00
    """
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


def write_report(report_md: str, run_id: str, output_dir: Path | None = None) -> Path:
    """将报告写入文件."""
    out = output_dir or Path("logs/reports")
    out.mkdir(parents=True, exist_ok=True)
    filepath = out / f"report-{run_id}.md"
    filepath.write_text(report_md, encoding="utf-8")
    return filepath
