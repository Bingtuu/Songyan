"""Approved 霞飞路《旧案》 cards round-trip through the plan-fact tables.

No live LLM. The loader does not write settlement rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.connection import get_db
from songyan.db.plan_fact_loader import (
    XIAFEI_PROJECT_ID,
    bundled_xiafei_fixture,
    load_plan_fact_fixture,
    read_plan_fact_fixture,
)
from songyan.db.plan_fact_repo import PlanFactError, PlanFactRepository


@pytest.fixture
async def fact_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary schema."""
    import songyan.db.connection as conn_mod
    from songyan.db.migrations import init_schema

    db_path = tmp_path / "xiafei.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


class TestXiafeiPlanFactSeed:
    async def test_approved_cards_round_trip(self, fact_db: Path) -> None:
        bundle = await load_plan_fact_fixture(bundled_xiafei_fixture())
        repo = PlanFactRepository()

        assert bundle.project_id == XIAFEI_PROJECT_ID
        entities = await repo.list_canon_entities(XIAFEI_PROJECT_ID)
        attributes = await repo.list_canon_attributes(XIAFEI_PROJECT_ID)
        events = await repo.list_canon_events(XIAFEI_PROJECT_ID)
        anchors = await repo.list_canon_time_anchors(XIAFEI_PROJECT_ID)
        clues = await repo.list_canon_clues(XIAFEI_PROJECT_ID)

        assert [row.entity_id for row in entities] == sorted(
            row.entity_id for row in bundle.entities
        )
        assert [row.attribute_id for row in attributes] == sorted(
            row.attribute_id for row in bundle.attributes
        )
        assert [row.event_id for row in events] == sorted(
            row.event_id for row in bundle.events
        )
        assert [row.anchor_id for row in anchors] == sorted(
            row.anchor_id for row in bundle.time_anchors
        )
        assert [row.clue_id for row in clues] == sorted(row.clue_id for row in bundle.clues)
        assert entities == sorted(bundle.entities, key=lambda row: row.entity_id)
        assert attributes == sorted(bundle.attributes, key=lambda row: row.attribute_id)
        assert events == sorted(bundle.events, key=lambda row: row.event_id)
        assert anchors == sorted(bundle.time_anchors, key=lambda row: row.anchor_id)
        assert clues == sorted(bundle.clues, key=lambda row: row.clue_id)

    async def test_cards_are_approved_and_sourced(self, fact_db: Path) -> None:
        bundle = read_plan_fact_fixture(bundled_xiafei_fixture())
        await load_plan_fact_fixture(bundled_xiafei_fixture())
        repo = PlanFactRepository()

        assert all(row.approval_status == "approved" for row in bundle.entities)
        assert all(row.approval_status == "approved" for row in bundle.events)
        assert all(row.approval_status == "approved" for row in bundle.clues)
        sources = {row.attribute_id: row.source for row in bundle.attributes}
        assert sources["attr-era-window"] == "plan"
        assert sources["attr-scratch-direction"] == "human"
        assert sources["attr-mechanism-direction"] == "human"
        assert sources["attr-case-time"] == "human"
        assert await repo.list_pending_entities(XIAFEI_PROJECT_ID) == []
        assert await repo.list_pending_attributes(XIAFEI_PROJECT_ID) == []
        assert await repo.list_pending_events(XIAFEI_PROJECT_ID) == []
        assert await repo.list_pending_clues(XIAFEI_PROJECT_ID) == []

    async def test_second_load_is_idempotent(self, fact_db: Path) -> None:
        await load_plan_fact_fixture(bundled_xiafei_fixture())
        await load_plan_fact_fixture(bundled_xiafei_fixture())
        repo = PlanFactRepository()

        events = await repo.list_canon_events(XIAFEI_PROJECT_ID)
        claim_ids = [claim.claim_id for event in events for claim in event.claims]
        assert "claim-ch1-scratch" in claim_ids
        assert len(claim_ids) == len(set(claim_ids))
        clues = await repo.list_canon_clues(XIAFEI_PROJECT_ID)
        blunt = next(row for row in clues if row.clue_id == "clue-blunt")
        assert blunt.mention_terms == ["钝器伤"]
        assert blunt.must_mention_in == [1, 2]

    async def test_loader_does_not_write_settlement_tables(self, fact_db: Path) -> None:
        async with get_db() as conn:
            before = await conn.execute("SELECT COUNT(*) FROM setting_snapshots")
            before_count = (await before.fetchone())[0]

        await load_plan_fact_fixture(bundled_xiafei_fixture())

        async with get_db() as conn:
            after = await conn.execute("SELECT COUNT(*) FROM setting_snapshots")
            after_count = (await after.fetchone())[0]

        assert before_count == 0
        assert after_count == 0

    def test_fixture_rejects_a_foreign_project_id(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(
            """
            {
              "project_id": "xiafei-jiuan",
              "project": {
                "genre_id": "urban",
                "protagonist_name": "顾怀瑾"
              },
              "entities": [
                {
                  "entity_id": "ent-other",
                  "project_id": "other",
                  "entity_type": "person",
                  "aliases": []
                }
              ]
            }
            """,
            encoding="utf-8",
        )

        with pytest.raises(PlanFactError):
            read_plan_fact_fixture(path)
