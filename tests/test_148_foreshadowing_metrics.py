"""Tests for Task 148 — arc foreshadowing fulfillment + long-range ledger.

覆盖：弧级兑现率、真兑现(resolved) vs 逾期归档(abandoned) 区分、无弧散点、
arc_plans 空优雅降级、长程台账 span 与被遗忘标记。
"""

from __future__ import annotations

from pathlib import Path

from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.evals.db_metrics import (
    collect_arc_fulfillment,
    collect_long_range_ledger,
    render_arc_fulfillment_section,
)
from songyan.models import ArcPlan, ForeshadowingItem, ProjectSetting

PID = "proj-148"


async def _seed_project() -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), PID
    )


async def _add_arc(index: int, start: int, end: int) -> None:
    await NarrativeRepository().add_arc_plan(
        ArcPlan(arc_id=f"{PID}-arc{index}", project_id=PID, arc_index=index,
                start_chapter=start, end_chapter=end, is_mainline=True)
    )


async def _add_fs(
    fid: str, planted: int, status: str, *,
    expected: int | None = None, lifecycle: str = "active",
) -> None:
    """建伏笔并按需设置 status/lifecycle_status（后者需直改，因模型不带该列）."""
    from songyan.db.connection import get_db
    async with get_db() as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES (?, ?, ?, ?, ?)""",
            ("v1", PID, planted, 1, "accepted"),
        )
        await conn.commit()
    await ForeshadowingRepository().create(
        ForeshadowingItem(
            foreshadowing_id=fid, description=f"fs {fid}",
            planted_in_chapter=planted, expected_resolve_chapter=expected,
            status=status,
        ),
        PID,
        "v1",
    )
    if lifecycle != "active":
        from songyan.db.connection import get_db
        async with get_db() as conn:
            await conn.execute(
                "UPDATE foreshadowings SET lifecycle_status = ? WHERE foreshadowing_id = ?",
                (lifecycle, fid),
            )
            await conn.commit()


class TestArcFulfillment:
    async def test_rate_and_abandoned_distinction(self, test_db: Path) -> None:
        await _seed_project()
        await _add_arc(0, 1, 10)
        # arc0 内：resolved(active) + resolved(archived 仍兑现) + overdue+archived(abandoned) + open
        await _add_fs("f1", 3, "resolved")
        await _add_fs("f2", 4, "resolved", lifecycle="archived")
        await _add_fs("f3", 5, "overdue", lifecycle="archived")
        await _add_fs("f4", 6, "planted")
        arcs = await collect_arc_fulfillment(PID)
        assert len(arcs) == 1
        a = arcs[0]
        assert a.total == 4
        assert a.resolved == 2          # archived+resolved 仍算兑现
        assert a.abandoned == 1         # overdue+archived
        assert a.fulfillment_rate == 0.5

    async def test_scatter_outside_arcs(self, test_db: Path) -> None:
        await _seed_project()
        await _add_arc(0, 1, 10)
        await _add_fs("f1", 3, "resolved")
        await _add_fs("f_out", 99, "resolved")  # 落在弧外 → 不计入 arc0
        arcs = await collect_arc_fulfillment(PID)
        assert arcs[0].total == 1

    async def test_no_arc_plans_graceful(self, test_db: Path) -> None:
        await _seed_project()
        await _add_fs("f1", 3, "resolved")
        assert await collect_arc_fulfillment(PID) == []
        assert "无 arc_plans" in render_arc_fulfillment_section([])


class TestLongRangeLedger:
    async def test_ledger_excludes_resolved_marks_abandoned(self, test_db: Path) -> None:
        await _seed_project()
        await _add_fs("f1", 3, "resolved")                       # 排除
        await _add_fs("f2", 5, "planted", expected=8)            # 未兑现，未遗忘
        await _add_fs("f3", 6, "overdue", lifecycle="dormant")   # 逾期归档 abandoned
        ledger = await collect_long_range_ledger(PID, current_chapter=20)
        ids = {r.foreshadowing_id: r for r in ledger}
        assert "f1" not in ids
        assert ids["f2"].is_abandoned is False and ids["f2"].span == 15
        assert ids["f3"].is_abandoned is True

    async def test_empty(self, test_db: Path) -> None:
        await _seed_project()
        assert await collect_long_range_ledger(PID, 10) == []
