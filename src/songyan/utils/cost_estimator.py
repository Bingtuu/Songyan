"""LLM 调用成本估算 — 基于 tiktoken 精确 token 计数."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# B18：chat 的报告 / 落库 cost_cny 用 owner 口径标签，不是 DeepSeek 账单。
# 输入 ¥2 / 1M tokens，输出 ¥8 / 1M tokens。
# 三章笔记：旧表（¥1/¥2）自报约 ¥0.458，同一 token 按本口径约为 ¥1.37。
# provider response_cost（USD）仍不入账，见 llm/client.py。
# deepseek-coder 保留旧缓存未命中表；deepseek-reasoner 保留 ¥4/¥12。
# 未知模型回落 default（与 deepseek-chat 同一用户口径）并 warning。
OWNER_CHAT_INPUT_CNY_PER_MILLION = 2.0
OWNER_CHAT_OUTPUT_CNY_PER_MILLION = 8.0

#: report 成本段标明的 chat 估算口径（标签，不是发票）
CHAT_COST_BASIS_LABEL = (
    "用户口径（chat 输入 ¥2/M、输出 ¥8/M；写入 cost_cny 的估算标签，不是 DeepSeek 账单）"
)

_OWNER_CHAT_RATES: dict[str, float] = {
    "input": OWNER_CHAT_INPUT_CNY_PER_MILLION,
    "output": OWNER_CHAT_OUTPUT_CNY_PER_MILLION,
}

PRICING: dict[str, dict[str, float]] = {
    "deepseek/deepseek-chat": dict(_OWNER_CHAT_RATES),
    # coder 不是 B18 的 chat 口径，保持 2025-05 缓存未命中价
    "deepseek/deepseek-coder": {
        "input": 1.0,
        "output": 2.0,
    },
    "deepseek-chat": dict(_OWNER_CHAT_RATES),
    # deepseek-reasoner：单独价目（缓存未命中输入 ¥4、输出 ¥12）
    "deepseek-reasoner": {
        "input": 4.0,
        "output": 12.0,
    },
    "deepseek/deepseek-reasoner": {
        "input": 4.0,
        "output": 12.0,
    },
    # 默认兜底：与 deepseek-chat 同一用户口径
    "default": dict(_OWNER_CHAT_RATES),
}

#: 已告警过的未知模型（每进程每模型只 warning 一次，避免热路径刷屏）
_warned_unknown_models: set[str] = set()


def _get_pricing(model: str) -> dict[str, float]:
    """获取模型定价；未知模型回落默认定价并 warning（每模型每进程一次）."""
    pricing = PRICING.get(model)
    if pricing is None:
        if model not in _warned_unknown_models:
            _warned_unknown_models.add(model)
            logger.warning("llm.pricing_unknown_model", model=model, fallback="default")
        pricing = PRICING["default"]
    return pricing


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
