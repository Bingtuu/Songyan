"""Tests for Task 155 — failure isolation strategy."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.migrations import init_schema
from songyan.exceptions import AutoHaltException
from songyan.workflows.phase2_graph import run_project_pipeline


@pytest.fixture(scope="module", autouse=True)
def ensure_proj_155():
    """保证主库 schema 与 proj-155 存在；本模块硬编码使用 project_id=proj-155."""
    db_path = get_db_path()
    asyncio.run(init_schema(db_path))

    async def _seed():
        async with get_db() as conn:
            await conn.execute(
                """INSERT OR IGNORE INTO projects (
                    project_id, title, genre_id, mode_id, protagonist_name,
                    estimated_chapters, words_per_chapter, target_word_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    "proj-155",
                    "Test Project 155",
                    "scifi",
                    "webnovel",
                    "Protagonist",
                    150,
                    3000,
                    450000,
                ),
            )
            await conn.commit()

    asyncio.run(_seed())
    yield


def _make_chapter_result(
    *,
    success: bool = True,
    chapter_number: int = 1,
    summary_text: str = "",
    context_emergency: bool = False,
    quality_gate_passed: bool = True,
) -> dict[str, Any]:
    return {
        "success": success,
        "summary_text": summary_text,
        "error": None if success else f"fail-ch{chapter_number}",
        "final_state": {},
        "final_version_id": f"v-{chapter_number}",
        "budget_used": 0.8,
        "context_emergency": context_emergency,
        "quality_gate_passed": quality_gate_passed,
        "settlement_success": success,
        "summary_success": success,
        "continuity_health_severity": None,
        "gate_triggered": False,
        "gate_reasons": [],
        "updated_min_health_score": None,
    }


class TestIsolateStrategy:
    async def test_isolate_continues_after_single_failure(self) -> None:
        """isolate 模式下 Ch2 失败，Ch1/Ch3 成功，最终 partial."""

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            ch = kwargs["chapter_number"]
            if ch == 2:
                return _make_chapter_result(success=False, chapter_number=ch)
            return _make_chapter_result(
                success=True, chapter_number=ch, summary_text=f"summary-{ch}"
            )

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
        ):
            result = await run_project_pipeline(
                project_id="proj-155",
                chapter_range=(1, 3),
                auto_confirm=True,
                on_failure="isolate",
            )

        assert result.final_status == "partial"
        assert result.chapters_completed == [1, 3]
        assert result.chapters_failed == [2]

    async def test_abort_stops_at_first_failure(self) -> None:
        """abort 模式下 Ch2 失败后终止."""

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            ch = kwargs["chapter_number"]
            if ch == 2:
                return _make_chapter_result(success=False, chapter_number=ch)
            return _make_chapter_result(
                success=True, chapter_number=ch, summary_text=f"summary-{ch}"
            )

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
        ):
            result = await run_project_pipeline(
                project_id="proj-155",
                chapter_range=(1, 3),
                auto_confirm=True,
                on_failure="abort",
            )

        assert result.final_status == "partial"
        assert result.chapters_completed == [1]
        assert result.chapters_failed == [2]

    async def test_default_on_failure_is_isolate(self) -> None:
        """不传 on_failure 时默认 isolate."""
        calls: list[str] = []

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            ch = kwargs["chapter_number"]
            calls.append(kwargs["on_failure"])
            if ch == 2:
                return _make_chapter_result(success=False, chapter_number=ch)
            return _make_chapter_result(success=True, chapter_number=ch)

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
        ):
            await run_project_pipeline(
                project_id="proj-155",
                chapter_range=(1, 3),
                auto_confirm=True,
            )

        assert all(strategy == "isolate" for strategy in calls)


class TestIsolateContextFallback:
    async def test_previous_summary_falls_back_to_latest_successful(self) -> None:
        """Ch2 失败后，Ch3 的 previous_summary 应来自 Ch1（最近成功章）."""
        summaries: list[tuple[int, str]] = []

        async def _fake_get_summary(project_id: str, chapter_number: int) -> str:
            return {
                1: "summary-1",
                2: "summary-2",
                3: "summary-3",
            }.get(chapter_number, "")

        async def _fake_previous_summary(
            project_id: str,
            chapter_number: int,
            *,
            latest_successful_chapter: int | None = None,
        ) -> str:
            source = (
                latest_successful_chapter
                if latest_successful_chapter is not None
                else chapter_number - 1
            )
            return await _fake_get_summary(project_id, source)

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            summaries.append((kwargs["chapter_number"], kwargs["previous_summary"]))
            ch = kwargs["chapter_number"]
            if ch == 2:
                return _make_chapter_result(success=False, chapter_number=ch)
            return _make_chapter_result(
                success=True, chapter_number=ch, summary_text=f"summary-{ch}"
            )

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch(
                "songyan.workflows.phase2_graph._get_previous_summary",
                side_effect=_fake_previous_summary,
            ),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
        ):
            await run_project_pipeline(
                project_id="proj-155",
                chapter_range=(1, 3),
                auto_confirm=True,
                on_failure="isolate",
            )

        # Ch1 previous_summary=""; Ch2 仍用上一章（Ch1）摘要；
        # Ch3 因 Ch2 失败，回退到最近成功章 Ch1 摘要
        assert summaries == [
            (1, ""),
            (2, "summary-1"),
            (3, "summary-1"),
        ]

    async def test_cursor_not_advanced_by_consecutive_failures(self) -> None:
        """连续失败章不推进游标，后续成功章仍用最近成功章摘要."""
        summaries: list[tuple[int, str]] = []

        async def _fake_get_summary(project_id: str, chapter_number: int) -> str:
            return {1: "summary-1", 4: "summary-4"}.get(chapter_number, "")

        async def _fake_previous_summary(
            project_id: str,
            chapter_number: int,
            *,
            latest_successful_chapter: int | None = None,
        ) -> str:
            source = (
                latest_successful_chapter
                if latest_successful_chapter is not None
                else chapter_number - 1
            )
            return await _fake_get_summary(project_id, source)

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            summaries.append((kwargs["chapter_number"], kwargs["previous_summary"]))
            ch = kwargs["chapter_number"]
            if ch in (2, 3):
                return _make_chapter_result(success=False, chapter_number=ch)
            return _make_chapter_result(
                success=True, chapter_number=ch, summary_text=f"summary-{ch}"
            )

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch(
                "songyan.workflows.phase2_graph._get_previous_summary",
                side_effect=_fake_previous_summary,
            ),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
        ):
            result = await run_project_pipeline(
                project_id="proj-155",
                chapter_range=(1, 4),
                auto_confirm=True,
                on_failure="isolate",
            )

        assert result.chapters_completed == [1, 4]
        assert result.chapters_failed == [2, 3]
        assert summaries[-1] == (4, "summary-1")

    async def test_first_chapter_failure_empty_previous_summary(self) -> None:
        """首章失败时，Ch2 的 previous_summary 为空串."""
        summaries: list[tuple[int, str]] = []

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            summaries.append((kwargs["chapter_number"], kwargs["previous_summary"]))
            ch = kwargs["chapter_number"]
            if ch == 1:
                return _make_chapter_result(success=False, chapter_number=ch)
            return _make_chapter_result(
                success=True, chapter_number=ch, summary_text=f"summary-{ch}"
            )

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._get_summary_text", return_value=""),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
        ):
            await run_project_pipeline(
                project_id="proj-155",
                chapter_range=(1, 2),
                auto_confirm=True,
                on_failure="isolate",
            )

        assert summaries[1] == (2, "")


class TestIsolateDoesNotSwallowAutoHalt:
    async def test_auto_halt_still_raises_in_isolate_mode(self) -> None:
        """isolate 模式下连续质量门失败仍触发 AutoHalt."""

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            ch = kwargs["chapter_number"]
            success = ch < 3
            return {
                "success": success,
                "summary_text": f"summary-{ch}" if success else "",
                "error": None if success else "fail",
                "final_state": {},
                "final_version_id": f"v-{ch}",
                "budget_used": 0.8,
                "context_emergency": False,
                "quality_gate_passed": False,
                "settlement_success": success,
                "summary_success": success,
                "continuity_health_severity": None,
                "gate_triggered": False,
                "gate_reasons": [],
                "updated_min_health_score": None,
            }

        saved_states: list[Any] = []

        async def _capture_state(state: Any) -> None:
            saved_states.append(state.model_copy(deep=True))

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", side_effect=_capture_state),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
        ):
            with pytest.raises(AutoHaltException) as exc_info:
                await run_project_pipeline(
                    project_id="proj-155",
                    chapter_range=(1, 5),
                    auto_confirm=True,
                    on_failure="isolate",
                )

        assert exc_info.value.reason == "quality_gate_fail_streak"
        assert saved_states[-1].status == "paused"
        assert saved_states[-1].completed_chapters == [1, 2]
        assert saved_states[-1].failed_chapters == [3]
