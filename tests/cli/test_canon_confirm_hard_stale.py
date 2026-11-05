"""M2 step 3: W4 content_stale + canon confirm --hard / --mark-stale."""

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
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.models.chapter import ChapterHead, ChapterVersion

_ENTITY_ID = "m2-stale-entity"
_ATTR_ID = "m2-stale-attr-window-2-4"
_ATTR_EMPTY_ID = "m2-stale-attr-empty-window"
_OLD_CONTENT = "第{n}章原文不得被覆盖"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def stale_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "canon-hard-stale.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
    for n in range(1, 6):
        version_id = f"v-stale-ch{n}"
        content = _OLD_CONTENT.format(n=n)
        await ChapterVersionRepository().create(
            ChapterVersion(
                version_id=version_id,
                project_id=DUSHI_LINGYI_PROJECT_ID,
                chapter_number=n,
                version_number=1,
                version_type="accepted",
                content=content,
                word_count=len(content),
            )
        )
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=DUSHI_LINGYI_PROJECT_ID,
                chapter_number=n,
                current_version_id=version_id,
                accepted_version_id=version_id,
                status="accepted",
            )
        )
    return db_path


def _edit_entity(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            _ENTITY_ID,
            "--type",
            "prop",
        ],
    )
    assert result.exit_code == 0, result.output


def _edit_attribute(
    runner: CliRunner,
    *,
    attribute_id: str,
    valid_from: str | None,
    valid_to: str | None,
) -> None:
    args = [
        "canon",
        "edit",
        "attribute",
        "--project-id",
        DUSHI_LINGYI_PROJECT_ID,
        "--attribute-id",
        attribute_id,
        "--entity-id",
        _ENTITY_ID,
        "--key",
        "edge",
        "--value",
        "硬变更试刀",
    ]
    if valid_from is not None:
        args.extend(["--valid-from-ch", valid_from])
    if valid_to is not None:
        args.extend(["--valid-to-ch", valid_to])
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output


async def _stale_map(project_id: str) -> dict[int, int]:
    heads = await ChapterHeadRepository().list_by_project(project_id)
    return {h.chapter_number: int(getattr(h, "content_stale", 0) or 0) for h in heads}


async def _version_content(version_id: str) -> str:
    row = await ChapterVersionRepository().get(version_id)
    assert row is not None
    return row.content


def test_hard_attribute_marks_chapters_2_to_4_only(
    runner: CliRunner, stale_db: Path
) -> None:
    _edit_entity(runner)
    _edit_attribute(runner, attribute_id=_ATTR_ID, valid_from="2", valid_to="4")

    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _ATTR_ID,
            "--hard",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "已入典" in result.output

    row = asyncio.run(PlanFactRepository().read_attribute(_ATTR_ID))
    assert row is not None
    assert row.approval_status == "approved"

    stale = asyncio.run(_stale_map(DUSHI_LINGYI_PROJECT_ID))
    assert stale[2] == 1
    assert stale[3] == 1
    assert stale[4] == 1
    assert stale[1] == 0
    assert stale[5] == 0


def test_hard_confirm_does_not_overwrite_chapter_version_content(
    runner: CliRunner, stale_db: Path
) -> None:
    _edit_entity(runner)
    _edit_attribute(runner, attribute_id=_ATTR_ID, valid_from="2", valid_to="4")

    before = {
        n: asyncio.run(_version_content(f"v-stale-ch{n}")) for n in range(1, 6)
    }

    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _ATTR_ID,
            "--hard",
        ],
    )
    assert result.exit_code == 0, result.output

    for n in range(1, 6):
        after = asyncio.run(_version_content(f"v-stale-ch{n}"))
        assert after == before[n]
        assert after == _OLD_CONTENT.format(n=n)


def test_soft_confirm_without_flags_does_not_mark_stale(
    runner: CliRunner, stale_db: Path
) -> None:
    _edit_entity(runner)
    _edit_attribute(runner, attribute_id=_ATTR_ID, valid_from="2", valid_to="4")

    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _ATTR_ID,
        ],
    )
    assert result.exit_code == 0, result.output

    row = asyncio.run(PlanFactRepository().read_attribute(_ATTR_ID))
    assert row is not None
    assert row.approval_status == "approved"

    stale = asyncio.run(_stale_map(DUSHI_LINGYI_PROJECT_ID))
    assert all(v == 0 for v in stale.values())


def test_soft_confirm_mark_stale_marks_window(
    runner: CliRunner, stale_db: Path
) -> None:
    _edit_entity(runner)
    _edit_attribute(runner, attribute_id=_ATTR_ID, valid_from="2", valid_to="4")

    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _ATTR_ID,
            "--mark-stale",
        ],
    )
    assert result.exit_code == 0, result.output

    stale = asyncio.run(_stale_map(DUSHI_LINGYI_PROJECT_ID))
    assert stale[2] == 1
    assert stale[3] == 1
    assert stale[4] == 1
    assert stale[1] == 0
    assert stale[5] == 0


def test_hard_with_uncomputable_range_fails_whole_command_no_canon_no_stale(
    runner: CliRunner, stale_db: Path
) -> None:
    _edit_entity(runner)
    _edit_attribute(
        runner, attribute_id=_ATTR_EMPTY_ID, valid_from=None, valid_to=None
    )

    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _ATTR_EMPTY_ID,
            "--hard",
        ],
    )
    assert result.exit_code == 2, result.output

    row = asyncio.run(PlanFactRepository().read_attribute(_ATTR_EMPTY_ID))
    assert row is not None
    assert row.approval_status == "pending"

    stale = asyncio.run(_stale_map(DUSHI_LINGYI_PROJECT_ID))
    assert all(v == 0 for v in stale.values())


def test_hard_entity_without_range_flags_fails(
    runner: CliRunner, stale_db: Path
) -> None:
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
            _ENTITY_ID,
            "--hard",
        ],
    )
    assert result.exit_code == 2, result.output

    row = asyncio.run(PlanFactRepository().read_entity(_ENTITY_ID))
    assert row is not None
    assert row.approval_status == "pending"

    stale = asyncio.run(_stale_map(DUSHI_LINGYI_PROJECT_ID))
    assert all(v == 0 for v in stale.values())


def test_hard_entity_with_explicit_from_to_marks_range(
    runner: CliRunner, stale_db: Path
) -> None:
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
            _ENTITY_ID,
            "--hard",
            "--from-ch",
            "2",
            "--to-ch",
            "4",
        ],
    )
    assert result.exit_code == 0, result.output

    row = asyncio.run(PlanFactRepository().read_entity(_ENTITY_ID))
    assert row is not None
    assert row.approval_status == "approved"

    stale = asyncio.run(_stale_map(DUSHI_LINGYI_PROJECT_ID))
    assert stale[2] == 1
    assert stale[3] == 1
    assert stale[4] == 1
    assert stale[1] == 0
    assert stale[5] == 0


def test_migration_adds_content_stale_default_zero(stale_db: Path) -> None:
    async def _check() -> None:
        async with get_db() as conn:
            cursor = await conn.execute("PRAGMA table_info(chapter_heads)")
            cols = {row[1]: row for row in await cursor.fetchall()}
            assert "content_stale" in cols
            # NOT NULL DEFAULT 0
            assert cols["content_stale"][3] == 1  # notnull
            # existing rows default 0
            cursor = await conn.execute(
                "SELECT content_stale FROM chapter_heads WHERE project_id = ?",
                (DUSHI_LINGYI_PROJECT_ID,),
            )
            values = [row[0] for row in await cursor.fetchall()]
            assert values
            assert all(v == 0 for v in values)

    asyncio.run(_check())
