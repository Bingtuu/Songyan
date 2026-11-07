"""M2 锁定语义（tech-m2 §3.2 / §4.3.3 / B3）：结算声称的伏笔 resolve 只是提案。

``apply_settlement`` 不得在无 human confirm 时把伏笔移出作者路径 open 集；
``foreshadowings.status='resolved'`` 的唯一写径是 ``canon confirm promise``。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from structlog.testing import capture_logs

from songyan.agents.settlement_extractor import apply_settlement
from songyan.db import ProjectRepository
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import (
    ForeshadowingItem,
    ForeshadowingUpdate,
    ProjectSetting,
    StateSettlement,
)


@pytest.fixture
async def fs_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "fs_resolve_proposal.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


async def _seed_project(project_id: str = "p1") -> None:
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="wuxia",
            mode_id="webnovel",
            protagonist_name="顾长风",
        ),
        project_id,
    )


async def _seed_version(
    project_id: str = "p1", version_id: str = "v1"
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES (?, ?, ?, ?, ?)""",
            (version_id, project_id, 1, 1, "accepted"),
        )
        await conn.commit()


async def _plant(repo: ForeshadowingRepository, foreshadowing_id: str) -> None:
    await repo.create(
        ForeshadowingItem(
            foreshadowing_id=foreshadowing_id,
            description=f"伏笔-{foreshadowing_id}",
            planted_in_chapter=1,
            expected_resolve_chapter=10,
            status="planted",
        ),
        "p1",
        "v1",
    )


async def _read_status(foreshadowing_id: str) -> tuple[str, object, object]:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT status, resolved_chapter, resolved_version_id "
            "FROM foreshadowings WHERE foreshadowing_id = ?",
            (foreshadowing_id,),
        )
        row = await cursor.fetchone()
    return row[0], row[1], row[2]


def _resolve_settlement(foreshadowing_id: str) -> StateSettlement:
    return StateSettlement(
        foreshadowing_updates=[
            ForeshadowingUpdate(
                operation="resolve",
                foreshadowing_id=foreshadowing_id,
                description="回收",
                source_version_id="v1",
            )
        ]
    )


async def test_resolve_proposal_keeps_foreshadowing_in_open_set(
    fs_db: Path,
) -> None:
    """模型声称 resolve 后：status 不变、追溯列不回填、仍在 open 集。"""
    await _seed_project()
    await _seed_version()
    repo = ForeshadowingRepository()
    await _plant(repo, "fs-1")

    async with get_db() as conn:
        await apply_settlement(
            _resolve_settlement("fs-1"), "p1", 12, "v1", conn=conn
        )
        await conn.commit()

    status, resolved_chapter, resolved_version_id = await _read_status("fs-1")
    assert status in ("planted", "due", "overdue")
    assert resolved_chapter is None
    assert resolved_version_id is None
    open_ids = {fs.foreshadowing_id for fs in await repo.list_schedulable("p1")}
    assert "fs-1" in open_ids


async def test_resolve_proposal_is_recorded_for_human_review(fs_db: Path) -> None:
    """提案要留痕（日志事件 + 观察计数），人可据此刻意 confirm promise 销账。"""
    await _seed_project()
    await _seed_version()
    repo = ForeshadowingRepository()
    await _plant(repo, "fs-1")

    settlement = _resolve_settlement("fs-1")
    with capture_logs() as logs:
        async with get_db() as conn:
            await apply_settlement(settlement, "p1", 12, "v1", conn=conn)
            await conn.commit()

    assert settlement.observation_counts.get("foreshadowing_resolve_proposed") == 1
    assert any(
        log.get("event") == "settlement.foreshadowing_resolve_proposed"
        and log.get("foreshadowing_id") == "fs-1"
        and log.get("suggested_chapter") == 12
        for log in logs
    )
