"""Tests for LLMAuditor Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.llm_auditor import (
    MAX_CONTENT_TOKENS,
    _build_issue,
    _build_llm_audit_result,
    _compute_overall_score,
    _render_context_info,
    _render_prompt,
    _validate_category,
    _validate_fix_type,
    _validate_severity,
    run_llm_audit,
    save_llm_audit,
)
from songyan.exceptions import LLMResponseParseError
from songyan.models import (
    ChapterGoal,
    ContextPackage,
    CreativeBrief,
    LLMAuditResult,
    ReviewCategory,
    ReviewIssue,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_valid_llm_response(**overrides: object) -> str:
    data = {
        "issues": [
            {
                "issue_id": "issue_001",
                "category": "character_behavior",
                "severity": "major",
                "evidence_quote": "林凡突然大笑起来",
                "evidence_location": "第2段",
                "issue_description": "人物行为不符合性格设定",
                "expected": "林凡应该保持冷静",
                "actual": "林凡突然大笑",
                "suggested_fix": "改为微微一笑或沉默",
                "fix_type": "patch",
                "confidence": 0.85,
            }
        ],
        "dimension_scores": {
            "world_consistency": 8.0,
            "character_behavior": 6.5,
            "timeline": 9.0,
            "new_setting_unregistered": 8.0,
            "narrative_pacing": 7.0,
            "narrative_hook": 7.5,
            "info_dump": 8.0,
            "dialogue_distinctness": 7.0,
            "dialogue_subtext": 6.0,
            "description_sensory": 7.5,
            "show_dont_tell": 6.5,
            "genre_numerical": 9.0,
        },
        "cliche_risk_score": 5.0,
        "character_autonomy_score": 7.0,
        "conceptual_idling_score": 4.0,
        "summary": "本章整体合格，但人物行为有突兀之处。",
    }
    data.update(overrides)  # type: ignore[arg-type]
    return json.dumps(data, ensure_ascii=False)


def _make_context_package() -> ContextPackage:
    goal = ChapterGoal(
        chapter_number=3,
        target_events=["争夺玄天剑"],
        emotional_arc="紧张→爆发",
        chapter_type="战斗",
    )
    return ContextPackage(
        chapter_goal=goal,
        creative_brief=CreativeBrief(
            mode_id="webnovel",
            chapter_goal=goal,
            creative_intent="让读者感受到爽感",
            forbidden_patterns=["不要冷笑"],
        ),
    )


# ---------------------------------------------------------------------------
# Prompt Rendering Tests
# ---------------------------------------------------------------------------
class TestRenderPrompt:
    def test_loads_template(self) -> None:
        prompt = _render_prompt("正文内容", None)
        assert "审查" in prompt or "语义审查" in prompt

    def test_includes_content(self) -> None:
        prompt = _render_prompt("这是测试正文", None)
        assert "这是测试正文" in prompt

    def test_truncates_long_content(self) -> None:
        long_content = "测" * (MAX_CONTENT_TOKENS + 1000)
        prompt = _render_prompt(long_content, None)
        assert "...（正文已截断）" in prompt
        # prompt 中包含的正文部分应被截断（不含模板和标记）
        # 提取 ``` 和 ``` 之间的内容检查
        import re
        code_match = re.search(r"```\n(.*?)\n?```", prompt, re.DOTALL)
        if code_match:
            embedded = code_match.group(1)
            assert len(embedded) <= MAX_CONTENT_TOKENS + 20

    def test_includes_context(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt("正文", ctx)
        assert "第3章" in prompt or "章节目标" in prompt
        assert "争夺玄天剑" in prompt


class TestRenderContextInfo:
    def test_none_context(self) -> None:
        info = _render_context_info(None)
        assert "无额外上下文" in info

    def test_with_context(self) -> None:
        ctx = _make_context_package()
        info = _render_context_info(ctx)
        assert "争夺玄天剑" in info
        assert "让读者感受到爽感" in info
        assert "不要冷笑" in info


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------
class TestValidateCategory:
    def test_valid(self) -> None:
        assert _validate_category("character_behavior") == "character_behavior"

    def test_invalid(self) -> None:
        assert _validate_category("invalid_category") is None

    def test_all_valid_categories(self) -> None:
        for cat in ReviewCategory:
            assert _validate_category(cat.value) == cat.value


class TestValidateSeverity:
    def test_valid(self) -> None:
        assert _validate_severity("critical") == "critical"
        assert _validate_severity("major") == "major"
        assert _validate_severity("minor") == "minor"
        assert _validate_severity("info") == "info"

    def test_invalid_fallback(self) -> None:
        assert _validate_severity("unknown") == "minor"


class TestValidateFixType:
    def test_valid(self) -> None:
        assert _validate_fix_type("patch") == "patch"
        assert _validate_fix_type("rewrite_scene") == "rewrite_scene"

    def test_invalid_fallback(self) -> None:
        assert _validate_fix_type("unknown") == "patch"


# ---------------------------------------------------------------------------
# Issue Building Tests
# ---------------------------------------------------------------------------
class TestBuildIssue:
    def test_valid_issue(self) -> None:
        data = {
            "issue_id": "i1",
            "category": "character_behavior",
            "severity": "major",
            "evidence_quote": "quote",
            "confidence": 0.9,
        }
        issue = _build_issue(data, 0)
        assert issue is not None
        assert issue.issue_id == "i1"
        assert issue.category == "character_behavior"
        assert issue.severity == "major"

    def test_invalid_category(self) -> None:
        data = {
            "category": "invalid",
            "severity": "major",
            "evidence_quote": "quote",
        }
        assert _build_issue(data, 0) is None

    def test_missing_issue_id(self) -> None:
        data = {
            "category": "world_consistency",
            "severity": "minor",
            "evidence_quote": "quote",
        }
        issue = _build_issue(data, 5)
        assert issue is not None
        assert issue.issue_id == "issue_005"

    def test_default_values(self) -> None:
        data = {
            "category": "narrative_pacing",
            "severity": "info",
            "evidence_quote": "",
        }
        issue = _build_issue(data, 0)
        assert issue is not None
        assert issue.fix_type == "patch"
        assert issue.confidence == 1.0


# ---------------------------------------------------------------------------
# Result Building Tests
# ---------------------------------------------------------------------------
class TestBuildLlmAuditResult:
    def test_full_result(self) -> None:
        data = json.loads(_make_valid_llm_response())
        result = _build_llm_audit_result(data)
        assert result.auditor_id == "llm_auditor"
        assert len(result.issues) == 1
        assert result.issues[0].category == "character_behavior"
        assert len(result.dimension_scores) == 12
        assert result.dimension_scores["character_behavior"] == 6.5
        assert result.cliche_risk_score == 5.0
        assert result.character_autonomy_score == 7.0
        assert result.conceptual_idling_score == 4.0
        assert "人物行为" in result.summary

    def test_empty_issues(self) -> None:
        data = json.loads(_make_valid_llm_response(issues=[]))
        result = _build_llm_audit_result(data)
        assert result.issues == []

    def test_invalid_issues_filtered(self) -> None:
        data = json.loads(_make_valid_llm_response())
        data["issues"].append({"category": "invalid", "severity": "major"})
        result = _build_llm_audit_result(data)
        assert len(result.issues) == 1  # 无效的被过滤

    def test_invalid_scores_clamped(self) -> None:
        data = json.loads(_make_valid_llm_response())
        data["dimension_scores"]["character_behavior"] = 15.0
        data["cliche_risk_score"] = -2.0
        result = _build_llm_audit_result(data)
        assert result.dimension_scores["character_behavior"] == 10.0
        assert result.cliche_risk_score == 0.0

    def test_missing_dimensions(self) -> None:
        data = json.loads(_make_valid_llm_response(dimension_scores={}))
        result = _build_llm_audit_result(data)
        assert result.dimension_scores == {}


# ---------------------------------------------------------------------------
# Score Computation Tests
# ---------------------------------------------------------------------------
class TestComputeOverallScore:
    def test_with_dimensions(self) -> None:
        result = LLMAuditResult(
            dimension_scores={"character_behavior": 8.0, "narrative_pacing": 6.0},
            cliche_risk_score=5.0,
            character_autonomy_score=7.0,
            conceptual_idling_score=4.0,
        )
        score = _compute_overall_score(result)
        assert 0.0 <= score <= 10.0

    def test_no_dimensions(self) -> None:
        result = LLMAuditResult()
        score = _compute_overall_score(result)
        assert score >= 0.0

    def test_critical_penalty(self) -> None:
        result = LLMAuditResult(
            dimension_scores={"character_behavior": 10.0},
            issues=[
                ReviewIssue(
                    issue_id="i1",
                    category=ReviewCategory.CHARACTER_BEHAVIOR,
                    severity="critical",
                    evidence_quote="q",
                    evidence_location="loc",
                    issue_description="desc",
                )
            ],
        )
        score = _compute_overall_score(result)
        assert score < 10.0

    def test_perfect_score(self) -> None:
        result = LLMAuditResult(
            dimension_scores={c.value: 10.0 for c in ReviewCategory},
            cliche_risk_score=0.0,  # 套路化风险最低
            character_autonomy_score=10.0,
            conceptual_idling_score=0.0,  # 概念空转度最低
        )
        score = _compute_overall_score(result)
        assert score == 10.0

    def test_cliche_risk_penalizes_score(self) -> None:
        """套路化风险越高，总分应越低."""
        base = LLMAuditResult(
            dimension_scores={"world_consistency": 8.0},
            character_autonomy_score=5.0,
            conceptual_idling_score=5.0,
        )
        low_risk = _compute_overall_score(base.model_copy(update={"cliche_risk_score": 0.0}))
        high_risk = _compute_overall_score(base.model_copy(update={"cliche_risk_score": 10.0}))
        assert high_risk < low_risk


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------
class TestRunLlmAudit:
    async def test_full_flow(self) -> None:
        llm_response = _make_valid_llm_response()
        with patch("songyan.agents.llm_auditor.call_llm", return_value=llm_response):
            result = await run_llm_audit("正文内容")
        assert len(result.issues) == 1
        assert len(result.dimension_scores) == 12
        assert result.duration_ms >= 0

    async def test_with_context_package(self) -> None:
        llm_response = _make_valid_llm_response()
        ctx = _make_context_package()
        with patch("songyan.agents.llm_auditor.call_llm", return_value=llm_response):
            result = await run_llm_audit("正文", context_package=ctx)
        assert result.summary != ""

    async def test_invalid_json_raises(self) -> None:
        with patch(
            "songyan.agents.llm_auditor.call_llm", return_value="不是 JSON"
        ), pytest.raises(LLMResponseParseError):
            await run_llm_audit("正文")

    async def test_empty_issues(self) -> None:
        llm_response = _make_valid_llm_response(issues=[])
        with patch("songyan.agents.llm_auditor.call_llm", return_value=llm_response):
            result = await run_llm_audit("正文")
        assert result.issues == []

    async def test_temperature_param(self) -> None:
        llm_response = _make_valid_llm_response()
        with patch("songyan.agents.llm_auditor.call_llm", return_value=llm_response) as mock:
            await run_llm_audit("正文", temperature=0.5)
        mock.assert_called_once()
        assert mock.call_args[1]["temperature"] == 0.5


class TestSaveLlmAudit:
    async def test_save_creates_report(self) -> None:
        mock_db = AsyncMock()
        result = LLMAuditResult(
            issues=[],
            dimension_scores={"character_behavior": 8.0},
        )
        await save_llm_audit(mock_db, "version_123", result)
        mock_db.create.assert_called_once()
        report = mock_db.create.call_args[0][0]
        report_id = mock_db.create.call_args[0][1]
        assert report.chapter_version_id == "version_123"
        assert report_id.startswith("la-")

    async def test_save_with_custom_id(self) -> None:
        mock_db = AsyncMock()
        result = LLMAuditResult()
        await save_llm_audit(mock_db, "v1", result, report_id="custom")
        assert mock_db.create.call_args[0][1] == "custom"
