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


_CONFIRMED = "已入典"
_ACCEPT_REMIND = "confirm"


def _edit_entity(runner: CliRunner, entity_id: str = _EDIT_ENTITY_ID) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            entity_id,
            "--type",
            "prop",
            "--alias",
            "试刀",
        ],
    )
    assert result.exit_code == 0, result.output


def _edit_attribute(
    runner: CliRunner,
    *,
    attribute_id: str = _EDIT_ATTR_ID,
    entity_id: str = _EDIT_ENTITY_ID,
    value: str = "双面开刃",
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
            attribute_id,
            "--entity-id",
            entity_id,
            "--key",
            "edge",
            "--value",
            value,
            "--valid-from-ch",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output


def test_canon_confirm_entity_approves_and_enters_canon_bible(
    runner: CliRunner, dushi_db: Path
) -> None:
    # New id: confirm lands in list_canon_*; bible still follows chapter-window refs.
    _edit_entity(runner)
    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            _EDIT_ENTITY_ID,
        ],
    )
    assert result.exit_code == 0, result.output
    assert _EDIT_ENTITY_ID in result.output
    assert _CONFIRMED in result.output

    row = asyncio.run(PlanFactRepository().read_entity(_EDIT_ENTITY_ID))
    assert row is not None
    assert row.approval_status == "approved"

    canon_ids = [
        e.entity_id
        for e in asyncio.run(
            PlanFactRepository().list_canon_entities(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    pending_ids = [
        e.entity_id
        for e in asyncio.run(
            PlanFactRepository().list_pending_entities(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    assert _EDIT_ENTITY_ID in canon_ids
    assert _EDIT_ENTITY_ID not in pending_ids

    # In-window fixture entity: demote via edit, then confirm back into bible.
    demote = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            "dly-token",
            "--type",
            "object",
            "--alias",
            "铜牌",
        ],
    )
    assert demote.exit_code == 0, demote.output
    bible_pending = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert "dly-token" not in bible_pending.entity_ids

    restore = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            "dly-token",
        ],
    )
    assert restore.exit_code == 0, restore.output
    assert _CONFIRMED in restore.output
    bible = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert "dly-token" in bible.entity_ids


def test_canon_confirm_attribute_approves_list_canon_and_bible(
    runner: CliRunner, dushi_db: Path
) -> None:
    # Attribute on in-window entity dly-token so chapter-1 bible can include it.
    result_edit = runner.invoke(
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
            "dly-token",
            "--key",
            "edge",
            "--value",
            "双面开刃",
            "--valid-from-ch",
            "1",
        ],
    )
    assert result_edit.exit_code == 0, result_edit.output

    bible_before = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert "双面开刃" not in bible_before.text
    assert _EDIT_ATTR_ID not in bible_before.attribute_ids

    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _EDIT_ATTR_ID,
        ],
    )
    assert result.exit_code == 0, result.output
    assert _EDIT_ATTR_ID in result.output
    assert _CONFIRMED in result.output

    row = asyncio.run(PlanFactRepository().read_attribute(_EDIT_ATTR_ID))
    assert row is not None
    assert row.approval_status == "approved"
    assert row.source == "human"

    canon_ids = [
        a.attribute_id
        for a in asyncio.run(
            PlanFactRepository().list_canon_attributes(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    pending_ids = [
        a.attribute_id
        for a in asyncio.run(
            PlanFactRepository().list_pending_attributes(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    assert _EDIT_ATTR_ID in canon_ids
    assert _EDIT_ATTR_ID not in pending_ids

    bible = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert _EDIT_ATTR_ID in bible.attribute_ids
    assert "双面开刃" in bible.text


def test_canon_dismiss_entity_rejects_excluded_from_queues_and_bible(
    runner: CliRunner, dushi_db: Path
) -> None:
    _edit_entity(runner)
    result = runner.invoke(
        cli,
        [
            "canon",
            "dismiss",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            _EDIT_ENTITY_ID,
        ],
    )
    assert result.exit_code == 0, result.output
    assert _EDIT_ENTITY_ID in result.output

    row = asyncio.run(PlanFactRepository().read_entity(_EDIT_ENTITY_ID))
    assert row is not None
    assert row.approval_status == "rejected"

    canon_ids = [
        e.entity_id
        for e in asyncio.run(
            PlanFactRepository().list_canon_entities(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    pending_ids = [
        e.entity_id
        for e in asyncio.run(
            PlanFactRepository().list_pending_entities(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    assert _EDIT_ENTITY_ID not in canon_ids
    assert _EDIT_ENTITY_ID not in pending_ids

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
    assert _EDIT_ENTITY_ID not in pending

    bible = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert _EDIT_ENTITY_ID not in bible.entity_ids


def test_canon_dismiss_attribute_rejects_not_in_canon_or_bible(
    runner: CliRunner, dushi_db: Path
) -> None:
    _edit_entity(runner)
    _edit_attribute(runner)
    result = runner.invoke(
        cli,
        [
            "canon",
            "dismiss",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _EDIT_ATTR_ID,
        ],
    )
    assert result.exit_code == 0, result.output

    row = asyncio.run(PlanFactRepository().read_attribute(_EDIT_ATTR_ID))
    assert row is not None
    assert row.approval_status == "rejected"
    assert row.source == "human"

    canon_ids = [
        a.attribute_id
        for a in asyncio.run(
            PlanFactRepository().list_canon_attributes(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    pending_ids = [
        a.attribute_id
        for a in asyncio.run(
            PlanFactRepository().list_pending_attributes(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    assert _EDIT_ATTR_ID not in canon_ids
    assert _EDIT_ATTR_ID not in pending_ids

    bible = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert "双面开刃" not in bible.text


def test_canon_accept_does_not_persist_status(
    runner: CliRunner, dushi_db: Path
) -> None:
    _edit_entity(runner)
    before = asyncio.run(PlanFactRepository().read_entity(_EDIT_ENTITY_ID))
    assert before is not None
    assert before.approval_status == "pending"

    result = runner.invoke(
        cli,
        [
            "canon",
            "accept",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            _EDIT_ENTITY_ID,
        ],
    )
    assert result.exit_code == 0, result.output
    assert _ACCEPT_REMIND in result.output.lower() or "confirm" in result.output
    assert _NOT_YET_CANON in result.output or "尚未入典" in result.output

    after = asyncio.run(PlanFactRepository().read_entity(_EDIT_ENTITY_ID))
    assert after is not None
    assert after.approval_status == "pending"
    assert after.model_dump() == before.model_dump()


def test_rejected_then_edit_overwrites_same_id_to_pending(
    runner: CliRunner, dushi_db: Path
) -> None:
    _edit_entity(runner)
    dismiss = runner.invoke(
        cli,
        [
            "canon",
            "dismiss",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            _EDIT_ENTITY_ID,
        ],
    )
    assert dismiss.exit_code == 0, dismiss.output
    rejected = asyncio.run(PlanFactRepository().read_entity(_EDIT_ENTITY_ID))
    assert rejected is not None
    assert rejected.approval_status == "rejected"

    reedit = runner.invoke(
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
            "再试",
        ],
    )
    assert reedit.exit_code == 0, reedit.output
    row = asyncio.run(PlanFactRepository().read_entity(_EDIT_ENTITY_ID))
    assert row is not None
    assert row.approval_status == "pending"
    assert "再试" in row.aliases

    pending_ids = [
        e.entity_id
        for e in asyncio.run(
            PlanFactRepository().list_pending_entities(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    canon_ids = [
        e.entity_id
        for e in asyncio.run(
            PlanFactRepository().list_canon_entities(DUSHI_LINGYI_PROJECT_ID)
        )
    ]
    assert _EDIT_ENTITY_ID in pending_ids
    assert _EDIT_ENTITY_ID not in canon_ids


def test_canon_confirm_missing_id_exits_1(
    runner: CliRunner, dushi_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            "no-such-entity-id",
        ],
    )
    assert result.exit_code == 1, result.output


def test_canon_dismiss_missing_db_exits_1_without_creating_file(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "no-dismiss.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{missing}")
    assert not missing.exists()

    result = runner.invoke(
        cli,
        [
            "canon",
            "dismiss",
            "attribute",
            "--project-id",
            "any-id",
            "--attribute-id",
            "a1",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "找不到数据库" in result.output
    assert not missing.exists()


def test_canon_confirm_missing_project_exits_1(
    runner: CliRunner, empty_schema_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "attribute",
            "--project-id",
            "no-such-project",
            "--attribute-id",
            "a1",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "项目不存在" in result.output
