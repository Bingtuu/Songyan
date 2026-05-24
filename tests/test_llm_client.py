"""Tests for LLM Client infrastructure."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.exceptions import LLMError
from songyan.llm.client import call_llm, get_llm
from songyan.llm.retry import async_retry, retry_with_backoff


# ---------------------------------------------------------------------------
# get_llm
# ---------------------------------------------------------------------------
class TestGetLLM:
    """Tests for get_llm factory."""

    def test_get_llm_returns_instance(self) -> None:
        """get_llm 应返回配置好的 LLM 实例."""
        with patch("songyan.llm.client.settings") as mock_settings:
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_base_url = "https://test.com"
            mock_settings.llm_model = "test-model"

            with patch("langchain_litellm.ChatLiteLLM") as mock_llm:
                instance = MagicMock()
                mock_llm.return_value = instance

                result = get_llm(temperature=0.5)

                assert result is instance
                mock_llm.assert_called_once_with(
                    model="test-model",
                    api_key="test-key",
                    base_url="https://test.com",
                    temperature=0.5,
                    max_tokens=4096,
                )

    def test_get_llm_missing_api_key(self) -> None:
        """API Key 缺失时应抛出 LLMError."""
        with patch("songyan.llm.client.settings") as mock_settings:
            mock_settings.llm_api_key = ""
            mock_settings.llm_base_url = "https://test.com"
            mock_settings.llm_model = "test-model"

            with patch.dict("os.environ", {}, clear=True):
                with pytest.raises(LLMError) as exc_info:
                    get_llm()

                assert "API Key" in str(exc_info.value)

    def test_get_llm_import_error(self) -> None:
        """langchain-litellm 未安装时应抛出 LLMError."""
        with patch.dict("sys.modules", {"langchain_litellm": None}):
            with patch("builtins.__import__", side_effect=ImportError("no module")):
                with pytest.raises(LLMError) as exc_info:
                    get_llm()

                assert "未安装" in str(exc_info.value)


# ---------------------------------------------------------------------------
# retry_with_backoff
# ---------------------------------------------------------------------------
class TestRetryWithBackoff:
    """Tests for retry_with_backoff."""

    async def test_success_first_attempt(self) -> None:
        """首次调用成功，不触发重试."""
        coro = AsyncMock(return_value="ok")

        result = await retry_with_backoff(coro)

        assert result == "ok"
        assert coro.await_count == 1

    async def test_eventual_success(self) -> None:
        """前两次失败，第三次成功."""
        coro = AsyncMock(side_effect=[ValueError("fail1"), ValueError("fail2"), "ok"])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(coro, max_retries=3)

        assert result == "ok"
        assert coro.await_count == 3
        # 指数退避: 1.0, 2.0
        assert mock_sleep.await_count == 2
        mock_sleep.assert_any_await(1.0)
        mock_sleep.assert_any_await(2.0)

    async def test_all_failures(self) -> None:
        """所有重试均失败，抛出 LLMError."""
        coro = AsyncMock(side_effect=[ValueError("fail")] * 3)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMError) as exc_info:
                await retry_with_backoff(coro, max_retries=3)

        assert "已重试 3 次" in str(exc_info.value)
        assert coro.await_count == 3

    async def test_max_delay_cap(self) -> None:
        """延迟不超过 max_delay."""
        coro = AsyncMock(side_effect=[ValueError("fail")] * 4)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(LLMError):
                await retry_with_backoff(
                    coro,
                    max_retries=4,
                    base_delay=5.0,
                    max_delay=8.0,
                )

        # delays: 5.0, 8.0(cap), 8.0(cap)
        assert mock_sleep.await_count == 3
        mock_sleep.assert_any_await(5.0)
        mock_sleep.assert_any_await(8.0)


# ---------------------------------------------------------------------------
# async_retry decorator
# ---------------------------------------------------------------------------
class TestAsyncRetry:
    """Tests for async_retry decorator."""

    async def test_decorator_success(self) -> None:
        """装饰器：正常执行."""

        @async_retry(max_retries=2)
        async def flaky() -> str:
            return "ok"

        result = await flaky()
        assert result == "ok"

    async def test_decorator_eventual_success(self) -> None:
        """装饰器：重试后成功."""
        call_count = 0

        @async_retry(max_retries=3)
        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await flaky()

        assert result == "ok"
        assert call_count == 3


# ---------------------------------------------------------------------------
# call_llm
# ---------------------------------------------------------------------------
class TestCallLLM:
    """Tests for call_llm wrapper."""

    async def test_call_llm_success(self) -> None:
        """正常调用返回 LLM 响应文本."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Hello, world!"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("songyan.llm.client.get_llm", return_value=mock_llm):
            result = await call_llm("test prompt")

        assert result == "Hello, world!"
        mock_llm.ainvoke.assert_awaited_once()

    async def test_call_llm_retry_then_success(self) -> None:
        """LLM 调用失败两次后成功."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "ok"
        mock_llm.ainvoke = AsyncMock(
            side_effect=[ConnectionError("fail1"), ConnectionError("fail2"), mock_response],
        )

        with patch("songyan.llm.client.get_llm", return_value=mock_llm):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await call_llm("test prompt")

        assert result == "ok"
        assert mock_llm.ainvoke.await_count == 3

    async def test_call_llm_all_retries_fail(self) -> None:
        """所有重试均失败."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=ConnectionError("fail"))

        with patch("songyan.llm.client.get_llm", return_value=mock_llm):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(LLMError) as exc_info:
                    await call_llm("test prompt")

        assert mock_llm.ainvoke.await_count == 3
        assert "LLM 调用失败" in str(exc_info.value)
