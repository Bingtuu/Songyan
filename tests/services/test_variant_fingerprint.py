"""M3 step 1: parent_canon_fingerprint stability (tech-m3 B2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ProjectRepository
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClaim,
    PlanClue,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)
from songyan.models.project import ProjectSetting
from songyan.plan_checks.bible import select_chapter_plan_bible_cards
from songyan.services.variant_fingerprint import (
    fingerprint_chapter_parent_canon,
    parent_canon_fingerprint,
)


def _cards() -> tuple[
    list[PlanEntity],
    list[PlanAttribute],
    list[PlanEvent],
    list[PlanClue],
    list[PlanTimeAnchor],
]:
    entities = [
        PlanEntity(
            entity_id="ent-b",
            project_id="p1",
            entity_type="person",
            aliases=["乙", "B"],
            approval_status="approved",
        ),
        PlanEntity(
            entity_id="ent-a",
            project_id="p1",
            entity_type="person",
            aliases=["甲"],
            approval_status="approved",
        ),
    ]
    anchors = [
        PlanTimeAnchor(
            anchor_id="ta-1",
            project_id="p1",
            date="第一天黄昏",
            kind="story",
            approval_status="approved",
        )
    ]
    events = [
        PlanEvent(
            event_id="evt-1",
            project_id="p1",
            ch=1,
            time_anchor_id="ta-1",
            participants=["ent-a", "ent-b"],
            causes=["ent-a"],
            reveals_evidence=[],
            claims=[PlanClaim(claim_id="c1", text="甲见到乙")],
            approval_status="approved",
        )
    ]
    attributes = [
        PlanAttribute(
            attribute_id="attr-1",
            project_id="p1",
            entity_id="ent-a",
            key="location",
            value="南站",
            source="plan",
            valid_from_ch=1,
            valid_to_ch=3,
            approval_status="approved",
        )
    ]
    clues = [
        PlanClue(
            clue_id="clue-1",
            project_id="p1",
            planted_ch=1,
            must_mention_in=[1],
            label="铜牌缺口",
            mention_terms=["缺口", "铜牌"],
            approval_status="approved",
        )
    ]
    return entities, attributes, events, clues, anchors


def test_fingerprint_stable_on_same_approved_set() -> None:
    entities, attributes, events, clues, anchors = _cards()
    a = parent_canon_fingerprint(
        entities=entities,
        attributes=attributes,
        events=events,
        clues=clues,
        time_anchors=anchors,
    )
    # Shuffle input order — digest must not change.
    b = parent_canon_fingerprint(
        entities=list(reversed(entities)),
        attributes=list(reversed(attributes)),
        events=list(reversed(events)),
        clues=list(reversed(clues)),
        time_anchors=list(reversed(anchors)),
    )
    assert a == b
    assert len(a) == 64
    assert all(ch in "0123456789abcdef" for ch in a)


def test_fingerprint_empty_set_is_stable() -> None:
    empty = parent_canon_fingerprint(
        entities=[],
        attributes=[],
        events=[],
        clues=[],
        time_anchors=[],
    )
    assert empty == parent_canon_fingerprint(
        entities=[],
        attributes=[],
        events=[],
        clues=[],
        time_anchors=[],
    )


def test_fingerprint_changes_when_approved_value_changes() -> None:
    entities, attributes, events, clues, anchors = _cards()
    base = parent_canon_fingerprint(
        entities=entities,
        attributes=attributes,
        events=events,
        clues=clues,
        time_anchors=anchors,
    )
    changed = [
        attributes[0].model_copy(update={"value": "北站"}),
    ]
    other = parent_canon_fingerprint(
        entities=entities,
        attributes=changed,
        events=events,
        clues=clues,
        time_anchors=anchors,
    )
    assert base != other


@pytest.fixture
async def fact_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "fp.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
        ),
        "p1",
    )
    entities, attributes, events, clues, anchors = _cards()
    repo = PlanFactRepository()
    for row in entities:
        await repo.write_entity(row)
    for row in anchors:
        await repo.write_time_anchor(row)
    for row in attributes:
        await repo.write_attribute(row)
    for row in events:
        await repo.write_event(row)
    for row in clues:
        await repo.write_clue(row)
    return db_path


@pytest.mark.asyncio
async def test_pending_does_not_change_fingerprint(fact_db: Path) -> None:
    before = await fingerprint_chapter_parent_canon("p1", 1)
    repo = PlanFactRepository()
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-pending",
            project_id="p1",
            entity_type="prop",
            aliases=["不该进指纹"],
            approval_status="pending",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-pending",
            project_id="p1",
            entity_id="ent-a",
            key="mood",
            value="pending-only",
            source="human",
            approval_status="pending",
        )
    )
    after = await fingerprint_chapter_parent_canon("p1", 1)
    assert before == after

    # Bible selection still sees only approved visible set.
    cards = select_chapter_plan_bible_cards(
        project_id="p1",
        chapter=1,
        entities=await repo.list_canon_entities("p1"),
        attributes=await repo.list_canon_attributes("p1"),
        events=await repo.list_canon_events("p1"),
        clues=await repo.list_canon_clues("p1"),
        time_anchors=await repo.list_canon_time_anchors("p1"),
    )
    assert "ent-pending" not in {e.entity_id for e in cards.entities}
    assert "attr-pending" not in {a.attribute_id for a in cards.attributes}
