"""Repository for run-level quality-debt ledger (V6 Task 146)."""

from __future__ import annotations

from sqlite3 import Row

import structlog
from pydantic import BaseModel

from songyan.db.connection import get_db

logger = structlog.get_logger(__name__)


class RunQualityDebtRow(BaseModel):
    """run 级质量债汇总（run_quality_debt 表一行）."""

    run_id: str
    project_id: str
    total_chapters: int = 0
    degraded_count: int = 0
    convergence_failed_count: int = 0
    qg_false_count: int = 0
    degraded_ratio: float = 0.0
    convergence_ratio: float = 0.0
    t4_breached: bool = False


class RunQualityDebtRepository:
    """Repository for the run-level quality-debt ledger."""

    async def upsert(self, row: RunQualityDebtRow) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO run_quality_debt (
                    run_id, project_id, total_chapters, degraded_count,
                    convergence_failed_count, qg_false_count,
                    degraded_ratio, convergence_ratio, t4_breached, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(run_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    total_chapters = excluded.total_chapters,
                    degraded_count = excluded.degraded_count,
                    convergence_failed_count = excluded.convergence_failed_count,
                    qg_false_count = excluded.qg_false_count,
                    degraded_ratio = excluded.degraded_ratio,
                    convergence_ratio = excluded.convergence_ratio,
                    t4_breached = excluded.t4_breached,
                    updated_at = datetime('now')""",
                (
                    row.run_id,
                    row.project_id,
                    row.total_chapters,
                    row.degraded_count,
                    row.convergence_failed_count,
                    row.qg_false_count,
                    row.degraded_ratio,
                    row.convergence_ratio,
                    int(row.t4_breached),
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="run_quality_debt",
            operation="upsert",
            run_id=row.run_id,
        )

    async def get(self, run_id: str) -> RunQualityDebtRow | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM run_quality_debt WHERE run_id = ?",
                (run_id,),
            )
            row = await cursor.fetchone()
        return self._row_to_model(row) if row is not None else None

    async def list_by_project(self, project_id: str) -> list[RunQualityDebtRow]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM run_quality_debt WHERE project_id = ? ORDER BY updated_at",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    @staticmethod
    def _row_to_model(row: Row) -> RunQualityDebtRow:
        return RunQualityDebtRow(
            run_id=row["run_id"],
            project_id=row["project_id"],
            total_chapters=row["total_chapters"],
            degraded_count=row["degraded_count"],
            convergence_failed_count=row["convergence_failed_count"],
            qg_false_count=row["qg_false_count"],
            degraded_ratio=row["degraded_ratio"],
            convergence_ratio=row["convergence_ratio"],
            t4_breached=bool(row["t4_breached"]),
        )
