"""Repository for ADR-0001 plan-first fact cards.

Create, read, and write entity / attribute / event / time-anchor / clue
rows. Canon lists return ``approval_status='approved'`` only. Attribute
canon rows also require ``source`` of ``plan`` or ``human``.

Pending rows live in the same tables. This repository does not read
settlement extracts and does not write settlement tables.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from sqlite3 import Row
from typing import TYPE_CHECKING

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import SongyanError
from songyan.models.plan_facts import (
    PlanApprovalStatus,
    PlanAttribute,
    PlanClaim,
    PlanClue,
    PlanEntity,
    PlanEvent,
    PlanFactSource,
    PlanTimeAnchor,
    TimeAnchorKind,
)
from songyan.utils.json_helpers import from_json, to_json

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)

_APPROVAL: dict[str, PlanApprovalStatus] = {
    "approved": "approved",
    "pending": "pending",
}
_SOURCE: dict[str, PlanFactSource] = {"plan": "plan", "human": "human"}
_KIND: dict[str, TimeAnchorKind] = {"story": "story", "history": "history"}


class PlanFactError(SongyanError):
    """A fact-card write or read failed a plan-fact invariant."""


def _text(row: Row, key: str) -> str:
    value = row[key]
    if isinstance(value, str):
        return value
    raise PlanFactError(f"{key} is not text")


def _optional_text(row: Row, key: str) -> str | None:
    value = row[key]
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise PlanFactError(f"{key} is not text")


def _integer(row: Row, key: str) -> int:
    value = row[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise PlanFactError(f"{key} is not an integer")
    return value


def _optional_integer(row: Row, key: str) -> int | None:
    value = row[key]
    if value is None:
        return None
    return _integer(row, key)


def _approval(row: Row) -> PlanApprovalStatus:
    try:
        return _APPROVAL[_text(row, "approval_status")]
    except KeyError as exc:
        raise PlanFactError(f"invalid approval_status: {exc}") from exc


def _source(row: Row) -> PlanFactSource:
    try:
        return _SOURCE[_text(row, "source")]
    except KeyError as exc:
        raise PlanFactError(f"invalid source: {exc}") from exc


def _kind(row: Row) -> TimeAnchorKind:
    try:
        return _KIND[_text(row, "kind")]
    except KeyError as exc:
        raise PlanFactError(f"invalid time anchor kind: {exc}") from exc


def _str_list(raw: object) -> list[str]:
    if not isinstance(raw, str):
        return []
    parsed = from_json(raw, [])
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str)]


def _claim_list(raw: object) -> list[PlanClaim]:
    if not isinstance(raw, str):
        return []
    parsed = from_json(raw, [])
    if not isinstance(parsed, list):
        raise PlanFactError("claims is not a list")
    claims: list[PlanClaim] = []
    for item in parsed:
        if not isinstance(item, dict):
            raise PlanFactError("claim entry is not an object")
        claims.append(PlanClaim.model_validate(item))
    return claims


def _int_list(raw: object) -> list[int]:
    if not isinstance(raw, str):
        return []
    parsed = from_json(raw, [])
    if not isinstance(parsed, list):
        return []
    values: list[int] = []
    for item in parsed:
        if isinstance(item, bool) or not isinstance(item, int):
            continue
        values.append(item)
    return values


def _entity_from_row(row: Row) -> PlanEntity:
    return PlanEntity(
        entity_id=_text(row, "entity_id"),
        project_id=_text(row, "project_id"),
        entity_type=_text(row, "entity_type"),
        aliases=_str_list(row["aliases"]),
        approval_status=_approval(row),
    )


def _attribute_from_row(row: Row) -> PlanAttribute:
    return PlanAttribute(
        attribute_id=_text(row, "attribute_id"),
        project_id=_text(row, "project_id"),
        entity_id=_text(row, "entity_id"),
        key=_text(row, "key"),
        value=_text(row, "value"),
        valid_from_ch=_optional_integer(row, "valid_from_ch"),
        valid_to_ch=_optional_integer(row, "valid_to_ch"),
        source=_source(row),
        approval_status=_approval(row),
    )


def _anchor_from_row(row: Row) -> PlanTimeAnchor:
    return PlanTimeAnchor(
        anchor_id=_text(row, "anchor_id"),
        project_id=_text(row, "project_id"),
        date=_text(row, "date"),
        kind=_kind(row),
        approval_status=_approval(row),
    )


def _event_from_row(row: Row) -> PlanEvent:
    return PlanEvent(
        event_id=_text(row, "event_id"),
        project_id=_text(row, "project_id"),
        ch=_integer(row, "ch"),
        time_anchor_id=_optional_text(row, "time_anchor_id"),
        participants=_str_list(row["participants"]),
        causes=_str_list(row["causes"]),
        reveals_evidence=_str_list(row["reveals_evidence"]),
        claims=_claim_list(row["claims"]),
        approval_status=_approval(row),
    )


def _clue_from_row(row: Row) -> PlanClue:
    return PlanClue(
        clue_id=_text(row, "clue_id"),
        project_id=_text(row, "project_id"),
        planted_ch=_integer(row, "planted_ch"),
        revealed_ch=_optional_integer(row, "revealed_ch"),
        must_mention_in=_int_list(row["must_mention_in"]),
        label=_text(row, "label"),
        mention_terms=_str_list(row["mention_terms"]),
        approval_status=_approval(row),
    )


class PlanFactRepository:
    """SQLite read/write helpers for plan-first fact cards."""

    async def write_entity(
        self,
        entity: PlanEntity,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """Insert or replace an entity card."""
        await self._execute(
            conn,
            """INSERT INTO plan_entities (
                entity_id, project_id, entity_type, aliases, approval_status
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                project_id = excluded.project_id,
                entity_type = excluded.entity_type,
                aliases = excluded.aliases,
                approval_status = excluded.approval_status,
                updated_at = datetime('now')""",
            (
                entity.entity_id,
                entity.project_id,
                entity.entity_type,
                to_json(entity.aliases),
                entity.approval_status,
            ),
            table="plan_entities",
            row_id=entity.entity_id,
        )

    async def read_entity(self, entity_id: str) -> PlanEntity | None:
        """Return one entity, or None when the id is unknown."""
        row = await self._fetch_one(
            "SELECT * FROM plan_entities WHERE entity_id = ?",
            (entity_id,),
        )
        if row is None:
            return None
        return _entity_from_row(row)

    async def list_canon_entities(self, project_id: str) -> list[PlanEntity]:
        """Approved entities for one project."""
        return await self._list_entities(project_id, "approved")

    async def list_pending_entities(self, project_id: str) -> list[PlanEntity]:
        """Unapproved entities for one project."""
        return await self._list_entities(project_id, "pending")

    async def write_attribute(
        self,
        attribute: PlanAttribute,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """Insert or replace an attribute card.

        The entity must already exist in the same project. A pending row
        is stored, but it is not canon until a later write marks it approved.
        """

        async def _require_entity(c: aiosqlite.Connection) -> None:
            await _require_same_project(
                c,
                table="plan_entities",
                id_column="entity_id",
                row_id=attribute.entity_id,
                project_id=attribute.project_id,
                label="entity",
            )

        await self._execute(
            conn,
            """INSERT INTO plan_attributes (
                attribute_id, project_id, entity_id, key, value,
                valid_from_ch, valid_to_ch, source, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(attribute_id) DO UPDATE SET
                project_id = excluded.project_id,
                entity_id = excluded.entity_id,
                key = excluded.key,
                value = excluded.value,
                valid_from_ch = excluded.valid_from_ch,
                valid_to_ch = excluded.valid_to_ch,
                source = excluded.source,
                approval_status = excluded.approval_status,
                updated_at = datetime('now')""",
            (
                attribute.attribute_id,
                attribute.project_id,
                attribute.entity_id,
                attribute.key,
                attribute.value,
                attribute.valid_from_ch,
                attribute.valid_to_ch,
                attribute.source,
                attribute.approval_status,
            ),
            table="plan_attributes",
            row_id=attribute.attribute_id,
            before=_require_entity,
        )

    async def read_attribute(self, attribute_id: str) -> PlanAttribute | None:
        """Return one attribute, or None when the id is unknown."""
        row = await self._fetch_one(
            "SELECT * FROM plan_attributes WHERE attribute_id = ?",
            (attribute_id,),
        )
        if row is None:
            return None
        return _attribute_from_row(row)

    async def list_canon_attributes(self, project_id: str) -> list[PlanAttribute]:
        """Approved plan|human attributes. Pending rows are excluded."""
        return await self._list_attributes(project_id, "approved")

    async def list_pending_attributes(self, project_id: str) -> list[PlanAttribute]:
        """Attributes waiting for approval."""
        return await self._list_attributes(project_id, "pending")

    async def write_time_anchor(
        self,
        anchor: PlanTimeAnchor,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """Insert or replace a time anchor."""
        await self._execute(
            conn,
            """INSERT INTO plan_time_anchors (
                anchor_id, project_id, date, kind, approval_status
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(anchor_id) DO UPDATE SET
                project_id = excluded.project_id,
                date = excluded.date,
                kind = excluded.kind,
                approval_status = excluded.approval_status,
                updated_at = datetime('now')""",
            (
                anchor.anchor_id,
                anchor.project_id,
                anchor.date,
                anchor.kind,
                anchor.approval_status,
            ),
            table="plan_time_anchors",
            row_id=anchor.anchor_id,
        )

    async def read_time_anchor(self, anchor_id: str) -> PlanTimeAnchor | None:
        """Return one time anchor, or None when the id is unknown."""
        row = await self._fetch_one(
            "SELECT * FROM plan_time_anchors WHERE anchor_id = ?",
            (anchor_id,),
        )
        if row is None:
            return None
        return _anchor_from_row(row)

    async def list_canon_time_anchors(self, project_id: str) -> list[PlanTimeAnchor]:
        """Approved time anchors for one project."""
        return await self._list_time_anchors(project_id, "approved")

    async def list_pending_time_anchors(self, project_id: str) -> list[PlanTimeAnchor]:
        """Unapproved time anchors for one project."""
        return await self._list_time_anchors(project_id, "pending")

    async def write_event(
        self,
        event: PlanEvent,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """Insert or replace an event card.

        When ``time_anchor_id`` is set, that anchor must belong to the
        same project.
        """

        async def _require_anchor(c: aiosqlite.Connection) -> None:
            if event.time_anchor_id is None:
                return
            await _require_same_project(
                c,
                table="plan_time_anchors",
                id_column="anchor_id",
                row_id=event.time_anchor_id,
                project_id=event.project_id,
                label="time_anchor",
            )

        await self._execute(
            conn,
            """INSERT INTO plan_events (
                event_id, project_id, ch, time_anchor_id,
                participants, causes, reveals_evidence, claims, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                project_id = excluded.project_id,
                ch = excluded.ch,
                time_anchor_id = excluded.time_anchor_id,
                participants = excluded.participants,
                causes = excluded.causes,
                reveals_evidence = excluded.reveals_evidence,
                claims = excluded.claims,
                approval_status = excluded.approval_status,
                updated_at = datetime('now')""",
            (
                event.event_id,
                event.project_id,
                event.ch,
                event.time_anchor_id,
                to_json(event.participants),
                to_json(event.causes),
                to_json(event.reveals_evidence),
                to_json([claim.model_dump() for claim in event.claims]),
                event.approval_status,
            ),
            table="plan_events",
            row_id=event.event_id,
            before=_require_anchor,
        )

    async def read_event(self, event_id: str) -> PlanEvent | None:
        """Return one event, or None when the id is unknown."""
        row = await self._fetch_one(
            "SELECT * FROM plan_events WHERE event_id = ?",
            (event_id,),
        )
        if row is None:
            return None
        return _event_from_row(row)

    async def list_canon_events(self, project_id: str) -> list[PlanEvent]:
        """Approved events for one project."""
        return await self._list_events(project_id, "approved")

    async def list_pending_events(self, project_id: str) -> list[PlanEvent]:
        """Unapproved events for one project."""
        return await self._list_events(project_id, "pending")

    async def write_clue(
        self,
        clue: PlanClue,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """Insert or replace a mystery clue card."""
        await self._execute(
            conn,
            """INSERT INTO plan_clues (
                clue_id, project_id, planted_ch, revealed_ch,
                must_mention_in, label, mention_terms, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(clue_id) DO UPDATE SET
                project_id = excluded.project_id,
                planted_ch = excluded.planted_ch,
                revealed_ch = excluded.revealed_ch,
                must_mention_in = excluded.must_mention_in,
                label = excluded.label,
                mention_terms = excluded.mention_terms,
                approval_status = excluded.approval_status,
                updated_at = datetime('now')""",
            (
                clue.clue_id,
                clue.project_id,
                clue.planted_ch,
                clue.revealed_ch,
                to_json(clue.must_mention_in),
                clue.label,
                to_json(clue.mention_terms),
                clue.approval_status,
            ),
            table="plan_clues",
            row_id=clue.clue_id,
        )

    async def read_clue(self, clue_id: str) -> PlanClue | None:
        """Return one clue, or None when the id is unknown."""
        row = await self._fetch_one(
            "SELECT * FROM plan_clues WHERE clue_id = ?",
            (clue_id,),
        )
        if row is None:
            return None
        return _clue_from_row(row)

    async def list_canon_clues(self, project_id: str) -> list[PlanClue]:
        """Approved clues for one project."""
        return await self._list_clues(project_id, "approved")

    async def list_pending_clues(self, project_id: str) -> list[PlanClue]:
        """Unapproved clues for one project."""
        return await self._list_clues(project_id, "pending")

    async def _list_entities(
        self, project_id: str, approval_status: PlanApprovalStatus
    ) -> list[PlanEntity]:
        rows = await self._fetch_all(
            """SELECT * FROM plan_entities
            WHERE project_id = ? AND approval_status = ?
            ORDER BY entity_id""",
            (project_id, approval_status),
        )
        return [_entity_from_row(row) for row in rows]

    async def _list_attributes(
        self, project_id: str, approval_status: PlanApprovalStatus
    ) -> list[PlanAttribute]:
        source_clause = ""
        if approval_status == "approved":
            source_clause = " AND source IN ('plan', 'human')"
        rows = await self._fetch_all(
            f"""SELECT * FROM plan_attributes
            WHERE project_id = ? AND approval_status = ?{source_clause}
            ORDER BY attribute_id""",
            (project_id, approval_status),
        )
        return [_attribute_from_row(row) for row in rows]

    async def _list_time_anchors(
        self, project_id: str, approval_status: PlanApprovalStatus
    ) -> list[PlanTimeAnchor]:
        rows = await self._fetch_all(
            """SELECT * FROM plan_time_anchors
            WHERE project_id = ? AND approval_status = ?
            ORDER BY anchor_id""",
            (project_id, approval_status),
        )
        return [_anchor_from_row(row) for row in rows]

    async def _list_events(
        self, project_id: str, approval_status: PlanApprovalStatus
    ) -> list[PlanEvent]:
        rows = await self._fetch_all(
            """SELECT * FROM plan_events
            WHERE project_id = ? AND approval_status = ?
            ORDER BY event_id""",
            (project_id, approval_status),
        )
        return [_event_from_row(row) for row in rows]

    async def _list_clues(
        self, project_id: str, approval_status: PlanApprovalStatus
    ) -> list[PlanClue]:
        rows = await self._fetch_all(
            """SELECT * FROM plan_clues
            WHERE project_id = ? AND approval_status = ?
            ORDER BY clue_id""",
            (project_id, approval_status),
        )
        return [_clue_from_row(row) for row in rows]

    async def _execute(
        self,
        conn: aiosqlite.Connection | None,
        statement: str,
        params: tuple[object, ...],
        *,
        table: str,
        row_id: str,
        before: Callable[[aiosqlite.Connection], Awaitable[None]] | None = None,
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            if before is not None:
                await before(c)
            await c.execute(statement, params)

        if conn is None:
            async with get_db() as owned:
                await _do(owned)
                await owned.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.write",
            table=table,
            operation="upsert",
            row_id=row_id,
        )

    async def _fetch_one(self, statement: str, params: tuple[object, ...]) -> Row | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(statement, params)
            row = await cursor.fetchone()
        if row is None:
            return None
        return row

    async def _fetch_all(self, statement: str, params: tuple[object, ...]) -> list[Row]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(statement, params)
            rows = await cursor.fetchall()
        return list(rows)


async def _require_same_project(
    conn: aiosqlite.Connection,
    *,
    table: str,
    id_column: str,
    row_id: str,
    project_id: str,
    label: str,
) -> None:
    cursor = await conn.execute(
        f"SELECT project_id FROM {table} WHERE {id_column} = ?",
        (row_id,),
    )
    found = await cursor.fetchone()
    owner = found[0] if found is not None else None
    if owner != project_id:
        raise PlanFactError(
            f"{label} {row_id} must reference a row in project {project_id}"
        )
