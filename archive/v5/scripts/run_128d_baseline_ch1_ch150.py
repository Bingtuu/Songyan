"""Task 128d: Ch1-Ch150 baseline 重跑验证.

在默认配置（observe，无 enforce）下重新跑 Ch1-Ch150，验证 128a-128c 修复后：
- QG false 章节降级接受（degraded_accept）不终止 run
- Ch1-Ch10 质量爬坡减少开局期阻断
- readability 专精 revision 路径生效
- 无状态污染或连续性断裂

用法:
    source .env && python scripts/run_128d_baseline_ch1_ch150.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.db.migrations import init_schema
from songyan.db.repository import CharacterRepository, ProjectRepository
from songyan.exceptions import AutoHaltException
from songyan.models import ProjectSetting
from songyan.models.character import Character, DialogueStyleCard
from songyan.workflows.phase2_graph import run_project_pipeline


async def _seed_project(project_id: str) -> None:
    """创建与 121q baseline 同配置的 xuanhuan + webnovel 干净项目."""
    project = ProjectSetting(
        title="Task128d Ch1-Ch150 baseline 重跑",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="林动",
        protagonist_background="出身卑微的少年",
        core_hook="废柴逆袭",
        target_reader_expectation="热血爽文",
        taboos=["绿帽"],
        target_word_count=100_000,
        tone="热血",
        estimated_chapters=150,
        words_per_chapter=3000,
        story_structure="serial",
    )
    await ProjectRepository().create(project, project_id)

    char_id = f"char-{project_id[:8]}"
    char = Character(
        character_id=char_id,
        project_id=project_id,
        name="林动",
        role_type="protagonist",
        background="出身卑微",
        dialogue_style_card=DialogueStyleCard(
            character_id=char_id,
            project_id=project_id,
            sentence_length_preference="short",
            common_openers=["哼", "小子"],
            anger_expression="冷笑+反问",
            pause_habit="愤怒时停顿",
        ),
    )
    await CharacterRepository().create(char)


async def main() -> None:
    await init_schema()

    project_id = uuid.uuid4().hex
    await _seed_project(project_id)
    print(f"Created baseline project: {project_id}")

    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(1, 150),
            mode_id="webnovel",
            auto_confirm=True,
            on_failure="abort",
        )
        print("\n=== Result ===")
        print(f"Final status: {result.final_status}")
        print(f"Completed chapters: {len(result.chapters_completed)}")
        print(f"Failed chapters: {result.chapters_failed}")
        print(f"Total duration: {result.total_duration_sec:.1f}s")
        print(f"Run log: logs/chapter_runs/run-{project_id}.jsonl")

        # 简单统计 degraded_accept / emergency / auto-halt
        log_path = Path(f"logs/chapter_runs/run-{project_id}.jsonl")
        if log_path.exists():
            degraded = 0
            emergency = 0
            qg_fail = 0
            with log_path.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("degraded_accept"):
                        degraded += 1
                    if rec.get("context_emergency"):
                        emergency += 1
                    if rec.get("quality_gate_passed") is False:
                        qg_fail += 1
            print("\n=== Run metrics ===")
            print(f"Degraded accept chapters: {degraded}")
            print(f"ContextEmergency chapters: {emergency}")
            print(f"Quality gate failed chapters: {qg_fail}")

    except AutoHaltException as exc:
        print("\n=== AutoHalt triggered ===")
        print(f"Last chapter: {exc.last_chapter}")
        print(f"Reason: {exc.reason}")
        print(f"Run log: logs/chapter_runs/run-{project_id}.jsonl")


if __name__ == "__main__":
    asyncio.run(main())
