"""Task 126: 候选硬门禁 enforce 模式 Ch1-Ch20 小窗口实跑验证.

用法:
    python scripts/run_126_enforce_validation.py
"""

from __future__ import annotations

import asyncio
import uuid

from songyan.db.repository import ProjectRepository
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig, ProjectSetting
from songyan.workflows.phase2_graph import run_project_pipeline

SOURCE_PROJECT_ID = "e95a1fa3"


def _enforce_gate_config() -> GateConfig:
    """Task 125 调优后的候选 enforce 配置."""
    return GateConfig(
        gate_mode="enforce",
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_p1_min_absolute=50,
        health_low_p1_anomaly_factor=1.8,
        # Task 127 重构为"历史新低 + P1 同步激增"复合条件，默认关闭。
        health_low_score_halt_enabled=False,
        health_low_streak_halt=True,
        health_low_streak_audit_window=3,
        health_low_streak_p1_limit=250,
        health_low_streak_p2_limit=1000,
        context_emergency_gate_enabled=True,
        context_emergency_single_halt=True,
        context_emergency_budget_ratio_threshold=1.3,
        context_emergency_failure_halt=True,
    )


async def main() -> None:
    source = await ProjectRepository().get(SOURCE_PROJECT_ID)
    if source is None:
        raise ValueError(f"Source project not found: {SOURCE_PROJECT_ID}")

    project_id = uuid.uuid4().hex
    project = ProjectSetting.model_validate(source.model_dump())
    await ProjectRepository().create(project, project_id)
    print(f"Created validation project: {project_id}")

    gate_config = _enforce_gate_config()
    print(f"Gate config: {gate_config.model_dump_json(indent=2)}")

    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(1, 20),
            mode_id=project.mode_id,
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
