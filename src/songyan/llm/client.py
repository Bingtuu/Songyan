"""LLM Client —— 统一封装 LangChain + litellm."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import structlog

from songyan.config import settings
from songyan.exceptions import LLMError
from songyan.llm.retry import retry_with_backoff

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import BaseMessage

logger = structlog.get_logger(__name__)


def get_llm(temperature: float = 0.7) -> BaseChatModel:
    """获取配置好的 LLM 实例.

    使用 litellm 统一接口，通过环境变量或 settings 配置模型参数。

    Args:
        temperature: 采样温度

    Returns:
        配置好的 ChatLiteLLM 实例

    Raises:
        LLMError: 配置缺失或模型初始化失败
    """
    try:
        from langchain_litellm import ChatLiteLLM
    except ImportError as e:
        msg = "langchain-litellm 未安装，无法初始化 LLM"
        raise LLMError(msg, cause=e) from e

    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY", "")
    base_url = settings.llm_base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    model = settings.llm_model or os.getenv("LLM_MODEL", "deepseek-chat")

    if not api_key:
        msg = "LLM API Key 未配置（请设置 LLM_API_KEY 环境变量或在 .env 中配置 llm_api_key）"
        raise LLMError(msg)

    try:
        llm = ChatLiteLLM(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=4096,
        )
    except Exception as e:
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
    max_retries: int = 3,
) -> str:
    """调用 LLM 并返回文本响应.

    自带指数退避重试。

    Args:
        prompt: 发送给 LLM 的提示文本
        temperature: 采样温度
        max_retries: 最大重试次数

    Returns:
        LLM 返回的文本内容

    Raises:
        LLMError: 调用失败（重试后仍失败）
    """
    llm = get_llm(temperature=temperature)

    async def _invoke() -> str:
        response: BaseMessage = await llm.ainvoke(prompt)
        return str(response.content)

    try:
        return await retry_with_backoff(
            _invoke,
            max_retries=max_retries,
            base_delay=1.0,
            max_delay=10.0,
            retryable_exceptions=(Exception,),
        )
    except LLMError:
        raise
    except Exception as e:
        msg = f"LLM 调用失败: {e}"
        raise LLMError(msg, cause=e) from e
