"""Task 139a: 离线模拟 enforce 模式 gate 触发，输出审计报告.

数据来源:
- Ch1-Ch30: `.tmp/task138n_ch1_ch30_rerun.db` 中的 continuity_reports 表.
- Ch31-Ch50: `logs/chapter_runs/run-01a32b97.jsonl`.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import aiosqlite

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.agents.continuity_auditor.continuity_health import classify_report
from songyan.models.continuity import (
    ContinuityReport,
    OrphanedSetting,
)
from songyan.models.gate_config import GateConfig
from songyan.workflows._gates import (
    check_context_emergency_single_gate,
    check_health_low_single_gate,
    check_health_low_streak_gate,
)

DB_PATH = Path(".tmp/task138n_ch1_ch30_rerun.db")
CH1_CH30_JSONL_PATH = Path("logs/chapter_runs/run-ba25db19.jsonl")
CH31_CH50_JSONL_PATH = Path("logs/chapter_runs/run-01a32b97.jsonl")
REPORT_PATH = Path("docs/reports/task-139a-enforce-gate-config-audit.md")


def _severity_report(
    overall_health_score: float | None,
    severity: dict | None,
) -> ContinuityReport:
    """用 severity 计数构造一个最小 ContinuityReport，用于离线 gate 模拟."""
    severity = severity or {}
    orphaned: list[OrphanedSetting] = []
    for category in ("critical", "recurring", "background"):
        key = {"critical": "P1", "recurring": "P2", "background": "P3"}[category]
        for _ in range(severity.get(key, 0)):
            orphaned.append(
                OrphanedSetting(
                    tracking_id="dummy",
                    setting_key="dummy",
                    setting_name="dummy",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=1,
                    chapters_since_mention=1,
                    category=category,
                )
            )
    score = overall_health_score if overall_health_score is not None else 10.0
    return ContinuityReport(
        report_id="dummy",
        project_id="dummy",
        checked_up_to_chapter=1,
        orphaned_settings=orphaned,
        overall_health_score=score,
    )


async def _load_continuity_reports(project_id: str) -> list[dict]:
    """从 Task 138n DB 加载指定项目的 continuity report，按章节去重保留最新."""
    rows: list[dict] = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                checked_up_to_chapter,
                overall_health_score,
                orphaned_settings,
                state_mismatches,
                forgotten_items,
                overdue_foreshadowings,
                created_at
            FROM continuity_reports
            WHERE project_id = ?
            ORDER BY checked_up_to_chapter, created_at DESC
            """,
            (project_id,),
        )
        seen: set[int] = set()
        async for row in cursor:
            ch = row["checked_up_to_chapter"]
            if ch in seen:
                continue
            seen.add(ch)
            rows.append(dict(row))
    return rows


def _load_jsonl(path: Path) -> list[dict]:
    """加载 JSONL 运行日志."""
    logs: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            logs.append(json.loads(line))
    return logs


def _report_from_db_row(row: dict) -> ContinuityReport:
    """从数据库行构造 ContinuityReport."""
    def _load(field: str) -> list:
        raw = row.get(field)
        if raw is None:
            return []
        if isinstance(raw, str):
            return json.loads(raw)
        return list(raw)

    orphaned = _load("orphaned_settings")
    state_mismatches = _load("state_mismatches")
    forgotten_items = _load("forgotten_items")
    overdue_foreshadowings = _load("overdue_foreshadowings")

    score = row["overall_health_score"]
    if score is None:
        score = 10.0

    return ContinuityReport(
        report_id="dummy",
        project_id="dummy",
        checked_up_to_chapter=row["checked_up_to_chapter"],
        orphaned_settings=orphaned,
        state_mismatches=state_mismatches,
        forgotten_items=forgotten_items,
        overdue_foreshadowings=overdue_foreshadowings,
        overall_health_score=score,
    )


def _chapter_result_from_log(log: dict) -> dict:
    """从 JSONL 日志构造 chapter_result."""
    return {
        "chapter_number": log["chapter_number"],
        "success": log.get("success"),
        "quality_gate_passed": log.get("quality_gate_passed"),
        "settlement_success": log.get("settlement_success"),
        "summary_success": log.get("summary_success"),
        "context_emergency": log.get("context_emergency", False),
        "continuity_health_severity": log.get("continuity_health_severity"),
    }


def _context_metrics_from_log(log: dict) -> dict:
    return {
        "context_emergency": log.get("context_emergency", False),
        "budget_used_before_emergency": log.get("budget_used_before_emergency"),
    }


def _simulate_qg_fail_streak(results: list[dict]) -> tuple[bool, str | None]:
    """模拟连续 3 章 QG 失败触发 AutoHalt."""
    qg_known = [r for r in results if r.get("quality_gate_passed") is not None]
    if len(qg_known) < 3:
        return False, None
    qg_fails = sum(1 for r in qg_known[-3:] if not r["quality_gate_passed"])
    if qg_fails >= 3:
        ch_start = qg_known[-3]["chapter_number"]
        ch_end = qg_known[-1]["chapter_number"]
        return True, f"quality_gate_fail_streak: Ch{ch_start}-Ch{ch_end}"
    return False, None


def _simulate_ce_degraded_streak(results: list[dict]) -> tuple[bool, str | None]:
    """模拟连续 3 章 ContextEmergency 且伴随降级触发 AutoHalt."""
    if len(results) < 3:
        return False, None
    window = results[-3:]
    emergencies = sum(1 for r in window if r.get("context_emergency"))
    if emergencies < 3:
        return False, None
    degraded = any(
        not r.get("success")
        or not r.get("quality_gate_passed", True)
        or not r.get("settlement_success", True)
        or not r.get("summary_success", True)
        for r in window
    )
    if degraded:
        ch_start = window[0]["chapter_number"]
        ch_end = window[-1]["chapter_number"]
        return True, f"context_emergency_degraded_streak: Ch{ch_start}-Ch{ch_end}"
    return False, None


def _simulate_enforce_gates(
    logs: list[dict],
    report_lookup: dict[int, ContinuityReport],
) -> list[dict]:
    """逐章模拟 enforce 模式下的 gate 触发."""
    config = GateConfig.for_mode("enforce")
    previous_p1_counts: list[int] = []
    min_health_score_so_far: float | None = None
    recent_results: list[dict] = []
    triggers: list[dict] = []

    for log in logs:
        chapter_number = log["chapter_number"]
        report = report_lookup.get(chapter_number)
        context_metrics = _context_metrics_from_log(log)
        chapter_result = _chapter_result_from_log(log)

        if report is not None:
            health_report = report
        else:
            health_report = _severity_report(
                log.get("continuity_health_score"),
                log.get("continuity_health_severity"),
            )

        triggered, reasons, updated_min_score = check_health_low_single_gate(
            health_report,
            config,
            previous_p1_counts=previous_p1_counts,
            min_health_score_so_far=min_health_score_so_far,
        )

        if report is not None:
            severity = classify_report(report)
            previous_p1_counts.append(severity["P1"])
        elif log.get("continuity_health_severity"):
            previous_p1_counts.append(log["continuity_health_severity"].get("P1", 0))

        min_health_score_so_far = updated_min_score

        streak_triggered, streak_reasons = check_health_low_streak_gate(
            recent_results, config, previous_p1_counts=previous_p1_counts
        )
        if streak_triggered:
            reasons.extend(streak_reasons)

        ce_triggered, ce_reasons = check_context_emergency_single_gate(
            context_metrics, chapter_result, config
        )
        if ce_triggered:
            reasons.extend(ce_reasons)

        qg_triggered, qg_reason = _simulate_qg_fail_streak(
            recent_results + [chapter_result]
        )
        if qg_triggered:
            reasons.append(qg_reason)

        ce_streak_triggered, ce_streak_reason = _simulate_ce_degraded_streak(
            recent_results + [chapter_result]
        )
        if ce_streak_triggered:
            reasons.append(ce_streak_reason)

        record = {
            "chapter_number": chapter_number,
            "gate_triggered": bool(reasons),
            "gate_reasons": reasons,
            "continuity_health_score": log.get("continuity_health_score"),
            "continuity_health_severity": log.get("continuity_health_severity"),
            "context_emergency": log.get("context_emergency", False),
            "quality_gate_passed": log.get("quality_gate_passed"),
            "success": log.get("success"),
        }
        triggers.append(record)
        recent_results.append(chapter_result)

    return triggers


def _generate_report(triggers: list[dict]) -> str:
    """生成 markdown 审计报告."""
    total = len(triggers)
    triggered = [t for t in triggers if t["gate_triggered"]]
    reason_counter: dict[str, int] = {}
    for t in triggered:
        for reason in t["gate_reasons"]:
            key = reason.split(":")[0]
            reason_counter[key] = reason_counter.get(key, 0) + 1

    lines = [
        "# Task 139a：V5.2 Enforce 门禁配置最终审计报告",
        "",
        "> 数据来源:",
        "> - Ch1-Ch30: `.tmp/task138n_ch1_ch30_rerun.db` (Task 138n 重跑数据)",
        "> - Ch31-Ch50: `logs/chapter_runs/run-01a32b97.jsonl` (Task 138o 延续验证数据)",
        "> - 模拟配置: `GateConfig.for_mode('enforce')`",
        "",
        "## 总体结论",
        "",
        f"- 分析章节数: {total}",
        f"- 触发 gate 章节数: {len(triggered)}",
        f"- 触发比例: {len(triggered)/total*100:.1f}%",
        "",
        "## 各 gate 触发统计",
        "",
        "| Gate 类型 | 触发次数 |",
        "|-----------|----------|",
    ]
    for key, count in sorted(reason_counter.items()):
        lines.append(f"| {key} | {count} |")
    if not reason_counter:
        lines.append("| (无) | 0 |")

    lines.extend([
        "",
        "## 逐章触发详情",
        "",
        "| 章节 | gate_triggered | 触发原因 | health_score | QG | CE |",
        "|------|----------------|----------|--------------|----|----|",
    ])
    for t in triggers:
        reasons = "; ".join(t["gate_reasons"]) if t["gate_reasons"] else "-"
        ch = t["chapter_number"]
        score = t["continuity_health_score"]
        qg = t["quality_gate_passed"]
        ce = t["context_emergency"]
        lines.append(
            f"| {ch} | {t['gate_triggered']} | {reasons} | "
            f"{score} | {qg} | {ce} |"
        )

    lines.extend([
        "",
        "## 阈值审计说明",
        "",
        "本次离线模拟使用 `GateConfig.for_mode('enforce')` 的默认阈值:",
        "",
        "- `health_low_p1_halt`: 任意 P1 触发（经 P1 异常检测保护）。",
        "- `health_low_score_halt`: 历史新低 + P1 超过近期中位数 1.8 倍且 ≥20。",
        "- `health_low_streak_halt`: 连续 3 章审计点窗口内 P1≥1 或 P2≥2。",
        (
            "- `context_emergency_single_halt`: ContextEmergency 且 "
            "`budget_used_before_emergency ≥ 1.3`。"
        ),
        "- `context_emergency_failure_halt`: ContextEmergency 导致 settlement/summary 失败。",
        "- `quality_gate_fail_streak`: 连续 3 章 QG 失败。",
        "- `context_emergency_degraded_streak`: 连续 3 章 ContextEmergency 且伴随降级。",
        "",
        "## 结论",
        "",
    ])
    if not triggered:
        lines.append(
            "离线模拟结果显示，当前 enforce 默认配置在 Ch1-Ch50 历史数据上 "
            "**零误触发**，满足进入 Task 139b 实跑验证的条件。"
        )
    else:
        lines.append(
            "离线模拟结果显示，当前 enforce 默认配置在 Ch1-Ch50 历史数据上 "
            f"触发 {len(triggered)} 次 gate。需根据触发原因评估是否为误触发，"
            "再决定是否调整阈值或进入 Task 139b。"
        )

    lines.append("")
    return "\n".join(lines)


async def main() -> None:
    """主入口."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"数据库不存在: {DB_PATH}")
    if not CH1_CH30_JSONL_PATH.exists():
        raise FileNotFoundError(f"JSONL 不存在: {CH1_CH30_JSONL_PATH}")
    if not CH31_CH50_JSONL_PATH.exists():
        raise FileNotFoundError(f"JSONL 不存在: {CH31_CH50_JSONL_PATH}")

    ch1_ch30_run_logs = _load_jsonl(CH1_CH30_JSONL_PATH)
    ch31_ch50_run_logs = _load_jsonl(CH31_CH50_JSONL_PATH)

    if not ch1_ch30_run_logs or not ch31_ch50_run_logs:
        raise ValueError("JSONL 日志为空")

    project_id = ch1_ch30_run_logs[0]["project_id"]
    db_rows = await _load_continuity_reports(project_id)

    report_lookup: dict[int, ContinuityReport] = {}
    for row in db_rows:
        report = _report_from_db_row(row)
        report_lookup[row["checked_up_to_chapter"]] = report

    def _enrich_log(log: dict) -> dict:
        chapter_number = log["chapter_number"]
        report = report_lookup.get(chapter_number)
        ctx_pressure = log.get("context_pressure") or {}
        if isinstance(ctx_pressure, str):
            ctx_pressure = json.loads(ctx_pressure)
        budget_before = None
        if isinstance(ctx_pressure, dict):
            budget_before = ctx_pressure.get("budget_used_before_emergency")

        if log.get("continuity_health_score") is not None:
            health_score = log["continuity_health_score"]
        elif report is not None:
            health_score = report.overall_health_score
        else:
            health_score = None

        if log.get("continuity_health_severity") is not None:
            health_severity = log["continuity_health_severity"]
        elif report is not None:
            health_severity = classify_report(report)
        else:
            health_severity = None

        return {
            "chapter_number": chapter_number,
            "success": log.get("success"),
            "quality_gate_passed": log.get("quality_gate_passed"),
            "settlement_success": log.get("settlement_success"),
            "summary_success": log.get("summary_success"),
            "context_emergency": log.get("context_emergency", False) or False,
            "budget_used_before_emergency": budget_before,
            "continuity_health_score": health_score,
            "continuity_health_severity": health_severity,
        }

    all_logs = sorted(
        [_enrich_log(log) for log in ch1_ch30_run_logs + ch31_ch50_run_logs],
        key=lambda x: x["chapter_number"],
    )

    triggers = _simulate_enforce_gates(all_logs, report_lookup)

    report_md = _generate_report(triggers)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_md, encoding="utf-8")

    triggered = [t for t in triggers if t["gate_triggered"]]
    print(f"分析完成: {len(triggers)} 章, {len(triggered)} 章触发 gate")
    print(f"报告已生成: {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
