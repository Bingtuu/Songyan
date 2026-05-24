"""Songyan 自定义异常体系."""

from __future__ import annotations


class SongyanError(Exception):
    """所有 Songyan 异常的基类."""


class LLMError(SongyanError):
    """LLM API 调用失败（重试后仍失败）."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class LLMResponseParseError(SongyanError):
    """LLM 返回内容无法解析为预期格式."""

    def __init__(self, message: str, *, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response
