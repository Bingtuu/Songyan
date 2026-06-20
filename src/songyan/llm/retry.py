"""指数退避重试工具."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

import structlog

from songyan.exceptions import LLMError

logger = structlog.get_logger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    coro: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retryable_exceptions: tuple[type[Exception], ...] = (LLMError, TimeoutError, ConnectionError),
    **kwargs: Any,
) -> T:
    """执行异步函数，失败时指数退避重试.

    Args:
        coro: 要执行的异步函数
        max_retries: 最大重试次数（含首次调用，即最多执行 max_retries 次）
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        retryable_exceptions: 哪些异常类型会触发重试

    Returns:
        函数返回值

    Raises:
        LLMError: 所有重试均失败后抛出
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries):
        try:
            return await coro(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = min(
                    base_delay * (2**attempt) * random.uniform(0.75, 1.25), max_delay
                )  # PERF-06: +jitter
                logger.warning(
                    "llm.retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)

    msg = f"LLM 调用失败，已重试 {max_retries} 次: {last_exception}"
    raise LLMError(msg, cause=last_exception)


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retryable_exceptions: tuple[type[Exception], ...] = (LLMError, TimeoutError, ConnectionError),
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """装饰器：为异步函数添加指数退避重试."""

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_with_backoff(
                func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions,
                **kwargs,
            )

        return wrapper

    return decorator
