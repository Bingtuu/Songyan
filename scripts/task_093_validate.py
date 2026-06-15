#!/usr/bin/env python3
"""Task 093: 字数约束收紧验证 — 简化版 runner.

验证范围: Ch2-Ch5（观察收紧 ±20% 后的达标率变化）
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Row
from typing import Any
from unittest.mock import patch

# Windows 控制台 UTF-8 编码修复
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.llm.client import call_llm
from songyan.workflows.phase1_graph import reset_checkpointer
from songyan.workflows.phase2_graph import run_project_pipeline
from evals.runner import import_seed_chapter, import_seed_project
from songyan.utils.cost_estimator import estimate_cost_from_calls, format_cost_estimate
from songyan.utils.word_count import count_chinese_words

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
SEED_CONFIG_PATH = "evals/seeds/scifi_webnovel.json"
SEED_CHAPTER_PATH = "evals/seeds/chapters/scifi_ch1.md"
OUTPUT_DIR = Path("evals/output/task_093_validation")
LLM_CALLS: list[dict[str, Any]] = []

# ---------------------------------------------------------------------------
# LLM 追踪
# ---------------------------------------------------------------------------
def _make_wrapper(agent_name: str):
    orig = call_llm
    async def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            result = await orig(*args, **kwargs)
            return result
        finally:
            duration = time.monotonic() - start
            messages = kwargs.get("messages", args[0] if args else [])
            model = kwargs.get("model", "")
            LLM_CALLS.append({
                "agent": agent_name,
                "model": model,
                "messages": messages,
                "duration_sec": round(duration, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    return wrapper

# ---------------------------------------------------------------------------
# Metrics 收集
# ---------------------------------------------------------------------------
async def _collect_metrics(project_id: str, chapter_number: int, db_path: Path) -> dict:
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = Row
    cur = conn.cursor()

    # 查找最新非 abandoned version
    cur.execute(
        """SELECT version_id, word_count, content
           FROM chapter_versions
           WHERE project_id=? AND chapter_number=? AND is_abandoned=0
           ORDER BY version_number DESC LIMIT 1""",
        (project_id, chapter_number),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"error": "no version found"}

    version_id = row["version_id"]
    word_count = row["word_count"]

    # 从 chapter_heads 获取当前状态
    cur.execute(
        "SELECT status, current_version_id FROM chapter_heads WHERE project_id=? AND chapter_number=?",
        (project_id, chapter_number),
    )
    head_row = cur.fetchone()
    status = head_row["status"] if head_row else "unknown"

    # goal
    cur.execute(
        "SELECT word_count_target FROM chapter_goals WHERE project_id=? AND chapter_number=?",
        (project_id, chapter_number),
    )
    goal_row = cur.fetchone()
    target = goal_row["word_count_target"] if goal_row else None

    # version history
    cur.execute(
        """SELECT version_number, version_type, is_abandoned, word_count, created_at
           FROM chapter_versions
           WHERE project_id=? AND chapter_number=?
           ORDER BY version_number""",
        (project_id, chapter_number),
    )
    versions = [
        {
            "v": r["version_number"],
            "type": r["version_type"],
            "abandoned": bool(r["is_abandoned"]),
            "wc": r["word_count"],
        }
        for r in cur.fetchall()
    ]

    # lifecycle
    cur.execute(
        "SELECT COUNT(*) FROM chapter_context_items WHERE project_id=? AND chapter_number=? AND lifecycle=?",
        (project_id, chapter_number, "active"),
    )
    active_n = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM chapter_context_items WHERE project_id=? AND chapter_number=? AND lifecycle=?",
        (project_id, chapter_number, "dormant"),
    )
    dormant_n = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM chapter_context_items WHERE project_id=? AND chapter_number=? AND lifecycle=?",
        (project_id, chapter_number, "archived"),
    )
    archived_n = cur.fetchone()[0]

    # revision info
    cur.execute(
        "SELECT revision_type, status FROM chapter_revisions WHERE version_id=? ORDER BY sequence_number",
        (version_id,),
    )
    revisions = [{"type": r["revision_type"], "status": r["status"]} for r in cur.fetchall()]

    conn.close()

    return {
        "version_id": version_id,
        "status": status,
        "word_count": word_count,
        "target": target,
        "compliance": None if target is None else round(word_count / target, 3),
        "versions": versions,
        "lifecycle": {"active": active_n, "dormant": dormant_n, "archived": archived_n},
        "revisions": revisions,
    }


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
async def main():
    print("=" * 60)
    print("Task 093 验证: 字数约束收紧 ±20%")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    db_path = OUTPUT_DIR / "test.db"
    settings.database_url = f"sqlite:///{db_path}"

    # 强制重新初始化
    if db_path.exists():
        db_path.unlink()
        for f in OUTPUT_DIR.glob("*.db*"):
            f.unlink()

    print(f"\n📁 数据库: {db_path}")
    await init_schema()
    print("   Schema 初始化完成")

    # 验证表数
    import sqlite3
    conn_check = sqlite3.connect(str(db_path))
    cur_check = conn_check.cursor()
    cur_check.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur_check.fetchall()]
    conn_check.close()
    print(f"   表数: {len(tables)}")
    if len(tables) == 0:
        print("❌ ERROR: 0 tables! 中止")
        return

    print("\n📥 导入种子项目...")
    project_id = await import_seed_project(SEED_CONFIG_PATH)
    print(f"   项目: {project_id}")

    print("📥 导入种子章节 (Ch1)...")
    await import_seed_chapter(project_id, SEED_CHAPTER_PATH, chapter_number=1)
    print("   完成")

    # Patch LLM
    targets = [
        ("songyan.agents.goal_planner.call_llm", "goal_planner"),
        ("songyan.agents.creative_director.call_llm", "creative_director"),
        ("songyan.agents.writer.call_llm", "writer"),
        ("songyan.agents.llm_auditor.call_llm", "llm_auditor"),
        ("songyan.agents.literary_auditor.call_llm", "literary_auditor"),
        ("songyan.agents.revision_handler.call_llm", "revision_handler"),
        ("songyan.agents.settlement_extractor.call_llm", "settlement_extractor"),
        ("songyan.agents.summary_writer.call_llm", "summary_writer"),
    ]

    results = []
    start_ch = 2
    end_ch = 5

    with contextlib.ExitStack() as stack:
        for target, agent_name in targets:
            stack.enter_context(patch(target, _make_wrapper(agent_name)))

        for ch in range(start_ch, end_ch + 1):
            print(f"\n{'='*60}")
            print(f"🚀 Chapter {ch}")
            print(f"{'='*60}")
            LLM_CALLS.clear()
            ch_start = time.monotonic()

            try:
                await reset_checkpointer()
                result = await run_project_pipeline(
                    project_id=project_id,
                    chapter_range=(ch, ch),
                    mode_id="webnovel_intense",
                    auto_confirm=True,
                )
                ch_time = round(time.monotonic() - ch_start, 1)
                metrics = await _collect_metrics(project_id, ch, db_path)
                results.append({
                    "chapter": ch,
                    "status": "success",
                    "time_sec": ch_time,
                    **metrics,
                })
                print(f"✅ Ch{ch} 完成 | 状态: {metrics['status']} | 字数: {metrics['word_count']} | 目标: {metrics['target']} | 达标: {metrics['compliance']}")
                print(f"   版本历史: {metrics['versions']}")
            except Exception as e:
                ch_time = round(time.monotonic() - ch_start, 1)
                results.append({
                    "chapter": ch,
                    "status": "failed",
                    "time_sec": ch_time,
                    "error": str(e),
                })
                print(f"❌ Ch{ch} 失败: {e}")
                traceback.print_exc()

    # 汇总
    print(f"\n{'='*60}")
    print("📊 汇总")
    print(f"{'='*60}")

    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    total_llm = len(LLM_CALLS)
    cost = estimate_cost_from_calls(LLM_CALLS)

    print(f"成功: {len(success)}/{len(results)} | 失败: {len(failed)}")
    if failed:
        for f in failed:
            print(f"  Ch{f['chapter']}: {f.get('error', 'unknown')}")

    print(f"\nLLM 调用: {total_llm}")
    print(format_cost_estimate(cost))

    # 字数达标分析
    print(f"\n📏 字数达标分析 (目标 ±20% = [0.80, 1.20]):")
    for r in success:
        comp = r.get("compliance")
        status_icon = "✅" if comp and 0.80 <= comp <= 1.20 else "❌"
        print(f"  Ch{r['chapter']}: {r['word_count']} / {r['target']} = {comp} {status_icon}")

    # 保存结果
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": "093",
        "config": {"constraint": "±20%"},
        "results": results,
        "summary": {
            "success": len(success),
            "failed": len(failed),
            "total_llm_calls": total_llm,
            "cost_estimate": cost,
        },
    }
    report_path = OUTPUT_DIR / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 报告: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
