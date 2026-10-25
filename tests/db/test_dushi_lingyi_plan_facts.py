"""Approved 都市灵异《末班铜牌》 cards round-trip through the plan-fact tables.

No live LLM. The loader does not write settlement rows. Same path as
``xiafei-jiuan``: bundled JSON, ``load_plan_fact_fixture``, canon reads.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.connection import get_db
from songyan.db.plan_fact_loader import (
    DUSHI_LINGYI_PROJECT_ID,
    bundled_dushi_lingyi_fixture,
    load_plan_fact_fixture,
    read_plan_fact_fixture,
)
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ProjectRepository


@pytest.fixture
async def fact_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary schema."""
    import songyan.db.connection as conn_mod
    from songyan.db.migrations import init_schema

    db_path = tmp_path / "dushi_lingyi.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


class TestDushiLingyiPlanFactSeed:
    async def test_approved_cards_round_trip(self, fact_db: Path) -> None:
        bundle = await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
        repo = PlanFactRepository()

        assert bundle.project_id == DUSHI_LINGYI_PROJECT_ID
        assert bundle.project.title == "末班铜牌"
        assert "都市灵异" in bundle.project.core_hook
        entities = await repo.list_canon_entities(DUSHI_LINGYI_PROJECT_ID)
        attributes = await repo.list_canon_attributes(DUSHI_LINGYI_PROJECT_ID)
        events = await repo.list_canon_events(DUSHI_LINGYI_PROJECT_ID)
        anchors = await repo.list_canon_time_anchors(DUSHI_LINGYI_PROJECT_ID)
        clues = await repo.list_canon_clues(DUSHI_LINGYI_PROJECT_ID)

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
        assert {row.ch for row in events} == {1, 2, 3}

    async def test_cards_are_approved_and_sourced(self, fact_db: Path) -> None:
        bundle = read_plan_fact_fixture(bundled_dushi_lingyi_fixture())
        await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
        repo = PlanFactRepository()

        assert all(row.approval_status == "approved" for row in bundle.entities)
        assert all(row.approval_status == "approved" for row in bundle.time_anchors)
        assert all(row.approval_status == "approved" for row in bundle.attributes)
        assert all(row.approval_status == "approved" for row in bundle.events)
        assert all(row.approval_status == "approved" for row in bundle.clues)
        sources = {row.attribute_id: row.source for row in bundle.attributes}
        assert sources["dly-attr-window-time"] == "plan"
        assert sources["dly-attr-notch-direction"] == "human"
        assert sources["dly-attr-notch-count"] == "human"
        assert sources["dly-attr-mark-owner"] == "human"
        assert sources["dly-attr-mark-site"] == "human"
        assert sources["dly-attr-return-direction"] == "human"
        assert sources["dly-attr-day-time"] == "human"
        assert await repo.list_pending_entities(DUSHI_LINGYI_PROJECT_ID) == []
        assert await repo.list_pending_attributes(DUSHI_LINGYI_PROJECT_ID) == []
        assert await repo.list_pending_events(DUSHI_LINGYI_PROJECT_ID) == []
        assert await repo.list_pending_clues(DUSHI_LINGYI_PROJECT_ID) == []
        assert await repo.list_pending_time_anchors(DUSHI_LINGYI_PROJECT_ID) == []

        canon = {row.attribute_id: row.value for row in await repo.list_canon_attributes(
            DUSHI_LINGYI_PROJECT_ID
        )}
        assert canon["dly-attr-notch-direction"] == "东向西"
        assert canon["dly-attr-notch-count"] == "1"
        assert canon["dly-attr-mark-owner"] == "周晚宁"
        assert canon["dly-attr-mark-site"] == "铜牌正面"
        assert canon["dly-attr-return-direction"] == "面朝东"
        assert canon["dly-attr-window-time"] == "23:40-00:10"
        assert canon["dly-attr-day-time"] == "2024-11-02"

    async def test_second_load_is_idempotent(self, fact_db: Path) -> None:
        await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
        await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
        repo = PlanFactRepository()

        events = await repo.list_canon_events(DUSHI_LINGYI_PROJECT_ID)
        claim_ids = [claim.claim_id for event in events for claim in event.claims]
        assert "dly-claim-ch1-notch" in claim_ids
        assert len(claim_ids) == len(set(claim_ids))
        clues = await repo.list_canon_clues(DUSHI_LINGYI_PROJECT_ID)
        notch = next(row for row in clues if row.clue_id == "dly-clue-notch")
        assert notch.mention_terms == ["东向西"]
        assert notch.must_mention_in == [1, 2]

    async def test_loader_does_not_write_settlement_tables(self, fact_db: Path) -> None:
        async with get_db() as conn:
            before = await conn.execute("SELECT COUNT(*) FROM setting_snapshots")
            before_count = (await before.fetchone())[0]

        await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())

        async with get_db() as conn:
            after = await conn.execute("SELECT COUNT(*) FROM setting_snapshots")
            after_count = (await after.fetchone())[0]

        assert before_count == 0
        assert after_count == 0

    async def test_retarget_puts_approved_cards_on_the_writing_project(
        self, fact_db: Path
    ) -> None:
        bundle = await load_plan_fact_fixture(
            bundled_dushi_lingyi_fixture(),
            project_id="runtime-dushi-lingyi",
        )
        repo = PlanFactRepository()

        assert bundle.project_id == "runtime-dushi-lingyi"
        assert [row.project_id for row in bundle.clues] == ["runtime-dushi-lingyi"] * len(
            bundle.clues
        )
        clues = await repo.list_canon_clues("runtime-dushi-lingyi")
        assert {row.clue_id for row in clues} == {row.clue_id for row in bundle.clues}
        assert await repo.list_canon_clues(DUSHI_LINGYI_PROJECT_ID) == []
        assert await repo.list_canon_attributes("runtime-dushi-lingyi")
        project = await ProjectRepository().get("runtime-dushi-lingyi")
        assert project is not None
        assert project.title == "末班铜牌"
