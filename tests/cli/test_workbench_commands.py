"""M0 step 1: read-only ``canon show`` for approved and pending plan facts."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.plan_fact_loader import (
    DUSHI_LINGYI_PROJECT_ID,
    bundled_dushi_lingyi_fixture,
    load_plan_fact_fixture,
)
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline
from songyan.models.plan_facts import PlanEntity
from songyan.plan_checks.bible import load_chapter_plan_bible

_PENDING_ID = "dly-pending-not-canon"
_CONFLICT = "只属于故事线的冲突句甲"
_ARC_ID = "dly-arc-storyline-only"
_THREAD_ID = "dly-thread-storyline-only"
_APPROVED = {
    "entity": "dly-shen",
    "attribute": "dly-attr-notch-direction",
    "event": "dly-evt-ch1-intake",
    "time_anchor": "dly-ta-day",
    "clue": "dly-clue-notch",
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def dushi_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """都市灵异夹具，外加一条测试自己写入的 pending 实体."""
    db_path = tmp_path / "workbench.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
    await PlanFactRepository().write_entity(
        PlanEntity(
            entity_id=_PENDING_ID,
            project_id=DUSHI_LINGYI_PROJECT_ID,
            entity_type="prop",
            approval_status="pending",
        )
    )
    return db_path


@pytest.fixture
async def dushi_with_storyline(dushi_db: Path) -> Path:
    """测试夹具写入大纲、弧和线索。命令本身不得写这些表."""
    repo = NarrativeRepository()
    await repo.upsert_outline(
        StoryOutline(project_id=DUSHI_LINGYI_PROJECT_ID, core_conflict=_CONFLICT)
    )
    await repo.add_arc_plan(
        ArcPlan(
            arc_id=_ARC_ID,
            project_id=DUSHI_LINGYI_PROJECT_ID,
            arc_index=0,
            start_chapter=1,
            end_chapter=3,
            arc_goal="弧目标不进Canon",
        )
    )
    await repo.add_thread(
        PlotThread(
            thread_id=_THREAD_ID,
            project_id=DUSHI_LINGYI_PROJECT_ID,
            title="线索标题不进Canon",
            status="opened",
        )
    )
    return dushi_db


def _between(text: str, start: str, end: str | None) -> str:
    begin = text.index(start) + len(start)
    if end is None:
        return text[begin:]
    return text[begin : text.index(end, begin)]


async def _storyline_counts() -> tuple[int, int, int]:
    async with get_db() as conn:
        counts: list[int] = []
        for table in ("story_outlines", "arc_plans", "plot_threads"):
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            counts.append(int(row[0]))
    return counts[0], counts[1], counts[2]


async def _entity_count() -> int:
    async with get_db() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM plan_entities")
        row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


def test_canon_show_splits_approved_and_pending(
    runner: CliRunner, dushi_db: Path
) -> None:
    before = asyncio.run(_entity_count())
    result = runner.invoke(
        cli,
        ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID],
    )
    after = asyncio.run(_entity_count())

    assert result.exit_code == 0, result.output
    canon = _between(result.output, "# Canon（approved）", "# Pending（不是 Canon）")
    pending = _between(
        result.output,
        "# Pending（不是 Canon）",
        "# Storyline（规划骨架，不是已确认事实）",
    )
    storyline = _between(result.output, "# Storyline（规划骨架，不是已确认事实）", None)

    for kind, card_id in _APPROVED.items():
        assert f"## {kind}" in canon
        assert card_id in canon
        assert card_id not in pending
    assert _PENDING_ID not in canon
    assert _PENDING_ID in pending
    assert "approval_status=pending" in pending
    assert "approval_status=pending" not in canon
    assert storyline.strip() == "（空）"
    assert after == before

    bible = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert "dly-shen" in bible.entity_ids
    assert _PENDING_ID not in bible.entity_ids
    assert _PENDING_ID not in bible.text


def test_canon_show_storyline_is_not_canon(
    runner: CliRunner, dushi_with_storyline: Path
) -> None:
    before = asyncio.run(_storyline_counts())
    result = runner.invoke(
        cli,
        ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID],
    )
    after = asyncio.run(_storyline_counts())

    assert result.exit_code == 0, result.output
    canon = _between(result.output, "# Canon（approved）", "# Pending（不是 Canon）")
    storyline = _between(result.output, "# Storyline（规划骨架，不是已确认事实）", None)
    assert _CONFLICT in storyline
    assert "arcs: 1" in storyline
    assert "opened=1" in storyline
    assert "approval_status" not in storyline
    assert _CONFLICT not in canon
    assert "dly-shen" in canon
    assert after == before


def test_canon_show_json_storyline_empty(runner: CliRunner, dushi_db: Path) -> None:
    result = runner.invoke(
        cli,
        ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID, "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert set(payload) == {"project_id", "canon", "pending", "storyline"}
    assert payload["storyline"] == {"outline": None, "arcs": [], "threads": []}


def test_canon_show_json_storyline_filled(
    runner: CliRunner, dushi_with_storyline: Path
) -> None:
    result = runner.invoke(
        cli,
        ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID, "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["storyline"]["outline"]["core_conflict"] == _CONFLICT
    assert payload["storyline"]["arcs"][0]["arc_id"] == _ARC_ID
    assert payload["storyline"]["threads"][0]["thread_id"] == _THREAD_ID
    assert payload["storyline"]["threads"][0]["status"] == "opened"
    assert _CONFLICT not in json.dumps(payload["canon"], ensure_ascii=False)
