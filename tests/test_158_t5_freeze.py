"""Task 158b T5 冻结判定测试.

用合成 run_db_metrics 样本验证 T5 尺寸/耗时红线与冻结建议分支。
"""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.run_158_ch1_ch100 as runner
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ProjectRepository
from songyan.db.run_db_metrics_repo import RunDbMetricsRepository
from songyan.models import ProjectRunState, ProjectSetting

PID = "proj-158-t5"


async def _seed_project() -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="scifi", protagonist_name="林渊"), PID
    )


async def _seed_run(run_id: str) -> None:
    await ProjectRunRepository().create(
        ProjectRunState(
            run_id=run_id,
            project_id=PID,
            chapter_range_start=1,
            chapter_range_end=100,
            current_chapter=1,
            status="running",
        )
    )


async def _create_samples(
    run_id: str, samples: list[tuple[int, int, float]]
) -> None:
    """samples: list of (chapter, db_size_mb, scan_latency_ms)."""
    repo = RunDbMetricsRepository()
    for ch, size_mb, scan_ms in samples:
        await repo.create(
            run_id=run_id,
            project_id=PID,
            chapter_number=ch,
            db_size_bytes=size_mb * 1024 * 1024,
            wal_size_bytes=0,
            page_count=max(size_mb * 1024 * 1024 // 4096, 1),
            page_size=4096,
            scan_latency_ms=scan_ms,
        )


class TestT5Freeze:
    async def test_insufficient_samples_undecided(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_run("run-insufficient")
        await _create_samples("run-insufficient", [(10, 100, 10.0)])

        t5 = await runner._evaluate_t5(PID, "run-insufficient")
        assert t5["sufficient"] is False
        assert t5["size_passed"] is None
        assert t5["latency_passed"] is None
        assert "样本不足" in t5["recommendation"]

    async def test_size_pass_latency_pass_maintain(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_run("run-pass")
        await _create_samples(
            "run-pass",
            [
                (10, 100, 10.0),
                (20, 150, 11.0),
                (30, 200, 12.0),
                (100, 299, 14.0),
            ],
        )

        t5 = await runner._evaluate_t5(PID, "run-pass")
        assert t5["sufficient"] is True
        assert t5["size_passed"] is True
        assert t5["latency_passed"] is True
        assert t5["db_size_mb"] == pytest.approx(299.0, abs=0.01)
        assert "维持" in t5["recommendation"]
        assert not t5["size_breach_chapters"]
        assert not t5["latency_breach_chapters"]

    async def test_size_breach_at_301mb(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_run("run-size-breach")
        await _create_samples(
            "run-size-breach",
            [
                (10, 100, 10.0),
                (20, 200, 12.0),
                (100, 301, 14.0),
            ],
        )

        t5 = await runner._evaluate_t5(PID, "run-size-breach")
        assert t5["sufficient"] is True
        assert t5["size_passed"] is False
        assert t5["latency_passed"] is True
        assert 100 in t5["size_breach_chapters"]
        assert "调整" in t5["recommendation"]

    async def test_latency_breach_at_1_6x(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_run("run-latency-breach")
        # 前 10 个样本建立 10ms 基线；1.5x = 15ms；第 11 个 16ms 破线
        samples = [(i * 10, 100, 10.0) for i in range(1, 11)]
        samples.append((100, 100, 16.0))
        await _create_samples("run-latency-breach", samples)

        t5 = await runner._evaluate_t5(PID, "run-latency-breach")
        assert t5["sufficient"] is True
        assert t5["size_passed"] is True
        assert t5["latency_passed"] is False
        assert 100 in t5["latency_breach_chapters"]
        assert "调整" in t5["recommendation"]

    async def test_latency_pass_at_1_4x(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_run("run-latency-pass")
        samples = [(i * 10, 100, 10.0) for i in range(1, 11)]
        samples.append((100, 100, 14.0))
        await _create_samples("run-latency-pass", samples)

        t5 = await runner._evaluate_t5(PID, "run-latency-pass")
        assert t5["sufficient"] is True
        assert t5["size_passed"] is True
        assert t5["latency_passed"] is True
        assert not t5["latency_breach_chapters"]

    async def test_baseline_uses_first_10_samples(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_run("run-baseline-10")
        samples = [(i * 10, 100, 10.0) for i in range(1, 11)]
        samples.append((100, 100, 15.1))  # 基线 10ms，1.5x=15ms，15.1 破线
        await _create_samples("run-baseline-10", samples)

        t5 = await runner._evaluate_t5(PID, "run-baseline-10")
        assert t5["baseline_ms"] == pytest.approx(10.0, abs=0.01)
        assert t5["latency_passed"] is False

    async def test_latency_no_baseline_when_zero(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_run("run-zero-baseline")
        # 如果 scan_latency_ms 为 0，基线为 0，不应误判红线
        await _create_samples(
            "run-zero-baseline",
            [
                (10, 100, 0.0),
                (20, 100, 0.0),
                (30, 100, 0.0),
            ],
        )

        t5 = await runner._evaluate_t5(PID, "run-zero-baseline")
        assert t5["sufficient"] is True
        # baseline_ms == 0 时 check_t5_latency_redline 返回 False
        assert t5["latency_passed"] is True
