"""Load a plan-fact fixture JSON into the ADR-0001 tables.

The loader upserts rows through ``PlanFactRepository``. It does not read
or write settlement tables, and it does not run checkers.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

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

XIAFEI_PROJECT_ID = "xiafei-jiuan"


class PlanFactBundle(BaseModel):
    """One project's plan cards, as stored in a fixture file."""

    project_id: str
    project: ProjectSetting
    entities: list[PlanEntity] = Field(default_factory=list)
    time_anchors: list[PlanTimeAnchor] = Field(default_factory=list)
    attributes: list[PlanAttribute] = Field(default_factory=list)
    events: list[PlanEvent] = Field(default_factory=list)
    clues: list[PlanClue] = Field(default_factory=list)


def bundled_xiafei_fixture() -> Path:
    """Path to the approved 霞飞路《旧案》 ch1–3 cards shipped with the package."""
    return Path(__file__).resolve().parents[1] / "plan_facts" / "xiafei_jiuan.json"


def read_plan_fact_fixture(path: Path) -> PlanFactBundle:
    """Parse a fixture file. Does not touch the database."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    bundle = PlanFactBundle.model_validate(payload)
    _require_consistent_ids(bundle)
    return bundle


async def load_plan_fact_fixture(path: Path) -> PlanFactBundle:
    """Upsert the fixture into the current database and return the bundle.

    Creates the project row when ``project_id`` is new. A second load
    updates the cards and leaves an existing project row in place.
    """
    from songyan.db.connection import get_db

    bundle = read_plan_fact_fixture(path)
    repo = PlanFactRepository()
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT project_id FROM projects WHERE project_id = ?",
            (bundle.project_id,),
        )
        if await cursor.fetchone() is None:
            await ProjectRepository().create(bundle.project, bundle.project_id, conn=conn)
        for anchor in bundle.time_anchors:
            await repo.write_time_anchor(anchor, conn=conn)
        for entity in bundle.entities:
            await repo.write_entity(entity, conn=conn)
        for attribute in bundle.attributes:
            await repo.write_attribute(attribute, conn=conn)
        for event in bundle.events:
            await repo.write_event(event, conn=conn)
        for clue in bundle.clues:
            await repo.write_clue(clue, conn=conn)
        await conn.commit()
    return bundle


def _require_consistent_ids(bundle: PlanFactBundle) -> None:
    if not bundle.project_id.strip():
        raise PlanFactError("project_id is empty")
    _unique([row.entity_id for row in bundle.entities], "entity_id")
    _unique([row.anchor_id for row in bundle.time_anchors], "anchor_id")
    _unique([row.attribute_id for row in bundle.attributes], "attribute_id")
    _unique([row.event_id for row in bundle.events], "event_id")
    _unique([row.clue_id for row in bundle.clues], "clue_id")
    rows: list[PlanEntity | PlanAttribute | PlanTimeAnchor | PlanEvent | PlanClue] = [
        *bundle.entities,
        *bundle.time_anchors,
        *bundle.attributes,
        *bundle.events,
        *bundle.clues,
    ]
    for row in rows:
        if row.project_id != bundle.project_id:
            raise PlanFactError(
                f"{row.project_id} does not match fixture project {bundle.project_id}"
            )


def _unique(ids: list[str], label: str) -> None:
    if len(ids) != len(set(ids)):
        raise PlanFactError(f"duplicate {label}")
