"""Tests for LLM client — call_llm, get_llm, retry logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.exceptions import LLMError
from songyan.llm.client import call_llm, get_llm


class TestGetLlm:
    """LLM 实例获取测试."""

    def test_get_llm_returns_instance(self) -> None:
        """get_llm 应返回配置好的 ChatLiteLLM 实例."""
        with patch("songyan.llm.client.settings") as mock_settings:
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_base_url = "https://test.com"
            mock_settings.llm_model = "test-model"

            with patch("songyan.llm.client._get_llm_cached") as mock_cached:
                mock_instance = MagicMock()
                mock_cached.return_value = mock_instance

                result = get_llm()
                assert result is mock_instance
                mock_cached.assert_called_once()

    def test_get_llm_no_api_key_raises(self) -> None:
        """未配置 API Key 时应抛出 LLMError."""
        with patch("songyan.llm.client.settings") as mock_settings:
            mock_settings.llm_api_key = None
            mock_settings.llm_base_url = None
            mock_settings.llm_model = None

            with patch.dict("os.environ", {}, clear=True):
                with pytest.raises(LLMError):
                    get_llm()


class TestCallLlm:
    """LLM 调用测试."""

    @pytest.mark.asyncio
    async def test_call_llm_success(self) -> None:
        """正常调用应返回 LLM 响应文本."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Hello, world!"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        async def _passthrough(coro, **kwargs):
            return await coro()

        with patch("songyan.llm.client.get_llm", return_value=mock_llm):
            with patch(
                "songyan.llm.client.retry_with_backoff", new_callable=AsyncMock
            ) as mock_retry:
                mock_retry.side_effect = _passthrough
                result = await call_llm("test prompt")
                assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_call_llm_normalizes_content_blocks(self) -> None:
        """DeepSeek v4 / LiteLLM content blocks should expose only text blocks."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            {"type": "thinking", "thinking": "internal reasoning"},
            {"type": "text", "text": '{"ok": true}'},
        ]
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        async def _passthrough(coro, **kwargs):
            return await coro()

        with patch("songyan.llm.client.get_llm", return_value=mock_llm):
            with patch(
                "songyan.llm.client.retry_with_backoff", new_callable=AsyncMock
            ) as mock_retry:
                mock_retry.side_effect = _passthrough
                result = await call_llm("test prompt")
                assert result == '{"ok": true}'

    @pytest.mark.asyncio
    async def test_call_llm_skips_reasoning_only_blocks(self) -> None:
        """Reasoning-only content should not be stringified into downstream JSON."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [{"type": "reasoning", "content": "hidden"}]
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        async def _passthrough(coro, **kwargs):
            return await coro()

        with patch("songyan.llm.client.get_llm", return_value=mock_llm):
            with patch(
                "songyan.llm.client.retry_with_backoff", new_callable=AsyncMock
            ) as mock_retry:
                mock_retry.side_effect = _passthrough
                result = await call_llm("test prompt")
                assert result == ""

    @pytest.mark.asyncio
    async def test_call_llm_type_error_not_retried(self) -> None:
        """TypeError/ValueError/KeyError/AttributeError 不应触发重试，直接抛出."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=TypeError("bad arg"))

        with patch("songyan.llm.client.get_llm", return_value=mock_llm):
            with pytest.raises(TypeError):
                await call_llm("test prompt")

    @pytest.mark.asyncio
    async def test_call_llm_network_error_retried(self) -> None:
        """网络/API 错误应被包装为 LLMError 并触发重试."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=ConnectionError("network down"))

        async def _fail(coro, **kwargs):
            raise LLMError("all retries failed")

        with patch("songyan.llm.client.get_llm", return_value=mock_llm):
            with patch(
                "songyan.llm.client.retry_with_backoff", new_callable=AsyncMock
            ) as mock_retry:
                mock_retry.side_effect = _fail
                with pytest.raises(LLMError):
                    await call_llm("test prompt")

    @pytest.mark.asyncio
    async def test_call_llm_timeout_raises(self) -> None:
        """总超时应抛出 LLMError."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=TimeoutError("too slow"))

        async def _timeout(coro, **kwargs):
            raise TimeoutError("too slow")

        with patch("songyan.llm.client.get_llm", return_value=mock_llm):
            with patch(
                "songyan.llm.client.retry_with_backoff", new_callable=AsyncMock
            ) as mock_retry:
                mock_retry.side_effect = _timeout
                with pytest.raises(LLMError):
                    await call_llm("test prompt", max_retries=1)

    @pytest.mark.asyncio
    async def test_call_llm_temperature_defaults_to_settings(self) -> None:
        """Task 171c: temperature 未显式传入时应从 settings.llm_temperature 解析（去死配置）."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "ok"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        async def _passthrough(coro, **kwargs):
            return await coro()

        with patch("songyan.llm.client.get_llm", return_value=mock_llm) as mock_get:
            with patch("songyan.llm.client.settings") as mock_settings:
                mock_settings.llm_temperature = 0.42
                mock_settings.llm_max_retries = 3
                mock_settings.llm_run_call_budget = 0
                mock_settings.run_cost_budget = 0
                with patch(
                    "songyan.llm.client.retry_with_backoff", new_callable=AsyncMock
                ) as mock_retry:
                    mock_retry.side_effect = _passthrough
                    await call_llm("test prompt")
                    # get_llm 应收到来自 settings 的温度，而非旧的硬编码 0.7
                    assert mock_get.call_args.kwargs["temperature"] == 0.42

    @pytest.mark.asyncio
    async def test_call_llm_explicit_temperature_overrides_settings(self) -> None:
        """显式 temperature 优先于 settings（生产 caller 行为不变）."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "ok"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        async def _passthrough(coro, **kwargs):
            return await coro()

        with patch("songyan.llm.client.get_llm", return_value=mock_llm) as mock_get:
            with patch("songyan.llm.client.settings") as mock_settings:
                mock_settings.llm_temperature = 0.42
                mock_settings.llm_max_retries = 3
                mock_settings.llm_run_call_budget = 0
                mock_settings.run_cost_budget = 0
                with patch(
                    "songyan.llm.client.retry_with_backoff", new_callable=AsyncMock
                ) as mock_retry:
                    mock_retry.side_effect = _passthrough
                    await call_llm("test prompt", temperature=0.9)
                    assert mock_get.call_args.kwargs["temperature"] == 0.9
