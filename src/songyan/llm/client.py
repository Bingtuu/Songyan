"""LLM Client —— 统一封装 LangChain + litellm."""

from __future__ import annotations

import asyncio
import os
from functools import lru_cache
from typing import TYPE_CHECKING

import structlog

from songyan.config import settings
from songyan.exceptions import LLMError
from songyan.llm.retry import retry_with_backoff

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import BaseMessage

logger = structlog.get_logger(__name__)


@lru_cache(maxsize=8)
def _get_llm_cached(model: str, api_key: str, base_url: str, temperature: float, max_tokens: int) -> BaseChatModel:
    """缓存 LLM 实例，避免每次调用都重新创建."""
    from langchain_litellm import ChatLiteLLM

    return ChatLiteLLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=60,
    )


def get_llm(temperature: float = 0.7, max_tokens: int = 4096) -> BaseChatModel:
    """获取配置好的 LLM 实例（带缓存）.

    使用 litellm 统一接口，通过环境变量或 settings 配置模型参数。
    相同参数组合会复用已创建的实例。

    Args:
        temperature: 采样温度
        max_tokens: 最大输出 token 数（默认 4096）

    Returns:
        配置好的 ChatLiteLLM 实例

    Raises:
        LLMError: 配置缺失或模型初始化失败
    """
    import importlib.util

    if importlib.util.find_spec("langchain_litellm") is None:
        msg = "langchain-litellm 未安装，无法初始化 LLM"
        raise LLMError(msg)

    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY", "")
    base_url = settings.llm_base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    model = settings.llm_model or os.getenv("LLM_MODEL", "deepseek-chat")

    if not api_key:
        msg = "LLM API Key 未配置（请设置 LLM_API_KEY 环境变量或在 .env 中配置 llm_api_key）"
        raise LLMError(msg)

    try:
        llm = _get_llm_cached(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except (ImportError, ValueError, TypeError, RuntimeError, ConnectionError) as e:
        msg = f"LLM 初始化失败 (model={model}): {e}"
        raise LLMError(msg, cause=e) from e

    logger.debug(
        "llm.init",
        model=model,
        base_url=base_url,
        temperature=temperature,
    )
    return llm


async def call_llm(
    prompt: str,
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    max_retries: int = 3,
) -> str:
    """调用 LLM 并返回文本响应.

    自带指数退避重试。

    Args:
        prompt: 发送给 LLM 的提示文本
        temperature: 采样温度
        max_tokens: 最大输出 token 数（默认 4096）
        max_retries: 最大重试次数

    Returns:
        LLM 返回的文本内容

    Raises:
        LLMError: 调用失败（重试后仍失败）
    """
    llm = get_llm(temperature=temperature, max_tokens=max_tokens)

    async def _invoke() -> str:
        try:
            from langchain_core.messages import HumanMessage

            response: BaseMessage = await llm.ainvoke([HumanMessage(content=prompt)])
            return str(response.content)
        except (TypeError, ValueError, KeyError, AttributeError):
            # 编程错误（参数类型、配置错误等），直接抛出，不重试
            raise
        except Exception as e:
            # 网络/API 瞬态错误，包装为 LLMError 以便重试
            raise LLMError(f"LLM 调用失败: {e}", cause=e) from e

    try:
        # 总超时 = 单次超时 60s * 最大重试次数 + 退避延迟缓冲
        total_timeout = 60 * max_retries + 30
        return await asyncio.wait_for(
            retry_with_backoff(
                _invoke,
                max_retries=max_retries,
                base_delay=1.0,
                max_delay=10.0,
                retryable_exceptions=(LLMError,),
            ),
            timeout=total_timeout,
        )
    except TimeoutError as e:
        raise LLMError(
            f"LLM 调用总超时（超过 {total_timeout} 秒）", cause=e
        ) from e
    except LLMError:
        raise
