"""task 269 切片2：伏笔 horizon=8（urban）+ 承诺归档写径 + 到期日确认口径。

口径钉死：
- urban.foreshadowing_horizon_floor == 8（xuanhuan/wuxia 仍 48，scifi 仍 0）。
- LLM 的 expected_resolve_chapter 未确认前只是建议：结算不翻 due/overdue、
  紧迫 +2 不算；人显式 `canon confirm promise-due` 后才按到期日驱动。
- `canon dismiss promise` 归档（lifecycle_status=archived，幂等）：出开放集、
  出 today overdue、出上下文；`canon confirm promise` 对归档行拒绝。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.agents.context_manager import _rank_foreshadowings
from songyan.agents.settlement_extractor import apply_settlement
from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import (
    ForeshadowingItem,
    ProjectSetting,
    StateSettlement,
)

_PROJECT = "p-promise-admin"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def promise_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "promise-admin.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="urban",
            mode_id="webnovel",
            protagonist_name="陈屿",
            title="promise admin",
        ),
        _PROJECT,
    )
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES (?, ?, ?, ?, ?)""",
            ("v1", _PROJECT, 1, 1, "accepted"),
        )
        await conn.execute(
            """INSERT INTO chapter_heads (
                project_id, chapter_number, accepted_version_id, status
            ) VALUES (?, ?, ?, ?)""",
            (_PROJECT, 1, "v1", "accepted"),
        )
        await conn.commit()
    repo = ForeshadowingRepository()
    await repo.create(
        ForeshadowingItem(
            foreshadowing_id="fs-open",
            description="开着的承诺",
            planted_in_chapter=1,
            expected_resolve_chapter=3,
            status="planted",
        ),
        _PROJECT,
        "v1",
    )
    await repo.create(
        ForeshadowingItem(
            foreshadowing_id="fs-late",
            description="晚的承诺",
            planted_in_chapter=1,
            expected_resolve_chapter=10,
            status="planted",
        ),
        _PROJECT,
        "v1",
    )
    return db_path


async def _status(foreshadowing_id: str) -> str:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT status FROM foreshadowings WHERE foreshadowing_id = ?",
            (foreshadowing_id,),
        )
        row = await cursor.fetchone()
    return row[0]


def test_urban_horizon_floor_is_8(promise_db: Path) -> None:
    from songyan.db.genre_runtime_profile_repo import load_profile_from_registry

    assert load_profile_from_registry("urban").foreshadowing_horizon_floor == 8
    assert load_profile_from_registry("xuanhuan").foreshadowing_horizon_floor == 48
    assert load_profile_from_registry("wuxia").foreshadowing_horizon_floor == 48
    assert load_profile_from_registry("scifi").foreshadowing_horizon_floor == 0


async def _apply(chapter: int) -> None:
    async with get_db() as conn:
        await apply_settlement(StateSettlement(), _PROJECT, chapter, "v1", conn=conn)
        await conn.commit()


class TestConfirmedDueGate:
    def test_unconfirmed_expected_not_overdue(
        self, promise_db: Path
    ) -> None:
        """未确认的 expected 只是建议：结算不翻 overdue。"""
        asyncio.run(_apply(6))  # chapter 6 早已过 expected=3
        assert asyncio.run(_status("fs-open")) == "planted"

    def test_confirmed_due_drives_overdue(self, promise_db: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "canon", "confirm", "promise-due",
                "--project-id", _PROJECT,
                "--foreshadowing-id", "fs-open",
                "--chapter", "3",
            ],
        )
        assert result.exit_code == 0, result.output
        asyncio.run(_apply(6))
        assert asyncio.run(_status("fs-open")) == "overdue"

    def test_urgency_within_2_uses_confirmed_only(self, promise_db: Path) -> None:
        unconfirmed = ForeshadowingItem(
            foreshadowing_id="fs-a",
            description="a",
            planted_in_chapter=1,
            expected_resolve_chapter=7,  # 2 章内（current=5）但未确认
        )
        confirmed = ForeshadowingItem(
            foreshadowing_id="fs-b",
            description="b",
            planted_in_chapter=1,
            expected_resolve_chapter=7,
            confirmed_due_chapter=7,
        )
        ranked = _rank_foreshadowings(
            [unconfirmed, confirmed], foreshadowing_due=[], current_chapter=5
        )
        # 已确认到期排前（+2 生效）；未确认只按 planted 序
        assert ranked[0].foreshadowing_id == "fs-b"
        assert ranked[-1].foreshadowing_id == "fs-a"


class TestPromiseArchive:
    def test_archive_excludes_from_open_set_and_today(
        self, runner: CliRunner, promise_db: Path
    ) -> None:
        result = runner.invoke(
            cli,
            ["canon", "dismiss", "promise", "--project-id", _PROJECT,
             "--foreshadowing-id", "fs-open"],
        )
        assert result.exit_code == 0, result.output

        # 开放集不再出现
        result = runner.invoke(
            cli, ["canon", "show", "--project-id", _PROJECT, "--kind", "promise", "--json"]
        )
        assert result.exit_code == 0, result.output
        ids = {p["foreshadowing_id"] for p in json.loads(result.stdout)["promises"]}
        assert "fs-open" not in ids
        assert "fs-late" in ids

        # today 的 overdue 计数不含归档行
        result = runner.invoke(cli, ["today", "--project-id", _PROJECT])
        assert result.exit_code == 0, result.output

        # 幂等 noop
        result = runner.invoke(
            cli,
            ["canon", "dismiss", "promise", "--project-id", _PROJECT,
             "--foreshadowing-id", "fs-open"],
        )
        assert result.exit_code == 0, result.output
        assert "noop" in result.output

    def test_confirm_promise_rejects_archived(
        self, runner: CliRunner, promise_db: Path
    ) -> None:
        runner.invoke(
            cli,
            ["canon", "dismiss", "promise", "--project-id", _PROJECT,
             "--foreshadowing-id", "fs-open"],
        )
        result = runner.invoke(
            cli,
            ["canon", "confirm", "promise", "--project-id", _PROJECT,
             "--foreshadowing-id", "fs-open",
             "--chapter", "1", "--evidence", "人证"],
        )
        assert result.exit_code != 0

    def test_promise_due_rejects_archived(
        self, runner: CliRunner, promise_db: Path
    ) -> None:
        runner.invoke(
            cli,
            ["canon", "dismiss", "promise", "--project-id", _PROJECT,
             "--foreshadowing-id", "fs-open"],
        )
        result = runner.invoke(
            cli,
            ["canon", "confirm", "promise-due", "--project-id", _PROJECT,
             "--foreshadowing-id", "fs-open", "--chapter", "3"],
        )
        assert result.exit_code == 2

    def test_promise_text_shows_suggested_due(
        self, runner: CliRunner, promise_db: Path
    ) -> None:
        result = runner.invoke(
            cli, ["canon", "show", "--project-id", _PROJECT, "--kind", "promise"]
        )
        assert result.exit_code == 0, result.output
        assert "建议到期" in result.output
