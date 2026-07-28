"""Task 193.t tests — overdue operational 消费侧 lifecycle 过滤.

冻结验收门口径（`list_overdue_unresolved` 全计 archived/dormant/active）不动；
operational 消费侧（continuity health / streak halt 的 `_find_overdue_foreshadowings`）
改用 lifecycle-aware 的 `list_overdue_actionable`（仅 `lifecycle_status='active'`）——
dormant（系统 >5 章逾期停放）与 archived（>15 章退役）不再产生停 run 的 P2 压力，
五门 overdue（five_gate 自有 SQL）与 vdim 冻结口径不受影响。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.agents.continuity_auditor._scanners import _find_overdue_foreshadowings
from songyan.db import ProjectRepository
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import ForeshadowingItem, ProjectSetting


@pytest.fixture
async def fs_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "fs193t.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


async def _seed_project(project_id: str = "p1") -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="wuxia", protagonist_name="顾长风"), project_id
    )


async def _seed_version(project_id: str = "p1") -> None:
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES ('v1', ?, 1, 1, 'accepted')""",
            (project_id,),
        )
        await conn.commit()


async def _plant(
    repo: ForeshadowingRepository,
    foreshadowing_id: str,
    *,
    status: str = "overdue",
    expected_resolve_chapter: int | None = 10,
) -> None:
    await repo.create(
        ForeshadowingItem(
            foreshadowing_id=foreshadowing_id,
            description=f"伏笔-{foreshadowing_id}",
            planted_in_chapter=1,
            expected_resolve_chapter=expected_resolve_chapter,
            status=status,
        ),
        "p1",
        "v1",
    )


async def _set_lifecycle(foreshadowing_id: str, lifecycle: str) -> None:
    async with get_db() as conn:
        await conn.execute(
            "UPDATE foreshadowings SET lifecycle_status = ? WHERE foreshadowing_id = ?",
            (lifecycle, foreshadowing_id),
        )
        await conn.commit()


async def _seed_three_lifecycle(repo: ForeshadowingRepository) -> None:
    await _seed_project("p1")
    await _seed_version("p1")
    await _plant(repo, "fs-active-overdue")
    await _plant(repo, "fs-dormant-overdue")
    await _set_lifecycle("fs-dormant-overdue", "dormant")
    await _plant(repo, "fs-archived-overdue")
    await _set_lifecycle("fs-archived-overdue", "archived")


class TestListOverdueActionable:
    async def test_returns_only_active_lifecycle(self, fs_db: Path) -> None:
        repo = ForeshadowingRepository()
        await _seed_three_lifecycle(repo)

        items = await repo.list_overdue_actionable("p1", up_to_chapter=50)
        ids = {fs.foreshadowing_id for fs in items}
        assert ids == {"fs-active-overdue"}

    async def test_frozen_sibling_unchanged(self, fs_db: Path) -> None:
        """冻结验收门口径的 list_overdue_unresolved 必须保持全计（172c.r）."""
        repo = ForeshadowingRepository()
        await _seed_three_lifecycle(repo)

        items = await repo.list_overdue_unresolved("p1", up_to_chapter=50)
        ids = {fs.foreshadowing_id for fs in items}
        assert ids == {
            "fs-active-overdue",
            "fs-dormant-overdue",
            "fs-archived-overdue",
        }

    async def test_excludes_resolved_future_and_unknown_horizon(
        self, fs_db: Path
    ) -> None:
        await _seed_project("p1")
        await _seed_version("p1")
        repo = ForeshadowingRepository()
        await _plant(repo, "fs-resolved", status="resolved")
        await _plant(repo, "fs-future", status="planted", expected_resolve_chapter=100)
        await _plant(repo, "fs-no-horizon", status="planted", expected_resolve_chapter=None)

        items = await repo.list_overdue_actionable("p1", up_to_chapter=50)
        assert items == []


class TestFindOverdueForeshadowingsOperationalScope:
    async def test_excludes_dormant_and_archived(self, fs_db: Path) -> None:
        """193.t：operational 口径只计 active overdue——dormant/archived 是
        生命周期调度器已停放/退役的条目，不应再产生停 run 的 P2 压力（192.ad）。"""
        repo = ForeshadowingRepository()
        await _seed_three_lifecycle(repo)
        await _plant(repo, "fs-resolved", status="resolved")

        result = await _find_overdue_foreshadowings("p1", 50, repo)
        ids = {fs.foreshadowing_id for fs in result}
        assert ids == {"fs-active-overdue"}
        for fs in result:
            assert fs.overdue_by == 50 - 10
