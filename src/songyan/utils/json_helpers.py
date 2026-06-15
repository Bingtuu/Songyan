"""JSON 序列化/反序列化公共工具 —— 原位于 db/repository.py 的私有函数提升."""

from __future__ import annotations

import json
from typing import Any


def _jsonable(value: Any) -> Any:
    """Recursively convert Pydantic models in containers to JSON-ready values."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def to_json(value: Any) -> str:
    """Convert Pydantic-friendly values to SQLite JSON text."""
    return json.dumps(_jsonable(value), ensure_ascii=False, default=str)


def from_json(value: str | None, default: Any = None) -> Any:
    """Convert SQLite JSON text to Python values."""
    if value is None:
        return default
    return json.loads(value)


def model_json(value: Any) -> str:
    """Serialize a Pydantic model or plain value as JSON text."""
    return to_json(value)
