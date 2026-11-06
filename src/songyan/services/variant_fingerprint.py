"""parent_canon_fingerprint — stable hash of chapter-visible approved Canon (tech-m3 B2).

Input set matches ``load_chapter_plan_bible`` visibility: approved plan cards only
(attributes with source plan|human|extract). Pending / rejected / body / storyline
are excluded.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClue,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)


def parent_canon_fingerprint(
    *,
    entities: list[PlanEntity],
    attributes: list[PlanAttribute],
    events: list[PlanEvent],
    clues: list[PlanClue],
    time_anchors: list[PlanTimeAnchor],
) -> str:
    """Return sha256 hex of a canonical JSON snapshot of the given cards.

    Callers must pass the bible-visible approved set (same selection as
    ``load_chapter_plan_bible``). List order does not affect the digest.
    """
    payload = {
        "attributes": [
            _attribute_dict(row)
            for row in sorted(attributes, key=lambda r: r.attribute_id)
        ],
        "clues": [_clue_dict(row) for row in sorted(clues, key=lambda r: r.clue_id)],
        "entities": [
            _entity_dict(row) for row in sorted(entities, key=lambda r: r.entity_id)
        ],
        "events": [_event_dict(row) for row in sorted(events, key=lambda r: r.event_id)],
        "time_anchors": [
            _anchor_dict(row) for row in sorted(time_anchors, key=lambda r: r.anchor_id)
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _entity_dict(row: PlanEntity) -> dict[str, Any]:
    return {
        "aliases": sorted(alias for alias in row.aliases if alias.strip()),
        "entity_id": row.entity_id,
        "entity_type": row.entity_type,
    }


def _attribute_dict(row: PlanAttribute) -> dict[str, Any]:
    return {
        "attribute_id": row.attribute_id,
        "entity_id": row.entity_id,
        "key": row.key,
        "source": row.source,
        "valid_from_ch": row.valid_from_ch,
        "valid_to_ch": row.valid_to_ch,
        "value": row.value,
    }


def _event_dict(row: PlanEvent) -> dict[str, Any]:
    return {
        "causes": sorted(row.causes),
        "ch": row.ch,
        "claims": [
            {"claim_id": claim.claim_id, "text": claim.text}
            for claim in sorted(row.claims, key=lambda c: c.claim_id)
        ],
        "event_id": row.event_id,
        "participants": sorted(row.participants),
        "reveals_evidence": sorted(row.reveals_evidence),
        "time_anchor_id": row.time_anchor_id,
    }


def _clue_dict(row: PlanClue) -> dict[str, Any]:
    return {
        "clue_id": row.clue_id,
        "label": row.label,
        "mention_terms": sorted(row.mention_terms),
        "must_mention_in": sorted(row.must_mention_in),
        "planted_ch": row.planted_ch,
        "revealed_ch": row.revealed_ch,
    }


def _anchor_dict(row: PlanTimeAnchor) -> dict[str, Any]:
    return {
        "anchor_id": row.anchor_id,
        "date": row.date,
        "kind": row.kind,
    }


async def fingerprint_chapter_parent_canon(project_id: str, chapter: int) -> str:
    """Load bible-visible approved Canon and return ``parent_canon_fingerprint``."""
    from songyan.db.plan_fact_repo import PlanFactRepository
    from songyan.plan_checks.bible import select_chapter_plan_bible_cards

    repo = PlanFactRepository()
    cards = select_chapter_plan_bible_cards(
        project_id=project_id,
        chapter=chapter,
        entities=await repo.list_canon_entities(project_id),
        attributes=await repo.list_canon_attributes(project_id),
        events=await repo.list_canon_events(project_id),
        clues=await repo.list_canon_clues(project_id),
        time_anchors=await repo.list_canon_time_anchors(project_id),
    )
    return parent_canon_fingerprint(
        entities=cards.entities,
        attributes=cards.attributes,
        events=cards.events,
        clues=cards.clues,
        time_anchors=cards.time_anchors,
    )

