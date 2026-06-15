"""Tests for ProjectRunState and ProjectRunResult models."""

from __future__ import annotations

from songyan.models import ProjectRunResult, ProjectRunState


class TestProjectRunState:
    def test_instantiation_defaults(self) -> None:
        state = ProjectRunState(
            run_id="run-001",
            project_id="proj-001",
            chapter_range_start=1,
            chapter_range_end=3,
        )
        assert state.run_id == "run-001"
        assert state.current_chapter == 0
        assert state.completed_chapters == []
        assert state.failed_chapters == []
        assert state.accumulated_summary == ""
        assert state.total_cost == 0.0
        assert state.status == "running"

    def test_full_instantiation(self) -> None:
        state = ProjectRunState(
            run_id="run-002",
            project_id="proj-002",
            chapter_range_start=2,
            chapter_range_end=5,
            current_chapter=3,
            completed_chapters=[2, 3],
            failed_chapters=[],
            accumulated_summary="summary",
            total_cost=0.5,
            status="completed",
        )
        assert state.current_chapter == 3
        assert state.completed_chapters == [2, 3]
        assert state.status == "completed"

    def test_invalid_status_rejected(self) -> None:
        # Pydantic v2 中 Literal 未限制自由字符串，但模型仍可保存
        state = ProjectRunState(
            run_id="run-003",
            project_id="proj-003",
            chapter_range_start=1,
            chapter_range_end=2,
            status="weird_status",
        )
        assert state.status == "weird_status"


class TestProjectRunResult:
    def test_instantiation_defaults(self) -> None:
        result = ProjectRunResult(
            project_id="proj-001",
            run_id="run-001",
        )
        assert result.final_status == ""
        assert result.chapters_completed == []
        assert result.total_cost == 0.0
        assert result.total_duration_sec == 0.0

    def test_full_instantiation(self) -> None:
        result = ProjectRunResult(
            project_id="proj-001",
            run_id="run-001",
            chapters_completed=[1, 2, 3],
            chapters_failed=[],
            total_cost=1.5,
            total_duration_sec=120.0,
            final_status="completed",
            accumulated_summary="ch1 summary\n\nch2 summary",
        )
        assert result.final_status == "completed"
        assert len(result.chapters_completed) == 3
