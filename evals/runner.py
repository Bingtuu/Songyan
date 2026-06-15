"""评测运行器 — 种子项目导入 + 单章生成 + 结果收集."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import structlog

from evals.models import EvaluationResult, SeedProjectConfig
from songyan.db.connection import get_db
from songyan.db.context_repo import SummaryRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.review_repo import ReviewReportRepository
from songyan.db.settlement_repo import (
    NumericalLedgerRepository,
    SettingSnapshotRepository,
)
from songyan.models import (
    ChapterHead,
    ChapterSummary,
    ChapterVersion,
    Character,
    CharacterState,
    NewSetting,
    NumericalUpdate,
    ProjectSetting,
)
from songyan.workflows._helpers import new_id
from songyan.workflows.phase1_graph import (
    resume_human_confirm,
    run_chapter_pipeline,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Seed project import
# =============================================================================


async def import_seed_project(config_path: str) -> str:
    """导入种子项目配置，返回 project_id.

    注意：角色初始状态（character_states）不在此函数写入，
    因为 source_version_id 必须关联到 chapter_versions 表中的真实版本。
    请在 import_seed_chapter 之后调用 _import_seed_character_states().
    """
    config = SeedProjectConfig.model_validate_json(Path(config_path).read_text(encoding="utf-8"))
    project_id = new_id("proj")

    # 1. 创建项目
    project = ProjectSetting(
        title=config.project_name,
        genre_id=config.genre_id,
        mode_id=config.mode_id,
        protagonist_name=_extract_protagonist_name(config),
        protagonist_background="",
        core_hook=config.description[:200],
        target_reader_expectation="",
        taboos=[],
        target_word_count=100_000,
        tone="",
        reference_works=[],
    )
    await ProjectRepository().create(project, project_id)
    logger.info("evals.project_imported", project_id=project_id, name=config.project_name)

    # 2. 创建角色（不写入状态快照，留到种子章节导入后）
    from songyan.models.character import DialogueStyleCard
    char_repo = CharacterRepository()
    for seed_char in config.characters:
        char_id = new_id("char")
        char = Character(
            character_id=char_id,
            project_id=project_id,
            name=seed_char.name,
            role_type=seed_char.role or "protagonist",
            background=seed_char.description,
            personality_traits=[],
            goals=[],
            relationships={},
            dialogue_style_card=DialogueStyleCard(
                character_id=char_id,
                project_id=project_id,
                sentence_length_preference="mixed",
                common_openers=[],
                common_closers=[],
            ),
        )
        await char_repo.create(char)

    # 3. 创建初始设定
    setting_repo = SettingSnapshotRepository()
    for seed_setting in config.initial_settings:
        setting = NewSetting(
            setting_name=seed_setting.setting_name,
            description=seed_setting.description,
            source_quote=seed_setting.source_quote,
            setting_key=seed_setting.setting_key,
        )
        setting_id = new_id("set")
        await setting_repo.create(setting, project_id, setting_id)

    # 4. 数值体系初始 ledger（玄幻必填）
    if config.numerical_system:
        await _init_numerical_ledgers(config, project_id, char_repo)

    logger.info(
        "evals.seed_project_done",
        project_id=project_id,
        character_count=len(config.characters),
    )
    return project_id


def _extract_protagonist_name(config: SeedProjectConfig) -> str:
    """从角色列表中提取主角姓名."""
    for c in config.characters:
        if c.role == "protagonist":
            return c.name
    return config.characters[0].name if config.characters else "主角"


async def _init_numerical_ledgers(
    config: SeedProjectConfig,
    project_id: str,
    char_repo: CharacterRepository,
) -> None:
    """为数值体系创建初始 ledger 记录."""
    numerical_repo = NumericalLedgerRepository()
    characters = await char_repo.list_by_project(project_id)
    seed_char_map = {sc.name: sc for sc in config.characters}

    for char in characters:
        seed_char = seed_char_map.get(char.name)
        if seed_char is None:
            continue
        for field, value in (seed_char.initial_state or {}).items():
            # 仅对数值类型的字段创建 ledger
            try:
                opening = float(value)
            except (ValueError, TypeError):
                continue
            update = NumericalUpdate(
                character_id=char.character_id,
                attribute_name=field,
                opening_value=opening,
                closing_value=opening,
            )
            ledger_id = new_id("num")
            await numerical_repo.create(update, project_id, 0, ledger_id)


# =============================================================================
# Seed chapter import
# =============================================================================


async def import_seed_chapter(
    project_id: str,
    chapter_path: str,
    chapter_number: int = 1,
) -> str:
    """导入种子章节，返回 version_id."""
    content = Path(chapter_path).read_text(encoding="utf-8")
    word_count = len(content)

    version_id = new_id("v")
    version = ChapterVersion(
        version_id=version_id,
        project_id=project_id,
        chapter_number=chapter_number,
        version_number=1,
        version_type="accepted",
        content=content,
        word_count=word_count,
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

    # 为种子章节写入 summary（Chapter 2 的 goal_planner / context_manager 依赖此前置摘要）
    await _write_seed_summary(project_id, chapter_number, content)

    logger.info(
        "evals.seed_chapter_imported",
        project_id=project_id,
        chapter_number=chapter_number,
        version_id=version_id,
        word_count=word_count,
    )
    return version_id


async def _write_seed_summary(project_id: str, chapter_number: int, content: str) -> None:
    """为种子章节生成一个简易 summary 并写入 DB."""
    # 取正文前 200 字作为剧情摘要
    preview = content[:200].replace("\n", " ")
    summary = ChapterSummary(
        chapter_number=chapter_number,
        summary=f"种子章节：{preview}...",
        key_events=["故事开端"],
        characters_appeared=[],
        emotional_tone="",
    )

    summary_id = new_id("sum")
    await SummaryRepository().create(summary, project_id, summary_id)


# =============================================================================
# Run evaluation
# =============================================================================


async def _import_seed_character_states(
    project_id: str,
    config: SeedProjectConfig,
    source_version_id: str,
) -> None:
    """在种子章节导入后，用真实 version_id 写入角色初始状态快照."""
    char_repo = CharacterRepository()
    characters = await char_repo.list_by_project(project_id)

    for char in characters:
        # 找到对应的 seed_char 配置
        seed_char = next((sc for sc in config.characters if sc.name == char.name), None)
        if seed_char is None:
            continue
        for field, value in (seed_char.initial_state or {}).items():
            state = CharacterState(
                character_id=char.character_id,
                field=field,
                value=str(value),
                source_version_id=source_version_id,
            )
            await char_repo.add_state_snapshot(state)

    logger.info("evals.character_states_imported", project_id=project_id, count=len(characters))


async def run_seed_project(
    project_config_path: str,
    seed_chapter_path: str,
    output_dir: str,
    auto_accept: bool = True,
    target_chapter_number: int = 2,
) -> EvaluationResult:
    """运行单个种子项目的评测（mock LLM 模式）.

    1. 导入项目配置到 SQLite
    2. 将种子章节作为 chapter 1 写入 DB（含 summary + character_states）
    3. 调用 run_chapter_pipeline 生成 chapter 2（在 human_confirm 中断）
    4. 若 auto_accept=True，调用 resume_human_confirm("accept") 继续 settlement/summary
    5. 收集原始结果并持久化
    6. 返回 EvaluationResult
    """
    logs: list[str] = []
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config = SeedProjectConfig.model_validate_json(
        Path(project_config_path).read_text(encoding="utf-8")
    )

    start_time = time.perf_counter()

    # Step 1: 导入项目
    project_id = await import_seed_project(project_config_path)
    logs.append(f"Imported project: {project_id}")

    # Step 2: 导入种子章节
    seed_version_id = await import_seed_chapter(project_id, seed_chapter_path, chapter_number=1)
    logs.append(f"Imported seed chapter from {seed_chapter_path}")

    # Step 2b: 补充写入角色初始状态（使用种子章节的 version_id 作为 source_version_id）
    await _import_seed_character_states(project_id, config, seed_version_id)
    logs.append(f"Imported character states with source_version_id={seed_version_id}")

    # Step 3: 运行 Chapter 2 生成（mock LLM 模式下会在 human_confirm 中断）
    thread_id = f"thread-{uuid.uuid4().hex[:8]}"
    state = await run_chapter_pipeline(
        project_id=project_id,
        chapter_number=target_chapter_number,
        mode_id=config.mode_id,
        thread_id=thread_id,
    )
    logs.append(f"Pipeline reached human_confirm (thread_id={thread_id})")

    # Step 3b: 自动接受
    final_state: dict[str, Any] = {}
    if auto_accept and "__interrupt__" in state:
        final_state = await resume_human_confirm(thread_id, "accept")
        logs.append(f"Auto-accepted, status={final_state.get('status')}")
    else:
        final_state = state

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # Step 4: 收集原始结果
    version_id = final_state.get("current_version_id", "")
    report_id = final_state.get("review_report_id", "")
    settlement_id = final_state.get("settlement_id") or ""
    summary_id = final_state.get("summary_id") or ""
    success = final_state.get("status") == "done"

    # Step 5: 持久化原始结果
    await _persist_outputs(
        output_path=output_path,
        project_id=project_id,
        version_id=version_id,
        report_id=report_id,
        settlement_id=settlement_id,
        summary_id=summary_id,
        chapter_number=target_chapter_number,
    )

    # V4.0: 生命周期状态统计
    lifecycle_stats = await _collect_lifecycle_stats(project_id)

    result = EvaluationResult(
        project_id=project_id,
        project_name=config.project_name,
        genre_id=config.genre_id,
        mode_id=config.mode_id,
        seed_config_path=project_config_path,
        seed_chapter_path=seed_chapter_path,
        success=success,
        chapter_version_id=version_id,
        merged_review_report_id=report_id,
        settlement_id=settlement_id,
        summary_id=summary_id,
        duration_ms=duration_ms,
        metrics=lifecycle_stats,
        logs=logs,
        output_dir=str(output_path),
    )

    result_path = output_path / "result.json"
    result_path.write_text(
        result.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(
        "evals.run_complete",
        project_id=project_id,
        success=success,
        duration_ms=duration_ms,
        lifecycle_stats=lifecycle_stats,
    )
    return result


async def _persist_outputs(
    output_path: Path,
    project_id: str,
    version_id: str,
    report_id: str,
    settlement_id: str,
    summary_id: str,
    chapter_number: int = 2,
) -> None:
    """将评测原始产物持久化到 output_dir."""
    # Chapter v2 正文
    if version_id:
        version = await ChapterVersionRepository().get(version_id)
        if version:
            (output_path / "chapter_v2.md").write_text(version.content, encoding="utf-8")

    # Review report
    if report_id:
        report = await ReviewReportRepository().get_by_version(version_id)
        if report:
            (output_path / "review_report.json").write_text(
                report.model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    # Settlement — 从 DB 重建已应用的数据摘要
    if settlement_id:
        settlement_data = await _build_settlement_output(
            project_id, version_id, chapter_number=chapter_number
        )
        (output_path / "settlement.json").write_text(
            json.dumps(settlement_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Summary
    if summary_id:
        summaries = await SummaryRepository().list_recent(
            project_id, before_chapter=chapter_number + 1, limit=1
        )
        if summaries:
            (output_path / "summary.json").write_text(
                summaries[0].model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )


async def _collect_lifecycle_stats(project_id: str) -> dict[str, int]:
    """收集项目下所有生命周期表的状态分布统计.

    V4.0 Task 087: 用于决策门 0 的数据量对比。
    """
    stats: dict[str, int] = {}
    tables = [
        ("setting_snapshots", "settings"),
        ("foreshadowings", "foreshadowings"),
        ("human_marks", "marks"),
    ]
    async with get_db() as conn:
        for table, key in tables:
            for status in ("active", "dormant", "archived"):
                cursor = await conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE project_id = ? AND lifecycle_status = ?",  # noqa: S608
                    (project_id, status),
                )
                row = await cursor.fetchone()
                stats[f"{key}_{status}"] = row[0] if row else 0

        # character_states 无 project_id，需 JOIN characters
        for status in ("active", "dormant", "archived"):
            cursor = await conn.execute(
                """SELECT COUNT(*) FROM character_states cs
                JOIN characters c ON cs.character_id = c.character_id
                WHERE c.project_id = ? AND cs.lifecycle_status = ?""",
                (project_id, status),
            )
            row = await cursor.fetchone()
            stats[f"character_states_{status}"] = row[0] if row else 0

    return stats


async def _build_settlement_output(
    project_id: str, version_id: str, chapter_number: int = 2
) -> dict[str, Any]:
    """从 DB 重建 settlement 已应用的数据摘要."""
    output: dict[str, Any] = {
        "version_id": version_id,
        "character_updates": [],
        "new_settings": [],
        "numerical_updates": [],
    }

    # 1. 角色状态更新（取 source_version_id 匹配的记录）
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT character_id, field, value
               FROM character_states
               WHERE source_version_id = ?
               ORDER BY character_id, field""",
            (version_id,),
        )
        rows = await cursor.fetchall()
        output["character_updates"] = [
            {"character_id": r[0], "field": r[1], "new_value": r[2]} for r in rows
        ]

    # 2. 新设定登记（取该 project 下最新创建的 setting_snapshots）
    setting_repo = SettingSnapshotRepository()
    settings = await setting_repo.list_by_project(project_id)
    # 简单过滤：只保留有 setting_key 的（seed 阶段的 setting_key 可能为空）
    output["new_settings"] = [
        {
            "setting_key": s.setting_key,
            "setting_name": s.setting_name,
            "description": s.description,
            "source_quote": s.source_quote,
        }
        for s in settings
        if s.setting_key
    ]

    # 3. 数值变更
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT character_id, attribute_name, opening_value, closing_value
               FROM numerical_ledgers
               WHERE project_id = ? AND chapter_number = ?
               ORDER BY character_id, attribute_name""",
            (project_id, chapter_number),
        )
        rows = await cursor.fetchall()
        output["numerical_updates"] = [
            {
                "character_id": r[0],
                "attribute_name": r[1],
                "opening_value": r[2],
                "closing_value": r[3],
            }
            for r in rows
        ]

    return output
