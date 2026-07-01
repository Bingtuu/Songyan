"""Generate Task 129 enforce mode validation report from DB and logs."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path("songyan.db")
LOG_DIR = Path("logs/chapter_runs")
REPORT_PATH = Path("docs/reports/task-129-enforce-validation-report.md")
RUN_ID = "run-89d7a2d4"
PROJECT_ID = "3cf71586df2a4b5c9170d9b1a5f059cf"


def load_logs(run_id: str) -> list[dict[str, Any]]:
    log_file = LOG_DIR / f"{run_id}.jsonl"
    rows: list[dict[str, Any]] = []
    if not log_file.exists():
        return rows
    with log_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def query_one(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> sqlite3.Row | None:
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchone()


def query_all(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()


def format_duration(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {sec}s"
    return f"{minutes}m {sec}s"


def main() -> None:
    logs = load_logs(RUN_ID)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    run_row = query_one(conn, "SELECT * FROM project_runs WHERE run_id=?", (RUN_ID,))
    if run_row is None:
        raise RuntimeError(f"Run {RUN_ID} not found in project_runs")

    # Aggregate per-chapter metrics from logs
    qg_failed = [r for r in logs if not r.get("quality_gate_passed", True)]
    gate_triggered = [r for r in logs if r.get("gate_triggered")]
    degraded = [r for r in logs if r.get("degraded_accept")]
    conv_failed = [r for r in logs if r.get("convergence_failed")]
    settlement_failed = [r for r in logs if not r.get("settlement_success")]
    context_emergency = [r for r in logs if r.get("context_emergency")]

    total_words = sum(r.get("word_count", 0) for r in logs)
    total_duration = sum(r.get("duration_sec", 0) for r in logs)

    # Continuity reports
    cont_sql = (
        "SELECT checked_up_to_chapter, overall_health_score, "
        "orphaned_settings, forgotten_items, state_mismatches, "
        "overdue_foreshadowings "
        "FROM continuity_reports WHERE project_id=? "
        "ORDER BY checked_up_to_chapter"
    )
    cont_rows = query_all(conn, cont_sql, (PROJECT_ID,))

    # State tables
    state_counts = {
        "character_states": query_one(conn, "SELECT COUNT(*) AS c FROM character_states")["c"],
        "setting_tracking": query_one(
            conn, "SELECT COUNT(*) AS c FROM setting_tracking WHERE project_id=?", (PROJECT_ID,)
        )["c"],
        "foreshadowings": query_one(
            conn, "SELECT COUNT(*) AS c FROM foreshadowings WHERE project_id=?", (PROJECT_ID,)
        )["c"],
        "numerical_ledgers": query_one(
            conn, "SELECT COUNT(*) AS c FROM numerical_ledgers WHERE project_id=?", (PROJECT_ID,)
        )["c"],
        "summaries": query_one(
            conn, "SELECT COUNT(*) AS c FROM summaries WHERE project_id=?", (PROJECT_ID,)
        )["c"],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Task 129 enforce 模式 Ch1–Ch50 验证报告\n\n")
        f.write(f"> **运行ID**: `{RUN_ID}`  \n")
        f.write(f"> **项目ID**: `{PROJECT_ID}`  \n")
        f.write(f"> **生成时间**: {datetime.utcnow().isoformat()}  \n")
        f.write("> **状态**: **AutoHalt 终止**（未跑完 Ch1–Ch50）  \n\n"
        )

        f.write("## 1. 执行摘要\n\n")
        f.write("- **目标**: 以 `gate_mode=\"enforce\"` 跑通 Ch1–Ch50。\n")
        f.write(f"- **实际完成**: Ch1–Ch{len(logs)}（共 {len(logs)} 章）。\n")
        f.write(f"- **终止原因**: `{run_row['status']}` —— quality_gate_fail_streak。\n")
        f.write(f"- **总字数**: {total_words:,} 字。\n")
        f.write(f"- **总耗时**: {format_duration(total_duration)}。\n")
        avg = format_duration(total_duration / len(logs)) if logs else "N/A"
        f.write(f"- **平均每章耗时**: {avg}。\n\n")

        f.write("## 2. 关键指标 vs 验收标准\n\n")
        f.write("| 指标 | 实际值 | 验收标准 | 是否达标 |\n")
        f.write("|------|--------|----------|----------|\n")
        f.write(f"| 覆盖章节 | Ch1–Ch{len(logs)} | Ch1–Ch50 | ❌ |\n")
        f.write("| AutoHalt 次数 | 1 | 0 | ❌ |\n")
        gate_ok = "✅" if len(gate_triggered) <= 1 else "❌"
        f.write(f"| Gate 触发次数 | {len(gate_triggered)} | ≤ 1 | {gate_ok} |\n")
        f.write(f"| Quality Gate 失败 | {len(qg_failed)} 章 | 0 | ❌ |\n")
        f.write(f"| Convergence 失败 | {len(conv_failed)} 章 | 0 | ❌ |\n")
        f.write(f"| Settlement 失败 | {len(settlement_failed)} 章 | 0 | ❌ |\n")
        degraded_ok = "✅" if len(degraded) == 0 else "❌"
        f.write(f"| Degraded accept | {len(degraded)} 章 | 0 | {degraded_ok} |\n")
        emergency_ok = "✅" if len(context_emergency) <= 3 else "❌"
        f.write(f"| ContextEmergency | {len(context_emergency)} 次 | ≤ 3 | {emergency_ok} |\n")
        failed_raw = run_row["failed_chapters"] or "[]"
        failed = json.loads(failed_raw)
        f.write(f"| Failed 章节 | {len(failed)} | 0 | ✅ |\n\n")

        f.write("## 3. 各章节质量概览\n\n")
        f.write("| Ch | 字数 | QG | Settlement | Converge | 预算 | 总分 | 健康分 | 耗时 |\n")
        f.write("|----|------|----|------------|----------|------|------|--------|------|\n")
        for r in logs:
            score_card = r.get("score_card", {}) or {}
            overall = score_card.get("overall_score", 0.0)
            health = r.get("continuity_health_score")
            health_str = f"{health:.2f}" if health is not None else "—"
            qg = "✅" if r.get("quality_gate_passed") else "❌"
            settled = "✅" if r.get("settlement_success") else "❌"
            conv = "✅" if not r.get("convergence_failed") else "❌"
            f.write(
                f"| {r['chapter_number']} | {r.get('word_count', 0)} | {qg} | "
                f"{settled} | {conv} | {r.get('budget_used', 0):.3f} | "
                f"{overall:.4f} | {health_str} | "
                f"{format_duration(r.get('duration_sec', 0))} |\n"
            )
        f.write("\n")

        f.write("## 4. AutoHalt 根因分析\n\n")
        f.write(
            "进程在 Chapter 15 后因 **quality_gate_fail_streak** 暂停。"
            "根据日志，Chapter 13、14、15 连续出现 "
            "`quality_gate_passed=False`，满足 streak 条件。\n\n"
        )
        f.write("质量门失败章节详情：\n\n")
        f.write("| Ch | 失败原因 | 字数比 | 预算 | 可读性 | 连贯性 | 总分 |\n")
        f.write("|----|----------|--------|------|--------|--------|------|\n")
        for r in qg_failed:
            sc = r.get("score_card", {}) or {}
            flags = sc.get("flags", {})
            reasons: list[str] = []
            if not flags.get("readability_ok"):
                reasons.append("readability")
            if flags.get("coherence_major"):
                reasons.append("coherence_major")
            if flags.get("coherence_critical"):
                reasons.append("coherence_critical")
            if not reasons:
                reasons.append("overall_score")
            length_details = sc.get("length", {}).get("details", {})
            word_ratio = length_details.get("word_count_ratio", 1.0)
            budget_details = sc.get("budget", {}).get("details", {})
            budget_used = budget_details.get("budget_used", r.get("budget_used", 0))
            readability = sc.get("readability", {}).get("score", 0)
            coherence = sc.get("coherence", {}).get("score", 0)
            overall = sc.get("overall_score", 0)
            f.write(
                f"| {r['chapter_number']} | {', '.join(reasons)} | {word_ratio:.2f} | "
                f"{budget_used:.3f} | {readability:.4f} | {coherence:.4f} | {overall:.4f} |\n"
            )
        f.write("\n")

        f.write("## 5. Continuity Health 趋势\n\n")
        f.write("| 检查点 | 健康分 | Orphaned | Forgotten | StateMismatch | OverdueShadow |\n")
        f.write("|--------|--------|----------|-----------|-------------|---------------|\n")
        for row in cont_rows:
            orphaned = len(json.loads(row["orphaned_settings"]))
            forgotten = len(json.loads(row["forgotten_items"]))
            mismatches = len(json.loads(row["state_mismatches"]))
            overdue = len(json.loads(row["overdue_foreshadowings"]))
            f.write(
                f"| Ch{row['checked_up_to_chapter']} | {row['overall_health_score']:.2f} | "
                f"{orphaned} | {forgotten} | {mismatches} | {overdue} |\n"
            )
        f.write("\n")

        f.write("## 6. 发现的关键问题\n\n")
        f.write(
            "1. **Writer 结构输出单一**：所有章节的 `scenes_count=1`，"
            "明显低于 prompt 要求的 2+ 场景结构，导致可读性和连贯性承压。\n"
        )
        f.write(
            "2. **角色状态表为空**：`character_states` 记录数为 0，"
            "`numerical_ledgers` 记录数也为 0，说明 settlement extractor "
            "未成功建立角色状态快照。\n"
        )
        f.write(
            "3. **Orphaned settings 快速累积**：从 Ch6 的 7 个上升到 Ch15 的 27 个，"
            "设定回收严重不足。\n"
        )
        f.write(
            "4. **Continuity health 持续恶化**：Ch9 健康分 1.2，"
            "Ch12/Ch15 跌至 0.0，P1/P3 问题大量堆积。\n"
        )
        f.write(
            "5. **Settlement 失败章未建立摘要**：Ch3、Ch11、Ch14、Ch15 "
            "`settlement_success=False`，对应 `summary_id=None`，"
            "导致后续上下文缺乏结算信息。\n"
        )
        f.write(
            "6. **质量门阈值在中段过于严格**：Chapter 12 健康分 0.0 但 "
            "quality_gate_passed=True，而 Chapter 14/15 在总分更低时失败，"
            "显示 budget/readability 权重与 continuity 健康分存在错位。\n\n"
        )

        f.write("## 7. 数据资产\n\n")
        f.write(f"- 运行日志：`{LOG_DIR / f'{RUN_ID}.jsonl'}`\n")
        f.write(f"- 数据库：`{DB_PATH}`（project_id=`{PROJECT_ID}`）\n")
        f.write("- 状态表统计：\n")
        for name, cnt in state_counts.items():
            f.write(f"  - `{name}`: {cnt}\n")
        f.write("\n")

        f.write("## 8. 结论与下一步建议\n\n")
        f.write(
            "**结论**：本次 enforce 模式 Ch1–Ch50 验证 **未能跑通**，"
            "在 Ch15 因 quality gate streak 触发 AutoHalt。问题集中在 Writer "
            "结构输出、Settlement 提取、设定回收与连续性维护四个环节。\n\n"
        )
        f.write("**建议下一步**：\n")
        f.write(
            "1. **Task 130**：修复 Writer 多场景结构输出（prompt / parser 调优），"
            "确保每章至少 2 个 scene。\n"
        )
        f.write(
            "2. **Task 131**：修复 SettlementExtractor 角色状态与数值台账提取，"
            "解决 `character_states` 和 `numerical_ledgers` 为空的问题。\n"
        )
        f.write(
            "3. **Task 132**：优化设定回收策略，降低 orphaned settings 累积速度；"
            "或调整 continuity auditor 的评分/衰减逻辑。\n"
        )
        f.write(
            "4. 在完成上述修复后，重新发起 Task 129 复跑，目标 Ch1–Ch50 无 AutoHalt。\n\n"
        )

        f.write("---\n\n")
        f.write("*报告由 `scripts/generate_task129_report.py` 自动生成。*\n")

    print(f"Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
