"""Async repository for project-level multi-chapter run states."""

from __future__ import annotations

import json
from sqlite3 import Row

import structlog

from songyan.db.connection import get_db
from songyan.models import ProjectRunState

logger = structlog.get_logger(__name__)


class ProjectRunRepository:
    """Repository for project_runs table."""

    async def create(self, run_state: ProjectRunState) -> None:
        """创建项目运行记录."""
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO project_runs (
                    run_id, project_id, chapter_range_start, chapter_range_end,
                    current_chapter, completed_chapters, failed_chapters,
                    accumulated_summary, total_cost, status, pause_reason,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_state.run_id,
                    run_state.project_id,
                    run_state.chapter_range_start,
                    run_state.chapter_range_end,
                    run_state.current_chapter,
                    json.dumps(run_state.completed_chapters, ensure_ascii=False),
                    json.dumps(run_state.failed_chapters, ensure_ascii=False),
                    run_state.accumulated_summary,
                    run_state.total_cost,
                    run_state.status,
                    run_state.pause_reason,
                    run_state.created_at.isoformat(),
                    run_state.updated_at.isoformat(),
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="project_runs",
            operation="create",
            run_id=run_state.run_id,
            project_id=run_state.project_id,
        )

    async def get(self, run_id: str) -> ProjectRunState | None:
        """按 run_id 查询."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM project_runs WHERE run_id = ?",
                (run_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    async def update(self, run_state: ProjectRunState) -> None:
        """更新运行状态."""
        from datetime import datetime

        run_state.updated_at = datetime.now()
        async with get_db() as conn:
            await conn.execute(
                """UPDATE project_runs SET
                    current_chapter = ?,
                    completed_chapters = ?,
                    failed_chapters = ?,
                    accumulated_summary = ?,
                    total_cost = ?,
                    status = ?,
                    pause_reason = ?,
                    updated_at = ?
                WHERE run_id = ?""",
                (
                    run_state.current_chapter,
                    json.dumps(run_state.completed_chapters, ensure_ascii=False),
                    json.dumps(run_state.failed_chapters, ensure_ascii=False),
                    run_state.accumulated_summary,
                    run_state.total_cost,
                    run_state.status,
                    run_state.pause_reason,
                    run_state.updated_at.isoformat(),
                    run_state.run_id,
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="project_runs",
            operation="update",
            run_id=run_state.run_id,
            status=run_state.status,
        )

    async def list_by_project(self, project_id: str) -> list[ProjectRunState]:
        """查询项目下的所有运行记录."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM project_runs WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def _row_to_model(self, row: Row) -> ProjectRunState:
        from datetime import datetime

        return ProjectRunState(
            run_id=row["run_id"],
            project_id=row["project_id"],
            chapter_range_start=row["chapter_range_start"],
            chapter_range_end=row["chapter_range_end"],
            current_chapter=row["current_chapter"] or 0,
            completed_chapters=json.loads(row["completed_chapters"] or "[]"),
            failed_chapters=json.loads(row["failed_chapters"] or "[]"),
            accumulated_summary=row["accumulated_summary"] or "",
            total_cost=row["total_cost"] or 0.0,
            status=row["status"] or "running",
            # Task 193.r: 旧库未迁移时无此列，回退 None（评测侧按保守旧行为处理）
            pause_reason=(
                row["pause_reason"] if "pause_reason" in row.keys() else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
