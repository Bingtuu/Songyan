"""Workflow 辅助函数 — 数据加载和上下文组装."""

from __future__ import annotations

import uuid
from sqlite3 import Row

from songyan.db.connection import get_db
from songyan.db.context_repo import CharacterStateRepository, SummaryRepository
from songyan.db.repository import (
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.review_repo import CreativeBriefRepository, ReviewReportRepository
from songyan.db.settlement_repo import (
    ForeshadowingRepository,
    SettingSnapshotRepository,
)
from songyan.genres.loader import load_genre_profile
from songyan.models import (
    ChapterGoal,
    ChapterVersion,
    ContextPackage,
    CreativeBrief,
    LLMAuditResult,
    MergedReviewReport,
    ProjectSetting,
    RuleAuditResult,
)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def load_project(project_id: str) -> ProjectSetting | None:
    return await ProjectRepository().get(project_id)


async def load_characters(project_id: str) -> list:
    return await CharacterRepository().list_by_project(project_id)


async def load_character_states(project_id: str) -> list:
    return await CharacterStateRepository().list_latest_by_project(project_id)


async def load_recent_summaries(project_id: str, chapter_number: int) -> list:
    return await SummaryRepository().list_recent(project_id, chapter_number)


async def load_active_foreshadowings(project_id: str) -> list:
    return await ForeshadowingRepository().list_active(project_id)


async def load_setting_snapshots(project_id: str) -> list:
    return await SettingSnapshotRepository().list_by_project(project_id)


async def load_chapter_goal(goal_id: str) -> ChapterGoal | None:
    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            "SELECT * FROM chapter_goals WHERE goal_id = ?",
            (goal_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    import json

    from songyan.models import ChapterGoal

    return ChapterGoal(
        chapter_number=row["chapter_number"],
        previous_summary=row["previous_summary"] or "",
        target_events=json.loads(row["target_events"] or "[]"),
        emotional_arc=row["emotional_arc"] or "",
        hooks=json.loads(row["hooks"] or "[]"),
        obligations=json.loads(row["obligations"] or "[]"),
        word_count_target=row["word_count_target"] or 3000,
        chapter_type=row["chapter_type"] or "",
    )


async def load_creative_brief(brief_id: str) -> CreativeBrief | None:
    return await CreativeBriefRepository().get(brief_id)


async def load_version(version_id: str) -> ChapterVersion | None:
    return await ChapterVersionRepository().get(version_id)


async def load_merged_report(version_id: str) -> MergedReviewReport | None:
    """加载指定版本的最新合并审查报告."""
    return await ReviewReportRepository().get_by_version(version_id)


async def load_latest_audits(
    version_id: str,
) -> tuple[RuleAuditResult | None, LLMAuditResult | None]:
    """加载指定版本的最新 rule 和 llm 审计结果."""
    from songyan.db.repository import _from_json

    rule_result: RuleAuditResult | None = None
    llm_result: LLMAuditResult | None = None

    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            """SELECT audit_type, rule_audit_result, llm_audit_result
            FROM review_reports
            WHERE chapter_version_id = ?
            ORDER BY created_at DESC""",
            (version_id,),
        )
        rows = await cursor.fetchall()

    for row in rows:
        if rule_result is None:
            rule_data = _from_json(row["rule_audit_result"], {})
            if rule_data:
                rule_result = RuleAuditResult.model_validate(rule_data)
        if llm_result is None:
            llm_data = _from_json(row["llm_audit_result"], {})
            if llm_data:
                llm_result = LLMAuditResult.model_validate(llm_data)
        if rule_result is not None and llm_result is not None:
            break

    return rule_result, llm_result


async def assemble_context_package(
    project_id: str,
    chapter_number: int,
    chapter_goal: ChapterGoal,
    creative_brief: CreativeBrief | None,
) -> ContextPackage:
    """组装 ContextPackage — 从 DB 加载所有依赖."""
    from songyan.agents.context_manager import assemble_context_package as _assemble
    from songyan.creative_modes.registry import load_creative_mode_profile

    project = await load_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    genre_profile = load_genre_profile(project.genre_id)
    mode_profile = load_creative_mode_profile(project.mode_id)

    return await _assemble(
        chapter_goal=chapter_goal,
        creative_brief=creative_brief,
        genre_profile=genre_profile,
        mode_profile=mode_profile,
        project=project,
        characters=await load_characters(project_id),
        character_states=await load_character_states(project_id),
        recent_summaries=await load_recent_summaries(project_id, chapter_number),
        active_foreshadowings=await load_active_foreshadowings(project_id),
        setting_snapshots=await load_setting_snapshots(project_id),
    )
