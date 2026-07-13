"""Tests for Task 145 — V6 Stage A metrics framework (orphan absolute + T7).

覆盖：orphan 分类计数（不变量 critical+recurring+other=total）、T7 写入侧速率、
渲染段与斜率、以及 metrics CLI 端到端（隔离 DB）。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.config import settings
from songyan.db.continuity_repo import (
    ContinuityReportRepository,
    SettingTrackingRepository,
)
from songyan.db.repository import ProjectRepository
from songyan.evals.db_metrics import (
    collect_new_critical_rate,
    collect_orphan_metrics,
    linear_slope,
    render_orphan_section,
)
from songyan.models import (
    ContinuityReport,
    OrphanedSetting,
    ProjectSetting,
)

pytestmark = pytest.mark.performance

PID = "proj-145"


async def _seed_project() -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), PID
    )


def _orphan(key: str, category: str, intro: int, last: int, up_to: int) -> OrphanedSetting:
    return OrphanedSetting(
        tracking_id=f"t-{key}",
        setting_key=key,
        setting_name=key,
        introduced_in_chapter=intro,
        last_mentioned_chapter=last,
        chapters_since_mention=up_to - last,
        category=category,
    )


async def _seed_report(chapter: int, orphans: list[OrphanedSetting]) -> None:
    await ContinuityReportRepository().create(
        ContinuityReport(
            report_id=f"rpt-{chapter}",
            project_id=PID,
            checked_up_to_chapter=chapter,
            orphaned_settings=orphans,
            overall_health_score=9.0,
        )
    )


async def _seed_setting(key: str, category: str, intro: int) -> None:
    await SettingTrackingRepository().create(
        tracking_id=f"st-{key}",
        project_id=PID,
        setting_key=key,
        setting_name=key,
        description="",
        introduced_in_chapter=intro,
        category=category,
    )


# --------------------------------------------------------------------------- #
# orphan metrics
# --------------------------------------------------------------------------- #
class TestOrphanMetrics:
    async def test_classification_invariant(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_report(3, [
            _orphan("a", "critical", 1, 1, 3),
            _orphan("b", "recurring", 1, 1, 3),
            _orphan("c", "background", 1, 1, 3),
            _orphan("d", "technical", 1, 1, 3),
        ])
        points = await collect_orphan_metrics(PID, 1, 10)
        assert len(points) == 1
        p = points[0]
        assert p.chapter == 3
        assert p.orphan_total == 4
        assert p.orphan_critical == 1
        assert p.orphan_recurring == 1
        assert p.orphan_other == 2  # background + technical
        # 不变量
        assert p.orphan_critical + p.orphan_recurring + p.orphan_other == p.orphan_total

    async def test_curve_and_slope(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_report(1, [_orphan("a", "background", 1, 1, 1)])
        await _seed_report(2, [_orphan(f"x{i}", "background", 1, 1, 2) for i in range(3)])
        await _seed_report(3, [_orphan(f"y{i}", "background", 1, 1, 3) for i in range(5)])
        points = await collect_orphan_metrics(PID, 1, 10)
        assert [p.orphan_total for p in points] == [1, 3, 5]
        slope = linear_slope([p.chapter for p in points], [float(p.orphan_total) for p in points])
        assert slope == 2.0  # +2/章

    async def test_latest_report_per_chapter(self, test_db: Path) -> None:
        await _seed_project()
        # 同章两条 report：取最后一条（更多 orphan）
        await _seed_report(5, [_orphan("a", "critical", 1, 1, 5)])
        await ContinuityReportRepository().create(
            ContinuityReport(
                report_id="rpt-5b", project_id=PID, checked_up_to_chapter=5,
                orphaned_settings=[
                    _orphan("a", "critical", 1, 1, 5),
                    _orphan("b", "critical", 2, 2, 5),
                ],
                overall_health_score=8.0,
            )
        )
        points = await collect_orphan_metrics(PID, 1, 10)
        assert len(points) == 1
        assert points[0].orphan_critical == 2

    async def test_empty(self, test_db: Path) -> None:
        await _seed_project()
        assert await collect_orphan_metrics(PID, 1, 10) == []
        assert "无 continuity_reports" in render_orphan_section([])


# --------------------------------------------------------------------------- #
# T7 new critical rate
# --------------------------------------------------------------------------- #
class TestCriticalRate:
    async def test_new_critical_per_chapter(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_setting("s1", "critical", 1)
        await _seed_setting("s2", "background", 1)
        await _seed_setting("s3", "critical", 2)
        await _seed_setting("s4", "critical", 2)
        await _seed_setting("s5", "technical", 3)
        points = await collect_new_critical_rate(PID, 1, 10)
        by_ch = {p.chapter: p for p in points}
        assert by_ch[1].new_critical == 1 and by_ch[1].new_total == 2
        assert by_ch[2].new_critical == 2 and by_ch[2].new_total == 2
        assert by_ch[3].new_critical == 0 and by_ch[3].new_total == 1

    async def test_empty(self, test_db: Path) -> None:
        await _seed_project()
        assert await collect_new_critical_rate(PID, 1, 10) == []


# --------------------------------------------------------------------------- #
# metrics CLI (isolated DB, sync test)
# --------------------------------------------------------------------------- #
def test_metrics_cli(tmp_path: Path) -> None:
    from songyan.cli.main import cli
    from songyan.db.migrations import init_schema

    db_file = tmp_path / "cli_metrics.db"
    orig_url = settings.database_url
    orig_mode = settings.checkpointer_mode
    settings.database_url = f"sqlite:///{db_file}"
    settings.checkpointer_mode = "memory"
    try:
        asyncio.run(init_schema(db_file))

        async def _seed() -> None:
            await _seed_project()
            await _seed_report(2, [_orphan("a", "critical", 1, 1, 2)])
            await _seed_setting("s1", "critical", 1)

        asyncio.run(_seed())

        out = tmp_path / "m.md"
        result = CliRunner().invoke(
            cli, ["metrics", "--project-id", PID, "--chapters", "1-5", "-o", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "orphan 绝对量" in content
        assert "每章新 critical 产生速率" in content
    finally:
        settings.database_url = orig_url
        settings.checkpointer_mode = orig_mode
