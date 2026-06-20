"""Async repositories for continuity tracking and audit reports."""

from __future__ import annotations

import json as _json
from sqlite3 import Row
from typing import TYPE_CHECKING

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

    async def find_orphaned(
        self, project_id: str, up_to_chapter: int, threshold: int = 3
    ) -> list[dict]:
        """Find settings whose last mention is more than threshold chapters ago."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM setting_tracking
                   WHERE project_id = ?
                     AND status = 'active'
                     AND last_mentioned_chapter < ?""",
                (project_id, up_to_chapter - threshold),
            )
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
