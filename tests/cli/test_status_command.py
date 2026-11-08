"""M4 步 1: ``songyan status`` 项目级计数面（tech-m4 §4.5 / B10 / B11 / task 238）."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ContextSnapshotRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.context import ContextSnapshot
from songyan.models.project import ProjectSetting
from songyan.models.variant import ChapterVariant

_PROJECT = "p-m4-status"
_EMPTY_PROJECT = "p-m4-status-empty"
_TS = "2026-11-08T00:00:00Z"

_STATUS_TABLES = (
    "chapter_heads",
    "chapter_variants",
    "chapter_versions",
    "context_snapshots",
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def status_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-status.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 status",
        ),
        _PROJECT,
    )
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 status empty",
        ),
        _EMPTY_PROJECT,
    )

    # ch1: accepted 且 content_stale=0 → settled
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="v-a",
            project_id=_PROJECT,
            chapter_number=1,
            version_number=1,
            content="第1章定稿",
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=1,
            current_version_id="v-a",
            accepted_version_id="v-a",
            content_stale=0,
        )
    )
    # ch2: picked 槽未 accept → picked
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="v-w",
            project_id=_PROJECT,
            chapter_number=2,
            version_number=1,
            content="第2章工作稿",
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=2,
            current_version_id="v-w",
        )
    )
    await ChapterVariantRepository().insert(
        ChapterVariant(
            variant_id="var-2-1",
            project_id=_PROJECT,
            chapter_number=2,
            slot_index=1,
            status="picked",
            parent_canon_fingerprint="fp",
            content_ref="v-w",
            created_at=_TS,
            updated_at=_TS,
        )
    )
    # snapshots: ch3 / ch5 触发 ContextEmergency（ch5 最近）；ch4 未触发
    for snapshot_id, chapter, emergency, budget_before, created in [
        ("snap-3", 3, True, 0.35, datetime(2026, 11, 8)),
        ("snap-4", 4, False, None, datetime(2026, 11, 8, 12)),
        ("snap-5", 5, True, 0.8, datetime(2026, 11, 9)),
    ]:
        await ContextSnapshotRepository().create(
            ContextSnapshot(
                snapshot_id=snapshot_id,
                project_id=_PROJECT,
                chapter_number=chapter,
                budget_used=1.0,
                context_emergency=emergency,
                context_emergency_level=2 if emergency else 0,
                budget_used_before_emergency=budget_before,
                created_at=created,
            )
        )
    return db_path


async def _table_counts() -> dict[str, int]:
    async with get_db() as conn:
        out: dict[str, int] = {}
        for table in _STATUS_TABLES:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            out[table] = int(row[0])
    return out


def test_status_text_counts_and_emergency(
    runner: CliRunner, status_db: Path
) -> None:
    before = asyncio.run(_table_counts())
    result = runner.invoke(cli, ["status", "--project-id", _PROJECT])
    after = asyncio.run(_table_counts())

    assert result.exit_code == 0, result.output
    assert (
        "progress: stale=0 settled=1 picked=1 variants_ready=0 drafting=0 empty=0"
        in result.output
    )
    assert "pending_confirm: 1" in result.output
    assert "context_emergency: count=2 last_chapter=5 budget_used_before=0.8" in (
        result.output
    )
    assert after == before


def test_status_json_shape(runner: CliRunner, status_db: Path) -> None:
    before = asyncio.run(_table_counts())
    result = runner.invoke(cli, ["status", "--project-id", _PROJECT, "--json"])
    after = asyncio.run(_table_counts())

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert set(payload) == {"project_id", "progress", "pending_confirm", "context_emergency"}
    assert payload["project_id"] == _PROJECT
    assert payload["progress"] == {
        "stale": 0,
        "settled": 1,
        "picked": 1,
        "variants_ready": 0,
        "drafting": 0,
        "empty": 0,
    }
    assert payload["pending_confirm"] == 1
    assert payload["context_emergency"] == {
        "count": 2,
        "last_chapter": 5,
        "budget_used_before": 0.8,
    }
    assert after == before


def test_status_no_records_boundary(runner: CliRunner, status_db: Path) -> None:
    result = runner.invoke(cli, ["status", "--project-id", _EMPTY_PROJECT])

    assert result.exit_code == 0, result.output
    assert (
        "progress: stale=0 settled=0 picked=0 variants_ready=0 drafting=0 empty=0"
        in result.output
    )
    assert "pending_confirm: 0" in result.output
    assert "context_emergency: count=0 last_chapter=- budget_used_before=-" in (
        result.output
    )

    result_json = runner.invoke(cli, ["status", "--project-id", _EMPTY_PROJECT, "--json"])
    assert result_json.exit_code == 0, result_json.output
    payload = json.loads(result_json.output)
    assert payload["progress"] == {
        "stale": 0,
        "settled": 0,
        "picked": 0,
        "variants_ready": 0,
        "drafting": 0,
        "empty": 0,
    }
    assert payload["pending_confirm"] == 0
    assert payload["context_emergency"] == {
        "count": 0,
        "last_chapter": None,
        "budget_used_before": None,
    }


def test_status_missing_db_exits_1_without_creating_file(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "no-such-status.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{missing}")
    assert not missing.exists()

    result = runner.invoke(cli, ["status", "--project-id", "any-id"])

    assert result.exit_code == 1, result.output
    assert "找不到数据库" in result.output
    assert not missing.exists()


def test_status_missing_project_exits_1(
    runner: CliRunner, status_db: Path
) -> None:
    result = runner.invoke(cli, ["status", "--project-id", "no-such-project"])

    assert result.exit_code == 1, result.output
    assert "项目不存在" in result.output
    assert "no-such-project" in result.output


def test_status_missing_project_id_usage_error_exit_2(runner: CliRunner) -> None:
    """B11 口径：usage 错误（缺 --project-id）走 Click 默认 exit 2。"""
    result = runner.invoke(cli, ["status"])

    assert result.exit_code == 2
