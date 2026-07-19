"""Task 173：pipeline 收尾必须同时清理 LLM client 与 checkpointer（sqlite 模式挂死根因）.

生产缺陷（D2 scifi end10 实跑复现）：`checkpointer_mode=sqlite` 时
`AsyncSqliteSaver` 持有的 aiosqlite 连接（非 daemon `_connection_worker_thread`）
在 pipeline 结束后无人关闭，主线程在 `threading._shutdown` 中 join 该线程，
进程在结果落盘后挂死（py-spy 实证 2026-07-19）。`reset_checkpointer()`
（关闭 saver + 清编译图缓存）此前只有测试路径调用。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from songyan.workflows import phase2_graph


def _stub_result() -> object:
    return phase2_graph.ProjectRunResult(
        project_id="p1",
        run_id="run-x",
        chapters_completed=[1],
        chapters_failed=[],
        total_cost=0.0,
        total_duration_sec=0.1,
        final_status="completed",
        accumulated_summary="",
    )


@pytest.mark.asyncio
async def test_pipeline_finally_closes_checkpointer_on_success() -> None:
    """正常完成时：wrapper finally 同时调用 aclose_llm_clients 与 reset_checkpointer."""
    with (
        patch.object(
            phase2_graph, "_run_project_pipeline_impl", new=AsyncMock(return_value=_stub_result())
        ) as impl,
        patch("songyan.llm.client.aclose_llm_clients", new=AsyncMock()) as aclose,
        patch("songyan.workflows.phase1_graph.reset_checkpointer", new=AsyncMock()) as reset_cp,
    ):
        result = await phase2_graph.run_project_pipeline(project_id="p1", chapter_range=(1, 1))

    assert result.final_status == "completed"
    impl.assert_awaited_once()
    aclose.assert_awaited_once()
    reset_cp.assert_awaited_once()


@pytest.mark.asyncio
async def test_pipeline_finally_closes_checkpointer_on_exception() -> None:
    """异常路径：impl 抛错时 finally 仍执行两侧清理，且不屏蔽原异常."""
    with (
        patch.object(
            phase2_graph,
            "_run_project_pipeline_impl",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch("songyan.llm.client.aclose_llm_clients", new=AsyncMock()) as aclose,
        patch("songyan.workflows.phase1_graph.reset_checkpointer", new=AsyncMock()) as reset_cp,
    ):
        with pytest.raises(RuntimeError, match="boom"):
            await phase2_graph.run_project_pipeline(project_id="p1", chapter_range=(1, 1))

    aclose.assert_awaited_once()
    reset_cp.assert_awaited_once()
