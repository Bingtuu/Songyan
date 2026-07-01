"""Ch41-Ch50 真实 LLM 快速验证 — 方案 A.

Steps:
    1. 创建 scifi 项目，导入 Ch1 种子
    2. Mock 快速构建 Ch2-Ch40 历史（直接 DB 写入，不调用 LLM）
    3. 设置 checkpointer_mode = "memory"（避免 Windows 卡死）
    4. 运行 Ch41-Ch50 真实 LLM pipeline（auto_confirm）
    5. 收集并输出 V3.1 验证指标

Usage:
    cd g:\\vibe\\Songyan && python scripts/validate_ch41_50_real_llm.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# 确保项目根目录在 Python path 中（直接运行脚本时需要）
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.context_repo import SummaryRepository
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.models import ChapterHead, ChapterSummary, ChapterVersion, CharacterState
from songyan.workflows._helpers import new_id
from songyan.workflows.phase2_graph import run_project_pipeline

from evals.runner import import_seed_chapter, import_seed_project

SEED_CONFIG = "evals/seeds/scifi_new_weird.json"
SEED_CHAPTER = "evals/seeds/chapters/scifi_new_weird_ch1.md"
OUTPUT_DIR = Path("evals/output/validation_ch41_50")


# ---------------------------------------------------------------------------
# Helpers: 构建 Ch2-Ch40 mock 历史
# ---------------------------------------------------------------------------


async def _build_chapter_history(project_id: str, chapter_number: int) -> str:
    """直接 DB 写入单章 mock 历史（模拟已完成的章节）."""
    version_id = new_id("v")
    content = (
        f"【第{chapter_number}章正文】\n\n"
        f"主角在第{chapter_number}章继续冒险，遭遇新的挑战和敌人。\n"
        f"他运用智慧化解危机，实力略有提升。\n"
    )
    version = ChapterVersion(
        version_id=version_id,
        project_id=project_id,
        chapter_number=chapter_number,
        version_number=1,
        version_type="accepted",
        content=content,
        word_count=len(content),
    )
    await ChapterVersionRepository().create(version)

    head = ChapterHead(
        project_id=project_id,
        chapter_number=chapter_number,
        current_version_id=version_id,
        accepted_version_id=version_id,
        status="accepted",
    )
    await ChapterHeadRepository().update(head)

    summary = ChapterSummary(
        chapter_number=chapter_number,
        summary=f"第{chapter_number}章：主角遭遇新挑战，剧情持续推进。",
        key_events=[f"事件{chapter_number}-A"],
        characters_appeared=["主角"],
        emotional_tone="紧张",
        impact_score=0.3,
    )
    summary_id = new_id("sum")
    await SummaryRepository().create(summary, project_id, summary_id)

    char_repo = CharacterRepository()
    characters = await char_repo.list_by_project(project_id)
    for char in characters:
        state = CharacterState(
            character_id=char.character_id,
            field="location",
            value=f"地点{chapter_number}",
            source_version_id=version_id,
        )
        await char_repo.add_state_snapshot(state)

    return version_id


# ---------------------------------------------------------------------------
# Metrics collector
# ---------------------------------------------------------------------------


async def _collect_metrics(project_id: str) -> dict:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM summaries WHERE project_id = ?",
            (project_id,),
        )
        summary_count = (await cursor.fetchone())[0]

        cursor = await conn.execute(
            """SELECT COUNT(*) FROM character_states cs
            JOIN characters c ON cs.character_id = c.character_id
            WHERE c.project_id = ?""",
            (project_id,),
        )
        character_state_count = (await cursor.fetchone())[0]

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM chapter_versions WHERE project_id = ?",
            (project_id,),
        )
        version_count = (await cursor.fetchone())[0]

    budget_data: dict[int, dict] = {}
    rewrite_count = 0
    for ch in range(41, 51):
        versions = await ChapterVersionRepository().list_by_chapter(
            project_id, ch, include_abandoned=True
        )
        for v in versions:
            if v.generation_metadata and "context_snapshot" in v.generation_metadata:
                snap = v.generation_metadata["context_snapshot"]
                budget_data[ch] = {
                    "tokens": snap.get("estimated_tokens", 0),
                    "budget_used": round(snap.get("budget_used", 0.0), 4),
                }
            if v.generation_metadata and v.generation_metadata.get("_was_rewritten"):
                rewrite_count += 1

    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT COUNT(*) FROM setting_snapshots
            WHERE project_id = ? AND source_quote != ''""",
            (project_id,),
        )
        setting_with_quote = (await cursor.fetchone())[0]

        # 每章 settlement source_quote 数量
        # NOTE: setting_snapshots 表没有 chapter_number 列，无法直接按章分组
        # 防御性处理：若列不存在则跳过
        quotes_per_chapter: dict[int, int] = {}
        try:
            cursor = await conn.execute(
                """SELECT chapter_number, COUNT(*) FROM setting_snapshots
                WHERE project_id = ? AND source_quote != ''
                GROUP BY chapter_number""",
                (project_id,),
            )
            quotes_per_chapter = {
                row[0]: row[1] async for row in cursor
            }
        except Exception:
            pass

    return {
        "summary_count": summary_count,
        "character_state_count": character_state_count,
        "version_count": version_count,
        "budget_used_per_chapter": budget_data,
        "max_budget_used": max((d["budget_used"] for d in budget_data.values()), default=0.0),
        "rewrite_count": rewrite_count,
        "rewrite_rate": rewrite_count / 10,
        "setting_with_source_quote": setting_with_quote,
        "quotes_per_chapter": quotes_per_chapter,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    db_path = OUTPUT_DIR / "test.db"

    # 隔离：使用独立数据库 + MemorySaver
    with patch("songyan.db.connection.get_db_path", return_value=db_path):
        original_url = settings.database_url
        original_mode = settings.checkpointer_mode
        settings.database_url = f"sqlite:///{db_path}"
        settings.checkpointer_mode = "memory"

        try:
            await init_schema(db_path)

            print("=" * 60)
            print("Ch41-Ch50 真实 LLM 快速验证 — 方案 A")
            print("=" * 60)

            # Step 1: 创建种子项目
            print("\n[1/4] 创建种子项目...")
            project_id = await import_seed_project(SEED_CONFIG)
            await import_seed_chapter(project_id, SEED_CHAPTER)
            print(f"   项目 ID: {project_id}")

            # Step 2: 快速构建 Ch2-Ch40 历史
            print("\n[2/4] 构建 Ch2-Ch40 mock 历史...")
            t0 = time.monotonic()
            for ch in range(2, 41):
                await _build_chapter_history(project_id, ch)
            print(f"   耗时: {time.monotonic() - t0:.1f}s")

            # Step 3: 运行 Ch41-Ch50 真实 LLM
            print("\n[3/4] 运行 Ch41-Ch50 真实 LLM pipeline...")
            print("   （每章约 3-5 分钟，请耐心等待...）")
            t0 = time.monotonic()
            result = await run_project_pipeline(
                project_id=project_id,
                chapter_range=(41, 50),
                mode_id="webnovel",
                auto_confirm=True,
                on_failure="abort",
            )
            elapsed = time.monotonic() - t0

            # Step 4: 收集指标
            print("\n[4/4] 收集指标...")
            metrics = await _collect_metrics(project_id)

            report = {
                "validation": "Ch41-Ch50 Real LLM (方案 A)",
                "project_id": project_id,
                "chapters_completed": result.chapters_completed,
                "chapters_failed": result.chapters_failed,
                "total_duration_sec": round(elapsed, 2),
                "history_summaries": 40,
                "generated_summaries": metrics["summary_count"],
                "character_state_count": metrics["character_state_count"],
                "version_count": metrics["version_count"],
                "max_budget_used": round(metrics["max_budget_used"], 4),
                "budget_used_by_chapter": {
                    f"Ch{ch}": data for ch, data in metrics["budget_used_per_chapter"].items()
                },
                "rewrite_count": metrics["rewrite_count"],
                "rewrite_rate": f"{metrics['rewrite_rate']:.1%}",
                "setting_with_source_quote": metrics["setting_with_source_quote"],
                "quotes_per_chapter": metrics["quotes_per_chapter"],
                "status": "PASS" if not result.chapters_failed else "FAIL",
            }

            report_path = OUTPUT_DIR / "report.json"
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )

            print("\n" + "=" * 60)
            print("验证报告")
            print("=" * 60)
            print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
            print("=" * 60)
            print(f"\n报告已保存: {report_path}")

        finally:
            settings.database_url = original_url
            settings.checkpointer_mode = original_mode


if __name__ == "__main__":
    asyncio.run(main())
