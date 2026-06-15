"""Task 081: Ch51-Ch70 真实 LLM 验证脚本.

用法:
    python scripts/run_task_081_ch51_ch70.py

输出:
    evals/output/validation_ch51_70/ 目录
    - test.db: 运行数据库（复制自 validation_ch41_50/test.db）
    - task_081_log.jsonl: 每章运行日志
    - task_081_report.md: 最终验证报告
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from sqlite3 import Row
from typing import Any

import structlog

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.workflows.phase1_graph import reset_checkpointer
from songyan.workflows.phase2_graph import run_project_pipeline

logger = structlog.get_logger(__name__)

# =============================================================================
# Config
# =============================================================================

SOURCE_DB = Path("evals/output/validation_ch41_50/test.db")
OUTPUT_DIR = Path("evals/output/validation_ch51_70")
DB_PATH = OUTPUT_DIR / "test.db"
LOG_PATH = OUTPUT_DIR / "task_081_log.jsonl"
REPORT_PATH = OUTPUT_DIR / "task_081_report.md"
PROJECT_ID = "proj-4b72ecf2"
MODE_ID = "webnovel"
CHAPTER_RANGE = (51, 70)

# =============================================================================
# Helpers
# =============================================================================


def _now() -> str:
    return datetime.now().isoformat()


async def _log_event(event: dict[str, Any]) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


async def _collect_chapter_metrics(project_id: str, chapter_number: int) -> dict[str, Any]:
    """收集单章的关键指标."""
    metrics: dict[str, Any] = {"chapter_number": chapter_number}

    async with get_db() as conn:
        conn.row_factory = Row

        # 1. 字数
        cursor = await conn.execute(
            """SELECT word_count, content FROM chapter_versions
            WHERE project_id = ? AND chapter_number = ? AND version_type = 'accepted'
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, chapter_number),
        )
        row = await cursor.fetchone()
        if row:
            metrics["word_count"] = row["word_count"]
            metrics["content_len"] = len(row["content"])
        else:
            metrics["word_count"] = 0
            metrics["content_len"] = 0

        # 2. 版本数
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM chapter_versions WHERE project_id = ? AND chapter_number = ?",
            (project_id, chapter_number),
        )
        metrics["version_count"] = (await cursor.fetchone())[0]

        # 3. settlement 数据量
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM setting_snapshots WHERE project_id = ?",
            (project_id,),
        )
        metrics["total_settings"] = (await cursor.fetchone())[0]

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM foreshadowings WHERE project_id = ? AND status != 'resolved' AND status != 'archived'",
            (project_id,),
        )
        metrics["active_foreshadowings"] = (await cursor.fetchone())[0]

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM character_states cs JOIN characters c ON cs.character_id = c.character_id WHERE c.project_id = ?",
            (project_id,),
        )
        metrics["total_character_states"] = (await cursor.fetchone())[0]

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM human_marks WHERE project_id = ? AND resolved_at IS NULL",
            (project_id,),
        )
        metrics["unresolved_human_marks"] = (await cursor.fetchone())[0]

        # 4. 连续性健康分 (兼容旧schema: overall_health_score)
        cursor = await conn.execute(
            """SELECT overall_health_score, overdue_foreshadowings, orphaned_settings
            FROM continuity_reports
            WHERE project_id = ? AND checked_up_to_chapter = ?
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, chapter_number),
        )
        row = await cursor.fetchone()
        if row:
            metrics["health_score"] = row["overall_health_score"]
            try:
                overdue = json.loads(row["overdue_foreshadowings"] or "[]")
                metrics["overdue_count"] = len(overdue)
            except json.JSONDecodeError:
                metrics["overdue_count"] = 0
            try:
                orphaned = json.loads(row["orphaned_settings"] or "[]")
                metrics["orphaned_count"] = len(orphaned)
            except json.JSONDecodeError:
                metrics["orphaned_count"] = 0
            metrics["constraints_written"] = None  # 旧schema无此字段
        else:
            metrics["health_score"] = None
            metrics["constraints_written"] = None
            metrics["overdue_count"] = None
            metrics["orphaned_count"] = None

        # 5. 审查结果 (兼容旧schema: issues JSON)
        cursor = await conn.execute(
            """SELECT issues, overall_score FROM review_reports
            WHERE chapter_version_id IN (
                SELECT version_id FROM chapter_versions
                WHERE project_id = ? AND chapter_number = ? AND version_type = 'accepted'
            )
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, chapter_number),
        )
        row = await cursor.fetchone()
        if row:
            try:
                issues = json.loads(row["issues"] or "[]")
                metrics["critical_count"] = sum(1 for i in issues if i.get("severity") == "critical")
                metrics["major_count"] = sum(1 for i in issues if i.get("severity") == "major")
                metrics["minor_count"] = sum(1 for i in issues if i.get("severity") == "minor")
            except json.JSONDecodeError:
                metrics["critical_count"] = 0
                metrics["major_count"] = 0
                metrics["minor_count"] = 0
        else:
            metrics["critical_count"] = None
            metrics["major_count"] = None
            metrics["minor_count"] = None

        # 6. generation_metadata（budget_used 等）
        cursor = await conn.execute(
            """SELECT generation_metadata FROM chapter_versions
            WHERE project_id = ? AND chapter_number = ? AND version_type = 'accepted'
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, chapter_number),
        )
        row = await cursor.fetchone()
        if row and row["generation_metadata"]:
            try:
                meta = json.loads(row["generation_metadata"])
                metrics["budget_used"] = meta.get("budget_used")
                metrics["_budget_enforced"] = meta.get("_budget_enforced")
                metrics["_was_truncated"] = meta.get("_was_truncated")
                metrics["_disallowed_by_scene_structure"] = meta.get("_disallowed_by_scene_structure")
                metrics["_rewrite_reason"] = meta.get("_rewrite_reason")
                metrics["revision_rounds"] = meta.get("revision_rounds")
            except json.JSONDecodeError:
                metrics["budget_used"] = None
        else:
            metrics["budget_used"] = None

    return metrics


async def _generate_report(results: list[dict[str, Any]]) -> str:
    """生成 Markdown 验证报告."""
    lines = [
        "# Task 081: Ch51-Ch70 验证报告",
        "",
        f"> **运行时间**: {_now()}",
        f"> **模型**: {settings.llm_model}",
        f"> **项目**: {PROJECT_ID}",
        f"> **模式**: {MODE_ID}",
        "",
        "## 执行摘要",
        "",
    ]

    total_chapters = len(results)
    success_count = sum(1 for r in results if r.get("status") == "success")
    fail_count = sum(1 for r in results if r.get("status") == "failed")

    lines.append(f"- **完成章节**: {success_count}/{total_chapters}")
    lines.append(f"- **失败章节**: {fail_count}")
    lines.append(f"- **总耗时**: {sum(r.get('elapsed_sec', 0) for r in results):.0f}s")
    lines.append("")

    # 关键指标表
    lines.append("## 关键指标总览")
    lines.append("")
    lines.append("| 章节 | 状态 | 字数 | budget_used | 版本数 | health_score | constraints | overdue | critical | major | 备注 |")
    lines.append("|------|------|------|-------------|--------|--------------|-------------|---------|----------|-------|------|")

    for r in results:
        ch = r.get("chapter_number", "?")
        status = "✅" if r.get("status") == "success" else "❌"
        wc = r.get("word_count", "-")
        bu = r.get("budget_used", "-")
        if isinstance(bu, float):
            bu = f"{bu:.2f}"
        vc = r.get("version_count", "-")
        hs = r.get("health_score", "-")
        if isinstance(hs, float):
            hs = f"{hs:.1f}"
        cw = r.get("constraints_written", "-")
        od = r.get("overdue_count", "-")
        cr = r.get("critical_count", "-")
        ma = r.get("major_count", "-")
        note = r.get("note", "")
        lines.append(f"| Ch{ch} | {status} | {wc} | {bu} | {vc} | {hs} | {cw} | {od} | {cr} | {ma} | {note} |")

    lines.append("")
    lines.append("## 字数控制分析")
    lines.append("")
    lines.append("| 章节 | 目标字数 | 实际字数 | 偏差 | 截断标记 |")
    lines.append("|------|---------|---------|------|----------|")

    for r in results:
        ch = r.get("chapter_number", "?")
        wc = r.get("word_count", 0)
        target = 3200  # scifi 默认目标
        deviation = f"{((wc - target) / target * 100):+.0f}%" if wc else "-"
        truncated = "✅" if r.get("_was_truncated") else ""
        lines.append(f"| Ch{ch} | {target} | {wc} | {deviation} | {truncated} |")

    lines.append("")
    lines.append("## 上下文膨胀趋势")
    lines.append("")
    lines.append("| 章节 | active_foreshadowings | total_settings | total_character_states | unresolved_human_marks |")
    lines.append("|------|----------------------|----------------|------------------------|------------------------|")

    for r in results:
        ch = r.get("chapter_number", "?")
        af = r.get("active_foreshadowings", "-")
        ts = r.get("total_settings", "-")
        tcs = r.get("total_character_states", "-")
        uhm = r.get("unresolved_human_marks", "-")
        lines.append(f"| Ch{ch} | {af} | {ts} | {tcs} | {uhm} |")

    lines.append("")
    lines.append("## 失败详情")
    lines.append("")

    failed = [r for r in results if r.get("status") == "failed"]
    if failed:
        for r in failed:
            ch = r.get("chapter_number", "?")
            error = r.get("error", "未知错误")
            lines.append(f"### Ch{ch}")
            lines.append(f"- **Error**: {error}")
            lines.append("")
    else:
        lines.append("无失败章节。")
        lines.append("")

    lines.append("## 原始数据")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(results, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================


async def _main() -> int:
    print("=" * 60)
    print("Task 081: Ch51-Ch70 Real LLM Validation")
    print("=" * 60)

    # 1. 准备环境
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not SOURCE_DB.exists():
        print(f"\n[ERROR] 源数据库不存在: {SOURCE_DB}")
        return 1

    if not DB_PATH.exists():
        print(f"\n[COPY] Source DB to {DB_PATH}")
        shutil.copy2(SOURCE_DB, DB_PATH)
    else:
        print(f"\n[USE] Existing DB: {DB_PATH}")

    settings.database_url = f"sqlite:///{DB_PATH}"
    print(f"[DB] {DB_PATH}")

    # 2. 验证项目存在
    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            "SELECT title, genre_id, mode_id FROM projects WHERE project_id = ?",
            (PROJECT_ID,),
        )
        row = await cursor.fetchone()
    if not row:
        print(f"[ERROR] 项目 {PROJECT_ID} 不存在于数据库")
        return 1
    print(f"[PROJECT] {row['title']} ({row['genre_id']}, {row['mode_id']})")

    # 3. 确认已有章节数
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT MAX(chapter_number) FROM chapter_versions WHERE project_id = ?",
            (PROJECT_ID,),
        )
        max_chapter = (await cursor.fetchone())[0] or 0
    print(f"[INFO] Existing chapters up to: {max_chapter}")

    # 自动调整起始章节
    start_chapter = max(max_chapter + 1, CHAPTER_RANGE[0])
    if start_chapter > CHAPTER_RANGE[1]:
        print(f"[INFO] All chapters already exist. Nothing to do.")
        return 0

    # 4. 重置 checkpointer
    await reset_checkpointer()

    # 5. 运行多章流水线
    remaining = CHAPTER_RANGE[1] - start_chapter + 1
    print(f"\n[START] Ch{start_chapter}-Ch{CHAPTER_RANGE[1]} pipeline")
    print(f"        Est. ~8 min/chapter, total ~{remaining * 8} min")
    print("        Press Ctrl+C to interrupt\n")

    results: list[dict[str, Any]] = []
    total_start = time.monotonic()

    try:
        for chapter_number in range(start_chapter, CHAPTER_RANGE[1] + 1):
            print(f"\n{'='*60}")
            print(f"Chapter {chapter_number}")
            print(f"{'='*60}")

            ch_start = time.monotonic()
            ch_result: dict[str, Any] = {
                "chapter_number": chapter_number,
                "start_time": _now(),
            }

            try:
                result = await run_project_pipeline(
                    project_id=PROJECT_ID,
                    chapter_range=(chapter_number, chapter_number),
                    mode_id=MODE_ID,
                    auto_confirm=True,
                    on_failure="abort",
                )

                ch_elapsed = time.monotonic() - ch_start
                ch_result["elapsed_sec"] = round(ch_elapsed, 1)
                ch_result["end_time"] = _now()

                if result.final_status == "completed":
                    ch_result["status"] = "success"
                    print(f"[OK] Ch{chapter_number} done ({ch_elapsed:.0f}s)")
                else:
                    ch_result["status"] = "failed"
                    ch_result["error"] = f"final_status={result.final_status}"
                    print(f"[FAIL] Ch{chapter_number}: {result.final_status}")

            except Exception as exc:
                ch_elapsed = time.monotonic() - ch_start
                ch_result["elapsed_sec"] = round(ch_elapsed, 1)
                ch_result["end_time"] = _now()
                ch_result["status"] = "failed"
                ch_result["error"] = str(exc)
                print(f"[ERROR] Ch{chapter_number}: {exc}")
                import traceback
                traceback.print_exc()

            # 收集指标
            metrics = await _collect_chapter_metrics(PROJECT_ID, chapter_number)
            ch_result.update(metrics)
            results.append(ch_result)

            # 实时日志
            await _log_event(ch_result)

            # 实时保存报告
            report_md = await _generate_report(results)
            REPORT_PATH.write_text(report_md, encoding="utf-8")

    except KeyboardInterrupt:
        print("\n\n[INTERRUPT] User stopped")
        return 130

    total_elapsed = time.monotonic() - total_start

    # 6. 最终报告
    print(f"\n{'='*60}")
    print("验证完成")
    print(f"{'='*60}")
    print(f"总章节: {len(results)}")
    print(f"成功: {sum(1 for r in results if r.get('status') == 'success')}")
    print(f"失败: {sum(1 for r in results if r.get('status') == 'failed')}")
    print(f"总耗时: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)")
    print(f"\n📁 报告: {REPORT_PATH}")
    print(f"📁 日志: {LOG_PATH}")
    print(f"📁 数据库: {DB_PATH}")

    # 更新最终的 STATUS.md 参考
    print(f"\n请检查 {REPORT_PATH} 获取详细分析")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(_main()))
    except KeyboardInterrupt:
        print("\n已取消。")
        sys.exit(130)
