"""Tests for Task 153 — run-level resume."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

from songyan.db.connection import get_db
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models import ChapterHead, ChapterVersion, ProjectRunState, ProjectSetting
from songyan.workflows.checkpointer import prune_orphan_checkpoints
from songyan.workflows.phase2_graph import (
    _compute_resume_start,
    _find_resume_run,
    _rebuild_accumulated_summary,
    run_project_pipeline,
)

PID = "proj-153"
RID = "run-153"


def _make_chapter_state(status: str = "done") -> dict[str, Any]:
    return {
        "status": status,
        "error": None,
        "thread_id": "thread-1",
    }


async def _seed_project_and_run(
    *,
    completed: list[int] | None = None,
    failed: list[int] | None = None,
    status: str = "running",
    start: int = 1,
    end: int = 5,
) -> ProjectRunState:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), PID
    )
    run_state = ProjectRunState(
        run_id=RID,
        project_id=PID,
        chapter_range_start=start,
        chapter_range_end=end,
        current_chapter=start,
        completed_chapters=completed or [],
        failed_chapters=failed or [],
        status=status,
    )
    await ProjectRunRepository().create(run_state)
    return run_state


async def _accept_chapters(chapters: list[int]) -> None:
    """在 chapter_heads 表中创建真实 accepted head 记录."""
    version_repo = ChapterVersionRepository()
    head_repo = ChapterHeadRepository()
    for ch in chapters:
        version_id = f"accepted-{ch}"
        await version_repo.create(
            ChapterVersion(
                version_id=version_id,
                project_id=PID,
                chapter_number=ch,
                version_number=1,
                version_type="accepted",
                content=f"accepted content {ch}",
                word_count=10,
            )
        )
        await head_repo.update(
            ChapterHead(
                project_id=PID,
                chapter_number=ch,
                current_version_id=version_id,
                accepted_version_id=version_id,
                status="accepted",
            )
        )


async def _insert_summary(chapter_number: int, text: str) -> None:
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO summaries
            (summary_id, project_id, chapter_number, plot_summary, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                f"sum-{chapter_number}",
                PID,
                chapter_number,
                text,
                datetime.now().isoformat(),
            ),
        )
        await conn.commit()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class TestResumeHelpers:
    async def test_find_resume_run_by_run_id(self, test_db: Any) -> None:
        await _seed_project_and_run()
        got = await _find_resume_run(PID, run_id=RID)
        assert got is not None
        assert got.run_id == RID

    async def test_find_resume_run_by_resume_flag(self, test_db: Any) -> None:
        await _seed_project_and_run()
        got = await _find_resume_run(PID, resume=True)
        assert got is not None
        assert got.run_id == RID

    async def test_find_resume_run_no_run_returns_none(self, test_db: Any) -> None:
        await ProjectRepository().create(
            ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), PID
        )
        got = await _find_resume_run(PID, resume=True)
        assert got is None

    def test_compute_resume_start(self) -> None:
        assert _compute_resume_start(1, 5, {1, 2}) == 3
        assert _compute_resume_start(1, 5, set()) == 1
        assert _compute_resume_start(1, 5, {1, 2, 3, 4, 5}) == 6

    async def test_rebuild_accumulated_summary(self, test_db: Any) -> None:
        await ProjectRepository().create(
            ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), PID
        )
        await _insert_summary(1, "s1")
        await _insert_summary(2, "s2")
        persisted, parts = await _rebuild_accumulated_summary(PID, {1, 2})
        assert persisted == "第2章：s2"
        assert parts == ["第1章：s1", "第2章：s2"]


# --------------------------------------------------------------------------- #
# Pipeline resume behavior
# --------------------------------------------------------------------------- #
class TestPipelineResume:
    async def test_resume_skips_accepted_and_rebuilds_summary(self, test_db: Any) -> None:
        """已 accept 章被跳过，resume 起点为第一个非 accept 章，累积摘要从 summaries 重建."""
        await _seed_project_and_run(completed=[1, 2], status="running")
        await _accept_chapters([1, 2])
        await _insert_summary(1, "summary-1")
        await _insert_summary(2, "summary-2")

        calls: list[int] = []

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            calls.append(kwargs["chapter_number"])
            return {
                "success": True,
                "summary_text": f"summary-{kwargs['chapter_number']}",
                "error": None,
                "final_state": {},
                "final_version_id": f"v-{kwargs['chapter_number']}",
                "budget_used": 0.8,
                "context_emergency": False,
                "quality_gate_passed": True,
                "settlement_success": True,
                "summary_success": True,
            }

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_prune,
        ):
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 4),
                auto_confirm=True,
                resume=True,
            )

        # Ch1/Ch2 已 accept 被跳过；Ch3/Ch4 执行
        assert result.run_id == RID
        assert result.chapters_completed == [1, 2, 3, 4]
        assert calls == [3, 4]
        assert result.accumulated_summary == (
            "第1章：summary-1\n\n"
            "第2章：summary-2\n\n"
            "第3章：summary-3\n\n"
            "第4章：summary-4"
        )
        mock_prune.assert_awaited_once()

    async def test_resume_trusts_accepted_head_over_completed_chapters(self, test_db: Any) -> None:
        """project_runs.completed_chapters 领先于 accepted head 时，以 head 为准."""
        # 模拟硬 kill 时刻：completed_chapters 写了 3，但 Ch3 尚未 accept
        await _seed_project_and_run(completed=[1, 2, 3], status="running")
        await _accept_chapters([1, 2])  # Ch3 未完成

        calls: list[int] = []

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            calls.append(kwargs["chapter_number"])
            return {
                "success": True,
                "summary_text": f"summary-{kwargs['chapter_number']}",
                "error": None,
                "final_state": {},
                "final_version_id": f"v-{kwargs['chapter_number']}",
                "budget_used": 0.8,
                "context_emergency": False,
                "quality_gate_passed": True,
                "settlement_success": True,
                "summary_success": True,
            }

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 3),
                auto_confirm=True,
                resume=True,
            )

        # Ch3 因未真正 accept 被重跑
        assert result.chapters_completed == [1, 2, 3]
        assert calls == [3]

    async def test_resume_ignores_status_accepted_without_accepted_version(
        self, test_db: Any
    ) -> None:
        """status=accepted 但 accepted_version_id 为空时仍必须重跑该章."""
        await _seed_project_and_run(completed=[1], status="running", start=1, end=1)
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=PID,
                chapter_number=1,
                current_version_id=None,
                accepted_version_id=None,
                status="accepted",
            )
        )

        calls: list[int] = []

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            calls.append(kwargs["chapter_number"])
            return {
                "success": True,
                "summary_text": "summary-1",
                "error": None,
                "final_state": {},
                "final_version_id": "v-1",
                "budget_used": 0.8,
                "context_emergency": False,
                "quality_gate_passed": True,
                "settlement_success": True,
                "summary_success": True,
            }

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 1),
                auto_confirm=True,
                resume=True,
            )

        assert result.chapters_completed == [1]
        assert calls == [1]

    async def test_stuck_at_running_resumes_and_completes(self, test_db: Any) -> None:
        """status='running' 的 stuck run 可被续完."""
        await _seed_project_and_run(completed=[1], failed=[2], status="running")
        await _accept_chapters([1])

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            return {
                "success": True,
                "summary_text": f"summary-{kwargs['chapter_number']}",
                "error": None,
                "final_state": {},
                "final_version_id": f"v-{kwargs['chapter_number']}",
                "budget_used": 0.8,
                "context_emergency": False,
                "quality_gate_passed": True,
                "settlement_success": True,
                "summary_success": True,
            }

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 3),
                auto_confirm=True,
                resume=True,
            )

        assert result.run_id == RID
        assert result.final_status == "completed"
        assert result.chapters_completed == [1, 2, 3]
        assert result.chapters_failed == []

    async def test_resume_from_paused_logs_warning(self, test_db: Any) -> None:
        """从 paused 状态 resume 时记录明确警告，不静默跳出门禁."""
        await _seed_project_and_run(completed=[1], status="paused")
        await _accept_chapters([1])

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            return {
                "success": True,
                "summary_text": f"summary-{kwargs['chapter_number']}",
                "error": None,
                "final_state": {},
                "final_version_id": f"v-{kwargs['chapter_number']}",
                "budget_used": 0.8,
                "context_emergency": False,
                "quality_gate_passed": True,
                "settlement_success": True,
                "summary_success": True,
            }

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch("songyan.workflows.phase2_graph.logger.warning") as mock_warn,
        ):
            await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 2),
                auto_confirm=True,
                resume=True,
            )

        messages = [str(call.kwargs.get("reason", "")) for call in mock_warn.call_args_list]
        assert any("质量熔断" in m for m in messages)

    async def test_default_new_run_behavior_unchanged(self, test_db: Any) -> None:
        """不传 resume/run_id 时仍新建 run，行为与现状一致."""
        await _seed_project_and_run(completed=[1], status="running")
        await _accept_chapters([1])

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            return {
                "success": True,
                "summary_text": f"summary-{kwargs['chapter_number']}",
                "error": None,
                "final_state": {},
                "final_version_id": f"v-{kwargs['chapter_number']}",
                "budget_used": 0.8,
                "context_emergency": False,
                "quality_gate_passed": True,
                "settlement_success": True,
                "summary_success": True,
            }

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_prune,
        ):
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 2),
                auto_confirm=True,
            )

        assert result.run_id != RID
        assert result.chapters_completed == [1, 2]
        mock_prune.assert_not_awaited()

    async def test_resume_completed_run_returns_early(self, test_db: Any) -> None:
        """resume 指向已 completed 的 run 时直接返回，不重新执行."""
        await _seed_project_and_run(completed=[1, 2], status="completed")
        await _accept_chapters([1, 2])

        with patch("songyan.workflows.phase2_graph._run_single_chapter") as mock_run:
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 2),
                auto_confirm=True,
                run_id=RID,
            )

        mock_run.assert_not_called()
        assert result.run_id == RID
        assert result.final_status == "completed"
        assert result.chapters_completed == [1, 2]

    async def test_resume_completed_run_expanded_range_continues(
        self, test_db: Any
    ) -> None:
        """Bug B（V8 172b）：completed run 但请求 end 超出已 accepted 范围时不得短路.

        分段爬坡逐段扩大 end（如 seg1 完成 Ch1-2 并 completed，seg2 请求 (1,4)）。
        旧逻辑一律短路返回，导致 Ch3-4 从未生成。修复后应 resume 续跑缺口章。
        """
        await _seed_project_and_run(completed=[1, 2], status="completed", end=2)
        await _accept_chapters([1, 2])

        generated: list[int] = []

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            generated.append(kwargs["chapter_number"])
            return {
                "success": True,
                "summary_text": f"summary-{kwargs['chapter_number']}",
                "error": None,
                "final_state": {},
                "final_version_id": f"v-{kwargs['chapter_number']}",
                "budget_used": 0.8,
                "context_emergency": False,
                "quality_gate_passed": True,
                "settlement_success": True,
                "summary_success": True,
            }

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 4),
                auto_confirm=True,
                resume=True,
            )

        # 关键断言：Ch3-4 缺口必须被驱动生成（不再 0 生成短路），已 accepted 的 Ch1-2 跳过
        assert sorted(generated) == [3, 4], f"only Ch3-4 must be generated, got {sorted(generated)}"
        assert result.final_status == "completed"
        assert result.chapters_completed == [1, 2, 3, 4]


# --------------------------------------------------------------------------- #
# Checkpoint pruning
# --------------------------------------------------------------------------- #
class TestCheckpointPruning:
    async def test_prune_orphan_checkpoints_memory_mode(self, test_db: Any) -> None:
        from songyan.config import settings

        original = settings.checkpointer_mode
        settings.checkpointer_mode = "memory"
        try:
            assert await prune_orphan_checkpoints(PID, set()) == 0
        finally:
            settings.checkpointer_mode = original

    async def test_prune_orphan_checkpoints_sqlite(self, test_db: Any) -> None:
        """metadata 带 project_id 的旧 checkpoint 可被清理；不匹配的保留."""
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        from songyan.config import settings

        original_mode = settings.checkpointer_mode
        settings.checkpointer_mode = "sqlite"
        try:
            async with get_db() as conn:
                saver = AsyncSqliteSaver(conn)
                await saver.setup()
                await conn.execute(
                    """
                    INSERT INTO checkpoints
                    (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id,
                     type, checkpoint, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "t-old",
                        "",
                        "c1",
                        "",
                        "",
                        b"",
                        json.dumps({"project_id": PID, "chapter_number": 1}),
                    ),
                )
                await conn.execute(
                    """
                    INSERT INTO checkpoints
                    (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id,
                     type, checkpoint, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "t-other",
                        "",
                        "c2",
                        "",
                        "",
                        b"",
                        json.dumps({"project_id": "other-proj", "chapter_number": 1}),
                    ),
                )
                await conn.commit()

            pruned = await prune_orphan_checkpoints(PID, {"t-active"})
            assert pruned == 1

            async with get_db() as conn:
                cur = await conn.execute(
                    """
                    SELECT thread_id FROM checkpoints
                    WHERE json_extract(metadata, '$.project_id') != ?
                    """,
                    (PID,),
                )
                rows = await cur.fetchall()
                assert [r[0] for r in rows] == ["t-other"]
        finally:
            settings.checkpointer_mode = original_mode
            from songyan.workflows.checkpointer import reset_checkpointer

            await reset_checkpointer()
