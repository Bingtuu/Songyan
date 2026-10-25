"""Phase B fact-card schema — create/read/write round-trip and canon vs pending.

No live LLM. These tests lock ADR-0001's minimal records. They do not
exercise SettlementExtractor or the generation graph.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from songyan.db.connection import get_db
from songyan.db.migrations import _EXPECTED_TABLES, init_schema, run_migrations, verify_schema
from songyan.db.plan_fact_repo import PlanFactError, PlanFactRepository
from songyan.db.repository import ProjectRepository
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClue,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)
from songyan.models.project import ProjectSetting

_PLAN_TABLES = (
    "plan_entities",
    "plan_attributes",
    "plan_events",
    "plan_time_anchors",
    "plan_clues",
)


@pytest.fixture
async def fact_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary schema and seed one project."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "facts.db"
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
    return db_path


def _knife() -> PlanEntity:
    return PlanEntity(
        entity_id="ent-knife",
        project_id="p1",
        entity_type="object",
        aliases=["银刀", "那把刀"],
    )


def _direction(*, approval_status: str = "approved", source: str = "plan") -> PlanAttribute:
    return PlanAttribute.model_validate(
        {
            "attribute_id": "attr-direction",
            "project_id": "p1",
            "entity_id": "ent-knife",
            "key": "direction",
            "value": "东",
            "valid_from_ch": 1,
            "valid_to_ch": 3,
            "source": source,
            "approval_status": approval_status,
        }
    )


class TestPlanFactModels:
    def test_attribute_source_must_be_plan_or_human(self) -> None:
        with pytest.raises(ValidationError):
            PlanAttribute.model_validate(
                {
                    "attribute_id": "attr-bad",
                    "project_id": "p1",
                    "entity_id": "ent-knife",
                    "key": "direction",
                    "value": "东",
                    "source": "extracted",
                }
            )

    def test_attribute_rejects_inverted_validity_window(self) -> None:
        with pytest.raises(ValidationError):
            PlanAttribute(
                attribute_id="attr-bad",
                project_id="p1",
                entity_id="ent-knife",
                key="direction",
                value="东",
                valid_from_ch=5,
                valid_to_ch=2,
                source="human",
            )

    def test_time_anchor_kind_is_story_or_history(self) -> None:
        with pytest.raises(ValidationError):
            PlanTimeAnchor.model_validate(
                {
                    "anchor_id": "ta-bad",
                    "project_id": "p1",
                    "date": "1937-08",
                    "kind": "calendar",
                }
            )

    def test_clue_rejects_reveal_before_plant(self) -> None:
        with pytest.raises(ValidationError):
            PlanClue(
                clue_id="clue-bad",
                project_id="p1",
                planted_ch=4,
                revealed_ch=2,
                must_mention_in=[4],
            )


class TestPlanFactRoundTrip:
    async def test_entity_write_read_round_trip(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        entity = _knife()

        await repo.write_entity(entity)
        loaded = await repo.read_entity(entity.entity_id)

        assert loaded == entity

    async def test_attribute_write_read_round_trip(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        await repo.write_entity(_knife())
        attribute = _direction(source="human")

        await repo.write_attribute(attribute)
        loaded = await repo.read_attribute(attribute.attribute_id)

        assert loaded == attribute
        assert loaded is not None
        assert loaded.source == "human"
        assert loaded.valid_from_ch == 1
        assert loaded.valid_to_ch == 3

    async def test_time_anchor_and_event_round_trip(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        await repo.write_entity(_knife())
        anchor = PlanTimeAnchor(
            anchor_id="ta-1931",
            project_id="p1",
            date="1931-09-18",
            kind="history",
        )
        event = PlanEvent(
            event_id="evt-find-knife",
            project_id="p1",
            ch=2,
            time_anchor_id=anchor.anchor_id,
            participants=["ent-knife"],
            causes=["evt-earlier"],
            reveals_evidence=["clue-blade"],
        )

        await repo.write_time_anchor(anchor)
        await repo.write_event(event)

        assert await repo.read_time_anchor(anchor.anchor_id) == anchor
        assert await repo.read_event(event.event_id) == event

    async def test_clue_round_trip(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        clue = PlanClue(
            clue_id="clue-blade",
            project_id="p1",
            planted_ch=1,
            revealed_ch=3,
            must_mention_in=[1, 3],
        )

        await repo.write_clue(clue)

        assert await repo.read_clue(clue.clue_id) == clue

    async def test_write_updates_existing_row(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        await repo.write_entity(_knife())
        revised = _knife().model_copy(update={"aliases": ["银刀", "那把刀", "证物甲"]})

        await repo.write_entity(revised)

        assert await repo.read_entity("ent-knife") == revised

    async def test_read_missing_returns_none(self, fact_db: Path) -> None:
        repo = PlanFactRepository()

        assert await repo.read_entity("missing") is None
        assert await repo.read_attribute("missing") is None
        assert await repo.read_event("missing") is None
        assert await repo.read_time_anchor("missing") is None
        assert await repo.read_clue("missing") is None


class TestCanonVersusPending:
    async def test_pending_attribute_is_not_plan_or_human_canon(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        await repo.write_entity(_knife())
        pending = _direction(approval_status="pending", source="plan")
        approved = PlanAttribute(
            attribute_id="attr-owner",
            project_id="p1",
            entity_id="ent-knife",
            key="owner",
            value="陈照",
            valid_from_ch=1,
            source="human",
        )

        await repo.write_attribute(pending)
        await repo.write_attribute(approved)

        canon_ids = [row.attribute_id for row in await repo.list_canon_attributes("p1")]
        pending_ids = [row.attribute_id for row in await repo.list_pending_attributes("p1")]

        assert canon_ids == ["attr-owner"]
        assert pending_ids == ["attr-direction"]
        assert approved.source == "human"
        assert pending.source == "plan"

    async def test_approving_a_pending_row_moves_it_into_canon(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        await repo.write_entity(_knife())
        await repo.write_attribute(_direction(approval_status="pending"))

        assert await repo.list_canon_attributes("p1") == []

        await repo.write_attribute(_direction(approval_status="approved", source="human"))

        canon = await repo.list_canon_attributes("p1")
        assert [row.attribute_id for row in canon] == ["attr-direction"]
        assert canon[0].approval_status == "approved"
        assert canon[0].source == "human"
        assert await repo.list_pending_attributes("p1") == []

    async def test_pending_cards_of_each_type_stay_out_of_canon(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        await repo.write_entity(_knife().model_copy(update={"approval_status": "pending"}))
        await repo.write_time_anchor(
            PlanTimeAnchor(
                anchor_id="ta-story",
                project_id="p1",
                date="案发当夜",
                kind="story",
                approval_status="pending",
            )
        )
        await repo.write_event(
            PlanEvent(
                event_id="evt-pending",
                project_id="p1",
                ch=1,
                participants=["ent-knife"],
                approval_status="pending",
            )
        )
        await repo.write_clue(
            PlanClue(
                clue_id="clue-pending",
                project_id="p1",
                planted_ch=1,
                revealed_ch=2,
                must_mention_in=[2],
                approval_status="pending",
            )
        )

        assert await repo.list_canon_entities("p1") == []
        assert await repo.list_canon_time_anchors("p1") == []
        assert await repo.list_canon_events("p1") == []
        assert await repo.list_canon_clues("p1") == []
        assert [row.entity_id for row in await repo.list_pending_entities("p1")] == ["ent-knife"]
        assert [row.anchor_id for row in await repo.list_pending_time_anchors("p1")] == ["ta-story"]
        assert [row.event_id for row in await repo.list_pending_events("p1")] == ["evt-pending"]
        assert [row.clue_id for row in await repo.list_pending_clues("p1")] == ["clue-pending"]

    async def test_canon_lists_do_not_leak_across_projects(self, fact_db: Path) -> None:
        await ProjectRepository().create(
            ProjectSetting(
                genre_id="mystery",
                mode_id="webnovel",
                protagonist_name="别人",
            ),
            "p2",
        )
        repo = PlanFactRepository()
        await repo.write_entity(_knife())
        await repo.write_entity(
            PlanEntity(
                entity_id="ent-other",
                project_id="p2",
                entity_type="person",
                aliases=["别人"],
            )
        )

        assert [row.entity_id for row in await repo.list_canon_entities("p1")] == ["ent-knife"]
        assert [row.entity_id for row in await repo.list_canon_entities("p2")] == ["ent-other"]

    async def test_attribute_must_reference_entity_in_same_project(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        await repo.write_entity(_knife())

        with pytest.raises(PlanFactError):
            await repo.write_attribute(
                PlanAttribute(
                    attribute_id="attr-cross",
                    project_id="p2",
                    entity_id="ent-knife",
                    key="direction",
                    value="东",
                    source="plan",
                )
            )

    async def test_writing_pending_attribute_does_not_touch_settlement_tables(
        self, fact_db: Path
    ) -> None:
        repo = PlanFactRepository()
        await repo.write_entity(_knife())

        async with get_db() as conn:
            before = await conn.execute("SELECT COUNT(*) FROM setting_snapshots")
            before_count = (await before.fetchone())[0]

        await repo.write_attribute(_direction(approval_status="pending"))

        async with get_db() as conn:
            after = await conn.execute("SELECT COUNT(*) FROM setting_snapshots")
            after_count = (await after.fetchone())[0]

        assert before_count == 0
        assert after_count == 0
        assert await repo.list_canon_attributes("p1") == []


class TestPlanFactSchema:
    async def test_init_schema_creates_plan_fact_tables(self, fact_db: Path) -> None:
        import aiosqlite

        for table in _PLAN_TABLES:
            assert table in _EXPECTED_TABLES

        async with aiosqlite.connect(fact_db) as conn:
            assert await verify_schema(conn) == []
            columns = {}
            for table in _PLAN_TABLES:
                cursor = await conn.execute(f"PRAGMA table_info({table})")
                columns[table] = {row[1] for row in await cursor.fetchall()}

        assert {
            "entity_id",
            "entity_type",
            "aliases",
            "approval_status",
        } <= columns["plan_entities"]
        assert {
            "entity_id",
            "key",
            "value",
            "valid_from_ch",
            "valid_to_ch",
            "source",
            "approval_status",
        } <= columns["plan_attributes"]
        assert {
            "event_id",
            "ch",
            "time_anchor_id",
            "participants",
            "causes",
            "reveals_evidence",
            "approval_status",
        } <= columns["plan_events"]
        assert {"anchor_id", "date", "kind", "approval_status"} <= columns["plan_time_anchors"]
        assert {
            "clue_id",
            "planted_ch",
            "revealed_ch",
            "must_mention_in",
            "approval_status",
        } <= columns["plan_clues"]

    async def test_attribute_check_rejects_extracted_source(self, fact_db: Path) -> None:
        repo = PlanFactRepository()
        await repo.write_entity(_knife())

        with pytest.raises(sqlite3.IntegrityError):
            async with get_db() as conn:
                await conn.execute(
                    """INSERT INTO plan_attributes (
                        attribute_id, project_id, entity_id, key, value, source
                    ) VALUES (?, ?, ?, ?, ?, ?)""",
                    ("attr-extracted", "p1", "ent-knife", "direction", "东", "extracted"),
                )
                await conn.commit()

    async def test_run_migrations_recreates_dropped_plan_table(self, fact_db: Path) -> None:
        import aiosqlite

        async with aiosqlite.connect(fact_db) as conn:
            await conn.execute("DROP TABLE plan_clues")
            await conn.commit()
            assert "plan_clues" in await verify_schema(conn)

            await run_migrations(conn)
            await conn.commit()

            assert await verify_schema(conn) == []
