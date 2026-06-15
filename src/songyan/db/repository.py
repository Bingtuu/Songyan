"""Core async repositories for project, character, and chapter data."""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from sqlite3 import Row
from typing import TYPE_CHECKING, Any

import structlog

from songyan.db.connection import get_db
from songyan.utils.json_helpers import (
    from_json as _from_json,
)
from songyan.utils.json_helpers import (
    to_json as _to_json,
)

if TYPE_CHECKING:
    import aiosqlite
from songyan.models import (
    ChapterGoal,
    ChapterHead,
    ChapterVersion,
    Character,
    CharacterState,
    ProjectSetting,
)

logger = structlog.get_logger(__name__)


def _is_sqlite_locked(exc: sqlite3.OperationalError) -> bool:
    return "database is locked" in str(exc).lower()


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

    async def create(
        self, project: ProjectSetting, project_id: str, conn: aiosqlite.Connection | None = None
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO projects (
                    project_id, title, genre_id, mode_id, protagonist_name,
                    protagonist_background, core_hook, target_reader_expectation,
                    taboos, target_word_count, tone, reference_works,
                    arc_boundaries, volume_boundaries,
                    estimated_chapters, words_per_chapter, story_structure,
                    sub_genre_id, arc_boundaries_auto
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    _to_json(project.arc_boundaries),
                    _to_json(project.volume_boundaries),
                    project.estimated_chapters,
                    project.words_per_chapter,
                    project.story_structure,
                    project.sub_genre_id,
                    int(project.arc_boundaries_auto),
                ),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
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
            arc_boundaries=_from_json(row["arc_boundaries"], []),
            volume_boundaries=_from_json(row["volume_boundaries"], []),
            estimated_chapters=row["estimated_chapters"],
            words_per_chapter=row["words_per_chapter"],
            story_structure=row["story_structure"],
            sub_genre_id=row["sub_genre_id"],
            arc_boundaries_auto=bool(row["arc_boundaries_auto"]),
        )

    async def update_seed_config(
        self,
        project_id: str,
        *,
        estimated_chapters: int | None = None,
        words_per_chapter: int | None = None,
        story_structure: str | None = None,
        sub_genre_id: str | None = None,
        arc_boundaries_auto: bool | None = None,
        arc_boundaries: list[int] | None = None,
    ) -> None:
        """更新项目种子配置字段（仅更新提供的非 None 字段）.

        Args:
            project_id: 项目 ID
            estimated_chapters: 预估总章数
            words_per_chapter: 每章目标字数
            story_structure: 故事结构
            sub_genre_id: 子类型 ID
            arc_boundaries_auto: 是否自动推导 arc
            arc_boundaries: Arc 边界列表
        """
        updates: dict[str, Any] = {}
        if estimated_chapters is not None:
            updates["estimated_chapters"] = estimated_chapters
        if words_per_chapter is not None:
            updates["words_per_chapter"] = words_per_chapter
        if story_structure is not None:
            updates["story_structure"] = story_structure
        if sub_genre_id is not None:
            updates["sub_genre_id"] = sub_genre_id
        if arc_boundaries_auto is not None:
            updates["arc_boundaries_auto"] = int(arc_boundaries_auto)
        if arc_boundaries is not None:
            updates["arc_boundaries"] = _to_json(arc_boundaries)

        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [project_id]

        async with get_db() as conn:
            await conn.execute(
                f"UPDATE projects SET {set_clause} WHERE project_id = ?",
                values,
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="projects",
            operation="update_seed_config",
            project_id=project_id,
            fields=list(updates.keys()),
        )


class CharacterRepository:
    """Repository for character profiles and state snapshots."""

    async def create(
        self, character: Character, conn: aiosqlite.Connection | None = None
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO characters (
                    character_id, project_id, name, role_type, background,
                    personality_traits, goals, relationships, dialogue_style_card, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    character.character_id,
                    character.project_id,
                    character.name,
                    character.role_type,
                    character.background,
                    _to_json(character.personality_traits),
                    _to_json(character.goals),
                    _to_json(character.relationships),
                    _to_json(character.dialogue_style_card.model_dump(mode="json") if character.dialogue_style_card else {}),
                    _dt(character.created_at),
                ),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
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

    async def save_dialogue_style_card(
        self,
        character_id: str,
        card: Any,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """保存或更新角色的对话风格卡."""
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                "UPDATE characters SET dialogue_style_card = ? WHERE character_id = ?",
                (_to_json(card.model_dump(mode="json") if hasattr(card, "model_dump") else card), character_id),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.write",
            table="characters",
            operation="update_dialogue_style_card",
            character_id=character_id,
        )

    async def add_state_snapshot(
        self, state: CharacterState, conn: aiosqlite.Connection | None = None
    ) -> int:
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
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
            return int(cursor.lastrowid)

        if conn is None:
            async with get_db() as c:
                state_id = await _do(c)
                await c.commit()
        else:
            for attempt in range(20):
                try:
                    state_id = await _do(conn)
                    break
                except sqlite3.OperationalError as exc:
                    if not _is_sqlite_locked(exc) or attempt == 19:
                        raise
                    await asyncio.sleep(0.05 * (attempt + 1))
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

    async def create(
        self,
        goal: ChapterGoal,
        goal_id: str,
        project_id: str,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
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

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info("repository.write", table="chapter_goals", operation="insert", goal_id=goal_id)

    async def get(self, goal_id: str) -> ChapterGoal | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM chapter_goals WHERE goal_id = ?",
                (goal_id,),
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

    async def create(
        self, version: ChapterVersion, conn: aiosqlite.Connection | None = None
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO chapter_versions (
                    version_id, project_id, chapter_number, version_number,
                    version_type, is_abandoned, content, word_count, scenes,
                    generation_metadata, score_card, creative_brief_id, parent_version_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    version.version_id,
                    version.project_id,
                    version.chapter_number,
                    version.version_number,
                    version.version_type,
                    int(version.is_abandoned),
                    version.content,
                    version.word_count,
                    _to_json(version.scenes),
                    _to_json(version.generation_metadata),
                    _to_json(version.score_card),
                    version.creative_brief_id,
                    version.parent_version_id,
                    _dt(version.created_at),
                ),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
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

    async def list_by_chapter(
        self, project_id: str, chapter_number: int, *, include_abandoned: bool = False
    ) -> list[ChapterVersion]:
        async with get_db() as conn:
            conn.row_factory = Row
            sql = """SELECT * FROM chapter_versions
                WHERE project_id = ? AND chapter_number = ?"""
            if not include_abandoned:
                sql += " AND is_abandoned = 0"
            sql += " ORDER BY version_number"
            cursor = await conn.execute(sql, (project_id, chapter_number))
            rows = await cursor.fetchall()
        return [_version_from_row(row) for row in rows]

    async def mark_abandoned(self, version_id: str) -> None:
        async with get_db() as conn:
            await conn.execute(
                "UPDATE chapter_versions SET is_abandoned = 1 WHERE version_id = ?",
                (version_id,),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="chapter_versions",
            operation="mark_abandoned",
            version_id=version_id,
        )

    async def accept_version(self, version_id: str) -> None:
        """将版本标记为 accepted（RAG 索引触发条件）."""
        async with get_db() as conn:
            await conn.execute(
                "UPDATE chapter_versions SET version_type = 'accepted' WHERE version_id = ?",
                (version_id,),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="chapter_versions",
            operation="accept_version",
            version_id=version_id,
        )

    async def get_next_version_number(
        self, project_id: str, chapter_number: int
    ) -> int:
        """返回下一可用版本号（包含废弃版本，避免编号冲突）."""
        async with get_db() as conn:
            cursor = await conn.execute(
                """SELECT COALESCE(MAX(version_number), 0) + 1
                   FROM chapter_versions
                   WHERE project_id = ? AND chapter_number = ?""",
                (project_id, chapter_number),
            )
            row = await cursor.fetchone()
        return row[0] if row else 1

    async def update_score_card(
        self, version_id: str, score_card: dict[str, Any]
    ) -> None:
        """更新版本 score_card（Task 106-patch）."""
        async with get_db() as conn:
            await conn.execute(
                "UPDATE chapter_versions SET score_card = ? WHERE version_id = ?",
                (_to_json(score_card), version_id),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="chapter_versions",
            operation="update_score_card",
            version_id=version_id,
        )

    async def get_chain(self, version_id: str) -> list[ChapterVersion]:
        """使用 SQLite 递归 CTE 一次性查询整条版本链."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """WITH RECURSIVE chain AS (
                    SELECT * FROM chapter_versions WHERE version_id = ?
                    UNION ALL
                    SELECT v.* FROM chapter_versions v
                    INNER JOIN chain c ON v.version_id = c.parent_version_id
                )
                SELECT * FROM chain""",
                (version_id,),
            )
            rows = await cursor.fetchall()
        return [_version_from_row(row) for row in reversed(rows)]


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

    async def list_by_project(self, project_id: str) -> list[ChapterHead]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM chapter_heads WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [
            ChapterHead(
                project_id=row["project_id"],
                chapter_number=row["chapter_number"],
                current_version_id=row["current_version_id"],
                accepted_version_id=row["accepted_version_id"],
                status=row["status"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

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
    from songyan.models.character import DialogueStyleCard
    dsc_raw = row["dialogue_style_card"] if "dialogue_style_card" in row.keys() else None
    dsc_data = _from_json(dsc_raw, {})
    dialogue_style_card = DialogueStyleCard(**dsc_data) if dsc_data else None
    return Character(
        character_id=row["character_id"],
        project_id=row["project_id"],
        name=row["name"],
        role_type=row["role_type"],
        background=row["background"],
        personality_traits=_from_json(row["personality_traits"], []),
        goals=_from_json(row["goals"], []),
        relationships=_from_json(row["relationships"], {}),
        dialogue_style_card=dialogue_style_card,
        created_at=row["created_at"],
    )


def _version_from_row(row: Row) -> ChapterVersion:
    return ChapterVersion(
        version_id=row["version_id"],
        project_id=row["project_id"],
        chapter_number=row["chapter_number"],
        version_number=row["version_number"],
        version_type=row["version_type"],
        is_abandoned=bool(row["is_abandoned"]),
        content=row["content"],
        word_count=row["word_count"],
        scenes=_from_json(row["scenes"], []),
        generation_metadata=_from_json(row["generation_metadata"], {}),
        score_card=_from_json(row["score_card"] if "score_card" in row.keys() else None, {}),
        creative_brief_id=row["creative_brief_id"],
        parent_version_id=row["parent_version_id"],
        created_at=row["created_at"],
    )
