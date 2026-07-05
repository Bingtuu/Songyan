"""Repository for active foreshadowing schedules (V7 Task 167a)."""

from __future__ import annotations

from datetime import datetime
from sqlite3 import Row
from typing import Any

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import SongyanError
from songyan.models import ForeshadowingScheduleItem, ForeshadowingSchedulePlan
from songyan.utils.json_helpers import from_json as _from_json
from songyan.utils.json_helpers import to_json as _to_json

logger = structlog.get_logger(__name__)


class ForeshadowingScheduleRepositoryError(SongyanError):
    """Foreshadowing schedule repository error."""


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now()
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime.now()


class ForeshadowingScheduleRepository:
    """Read/write foreshadowing schedule plans and items."""

    async def create(self, plan: ForeshadowingSchedulePlan) -> None:
        """Persist one schedule plan and ordered items atomically."""
        for item in plan.items:
            if item.plan_id != plan.plan_id:
                msg = (
                    "foreshadowing schedule item plan_id mismatch: "
                    f"{item.item_id} -> {item.plan_id}"
                )
                raise ForeshadowingScheduleRepositoryError(msg)
            if item.project_id != plan.project_id:
                msg = (
                    "foreshadowing schedule item project_id mismatch: "
                    f"{item.item_id} -> {item.project_id}"
                )
                raise ForeshadowingScheduleRepositoryError(msg)
        async with get_db() as conn:
            try:
                await conn.execute(
                    """INSERT INTO foreshadowing_schedule_plans (
                        plan_id, project_id, target_chapter, current_arc_index,
                        horizon_chapters, max_items, status, summary,
                        evidence_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        plan.plan_id,
                        plan.project_id,
                        plan.target_chapter,
                        plan.current_arc_index,
                        plan.horizon_chapters,
                        plan.max_items,
                        plan.status,
                        plan.summary,
                        _to_json(plan.evidence),
                        plan.created_at.isoformat(),
                        plan.updated_at.isoformat(),
                    ),
                )
                for item in plan.items:
                    await conn.execute(
                        """INSERT INTO foreshadowing_schedule_items (
                            item_id, plan_id, project_id, item_order,
                            target_chapter, source_type, source_id, title,
                            description, priority_score, reason_codes,
                            rationale, status, evidence_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item.item_id,
                            item.plan_id,
                            item.project_id,
                            item.item_order,
                            item.target_chapter,
                            item.source_type,
                            item.source_id,
                            item.title,
                            item.description,
                            item.priority_score,
                            _to_json(item.reason_codes),
                            item.rationale,
                            item.status,
                            _to_json(item.evidence),
                            item.created_at.isoformat(),
                        ),
                    )
                await conn.commit()
            except Exception as exc:  # noqa: BLE001 - rollback and wrap repository errors
                await conn.rollback()
                msg = f"failed to create foreshadowing schedule plan: {plan.plan_id}"
                raise ForeshadowingScheduleRepositoryError(msg) from exc
        logger.info(
            "repository.write",
            table="foreshadowing_schedule_plans",
            operation="insert",
            plan_id=plan.plan_id,
            items=len(plan.items),
        )

    async def get(self, plan_id: str) -> ForeshadowingSchedulePlan | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM foreshadowing_schedule_plans WHERE plan_id = ?",
                (plan_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            items = await self._list_items(conn, plan_id)
        return self._row_to_plan(row, items)

    async def list_by_project(
        self,
        project_id: str,
        *,
        status: str | None = None,
        include_items: bool = False,
    ) -> list[ForeshadowingSchedulePlan]:
        query = "SELECT * FROM foreshadowing_schedule_plans WHERE project_id = ?"
        params: list[Any] = [project_id]
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY target_chapter, created_at, plan_id"
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            item_map: dict[str, list[ForeshadowingScheduleItem]] = {}
            if include_items:
                for row in rows:
                    item_map[row["plan_id"]] = await self._list_items(
                        conn, row["plan_id"]
                    )
        return [
            self._row_to_plan(row, item_map.get(row["plan_id"], []))
            for row in rows
        ]

    async def list_items(self, plan_id: str) -> list[ForeshadowingScheduleItem]:
        async with get_db() as conn:
            conn.row_factory = Row
            return await self._list_items(conn, plan_id)

    async def list_recent_items(
        self,
        project_id: str,
        *,
        start_chapter: int,
        end_chapter: int,
        statuses: tuple[str, ...] = ("draft", "active", "injected", "satisfied"),
    ) -> list[ForeshadowingScheduleItem]:
        """Return scheduled items in a chapter window for duplicate suppression."""
        placeholders = ",".join("?" * len(statuses))
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                f"""SELECT * FROM foreshadowing_schedule_items
                   WHERE project_id = ?
                     AND target_chapter BETWEEN ? AND ?
                     AND status IN ({placeholders})
                   ORDER BY target_chapter, item_order, item_id""",
                (project_id, start_chapter, end_chapter, *statuses),
            )
            rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    async def list_items_for_chapter(
        self,
        project_id: str,
        chapter_number: int,
        *,
        statuses: tuple[str, ...] = ("active", "injected"),
        limit: int | None = None,
    ) -> list[ForeshadowingScheduleItem]:
        """Return schedule items targeting one chapter."""
        placeholders = ",".join("?" * len(statuses))
        query = f"""SELECT * FROM foreshadowing_schedule_items
            WHERE project_id = ?
              AND target_chapter = ?
              AND status IN ({placeholders})
            ORDER BY priority_score DESC, item_order, item_id"""
        params: list[Any] = [project_id, chapter_number, *statuses]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    async def update_plan_status(
        self,
        plan_id: str,
        status: str,
        conn: Any | None = None,
    ) -> None:
        async def _do(c: Any) -> None:
            cursor = await c.execute(
                """UPDATE foreshadowing_schedule_plans
                   SET status = ?, updated_at = ?
                   WHERE plan_id = ?""",
                (status, datetime.now().isoformat(), plan_id),
            )
            if cursor.rowcount == 0:
                msg = f"foreshadowing schedule plan not found: {plan_id}"
                raise ForeshadowingScheduleRepositoryError(msg)

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)

    async def update_item_status(
        self,
        item_id: str,
        status: str,
        conn: Any | None = None,
    ) -> None:
        async def _do(c: Any) -> None:
            cursor = await c.execute(
                "UPDATE foreshadowing_schedule_items SET status = ? WHERE item_id = ?",
                (status, item_id),
            )
            if cursor.rowcount == 0:
                msg = f"foreshadowing schedule item not found: {item_id}"
                raise ForeshadowingScheduleRepositoryError(msg)

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)

    async def update_items_status(
        self,
        item_ids: list[str],
        status: str,
        conn: Any | None = None,
    ) -> None:
        if not item_ids:
            return
        placeholders = ",".join("?" * len(item_ids))

        async def _do(c: Any) -> None:
            cursor = await c.execute(
                f"""UPDATE foreshadowing_schedule_items
                   SET status = ?
                   WHERE item_id IN ({placeholders})""",
                (status, *item_ids),
            )
            if cursor.rowcount != len(item_ids):
                msg = (
                    "failed to update all foreshadowing schedule items "
                    f"({cursor.rowcount}/{len(item_ids)})"
                )
                raise ForeshadowingScheduleRepositoryError(msg)

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)

    async def _list_items(
        self,
        conn: Any,
        plan_id: str,
    ) -> list[ForeshadowingScheduleItem]:
        cursor = await conn.execute(
            """SELECT * FROM foreshadowing_schedule_items
               WHERE plan_id = ?
               ORDER BY item_order, item_id""",
            (plan_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    @staticmethod
    def _row_to_plan(
        row: Row,
        items: list[ForeshadowingScheduleItem],
    ) -> ForeshadowingSchedulePlan:
        return ForeshadowingSchedulePlan(
            plan_id=row["plan_id"],
            project_id=row["project_id"],
            target_chapter=row["target_chapter"],
            current_arc_index=row["current_arc_index"],
            horizon_chapters=row["horizon_chapters"],
            max_items=row["max_items"],
            status=row["status"],
            summary=row["summary"] or "",
            evidence=_from_json(row["evidence_json"], {}),
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
            items=items,
        )

    @staticmethod
    def _row_to_item(row: Row) -> ForeshadowingScheduleItem:
        return ForeshadowingScheduleItem(
            item_id=row["item_id"],
            plan_id=row["plan_id"],
            project_id=row["project_id"],
            item_order=row["item_order"],
            target_chapter=row["target_chapter"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            title=row["title"] or "",
            description=row["description"] or "",
            priority_score=row["priority_score"],
            reason_codes=_from_json(row["reason_codes"], []),
            rationale=row["rationale"] or "",
            status=row["status"],
            evidence=_from_json(row["evidence_json"], {}),
            created_at=_parse_dt(row["created_at"]),
        )
