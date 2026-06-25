"""Task 121p: Create project and run Ch1-Ch150 full single-run."""
from __future__ import annotations

import asyncio
import sys
import traceback
import uuid
from pathlib import Path

from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.models.project import ProjectSetting, derive_arc_boundaries
from songyan.workflows.phase2_graph import run_project_pipeline


async def main() -> None:
    await init_schema()

    project_id = uuid.uuid4().hex[:8]
    project = ProjectSetting(
        title="深空锚点",
        genre_id="scifi",
        mode_id="webnovel_intense",
        protagonist_name="林深",
        protagonist_background="前星际考古学家，因一场遗迹事故失去左腿，被学术界放逐",
        core_hook="人类在银河系边缘发现了一座不属于任何已知文明的巨型遗迹，主角是唯一一个曾进入过类似结构并活着回来的人",
        target_reader_expectation="硬核科幻+悬疑探险，要求科学细节自洽，节奏紧凑",
        target_word_count=450_000,
        tone="冷峻",
        estimated_chapters=150,
        words_per_chapter=3000,
        story_structure="serial",
        sub_genre_id="space_opera",
        arc_boundaries=derive_arc_boundaries("serial", 150),
        arc_boundaries_auto=True,
    )

    repo = ProjectRepository()
    await repo.create(project, project_id)
    print(f"Project created: {project_id}")

    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(1, 150),
            mode_id="webnovel_intense",
            auto_confirm=True,
            on_failure="retry",
        )
    except Exception:
        traceback_text = traceback.format_exc()
        crash_file = Path(f"logs/task121p/crash-{project_id}.log")
        crash_file.parent.mkdir(parents=True, exist_ok=True)
        crash_file.write_text(traceback_text, encoding="utf-8")
        print(
            f"\n=== PIPELINE EXCEPTION ===\n{traceback_text}\n==========================",
            file=sys.stderr,
        )
        print(f"Crash log written to: {crash_file}", file=sys.stderr)
        raise

    print(f"\nRun complete: {result.run_id}")
    print(f"Status: {result.final_status}")
    print(f"Completed: {len(result.chapters_completed)}/150")
    print(f"Failed: {result.chapters_failed}")
    print(f"Duration: {result.total_duration_sec:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
