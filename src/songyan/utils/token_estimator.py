"""Token 估算工具 — 从 context_manager 提取的公共组件."""

from __future__ import annotations

import json
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class TokenEstimator:
    """Token 估算器 — tiktoken 为主，字符数/2 为回退."""

    def __init__(self) -> None:
        self._encoder: Any | None = None
        self._fallback: bool = False
        try:
            import tiktoken

            self._encoder = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            self._fallback = True
            logger.warning("token_estimator.fallback", reason="tiktoken_unavailable")

    def estimate(self, text: str) -> int:
        """估算文本的 Token 数."""
        if not text:
            return 0
        if self._encoder is not None and not self._fallback:
            try:
                return len(self._encoder.encode(text))
            except (UnicodeDecodeError, ValueError, TypeError):
                pass
        # 回退：中文字符 ≈ 1 token，ASCII ≈ 0.25 token，平均按 len/2
        return max(1, len(text) // 2)

    def estimate_model(self, obj: BaseModel | dict | list | None) -> int:
        """估算 Pydantic 模型 / dict / list 的 Token 数."""
        if obj is None:
            return 0
        if isinstance(obj, BaseModel):
            text = json.dumps(obj.model_dump(mode="json"), ensure_ascii=False, default=str)
        elif isinstance(obj, (dict, list)):
            text = json.dumps(obj, ensure_ascii=False, default=str)
        else:
            text = str(obj)
        return self.estimate(text)


def truncate_to_tokens(text: str, max_tokens: int, estimator: TokenEstimator | None = None) -> str:
    """将文本截断到指定 Token 预算内（保留开头）.

    使用二分查找逼近目标 token 数，避免过度截断。
    """
    if not text:
        return text
    estimator = estimator or TokenEstimator()
    if estimator.estimate(text) <= max_tokens:
        return text

    # 二分查找截断点
    low, high = 0, len(text)
    while low < high - 1:
        mid = (low + high) // 2
        truncated = text[:mid]
        if estimator.estimate(truncated) <= max_tokens:
            low = mid
        else:
            high = mid

    return text[:low] + "\n...（正文已截断）"
