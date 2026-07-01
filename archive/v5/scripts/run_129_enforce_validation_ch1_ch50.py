"""Task 129: 候选硬门禁 enforce 模式 Ch1-Ch50 实跑验证.

用法:
    source .env && python scripts/run_129_enforce_validation_ch1_ch50.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.db.migrations import init_schema
from songyan.db.repository import CharacterRepository, ProjectRepository
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig, ProjectSetting
from songyan.models.character import Character, DialogueStyleCard
from songyan.workflows.phase2_graph import run_project_pipeline


def _enforce_gate_config() -> GateConfig:
    """Task 125 + Task 127 调优后的候选 enforce 配置."""
    return GateConfig(
        gate_mode="enforce",
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_p1_min_absolute=50,
        health_low_p1_anomaly_factor=1.8,
        health_low_streak_halt=True,
        health_low_streak_audit_window=3,
        health_low_streak_p1_limit=250,
        health_low_streak_p2_limit=1000,
        # Task 127 重构后的 score halt 复合条件
        health_low_score_halt_enabled=True,
        health_low_score_halt_window=3,
        health_low_score_halt_min_p1=20,
        health_low_score_halt_anomaly_factor=1.8,
        context_emergency_gate_enabled=True,
        context_emergency_single_halt=True,
        context_emergency_budget_ratio_threshold=1.3,
        context_emergency_failure_halt=True,
    )


async def _seed_project(project_id: str) -> None:
    """创建与集成测试同配置的 xuanhuan + webnovel 干净项目."""
    project = ProjectSetting(
        title="Task129 硬门禁 enforce 验证",
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
    print(f"Created validation project: {project_id}")

    gate_config = _enforce_gate_config()
    print(f"Gate config: {gate_config.model_dump_json(indent=2)}")

    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(1, 50),
            mode_id="webnovel",
            auto_confirm=True,
            on_failure="abort",
            gate_config=gate_config,
        )
        print("\n=== Result ===")
        print(f"Completed chapters: {result.chapters_completed}")
        print(f"Failed chapters: {result.chapters_failed}")
        print(f"Total cost: {result.total_cost}")
        print(f"Total duration: {result.total_duration_sec:.1f}s")
        print(f"Run log: logs/chapter_runs/run-{project_id}.jsonl")
    except AutoHaltException as exc:
        print("\n=== AutoHalt / Gate triggered ===")
        print(f"Last chapter: {exc.last_chapter}")
        print(f"Reason: {exc.reason}")
        print(f"Full message: {exc}")
        print(f"Run log: logs/chapter_runs/run-{project_id}.jsonl")


if __name__ == "__main__":
    asyncio.run(main())
