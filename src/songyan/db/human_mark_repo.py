"""Repository for human marks — Phase 7 Human-Augmented Memory."""

from __future__ import annotations

from datetime import datetime
from sqlite3 import Row
from typing import TYPE_CHECKING

import structlog

from songyan.db.connection import get_db
from songyan.models.human_mark import HumanMark

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)


class HumanMarkRepository:
    """Repository for human marks."""

    async def create(
        self,
        mark: HumanMark,
        conn: aiosqlite.Connection | None = None,
        *,
        replace: bool = False,
    ) -> None:
        """Insert a new human mark."""

        sql_prefix = "INSERT OR REPLACE INTO" if replace else "INSERT INTO"

        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                f"""{sql_prefix} human_marks (
                    mark_id, project_id, mark_type, target_key,
                    note, priority, created_at_chapter, resolved_at, created_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    mark.mark_id,
                    mark.project_id,
                    mark.mark_type,
                    mark.target_key,
                    mark.note,
                    mark.priority,
                    mark.created_at_chapter,
                    mark.resolved_at.isoformat() if mark.resolved_at else None,
                    mark.created_at.isoformat(),
                    mark.source,
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
            table="human_marks",
            operation="insert_or_replace" if replace else "insert",
            mark_id=mark.mark_id,
            project_id=mark.project_id,
        )

    async def get(self, mark_id: str) -> HumanMark | None:
        """Get a mark by ID."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM human_marks WHERE mark_id = ?",
                (mark_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_mark(row)

    async def list_by_project(
        self,
        project_id: str,
        mark_type: str | None = None,
        min_priority: int = 0,
        include_resolved: bool = False,
        min_chapter: int | None = None,
    ) -> list[HumanMark]:
        """List marks for a project, optionally filtered.

        V4.0: 默认只返回 lifecycle_status='active' 的记录。
        priority>=8 的记录即使 dormant 也被保留。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            conditions = ["project_id = ?", "priority >= ?"]
            params: list = [project_id, min_priority]

            if mark_type:
                conditions.append("mark_type = ?")
                params.append(mark_type)
            if not include_resolved:
                conditions.append("resolved_at IS NULL")
            if min_chapter is not None:
                conditions.append("created_at_chapter >= ?")
                params.append(min_chapter)

            # V4.0: 只返回 active；priority>=8 的 dormant 也被保留
            conditions.append(
                "(lifecycle_status = 'active' OR priority >= 8)"
            )

            sql = (
                "SELECT * FROM human_marks WHERE "
                + " AND ".join(conditions)
                + " ORDER BY priority DESC, created_at DESC"
            )
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
        return [self._row_to_mark(row) for row in rows]

    async def count_unresolved_by_chapter(
        self,
        project_id: str,
        chapter_number: int,
    ) -> int:
        """返回指定章节未解决的 human_marks 数量（预算检查用）."""
        async with get_db() as conn:
            cursor = await conn.execute(
                """SELECT COUNT(*) FROM human_marks
                WHERE project_id = ? AND created_at_chapter = ? AND resolved_at IS NULL""",
                (project_id, chapter_number),
            )
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def archive_stale(
        self,
        project_id: str,
        current_chapter: int,
        window: int = 10,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 unresolved + 10 章未提及的 human_marks 标记为 dormant.

        priority>=8 除外。
        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """UPDATE human_marks
                SET lifecycle_status = 'dormant'
                WHERE project_id = ?
                  AND lifecycle_status = 'active'
                  AND resolved_at IS NULL
                  AND created_at_chapter < ?
                  AND priority < 8""",
                (project_id, current_chapter - window),
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="human_marks",
                operation="archive_stale",
                project_id=project_id,
                current_chapter=current_chapter,
                window=window,
                archived_count=archived,
            )
        return archived

    async def archive_very_stale(
        self,
        project_id: str,
        current_chapter: int,
        window: int = 20,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 resolved 或 >20 章未提及的 human_marks 标记为 archived.

        priority>=8 除外。
        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """UPDATE human_marks
                SET lifecycle_status = 'archived'
                WHERE project_id = ?
                  AND lifecycle_status IN ('active', 'dormant')
                  AND priority < 8
                  AND (
                      resolved_at IS NOT NULL
                      OR created_at_chapter < ?
                  )""",
                (project_id, current_chapter - window),
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="human_marks",
                operation="archive_very_stale",
                project_id=project_id,
                current_chapter=current_chapter,
                window=window,
                archived_count=archived,
            )
        return archived

    async def remove(self, mark_id: str) -> bool:
        """Remove a mark by ID. Returns True if deleted."""
        async with get_db() as conn:
            cursor = await conn.execute(
                "DELETE FROM human_marks WHERE mark_id = ?",
                (mark_id,),
            )
            await conn.commit()
            deleted = cursor.rowcount > 0
        if deleted:
            logger.info(
                "repository.write",
                table="human_marks",
                operation="delete",
                mark_id=mark_id,
            )
        return deleted

    async def update_priority(self, mark_id: str, priority: int) -> bool:
        """Update a mark's priority. Returns True if updated."""
        async with get_db() as conn:
            cursor = await conn.execute(
                "UPDATE human_marks SET priority = ? WHERE mark_id = ?",
                (priority, mark_id),
            )
            await conn.commit()
            updated = cursor.rowcount > 0
        if updated:
            logger.info(
                "repository.write",
                table="human_marks",
                operation="update_priority",
                mark_id=mark_id,
                priority=priority,
            )
        return updated

    async def resolve(self, mark_id: str) -> bool:
        """Mark a mark as resolved (soft-resolve via timestamp)."""
        from datetime import datetime

        async with get_db() as conn:
            cursor = await conn.execute(
                "UPDATE human_marks SET resolved_at = ? WHERE mark_id = ?",
                (datetime.utcnow().isoformat(), mark_id),
            )
            await conn.commit()
            updated = cursor.rowcount > 0
        if updated:
            logger.info(
                "repository.write",
                table="human_marks",
                operation="resolve",
                mark_id=mark_id,
            )
        return updated

    def _row_to_mark(self, row: Row) -> HumanMark:
        """Convert a DB row to HumanMark."""
        return HumanMark(
            mark_id=row["mark_id"],
            project_id=row["project_id"],
            mark_type=row["mark_type"],
            target_key=row["target_key"],
            note=row["note"] or "",
            priority=row["priority"],
            created_at_chapter=row["created_at_chapter"],
            resolved_at=None,  # Simplified: not parsing ISO string back
            lifecycle_status=row["lifecycle_status"] if "lifecycle_status" in row.keys() else "active",
            created_at=datetime.fromisoformat(row["created_at"]),
            source=row["source"] if "source" in row.keys() else "human",
        )
