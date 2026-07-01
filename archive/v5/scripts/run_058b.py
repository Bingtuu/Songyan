"""Task 058b 执行脚本 — 生成 Ch2~Ch30."""

import asyncio
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.workflows.phase2_graph import run_project_pipeline

PROJECT_ID = "proj-e74ef1e4"
OUTPUT_DIR = Path("projects/orbital_horror_058b")


async def main():
    print("=" * 60)
    print("Task 058b: 30 章封闭验证执行")
    print(f"Project: {PROJECT_ID}")
    print(f"Range: Ch2 ~ Ch30")
    print("=" * 60)

    t0 = time.monotonic()

    try:
        result = await run_project_pipeline(
            project_id=PROJECT_ID,
            chapter_range=(2, 30),
            mode_id="webnovel",
            auto_confirm=True,
            on_failure="retry",
            continuity_health_threshold=7.0,
        )

        duration = time.monotonic() - t0

        print("\n" + "=" * 60)
        print("运行完成")
        print("=" * 60)
        print(f"Final status: {result.final_status}")
        print(f"Completed: {result.chapters_completed}")
        print(f"Failed: {result.chapters_failed}")
        print(f"Total duration: {duration / 60:.1f} min")
        print(f"Avg per chapter: {duration / max(len(result.chapters_completed), 1) / 60:.1f} min")

        # 保存结果摘要
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        summary = {
            "project_id": PROJECT_ID,
            "final_status": result.final_status,
            "chapters_completed": result.chapters_completed,
            "chapters_failed": result.chapters_failed,
            "total_duration_sec": duration,
            "timestamp": datetime.now().isoformat(),
        }
        (OUTPUT_DIR / "run_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nSummary saved to: {OUTPUT_DIR / 'run_summary.json'}")

    except Exception as exc:
        duration = time.monotonic() - t0
        print(f"\n[FATAL] 运行失败 after {duration / 60:.1f} min")
        traceback.print_exc()

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "run_error.txt").write_text(
            f"Time: {datetime.now().isoformat()}\nDuration: {duration:.1f}s\n\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
