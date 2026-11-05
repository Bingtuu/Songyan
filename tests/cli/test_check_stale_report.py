"""M2 step 4: ``songyan check`` reports content_stale / affected chapter range."""

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
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.plan_facts import PlanAttribute, PlanEntity
from songyan.models.project import ProjectSetting

_PROJECT_ID = "check-stale-m2-proj"
_ENTITY_ID = "chk-stale-entity"
_ATTR_ID = "chk-stale-attr-2-4"
_OLD_CONTENT = "第{n}章原文不得被覆盖"
_PLAN_TABLES = (
    "plan_entities",
    "plan_attributes",
    "plan_events",
    "plan_time_anchors",
    "plan_clues",
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def stale_check_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal project + chapters 1–5; no heavy plan bible (gate stays pass)."""
    db_path = tmp_path / "check-stale.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(genre_id="urban_fantasy", protagonist_name="试刀"),
        _PROJECT_ID,
    )
    repo = PlanFactRepository()
    await repo.write_entity(
        PlanEntity(
            entity_id=_ENTITY_ID,
            project_id=_PROJECT_ID,
            entity_type="prop",
            aliases=["刻痕"],
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="chk-stale-attr-canon",
            project_id=_PROJECT_ID,
            entity_id=_ENTITY_ID,
            key="direction",
            value="东向西",
            valid_from_ch=1,
            valid_to_ch=5,
            source="human",
            approval_status="approved",
        )
    )
    for n in range(1, 6):
        version_id = f"v-check-stale-ch{n}"
        content = _OLD_CONTENT.format(n=n)
        await ChapterVersionRepository().create(
            ChapterVersion(
                version_id=version_id,
                project_id=_PROJECT_ID,
                chapter_number=n,
                version_number=1,
                version_type="accepted",
                content=content,
                word_count=len(content),
            )
        )
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=_PROJECT_ID,
                chapter_number=n,
                current_version_id=version_id,
                accepted_version_id=version_id,
                status="accepted",
            )
        )
    return db_path


def _parse_cli_json(text: str) -> dict:
    start = text.find("{")
    assert start >= 0, text
    return json.loads(text[start:])


def _edit_pending_attribute(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "attribute",
            "--project-id",
            _PROJECT_ID,
            "--attribute-id",
            _ATTR_ID,
            "--entity-id",
            _ENTITY_ID,
            "--key",
            "edge",
            "--value",
            "硬变更试刀",
            "--valid-from-ch",
            "2",
            "--valid-to-ch",
            "4",
        ],
    )
    assert result.exit_code == 0, result.output


def _hard_confirm_attribute(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "attribute",
            "--project-id",
            _PROJECT_ID,
            "--attribute-id",
            _ATTR_ID,
            "--hard",
        ],
    )
    assert result.exit_code == 0, result.output


async def _stale_map(project_id: str) -> dict[int, int]:
    heads = await ChapterHeadRepository().list_by_project(project_id)
    return {h.chapter_number: int(h.content_stale or 0) for h in heads}


async def _plan_approval_snapshot(project_id: str) -> dict[str, str]:
    repo = PlanFactRepository()
    statuses: dict[str, str] = {}
    for row in await repo.list_canon_attributes(project_id):
        statuses[f"attr:{row.attribute_id}"] = row.approval_status
    for row in await repo.list_pending_attributes(project_id):
        statuses[f"attr:{row.attribute_id}"] = row.approval_status
    for row in await repo.list_canon_entities(project_id):
        statuses[f"ent:{row.entity_id}"] = row.approval_status
    for row in await repo.list_pending_entities(project_id):
        statuses[f"ent:{row.entity_id}"] = row.approval_status
    return statuses


async def _plan_counts(project_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    async with get_db() as conn:
        for table in _PLAN_TABLES:
            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
            assert row is not None
            counts[table] = int(row[0])
    return counts


async def _version_contents() -> dict[str, str]:
    out: dict[str, str] = {}
    for n in range(1, 6):
        row = await ChapterVersionRepository().get(f"v-check-stale-ch{n}")
        assert row is not None
        out[f"v-check-stale-ch{n}"] = row.content
    return out


def test_check_reports_stale_range_after_hard_confirm_json(
    runner: CliRunner, stale_check_db: Path
) -> None:
    _edit_pending_attribute(runner)
    _hard_confirm_attribute(runner)

    stale_before = asyncio.run(_stale_map(_PROJECT_ID))
    assert stale_before[2] == 1
    assert stale_before[3] == 1
    assert stale_before[4] == 1
    assert stale_before[1] == 0
    assert stale_before[5] == 0

    result = runner.invoke(
        cli,
        [
            "check",
            "--project-id",
            _PROJECT_ID,
            "--chapter",
            "3",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_cli_json(result.output)
    assert payload["chapter"] == 3
    assert payload["content_stale_chapters"] == [2, 3, 4]
    assert payload["chapter_content_stale"] is True


def test_check_reports_stale_range_markdown_names_chapters(
    runner: CliRunner, stale_check_db: Path
) -> None:
    _edit_pending_attribute(runner)
    _hard_confirm_attribute(runner)

    result = runner.invoke(
        cli,
        [
            "check",
            "--project-id",
            _PROJECT_ID,
            "--chapter",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "正文过期" in result.output
    assert "2–4" in result.output
    assert "受影响" in result.output
    assert "未标过期" in result.output


def test_check_does_not_mutate_stale_or_plan_or_versions(
    runner: CliRunner, stale_check_db: Path
) -> None:
    _edit_pending_attribute(runner)
    _hard_confirm_attribute(runner)

    stale_before = asyncio.run(_stale_map(_PROJECT_ID))
    plan_before = asyncio.run(_plan_approval_snapshot(_PROJECT_ID))
    counts_before = asyncio.run(_plan_counts(_PROJECT_ID))
    versions_before = asyncio.run(_version_contents())

    result = runner.invoke(
        cli,
        [
            "check",
            "--project-id",
            _PROJECT_ID,
            "--chapter",
            "2",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_cli_json(result.output)
    assert payload["content_stale_chapters"] == [2, 3, 4]
    assert payload["chapter_content_stale"] is True

    assert asyncio.run(_stale_map(_PROJECT_ID)) == stale_before
    assert asyncio.run(_plan_approval_snapshot(_PROJECT_ID)) == plan_before
    assert asyncio.run(_plan_counts(_PROJECT_ID)) == counts_before
    assert asyncio.run(_version_contents()) == versions_before


def test_check_empty_stale_list_when_none_marked(
    runner: CliRunner, stale_check_db: Path
) -> None:
    """No hard confirm → check still emits empty stale list, no DB write."""
    stale_before = asyncio.run(_stale_map(_PROJECT_ID))
    assert all(v == 0 for v in stale_before.values())

    result = runner.invoke(
        cli,
        [
            "check",
            "--project-id",
            _PROJECT_ID,
            "--chapter",
            "1",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_cli_json(result.output)
    assert payload["content_stale_chapters"] == []
    assert payload["chapter_content_stale"] is False
    assert asyncio.run(_stale_map(_PROJECT_ID)) == stale_before


def test_check_reports_stale_via_direct_mark_fixture(
    runner: CliRunner, stale_check_db: Path
) -> None:
    """Direct mark_content_stale fixture (without confirm) still surfaces in check."""
    updated = asyncio.run(
        ChapterHeadRepository().mark_content_stale(_PROJECT_ID, [2, 4])
    )
    assert updated == 2

    result = runner.invoke(
        cli,
        [
            "check",
            "--project-id",
            _PROJECT_ID,
            "--chapter",
            "4",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_cli_json(result.output)
    assert payload["content_stale_chapters"] == [2, 4]
    assert payload["chapter_content_stale"] is True

    stale_after = asyncio.run(_stale_map(_PROJECT_ID))
    assert stale_after[2] == 1
    assert stale_after[4] == 1
    assert stale_after[3] == 0
