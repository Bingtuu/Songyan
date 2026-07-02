"""Repository for run-level DB maintenance telemetry samples (Task 156)."""

from __future__ import annotations

import uuid
from sqlite3 import Row
from typing import TYPE_CHECKING

from songyan.db.connection import get_db

if TYPE_CHECKING:
    import aiosqlite


class RunDbMetricsRepository:
    """读写 run_db_metrics 表：按 run / chapter 记录 DB 尺寸与扫描耗时."""

    async def create(
        self,
        run_id: str,
        project_id: str,
        chapter_number: int,
        db_size_bytes: int,
        wal_size_bytes: int,
        page_count: int,
        page_size: int,
        scan_latency_ms: float,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        sample_id = f"dbm_{uuid.uuid4().hex[:16]}"

        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO run_db_metrics (
                    sample_id, run_id, project_id, chapter_number,
                    db_size_bytes, wal_size_bytes, page_count, page_size,
                    scan_latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sample_id,
                    run_id,
                    project_id,
                    chapter_number,
                    db_size_bytes,
                    wal_size_bytes,
                    page_count,
                    page_size,
                    scan_latency_ms,
                ),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)

    async def list_by_project(
        self,
        project_id: str,
        *,
        chapter_start: int | None = None,
        chapter_end: int | None = None,
    ) -> list[dict]:
        async with get_db() as conn:
            conn.row_factory = Row
            query = "SELECT * FROM run_db_metrics WHERE project_id = ?"
            params: list = [project_id]
            if chapter_start is not None and chapter_end is not None:
                query += " AND chapter_number BETWEEN ? AND ?"
                params.extend([chapter_start, chapter_end])
            query += " ORDER BY chapter_number"
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def list_by_run(self, run_id: str) -> list[dict]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM run_db_metrics WHERE run_id = ? ORDER BY chapter_number",
                (run_id,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
