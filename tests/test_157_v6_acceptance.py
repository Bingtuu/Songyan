"""Task 157a: V6 验收判据 harness Layer 2 测试.

用隔离临时 SQLite + 合成数据钉死 T1-T8 及三态语义；不跑 LLM。
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from songyan.db.continuity_repo import (
    ContinuityReportRepository,
    SettingTrackingRepository,
)
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.db.run_db_metrics_repo import RunDbMetricsRepository
from songyan.evals.db_metrics import ChapterRunLog
from songyan.evals.v6_acceptance import (
    check_t1,
    check_t2,
    check_t3_t8,
    check_t4,
    check_t5,
    check_t6a,
    check_t6b,
    check_t6c_attribution,
    check_t6c_observation,
    check_t7_rate,
    evaluate_v6_acceptance,
    render_v6_acceptance_section,
)
from songyan.models import (
    ChapterHead,
    ChapterVersion,
    ContinuityReport,
    LiteraryAuditResult,
    OrphanedSetting,
    PlotThread,
    ProjectSetting,
)

PROJECT_ID = "test-157"


async def _ensure_project(project_id: str) -> None:
    repo = ProjectRepository()
    existing = await repo.get(project_id)
    if existing is not None:
        return
    await repo.create(
        ProjectSetting(
            title=f"Test {project_id}",
            genre_id="urban",
            protagonist_name="Tester",
        ),
        project_id=project_id,
    )


async def _make_accepted_head(project_id: str, chapter: int, status: str = "accepted") -> None:
    await _ensure_project(project_id)
    version_id = f"v_{project_id}_{chapter}"
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter,
            version_number=1,
            version_type="accepted" if status == "accepted" else "draft",
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=chapter,
            current_version_id=version_id,
            accepted_version_id=version_id if status == "accepted" else None,
            status=status,
        )
    )


async def _make_orphan_report(
    project_id: str,
    chapter: int,
    total: int,
    critical: int = 0,
    health_score: float = 8.0,
) -> None:
    settings = [
        OrphanedSetting(
            tracking_id=f"os_{project_id}_{chapter}_{i}_{uuid.uuid4().hex[:6]}",
            setting_key=f"key_{chapter}_{i}",
            setting_name=f"name_{chapter}_{i}",
            introduced_in_chapter=chapter,
            last_mentioned_chapter=chapter,
            chapters_since_mention=0,
            category="critical" if i < critical else "background",
        )
        for i in range(total)
    ]
    await ContinuityReportRepository().create(
        ContinuityReport(
            report_id=f"rep_{project_id}_{chapter}_{uuid.uuid4().hex[:6]}",
            project_id=project_id,
            checked_up_to_chapter=chapter,
            orphaned_settings=settings,
            overall_health_score=health_score,
        )
    )


async def _make_critical_setting(
    project_id: str,
    chapter: int,
    idx: int,
    status: str = "active",
) -> None:
    await SettingTrackingRepository().create(
        tracking_id=f"st_{project_id}_{chapter}_{idx}",
        project_id=project_id,
        setting_key=f"setting_{chapter}_{idx}",
        setting_name=f"Setting {chapter}-{idx}",
        description="",
        introduced_in_chapter=chapter,
        source_version_id=f"v_{project_id}_{chapter}",
        category="critical",
        status=status,
    )


async def _make_observation(
    project_id: str,
    chapter: int,
    scores: dict[str, float],
) -> None:
    await _ensure_project(project_id)
    version_id = f"v_lit_{project_id}_{chapter}"
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter,
            version_number=2,
            version_type="accepted",
        )
    )
    await LiteraryObservationRepository().create(
        LiteraryAuditResult(
            literary_quality_score=scores.get("literary_quality_score", 0.0),
            character_autonomy_score=scores.get("character_autonomy_score", 0.0),
            conceptual_grounding_score=scores.get("conceptual_grounding_score", 0.0),
            fissure_preservation_score=scores.get("fissure_preservation_score", 0.0),
        ),
        observation_id=f"lit_{project_id}_{chapter}_{uuid.uuid4().hex[:6]}",
        version_id=version_id,
    )


async def _make_db_sample(
    run_id: str,
    project_id: str,
    chapter: int,
    db_size_bytes: int,
    scan_ms: float,
) -> None:
    await _ensure_project(project_id)
    await RunDbMetricsRepository().create(
        run_id=run_id,
        project_id=project_id,
        chapter_number=chapter,
        db_size_bytes=db_size_bytes,
        wal_size_bytes=0,
        page_count=db_size_bytes // 4096,
        page_size=4096,
        scan_latency_ms=scan_ms,
    )


def _make_run_log(
    chapter: int,
    *,
    degraded_accept: bool = False,
    convergence_failed: bool = False,
    quality_gate_passed: bool | None = True,
) -> ChapterRunLog:
    return ChapterRunLog(
        log_id=f"log_{chapter}",
        project_id=PROJECT_ID,
        chapter_number=chapter,
        started_at=datetime.now(),
        finished_at=datetime.now(),
        success=True,
        degraded_accept=degraded_accept,
        convergence_failed=convergence_failed,
        quality_gate_passed=quality_gate_passed,
    )


class TestT2Completion:
    async def test_all_accepted_pass(self, test_db) -> None:
        for ch in range(1, 51):
            await _make_accepted_head(PROJECT_ID, ch, "accepted")
        result = await check_t2(PROJECT_ID, 1, 50)
        assert result.passed is True
        assert result.measured == "50/50"

    async def test_missing_and_draft_fail(self, test_db) -> None:
        for ch in range(1, 50):
            await _make_accepted_head(PROJECT_ID, ch, "accepted")
        await _make_accepted_head(PROJECT_ID, 50, "draft")
        result = await check_t2(PROJECT_ID, 1, 50)
        assert result.passed is False
        assert "50" in result.detail

    async def test_no_heads_undecided(self, test_db) -> None:
        result = await check_t2(PROJECT_ID, 1, 10)
        assert result.passed is None
        assert result.sufficient is False


class TestT6aOrphanSlope:
    async def test_slope_below_threshold_pass(self, test_db) -> None:
        for ch in range(1, 11):
            await _make_orphan_report(PROJECT_ID, ch, total=ch * 3)
        result = await check_t6a(PROJECT_ID, 1, 10)
        assert result.passed is True
        assert result.measured == pytest.approx(3.0, abs=0.01)

    async def test_slope_above_threshold_fail(self, test_db) -> None:
        for ch in range(1, 11):
            await _make_orphan_report(PROJECT_ID, ch, total=ch * 4)
        result = await check_t6a(PROJECT_ID, 1, 10)
        assert result.passed is False
        assert result.measured == pytest.approx(4.0, abs=0.01)

    async def test_insufficient_points_undecided(self, test_db) -> None:
        await _make_orphan_report(PROJECT_ID, 1, total=1)
        result = await check_t6a(PROJECT_ID, 1, 1)
        assert result.passed is None
        assert result.sufficient is False


class TestT6bP1Orphan:
    async def test_all_zero_pass(self, test_db) -> None:
        for ch in range(1, 11):
            await _make_orphan_report(PROJECT_ID, ch, total=2, critical=0)
        result = await check_t6b(PROJECT_ID, 1, 10)
        assert result.passed is True
        assert result.measured == 0

    async def test_critical_breach_fail(self, test_db) -> None:
        for ch in range(1, 11):
            await _make_orphan_report(PROJECT_ID, ch, total=2, critical=0)
        await _make_orphan_report(PROJECT_ID, 5, total=2, critical=1)
        result = await check_t6b(PROJECT_ID, 1, 10)
        assert result.passed is False
        assert "5" in result.detail

    async def test_missing_report_undecided(self, test_db) -> None:
        for ch in range(1, 10):
            await _make_orphan_report(PROJECT_ID, ch, total=2, critical=0)
        result = await check_t6b(PROJECT_ID, 1, 10)
        assert result.passed is None
        assert result.sufficient is False


class TestT6cAttribution:
    async def test_attribution_pass(self, test_db) -> None:
        # orphan 斜率接近基线，要求 T7 降幅很小即可
        for ch in range(1, 11):
            await _make_orphan_report(PROJECT_ID, ch, total=round(6.0 * ch))
            await _make_critical_setting(PROJECT_ID, ch, 0)
        result = await check_t6c_attribution(PROJECT_ID, 1, 10)
        assert result.passed is True

    async def test_attribution_fail(self, test_db) -> None:
        # orphan 下降但 T7 没同步降
        for ch in range(1, 11):
            await _make_orphan_report(PROJECT_ID, ch, total=round(6.0 * ch))
        for ch in range(1, 11):
            for i in range(5):
                await _make_critical_setting(PROJECT_ID, ch, i)
        result = await check_t6c_attribution(PROJECT_ID, 1, 10)
        assert result.passed is False

    async def test_insufficient_undecided(self, test_db) -> None:
        await _make_orphan_report(PROJECT_ID, 1, total=1)
        result = await check_t6c_attribution(PROJECT_ID, 1, 1)
        assert result.passed is None
        assert result.sufficient is False


class TestT6cObservation:
    async def test_demoted_ratio(self, test_db) -> None:
        for ch in range(1, 11):
            await _make_critical_setting(PROJECT_ID, ch, 0, status="active")
            await _make_critical_setting(PROJECT_ID, ch, 1, status="candidate")
        result = await check_t6c_observation(PROJECT_ID, 1, 10)
        assert result.passed is None
        assert "50.0%" in result.measured


class TestT7Rate:
    async def test_rate_reported(self, test_db) -> None:
        for ch in range(1, 6):
            for i in range(2):
                await _make_critical_setting(PROJECT_ID, ch, i)
        result = await check_t7_rate(PROJECT_ID, 1, 5)
        assert result.passed is None
        assert result.measured == pytest.approx(2.0, abs=0.01)


class TestT3T8LiteraryTrend:
    async def test_no_breach(self, test_db) -> None:
        for ch in range(1, 16):
            await _make_observation(
                PROJECT_ID,
                ch,
                {
                    "literary_quality_score": 9.0,
                    "character_autonomy_score": 9.0,
                    "conceptual_grounding_score": 9.0,
                    "fissure_preservation_score": 9.0,
                },
            )
        result = await check_t3_t8(PROJECT_ID, 1, 15)
        assert result.passed is True

    async def test_breach_detected(self, test_db) -> None:
        for ch in range(1, 11):
            await _make_observation(
                PROJECT_ID,
                ch,
                {
                    "literary_quality_score": 10.0,
                    "character_autonomy_score": 10.0,
                    "conceptual_grounding_score": 10.0,
                    "fissure_preservation_score": 10.0,
                },
            )
        for ch in range(11, 16):
            await _make_observation(
                PROJECT_ID,
                ch,
                {
                    "literary_quality_score": 7.0,
                    "character_autonomy_score": 7.0,
                    "conceptual_grounding_score": 7.0,
                    "fissure_preservation_score": 7.0,
                },
            )
        result = await check_t3_t8(PROJECT_ID, 1, 15)
        assert result.passed is False
        assert result.measured != "none"


class TestT4QualityDebt:
    def test_pass(self) -> None:
        logs = [_make_run_log(ch) for ch in range(1, 51)]
        result = check_t4(logs)
        assert result.passed is True

    def test_degraded_breach(self) -> None:
        logs = [
            _make_run_log(ch, degraded_accept=(ch <= 11))
            for ch in range(1, 51)
        ]
        result = check_t4(logs)
        assert result.passed is False

    def test_convergence_breach(self) -> None:
        logs = [
            _make_run_log(ch, convergence_failed=(ch <= 6))
            for ch in range(1, 51)
        ]
        result = check_t4(logs)
        assert result.passed is False

    def test_insufficient(self) -> None:
        logs = [_make_run_log(ch) for ch in range(1, 10)]
        result = check_t4(logs)
        assert result.passed is None
        assert result.sufficient is False

    def test_no_logs(self) -> None:
        result = check_t4(None)
        assert result.passed is None


class TestT5DbMetrics:
    async def test_pass(self, test_db) -> None:
        run_id = "run_t5_pass"
        for ch in (10, 20, 30):
            await _make_db_sample(run_id, PROJECT_ID, ch, 100 * 1024 * 1024, 10.0)
        result = await check_t5(PROJECT_ID, run_id=run_id)
        assert result.passed is True

    async def test_size_breach(self, test_db) -> None:
        run_id = "run_t5_size"
        await _make_db_sample(run_id, PROJECT_ID, 10, 100 * 1024 * 1024, 10.0)
        await _make_db_sample(run_id, PROJECT_ID, 20, 301 * 1024 * 1024, 10.0)
        await _make_db_sample(run_id, PROJECT_ID, 30, 301 * 1024 * 1024, 10.0)
        result = await check_t5(PROJECT_ID, run_id=run_id)
        assert result.passed is False
        assert "尺寸" in result.detail

    async def test_latency_breach(self, test_db) -> None:
        run_id = "run_t5_latency"
        await _make_db_sample(run_id, PROJECT_ID, 10, 100 * 1024 * 1024, 10.0)
        await _make_db_sample(run_id, PROJECT_ID, 20, 100 * 1024 * 1024, 10.0)
        await _make_db_sample(run_id, PROJECT_ID, 30, 100 * 1024 * 1024, 100.0)
        result = await check_t5(PROJECT_ID, run_id=run_id)
        assert result.passed is False

    async def test_insufficient(self, test_db) -> None:
        result = await check_t5(PROJECT_ID, run_id="missing")
        assert result.passed is None
        assert result.sufficient is False


class TestT1MainlineThread:
    async def test_mainline_advanced_pass(self, test_db) -> None:
        await _ensure_project(PROJECT_ID)
        thread = PlotThread(
            thread_id="t1_main",
            project_id=PROJECT_ID,
            title="主线",
            description="",
            is_mainline=True,
            opened_chapter=5,
            expected_resolve_arc=1,
            status="advanced",
            last_status_chapter=10,
            last_status_version_id="v10",
        )
        await NarrativeRepository().add_thread(thread)
        result = await check_t1(PROJECT_ID, 1, 15)
        assert result.passed is True
        assert result.measured == 1

    async def test_no_mainline_fail(self, test_db) -> None:
        await _ensure_project(PROJECT_ID)
        thread = PlotThread(
            thread_id="t1_side",
            project_id=PROJECT_ID,
            title="支线",
            description="",
            is_mainline=False,
            opened_chapter=5,
            expected_resolve_arc=1,
            status="advanced",
            last_status_chapter=10,
            last_status_version_id="v10",
        )
        await NarrativeRepository().add_thread(thread)
        result = await check_t1(PROJECT_ID, 1, 15)
        assert result.passed is False

    async def test_opened_only_fail(self, test_db) -> None:
        await _ensure_project(PROJECT_ID)
        thread = PlotThread(
            thread_id="t1_opened",
            project_id=PROJECT_ID,
            title="主线未推进",
            description="",
            is_mainline=True,
            opened_chapter=5,
            expected_resolve_arc=1,
            status="opened",
            last_status_chapter=5,
            last_status_version_id="v5",
        )
        await NarrativeRepository().add_thread(thread)
        result = await check_t1(PROJECT_ID, 1, 15)
        assert result.passed is False


class TestAggregate:
    async def test_all_pass(self, test_db) -> None:
        for ch in range(1, 51):
            await _make_accepted_head(PROJECT_ID, ch, "accepted")
            await _make_orphan_report(PROJECT_ID, ch, total=ch * 3, critical=0)
            await _make_observation(
                PROJECT_ID,
                ch,
                {
                    "literary_quality_score": 9.0,
                    "character_autonomy_score": 9.0,
                    "conceptual_grounding_score": 9.0,
                    "fissure_preservation_score": 9.0,
                },
            )
        thread = PlotThread(
            thread_id="main",
            project_id=PROJECT_ID,
            title="主线",
            description="",
            is_mainline=True,
            opened_chapter=5,
            expected_resolve_arc=1,
            status="advanced",
            last_status_chapter=20,
            last_status_version_id="v20",
        )
        await NarrativeRepository().add_thread(thread)
        logs = [_make_run_log(ch) for ch in range(1, 51)]
        run_id = "run_agg"
        for ch in (10, 20, 30, 40, 50):
            await _make_db_sample(run_id, PROJECT_ID, ch, 100 * 1024 * 1024, 10.0)

        result = await evaluate_v6_acceptance(
            PROJECT_ID, 1, 50, run_id=run_id, run_logs=logs
        )
        t2 = next(r for r in result.results if r.key == "T2")
        t6a = next(r for r in result.results if r.key == "T6a")
        assert result.all_passed is True
        assert t2.passed is True
        assert t6a.passed is True
        assert "T4" not in result.undecided  # 50 章 logs 已提供

    async def test_with_fail(self, test_db) -> None:
        for ch in range(1, 51):
            await _make_accepted_head(PROJECT_ID, ch, "accepted")
            await _make_orphan_report(PROJECT_ID, ch, total=ch * 10, critical=0)
        result = await evaluate_v6_acceptance(PROJECT_ID, 1, 50)
        assert result.all_passed is False
        t6a = next(r for r in result.results if r.key == "T6a")
        assert t6a.passed is False

    async def test_render_section(self, test_db) -> None:
        for ch in range(1, 6):
            await _make_accepted_head(PROJECT_ID, ch, "accepted")
        result = await evaluate_v6_acceptance(PROJECT_ID, 1, 5)
        text = render_v6_acceptance_section(result)
        assert "V6 验收判据" in text
        assert "T2" in text


class TestReadOnly:
    async def test_harness_does_not_write(self, test_db) -> None:
        for ch in range(1, 6):
            await _make_orphan_report(PROJECT_ID, ch, total=1, critical=0)
        before = len(await SettingTrackingRepository().list_by_project(PROJECT_ID))
        await evaluate_v6_acceptance(PROJECT_ID, 1, 5)
        after = len(await SettingTrackingRepository().list_by_project(PROJECT_ID))
        assert before == after
