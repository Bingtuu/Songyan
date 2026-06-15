"""LLM response parsing utilities — JSON extraction and validation."""

from __future__ import annotations

import json
import re

import structlog

from songyan.exceptions import LLMResponseParseError

logger = structlog.get_logger(__name__)


def _extract_json_balanced(text: str) -> str | None:
    """使用括号计数法提取第一个完整的 JSON 对象.

    支持嵌套结构，避免贪婪/非贪婪正则的缺陷。
    正确跳过 JSON 字符串内部的花括号。
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    end = start
    for i, ch in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if depth != 0:
        return None  # 未找到闭合的 JSON
    return text[start:end]


def _manual_json_repair(text: str) -> dict | None:
    """无 json_repair 库时的手动修复尝试.

    处理常见问题：markdown 代码块标记、尾部逗号、单引号、未引用 key 等。
    """
    if not text or not text.strip():
        return None

    cleaned = text.strip()
    # 去掉 markdown 代码块标记
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    # 去掉尾部逗号（JSON 标准不允许）
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    # 修复未引用的 key（如 {foo: "bar"} → {"foo": "bar"}）
    cleaned = re.sub(
        r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:',
        r'\1"\2":',
        cleaned,
    )

    # 修复单引号为双引号 — 只替换 JSON 字符串边界上的单引号
    # （如 "key": 'value'），避免破坏内容中的合法单引号（如 don't）
    cleaned = re.sub(
        r"(?<=[:\s])'([^']+)'(?=\s*[,}\]])",
        r'"\1"',
        cleaned,
    )

    # 尝试解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def extract_json(text: str) -> str:
    """从 LLM 响应中提取 JSON 字符串.

    处理以下情况：
    - 纯 JSON
    - markdown 代码块包裹的 JSON（仅提取第一个 code block）
    - 前后有额外文本的 JSON
    - 嵌套 JSON 对象

    限制：如果响应包含多个 markdown code block，仅提取第一个。
    如需处理多 block 场景，请在调用方确保 LLM 输出单一 JSON 块。
    """
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # 优先使用括号计数法（支持嵌套，不跨多个对象）
    balanced = _extract_json_balanced(text)
    if balanced is not None:
        return balanced

    return text.strip()


def parse_llm_response(text: str) -> dict:
    """解析 LLM 响应为字典.

    先尝试标准 json.loads，失败时 fallback 到 json_repair 库
    （处理 LLM 常见的 JSON 语法错误：尾部逗号、注释、未闭合字符串等）。

    Args:
        text: LLM 返回的原始文本

    Returns:
        解析后的字典

    Raises:
        LLMResponseParseError: 解析失败
    """
    json_text = extract_json(text)
    try:
        result = json.loads(json_text)
    except json.JSONDecodeError:
        # Fallback 1: 尝试 json_repair 库
        try:
            from json_repair import repair_json

            repaired = repair_json(json_text)
            result = json.loads(repaired)
        except (ImportError, ValueError, TypeError, RuntimeError):
            # Fallback 2: 无 json_repair 时的手动修复
            result = _manual_json_repair(json_text)
            if result is None:
                logger.warning(
                    "llm.parse_failed",
                    raw_preview=text[:200],
                    stage="all_fallbacks_exhausted",
                )
                msg = "LLM 返回内容无法解析为 JSON（标准解析和 repair 均失败）"
                raise LLMResponseParseError(msg, raw_response=text)

    if not isinstance(result, dict):
        msg = f"LLM 返回 JSON 非对象类型（实际为 {type(result).__name__}）"
        raise LLMResponseParseError(msg, raw_response=text)

    return result
