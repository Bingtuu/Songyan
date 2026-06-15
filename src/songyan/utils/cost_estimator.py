"""LLM 调用成本估算 — 基于 tiktoken 精确 token 计数."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# DeepSeek API 定价（CNY / 1M tokens，2025-05）
# 输入：缓存命中 ¥0.1，缓存未命中 ¥1.0
# 输出：¥2.0
# 保守估算使用缓存未命中价格
PRICING: dict[str, dict[str, float]] = {
    "deepseek/deepseek-chat": {
        "input": 1.0,
        "output": 2.0,
    },
    "deepseek/deepseek-coder": {
        "input": 1.0,
        "output": 2.0,
    },
    "deepseek-chat": {
        "input": 1.0,
        "output": 2.0,
    },
    # 默认兜底
    "default": {
        "input": 1.0,
        "output": 2.0,
    },
}


def _get_pricing(model: str) -> dict[str, float]:
    """获取模型定价，未知模型使用默认定价."""
    return PRICING.get(model, PRICING["default"])


def count_tokens(text: str, model: str = "deepseek-chat") -> int:
    """使用 tiktoken 计算文本的 token 数.

    Args:
        text: 待计算的文本
        model: 模型标识（用于选择 tokenizer）

    Returns:
        token 数量
    """
    try:
        import tiktoken

        # DeepSeek 使用 cl100k_base（与 GPT-4 相同）
        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text))
    except (ImportError, ValueError, TypeError):
        # tiktoken 不可用时 fallback 到粗略估算（1 token ≈ 2 中文字符）
        return len(text) // 2


def estimate_cost(
    prompt_text: str,
    response_text: str,
    model: str = "deepseek-chat",
) -> float:
    """估算单次 LLM 调用的成本（CNY）.

    Args:
        prompt_text: prompt 文本
        response_text: response 文本
        model: 模型标识

    Returns:
        预估成本（人民币）
    """
    pricing = _get_pricing(model)
    input_tokens = count_tokens(prompt_text, model)
    output_tokens = count_tokens(response_text, model)

    input_cost = input_tokens * pricing["input"] / 1_000_000
    output_cost = output_tokens * pricing["output"] / 1_000_000

    return input_cost + output_cost


def estimate_cost_from_tokens(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "deepseek-chat",
) -> float:
    """基于精确 token 数估算成本（比文本估算更精确）.

    Args:
        prompt_tokens: 输入 token 数（如 litellm 实际返回）
        completion_tokens: 输出 token 数（如 litellm 实际返回）
        model: 模型标识

    Returns:
        预估成本（人民币）
    """
    pricing = _get_pricing(model)
    input_cost = prompt_tokens * pricing["input"] / 1_000_000
    output_cost = completion_tokens * pricing["output"] / 1_000_000
    return input_cost + output_cost


def estimate_cost_from_calls(
    calls: list[dict[str, Any]],
    model: str = "deepseek-chat",
) -> float:
    """从调用记录列表估算总成本.

    Args:
        calls: 调用记录列表，每个记录包含 prompt_chars / response_chars / agent
        model: 模型标识

    Returns:
        预估总成本（人民币）
    """

    total = 0.0
    for call in calls:
        prompt = call.get("prompt_chars", "")
        response = call.get("response_chars", "")
        # prompt_chars 可能是 str 或 int（如果是 str 则直接使用）
        if isinstance(prompt, int):
            prompt = " " * prompt
        if isinstance(response, int):
            response = " " * response
        total += estimate_cost(prompt, response, model)
    return total


def format_cost_estimate(cost_cny: float) -> str:
    """格式化成本估算为可读字符串."""
    if cost_cny < 0.01:
        return f"~¥{cost_cny:.4f}"
    if cost_cny < 1.0:
        return f"~¥{cost_cny:.2f}"
    return f"~¥{cost_cny:.2f}"
