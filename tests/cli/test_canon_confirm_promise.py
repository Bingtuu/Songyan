"""M2 step 2: W5 human confirm settle via ``canon confirm promise``."""

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
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.context import ForeshadowingItem

_OVERDUE_ID = "fs-overdue-m2-step2"
_PLANTED_ID = "fs-planted-m2-step2"
_OTHER_ID = "fs-other-open-m2-step2"
_RESOLVE_CHAPTER = 4
_RESOLVE_VERSION = "v-m2-step2-ch4"
_SOURCE_VERSION = "v-m2-step2-src"
_EVIDENCE = "第4章当面兑现了那句承诺"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


async def _seed_version(
    project_id: str, version_id: str, chapter_number: int
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES (?, ?, ?, ?, ?)""",
            (version_id, project_id, chapter_number, 1, "accepted"),
        )
        await conn.commit()


async def _seed_accepted_chapter(
    project_id: str, chapter: int, version_id: str, content: str = "兑现正文"
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


async def _seed_foreshadowing(
    foreshadowing_id: str,
    *,
    description: str,
    planted: int,
    status: str,
    expected: int | None = None,
    lifecycle_status: str = "active",
    source_version_id: str = _SOURCE_VERSION,
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
async def settle_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "confirm-promise.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
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
        _OTHER_ID,
        description="另一条开放债",
        planted=2,
        expected=8,
        status="due",
    )
    await _seed_accepted_chapter(
        DUSHI_LINGYI_PROJECT_ID, _RESOLVE_CHAPTER, _RESOLVE_VERSION
    )
    return db_path


async def _open_ids() -> set[str]:
    items = await ForeshadowingRepository().list_schedulable(DUSHI_LINGYI_PROJECT_ID)
    return {item.foreshadowing_id for item in items}


async def _read_trace(foreshadowing_id: str) -> tuple[str, int | None, str | None]:
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT status, resolved_chapter, resolved_version_id
               FROM foreshadowings WHERE foreshadowing_id = ?""",
            (foreshadowing_id,),
        )
        row = await cursor.fetchone()
    assert row is not None
    return str(row[0]), row[1], row[2]


def test_without_confirm_open_set_unchanged(
    runner: CliRunner, settle_db: Path
) -> None:
    """PRD §6.6 验收 2：未经 confirm 的销账不清 open 集（含「提案未确认」）。"""
    before = asyncio.run(_open_ids())
    assert _OVERDUE_ID in before

    # No confirm invoked — "model/proposal settle claim" never reached author write.
    show = runner.invoke(
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
    today = runner.invoke(
        cli, ["today", "--project-id", DUSHI_LINGYI_PROJECT_ID]
    )
    after = asyncio.run(_open_ids())
    status, resolved_ch, resolved_vid = asyncio.run(_read_trace(_OVERDUE_ID))

    assert show.exit_code == 0, show.output
    assert today.exit_code == 0, today.output
    assert _OVERDUE_ID in show.output
    assert "promise_overdue: 1" in today.output
    assert after == before
    assert status == "overdue"
    assert resolved_ch is None
    assert resolved_vid is None


def test_confirm_promise_settles_and_backfills_trace(
    runner: CliRunner, settle_db: Path
) -> None:
    before = asyncio.run(_open_ids())
    assert _OVERDUE_ID in before
    assert _OTHER_ID in before

    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "promise",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--foreshadowing-id",
            _OVERDUE_ID,
            "--chapter",
            str(_RESOLVE_CHAPTER),
            "--evidence",
            _EVIDENCE,
        ],
    )
    assert result.exit_code == 0, result.output
    assert _OVERDUE_ID in result.output
    assert "resolved" in result.output.lower() or "已销账" in result.output
    assert _EVIDENCE in result.output or "evidence" in result.output.lower()

    status, resolved_ch, resolved_vid = asyncio.run(_read_trace(_OVERDUE_ID))
    assert status == "resolved"
    assert resolved_ch == _RESOLVE_CHAPTER
    assert resolved_vid == _RESOLVE_VERSION

    after = asyncio.run(_open_ids())
    assert _OVERDUE_ID not in after
    assert _OTHER_ID in after
    assert _PLANTED_ID in after

    show = runner.invoke(
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
    today = runner.invoke(
        cli, ["today", "--project-id", DUSHI_LINGYI_PROJECT_ID]
    )
    assert show.exit_code == 0, show.output
    assert today.exit_code == 0, today.output
    assert _OVERDUE_ID not in show.output
    assert "promise_overdue: 0" in today.output
    assert "promise_planted: 1" in today.output
    assert "promise_due: 1" in today.output


def test_confirm_promise_requires_evidence(
    runner: CliRunner, settle_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "promise",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--foreshadowing-id",
            _PLANTED_ID,
            "--chapter",
            str(_RESOLVE_CHAPTER),
            "--evidence",
            "   ",
        ],
    )
    assert result.exit_code == 1, result.output
    status, resolved_ch, _ = asyncio.run(_read_trace(_PLANTED_ID))
    assert status == "planted"
    assert resolved_ch is None
    assert _PLANTED_ID in asyncio.run(_open_ids())


def test_confirm_promise_missing_accepted_version_exits_2(
    runner: CliRunner, settle_db: Path
) -> None:
    """章无 accepted_version_id → exit 2；不写 resolved。"""
    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "promise",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--foreshadowing-id",
            _PLANTED_ID,
            "--chapter",
            "99",
            "--evidence",
            _EVIDENCE,
        ],
    )
    assert result.exit_code == 2, result.output
    status, resolved_ch, resolved_vid = asyncio.run(_read_trace(_PLANTED_ID))
    assert status == "planted"
    assert resolved_ch is None
    assert resolved_vid is None
    assert _PLANTED_ID in asyncio.run(_open_ids())


def test_confirm_promise_unknown_id_exits_1(
    runner: CliRunner, settle_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "promise",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--foreshadowing-id",
            "fs-does-not-exist",
            "--chapter",
            str(_RESOLVE_CHAPTER),
            "--evidence",
            _EVIDENCE,
        ],
    )
    assert result.exit_code == 1, result.output


def test_confirm_promise_missing_project_exits_1(
    runner: CliRunner, settle_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "promise",
            "--project-id",
            "no-such-project",
            "--foreshadowing-id",
            _OVERDUE_ID,
            "--chapter",
            str(_RESOLVE_CHAPTER),
            "--evidence",
            _EVIDENCE,
        ],
    )
    assert result.exit_code == 1, result.output


def test_confirm_promise_rejects_non_open(
    runner: CliRunner, settle_db: Path
) -> None:
    """Already resolved (or not in author open set) must not be re-settled."""
    asyncio.run(
        ForeshadowingRepository().update_status(
            _OTHER_ID,
            "resolved",
            resolved_chapter=_RESOLVE_CHAPTER,
            resolved_version_id=_RESOLVE_VERSION,
        )
    )
    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "promise",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--foreshadowing-id",
            _OTHER_ID,
            "--chapter",
            str(_RESOLVE_CHAPTER),
            "--evidence",
            _EVIDENCE,
        ],
    )
    assert result.exit_code == 1, result.output


def test_s3_uses_existing_foreshadowings_table_only(
    runner: CliRunner, settle_db: Path
) -> None:
    """PRD §6.6 验收 3 / S3：无第二伏笔表。"""

    async def _tables() -> set[str]:
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            rows = await cursor.fetchall()
        return {str(r[0]) for r in rows}

    names = asyncio.run(_tables())
    assert "foreshadowings" in names
    promise_like = {n for n in names if "promise" in n.lower()}
    assert promise_like == set()


def test_confirm_promise_persists_evidence(
    runner: CliRunner, settle_db: Path
) -> None:
    """task 228：人给的 --evidence 持久化到 resolved_evidence（审计留痕）。"""
    result = runner.invoke(
        cli,
        [
            "canon", "confirm", "promise",
            "--project-id", DUSHI_LINGYI_PROJECT_ID,
            "--foreshadowing-id", _OVERDUE_ID,
            "--chapter", str(_RESOLVE_CHAPTER),
            "--evidence", _EVIDENCE,
        ],
    )
    assert result.exit_code == 0, result.output

    async def _read_evidence() -> str | None:
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT resolved_evidence FROM foreshadowings WHERE foreshadowing_id = ?",
                (_OVERDUE_ID,),
            )
            row = await cursor.fetchone()
        return None if row is None else row[0]

    assert asyncio.run(_read_evidence()) == _EVIDENCE


def test_confirm_promise_concurrent_double_settle_guarded(
    settle_db: Path,
) -> None:
    """task 228：并发双销账同一伏笔——守卫与写入同事务，恰一个成功。"""
    from click import ClickException

    from songyan.cli.commands.canon_write import _confirm_promise

    async def _one(tag: str) -> str:
        return await _confirm_promise(
            project_id=DUSHI_LINGYI_PROJECT_ID,
            foreshadowing_id=_PLANTED_ID,
            chapter=_RESOLVE_CHAPTER,
            evidence=f"并发证据{tag}",
        )

    async def _race() -> tuple[list[str], list[BaseException]]:
        ok: list[str] = []
        errs: list[BaseException] = []
        results = await asyncio.gather(
            _one("A"), _one("B"), return_exceptions=True
        )
        for r in results:
            if isinstance(r, BaseException):
                errs.append(r)
            else:
                ok.append(r)
        return ok, errs

    ok, errs = asyncio.run(_race())
    assert len(ok) == 1, f"expect exactly one winner, got {ok}"
    assert len(errs) == 1
    assert isinstance(errs[0], ClickException)
    assert "不在开放承诺集" in str(errs[0])


async def test_migration_adds_resolved_evidence_column(
    tmp_path: Path,
) -> None:
    """task 228：旧库（无 resolved_evidence 列）跑迁移补列，既有行保持 NULL。"""
    import aiosqlite

    from songyan.db.migrations import init_schema, run_migrations

    db_path = tmp_path / "old-evidence.db"
    await init_schema(str(db_path))
    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute("DROP TABLE foreshadowings")
        await conn.execute(
            """CREATE TABLE foreshadowings (
                foreshadowing_id        TEXT PRIMARY KEY,
                project_id              TEXT NOT NULL,
                description             TEXT NOT NULL,
                planted_in_chapter      INTEGER NOT NULL,
                expected_resolve_chapter INTEGER,
                status                  TEXT DEFAULT 'planted',
                lifecycle_status        TEXT DEFAULT 'active',
                source_version_id       TEXT NOT NULL,
                created_at              TEXT DEFAULT (datetime('now'))
            )"""
        )
        await conn.execute(
            "INSERT INTO foreshadowings ("
            "foreshadowing_id, project_id, description, planted_in_chapter,"
            " status, source_version_id"
            ") VALUES ('fs-old', 'proj-1', '旧伏笔', 1, 'resolved', 'v-old')"
        )
        await conn.commit()

        await run_migrations(conn)
        await conn.commit()

        cursor = await conn.execute("PRAGMA table_info(foreshadowings)")
        columns = {row[1] for row in await cursor.fetchall()}
        assert "resolved_evidence" in columns

        cursor = await conn.execute(
            "SELECT resolved_evidence FROM foreshadowings WHERE foreshadowing_id = 'fs-old'"
        )
        assert (await cursor.fetchone())[0] is None
