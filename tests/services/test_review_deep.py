"""tech-m4-followup 步 3：review --deep 纯函数件（prompt / 估价 / 解析）。"""

from __future__ import annotations

import pytest

from songyan.services.review_deep import (
    DeepReviewError,
    build_deep_review_prompt,
    estimate_deep_review_cost,
    parse_deep_findings,
)


class TestPrompt:
    def test_sections_present(self) -> None:
        prompt = build_deep_review_prompt(
            content="正文甲",
            bible_text="圣经乙",
            previous_summary="摘要丙",
        )
        assert "圣经乙" in prompt
        assert "摘要丙" in prompt
        assert "正文甲" in prompt
        for check in ("fact", "continuity", "repetition", "voice"):
            assert check in prompt
        assert "JSON" in prompt


class TestEstimate:
    def test_positive_cost_with_model(self) -> None:
        prompt = build_deep_review_prompt(
            content="正文" * 500,
            bible_text="圣经" * 100,
            previous_summary="",
        )
        cost, model = estimate_deep_review_cost(prompt)
        assert cost > 0
        assert isinstance(model, str) and model


class TestParse:
    def test_valid_array(self) -> None:
        raw = (
            '[{"severity": "hard", "check": "fact", "message": "矛盾",'
            ' "evidence": "原文片段", "location": "第1段"}]'
        )
        findings = parse_deep_findings(raw)
        assert len(findings) == 1
        assert findings[0].severity == "hard"
        assert findings[0].source == "deep"
        assert findings[0].message == "矛盾"
        assert findings[0].evidence == "原文片段"

    def test_markdown_wrapped(self) -> None:
        raw = '前言废话\n```json\n[{"severity": "warning", "message": "复读"}]\n```\n后记'
        findings = parse_deep_findings(raw)
        assert len(findings) == 1
        assert findings[0].severity == "warning"

    def test_empty_array(self) -> None:
        assert parse_deep_findings("[]") == []

    def test_invalid_severity_defaults_info(self) -> None:
        findings = parse_deep_findings('[{"severity": "fatal", "message": "x"}]')
        assert findings[0].severity == "info"

    def test_missing_optionals_default_empty(self) -> None:
        findings = parse_deep_findings('[{"message": "只有消息"}]')
        assert findings[0].evidence == ""
        assert findings[0].location == ""
        assert findings[0].severity == "info"

    def test_garbage_raises(self) -> None:
        with pytest.raises(DeepReviewError):
            parse_deep_findings("完全不是 JSON 的胡话")
