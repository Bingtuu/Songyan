"""Async repository for narrative skeleton (V6 阶段 0 / Task 141).

``StoryOutline`` / ``ArcPlan`` / ``PlotThread`` 的持久化与 PlotThread 生命周期
状态机。遵守"写操作集中在 repository、Agent 不直接拿 connection"规则。

区别于回顾型 ``layered_context_repo``（arc_summaries 等）：本模块只处理 **前置规划**
实体，供 V6 GoalPlanner 自顶向下派生章节目标与追踪线索兑现。
"""

from __future__ import annotations

import json as _json
from datetime import datetime
from sqlite3 import Row
from typing import TYPE_CHECKING, Literal

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import SongyanError
from songyan.models import ArcPlan, PlotThread, PlotThreadStatus, StoryOutline

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)


class NarrativeError(SongyanError):
    """叙事骨架 repository 操作错误（如线索不存在、原子导入失败）."""


class InvalidThreadTransitionError(NarrativeError):
    """PlotThread 状态迁移非法（如 resolved→opened）."""


# 合法状态迁移图：planned→opened→advanced→resolved；任意态→abandoned。
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "planned": {"opened", "abandoned"},
    "opened": {"advanced", "resolved", "abandoned"},
    "advanced": {"advanced", "resolved", "abandoned"},
    "resolved": {"abandoned"},
    "abandoned": set(),
}


def _parse_dt(value: str | None) -> datetime:
    """Parse a SQLite datetime string into a Python datetime."""
    if not value:
        return datetime.now()
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now()


class NarrativeRepository:
    """Repository for narrative skeleton (StoryOutline / ArcPlan / PlotThread).

    写方法均支持可选 ``conn``：传入时不提交（由调用方在事务内统一提交），
    不传则各自开连接并提交。用于 Task 142 的原子导入与 Task 144 的结算联动。
    """

    # ------------------------------------------------------------------ #
    # StoryOutline
    # ------------------------------------------------------------------ #
    async def upsert_outline(
        self, outline: StoryOutline, conn: aiosqlite.Connection | None = None
    ) -> None:
        """插入或更新全书大纲（每个项目一条）."""

        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO story_outlines (
                    project_id, core_conflict, mainline_synopsis,
                    themes, intended_ending, updated_at
                ) VALUES (?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(project_id) DO UPDATE SET
                    core_conflict = excluded.core_conflict,
                    mainline_synopsis = excluded.mainline_synopsis,
                    themes = excluded.themes,
                    intended_ending = excluded.intended_ending,
                    updated_at = datetime('now')""",
                (
                    outline.project_id,
                    outline.core_conflict,
                    outline.mainline_synopsis,
                    _json.dumps(outline.themes, ensure_ascii=False),
                    outline.intended_ending,
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
            table="story_outlines",
            operation="upsert",
            project_id=outline.project_id,
        )

    async def get_outline(self, project_id: str) -> StoryOutline | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM story_outlines WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return StoryOutline(
            project_id=row["project_id"],
            core_conflict=row["core_conflict"] or "",
            mainline_synopsis=row["mainline_synopsis"] or "",
            themes=_json.loads(row["themes"] or "[]"),
            intended_ending=row["intended_ending"] or "",
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    # ------------------------------------------------------------------ #
    # ArcPlan
    # ------------------------------------------------------------------ #
    async def add_arc_plan(
        self, arc: ArcPlan, conn: aiosqlite.Connection | None = None
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO arc_plans (
                    arc_id, project_id, arc_index, start_chapter, end_chapter,
                    arc_goal, threads_to_open, threads_to_resolve, is_mainline
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    arc.arc_id,
                    arc.project_id,
                    arc.arc_index,
                    arc.start_chapter,
                    arc.end_chapter,
                    arc.arc_goal,
                    _json.dumps(arc.threads_to_open, ensure_ascii=False),
                    _json.dumps(arc.threads_to_resolve, ensure_ascii=False),
                    int(arc.is_mainline),
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
            table="arc_plans",
            operation="insert",
            arc_id=arc.arc_id,
        )

    async def list_arc_plans(self, project_id: str) -> list[ArcPlan]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM arc_plans WHERE project_id = ? ORDER BY arc_index",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [self._row_to_arc(row) for row in rows]

    async def get_arc_for_chapter(
        self, project_id: str, chapter: int
    ) -> ArcPlan | None:
        """返回覆盖指定章节的弧规划（start_chapter <= chapter <= end_chapter）."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM arc_plans
                   WHERE project_id = ?
                     AND start_chapter <= ? AND end_chapter >= ?
                   ORDER BY arc_index LIMIT 1""",
                (project_id, chapter, chapter),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_arc(row)

    async def get_arc_by_id(
        self,
        arc_id: str,
        conn: aiosqlite.Connection | None = None,
    ) -> ArcPlan | None:
        """按 arc_id 读取弧规划."""

        async def _do(c: aiosqlite.Connection) -> ArcPlan | None:
            c.row_factory = Row
            cursor = await c.execute(
                "SELECT * FROM arc_plans WHERE arc_id = ?",
                (arc_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_arc(row) if row is not None else None

        if conn is None:
            async with get_db() as c:
                return await _do(c)
        return await _do(conn)

    async def update_arc_goal(
        self,
        arc_id: str,
        arc_goal: str,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """更新未来 ArcPlan 的 arc_goal（供 approved re-plan 应用）."""

        async def _do(c: aiosqlite.Connection) -> None:
            cursor = await c.execute(
                "UPDATE arc_plans SET arc_goal = ? WHERE arc_id = ?",
                (arc_goal, arc_id),
            )
            if cursor.rowcount == 0:
                msg = f"arc plan not found: {arc_id}"
                raise NarrativeError(msg)

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.write",
            table="arc_plans",
            operation="update_arc_goal",
            arc_id=arc_id,
        )

    async def update_arc_thread_list(
        self,
        arc_id: str,
        field: Literal["threads_to_open", "threads_to_resolve"],
        values: list[str],
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """结构化更新 ArcPlan 的线索列表字段."""

        async def _do(c: aiosqlite.Connection) -> None:
            cursor = await c.execute(
                f"UPDATE arc_plans SET {field} = ? WHERE arc_id = ?",
                (_json.dumps(values, ensure_ascii=False), arc_id),
            )
            if cursor.rowcount == 0:
                msg = f"arc plan not found: {arc_id}"
                raise NarrativeError(msg)

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.write",
            table="arc_plans",
            operation=f"update_{field}",
            arc_id=arc_id,
        )

    @staticmethod
    def _row_to_arc(row: Row) -> ArcPlan:
        return ArcPlan(
            arc_id=row["arc_id"],
            project_id=row["project_id"],
            arc_index=row["arc_index"],
            start_chapter=row["start_chapter"],
            end_chapter=row["end_chapter"],
            arc_goal=row["arc_goal"] or "",
            threads_to_open=_json.loads(row["threads_to_open"] or "[]"),
            threads_to_resolve=_json.loads(row["threads_to_resolve"] or "[]"),
            is_mainline=bool(row["is_mainline"]),
            created_at=_parse_dt(row["created_at"]),
        )

    # ------------------------------------------------------------------ #
    # PlotThread
    # ------------------------------------------------------------------ #
    async def add_thread(
        self, thread: PlotThread, conn: aiosqlite.Connection | None = None
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO plot_threads (
                    thread_id, project_id, title, description, is_mainline,
                    opened_chapter, expected_resolve_arc, status,
                    last_status_chapter, last_status_version_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    thread.thread_id,
                    thread.project_id,
                    thread.title,
                    thread.description,
                    int(thread.is_mainline),
                    thread.opened_chapter,
                    thread.expected_resolve_arc,
                    thread.status,
                    thread.last_status_chapter,
                    thread.last_status_version_id,
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
            table="plot_threads",
            operation="insert",
            thread_id=thread.thread_id,
        )

    async def list_threads(
        self, project_id: str, status: PlotThreadStatus | None = None
    ) -> list[PlotThread]:
        query = "SELECT * FROM plot_threads WHERE project_id = ?"
        params: list[object] = [project_id]
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at, thread_id"
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [self._row_to_thread(row) for row in rows]

    async def get_thread(
        self,
        thread_id: str,
        conn: aiosqlite.Connection | None = None,
    ) -> PlotThread | None:
        async def _do(c: aiosqlite.Connection) -> PlotThread | None:
            c.row_factory = Row
            cursor = await c.execute(
                "SELECT * FROM plot_threads WHERE thread_id = ?",
                (thread_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_thread(row) if row is not None else None

        if conn is None:
            async with get_db() as c:
                return await _do(c)
        return await _do(conn)

    async def count_threads_by_status(self, project_id: str) -> dict[str, int]:
        """按状态统计线索数量（供 report 与阶段 A 弧级兑现率使用）."""
        async with get_db() as conn:
            cursor = await conn.execute(
                """SELECT status, COUNT(*) FROM plot_threads
                   WHERE project_id = ? GROUP BY status""",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    async def advance_thread_status(
        self,
        thread_id: str,
        new_status: PlotThreadStatus,
        chapter: int,
        version_id: str,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """变更线索状态，写入 last_status_chapter/version_id（T1 可追溯）.

        Raises:
            NarrativeError: 线索不存在。
            InvalidThreadTransitionError: 状态迁移非法。
        """

        async def _do(c: aiosqlite.Connection) -> None:
            c.row_factory = Row
            cursor = await c.execute(
                "SELECT status, opened_chapter FROM plot_threads WHERE thread_id = ?",
                (thread_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                msg = f"plot thread not found: {thread_id}"
                raise NarrativeError(msg)
            current: str = row["status"]
            if new_status not in _ALLOWED_TRANSITIONS.get(current, set()):
                msg = (
                    f"illegal plot thread transition {current} -> {new_status} "
                    f"(thread_id={thread_id})"
                )
                raise InvalidThreadTransitionError(msg)

            set_opened = ""
            params: list[object] = [new_status, chapter, version_id]
            if new_status == "opened" and row["opened_chapter"] is None:
                set_opened = ", opened_chapter = ?"
                params.append(chapter)
            params.append(thread_id)
            await c.execute(
                f"""UPDATE plot_threads SET
                    status = ?, last_status_chapter = ?,
                    last_status_version_id = ?, updated_at = datetime('now'){set_opened}
                WHERE thread_id = ?""",
                params,
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.write",
            table="plot_threads",
            operation="advance_status",
            thread_id=thread_id,
            new_status=new_status,
            chapter=chapter,
        )

    async def update_thread_expected_resolve_arc(
        self,
        thread_id: str,
        expected_resolve_arc: int | None,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """更新未来规划中的线索预期收束弧."""

        async def _do(c: aiosqlite.Connection) -> None:
            cursor = await c.execute(
                """UPDATE plot_threads
                   SET expected_resolve_arc = ?, updated_at = datetime('now')
                   WHERE thread_id = ?""",
                (expected_resolve_arc, thread_id),
            )
            if cursor.rowcount == 0:
                msg = f"plot thread not found: {thread_id}"
                raise NarrativeError(msg)

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.write",
            table="plot_threads",
            operation="update_expected_resolve_arc",
            thread_id=thread_id,
            expected_resolve_arc=expected_resolve_arc,
        )

    @staticmethod
    def _row_to_thread(row: Row) -> PlotThread:
        return PlotThread(
            thread_id=row["thread_id"],
            project_id=row["project_id"],
            title=row["title"] or "",
            description=row["description"] or "",
            is_mainline=bool(row["is_mainline"]),
            opened_chapter=row["opened_chapter"],
            expected_resolve_arc=row["expected_resolve_arc"],
            status=row["status"],
            last_status_chapter=row["last_status_chapter"],
            last_status_version_id=row["last_status_version_id"],
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    # ------------------------------------------------------------------ #
    # 原子导入（Task 142）
    # ------------------------------------------------------------------ #
    async def import_outline(
        self,
        project_id: str,
        outline: StoryOutline | None,
        arcs: list[ArcPlan],
        threads: list[PlotThread],
    ) -> None:
        """在单个事务中写入大纲 + 弧规划 + 线索；任一步失败则整体回滚.

        Raises:
            NarrativeError: 写入失败（已回滚，不留半份数据）。
        """
        async with get_db() as conn:
            try:
                if outline is not None:
                    await self.upsert_outline(outline, conn=conn)
                for arc in arcs:
                    await self.add_arc_plan(arc, conn=conn)
                for thread in threads:
                    await self.add_thread(thread, conn=conn)
                await conn.commit()
            except NarrativeError:
                await conn.rollback()
                raise
            except Exception as exc:  # noqa: BLE001 - 统一转自定义异常并回滚
                await conn.rollback()
                msg = f"大纲导入失败，已回滚: {exc}"
                raise NarrativeError(msg) from exc
        logger.info(
            "repository.write",
            table="narrative_skeleton",
            operation="import_outline",
            project_id=project_id,
            arcs=len(arcs),
            threads=len(threads),
        )
