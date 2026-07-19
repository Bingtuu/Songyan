"""Task 175 阶段 D：LLMBudgetExceededError 必须穿透 phase1 宽捕获到达 pause 路径.

生产缺陷（D1 熔断实证实跑发现）：`run_chapter_pipeline` 的 `except Exception`
把预算熔断异常包装为 `{"error": "Pipeline failure: ...", "status": "failed"}`，
异常类型丢失，phase2 的 `except LLMBudgetExceededError`（pause + resume 路径）
永远接不到——run 变成 failed 而非 paused。
"""

from __future__ import annotations

import pytest

from songyan.exceptions import LLMBudgetExceededError, LLMError
from songyan.workflows import phase1_graph


class _BudgetBoomGraph:
    async def ainvoke(self, state: object, config: object = None) -> object:
        raise LLMBudgetExceededError(
            message="单 run 成本预算超限（¥0.05），已用 ¥0.0512",
            used_calls=11,
            budget=0,
            last_chapter=1,
            used_cost=0.0512,
            budget_cost=0.05,
        )


class _LLMErrorGraph:
    async def ainvoke(self, state: object, config: object = None) -> object:
        raise LLMError("LLM 调用失败: boom")


async def _build(graph: object):
    async def _fake() -> object:
        return graph

    return _fake


@pytest.mark.asyncio
async def test_budget_exceeded_propagates_instead_of_chapter_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """预算熔断异常必须原样传播，不得包装为章节失败状态."""
    monkeypatch.setattr(
        phase1_graph, "build_phase1_graph", await _build(_BudgetBoomGraph())
    )

    with pytest.raises(LLMBudgetExceededError):
        await phase1_graph.run_chapter_pipeline(project_id="p1", chapter_number=1)


@pytest.mark.asyncio
async def test_llm_error_still_wrapped_as_chapter_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """防回归：普通 LLMError 仍按既有语义包装为章节失败状态."""
    monkeypatch.setattr(
        phase1_graph, "build_phase1_graph", await _build(_LLMErrorGraph())
    )

    result = await phase1_graph.run_chapter_pipeline(project_id="p1", chapter_number=1)

    assert result["status"] == "failed"
    assert "Pipeline LLM failure" in (result["error"] or "")
