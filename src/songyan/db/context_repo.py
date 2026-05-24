"""Async repositories for context package assembly."""

from __future__ import annotations

from sqlite3 import Row

import structlog

from songyan.db.connection import get_db
from songyan.db.repository import _from_json
from songyan.models import ChapterSummary, CharacterState

logger = structlog.get_logger(__name__)


class SummaryRepository:
    """Repository for chapter summaries."""

    async def list_recent(
        self,
        project_id: str,
        before_chapter: int,
        limit: int = 3,
    ) -> list[ChapterSummary]:
        """获取最近 N 章的摘要（before_chapter 之前的章节）."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT chapter_number, plot_summary, key_events
                FROM summaries
                WHERE project_id = ? AND chapter_number < ?
                ORDER BY chapter_number DESC
                LIMIT ?""",
                (project_id, before_chapter, limit),
            )
            rows = await cursor.fetchall()
        # 按 chapter_number 升序返回（从旧到新）
        summaries = [
            ChapterSummary(
                chapter_number=row["chapter_number"],
                summary=row["plot_summary"] or "",
                key_events=_from_json(row["key_events"], []),
            )
            for row in reversed(rows)
        ]
        logger.info(
            "repository.read",
            table="summaries",
            operation="list_recent",
            project_id=project_id,
            count=len(summaries),
        )
        return summaries


class CharacterStateRepository:
    """Repository for querying character state snapshots."""

    async def list_recent_by_project(
        self,
        project_id: str,
        limit_per_character: int = 5,
    ) -> list[CharacterState]:
        """获取项目下每个角色的最新状态记录.

        返回每个角色最近 limit_per_character 条状态记录。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            # 先获取项目下的所有角色 ID
            cursor = await conn.execute(
                "SELECT character_id FROM characters WHERE project_id = ?",
                (project_id,),
            )
            char_rows = await cursor.fetchall()
            character_ids = [row["character_id"] for row in char_rows]

            all_states: list[CharacterState] = []
            for char_id in character_ids:
                cursor = await conn.execute(
                    """SELECT character_id, field, value, source_version_id, created_at
                    FROM character_states
                    WHERE character_id = ?
                    ORDER BY created_at DESC, state_id DESC
                    LIMIT ?""",
                    (char_id, limit_per_character),
                )
                rows = await cursor.fetchall()
                all_states.extend(
                    [
                        CharacterState(
                            character_id=row["character_id"],
                            field=row["field"],
                            value=row["value"],
                            source_version_id=row["source_version_id"],
                            created_at=row["created_at"],
                        )
                        for row in rows
                    ]
                )
        logger.info(
            "repository.read",
            table="character_states",
            operation="list_recent_by_project",
            project_id=project_id,
            count=len(all_states),
        )
        return all_states

    async def list_latest_by_project(
        self,
        project_id: str,
    ) -> list[CharacterState]:
        """获取项目下每个角色的最新一条状态记录（每个 field 取最新）."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT cs.character_id, cs.field, cs.value,
                          cs.source_version_id, cs.created_at
                FROM character_states cs
                INNER JOIN characters c ON cs.character_id = c.character_id
                WHERE c.project_id = ?
                AND cs.created_at = (
                    SELECT MAX(created_at)
                    FROM character_states cs2
                    WHERE cs2.character_id = cs.character_id
                    AND cs2.field = cs.field
                )
                ORDER BY cs.character_id, cs.field""",
                (project_id,),
            )
            rows = await cursor.fetchall()
        states = [
            CharacterState(
                character_id=row["character_id"],
                field=row["field"],
                value=row["value"],
                source_version_id=row["source_version_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
        logger.info(
            "repository.read",
            table="character_states",
            operation="list_latest_by_project",
            project_id=project_id,
            count=len(states),
        )
        return states
