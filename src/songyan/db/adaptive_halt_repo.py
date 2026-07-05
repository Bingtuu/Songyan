"""Repository for adaptive halt decisions (V7 Task 169a)."""

from __future__ import annotations

from datetime import datetime
from sqlite3 import Row

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import SongyanError
from songyan.models import AdaptiveHaltDecision, AdaptiveHaltReason
from songyan.utils.json_helpers import from_json as _from_json
from songyan.utils.json_helpers import to_json as _to_json

logger = structlog.get_logger(__name__)


class AdaptiveHaltDecisionRepositoryError(SongyanError):
    """Adaptive halt decision repository error."""


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


class AdaptiveHaltDecisionRepository:
    """Read/write adaptive halt decision ledger rows."""

    async def create(self, decision: AdaptiveHaltDecision) -> None:
        """Persist one adaptive halt decision."""
        async with get_db() as conn:
            try:
                await conn.execute(
                    """INSERT INTO adaptive_halt_decisions (
                        decision_id, project_id, run_id, chapter_start,
                        chapter_end, evaluated_at_chapter, status, reasons_json,
                        evidence_json, policy_id, policy_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        decision.decision_id,
                        decision.project_id,
                        _run_key(decision.run_id),
                        decision.chapter_start,
                        decision.chapter_end,
                        decision.evaluated_at_chapter,
                        decision.status,
                        _to_json(decision.reasons),
                        _to_json(decision.evidence),
                        decision.policy_id,
                        decision.policy_version,
                        decision.created_at.isoformat(),
                    ),
                )
                await conn.commit()
            except Exception as exc:  # noqa: BLE001 - rollback and wrap repository errors
                await conn.rollback()
                msg = f"failed to create adaptive halt decision: {decision.decision_id}"
                raise AdaptiveHaltDecisionRepositoryError(msg) from exc
        logger.info(
            "repository.write",
            table="adaptive_halt_decisions",
            operation="insert",
            decision_id=decision.decision_id,
            status=decision.status,
        )

    async def get(self, decision_id: str) -> AdaptiveHaltDecision | None:
        """Return one decision by id."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM adaptive_halt_decisions WHERE decision_id = ?",
                (decision_id,),
            )
            row = await cursor.fetchone()
        return self._row_to_decision(row) if row is not None else None

    async def list_by_project(
        self,
        project_id: str,
        *,
        run_id: str | None = None,
    ) -> list[AdaptiveHaltDecision]:
        """List decisions for one project and optional run."""
        query = "SELECT * FROM adaptive_halt_decisions WHERE project_id = ?"
        params: list[object] = [project_id]
        if run_id is not None:
            query += " AND run_id = ?"
            params.append(_run_key(run_id))
        query += " ORDER BY evaluated_at_chapter, created_at, decision_id"
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [self._row_to_decision(row) for row in rows]

    async def list_by_chapter(
        self,
        project_id: str,
        chapter_number: int,
        *,
        run_id: str | None = None,
    ) -> list[AdaptiveHaltDecision]:
        """List decisions evaluated at one chapter."""
        query = """SELECT * FROM adaptive_halt_decisions
                   WHERE project_id = ?
                     AND evaluated_at_chapter = ?"""
        params: list[object] = [project_id, chapter_number]
        if run_id is not None:
            query += " AND run_id = ?"
            params.append(_run_key(run_id))
        query += " ORDER BY created_at, decision_id"
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [self._row_to_decision(row) for row in rows]

    @staticmethod
    def _row_to_decision(row: Row) -> AdaptiveHaltDecision:
        reasons = [
            AdaptiveHaltReason(**item)
            for item in _from_json(row["reasons_json"], [])
        ]
        return AdaptiveHaltDecision(
            decision_id=row["decision_id"],
            project_id=row["project_id"],
            run_id=_model_run_id(row["run_id"]),
            chapter_start=row["chapter_start"],
            chapter_end=row["chapter_end"],
            evaluated_at_chapter=row["evaluated_at_chapter"],
            status=row["status"],
            reasons=reasons,
            evidence=_from_json(row["evidence_json"], {}),
            policy_id=row["policy_id"],
            policy_version=row["policy_version"],
            created_at=_parse_dt(row["created_at"]),
        )
