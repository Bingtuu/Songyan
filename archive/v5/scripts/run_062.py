"""Task 062: End-to-end verification run — Ch31-Ch40."""

import asyncio
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.db.migrations import init_schema
from songyan.workflows.phase1_graph import reset_checkpointer
from songyan.workflows.phase2_graph import run_project_pipeline

PROJECT_ID = "proj-e74ef1e4"
OUTPUT_DIR = Path("projects/orbital_horror_062")


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_dir = OUTPUT_DIR / "chapters"
    md_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Task 062: End-to-end verification — Ch31-Ch40")
    print("=" * 60)

    await init_schema()
    await reset_checkpointer()

    t0 = time.monotonic()
    try:
        result = await run_project_pipeline(
            project_id=PROJECT_ID,
            chapter_range=(31, 40),
            mode_id="webnovel",
            auto_confirm=True,
            on_failure="retry",
            continuity_health_threshold=7.0,
        )

        duration = time.monotonic() - t0
        print(f"Final status: {result.final_status}")
        print(f"Completed: {result.chapters_completed}")
        print(f"Failed: {result.chapters_failed}")
        print(f"Duration: {duration/60:.1f} min")

        summary = {"project_id": PROJECT_ID, "final_status": result.final_status,
            "chapters_completed": result.chapters_completed,
            "chapters_failed": result.chapters_failed,
            "total_duration_sec": duration,
            "timestamp": datetime.now().isoformat()}
        (OUTPUT_DIR / "run_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    except Exception as exc:
        duration = time.monotonic() - t0
        print(f"FATAL after {duration/60:.1f} min")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())