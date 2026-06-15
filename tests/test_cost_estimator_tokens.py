"""Tests for cost estimator token-based estimation (Task 033 A2-2)."""

from __future__ import annotations

from songyan.utils.cost_estimator import (
    estimate_cost,
    estimate_cost_from_tokens,
    format_cost_estimate,
)


class TestEstimateCostFromTokens:
    """基于精确 token 数的成本估算测试."""

    def test_basic_calculation(self) -> None:
        """基本计算：1000 input + 500 output tokens @ ¥1/¥2 per M."""
        cost = estimate_cost_from_tokens(1000, 500, model="deepseek-chat")
        # input: 1000 * 1 / 1M = 0.001
        # output: 500 * 2 / 1M = 0.001
        expected = 0.002
        assert abs(cost - expected) < 0.0001

    def test_zero_tokens(self) -> None:
        """0 tokens → 0 cost."""
        cost = estimate_cost_from_tokens(0, 0)
        assert cost == 0.0

    def test_only_input_tokens(self) -> None:
        cost = estimate_cost_from_tokens(1_000_000, 0)
        assert abs(cost - 1.0) < 0.0001

    def test_only_output_tokens(self) -> None:
        cost = estimate_cost_from_tokens(0, 1_000_000)
        assert abs(cost - 2.0) < 0.0001

    def test_consistency_with_text_estimate(self) -> None:
        """token 估算和文本估算应保持一致性（误差在合理范围内）."""
        prompt = "这是一个测试 prompt。" * 100  # ~1700 字符
        response = "这是一个测试 response。" * 100

        text_cost = estimate_cost(prompt, response, model="deepseek-chat")
        token_cost = estimate_cost_from_tokens(
            len(prompt) // 2, len(response) // 2, model="deepseek-chat"
        )

        # 两种估算应在同一数量级
        assert text_cost > 0
        assert token_cost > 0
        ratio = max(text_cost, token_cost) / min(text_cost, token_cost)
        assert ratio < 3.0  # 误差不超过 3 倍

    def test_unknown_model_uses_default(self) -> None:
        cost = estimate_cost_from_tokens(1000, 500, model="unknown-model")
        assert cost > 0

    def test_real_world_estimate_accuracy(self) -> None:
        """模拟真实调用：65K input + 45K output（科幻基线数据）."""
        # 来自 evals/output/MULTI_GENRE_REPORT.md
        # 科幻：~65,000 input chars, ~45,000 output chars
        # cl100k_base 对中文约 1.3-1.5 tokens/char
        input_tokens = int(65000 / 1.5)
        output_tokens = int(45000 / 1.5)
        cost = estimate_cost_from_tokens(input_tokens, output_tokens)
        # 预期 ~¥0.10-0.15（与实际账单误差 <= 20%）
        assert 0.08 < cost < 0.15


class TestFormatCostEstimate:
    def test_format_zero(self) -> None:
        assert "0.00" in format_cost_estimate(0.0)

    def test_format_small(self) -> None:
        result = format_cost_estimate(0.15)
        assert "¥" in result
        assert "0.15" in result

    def test_format_medium(self) -> None:
        result = format_cost_estimate(1.5)
        assert "¥" in result
        assert "1.50" in result
