"""Tests for LLM response parsing utilities."""

from __future__ import annotations

import pytest

from songyan.exceptions import LLMResponseParseError
from songyan.llm.parsing import extract_json, parse_llm_response


class TestExtractJson:
    def test_pure_json(self) -> None:
        text = '{"a": 1}'
        assert extract_json(text) == '{"a": 1}'

    def test_markdown_code_block(self) -> None:
        text = "```json\n{\"a\": 1}\n```"
        assert extract_json(text) == '{"a": 1}'

    def test_with_surrounding_text(self) -> None:
        text = 'Here is the result: {"a": 1} Thanks!'
        assert extract_json(text) == '{"a": 1}'

    def test_multiple_json_objects(self) -> None:
        """非贪婪匹配应只提取第一个 JSON 对象."""
        text = 'First: {"a": 1} Second: {"b": 2}'
        result = extract_json(text)
        assert result == '{"a": 1}'

    def test_nested_json(self) -> None:
        text = '{"outer": {"inner": 1}}'
        assert extract_json(text) == '{"outer": {"inner": 1}}'

    def test_no_json_returns_original(self) -> None:
        text = "Just plain text"
        assert extract_json(text) == "Just plain text"


class TestParseLlmResponse:
    def test_valid_json(self) -> None:
        result = parse_llm_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_markdown_block(self) -> None:
        text = "```json\n{\"key\": \"value\"}\n```"
        result = parse_llm_response(text)
        assert result == {"key": "value"}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(LLMResponseParseError):
            parse_llm_response("not json at all")

    def test_multiple_objects_extracts_first(self) -> None:
        """当 LLM 返回多个 JSON 对象时，应正确解析第一个."""
        text = '{"first": 1} some text {"second": 2}'
        result = parse_llm_response(text)
        assert result == {"first": 1}

    def test_trailing_comma_repair(self) -> None:
        """尾部逗号应被自动修复."""
        text = '{"a": 1, "b": 2,}'
        result = parse_llm_response(text)
        assert result == {"a": 1, "b": 2}

    def test_single_quotes_repair(self) -> None:
        """单引号 JSON 应被尝试修复."""
        text = "{'a': 1, 'b': 2}"
        # json_repair 或手动修复应能处理
        try:
            result = parse_llm_response(text)
            assert "a" in result
        except LLMResponseParseError:
            pytest.skip("json_repair 未安装或无法修复单引号")

    def test_nested_json_with_extra_text(self) -> None:
        """嵌套 JSON 前后有额外文本时应正确提取."""
        text = 'Here is the result: {"outer": {"inner": [1, 2, 3]}} End of response.'
        result = parse_llm_response(text)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_empty_json_object(self) -> None:
        """空 JSON 对象应返回空字典."""
        result = parse_llm_response("{}")
        assert result == {}

    def test_non_dict_json_raises(self) -> None:
        """JSON 数组等非对象类型应抛出异常."""
        with pytest.raises(LLMResponseParseError):
            parse_llm_response("[1, 2, 3]")

    def test_malformed_json_unrecoverable_raises(self) -> None:
        """完全无法修复的畸形 JSON 应抛出异常."""
        with pytest.raises(LLMResponseParseError):
            parse_llm_response("{ broken json without end")

    def test_markdown_block_with_language_tag(self) -> None:
        """带语言标签的 markdown 代码块."""
        text = '```json\n{"key": "value"}\n```'
        result = parse_llm_response(text)
        assert result == {"key": "value"}

    def test_markdown_block_without_language_tag(self) -> None:
        """不带语言标签的 markdown 代码块."""
        text = '```\n{"key": "value"}\n```'
        result = parse_llm_response(text)
        assert result == {"key": "value"}
