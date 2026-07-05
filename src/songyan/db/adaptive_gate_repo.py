"""Repository for adaptive gate signal snapshots (V7 Task 168a)."""

from __future__ import annotations

from datetime import datetime
from sqlite3 import Row

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import SongyanError
from songyan.models import (
    AdaptiveGateCleanlinessSignals,
    AdaptiveGateContextSignals,
    AdaptiveGateContinuitySignals,
    AdaptiveGateLiterarySignals,
    AdaptiveGateNarrativeSignals,
    AdaptiveGateQualitySignals,
    AdaptiveGateSignalSnapshot,
)
from songyan.utils.json_helpers import from_json as _from_json
from songyan.utils.json_helpers import to_json as _to_json

logger = structlog.get_logger(__name__)


class AdaptiveGateSignalRepositoryError(SongyanError):
    """Adaptive gate signal repository error."""


def _run_key(run_id: str | None) -> str:
    return run_id or ""


def _model_run_id(value: str | None) -> str | None:
    return value or None


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


class AdaptiveGateSignalRepository:
    """Read/write adaptive gate signal snapshots."""

    async def upsert(self, snapshot: AdaptiveGateSignalSnapshot) -> None:
        """Insert or replace one chapter-level signal snapshot."""
        now = datetime.now().isoformat()
        async with get_db() as conn:
            try:
                await conn.execute(
                    """INSERT INTO adaptive_gate_signal_snapshots (
                        snapshot_id, project_id, run_id, chapter_number,
                        source_status_json, continuity_json, quality_json,
                        literary_json, cleanliness_json, context_json,
                        narrative_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id, run_id, chapter_number) DO UPDATE SET
                        snapshot_id = excluded.snapshot_id,
                        source_status_json = excluded.source_status_json,
                        continuity_json = excluded.continuity_json,
                        quality_json = excluded.quality_json,
                        literary_json = excluded.literary_json,
                        cleanliness_json = excluded.cleanliness_json,
                        context_json = excluded.context_json,
                        narrative_json = excluded.narrative_json,
                        updated_at = excluded.updated_at""",
                    (
                        snapshot.snapshot_id,
                        snapshot.project_id,
                        _run_key(snapshot.run_id),
                        snapshot.chapter_number,
                        _to_json(snapshot.source_status),
                        _to_json(snapshot.continuity),
                        _to_json(snapshot.quality),
                        _to_json(snapshot.literary),
                        _to_json(snapshot.cleanliness),
                        _to_json(snapshot.context),
                        _to_json(snapshot.narrative),
                        snapshot.created_at.isoformat(),
                        now,
                    ),
                )
                await conn.commit()
            except Exception as exc:  # noqa: BLE001 - rollback and wrap repository errors
                await conn.rollback()
                msg = (
                    "failed to upsert adaptive gate signal snapshot: "
                    f"{snapshot.project_id}/Ch{snapshot.chapter_number}"
                )
                raise AdaptiveGateSignalRepositoryError(msg) from exc
        logger.info(
            "repository.write",
            table="adaptive_gate_signal_snapshots",
            operation="upsert",
            project_id=snapshot.project_id,
            run_id=snapshot.run_id,
            chapter_number=snapshot.chapter_number,
        )

    async def get(
        self,
        project_id: str,
        chapter_number: int,
        *,
        run_id: str | None = None,
    ) -> AdaptiveGateSignalSnapshot | None:
        """Return one snapshot by project/run/chapter."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM adaptive_gate_signal_snapshots
                   WHERE project_id = ?
                     AND run_id = ?
                     AND chapter_number = ?""",
                (project_id, _run_key(run_id), chapter_number),
            )
            row = await cursor.fetchone()
        return self._row_to_snapshot(row) if row is not None else None

    async def list_range(
        self,
        project_id: str,
        start_chapter: int,
        end_chapter: int,
        *,
        run_id: str | None = None,
    ) -> list[AdaptiveGateSignalSnapshot]:
        """List snapshots for one project/run and inclusive chapter range."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM adaptive_gate_signal_snapshots
                   WHERE project_id = ?
                     AND run_id = ?
                     AND chapter_number BETWEEN ? AND ?
                   ORDER BY chapter_number, snapshot_id""",
                (project_id, _run_key(run_id), start_chapter, end_chapter),
            )
            rows = await cursor.fetchall()
        return [self._row_to_snapshot(row) for row in rows]

    async def delete_range(
        self,
        project_id: str,
        start_chapter: int,
        end_chapter: int,
        *,
        run_id: str | None = None,
    ) -> int:
        """Delete snapshots for one project/run and inclusive chapter range."""
        async with get_db() as conn:
            cursor = await conn.execute(
                """DELETE FROM adaptive_gate_signal_snapshots
                   WHERE project_id = ?
                     AND run_id = ?
                     AND chapter_number BETWEEN ? AND ?""",
                (project_id, _run_key(run_id), start_chapter, end_chapter),
            )
            await conn.commit()
            deleted = cursor.rowcount
        logger.info(
            "repository.write",
            table="adaptive_gate_signal_snapshots",
            operation="delete_range",
            project_id=project_id,
            run_id=run_id,
            deleted=deleted,
        )
        return int(deleted)

    @staticmethod
    def _row_to_snapshot(row: Row) -> AdaptiveGateSignalSnapshot:
        return AdaptiveGateSignalSnapshot(
            snapshot_id=row["snapshot_id"],
            project_id=row["project_id"],
            run_id=_model_run_id(row["run_id"]),
            chapter_number=row["chapter_number"],
            source_status=_from_json(row["source_status_json"], {}),
            continuity=AdaptiveGateContinuitySignals(
                **_from_json(row["continuity_json"], {})
            ),
            quality=AdaptiveGateQualitySignals(**_from_json(row["quality_json"], {})),
            literary=AdaptiveGateLiterarySignals(**_from_json(row["literary_json"], {})),
            cleanliness=AdaptiveGateCleanlinessSignals(
                **_from_json(row["cleanliness_json"], {})
            ),
            context=AdaptiveGateContextSignals(**_from_json(row["context_json"], {})),
            narrative=AdaptiveGateNarrativeSignals(
                **_from_json(row["narrative_json"], {})
            ),
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )
