"""Tests for Task 154 — LLM rate-limit awareness and per-run budget."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from songyan.config import settings
from songyan.exceptions import LLMBudgetExceededError, LLMError, LLMRateLimitError
from songyan.llm.client import (
    call_llm,
    get_llm_call_count,
    reset_llm_call_count,
    set_llm_budget_last_chapter,
)
from songyan.llm.retry import retry_with_backoff
from songyan.workflows.phase2_graph import run_project_pipeline

pytestmark = pytest.mark.performance


class FakeRateLimitError(Exception):
    """模拟 litellm / provider 抛出的 429 异常."""

    def __init__(self, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status_code = 429
        self.headers = headers or {}


# --------------------------------------------------------------------------- #
# Rate-limit classification in call_llm
# --------------------------------------------------------------------------- #
class TestRateLimitClassification:
    async def test_429_with_retry_after(self, monkeypatch: Any) -> None:
        """status_code=429 + Retry-After 被识别并按建议退避后成功."""
        monkeypatch.setattr(settings, "llm_run_call_budget", 0)
        reset_llm_call_count()

        calls: list[int] = []

        async def _mock_ainvoke(*args: Any, **kwargs: Any) -> Any:
            calls.append(len(calls))
            if len(calls) == 1:
                raise FakeRateLimitError("rate limited", headers={"Retry-After": "0.01"})
            return type("R", (), {"content": "ok"})()

        with patch("songyan.llm.client.get_llm") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.side_effect = _mock_ainvoke
            mock_get_llm.return_value = mock_llm
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await call_llm("prompt")

        assert result == "ok"
        assert len(calls) == 2

    async def test_retry_after_capped_by_max_wait(self, monkeypatch: Any) -> None:
        """Retry-After 超过 llm_rate_limit_max_wait 时被截断."""
        monkeypatch.setattr(settings, "llm_rate_limit_max_wait", 3.0)
        monkeypatch.setattr(settings, "llm_run_call_budget", 0)
        reset_llm_call_count()

        delays: list[float] = []

        async def _patched_sleep(delay: float) -> None:
            delays.append(delay)

        async def _mock_ainvoke(*args: Any, **kwargs: Any) -> Any:
            raise FakeRateLimitError("rate limited", headers={"retry-after": "120"})

        with patch("songyan.llm.client.get_llm") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.side_effect = _mock_ainvoke
            mock_get_llm.return_value = mock_llm
            with patch("asyncio.sleep", side_effect=_patched_sleep):
                with pytest.raises(LLMRateLimitError):
                    await call_llm("prompt", max_retries=2)

        assert delays == [3.0]

    async def test_429_without_retry_after_falls_back_to_backoff(self, monkeypatch: Any) -> None:
        """无 Retry-After 时回退指数退避 + jitter（范围校验）."""
        monkeypatch.setattr(settings, "llm_run_call_budget", 0)
        reset_llm_call_count()

        delays: list[float] = []

        async def _patched_sleep(delay: float) -> None:
            delays.append(delay)

        async def _mock_ainvoke(*args: Any, **kwargs: Any) -> Any:
            raise FakeRateLimitError("rate limited", headers={})

        with patch("songyan.llm.client.get_llm") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.side_effect = _mock_ainvoke
            mock_get_llm.return_value = mock_llm
            with patch("asyncio.sleep", side_effect=_patched_sleep):
                with pytest.raises(LLMRateLimitError):
                    await call_llm("prompt", max_retries=3)

        # 指数退避：base 1.0 * 2^attempt * jitter(0.75-1.25)，<= max_delay
        assert len(delays) == 2
        for delay in delays:
            assert 0.0 < delay <= 10.0

    async def test_programming_error_not_retried(self, monkeypatch: Any) -> None:
        """TypeError 等编程异常直接抛出，不重试."""
        monkeypatch.setattr(settings, "llm_run_call_budget", 0)
        reset_llm_call_count()

        async def _mock_ainvoke(*args: Any, **kwargs: Any) -> Any:
            raise TypeError("bad arg")

        with patch("songyan.llm.client.get_llm") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.side_effect = _mock_ainvoke
            mock_get_llm.return_value = mock_llm
            with pytest.raises(TypeError, match="bad arg"):
                await call_llm("prompt")


# --------------------------------------------------------------------------- #
# retry_with_backoff generic behavior
# --------------------------------------------------------------------------- #
class TestRetryWithBackoff:
    async def test_retry_with_backoff_uses_retry_after(self, monkeypatch: Any) -> None:
        """retry_with_backoff 看到 LLMRateLimitError.retry_after 时按建议等待."""
        monkeypatch.setattr(settings, "llm_rate_limit_max_wait", 3.0)

        delays: list[float] = []

        async def _patched_sleep(delay: float) -> None:
            delays.append(delay)

        async def _invoke() -> str:
            raise LLMRateLimitError("rate limited", retry_after=2.5)

        with patch("asyncio.sleep", side_effect=_patched_sleep):
            with pytest.raises(LLMRateLimitError):
                await retry_with_backoff(
                    _invoke,
                    max_retries=2,
                    base_delay=0.1,
                    max_delay=100.0,
                    retryable_exceptions=(LLMError,),
                )

        assert delays == [2.5]

    async def test_retry_with_backoff_falls_back_without_retry_after(self) -> None:
        """LLMRateLimitError 无 retry_after 时回退指数退避."""
        async def _invoke() -> str:
            raise LLMRateLimitError("rate limited", retry_after=None)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(LLMRateLimitError):
                await retry_with_backoff(
                    _invoke,
                    max_retries=3,
                    base_delay=0.1,
                    max_delay=1.0,
                    retryable_exceptions=(LLMError,),
                )

        assert mock_sleep.call_count == 2
        for call in mock_sleep.call_args_list:
            assert 0.0 < call.args[0] <= 1.0


# --------------------------------------------------------------------------- #
# Per-run budget
# --------------------------------------------------------------------------- #
class TestPerRunBudget:
    def test_reset_and_get_count(self) -> None:
        reset_llm_call_count()
        assert get_llm_call_count() == 0

    async def test_budget_zero_never_trips(self, monkeypatch: Any) -> None:
        """budget=0 时不熔断."""
        monkeypatch.setattr(settings, "llm_run_call_budget", 0)
        reset_llm_call_count()

        with patch("songyan.llm.client.get_llm") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = type("R", (), {"content": "ok"})()
            mock_get_llm.return_value = mock_llm
            for _ in range(5):
                assert await call_llm("prompt") == "ok"

    async def test_budget_trips_on_nth_plus_one_call(self, monkeypatch: Any) -> None:
        """budget=N 时第 N+1 次 call_llm 抛 LLMBudgetExceededError."""
        monkeypatch.setattr(settings, "llm_run_call_budget", 2)
        reset_llm_call_count()
        set_llm_budget_last_chapter(7)

        with patch("songyan.llm.client.get_llm") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = type("R", (), {"content": "ok"})()
            mock_get_llm.return_value = mock_llm
            assert await call_llm("p1") == "ok"
            assert await call_llm("p2") == "ok"
            with pytest.raises(LLMBudgetExceededError) as exc_info:
                await call_llm("p3")
            assert exc_info.value.used_calls == 2
            assert exc_info.value.budget == 2
            assert exc_info.value.last_chapter == 7

    def test_count_isolation_between_runs(self, monkeypatch: Any) -> None:
        """不同 run 的计数互不串扰（通过 reset 隔离）."""
        monkeypatch.setattr(settings, "llm_run_call_budget", 1)
        reset_llm_call_count()
        assert get_llm_call_count() == 0
        # 模拟一次调用后计数
        from songyan.llm.client import _llm_call_count

        _llm_call_count.set(1)
        assert get_llm_call_count() == 1
        reset_llm_call_count()
        assert get_llm_call_count() == 0


# --------------------------------------------------------------------------- #
# Pipeline-level budget pause
# --------------------------------------------------------------------------- #
class TestPipelineBudgetPause:
    async def test_budget_exceeded_pauses_run(self, monkeypatch: Any) -> None:
        """phase2_graph 捕获 LLMBudgetExceededError 并将 run 置 paused."""
        monkeypatch.setattr(settings, "llm_run_call_budget", 1)
        reset_llm_call_count()

        saved_states: list[Any] = []

        async def _capture_state(state: Any) -> None:
            saved_states.append(state.model_copy(deep=True))

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            # 第一次成功，第二次触发预算熔断
            if kwargs["chapter_number"] == 1:
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
            raise LLMBudgetExceededError(
                "budget exceeded",
                used_calls=1,
                budget=1,
                last_chapter=kwargs["chapter_number"],
            )

        with (
            patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
            patch("songyan.workflows.phase2_graph._save_run_state", side_effect=_capture_state),
            patch("songyan.workflows.phase2_graph.reset_checkpointer", new_callable=AsyncMock),
        ):
            with pytest.raises(LLMBudgetExceededError):
                await run_project_pipeline(
                    project_id="proj-154",
                    chapter_range=(1, 3),
                    auto_confirm=True,
                )

        assert saved_states[-1].status == "paused"
        assert saved_states[-1].completed_chapters == [1]
        assert saved_states[-1].failed_chapters == []

    async def test_max_retries_from_settings(self, monkeypatch: Any) -> None:
        """call_llm max_retries=None 时回退 settings.llm_max_retries."""
        monkeypatch.setattr(settings, "llm_max_retries", 2)
        monkeypatch.setattr(settings, "llm_run_call_budget", 0)
        reset_llm_call_count()

        with patch("songyan.llm.client.retry_with_backoff") as mock_retry:
            mock_retry.return_value = "ok"
            await call_llm("prompt", max_retries=None)

        assert mock_retry.call_args.kwargs["max_retries"] == 2
