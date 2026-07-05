"""Task 168b: adaptive gate window aggregation and reporting tests."""

from __future__ import annotations

from pathlib import Path

from songyan.db.adaptive_gate_repo import AdaptiveGateSignalRepository
from songyan.db.repository import ProjectRepository
from songyan.evals.adaptive_gate import (
    build_adaptive_gate_data_plane_report,
    build_adaptive_gate_signal_snapshot,
    collect_adaptive_gate_windows,
    refresh_adaptive_gate_signal_snapshots,
    render_adaptive_gate_data_plane_section,
)
from songyan.evals.db_metrics import render_stage_a_metrics
from songyan.models import ProjectSetting

PID = "proj-168b"


async def _seed_project(project_id: str = PID) -> str:
    await ProjectRepository().create(
        ProjectSetting(title=project_id, genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )
    return project_id


async def _upsert_snapshot(
    chapter: int,
    *,
    project_id: str = PID,
    continuity: dict | None = None,
    quality: dict | None = None,
    literary: dict | None = None,
    cleanliness: dict | None = None,
    context: dict | None = None,
    narrative: dict | None = None,
    source_status: dict | None = None,
) -> None:
    await AdaptiveGateSignalRepository().upsert(
        build_adaptive_gate_signal_snapshot(
            project_id=project_id,
            chapter_number=chapter,
            continuity=continuity,
            quality=quality,
            literary=literary,
            cleanliness=cleanliness,
            context=context,
            narrative=narrative,
            source_status=source_status,
        )
    )


class TestAdaptiveGateWindowAggregation:
    async def test_empty_snapshot_report_is_non_throwing(self, test_db: Path) -> None:
        await _seed_project()

        report = await build_adaptive_gate_data_plane_report(PID, 1, 5)
        rendered = render_adaptive_gate_data_plane_section(report)

        assert report.snapshot_count == 0
        assert report.windows == []
        assert "无 adaptive_gate_signal_snapshots" in rendered

    async def test_insufficient_source_is_not_used_for_window_math(
        self,
        test_db: Path,
    ) -> None:
        await _seed_project()
        for chapter in range(1, 6):
            await _upsert_snapshot(
                chapter,
                continuity={"health_score": 1.0, "p1_count": 99},
                source_status={"continuity": "insufficient"},
            )

        windows = await collect_adaptive_gate_windows(PID, 1, 5, window=5)

        assert len(windows) == 1
        assert windows[0].health_min is None
        assert windows[0].p1_median is None
        assert windows[0].source_status_counts["continuity"]["insufficient"] == 5

    async def test_w5_continuity_orphan_and_t7_window(self, test_db: Path) -> None:
        await _seed_project()
        for chapter in range(1, 6):
            await _upsert_snapshot(
                chapter,
                continuity={
                    "health_score": float(11 - chapter),
                    "p1_count": chapter - 1,
                    "p2_count": 2,
                    "orphan_total": chapter,
                    "new_critical_count": chapter - 1,
                },
            )

        window = (await collect_adaptive_gate_windows(PID, 1, 5, window=5))[0]

        assert window.health_min == 6.0
        assert window.health_median == 8.0
        assert window.p1_median == 2.0
        assert window.orphan_slope == 1.0
        assert window.orphan_delta == 4
        assert window.new_critical_mean == 2.0

    async def test_quality_schedule_and_context_ratios(self, test_db: Path) -> None:
        await _seed_project()
        for chapter in range(1, 6):
            await _upsert_snapshot(
                chapter,
                quality={
                    "quality_gate_passed": chapter not in {2, 4},
                    "degraded_accept": chapter in {1, 2},
                    "convergence_failed": chapter == 3,
                    "qg_false": chapter in {2, 4},
                },
                context={
                    "context_emergency": chapter in {4, 5},
                    "budget_used": chapter / 10,
                    "db_size_bytes": chapter * 1024 * 1024,
                    "scan_latency_ms": float(chapter * 2),
                },
                narrative={
                    "schedule_injected_count": 1 if chapter <= 4 else 0,
                    "schedule_satisfied_count": 1 if chapter in {1, 2, 3} else 0,
                    "schedule_missed_count": 1 if chapter == 4 else 0,
                    "overdue_foreshadowing_count": 1 if chapter in {4, 5} else 0,
                },
            )

        window = (await collect_adaptive_gate_windows(PID, 1, 5, window=5))[0]

        assert window.degraded_ratio == 0.4
        assert window.convergence_ratio == 0.2
        assert window.qg_false_ratio == 0.4
        assert window.context_emergency_ratio == 0.4
        assert window.budget_used_max == 0.5
        assert window.db_size_max_mb == 5.0
        assert window.scan_latency_max_ms == 10.0
        assert window.schedule_hit_rate == 0.75
        assert window.schedule_missed_rate == 0.25
        assert window.schedule_overdue_rate == 0.2

    async def test_literary_cleanliness_and_rendering(self, test_db: Path) -> None:
        await _seed_project()
        for chapter in range(1, 6):
            await _upsert_snapshot(
                chapter,
                literary={
                    "literary_quality_score": 7.0,
                    "character_autonomy_score": 6.0,
                    "conceptual_grounding_score": 5.0 + chapter / 10,
                    "fissure_preservation_score": 8.0,
                },
                cleanliness={
                    "meta_tag_leak_count": 0,
                    "duplicate_paragraph_count": 1 if chapter == 3 else 0,
                    "timeline_conflict_count": 1,
                },
                source_status={"cleanliness": "observation"},
            )

        report = await build_adaptive_gate_data_plane_report(PID, 1, 5)
        rendered = render_adaptive_gate_data_plane_section(report)
        window = report.windows[0]

        assert window.literary_quality_mean == 7.0
        assert window.conceptual_grounding_mean == 5.3
        assert window.duplicate_paragraph_total == 1
        assert window.timeline_conflict_total == 5
        assert "只供 Task 169 判定使用" in rendered
        assert "不输出 pass/fail/halt" in rendered


class TestAdaptiveGateRefreshAndMetrics:
    async def test_refresh_creates_missing_snapshots_without_sources(
        self,
        test_db: Path,
    ) -> None:
        await _seed_project()

        count = await refresh_adaptive_gate_signal_snapshots(PID, 1, 3)
        rows = await AdaptiveGateSignalRepository().list_range(PID, 1, 3)

        assert count == 3
        assert [row.chapter_number for row in rows] == [1, 2, 3]
        assert all(
            status == "missing"
            for row in rows
            for status in row.source_status.values()
        )

    async def test_stage_metrics_renders_adaptive_gate_section(
        self,
        test_db: Path,
    ) -> None:
        await _seed_project()

        rendered = await render_stage_a_metrics(PID, 1, 5)

        assert "自适应门禁数据面" in rendered
        assert "只供 Task 169 判定使用" in rendered
