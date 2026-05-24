"""Core async repositories for project, character, and chapter data."""

from __future__ import annotations

import json
from datetime import datetime
from sqlite3 import Row
from typing import Any

import structlog

from songyan.db.connection import get_db
from songyan.models import (
    ChapterGoal,
    ChapterHead,
    ChapterVersion,
    Character,
    CharacterState,
    ProjectSetting,
)

logger = structlog.get_logger(__name__)


def _to_json(value: Any) -> str:
    """Convert Pydantic-friendly values to SQLite JSON text."""
    return json.dumps(_jsonable(value), ensure_ascii=False, default=str)


def _from_json(value: str | None, default: Any = None) -> Any:
    """Convert SQLite JSON text to Python values."""
    if value is None:
        return default
    return json.loads(value)


def _model_json(value: Any) -> str:
    """Serialize a Pydantic model or plain value as JSON text."""
    return _to_json(value)


def _jsonable(value: Any) -> Any:
    """Recursively convert Pydantic models in containers to JSON-ready values."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _dt(value: datetime | str | None) -> str:
    """Normalize datetime-ish values to an ISO string."""
    if isinstance(value, datetime):
        return value.isoformat()
    if value:
        return value
    return datetime.now().isoformat()


class ProjectRepository:
    """Repository for projects."""

    async def create(self, project: ProjectSetting, project_id: str) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO projects (
                    project_id, title, genre_id, mode_id, protagonist_name,
                    protagonist_background, core_hook, target_reader_expectation,
                    taboos, target_word_count, tone, reference_works
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id,
                    project.title,
                    project.genre_id,
                    project.mode_id,
                    project.protagonist_name,
                    project.protagonist_background,
                    project.core_hook,
                    project.target_reader_expectation,
                    _to_json(project.taboos),
                    project.target_word_count,
                    project.tone,
                    _to_json(project.reference_works),
                ),
            )
            await conn.commit()
        logger.info("repository.write", table="projects", operation="insert", project_id=project_id)

    async def get(self, project_id: str) -> ProjectSetting | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM projects WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return ProjectSetting(
            title=row["title"],
            genre_id=row["genre_id"],
            mode_id=row["mode_id"],
            protagonist_name=row["protagonist_name"],
            protagonist_background=row["protagonist_background"],
            core_hook=row["core_hook"],
            target_reader_expectation=row["target_reader_expectation"],
            taboos=_from_json(row["taboos"], []),
            target_word_count=row["target_word_count"],
            tone=row["tone"],
            reference_works=_from_json(row["reference_works"], []),
        )


class CharacterRepository:
    """Repository for character profiles and state snapshots."""

    async def create(self, character: Character) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO characters (
                    character_id, project_id, name, role_type, background,
                    personality_traits, goals, relationships, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    character.character_id,
                    character.project_id,
                    character.name,
                    character.role_type,
                    character.background,
                    _to_json(character.personality_traits),
                    _to_json(character.goals),
                    _to_json(character.relationships),
                    _dt(character.created_at),
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="characters",
            operation="insert",
            character_id=character.character_id,
        )

    async def get(self, character_id: str) -> Character | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM characters WHERE character_id = ?",
                (character_id,),
            )
            row = await cursor.fetchone()
        return _character_from_row(row) if row is not None else None

    async def list_by_project(self, project_id: str) -> list[Character]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM characters WHERE project_id = ? ORDER BY created_at, character_id",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [_character_from_row(row) for row in rows]

    async def add_state_snapshot(self, state: CharacterState) -> int:
        async with get_db() as conn:
            cursor = await conn.execute(
                """INSERT INTO character_states (
                    character_id, field, value, source_version_id, created_at
                ) VALUES (?, ?, ?, ?, ?)""",
                (
                    state.character_id,
                    state.field,
                    state.value,
                    state.source_version_id,
                    _dt(state.created_at),
                ),
            )
            await conn.commit()
            state_id = int(cursor.lastrowid)
        logger.info(
            "repository.write",
            table="character_states",
            operation="insert",
            character_id=state.character_id,
            state_id=state_id,
        )
        return state_id


class ChapterGoalRepository:
    """Repository for chapter goals."""

    async def create(self, goal: ChapterGoal, goal_id: str, project_id: str) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO chapter_goals (
                    goal_id, project_id, chapter_number, previous_summary,
                    target_events, emotional_arc, hooks, obligations,
                    word_count_target, chapter_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    goal_id,
                    project_id,
                    goal.chapter_number,
                    goal.previous_summary,
                    _to_json(goal.target_events),
                    goal.emotional_arc,
                    _to_json(goal.hooks),
                    _to_json(goal.obligations),
                    goal.word_count_target,
                    goal.chapter_type,
                ),
            )
            await conn.commit()
        logger.info("repository.write", table="chapter_goals", operation="insert", goal_id=goal_id)

    async def get_by_chapter(self, project_id: str, chapter_number: int) -> ChapterGoal | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM chapter_goals
                WHERE project_id = ? AND chapter_number = ?
                ORDER BY created_at DESC, goal_id DESC
                LIMIT 1""",
                (project_id, chapter_number),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return ChapterGoal(
            chapter_number=row["chapter_number"],
            previous_summary=row["previous_summary"],
            target_events=_from_json(row["target_events"], []),
            emotional_arc=row["emotional_arc"],
            hooks=_from_json(row["hooks"], []),
            obligations=_from_json(row["obligations"], []),
            word_count_target=row["word_count_target"],
            chapter_type=row["chapter_type"],
        )


class ChapterVersionRepository:
    """Repository for immutable chapter versions."""

    async def create(self, version: ChapterVersion) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO chapter_versions (
                    version_id, project_id, chapter_number, version_number,
                    version_type, content, word_count, scenes, generation_metadata,
                    creative_brief_id, parent_version_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    version.version_id,
                    version.project_id,
                    version.chapter_number,
                    version.version_number,
                    version.version_type,
                    version.content,
                    version.word_count,
                    _to_json(version.scenes),
                    _to_json(version.generation_metadata),
                    version.creative_brief_id,
                    version.parent_version_id,
                    _dt(version.created_at),
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="chapter_versions",
            operation="insert",
            version_id=version.version_id,
        )

    async def get(self, version_id: str) -> ChapterVersion | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM chapter_versions WHERE version_id = ?",
                (version_id,),
            )
            row = await cursor.fetchone()
        return _version_from_row(row) if row is not None else None

    async def list_by_chapter(self, project_id: str, chapter_number: int) -> list[ChapterVersion]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM chapter_versions
                WHERE project_id = ? AND chapter_number = ?
                ORDER BY version_number""",
                (project_id, chapter_number),
            )
            rows = await cursor.fetchall()
        return [_version_from_row(row) for row in rows]

    async def get_chain(self, version_id: str) -> list[ChapterVersion]:
        chain: list[ChapterVersion] = []
        current_id: str | None = version_id
        while current_id is not None:
            current = await self.get(current_id)
            if current is None:
                break
            chain.append(current)
            current_id = current.parent_version_id
        return list(reversed(chain))


class ChapterHeadRepository:
    """Repository for chapter heads."""

    async def get(self, project_id: str, chapter_number: int) -> ChapterHead | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM chapter_heads WHERE project_id = ? AND chapter_number = ?",
                (project_id, chapter_number),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return ChapterHead(
            project_id=row["project_id"],
            chapter_number=row["chapter_number"],
            current_version_id=row["current_version_id"],
            accepted_version_id=row["accepted_version_id"],
            status=row["status"],
            updated_at=row["updated_at"],
        )

    async def update(self, head: ChapterHead) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO chapter_heads (
                    project_id, chapter_number, current_version_id,
                    accepted_version_id, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, chapter_number) DO UPDATE SET
                    current_version_id = excluded.current_version_id,
                    accepted_version_id = excluded.accepted_version_id,
                    status = excluded.status,
                    updated_at = excluded.updated_at""",
                (
                    head.project_id,
                    head.chapter_number,
                    head.current_version_id,
                    head.accepted_version_id,
                    head.status,
                    _dt(head.updated_at),
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="chapter_heads",
            operation="upsert",
            project_id=head.project_id,
            chapter_number=head.chapter_number,
        )


def _character_from_row(row: Row) -> Character:
    return Character(
        character_id=row["character_id"],
        project_id=row["project_id"],
        name=row["name"],
        role_type=row["role_type"],
        background=row["background"],
        personality_traits=_from_json(row["personality_traits"], []),
        goals=_from_json(row["goals"], []),
        relationships=_from_json(row["relationships"], {}),
        created_at=row["created_at"],
    )


def _version_from_row(row: Row) -> ChapterVersion:
    return ChapterVersion(
        version_id=row["version_id"],
        project_id=row["project_id"],
        chapter_number=row["chapter_number"],
        version_number=row["version_number"],
        version_type=row["version_type"],
        content=row["content"],
        word_count=row["word_count"],
        scenes=_from_json(row["scenes"], []),
        generation_metadata=_from_json(row["generation_metadata"], {}),
        creative_brief_id=row["creative_brief_id"],
        parent_version_id=row["parent_version_id"],
        created_at=row["created_at"],
    )
