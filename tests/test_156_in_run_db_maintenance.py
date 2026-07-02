"""Tests for Task 156 — in-run DB maintenance."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from songyan.config import settings
from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.migrations import init_schema
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ProjectRepository
from songyan.db.run_db_metrics_repo import RunDbMetricsRepository
from songyan.evals.db_maintenance_metrics import (
    DbSizeMetrics,
    check_t5_latency_redline,
    check_t5_size_redline,
    collect_db_size_metrics,
    measure_continuity_scan_latency,
)
from songyan.models import ProjectRunState, ProjectSetting
from songyan.workflows._helpers import new_id
from songyan.workflows.phase2_graph import (
    _DB_MAINTENANCE_INTERVAL,
    _run_db_maintenance,
    run_project_pipeline,
)


@pytest.fixture
async def isolated_db(tmp_path: Path) -> Path:
    """创建独立临时库并初始化 schema，供 DB 维护测试."""
    db_file = tmp_path / "maintenance.db"
    original_url = settings.database_url
    settings.database_url = f"sqlite:///{db_file}"
    await init_schema(db_file)
    yield db_file
    settings.database_url = original_url


async def _seed_setting_tracking(db_file: Path, project_id: str, count: int) -> None:
    """向 setting_tracking 写入若干记录，供扫描耗时测试."""
    repo = SettingTrackingRepository()
    for i in range(count):
        await repo.create(
            tracking_id=new_id("st"),
            project_id=project_id,
            setting_key=f"setting-{i}",
            setting_name=f"Setting {i}",
            description="test",
            introduced_in_chapter=1,
            source_version_id=None,
            category="background",
            status="active",
        )


async def _create_run_record(run_id: str, project_id: str) -> None:
    """创建 projects + project_runs 记录，满足外键约束."""
    project = ProjectSetting(
        title="Maintenance Test",
        genre_id="urban",
        mode_id="webnovel",
        protagonist_name="Test",
    )
    await ProjectRepository().create(project, project_id)
    run_state = ProjectRunState(
        run_id=run_id,
        project_id=project_id,
        chapter_range_start=1,
        chapter_range_end=20,
        current_chapter=10,
        status="running",
    )
    await ProjectRunRepository().create(run_state)


class TestDbSizeTelemetry:
    async def test_collect_db_size_metrics(self, isolated_db: Path) -> None:
        """collect_db_size_metrics 返回与文件系统一致的尺寸."""
        # 写一点数据让库文件非空
        await _seed_setting_tracking(isolated_db, "proj-156", 3)

        metrics = await collect_db_size_metrics()

        assert metrics.db_size_bytes == isolated_db.stat().st_size
        wal_path = isolated_db.with_suffix(isolated_db.suffix + "-wal")
        assert metrics.wal_size_bytes == (
            wal_path.stat().st_size if wal_path.exists() else 0
        )
        assert metrics.page_count > 0
        assert metrics.page_size > 0


class TestContinuityScanLatency:
    async def test_measure_latency_positive(self, isolated_db: Path) -> None:
        """measure_continuity_scan_latency 返回正耗时."""
        await _seed_setting_tracking(isolated_db, "proj-156", 5)

        elapsed_ms = await measure_continuity_scan_latency("proj-156", up_to_chapter=10)

        assert elapsed_ms >= 0.0


class TestT5Redline:
    def test_size_redline_over_threshold(self) -> None:
        metrics = DbSizeMetrics(
            db_size_bytes=301 * 1024 * 1024,
            wal_size_bytes=0,
            page_count=1,
            page_size=4096,
        )
        assert check_t5_size_redline(metrics) is True

    def test_size_redline_under_threshold(self) -> None:
        metrics = DbSizeMetrics(
            db_size_bytes=100 * 1024 * 1024,
            wal_size_bytes=0,
            page_count=1,
            page_size=4096,
        )
        assert check_t5_size_redline(metrics) is False

    def test_latency_redline_over_baseline(self) -> None:
        assert check_t5_latency_redline(16.0, baseline_ms=10.0) is True

    def test_latency_redline_under_baseline(self) -> None:
        assert check_t5_latency_redline(14.0, baseline_ms=10.0) is False

    def test_latency_redline_no_baseline(self) -> None:
        assert check_t5_latency_redline(100.0, baseline_ms=0.0) is False


class TestRunDbMaintenance:
    async def test_persists_sample(self, isolated_db: Path) -> None:
        """_run_db_maintenance 把遥测样本写入 run_db_metrics."""
        await _seed_setting_tracking(isolated_db, "proj-156", 3)
        run_id = new_id("run")
        await _create_run_record(run_id, "proj-156")

        await _run_db_maintenance(run_id, "proj-156", chapter_number=10)

        samples = await RunDbMetricsRepository().list_by_run(run_id)
        assert len(samples) == 1
        assert samples[0]["chapter_number"] == 10
        assert samples[0]["db_size_bytes"] > 0
        assert samples[0]["scan_latency_ms"] >= 0.0

    async def test_non_blocking_on_failure(self, isolated_db: Path) -> None:
        """维护内部抛异常时不中断调用方."""
        with patch(
            "songyan.workflows.phase2_graph.collect_db_size_metrics",
            side_effect=RuntimeError("boom"),
        ):
            await _run_db_maintenance(new_id("run"), "proj-156", chapter_number=10)

    async def test_wal_checkpoint_truncate(self, isolated_db: Path) -> None:
        """维护后 WAL 文件应被截断（或原本就不存在）."""
        await _seed_setting_tracking(isolated_db, "proj-156", 10)
        run_id = new_id("run")
        await _create_run_record(run_id, "proj-156")

        await _run_db_maintenance(run_id, "proj-156", chapter_number=10)

        wal_path = isolated_db.with_suffix(isolated_db.suffix + "-wal")
        # checkpoint(TRUNCATE) 后 WAL 应为 0 字节或不存在
        if wal_path.exists():
            assert wal_path.stat().st_size == 0


class TestPeriodicTrigger:
    async def test_maintenance_triggered_every_interval(self, isolated_db: Path) -> None:
        """主循环每 _DB_MAINTENANCE_INTERVAL 章触发一次维护，收尾再触发一次."""
        calls: list[int] = []

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            return {
                "success": True,
                "summary_text": f"summary-{kwargs['chapter_number']}",
                "error": None,
                "final_state": {},
                "final_version_id": new_id("v"),
                "budget_used": 0.8,
                "context_emergency": False,
                "quality_gate_passed": True,
                "settlement_success": True,
                "summary_success": True,
                "continuity_health_severity": None,
                "gate_triggered": False,
                "gate_reasons": [],
                "updated_min_health_score": None,
            }

        async def _capture_maintenance(
            run_id: str, project_id: str, chapter_number: int, *, final: bool = False
        ) -> None:
            calls.append(chapter_number)

        with (
            patch(
                "songyan.workflows.phase2_graph._run_single_chapter",
                side_effect=_fake_run,
            ),
            patch(
                "songyan.workflows.phase2_graph._upsert_quality_debt",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows.phase2_graph._run_db_maintenance",
                side_effect=_capture_maintenance,
            ),
            patch(
                "songyan.workflows.phase2_graph._save_run_state",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows.phase2_graph.reset_checkpointer",
                new_callable=AsyncMock,
            ),
        ):
            await run_project_pipeline(
                project_id="proj-156",
                chapter_range=(1, _DB_MAINTENANCE_INTERVAL + 5),
                auto_confirm=True,
            )

        # 应在第 10 章触发一次，收尾（第 15 章）再触发一次
        assert _DB_MAINTENANCE_INTERVAL in calls
        assert (_DB_MAINTENANCE_INTERVAL + 5) in calls
