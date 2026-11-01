"""M0 step 1: read-only ``canon show`` for approved and pending plan facts."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_loader import (
    DUSHI_LINGYI_PROJECT_ID,
    bundled_dushi_lingyi_fixture,
    load_plan_fact_fixture,
)
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.models.plan_facts import PlanEntity
from songyan.plan_checks.bible import load_chapter_plan_bible

_PENDING_ID = "dly-pending-not-canon"
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


def _between(text: str, start: str, end: str | None) -> str:
    begin = text.index(start) + len(start)
    if end is None:
        return text[begin:]
    return text[begin : text.index(end, begin)]


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
