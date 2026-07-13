"""171v/171w literary guardrail audit helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from songyan.db.connection import get_db

GUARDRAIL_FIELDS: tuple[str, ...] = (
    "protagonist_active_choice",
    "new_concept_budget",
    "fatigue_motif_replacements",
    "supporting_character_goal",
)


@dataclass(slots=True)
class GuardrailPersistenceAuditRow:
    """Per-chapter persistence status for 171v structured guardrails."""

    chapter_number: int
    brief_id: str | None = None
    accepted_version_id: str | None = None
    accepted_creative_brief_id: str | None = None
    brief_fields_present: dict[str, bool] = field(default_factory=dict)
    accepted_snapshot_fields_present: dict[str, bool] = field(default_factory=dict)
    accepted_replayable: bool = False
    revision_versions_missing_guardrail_metadata: list[str] = field(default_factory=list)

    @property
    def brief_complete(self) -> bool:
        return all(self.brief_fields_present.get(field, False) for field in GUARDRAIL_FIELDS)

    @property
    def accepted_snapshot_complete(self) -> bool:
        return all(
            self.accepted_snapshot_fields_present.get(field, False)
            for field in GUARDRAIL_FIELDS
        )

    @property
    def revision_metadata_complete(self) -> bool:
        return not self.revision_versions_missing_guardrail_metadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "brief_id": self.brief_id,
            "accepted_version_id": self.accepted_version_id,
            "accepted_creative_brief_id": self.accepted_creative_brief_id,
            "brief_fields_present": self.brief_fields_present,
            "accepted_snapshot_fields_present": self.accepted_snapshot_fields_present,
            "accepted_replayable": self.accepted_replayable,
            "revision_versions_missing_guardrail_metadata": (
                self.revision_versions_missing_guardrail_metadata
            ),
            "brief_complete": self.brief_complete,
            "accepted_snapshot_complete": self.accepted_snapshot_complete,
            "revision_metadata_complete": self.revision_metadata_complete,
        }


def _loads_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict | list | str):
        return bool(value)
    return True


def _presence_from_mapping(mapping: dict[str, Any] | None) -> dict[str, bool]:
    mapping = mapping or {}
    return {field: _has_value(mapping.get(field)) for field in GUARDRAIL_FIELDS}


async def audit_171v_guardrail_persistence(
    project_id: str,
    start: int,
    end: int,
) -> list[GuardrailPersistenceAuditRow]:
    """Audit whether 171v guardrails are persisted and replayable for a range."""
    async with get_db() as conn:
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }

        cursor = await conn.execute(
            """SELECT cb.*
               FROM creative_briefs cb
               JOIN (
                   SELECT chapter_number, MAX(created_at || brief_id) AS latest_key
                   FROM creative_briefs
                   WHERE project_id = ?
                     AND chapter_number BETWEEN ? AND ?
                   GROUP BY chapter_number
               ) latest
                 ON latest.chapter_number = cb.chapter_number
                AND latest.latest_key = cb.created_at || cb.brief_id
               WHERE cb.project_id = ?""",
            (project_id, start, end, project_id),
        )
        brief_rows = {int(row["chapter_number"]): row for row in await cursor.fetchall()}

        cursor = await conn.execute(
            """SELECT h.chapter_number,
                      h.accepted_version_id,
                      v.creative_brief_id AS accepted_creative_brief_id,
                      v.generation_metadata AS accepted_generation_metadata
               FROM chapter_heads h
               LEFT JOIN chapter_versions v ON v.version_id = h.accepted_version_id
               WHERE h.project_id = ?
                 AND h.chapter_number BETWEEN ? AND ?""",
            (project_id, start, end),
        )
        accepted_rows = {int(row["chapter_number"]): row for row in await cursor.fetchall()}

        cursor = await conn.execute(
            """SELECT version_id, chapter_number, creative_brief_id, generation_metadata
               FROM chapter_versions
               WHERE project_id = ?
                 AND chapter_number BETWEEN ? AND ?
                 AND version_type = 'revision'
               ORDER BY chapter_number, version_number""",
            (project_id, start, end),
        )
        revision_rows = await cursor.fetchall()

    missing_revision_metadata: dict[int, list[str]] = {}
    for row in revision_rows:
        metadata = _loads_json(row["generation_metadata"], {})
        snapshot = metadata.get("creative_brief_snapshot") if isinstance(metadata, dict) else None
        snapshot_presence = _presence_from_mapping(snapshot if isinstance(snapshot, dict) else {})
        if not row["creative_brief_id"] or not all(snapshot_presence.values()):
            missing_revision_metadata.setdefault(int(row["chapter_number"]), []).append(
                row["version_id"]
            )

    result: list[GuardrailPersistenceAuditRow] = []
    for chapter in range(start, end + 1):
        brief_row = brief_rows.get(chapter)
        accepted_row = accepted_rows.get(chapter)
        brief_data = {
            field: _loads_json(brief_row[field], [] if field.endswith("replacements") else {})
            for field in GUARDRAIL_FIELDS
        } if brief_row else {}
        brief_presence = _presence_from_mapping(brief_data)

        accepted_metadata = (
            _loads_json(accepted_row["accepted_generation_metadata"], {})
            if accepted_row
            else {}
        )
        accepted_snapshot = (
            accepted_metadata.get("creative_brief_snapshot")
            if isinstance(accepted_metadata, dict)
            else None
        )
        accepted_snapshot_presence = _presence_from_mapping(
            accepted_snapshot if isinstance(accepted_snapshot, dict) else {}
        )
        accepted_replayable = bool(
            accepted_row
            and accepted_row["accepted_version_id"]
            and (
                all(accepted_snapshot_presence.values())
                or (
                    accepted_row["accepted_creative_brief_id"]
                    and all(brief_presence.values())
                )
            )
        )

        result.append(
            GuardrailPersistenceAuditRow(
                chapter_number=chapter,
                brief_id=brief_row["brief_id"] if brief_row else None,
                accepted_version_id=(
                    accepted_row["accepted_version_id"] if accepted_row else None
                ),
                accepted_creative_brief_id=(
                    accepted_row["accepted_creative_brief_id"] if accepted_row else None
                ),
                brief_fields_present=brief_presence,
                accepted_snapshot_fields_present=accepted_snapshot_presence,
                accepted_replayable=accepted_replayable,
                revision_versions_missing_guardrail_metadata=missing_revision_metadata.get(
                    chapter, []
                ),
            )
        )
    return result


def render_guardrail_persistence_section(
    rows: list[GuardrailPersistenceAuditRow],
) -> str:
    """Render a compact markdown section for 171v guardrail persistence."""
    lines = ["## 171v 护栏持久化审计", ""]
    if not rows:
        lines.append("（无审计数据）")
        return "\n".join(lines)

    brief_failures = [row.chapter_number for row in rows if not row.brief_complete]
    replay_failures = [row.chapter_number for row in rows if not row.accepted_replayable]
    revision_failures = [
        row.chapter_number for row in rows if not row.revision_metadata_complete
    ]

    lines.append(
        f"- brief 字段完整：{len(rows) - len(brief_failures)}/{len(rows)}；"
        f"accepted 可回放：{len(rows) - len(replay_failures)}/{len(rows)}；"
        f"revision metadata 完整：{len(rows) - len(revision_failures)}/{len(rows)}。"
    )
    lines.append("")
    lines.append("| 章 | brief | brief字段 | accepted回放 | revision缺口 |")
    lines.append("|----|-------|-----------|--------------|--------------|")
    for row in rows:
        missing_fields = [
            field for field, present in row.brief_fields_present.items() if not present
        ]
        lines.append(
            f"| {row.chapter_number} | {row.brief_id or '-'} | "
            f"{'OK' if not missing_fields else ','.join(missing_fields)} | "
            f"{'OK' if row.accepted_replayable else 'MISSING'} | "
            f"{row.revision_versions_missing_guardrail_metadata or '-'} |"
        )

    if brief_failures:
        lines.append(f"- brief 字段缺口章：{brief_failures}")
    if replay_failures:
        lines.append(f"- accepted 回放缺口章：{replay_failures}")
    if revision_failures:
        lines.append(f"- revision metadata 缺口章：{revision_failures}")
    return "\n".join(lines)
