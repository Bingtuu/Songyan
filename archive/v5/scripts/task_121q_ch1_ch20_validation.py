"""Task 121q: Ch1-Ch20 validation after 0.82 dynamic threshold + degraded_accept fix.

支持断点续跑：若进程中断，重新运行同一脚本会自动复用 project_id
并跳过已 accepted 的章节，从中断处继续。
"""
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

_PROJECT_ID_FILE = Path("logs/task121q/.last_validation_project_id")


async def main() -> None:
    await init_schema()

    # 断点续跑：若存在上次 project_id 则复用
    if _PROJECT_ID_FILE.exists():
        project_id = _PROJECT_ID_FILE.read_text().strip()
        print(f"Resuming existing project: {project_id}")
    else:
        project_id = uuid.uuid4().hex[:8]
        _PROJECT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PROJECT_ID_FILE.write_text(project_id)

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
            chapter_range=(1, 20),
            mode_id="webnovel_intense",
            auto_confirm=True,
            on_failure="retry",
        )
    except Exception as exc:
        # 记录完整错误堆栈到 stderr 和日志文件
        tb = traceback.format_exc()
        print(f"\n=== PIPELINE EXCEPTION ===\n{tb}\n==========================", file=sys.stderr)
        _log_crash(project_id, tb)
        raise

    print(f"\nRun complete: {result.run_id}")
    print(f"Status: {result.final_status}")
    print(f"Completed: {len(result.chapters_completed)}/20")
    print(f"Failed: {result.chapters_failed}")
    print(f"Duration: {result.total_duration_sec:.1f}s")

    # 成功后清理断点标记
    if result.final_status == "completed" and _PROJECT_ID_FILE.exists():
        _PROJECT_ID_FILE.unlink()


def _log_crash(project_id: str, traceback_str: str) -> None:
    crash_file = Path(f"logs/task121q/crash-{project_id}.log")
    crash_file.parent.mkdir(parents=True, exist_ok=True)
    crash_file.write_text(traceback_str, encoding="utf-8")
    print(f"Crash log written to: {crash_file}")


if __name__ == "__main__":
    asyncio.run(main())
