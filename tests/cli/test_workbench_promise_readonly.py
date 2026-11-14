"""M2 step 1: W5 read-only promise counts on today + canon show --kind promise."""

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
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models.context import ForeshadowingItem
from songyan.models.plan_facts import PlanEntity
from songyan.plan_checks.bible import load_chapter_plan_bible

_PENDING_ID = "dly-pending-promise-s8"
_OVERDUE_ID = "fs-overdue-m2-step1"
_PLANTED_ID = "fs-planted-m2-step1"
_DUE_ID = "fs-due-m2-step1"
_RESOLVED_ID = "fs-resolved-m2-step1"
_DORMANT_ID = "fs-dormant-overdue-m2-step1"
_PROMISE_HEAD = "# 开放承诺（不是已确认事实）"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


async def _seed_version(
    project_id: str, version_id: str, chapter_number: int = 1
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES (?, ?, ?, ?, ?)""",
            (version_id, project_id, chapter_number, 1, "accepted"),
        )
        await conn.commit()


async def _seed_foreshadowing(
    foreshadowing_id: str,
    *,
    description: str,
    planted: int,
    status: str,
    lifecycle_status: str = "active",
    expected: int | None = None,
    source_version_id: str = "v-m2-promise",
) -> None:
    await _seed_version(DUSHI_LINGYI_PROJECT_ID, source_version_id, planted)
    await ForeshadowingRepository().create(
        ForeshadowingItem(
            foreshadowing_id=foreshadowing_id,
            description=description,
            planted_in_chapter=planted,
            expected_resolve_chapter=expected,
            status=status,  # type: ignore[arg-type]
        ),
        DUSHI_LINGYI_PROJECT_ID,
        source_version_id,
    )
    if lifecycle_status != "active":
        async with get_db() as conn:
            await conn.execute(
                "UPDATE foreshadowings SET lifecycle_status = ? WHERE foreshadowing_id = ?",
                (lifecycle_status, foreshadowing_id),
            )
            await conn.commit()


@pytest.fixture
async def dushi_with_promises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """都市灵异夹具 + pending 实体 + open/closed foreshadowings."""
    db_path = tmp_path / "promise-readonly.db"
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
    await _seed_foreshadowing(
        _OVERDUE_ID,
        description="逾期承诺甲",
        planted=1,
        expected=2,
        status="overdue",
    )
    await _seed_foreshadowing(
        _PLANTED_ID,
        description="已种承诺乙",
        planted=3,
        expected=10,
        status="planted",
    )
    await _seed_foreshadowing(
        _DUE_ID,
        description="到期承诺丙",
        planted=2,
        expected=5,
        status="due",
    )
    await _seed_foreshadowing(
        _RESOLVED_ID,
        description="已销承诺丁",
        planted=1,
        expected=2,
        status="resolved",
    )
    await _seed_foreshadowing(
        _DORMANT_ID,
        description="休眠逾期戊",
        planted=1,
        expected=2,
        status="overdue",
        lifecycle_status="dormant",
    )
    return db_path


async def _foreshadowing_counts() -> dict[str, int]:
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT status, lifecycle_status, COUNT(*)
               FROM foreshadowings GROUP BY status, lifecycle_status"""
        )
        rows = await cursor.fetchall()
    return {f"{status}:{life}": int(n) for status, life, n in rows}


async def _plan_entity_count() -> int:
    async with get_db() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM plan_entities")
        row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


def test_today_counts_include_overdue_promise(
    runner: CliRunner, dushi_with_promises: Path
) -> None:
    before_fs = asyncio.run(_foreshadowing_counts())
    before_plan = asyncio.run(_plan_entity_count())
    result = runner.invoke(
        cli, ["today", "--project-id", DUSHI_LINGYI_PROJECT_ID]
    )
    after_fs = asyncio.run(_foreshadowing_counts())
    after_plan = asyncio.run(_plan_entity_count())

    assert result.exit_code == 0, result.output
    assert "promise_planted: 1" in result.output
    assert "promise_due: 1" in result.output
    assert "promise_overdue: 1" in result.output
    # Must not present open promises as confirmed Canon facts.
    assert "已确认事实（Canon / approved）" not in result.output
    assert _OVERDUE_ID not in result.output
    assert after_fs == before_fs
    assert after_plan == before_plan


def test_today_json_promise_counts(
    runner: CliRunner, dushi_with_promises: Path
) -> None:
    result = runner.invoke(
        cli, ["today", "--project-id", DUSHI_LINGYI_PROJECT_ID, "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "promise_counts" in payload
    assert payload["promise_counts"] == {
        "planted": 1,
        "due": 1,
        "overdue": 1,
    }
    # Open promises are not canon_counts.
    assert "promise" not in payload["canon_counts"]


def test_canon_show_kind_promise_lists_open_only(
    runner: CliRunner, dushi_with_promises: Path
) -> None:
    before_fs = asyncio.run(_foreshadowing_counts())
    result = runner.invoke(
        cli,
        [
            "canon",
            "show",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--kind",
            "promise",
        ],
    )
    after_fs = asyncio.run(_foreshadowing_counts())

    assert result.exit_code == 0, result.output
    assert _PROMISE_HEAD in result.output
    assert "不是已确认事实" in result.output
    assert _OVERDUE_ID in result.output
    assert _PLANTED_ID in result.output
    assert _DUE_ID in result.output
    assert _RESOLVED_ID not in result.output
    assert _DORMANT_ID not in result.output
    # Default Canon / Pending plan sections must not appear as confirmed facts here.
    assert "# 已确认事实（Canon / approved）" not in result.output
    assert _PENDING_ID not in result.output
    assert after_fs == before_fs


def test_canon_show_kind_promise_json(
    runner: CliRunner, dushi_with_promises: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "show",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--kind",
            "promise",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["project_id"] == DUSHI_LINGYI_PROJECT_ID
    assert payload["kind"] == "promise"
    ids = {row["foreshadowing_id"] for row in payload["promises"]}
    assert ids == {_OVERDUE_ID, _PLANTED_ID, _DUE_ID}
    statuses = {row["status"] for row in payload["promises"]}
    assert statuses == {"planted", "due", "overdue"}
    assert "canon" not in payload
    assert _PENDING_ID not in json.dumps(payload, ensure_ascii=False)


def test_default_canon_show_does_not_leak_promises_as_canon(
    runner: CliRunner, dushi_with_promises: Path
) -> None:
    result = runner.invoke(
        cli, ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID]
    )
    assert result.exit_code == 0, result.output
    canon = result.output.split("# 待确认提案（pending，不是已确认事实）")[0]
    assert _OVERDUE_ID not in canon
    assert _PLANTED_ID not in canon
    assert _DUE_ID not in canon
    assert _PENDING_ID not in canon
    assert "approval_status=pending" not in canon

    bible = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert _PENDING_ID not in bible.entity_ids
    assert _PENDING_ID not in bible.text
    assert _OVERDUE_ID not in bible.text
