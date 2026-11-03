"""M1 step 2: ``canon edit`` writes pending plan rows (entity + attribute)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_loader import (
    DUSHI_LINGYI_PROJECT_ID,
    bundled_dushi_lingyi_fixture,
    load_plan_fact_fixture,
)
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.plan_checks.bible import load_chapter_plan_bible

_EDIT_ENTITY_ID = "m1-edit-entity-knife"
_EDIT_ATTR_ID = "m1-edit-attr-edge"
_NOT_YET_CANON = "尚未入典"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def dushi_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "canon-edit.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
    return db_path


@pytest.fixture
async def empty_schema_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "empty-projects.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    return db_path


def _between(text: str, start: str, end: str | None) -> str:
    begin = text.index(start) + len(start)
    if end is None:
        return text[begin:]
    return text[begin : text.index(end, begin)]


def test_canon_edit_entity_writes_pending_visible_in_show_not_canon(
    runner: CliRunner, dushi_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            _EDIT_ENTITY_ID,
            "--type",
            "prop",
            "--alias",
            "试刀",
        ],
    )
    assert result.exit_code == 0, result.output
    assert _EDIT_ENTITY_ID in result.output
    assert _NOT_YET_CANON in result.output
    assert "pending" in result.output.lower() or "Pending" in result.output

    show = runner.invoke(
        cli, ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID]
    )
    assert show.exit_code == 0, show.output
    canon = _between(show.output, "# Canon（approved）", "# Pending（不是 Canon）")
    pending = _between(
        show.output,
        "# Pending（不是 Canon）",
        "# Storyline（规划骨架，不是已确认事实）",
    )
    assert _EDIT_ENTITY_ID not in canon
    assert _EDIT_ENTITY_ID in pending

    repo = PlanFactRepository()
    pending_ids = [
        row.entity_id
        for row in asyncio.run(repo.list_pending_entities(DUSHI_LINGYI_PROJECT_ID))
    ]
    canon_ids = [
        row.entity_id
        for row in asyncio.run(repo.list_canon_entities(DUSHI_LINGYI_PROJECT_ID))
    ]
    assert _EDIT_ENTITY_ID in pending_ids
    assert _EDIT_ENTITY_ID not in canon_ids

    bible = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert _EDIT_ENTITY_ID not in bible.entity_ids
    assert _EDIT_ENTITY_ID not in bible.text


def test_canon_edit_attribute_forces_human_source_pending_not_bible(
    runner: CliRunner, dushi_db: Path
) -> None:
    ent = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            _EDIT_ENTITY_ID,
            "--type",
            "prop",
        ],
    )
    assert ent.exit_code == 0, ent.output

    result = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _EDIT_ATTR_ID,
            "--entity-id",
            _EDIT_ENTITY_ID,
            "--key",
            "edge",
            "--value",
            "双面开刃",
            "--valid-from-ch",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert _EDIT_ATTR_ID in result.output
    assert _NOT_YET_CANON in result.output
    assert "human" in result.output

    row = asyncio.run(PlanFactRepository().read_attribute(_EDIT_ATTR_ID))
    assert row is not None
    assert row.approval_status == "pending"
    assert row.source == "human"
    assert row.key == "edge"
    assert row.value == "双面开刃"
    assert row.valid_from_ch == 1

    pending_ids = [
        a.attribute_id
        for a in asyncio.run(
            PlanFactRepository().list_pending_attributes(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    canon_ids = [
        a.attribute_id
        for a in asyncio.run(
            PlanFactRepository().list_canon_attributes(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    assert _EDIT_ATTR_ID in pending_ids
    assert _EDIT_ATTR_ID not in canon_ids

    show = runner.invoke(
        cli, ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID, "--json"]
    )
    assert show.exit_code == 0, show.output
    payload = json.loads(show.output)
    pending_attr_ids = [a["attribute_id"] for a in payload["pending"]["attributes"]]
    canon_attr_ids = [a["attribute_id"] for a in payload["canon"]["attributes"]]
    assert _EDIT_ATTR_ID in pending_attr_ids
    assert _EDIT_ATTR_ID not in canon_attr_ids

    bible = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert _EDIT_ATTR_ID not in bible.text
    assert "双面开刃" not in bible.text


def test_canon_edit_attribute_missing_entity_exits_1(
    runner: CliRunner, dushi_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            "orphan-attr",
            "--entity-id",
            "no-such-entity",
            "--key",
            "x",
            "--value",
            "y",
        ],
    )
    assert result.exit_code == 1, result.output


def test_canon_edit_missing_db_exits_1_without_creating_file(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "no-edit.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{missing}")
    assert not missing.exists()

    result = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "entity",
            "--project-id",
            "any-id",
            "--entity-id",
            "e1",
            "--type",
            "prop",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "找不到数据库" in result.output
    assert not missing.exists()


def test_canon_edit_missing_project_exits_1(
    runner: CliRunner, empty_schema_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "entity",
            "--project-id",
            "no-such-project",
            "--entity-id",
            "e1",
            "--type",
            "prop",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "项目不存在" in result.output


def test_canon_edit_overwrite_forces_pending(
    runner: CliRunner, dushi_db: Path
) -> None:
    """edit always lands pending even when overwriting an approved id."""
    first = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            "dly-shen",
            "--type",
            "character",
            "--alias",
            "沈改稿",
        ],
    )
    assert first.exit_code == 0, first.output
    row = asyncio.run(PlanFactRepository().read_entity("dly-shen"))
    assert row is not None
    assert row.approval_status == "pending"
    assert "沈改稿" in row.aliases
    canon_ids = [
        e.entity_id
        for e in asyncio.run(
            PlanFactRepository().list_canon_entities(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    assert "dly-shen" not in canon_ids
