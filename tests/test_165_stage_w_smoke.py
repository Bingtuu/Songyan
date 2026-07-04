"""Task 165 Layer 2 冒烟测试：复跑脚本 + 阶段 W 出口汇总逻辑.

不调用真实 LLM；只验证脚本常量隔离、T10 汇总、T9/T10 冻结草案、
阶段 W 出口表格与总结论。
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

import scripts.run_165_stage_w_ch150 as r165
from songyan.evals.db_metrics import LiteraryScorePoint
from songyan.models.project_run import ProjectRunResult


def _literary_points(values: list[float]) -> list[LiteraryScorePoint]:
    return [
        LiteraryScorePoint(
            chapter=index + 1,
            literary_quality_score=8.0,
            character_autonomy_score=8.0,
            conceptual_grounding_score=value,
            fissure_preservation_score=8.0,
        )
        for index, value in enumerate(values)
    ]


class TestConstantsIsolation:
    def test_default_range_is_1_to_150(self) -> None:
        assert r165.START_CHAPTER == 1
        assert r165.END_CHAPTER == 150

    def test_paths_use_task165_prefix(self) -> None:
        assert "task165_stage_w_ch150" in str(r165.DB_PATH)
        assert "task165_stage_w_ch150" in str(r165.METRICS_PATH)
        assert "task165_project" in str(r165.PROJECT_FILE)
        assert "task-165" in str(r165.REPORT_PATH)
        assert "task-165" in str(r165.CALIBRATION_REPORT_PATH)

    def test_does_not_touch_159_artifacts(self) -> None:
        for path in (
            r165.DB_PATH,
            r165.METRICS_PATH,
            r165.PROJECT_FILE,
            r165.REPORT_PATH,
            r165.CALIBRATION_REPORT_PATH,
        ):
            assert "task159" not in str(path)
            assert "task-159" not in str(path)

    def test_reuses_v6_harness_not_fork(self) -> None:
        assert r165.evaluate_v6_acceptance.__module__ == "songyan.evals.v6_acceptance"
        assert r165.render_v6_acceptance_section.__module__ == "songyan.evals.v6_acceptance"


class TestMainSmoke:
    @pytest.mark.asyncio
    async def test_mock_three_chapter_run_invokes_pipeline_and_report(
        self, monkeypatch
    ) -> None:
        calls: dict[str, object] = {}

        class FakeProjectRepository:
            async def get(self, project_id: str) -> SimpleNamespace:
                calls["project_id"] = project_id
                return SimpleNamespace(mode_id="test-mode")

        async def fake_run_project_pipeline(**kwargs) -> ProjectRunResult:
            calls["pipeline"] = kwargs
            return ProjectRunResult(
                project_id=kwargs["project_id"],
                run_id="run-165-smoke",
                chapters_completed=[1, 2, 3],
                chapters_failed=[],
                total_duration_sec=1.5,
                final_status="completed",
            )

        async def fake_find_run_id(project_id: str) -> str:
            calls["find_run_id"] = project_id
            return "run-165-smoke"

        async def fake_build_report(
            project_id: str,
            run_id: str | None,
            *,
            include_timeline_in_redline: bool = False,
        ) -> None:
            calls["report"] = {
                "project_id": project_id,
                "run_id": run_id,
                "include_timeline_in_redline": include_timeline_in_redline,
            }

        monkeypatch.setattr(sys, "argv", ["run_165", "--project-id", "proj-165"])
        monkeypatch.setattr(r165, "START_CHAPTER", 1)
        monkeypatch.setattr(r165, "END_CHAPTER", 3)
        monkeypatch.setattr(r165, "ProjectRepository", FakeProjectRepository)
        monkeypatch.setattr(r165, "run_project_pipeline", fake_run_project_pipeline)
        monkeypatch.setattr(r165, "_find_run_id", fake_find_run_id)
        monkeypatch.setattr(r165, "_build_and_write_report", fake_build_report)

        await r165.main()

        pipeline = calls["pipeline"]
        assert isinstance(pipeline, dict)
        assert pipeline["project_id"] == "proj-165"
        assert pipeline["chapter_range"] == (1, 3)
        assert pipeline["mode_id"] == "test-mode"
        assert pipeline["auto_confirm"] is True
        assert pipeline["on_failure"] == r165.ON_FAILURE
        assert pipeline["resume"] is False
        report = calls["report"]
        assert isinstance(report, dict)
        assert report == {
            "project_id": "proj-165",
            "run_id": "run-165-smoke",
            "include_timeline_in_redline": False,
        }

    @pytest.mark.asyncio
    async def test_report_only_path_skips_pipeline_and_allows_timeline_redline(
        self, monkeypatch
    ) -> None:
        calls: dict[str, object] = {"pipeline_called": False}

        async def fake_find_run_id(project_id: str) -> str:
            calls["find_run_id"] = project_id
            return "run-165-existing"

        async def fake_build_report(
            project_id: str,
            run_id: str | None,
            *,
            include_timeline_in_redline: bool = False,
        ) -> None:
            calls["report"] = {
                "project_id": project_id,
                "run_id": run_id,
                "include_timeline_in_redline": include_timeline_in_redline,
            }

        async def fake_run_project_pipeline(**kwargs) -> ProjectRunResult:
            calls["pipeline_called"] = True
            return ProjectRunResult(project_id=kwargs["project_id"], run_id="unexpected")

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_165",
                "--project-id",
                "proj-165",
                "--report",
                "--include-timeline-in-redline",
            ],
        )
        monkeypatch.setattr(r165, "_find_run_id", fake_find_run_id)
        monkeypatch.setattr(r165, "_build_and_write_report", fake_build_report)
        monkeypatch.setattr(r165, "run_project_pipeline", fake_run_project_pipeline)

        await r165.main()

        assert calls["pipeline_called"] is False
        assert calls["report"] == {
            "project_id": "proj-165",
            "run_id": "run-165-existing",
            "include_timeline_in_redline": True,
        }


class TestT10Calibration:
    def test_t10_passes_when_last_window_above_85pct(self) -> None:
        result = r165.evaluate_t10_calibration(
            _literary_points([10.0] * 5 + [8.5] * 5)
        )

        assert result.sufficient is True
        assert result.passed is True
        assert result.threshold == 8.5

    def test_t10_fails_when_last_window_below_85pct(self) -> None:
        result = r165.evaluate_t10_calibration(
            _literary_points([10.0] * 5 + [8.4] * 5)
        )

        assert result.sufficient is True
        assert result.passed is False

    def test_t10_insufficient_samples(self) -> None:
        result = r165.evaluate_t10_calibration(_literary_points([8.0] * 5))

        assert result.sufficient is False
        assert result.passed is None


class TestStageWExitSummary:
    def test_all_pass_verdict(self) -> None:
        rows = [
            r165.StageWExitRow(
                item="P 洁净",
                criterion="c",
                evidence="e",
                passed=True,
                measured="m",
                detail="d",
            ),
            r165.StageWExitRow(
                item="L 文学",
                criterion="c",
                evidence="e",
                passed=True,
                measured="m",
                detail="d",
            ),
        ]

        verdict, blockers = r165.summarize_stage_w_exit(rows)

        assert not blockers
        assert "阶段 W 通过" in verdict

    def test_fail_verdict_lists_blockers(self) -> None:
        rows = [
            r165.StageWExitRow(
                item="P 洁净",
                criterion="c",
                evidence="e",
                passed=False,
                measured="m",
                detail="d",
            ),
            r165.StageWExitRow(
                item="L 文学",
                criterion="c",
                evidence="e",
                passed=None,
                measured="m",
                detail="d",
            ),
        ]

        verdict, blockers = r165.summarize_stage_w_exit(rows)

        assert blockers == ["P 洁净"]
        assert "条件不通过" in verdict
        assert "L 文学" in verdict

    def test_render_stage_w_exit_section(self) -> None:
        rows = [
            r165.StageWExitRow(
                item="P 洁净",
                criterion="meta=0",
                evidence="check_t9",
                passed=True,
                measured="meta=0",
                detail="ok",
            )
        ]

        text = r165.render_stage_w_exit_section(rows)

        assert "阶段 W 出口核对" in text
        assert "P 洁净" in text
        assert "阶段 W 通过" in text

    def test_render_threshold_freeze_section(self) -> None:
        t9 = r165.T9Calibration(
            include_timeline_in_redline=False,
            passed=True,
            measured="meta=0, duplicate=0, timeline=1",
            detail="时间线诊断章: [2]",
        )
        t10 = r165.T10Calibration(
            sufficient=True,
            passed=True,
            first_window_mean=10.0,
            last_window_mean=8.6,
            threshold=8.5,
            detail="ok",
        )

        text = r165.render_threshold_freeze_section(t9, t10)

        assert "T9/T10 阈值标定与冻结草案" in text
        assert "仅报告不计红线" in text
        assert "×0.85" in text
