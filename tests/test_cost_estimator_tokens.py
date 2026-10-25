"""Tests for cost estimator token-based estimation (Task 033 A2-2)."""

from __future__ import annotations

from structlog.testing import capture_logs

from songyan.utils import cost_estimator as cost_estimator_module
from songyan.utils.cost_estimator import (
    CHAT_COST_BASIS_LABEL,
    OWNER_CHAT_INPUT_CNY_PER_MILLION,
    OWNER_CHAT_OUTPUT_CNY_PER_MILLION,
    PRICING,
    estimate_cost,
    estimate_cost_from_tokens,
    format_cost_estimate,
)


class TestEstimateCostFromTokens:
    """基于精确 token 数的成本估算测试."""

    def test_basic_calculation(self) -> None:
        """基本计算：1000 input + 500 output tokens @ 用户口径 ¥2/¥8 per M."""
        cost = estimate_cost_from_tokens(1000, 500, model="deepseek-chat")
        # input: 1000 * 2 / 1M = 0.002
        # output: 500 * 8 / 1M = 0.004
        expected = 0.006
        assert abs(cost - expected) < 0.0001

    def test_zero_tokens(self) -> None:
        """0 tokens → 0 cost."""
        cost = estimate_cost_from_tokens(0, 0)
        assert cost == 0.0

    def test_only_input_tokens(self) -> None:
        cost = estimate_cost_from_tokens(1_000_000, 0)
        assert abs(cost - OWNER_CHAT_INPUT_CNY_PER_MILLION) < 0.0001

    def test_only_output_tokens(self) -> None:
        cost = estimate_cost_from_tokens(0, 1_000_000)
        assert abs(cost - OWNER_CHAT_OUTPUT_CNY_PER_MILLION) < 0.0001

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

    def test_real_world_estimate_uses_owner_chat_basis(self) -> None:
        """65K/45K 字符量级按用户口径计价，不拿旧 ¥1/¥2 表当账单."""
        input_tokens = int(65000 / 1.5)
        output_tokens = int(45000 / 1.5)
        cost = estimate_cost_from_tokens(input_tokens, output_tokens)
        expected = (
            input_tokens * OWNER_CHAT_INPUT_CNY_PER_MILLION / 1_000_000
            + output_tokens * OWNER_CHAT_OUTPUT_CNY_PER_MILLION / 1_000_000
        )
        assert abs(cost - expected) < 0.0001
        assert cost > 0.30


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


class TestPricingFallback:
    """Task 232：未知模型定价口径——回落 default + 每模型每进程 warning 一次."""

    def setup_method(self) -> None:
        cost_estimator_module._warned_unknown_models.clear()

    def test_unknown_model_falls_back_to_default_with_warning_once(self) -> None:
        with capture_logs() as logs:
            cost1 = estimate_cost_from_tokens(1000, 500, model="some-new-model")
            estimate_cost_from_tokens(1000, 500, model="some-new-model")
        # 回落 default（与 deepseek-chat 同一用户口径 ¥2/¥8）
        assert cost1 == estimate_cost_from_tokens(1000, 500, model="deepseek-chat")
        warnings = [e for e in logs if e["event"] == "llm.pricing_unknown_model"]
        assert len(warnings) == 1
        assert warnings[0]["model"] == "some-new-model"

    def test_deepseek_reasoner_pricing_entry(self) -> None:
        # 2025-09 V3.1 调价口径：输入 ¥4 / 输出 ¥12 每 1M
        cost = estimate_cost_from_tokens(1_000_000, 1_000_000, model="deepseek-reasoner")
        assert abs(cost - 16.0) < 0.0001
        cost_prefixed = estimate_cost_from_tokens(
            1_000_000, 0, model="deepseek/deepseek-reasoner"
        )
        assert abs(cost_prefixed - 4.0) < 0.0001


class TestOwnerChatCostBasis:
    """B18：chat 标签锁在用户口径，reasoner/coder 价目不动，也不改 provider 账单."""

    def test_chat_constants_and_aliases(self) -> None:
        assert OWNER_CHAT_INPUT_CNY_PER_MILLION == 2.0
        assert OWNER_CHAT_OUTPUT_CNY_PER_MILLION == 8.0
        assert "¥2/M" in CHAT_COST_BASIS_LABEL
        assert "¥8/M" in CHAT_COST_BASIS_LABEL
        assert "不是 DeepSeek 账单" in CHAT_COST_BASIS_LABEL
        for model in ("deepseek-chat", "deepseek/deepseek-chat", "default"):
            assert PRICING[model]["input"] == 2.0
            assert PRICING[model]["output"] == 8.0
        assert PRICING["deepseek-reasoner"] == {"input": 4.0, "output": 12.0}
        assert PRICING["deepseek/deepseek-reasoner"] == {"input": 4.0, "output": 12.0}
        assert PRICING["deepseek/deepseek-coder"] == {"input": 1.0, "output": 2.0}

    def test_three_chapter_note_relabel(self) -> None:
        """旧 ¥1/¥2 自报 ¥0.458 的 token 量，按用户口径为 ¥1.37."""
        prompt_tokens = 231_000
        completion_tokens = 113_500
        old_basis = prompt_tokens * 1.0 / 1_000_000 + completion_tokens * 2.0 / 1_000_000
        labeled = estimate_cost_from_tokens(
            prompt_tokens, completion_tokens, model="deepseek-chat"
        )
        assert abs(old_basis - 0.458) < 1e-9
        assert abs(labeled - 1.37) < 1e-9
