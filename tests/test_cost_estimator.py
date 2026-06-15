"""Tests for cost estimator (Task 025)."""

from __future__ import annotations

from songyan.utils.cost_estimator import (
    count_tokens,
    estimate_cost,
    estimate_cost_from_calls,
    format_cost_estimate,
)


class TestCountTokens:
    def test_chinese_text(self) -> None:
        """中文字符的 token 计数应大于 0."""
        tokens = count_tokens("这是一个测试文本。", model="deepseek-chat")
        assert tokens > 0
        # cl100k_base 中每个中文字符约 1-2 tokens
        assert tokens >= 5

    def test_english_text(self) -> None:
        """英文文本的 token 计数."""
        tokens = count_tokens("Hello world", model="deepseek-chat")
        assert tokens > 0

    def test_empty_text(self) -> None:
        assert count_tokens("") == 0


class TestEstimateCost:
    def test_deepseek_chat_cost(self) -> None:
        """DeepSeek 定价：输入 ¥1/M，输出 ¥2/M."""
        prompt = "这是一个测试 prompt。" * 100  # ~1700 字符
        response = "这是一个测试 response。" * 100  # ~2100 字符
        cost = estimate_cost(prompt, response, model="deepseek-chat")
        assert cost > 0
        # 2000 字符 / 2 ≈ 1000 tokens
        # cost ≈ 1000 * 1 / 1M + 1000 * 2 / 1M = ¥0.003
        assert cost < 0.1  # 应远低于旧估算

    def test_unknown_model_uses_default(self) -> None:
        cost = estimate_cost("test", "test", model="unknown-model")
        assert cost > 0


class TestEstimateCostFromCalls:
    def test_multiple_calls(self) -> None:
        calls = [
            {"prompt_chars": 1000, "response_chars": 500},
            {"prompt_chars": 2000, "response_chars": 1000},
        ]
        total = estimate_cost_from_calls(calls)
        assert total > 0
        # 验证是单次的累加
        single = estimate_cost(" " * 1000, " " * 500)
        double = estimate_cost(" " * 2000, " " * 1000)
        assert abs(total - (single + double)) < 0.001


class TestFormatCostEstimate:
    def test_small_cost(self) -> None:
        assert "0.00" in format_cost_estimate(0.001)

    def test_medium_cost(self) -> None:
        assert "~¥0.15" == format_cost_estimate(0.15)

    def test_large_cost(self) -> None:
        assert "~¥1.50" == format_cost_estimate(1.5)
