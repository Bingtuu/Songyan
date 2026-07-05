"""Repository for V7 re-plan proposals (Task 166a)."""

from __future__ import annotations

from datetime import datetime
from sqlite3 import Row
from typing import Any

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import SongyanError
from songyan.models import (
    PlanningConstraint,
    ReplanAction,
    ReplanProposal,
    ReplanProposalStatus,
)
from songyan.utils.json_helpers import from_json as _from_json
from songyan.utils.json_helpers import to_json as _to_json

logger = structlog.get_logger(__name__)


class ReplanRepositoryError(SongyanError):
    """Re-plan proposal repository error."""


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


class ReplanProposalRepository:
    """Read/write ReplanProposal records and planning constraints."""

    async def create(self, proposal: ReplanProposal) -> None:
        """Persist one draft proposal and its ordered actions atomically."""
        if proposal.status != "draft":
            msg = "Task 166a can only create draft replan proposals"
            raise ReplanRepositoryError(msg)
        for action in proposal.actions:
            if action.proposal_id != proposal.proposal_id:
                msg = (
                    "replan action proposal_id mismatch: "
                    f"{action.action_id} -> {action.proposal_id}"
                )
                raise ReplanRepositoryError(msg)

        async with get_db() as conn:
            try:
                await conn.execute(
                    """INSERT INTO replan_proposals (
                        proposal_id, project_id, source_arc_index,
                        source_start_chapter, source_end_chapter, status,
                        summary, evidence_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        proposal.proposal_id,
                        proposal.project_id,
                        proposal.source_arc_index,
                        proposal.source_start_chapter,
                        proposal.source_end_chapter,
                        proposal.status,
                        proposal.summary,
                        _to_json(proposal.evidence),
                        proposal.created_at.isoformat(),
                        proposal.updated_at.isoformat(),
                    ),
                )
                for action in proposal.actions:
                    await conn.execute(
                        """INSERT INTO replan_actions (
                            action_id, proposal_id, project_id, action_order,
                            target_type, target_id, field, old_value_json,
                            new_value_json, reason, evidence_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            action.action_id,
                            action.proposal_id,
                            proposal.project_id,
                            action.action_order,
                            action.target_type,
                            action.target_id,
                            action.field,
                            _to_json(action.old_value),
                            _to_json(action.new_value),
                            action.reason,
                            _to_json(action.evidence),
                            action.created_at.isoformat(),
                        ),
                    )
                await conn.commit()
            except Exception as exc:  # noqa: BLE001 - rollback and wrap repository errors
                await conn.rollback()
                msg = f"failed to create replan proposal: {proposal.proposal_id}"
                raise ReplanRepositoryError(msg) from exc

        logger.info(
            "repository.write",
            table="replan_proposals",
            operation="insert",
            proposal_id=proposal.proposal_id,
            actions=len(proposal.actions),
        )

    async def get(
        self,
        proposal_id: str,
        conn: Any | None = None,
    ) -> ReplanProposal | None:
        """Return a proposal with actions."""
        async def _do(c: Any) -> ReplanProposal | None:
            c.row_factory = Row
            cursor = await c.execute(
                "SELECT * FROM replan_proposals WHERE proposal_id = ?",
                (proposal_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            actions = await self._list_actions(c, proposal_id)
            return self._row_to_proposal(row, actions)

        if conn is None:
            async with get_db() as c:
                return await _do(c)
        return await _do(conn)

    async def list_by_project(
        self,
        project_id: str,
        *,
        status: ReplanProposalStatus | None = None,
        include_actions: bool = False,
    ) -> list[ReplanProposal]:
        """List proposals for one project."""
        query = "SELECT * FROM replan_proposals WHERE project_id = ?"
        params: list[Any] = [project_id]
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC, proposal_id DESC"

        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            action_map: dict[str, list[ReplanAction]] = {}
            if include_actions:
                for row in rows:
                    action_map[row["proposal_id"]] = await self._list_actions(
                        conn, row["proposal_id"]
                    )
        return [
            self._row_to_proposal(row, action_map.get(row["proposal_id"], []))
            for row in rows
        ]

    async def list_actions(self, proposal_id: str) -> list[ReplanAction]:
        """List actions attached to one proposal."""
        async with get_db() as conn:
            conn.row_factory = Row
            return await self._list_actions(conn, proposal_id)

    async def approve(
        self,
        proposal_id: str,
        *,
        approved_by: str = "human",
        conn: Any | None = None,
    ) -> ReplanProposal:
        """Transition draft -> approved."""
        return await self._transition_status(
            proposal_id,
            expected_status="draft",
            next_status="approved",
            actor_field="approved_by",
            actor_value=approved_by,
            timestamp_field="approved_at",
            conn=conn,
        )

    async def reject(
        self,
        proposal_id: str,
        *,
        reason: str,
        conn: Any | None = None,
    ) -> ReplanProposal:
        """Transition draft -> rejected."""
        return await self._transition_status(
            proposal_id,
            expected_status="draft",
            next_status="rejected",
            actor_field="rejected_reason",
            actor_value=reason,
            timestamp_field="rejected_at",
            conn=conn,
        )

    async def mark_applied(
        self,
        proposal_id: str,
        *,
        applied_by: str = "human",
        conn: Any | None = None,
    ) -> ReplanProposal:
        """Transition approved -> applied."""
        return await self._transition_status(
            proposal_id,
            expected_status="approved",
            next_status="applied",
            actor_field="applied_by",
            actor_value=applied_by,
            timestamp_field="applied_at",
            conn=conn,
        )

    async def _transition_status(
        self,
        proposal_id: str,
        *,
        expected_status: str,
        next_status: str,
        actor_field: str,
        actor_value: str,
        timestamp_field: str,
        conn: Any | None = None,
    ) -> ReplanProposal:
        now = datetime.now().isoformat()

        async def _do(c: Any) -> ReplanProposal:
            c.row_factory = Row
            cursor = await c.execute(
                "SELECT status FROM replan_proposals WHERE proposal_id = ?",
                (proposal_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                msg = f"replan proposal not found: {proposal_id}"
                raise ReplanRepositoryError(msg)
            current = row["status"]
            if current != expected_status:
                msg = (
                    f"illegal replan proposal status transition "
                    f"{current} -> {next_status} (proposal_id={proposal_id})"
                )
                raise ReplanRepositoryError(msg)
            await c.execute(
                f"""UPDATE replan_proposals
                   SET status = ?, {timestamp_field} = ?, {actor_field} = ?,
                       updated_at = ?
                   WHERE proposal_id = ?""",
                (next_status, now, actor_value, now, proposal_id),
            )
            updated = await self.get(proposal_id, conn=c)
            if updated is None:
                msg = f"replan proposal not found after status update: {proposal_id}"
                raise ReplanRepositoryError(msg)
            return updated

        if conn is None:
            async with get_db() as c:
                try:
                    proposal = await _do(c)
                    await c.commit()
                except Exception as exc:  # noqa: BLE001 - rollback and wrap status errors
                    await c.rollback()
                    if isinstance(exc, ReplanRepositoryError):
                        raise
                    msg = f"failed to transition replan proposal: {proposal_id}"
                    raise ReplanRepositoryError(msg) from exc
        else:
            proposal = await _do(conn)
        logger.info(
            "repository.write",
            table="replan_proposals",
            operation=f"status_{next_status}",
            proposal_id=proposal_id,
        )
        return proposal

    async def create_planning_constraint(
        self,
        constraint: PlanningConstraint,
        conn: Any | None = None,
    ) -> None:
        """Persist one future-planning constraint."""

        async def _do(c: Any) -> None:
            await c.execute(
                """INSERT INTO planning_constraints (
                    constraint_id, project_id, source_proposal_id,
                    source_action_id, target_id, constraint_type, content,
                    reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    constraint.constraint_id,
                    constraint.project_id,
                    constraint.source_proposal_id,
                    constraint.source_action_id,
                    constraint.target_id,
                    constraint.constraint_type,
                    constraint.content,
                    constraint.reason,
                    constraint.status,
                    constraint.created_at.isoformat(),
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
            table="planning_constraints",
            operation="insert",
            constraint_id=constraint.constraint_id,
        )

    async def list_planning_constraints(
        self,
        project_id: str,
        *,
        status: str | None = "active",
    ) -> list[PlanningConstraint]:
        """List persisted planning constraints for one project."""
        query = "SELECT * FROM planning_constraints WHERE project_id = ?"
        params: list[Any] = [project_id]
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at, constraint_id"
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [self._row_to_planning_constraint(row) for row in rows]

    async def _list_actions(
        self,
        conn: Any,
        proposal_id: str,
    ) -> list[ReplanAction]:
        cursor = await conn.execute(
            """SELECT * FROM replan_actions
               WHERE proposal_id = ?
               ORDER BY action_order, action_id""",
            (proposal_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_action(row) for row in rows]

    @staticmethod
    def _row_to_proposal(
        row: Row,
        actions: list[ReplanAction],
    ) -> ReplanProposal:
        return ReplanProposal(
            proposal_id=row["proposal_id"],
            project_id=row["project_id"],
            source_arc_index=row["source_arc_index"],
            source_start_chapter=row["source_start_chapter"],
            source_end_chapter=row["source_end_chapter"],
            status=row["status"],
            summary=row["summary"] or "",
            evidence=_from_json(row["evidence_json"], {}),
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
            actions=actions,
        )

    @staticmethod
    def _row_to_action(row: Row) -> ReplanAction:
        return ReplanAction(
            action_id=row["action_id"],
            proposal_id=row["proposal_id"],
            action_order=row["action_order"],
            target_type=row["target_type"],
            target_id=row["target_id"] or "",
            field=row["field"],
            old_value=_from_json(row["old_value_json"], None),
            new_value=_from_json(row["new_value_json"], None),
            reason=row["reason"] or "",
            evidence=_from_json(row["evidence_json"], {}),
            created_at=_parse_dt(row["created_at"]),
        )

    @staticmethod
    def _row_to_planning_constraint(row: Row) -> PlanningConstraint:
        return PlanningConstraint(
            constraint_id=row["constraint_id"],
            project_id=row["project_id"],
            source_proposal_id=row["source_proposal_id"],
            source_action_id=row["source_action_id"],
            target_id=row["target_id"] or "",
            constraint_type=row["constraint_type"],
            content=row["content"],
            reason=row["reason"] or "",
            status=row["status"],
            created_at=_parse_dt(row["created_at"]),
        )
