"""Task 058b 执行脚本 — 逐章运行，支持 resume."""

import asyncio
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.db.connection import get_db
from songyan.workflows.phase2_graph import run_project_pipeline

PROJECT_ID = "proj-e74ef1e4"
OUTPUT_DIR = Path("projects/orbital_horror_058b")
PROGRESS_FILE = OUTPUT_DIR / "058b_progress.json"


async def get_last_completed_chapter() -> int:
    """查询数据库获取已完成的最后一章（从 chapter_heads 表查询 accepted 状态）."""
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT MAX(chapter_number) FROM chapter_heads
            WHERE project_id = ? AND status = 'accepted'""",
            (PROJECT_ID,),
        )
        row = await cursor.fetchone()
    return row[0] or 1


async def run_single_chapter(chapter_number: int) -> dict:
    """运行单章."""
    print(f"\n{'='*60}")
    print(f"Chapter {chapter_number}")
    print(f"{'='*60}")

    t0 = time.monotonic()
    result = await run_project_pipeline(
        project_id=PROJECT_ID,
        chapter_range=(chapter_number, chapter_number),
        mode_id="webnovel",
        auto_confirm=True,
        on_failure="retry",
        continuity_health_threshold=7.0,
    )
    elapsed = time.monotonic() - t0

    success = chapter_number not in result.chapters_failed
    status = "OK" if success else "FAIL"
    print(f"[{status}] {elapsed:.1f}s | status={result.final_status}")

    return {
        "chapter": chapter_number,
        "success": success,
        "elapsed_sec": elapsed,
        "final_status": result.final_status,
        "failed": result.chapters_failed,
    }


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 加载已有进度
    progress = []
    if PROGRESS_FILE.exists():
        progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        print(f"Loaded progress: {len(progress)} chapters done")

    last_done = await get_last_completed_chapter()
    start_ch = max(last_done + 1, 2)
    end_ch = 30

    print(f"Resume from Ch{start_ch} to Ch{end_ch}")
    print(f"Already completed: Ch1 ~ Ch{last_done}")

    for ch in range(start_ch, end_ch + 1):
        try:
            record = await run_single_chapter(ch)
            progress.append(record)
        except Exception as exc:
            print(f"[ERROR] Chapter {ch} failed with exception:")
            traceback.print_exc()
            progress.append({
                "chapter": ch,
                "success": False,
                "error": str(exc),
                "elapsed_sec": 0,
            })
            # 保存进度后退出，下次 resume 会重试这章
            PROGRESS_FILE.write_text(
                json.dumps(progress, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            sys.exit(1)

        # 每章保存进度
        PROGRESS_FILE.write_text(
            json.dumps(progress, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # 全部完成
    total_elapsed = sum(p.get("elapsed_sec", 0) for p in progress)
    ok_count = sum(1 for p in progress if p.get("success"))

    print("\n" + "=" * 60)
    print("ALL DONE")
    print("=" * 60)
    print(f"Completed: {ok_count} / {len(progress)}")
    print(f"Total time: {total_elapsed / 60:.1f} min")
    print(f"Avg per chapter: {total_elapsed / max(len(progress), 1) / 60:.1f} min")


if __name__ == "__main__":
    asyncio.run(main())
