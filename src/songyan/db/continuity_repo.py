"""Async repositories for continuity tracking and audit reports."""

from __future__ import annotations

import json as _json
from sqlite3 import Row
from typing import TYPE_CHECKING, Any

import structlog

from songyan.db.connection import get_db

if TYPE_CHECKING:
    import aiosqlite
from songyan.models.continuity import (
    ContinuityReport,
    ForgottenItem,
    OrphanedSetting,
    OverdueForeshadowing,
    StateMismatch,
)
from songyan.models.human_mark import SuggestedMark

logger = structlog.get_logger(__name__)


class SettingTrackingRepository:
    """Repository for setting lifecycle tracking."""

    LONG_SILENT_ARCHIVE_WINDOWS: dict[str, int] = {
        "background": 8,
        "technical": 10,
    }

    async def create(
        self,
        tracking_id: str,
        project_id: str,
        setting_key: str,
        setting_name: str,
        description: str,
        introduced_in_chapter: int,
        source_version_id: str | None = None,
        category: str = "background",
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO setting_tracking (
                    tracking_id, project_id, setting_key, setting_name,
                    description, introduced_in_chapter, last_mentioned_chapter,
                    source_version_id, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tracking_id,
                    project_id,
                    setting_key,
                    setting_name,
                    description,
                    introduced_in_chapter,
                    introduced_in_chapter,
                    source_version_id,
                    category,
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
            table="setting_tracking",
            operation="insert",
            tracking_id=tracking_id,
        )

    async def list_by_project(self, project_id: str) -> list[dict]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM setting_tracking "
                "WHERE project_id = ? "
                "ORDER BY introduced_in_chapter",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def update_last_mentioned(
        self, tracking_id: str, chapter: int, conn: aiosqlite.Connection | None = None
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """UPDATE setting_tracking
                   SET last_mentioned_chapter = ?
                   WHERE tracking_id = ?""",
                (chapter, tracking_id),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)

    async def update_status(
        self,
        tracking_id: str,
        status: str,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """UPDATE setting_tracking
                   SET status = ?
                   WHERE tracking_id = ?""",
                (status, tracking_id),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)

    async def archive_long_silent_nonessential(
        self,
        project_id: str,
        current_chapter: int,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """Archive long-silent background/technical settings before orphan scoring.

        Critical and recurring settings are intentionally excluded. High-priority
        human-marked settings and explicit recovery-required rows also stay active.
        """
        clauses: list[str] = []
        params: list[Any] = [project_id]
        for category, window in self.LONG_SILENT_ARCHIVE_WINDOWS.items():
            clauses.append("(category = ? AND last_mentioned_chapter < ?)")
            params.extend([category, current_chapter - window])
        if not clauses:
            return 0

        category_clause = " OR ".join(clauses)

        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                f"""UPDATE setting_tracking
                SET status = 'archived'
                WHERE project_id = ?
                  AND status = 'active'
                  AND recovery_required = 0
                  AND ({category_clause})
                  AND setting_key NOT IN (
                      SELECT target_key FROM human_marks
                      WHERE project_id = ?
                        AND mark_type = 'setting'
                        AND lifecycle_status = 'active'
                        AND resolved_at IS NULL
                        AND (
                            source != 'continuity_auditor'
                            OR created_at_chapter IS NULL
                            OR created_at_chapter < ?
                        )
                  )""",
                (*params, project_id, current_chapter),
            )
            await c.execute(
                f"""UPDATE setting_snapshots
                SET lifecycle_status = 'archived'
                WHERE project_id = ?
                  AND lifecycle_status IN ('active', 'dormant')
                  AND setting_key IN (
                      SELECT setting_key FROM setting_tracking
                      WHERE project_id = ?
                        AND status = 'archived'
                        AND ({category_clause})
                  )""",
                (project_id, project_id, *params[1:]),
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
                table="setting_tracking",
                operation="archive_long_silent_nonessential",
                project_id=project_id,
                current_chapter=current_chapter,
                archived_count=archived,
            )
        return archived

    async def active_setting_mark_keys(
        self,
        project_id: str,
        conn: aiosqlite.Connection | None = None,
        *,
        current_chapter: int | None = None,
    ) -> set[str]:
        """Return active unresolved setting human-mark targets for a project.

        ContinuityAuditor marks created for the same chapter are diagnostics for
        the current report; they should not become a permanent orphan exemption.
        """

        async def _do(c: aiosqlite.Connection) -> set[str]:
            chapter_clause = ""
            params: list[Any] = [project_id]
            if current_chapter is not None:
                chapter_clause = """AND (
                    source != 'continuity_auditor'
                    OR created_at_chapter IS NULL
                    OR created_at_chapter < ?
                )"""
                params.append(current_chapter)
            cursor = await c.execute(
                f"""SELECT DISTINCT target_key FROM human_marks
                WHERE project_id = ?
                  AND mark_type = 'setting'
                  AND lifecycle_status = 'active'
                  AND resolved_at IS NULL
                  AND target_key IS NOT NULL
                  AND target_key != ''
                  {chapter_clause}""",
                params,
            )
            rows = await cursor.fetchall()
            return {str(row[0]) for row in rows if row[0]}

        if conn is None:
            async with get_db() as c:
                return await _do(c)
        return await _do(conn)

    async def find_orphaned(
        self,
        project_id: str,
        up_to_chapter: int,
        threshold: int = 3,
        categories: list[str] | None = None,
    ) -> list[dict]:
        """Find settings whose last mention is more than threshold chapters ago."""
        query = """SELECT * FROM setting_tracking
                   WHERE project_id = ?
                     AND status = 'active'
                     AND last_mentioned_chapter < ?"""
        params: list[Any] = [project_id, up_to_chapter - threshold]
        if categories:
            placeholders = ",".join("?" * len(categories))
            query += f" AND category IN ({placeholders})"
            params.extend(categories)
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


class InventoryTrackerRepository:
    """Repository for inventory/item tracking."""

    async def create(
        self,
        track_id: str,
        project_id: str,
        character_id: str,
        item_name: str,
        item_description: str,
        acquired_in_chapter: int,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO inventory_tracker (
                    track_id, project_id, character_id, item_name,
                    item_description, acquired_in_chapter, last_used_chapter
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    track_id,
                    project_id,
                    character_id,
                    item_name,
                    item_description,
                    acquired_in_chapter,
                    acquired_in_chapter,
                ),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)

    async def list_by_project(self, project_id: str) -> list[dict]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM inventory_tracker WHERE project_id = ?",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def update_last_used(self, track_id: str, chapter: int) -> None:
        async with get_db() as conn:
            await conn.execute(
                """UPDATE inventory_tracker
                   SET last_used_chapter = ?
                   WHERE track_id = ?""",
                (chapter, track_id),
            )
            await conn.commit()


class LocationTrackerRepository:
    """Repository for character location tracking."""

    async def create(
        self,
        track_id: str,
        project_id: str,
        character_id: str,
        location: str,
        entered_in_chapter: int,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO location_tracker (
                    track_id, project_id, character_id, location,
                    entered_in_chapter, last_confirmed_chapter
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    track_id,
                    project_id,
                    character_id,
                    location,
                    entered_in_chapter,
                    entered_in_chapter,
                ),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)

    async def list_by_project(self, project_id: str) -> list[dict]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM location_tracker WHERE project_id = ?",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def update_last_confirmed(self, track_id: str, chapter: int) -> None:
        async with get_db() as conn:
            await conn.execute(
                """UPDATE location_tracker
                   SET last_confirmed_chapter = ?
                   WHERE track_id = ?""",
                (chapter, track_id),
            )
            await conn.commit()


class ContinuityReportRepository:
    """Repository for continuity audit reports."""

    async def create(self, report: ContinuityReport) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO continuity_reports (
                    report_id, project_id, checked_up_to_chapter,
                    orphaned_settings, forgotten_items, state_mismatches,
                    overdue_foreshadowings, suggested_marks, overall_health_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report.report_id,
                    report.project_id,
                    report.checked_up_to_chapter,
                    _json.dumps(
                        [s.model_dump() for s in report.orphaned_settings], ensure_ascii=False
                    ),
                    _json.dumps(
                        [i.model_dump() for i in report.forgotten_items], ensure_ascii=False
                    ),
                    _json.dumps(
                        [m.model_dump() for m in report.state_mismatches], ensure_ascii=False
                    ),
                    _json.dumps(
                        [f.model_dump() for f in report.overdue_foreshadowings], ensure_ascii=False
                    ),
                    _json.dumps(
                        [s.model_dump() for s in report.suggested_marks], ensure_ascii=False
                    ),
                    report.overall_health_score,
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="continuity_reports",
            operation="insert",
            report_id=report.report_id,
        )

    async def get_latest(self, project_id: str) -> ContinuityReport | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM continuity_reports
                   WHERE project_id = ?
                   ORDER BY created_at DESC, report_id DESC
                   LIMIT 1""",
                (project_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_report(row)

    async def list_by_chapter_range(
        self, project_id: str, chapter_start: int, chapter_end: int
    ) -> list[ContinuityReport]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT report_id, project_id, checked_up_to_chapter,
                          orphaned_settings, forgotten_items, state_mismatches,
                          overdue_foreshadowings, suggested_marks, overall_health_score,
                          created_at
                   FROM continuity_reports
                   WHERE project_id = ? AND checked_up_to_chapter BETWEEN ? AND ?
                   ORDER BY checked_up_to_chapter""",
                (project_id, chapter_start, chapter_end),
            )
            rows = await cursor.fetchall()
        return [self._row_to_report(row) for row in rows]

    def _row_to_report(self, row: Row) -> ContinuityReport:
        return ContinuityReport(
            report_id=row["report_id"],
            project_id=row["project_id"],
            checked_up_to_chapter=row["checked_up_to_chapter"],
            orphaned_settings=[
                OrphanedSetting.model_validate(item)
                for item in _json.loads(row["orphaned_settings"] or "[]")
            ],
            forgotten_items=[
                ForgottenItem.model_validate(item)
                for item in _json.loads(row["forgotten_items"] or "[]")
            ],
            state_mismatches=[
                StateMismatch.model_validate(item)
                for item in _json.loads(row["state_mismatches"] or "[]")
            ],
            overdue_foreshadowings=[
                OverdueForeshadowing.model_validate(item)
                for item in _json.loads(row["overdue_foreshadowings"] or "[]")
            ],
            suggested_marks=[
                SuggestedMark.model_validate(item)
                for item in _json.loads(row["suggested_marks"] or "[]")
            ],
            overall_health_score=row["overall_health_score"],
        )
