"""LLM response parsing utilities — JSON extraction and validation."""

from __future__ import annotations

import json
import re

from songyan.exceptions import LLMResponseParseError


def extract_json(text: str) -> str:
    """从 LLM 响应中提取 JSON 字符串.

    处理以下情况：
    - 纯 JSON
    - markdown 代码块包裹的 JSON
    - 前后有额外文本的 JSON
    """
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    json_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()

    return text.strip()


def parse_llm_response(text: str) -> dict:
    """解析 LLM 响应为字典.

    Args:
        text: LLM 返回的原始文本

    Returns:
        解析后的字典

    Raises:
        LLMResponseParseError: 解析失败
    """
    json_text = extract_json(text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        msg = f"LLM 返回内容无法解析为 JSON: {e}"
        raise LLMResponseParseError(msg, raw_response=text) from e
