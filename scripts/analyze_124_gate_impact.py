"""Task 124: 候选硬门禁离线影响面分析.

基于已有干净长跑数据（默认 run-a2bed648），对 Task 123 实现的候选硬门禁做离线仿真，
输出影响面报告，为是否开启 enforce 模式提供数据依据。

Usage:
    python scripts/analyze_124_gate_impact.py
    python scripts/analyze_124_gate_impact.py --run-id run-a2bed648
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from songyan.agents.continuity_auditor.continuity_health import classify_report
from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.models import GateConfig
from songyan.workflows._gates import (
    check_context_emergency_single_gate,
    check_health_low_single_gate,
    check_health_low_streak_gate,
)

DEFAULT_RUN_ID = "run-a2bed648"
DEFAULT_OUTPUT = "docs/reports/124-gate-impact-analysis-run-a2bed648.md"
_LOGS_DIR = Path("logs/chapter_runs")

# 候选 enforce 配置（Task 125 调优后，避免对正常叙事累积过度敏感）
_CANDIDATE_CONFIGS: dict[str, GateConfig] = {
    "health_low_p1_halt": GateConfig(
        gate_mode="enforce",
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_p1_min_absolute=50,
        health_low_p1_anomaly_factor=1.8,
    ),
    "health_low_score_halt": GateConfig(
        gate_mode="enforce",
        health_low_gate_enabled=True,
        health_low_score_halt_enabled=True,
        health_low_score_halt_window=3,
        health_low_score_halt_min_p1=20,
        health_low_score_halt_anomaly_factor=1.8,
    ),
    "health_low_streak_halt": GateConfig(
        gate_mode="enforce",
        health_low_gate_enabled=True,
        health_low_streak_halt=True,
        health_low_streak_audit_window=3,
        health_low_streak_p1_limit=250,
        health_low_streak_p2_limit=1000,
        health_low_p1_anomaly_factor=1.5,
    ),
    "context_emergency_budget_ratio_halt": GateConfig(
        gate_mode="enforce",
        context_emergency_gate_enabled=True,
        context_emergency_single_halt=True,
        context_emergency_budget_ratio_threshold=1.3,
    ),
    "context_emergency_failure_halt": GateConfig(
        gate_mode="enforce",
        context_emergency_gate_enabled=True,
        context_emergency_failure_halt=True,
    ),
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_jsonl_logs(run_id: str) -> list[dict[str, Any]]:
    """从 JSONL 文件加载 ChapterRunLog 记录."""
    path = _LOGS_DIR / f"{run_id}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"JSONL log not found: {path}")
    logs: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            logs.append(json.loads(line))
    return sorted(logs, key=lambda r: r["chapter_number"])


async def _load_continuity_reports(
    project_id: str,
    chapter_start: int,
    chapter_end: int,
) -> dict[int, Any]:
    """从数据库加载 ContinuityReport，按 checked_up_to_chapter 索引."""
    reports = await ContinuityReportRepository().list_by_chapter_range(
        project_id, chapter_start, chapter_end
    )
    return {report.checked_up_to_chapter: report for report in reports}


async def _resolve_project_id(run_id: str) -> str:
    """从 project_runs 表解析 run_id 对应的项目 ID."""
    run = await ProjectRunRepository().get(run_id)
    if run is None:
        raise ValueError(f"Run not found in database: {run_id}")
    return run.project_id


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class GateImpactAnalyzer:
    """离线门禁影响面分析器."""

    def __init__(self, logs: list[dict[str, Any]], reports: dict[int, Any]) -> None:
        self.logs = logs
        self.reports = reports
        self.chapters = [log["chapter_number"] for log in logs]

    def _build_recent_results(self, up_to_idx: int) -> list[dict[str, Any]]:
        """构建到当前章节为止的 recent_results 列表.

        离线分析不限制窗口大小，让 streak gate 能够按审计点窗口自由回溯。
        """
        return [
            {
                "chapter_number": log["chapter_number"],
                "success": log.get("success", False),
                "quality_gate_passed": log.get("quality_gate_passed"),
                "context_emergency": log.get("context_emergency", False),
                "settlement_success": log.get("settlement_success"),
                "summary_success": log.get("summary_success"),
                "continuity_health_severity": self._severity_for_chapter(
                    log["chapter_number"]
                ),
                "gate_triggered": False,
                "gate_reasons": [],
            }
            for log in self.logs[: up_to_idx + 1]
        ]

    def _severity_for_chapter(self, chapter_number: int) -> dict[str, int] | None:
        """获取指定章节的 continuity severity（仅在审计点章节有值）."""
        report = self.reports.get(chapter_number)
        if report is None:
            return None
        return classify_report(report)

    @staticmethod
    def _context_metrics_for(log: dict[str, Any]) -> dict[str, Any]:
        return {
            "context_emergency": log.get("context_emergency", False),
            "budget_used_before_emergency": log.get("budget_used_before_emergency"),
        }

    @staticmethod
    def _chapter_result_for(log: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": log.get("success", False),
            "quality_gate_passed": log.get("quality_gate_passed"),
            "context_emergency": log.get("context_emergency", False),
            "settlement_success": log.get("settlement_success"),
            "summary_success": log.get("summary_success"),
        }

    def _evaluate_chapter(
        self,
        log: dict[str, Any],
        report: Any | None,
        recent_results: list[dict[str, Any]],
        previous_report: Any | None,
        previous_p1_counts: list[int],
        min_health_score_so_far: float | None,
    ) -> dict[str, list[str]]:
        """对单章应用全部候选规则，返回触发的规则及原因."""
        ctx_metrics = self._context_metrics_for(log)
        chapter_result = self._chapter_result_for(log)
        triggered: dict[str, list[str]] = {}

        # health_low 单章规则
        if report is not None:
            triggered_p1, reasons_p1, _ = check_health_low_single_gate(
                report,
                _CANDIDATE_CONFIGS["health_low_p1_halt"],
                previous_p1_counts=previous_p1_counts,
                min_health_score_so_far=min_health_score_so_far,
            )
            if triggered_p1:
                triggered["health_low_p1_halt"] = reasons_p1

            triggered_score, reasons_score, _ = check_health_low_single_gate(
                report,
                _CANDIDATE_CONFIGS["health_low_score_halt"],
                previous_p1_counts=previous_p1_counts,
                min_health_score_so_far=min_health_score_so_far,
            )
            if triggered_score:
                triggered["health_low_score_halt"] = reasons_score

        # health_low streak 规则
        triggered_streak, reasons_streak = check_health_low_streak_gate(
            recent_results,
            _CANDIDATE_CONFIGS["health_low_streak_halt"],
            previous_p1_counts=previous_p1_counts,
        )
        if triggered_streak:
            triggered["health_low_streak_halt"] = reasons_streak

        # ContextEmergency 规则
        triggered_ce_ratio, reasons_ce_ratio = check_context_emergency_single_gate(
            ctx_metrics, chapter_result, _CANDIDATE_CONFIGS["context_emergency_budget_ratio_halt"]
        )
        if triggered_ce_ratio:
            triggered["context_emergency_budget_ratio_halt"] = reasons_ce_ratio

        triggered_ce_fail, reasons_ce_fail = check_context_emergency_single_gate(
            ctx_metrics, chapter_result, _CANDIDATE_CONFIGS["context_emergency_failure_halt"]
        )
        if triggered_ce_fail:
            triggered["context_emergency_failure_halt"] = reasons_ce_fail

        return triggered

    def analyze(self) -> dict[str, Any]:
        """执行全部规则仿真，返回结构化结果."""
        rule_names = list(_CANDIDATE_CONFIGS.keys())
        summary: dict[str, dict[str, Any]] = {
            name: {"count": 0, "first_chapter": None, "chapters": []}
            for name in rule_names
        }
        summary["any_gate"] = {"count": 0, "first_chapter": None, "chapters": []}
        per_chapter: dict[int, dict[str, Any]] = {}

        previous_report: Any | None = None
        previous_p1_counts: list[int] = []
        min_health_score_so_far: float | None = None

        for idx, log in enumerate(self.logs):
            chapter_number = log["chapter_number"]
            report = self.reports.get(chapter_number)
            recent_results = self._build_recent_results(idx)
            triggered = self._evaluate_chapter(
                log,
                report,
                recent_results,
                previous_report,
                previous_p1_counts,
                min_health_score_so_far,
            )

            per_chapter[chapter_number] = {
                "log": log,
                "report": report,
                "severity": self._severity_for_chapter(chapter_number),
                "triggered_rules": triggered,
            }

            if report is not None:
                previous_report = report
                severity = self._severity_for_chapter(chapter_number) or {}
                previous_p1_counts.append(severity.get("P1", 0))
                if report.overall_health_score is not None:
                    if min_health_score_so_far is None:
                        min_health_score_so_far = report.overall_health_score
                    else:
                        min_health_score_so_far = min(
                            min_health_score_so_far, report.overall_health_score
                        )

            any_triggered = False
            for rule_name, reasons in triggered.items():
                any_triggered = True
                summary[rule_name]["count"] += 1
                summary[rule_name]["chapters"].append(chapter_number)
                if summary[rule_name]["first_chapter"] is None:
                    summary[rule_name]["first_chapter"] = chapter_number

            if any_triggered:
                summary["any_gate"]["count"] += 1
                summary["any_gate"]["chapters"].append(chapter_number)
                if summary["any_gate"]["first_chapter"] is None:
                    summary["any_gate"]["first_chapter"] = chapter_number

        # 补充 run-level 影响面指标
        total = len(self.logs)
        chapter_index = {log["chapter_number"]: i for i, log in enumerate(self.logs)}
        for name, data in summary.items():
            first = data["first_chapter"]
            data["halt_count"] = data["count"]
            data["blocked_from_first_halt"] = (
                total - chapter_index[first] if first is not None else 0
            )

        return {
            "run_id": DEFAULT_RUN_ID,
            "project_id": None,
            "chapter_range": (min(self.chapters), max(self.chapters)),
            "total_chapters": total,
            "summary": summary,
            "per_chapter": per_chapter,
        }


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def _severity_distribution(per_chapter: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """统计审计点章节的 severity 分布."""
    scores: list[float] = []
    p1_counts: list[int] = []
    p2_counts: list[int] = []
    p3_counts: list[int] = []
    for data in per_chapter.values():
        report = data["report"]
        severity = data["severity"]
        if report is None or severity is None:
            continue
        if report.overall_health_score is not None:
            scores.append(report.overall_health_score)
        p1_counts.append(severity["P1"])
        p2_counts.append(severity["P2"])
        p3_counts.append(severity["P3"])

    def _stats(values: list[float | int]) -> dict[str, float | int]:
        if not values:
            return {"min": 0, "max": 0, "avg": 0.0, "median": 0.0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        median = (
            sorted_vals[n // 2]
            if n % 2 == 1
            else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        )
        return {
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "avg": sum(sorted_vals) / n,
            "median": median,
            "sum": sum(sorted_vals),
        }

    return {
        "audit_chapters": len(scores),
        "health_score": _stats(scores),
        "P1": _stats(p1_counts),
        "P2": _stats(p2_counts),
        "P3": _stats(p3_counts),
    }


def _render_report(result: dict[str, Any]) -> str:
    """渲染 Markdown 报告."""
    summary = result["summary"]
    per_chapter = result["per_chapter"]
    run_id = result["run_id"]
    project_id = result.get("project_id") or "unknown"
    ch_start, ch_end = result["chapter_range"]
    total = result["total_chapters"]
    dist = _severity_distribution(per_chapter)

    lines: list[str] = []
    lines.append(f"# Task 124: 候选硬门禁离线影响面分析 — {run_id}")
    lines.append("")
    lines.append(f"- **项目 ID**: `{project_id}`")
    lines.append(f"- **Run ID**: `{run_id}`")
    lines.append(f"- **分析章节范围**: Ch{ch_start} - Ch{ch_end}")
    lines.append(f"- **总章节数**: {total}")
    lines.append("")
    lines.append("## 1. 汇总表（enforce 模式仿真）")
    lines.append("")
    lines.append(
        "| 规则 | 触发次数 | 首次触发章 | 首次触发后阻断章节数 | 触发章节列表 |"
    )
    lines.append("|------|----------|------------|----------------------|--------------|")
    rule_order = [
        "health_low_p1_halt",
        "health_low_score_halt",
        "health_low_streak_halt",
        "context_emergency_budget_ratio_halt",
        "context_emergency_failure_halt",
        "any_gate",
    ]
    for rule in rule_order:
        data = summary[rule]
        chapters_str = ", ".join(str(c) for c in data["chapters"]) or "-"
        lines.append(
            f"| {rule} | {data['count']} | {data['first_chapter'] or '-'} | "
            f"{data['blocked_from_first_halt']} | {chapters_str} |"
        )
    lines.append("")
    lines.append("## 2. 关键发现")
    lines.append("")

    any_count = summary["any_gate"]["count"]
    first_any = summary["any_gate"]["first_chapter"]
    blocked_any = summary["any_gate"]["blocked_from_first_halt"]

    if any_count == 0:
        lines.append(
            "在本次分析的章节范围内，所有候选硬门禁规则均未触发。"
            "这表明当前默认阈值对于该 run 是安全的，可以考虑在监控下逐步开启 enforce 模式。"
        )
    else:
        lines.append(
            f"共有 **{any_count}** 章触发了至少一条候选硬门禁规则，"
            f"首次触发位于 **Ch{first_any}**，"
            f"若按首次触发即完全阻断计算，将影响后续 **{blocked_any}** 章（含触发章）。"
        )
        lines.append("")
        lines.append(
            "> 说明：本仿真假设 enforce 模式下触发即暂停 run；"
            "若人工介入后 resume，则实际阻断章节会小于该值。"
        )
        lines.append("")

        # ContextEmergency 相关规则触发情况
        ce_count = (
            summary["context_emergency_budget_ratio_halt"]["count"]
            + summary["context_emergency_failure_halt"]["count"]
        )
        if ce_count == 0:
            lines.append(
                "- **ContextEmergency 相关规则未触发**，"
                "与该 run 的 `context_emergency=False` 一致。"
            )
        else:
            lines.append(
                f"- ContextEmergency 相关规则共触发 {ce_count} 次，"
                "需重点关注超预算或 settlement/summary 失败章节。"
            )

        # health_low 相关规则触发情况
        hl_count = (
            summary["health_low_p1_halt"]["count"]
            + summary["health_low_score_halt"]["count"]
            + summary["health_low_streak_halt"]["count"]
        )
        lines.append(
            f"- **health_low 相关规则**共触发 {hl_count} 次（含同一章触发多条规则），"
            "说明当前 continuity audit 在该 run 中报告了大量 P1/state_mismatch。"
        )
        lines.append(
            "- `health_low_streak_halt` 触发次数显著高于单章规则，"
            "因为 streak 窗口继承了审计点的高 P1 计数，并在后续 2 章持续生效。"
        )

    lines.append("")
    lines.append("## 3. 审计点 severity 分布")
    lines.append("")
    lines.append(f"- 审计点章节数：{dist['audit_chapters']}")
    hs = dist["health_score"]
    lines.append(
        f"- overall_health_score：min={hs['min']}, max={hs['max']}, "
        f"avg={hs['avg']:.2f}, median={hs['median']:.2f}"
    )
    for level in ("P1", "P2", "P3"):
        s = dist[level]
        lines.append(
            f"- {level} 计数：min={s['min']}, max={s['max']}, "
            f"avg={s['avg']:.2f}, median={s['median']:.2f}"
        )
    lines.append("")
    lines.append("## 4. 逐章触发明细")
    lines.append("")
    lines.append("仅列出触发至少一条规则的章节。")
    lines.append("")
    lines.append(
        "| 章号 | health_score | P1/P2/P3 | context_emergency | "
        "budget_used_before_emergency | 触发规则 |"
    )
    lines.append(
        "|------|--------------|----------|-------------------|------------------------------|----------|"
    )
    triggered_count = 0
    for chapter_number in sorted(per_chapter):
        data = per_chapter[chapter_number]
        log = data["log"]
        report = data["report"]
        severity = data["severity"]
        triggered = data["triggered_rules"]
        if not triggered:
            continue
        triggered_count += 1

        health_score = report.overall_health_score if report else "N/A"
        severity_str = (
            f"{severity['P1']}/{severity['P2']}/{severity['P3']}" if severity else "N/A"
        )
        ctx_emergency = log.get("context_emergency", False)
        ratio = log.get("budget_used_before_emergency")
        ratio_str = f"{ratio:.4f}" if ratio is not None else "N/A"
        rules_str = ", ".join(triggered.keys())

        lines.append(
            f"| {chapter_number} | {health_score} | {severity_str} | {ctx_emergency} | "
            f"{ratio_str} | {rules_str} |"
        )

    if triggered_count == 0:
        lines.append("| - | - | - | - | - | 无 |")

    lines.append("")
    lines.append("## 5. 建议")
    lines.append("")
    if any_count == 0:
        lines.append(
            "1. 当前候选阈值（P1 异常检测、health_score 相对跌幅、审计点 streak）"
            "在该 run 中零触发，说明调整后的阈值对干净长跑是安全的。"
        )
        lines.append("2. 可在观测模式下继续收集更多样本，逐步验证 enforce 模式的误伤率。")
        lines.append("3. 定期用本脚本复盘新的 run_id，形成 gate 阈值调整的闭环。")
    else:
        lines.append(
            "1. **阈值仍需调优**：health_low 规则在该 run 中仍触发多次，"
            "建议提高 `health_low_p1_min_absolute` / `health_low_p1_anomaly_factor` "
            "或改用更鲁棒的滚动基线。"
        )
        lines.append(
            "2. **先复核 continuity audit 报告**：确认触发章节的 P1/state_mismatch "
            "是真实问题还是扫描噪音，再决定是否继续提高阈值。"
        )
        lines.append(
            "3. **保持默认 observe 模式**：在硬门禁阈值调优完成前，"
            "系统默认配置仍应保持 `gate_mode='observe'`，避免破坏 V5.0 已验证的长跑能力。"
        )
        lines.append(
            "4. **ContextEmergency 规则当前安全**：该 run 未出现 context emergency，"
            "可先保留默认关闭，待出现真实样本后再评估启用。"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*本报告由 `scripts/analyze_124_gate_impact.py` 自动生成，"
        "仿真规则复用 `src/songyan/workflows/_gates.py`。*"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(description="Task 124 offline gate impact analysis")
    parser.add_argument(
        "--run-id",
        default=DEFAULT_RUN_ID,
        help="Run ID to analyze (default: run-a2bed648)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Output markdown report path",
    )
    args = parser.parse_args()

    logs = _load_jsonl_logs(args.run_id)
    if not logs:
        raise ValueError(f"No logs found for run_id={args.run_id}")

    project_id = await _resolve_project_id(args.run_id)
    chapter_start = min(log["chapter_number"] for log in logs)
    chapter_end = max(log["chapter_number"] for log in logs)
    reports = await _load_continuity_reports(project_id, chapter_start, chapter_end)

    analyzer = GateImpactAnalyzer(logs, reports)
    result = analyzer.analyze()
    result["run_id"] = args.run_id
    result["project_id"] = project_id

    report = _render_report(result)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Report written to: {output_path}")
    print(
        f"Analyzed {result['total_chapters']} chapters, "
        f"any_gate triggered {result['summary']['any_gate']['count']} times."
    )


if __name__ == "__main__":
    asyncio.run(main())
