"""M1 step 4: ``songyan check`` thin wrap of ``run_plan_fact_gate`` (W6)."""

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
from songyan.db.plan_fact_loader import (
    DUSHI_LINGYI_PROJECT_ID,
    bundled_dushi_lingyi_fixture,
    load_plan_fact_fixture,
)
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.plan_facts import PlanAttribute, PlanEntity
from songyan.models.project import ProjectSetting

_PLAN_TABLES = (
    "plan_entities",
    "plan_attributes",
    "plan_events",
    "plan_time_anchors",
    "plan_clues",
)
_PROJECT_ID = "check-m1-proj"
_CANON_HINT = "若要入典"
_CONFIRM_HINT = "canon confirm"
_NO_PUBLISH = "可以发表"

def _parse_cli_json(text: str) -> dict:
    """CliRunner may capture structlog lines before the JSON payload."""
    start = text.find("{")
    assert start >= 0, text
    return json.loads(text[start:])




@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def dushi_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "check-dushi.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
    return db_path


@pytest.fixture
async def empty_schema_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "check-empty.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    return db_path


@pytest.fixture
async def minimal_project_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """One project, one approved typed attribute, no clues/events."""
    db_path = tmp_path / "check-minimal.db"
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
            entity_id="chk-entity",
            project_id=_PROJECT_ID,
            entity_type="prop",
            aliases=["刻痕"],
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="chk-attr-dir",
            project_id=_PROJECT_ID,
            entity_id="chk-entity",
            key="direction",
            value="东向西",
            valid_from_ch=1,
            valid_to_ch=3,
            source="human",
            approval_status="approved",
        )
    )
    return db_path


async def _seed_chapter(
    project_id: str,
    chapter: int,
    content: str,
    *,
    version_id: str = "v-check-1",
) -> None:
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter,
            version_number=1,
            version_type="accepted",
            content=content,
            word_count=len(content),
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=chapter,
            current_version_id=version_id,
            accepted_version_id=version_id,
            status="accepted",
        )
    )


async def _plan_snapshot(project_id: str) -> tuple[dict[str, int], dict[str, str]]:
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
    # rejected rows still readable via read_*
    return counts, statuses


def test_check_missing_db_exits_1_without_creating_file(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "no-such-check.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{missing}")
    result = runner.invoke(
        cli,
        ["check", "--project-id", "any", "--chapter", "1"],
    )
    assert result.exit_code == 1, result.output
    assert "找不到数据库" in result.output
    assert not missing.exists()


def test_check_missing_project_exits_1(
    runner: CliRunner, empty_schema_db: Path
) -> None:
    result = runner.invoke(
        cli,
        ["check", "--project-id", "no-such-project", "--chapter", "1"],
    )
    assert result.exit_code == 1, result.output
    assert "项目不存在" in result.output


def test_check_no_chapter_exits_2(
    runner: CliRunner, dushi_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "check",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--chapter",
            "1",
        ],
    )
    assert result.exit_code == 2, result.output
    assert "无章可查" in result.output


def test_check_empty_accepted_content_exits_2(
    runner: CliRunner, minimal_project_db: Path
) -> None:
    asyncio.run(_seed_chapter(_PROJECT_ID, 1, "   ", version_id="v-empty"))
    result = runner.invoke(
        cli,
        ["check", "--project-id", _PROJECT_ID, "--chapter", "1"],
    )
    assert result.exit_code == 2, result.output
    assert "无章可查" in result.output


def test_check_pass_exit_0_no_publish_wording_and_confirm_hint(
    runner: CliRunner, minimal_project_db: Path
) -> None:
    asyncio.run(_seed_chapter(_PROJECT_ID, 1, "刻痕仍是东向西。"))
    before = asyncio.run(_plan_snapshot(_PROJECT_ID))
    result = runner.invoke(
        cli,
        ["check", "--project-id", _PROJECT_ID, "--chapter", "1"],
    )
    assert result.exit_code == 0, result.output
    assert _NO_PUBLISH not in result.output
    assert _CANON_HINT in result.output
    assert _CONFIRM_HINT in result.output
    after = asyncio.run(_plan_snapshot(_PROJECT_ID))
    assert after == before


def test_check_injected_attribute_mismatch_reports_fields_exit_2(
    runner: CliRunner, minimal_project_db: Path, tmp_path: Path
) -> None:
    """PRD §6.4: approved attr + injected extract mismatch names fields."""
    asyncio.run(
        _seed_chapter(
            _PROJECT_ID,
            1,
            "正文里写西向东也不该被门现抽；只看注入的摘录。",
        )
    )
    extracts_path = tmp_path / "extracts.json"
    extracts_path.write_text(
        json.dumps(
            [
                {
                    "entity_id": "chk-entity",
                    "key": "direction",
                    "value": "西向东",
                    "chapter": 1,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    before = asyncio.run(_plan_snapshot(_PROJECT_ID))
    result = runner.invoke(
        cli,
        [
            "check",
            "--project-id",
            _PROJECT_ID,
            "--chapter",
            "1",
            "--extracts-json",
            str(extracts_path),
            "--json",
        ],
    )
    assert result.exit_code == 2, result.output
    payload = _parse_cli_json(result.output)
    assert payload["passed"] is False
    assert payload["project_id"] == _PROJECT_ID
    assert payload["chapter"] == 1
    mismatches = payload["attribute_mismatches"]
    assert len(mismatches) == 1
    row = mismatches[0]
    assert row["entity_id"] == "chk-entity"
    assert row["key"] == "direction"
    assert row["approved_value"] == "东向西"
    assert row["extract_value"] == "西向东"
    assert row["severity"] == "hard"
    assert _NO_PUBLISH not in result.output
    assert _CANON_HINT in json.dumps(payload, ensure_ascii=False) or _CANON_HINT in str(
        payload.get("hint", "")
    )
    after = asyncio.run(_plan_snapshot(_PROJECT_ID))
    assert after == before


def test_check_markdown_mismatch_names_bible_and_prose_side(
    runner: CliRunner, minimal_project_db: Path, tmp_path: Path
) -> None:
    asyncio.run(_seed_chapter(_PROJECT_ID, 1, "任意正文。"))
    extracts_path = tmp_path / "extracts.md.json"
    extracts_path.write_text(
        json.dumps(
            [
                {
                    "entity_id": "chk-entity",
                    "key": "direction",
                    "value": "西向东",
                    "chapter": 1,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        cli,
        [
            "check",
            "--project-id",
            _PROJECT_ID,
            "--chapter",
            "1",
            "--extracts-json",
            str(extracts_path),
        ],
    )
    assert result.exit_code == 2, result.output
    assert "chk-entity" in result.output
    assert "direction" in result.output
    assert "东向西" in result.output
    assert "西向东" in result.output
    assert _CANON_HINT in result.output
    assert _CONFIRM_HINT in result.output
    assert _NO_PUBLISH not in result.output


def test_check_does_not_invent_extracts_from_prose(
    runner: CliRunner, minimal_project_db: Path
) -> None:
    """Gate must not invent AttributeExtract from prose alone."""
    asyncio.run(
        _seed_chapter(
            _PROJECT_ID,
            1,
            "正文明明写着西向东，但没有注入摘录时不得报属性不一致。",
        )
    )
    result = runner.invoke(
        cli,
        ["check", "--project-id", _PROJECT_ID, "--chapter", "1", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_cli_json(result.output)
    assert payload["passed"] is True
    assert payload["attribute_mismatches"] == []
    assert _NO_PUBLISH not in result.output


def test_check_no_confirm_side_effect(
    runner: CliRunner, minimal_project_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W6 must not call confirm / write approval_status."""
    asyncio.run(_seed_chapter(_PROJECT_ID, 1, "东向西。"))
    writes: list[str] = []

    original_write_attr = PlanFactRepository.write_attribute
    original_write_ent = PlanFactRepository.write_entity

    async def _track_attr(self: PlanFactRepository, *args: object, **kwargs: object) -> None:
        writes.append("attribute")
        await original_write_attr(self, *args, **kwargs)

    async def _track_ent(self: PlanFactRepository, *args: object, **kwargs: object) -> None:
        writes.append("entity")
        await original_write_ent(self, *args, **kwargs)

    monkeypatch.setattr(PlanFactRepository, "write_attribute", _track_attr)
    monkeypatch.setattr(PlanFactRepository, "write_entity", _track_ent)

    extracts_path = tmp_path / "extracts-confirm.json"
    extracts_path.write_text(
        json.dumps(
            [
                {
                    "entity_id": "chk-entity",
                    "key": "direction",
                    "value": "西向东",
                    "chapter": 1,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        cli,
        [
            "check",
            "--project-id",
            _PROJECT_ID,
            "--chapter",
            "1",
            "--extracts-json",
            str(extracts_path),
        ],
    )
    assert result.exit_code == 2, result.output
    assert writes == []
