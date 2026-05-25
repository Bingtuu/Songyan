"""Tests for LiteraryAuditor Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.literary_auditor import (
    MAX_CONTENT_LENGTH,
    _build_literary_audit_result,
    _build_observation,
    _render_context_info,
    _render_prompt,
    _validate_observation_type,
    _validate_severity,
    run_literary_audit,
    save_literary_audit,
)
from songyan.exceptions import LLMResponseParseError
from songyan.models import (
    ChapterGoal,
    ContextPackage,
    CreativeBrief,
    LiteraryAuditResult,
    LiteraryObservation,
    Tension,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_valid_llm_response(**overrides: object) -> str:
    data = {
        "observations": [
            {
                "observation_id": "obs_001",
                "observation_type": "valuable_fissure",
                "description": "人物在关键时刻做出了出人意料的选择",
                "evidence_quote": "林凡沉默良久，最终放下了剑",
                "severity": "highlight",
                "recommendation": "保留这个裂隙，它比修复更有价值",
                "preserve": True,
            },
            {
                "observation_id": "obs_002",
                "observation_type": "cliche_risk",
                "description": "反派大笑的情节过于套路化",
                "evidence_quote": "反派仰天大笑：'你逃不掉的！'",
                "severity": "notice",
                "recommendation": "可以考虑让反派以沉默代替大笑",
                "preserve": False,
            },
        ],
        "literary_quality_score": 7.5,
        "character_autonomy_score": 8.0,
        "conceptual_grounding_score": 6.5,
        "fissure_preservation_score": 7.0,
        "summary": "本章人物自治度较高，但存在套路化风险。",
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
            mode_id="literary",
            chapter_goal=goal,
            creative_intent="探索人物在极端压力下的真实选择",
            allowed_fissures=["人物临时改变主意","对话中的沉默"],
            required_tensions=[
                Tension(
                    tension_id="t1",
                    description="林凡与师父的价值观冲突",
                    tension_type="value_conflict",
                    intensity=0.9,
                )
            ],
        ),
    )


# ---------------------------------------------------------------------------
# Prompt Rendering Tests
# ---------------------------------------------------------------------------
class TestRenderPrompt:
    def test_loads_template(self) -> None:
        prompt = _render_prompt("正文内容", None)
        assert "文学性" in prompt or "诊断" in prompt

    def test_includes_content(self) -> None:
        prompt = _render_prompt("这是测试正文", None)
        assert "这是测试正文" in prompt

    def test_truncates_long_content(self) -> None:
        long_content = "a" * (MAX_CONTENT_LENGTH + 1000)
        prompt = _render_prompt(long_content, None)
        assert "...（正文已截断）" in prompt
        import re
        code_match = re.search(r"```\n(.*?)\n?```", prompt, re.DOTALL)
        if code_match:
            embedded = code_match.group(1)
            assert len(embedded) <= MAX_CONTENT_LENGTH + 20

    def test_includes_context(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt("正文", ctx)
        assert "探索人物" in prompt
        assert "允许裂隙" in prompt
        assert "value_conflict" in prompt


class TestRenderContextInfo:
    def test_none_context(self) -> None:
        info = _render_context_info(None)
        assert "无额外上下文" in info

    def test_with_context(self) -> None:
        ctx = _make_context_package()
        info = _render_context_info(ctx)
        assert "探索人物在极端压力下的真实选择" in info
        assert "人物临时改变主意" in info
        assert "value_conflict" in info
        assert "争夺玄天剑" in info

    def test_empty_context(self) -> None:
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
        )
        info = _render_context_info(ctx)
        assert "无额外上下文" in info


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------
class TestValidateObservationType:
    def test_valid(self) -> None:
        assert _validate_observation_type("valuable_fissure") == "valuable_fissure"
        assert _validate_observation_type("cliche_risk") == "cliche_risk"

    def test_invalid(self) -> None:
        assert _validate_observation_type("invalid_type") is None

    def test_all_valid_types(self) -> None:
        valid_types = {
            "character_tooling",
            "conceptual_idling",
            "excessive_smoothing",
            "valuable_fissure",
            "cliche_risk",
            "polyphony_weakness",
            "authorial_intrusion",
        }
        for t in valid_types:
            assert _validate_observation_type(t) == t


class TestValidateSeverity:
    def test_valid(self) -> None:
        assert _validate_severity("notice") == "notice"
        assert _validate_severity("suggestion") == "suggestion"
        assert _validate_severity("highlight") == "highlight"

    def test_invalid_fallback(self) -> None:
        assert _validate_severity("unknown") == "suggestion"


# ---------------------------------------------------------------------------
# Observation Building Tests
# ---------------------------------------------------------------------------
class TestBuildObservation:
    def test_valid(self) -> None:
        data = {
            "observation_id": "o1",
            "observation_type": "cliche_risk",
            "description": "套路化",
            "evidence_quote": "quote",
            "severity": "notice",
            "recommendation": "改一下",
            "preserve": False,
        }
        obs = _build_observation(data, 0)
        assert obs is not None
        assert obs.observation_id == "o1"
        assert obs.observation_type == "cliche_risk"
        assert obs.severity == "notice"
        assert obs.preserve is False

    def test_invalid_type_filtered(self) -> None:
        data = {
            "observation_type": "invalid",
            "description": "desc",
        }
        assert _build_observation(data, 0) is None

    def test_valuable_fissure_preserve(self) -> None:
        data = {
            "observation_type": "valuable_fissure",
            "description": "有价值的裂隙",
            "preserve": False,
        }
        obs = _build_observation(data, 0)
        assert obs is not None
        assert obs.preserve is True  # 强制设为 True

    def test_missing_observation_id(self) -> None:
        data = {
            "observation_type": "authorial_intrusion",
            "description": "作者侵入",
        }
        obs = _build_observation(data, 7)
        assert obs is not None
        assert obs.observation_id == "obs_007"

    def test_default_severity(self) -> None:
        data = {
            "observation_type": "polyphony_weakness",
            "description": "复调弱化",
        }
        obs = _build_observation(data, 0)
        assert obs is not None
        assert obs.severity == "suggestion"
        assert obs.recommendation == ""


# ---------------------------------------------------------------------------
# Result Building Tests
# ---------------------------------------------------------------------------
class TestBuildLiteraryAuditResult:
    def test_full_result(self) -> None:
        data = json.loads(_make_valid_llm_response())
        result = _build_literary_audit_result(data)
        assert result.auditor_id == "literary_auditor"
        assert len(result.observations) == 2
        assert result.observations[0].observation_type == "valuable_fissure"
        assert result.literary_quality_score == 7.5
        assert result.character_autonomy_score == 8.0
        assert result.conceptual_grounding_score == 6.5
        assert result.fissure_preservation_score == 7.0
        assert "人物自治" in result.summary

    def test_empty_observations(self) -> None:
        data = json.loads(_make_valid_llm_response(observations=[]))
        result = _build_literary_audit_result(data)
        assert result.observations == []

    def test_invalid_observations_filtered(self) -> None:
        data = json.loads(_make_valid_llm_response())
        data["observations"].append({"observation_type": "invalid", "severity": "notice"})
        result = _build_literary_audit_result(data)
        assert len(result.observations) == 2  # 无效的被过滤

    def test_scores_clamped(self) -> None:
        data = json.loads(_make_valid_llm_response())
        data["literary_quality_score"] = 15.0
        data["character_autonomy_score"] = -2.0
        result = _build_literary_audit_result(data)
        assert result.literary_quality_score == 10.0
        assert result.character_autonomy_score == 0.0

    def test_missing_scores(self) -> None:
        data = json.loads(_make_valid_llm_response())
        del data["literary_quality_score"]
        del data["conceptual_grounding_score"]
        result = _build_literary_audit_result(data)
        assert result.literary_quality_score == 0.0
        assert result.conceptual_grounding_score == 0.0
        assert result.character_autonomy_score == 8.0  # 保留原值


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------
class TestRunLiteraryAudit:
    async def test_full_flow(self) -> None:
        llm_response = _make_valid_llm_response()
        with patch("songyan.agents.literary_auditor.call_llm", return_value=llm_response):
            result = await run_literary_audit("正文内容")
        assert len(result.observations) == 2
        assert result.literary_quality_score == 7.5
        assert result.duration_ms >= 0

    async def test_with_context_package(self) -> None:
        llm_response = _make_valid_llm_response()
        ctx = _make_context_package()
        with patch("songyan.agents.literary_auditor.call_llm", return_value=llm_response):
            result = await run_literary_audit("正文", context_package=ctx)
        assert result.summary != ""

    async def test_invalid_json_raises(self) -> None:
        with patch(
            "songyan.agents.literary_auditor.call_llm", return_value="不是 JSON"
        ), pytest.raises(LLMResponseParseError):
            await run_literary_audit("正文")

    async def test_empty_observations(self) -> None:
        llm_response = _make_valid_llm_response(observations=[])
        with patch("songyan.agents.literary_auditor.call_llm", return_value=llm_response):
            result = await run_literary_audit("正文")
        assert result.observations == []

    async def test_temperature_param(self) -> None:
        llm_response = _make_valid_llm_response()
        with patch("songyan.agents.literary_auditor.call_llm", return_value=llm_response) as mock:
            await run_literary_audit("正文", temperature=0.7)
        mock.assert_called_once()
        assert mock.call_args[1]["temperature"] == 0.7


class TestSaveLiteraryAudit:
    async def test_save_creates_record(self) -> None:
        mock_db = AsyncMock()
        result = LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="o1",
                    observation_type="cliche_risk",
                    description="套路",
                )
            ],
            literary_quality_score=7.0,
        )
        await save_literary_audit(mock_db, "version_123", result)
        mock_db.create.assert_called_once()
        saved_result = mock_db.create.call_args[0][0]
        observation_id = mock_db.create.call_args[0][1]
        version_id = mock_db.create.call_args[0][2]
        assert saved_result.literary_quality_score == 7.0
        assert observation_id.startswith("lit-")
        assert version_id == "version_123"

    async def test_save_with_custom_id(self) -> None:
        mock_db = AsyncMock()
        result = LiteraryAuditResult()
        await save_literary_audit(mock_db, "v1", result, observation_id="custom")
        assert mock_db.create.call_args[0][1] == "custom"
