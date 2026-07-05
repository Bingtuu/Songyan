"""Task 158a Layer 2 冒烟测试：长跑脚本 + kill→resume 编排.

不调用真实 LLM；用隔离 SQLite 与 mock 验证脚本行为。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import scripts.run_158_ch1_ch100 as runner
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models import ChapterHead, ChapterVersion, ProjectRunState, ProjectSetting
from songyan.workflows.phase2_graph import run_project_pipeline

PID = "proj-158-smoke"


def _make_chapter_state(chapter_number: int, status: str = "done") -> dict[str, Any]:
    return {
        "status": status,
        "success": status == "done",
        "error": None,
        "thread_id": "thread-1",
        "summary_text": f"summary-{chapter_number}",
        "final_state": {
            "current_version_id": f"v-{chapter_number}",
            "settlement_id": f"settle-{chapter_number}",
            "summary_id": f"sum-{chapter_number}",
            "_quality_gate_passed": True,
        },
        "final_version_id": f"v-{chapter_number}",
        "budget_used": 0.5,
        "context_emergency": False,
        "quality_gate_passed": True,
        "settlement_success": True,
        "summary_success": True,
        "updated_min_health_score": 8.0,
    }


async def _seed_project() -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="scifi", protagonist_name="林渊"), PID
    )


async def _accept_chapters(chapters: list[int]) -> None:
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
    from datetime import datetime

    from songyan.db.connection import get_db

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


async def _seed_run(
    completed: list[int],
    failed: list[int] | None = None,
    status: str = "running",
    current_chapter: int = 1,
) -> ProjectRunState:
    failed = failed or []
    state = ProjectRunState(
        run_id="run-158-smoke",
        project_id=PID,
        chapter_range_start=1,
        chapter_range_end=5,
        current_chapter=current_chapter,
        completed_chapters=completed,
        failed_chapters=failed,
        status=status,
    )
    await ProjectRunRepository().create(state)
    return state


class TestScriptImportsAndConstants:
    def test_default_range_is_1_to_100(self) -> None:
        assert runner.START_CHAPTER == 1
        assert runner.END_CHAPTER == 100

    def test_paths_use_task158_prefix(self) -> None:
        assert "task158_ch1_ch100" in str(runner.DB_PATH)
        assert "task158_ch1_ch100" in str(runner.METRICS_PATH)
        assert "task158_project" in str(runner.PROJECT_FILE)
        assert "task-158-ch1-ch100" in str(runner.REPORT_PATH)

    def test_evaluate_v6_acceptance_imported(self) -> None:
        # harness 必须从 songyan.evals.v6_acceptance 导入，不 fork
        assert runner.evaluate_v6_acceptance.__module__ == "songyan.evals.v6_acceptance"


class TestArgumentParsing:
    def test_defaults(self) -> None:
        parser = runner.argparse.ArgumentParser()
        parser.add_argument("--init", action="store_true")
        parser.add_argument("--resume", action="store_true")
        parser.add_argument("--project-id", default=None)
        parser.add_argument("--kill-at-chapter", type=int, default=None)
        args = parser.parse_args([])
        assert args.init is False
        assert args.resume is False
        assert args.project_id is None
        assert args.kill_at_chapter is None

    def test_resume_and_kill_flags(self) -> None:
        parser = runner.argparse.ArgumentParser()
        parser.add_argument("--init", action="store_true")
        parser.add_argument("--resume", action="store_true")
        parser.add_argument("--project-id", default=None)
        parser.add_argument("--kill-at-chapter", type=int, default=None)
        args = parser.parse_args(["--resume", "--kill-at-chapter", "50"])
        assert args.resume is True
        assert args.kill_at_chapter == 50


class TestMetricsJsonlAppend:
    async def test_append_metric_creates_jsonl(self, tmp_path: Path) -> None:
        metrics_path = tmp_path / "metrics.jsonl"
        with patch.object(runner, "METRICS_PATH", metrics_path):
            runner._append_metric({"chapter": 1, "accepted": True})
            runner._append_metric({"chapter": 2, "accepted": False})
        lines = metrics_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["chapter"] == 1
        assert json.loads(lines[1])["accepted"] is False


class TestKillResumeOrchestration:
    async def test_inflight_chapter_recomputed_on_resume(self, test_db: Path) -> None:
        """模拟硬 kill：run_state 已写 Ch3，但 Ch3 未 accept；resume 后只重算 Ch3."""
        await _seed_project()
        # 模拟 kill 前状态：Ch1/Ch2 accept，Ch3 在 run_state 中 current_chapter=3 但未 accept
        await _seed_run(completed=[1, 2], current_chapter=3, status="running")
        await _accept_chapters([1, 2])
        await _insert_summary(1, "summary-1")
        await _insert_summary(2, "summary-2")

        calls: list[int] = []

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            calls.append(kwargs["chapter_number"])
            return _make_chapter_state(kwargs["chapter_number"])

        with (
            patch(
                "songyan.workflows.phase2_graph._run_single_chapter",
                side_effect=_fake_run,
            ),
            patch(
                "songyan.workflows.phase2_graph._save_run_state",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows.phase2_graph.reset_checkpointer",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=3,
            ) as mock_prune,
        ):
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 3),
                mode_id="webnovel",
                auto_confirm=True,
                resume=True,
            )

        assert result.chapters_completed == [1, 2, 3]
        assert result.final_status == "completed"
        # Ch1/Ch2 已 accept 跳过；Ch3 in-flight 被重算
        assert calls == [3]
        mock_prune.assert_awaited_once()

    async def test_resume_after_exception_recomputes_inflight(self, test_db: Path) -> None:
        """模拟 run 执行到 Ch3 时异常中断，然后 resume."""
        await _seed_project()
        await _seed_run(completed=[1, 2], current_chapter=3, status="running")
        await _accept_chapters([1, 2])
        await _insert_summary(1, "summary-1")
        await _insert_summary(2, "summary-2")

        calls: list[int] = []

        async def _fake_run_first(**kwargs: Any) -> dict[str, Any]:
            calls.append(kwargs["chapter_number"])
            if kwargs["chapter_number"] == 3:
                return {
                    "success": False,
                    "status": "failed",
                    "error": "simulated chapter failure",
                    "final_state": {},
                    "final_version_id": None,
                    "summary_text": "",
                }
            return _make_chapter_state(kwargs["chapter_number"])

        # 第一次运行：Ch3 失败
        with (
            patch(
                "songyan.workflows.phase2_graph._run_single_chapter",
                side_effect=_fake_run_first,
            ),
            patch(
                "songyan.workflows.phase2_graph._save_run_state",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows.phase2_graph.reset_checkpointer",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 3),
                mode_id="webnovel",
                auto_confirm=True,
                resume=True,
                on_failure="isolate",
            )
        assert result.chapters_failed == [3]

        # 第二次运行：resume，Ch3 成功
        async def _fake_run_second(**kwargs: Any) -> dict[str, Any]:
            calls.append(kwargs["chapter_number"])
            return _make_chapter_state(kwargs["chapter_number"])

        with (
            patch(
                "songyan.workflows.phase2_graph._run_single_chapter",
                side_effect=_fake_run_second,
            ),
            patch(
                "songyan.workflows.phase2_graph._save_run_state",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows.phase2_graph.reset_checkpointer",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows.checkpointer.prune_orphan_checkpoints",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            result = await run_project_pipeline(
                project_id=PID,
                chapter_range=(1, 3),
                mode_id="webnovel",
                auto_confirm=True,
                resume=True,
                on_failure="isolate",
            )

        assert result.chapters_completed == [1, 2, 3]
        assert result.chapters_failed == []
        # 两次 resume 都只跑 Ch3
        assert calls == [3, 3]
