"""Tests for CreativeDirector Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.creative_director import (
    MIN_FORBIDDEN_PATTERNS,
    _build_creative_brief,
    _ensure_forbidden_patterns,
    _extract_json,
    _parse_llm_response,
    _validate_tension,
    generate_creative_brief,
)
from songyan.exceptions import LLMError, LLMResponseParseError
from songyan.models.chapter import ChapterGoal
from songyan.models.character import Character
from songyan.models.creative_mode import CreativeBrief, CreativeModeProfile
from songyan.models.genre import GenreProfile
from songyan.models.project import ProjectSetting


@pytest.fixture(autouse=True)
def _patch_load_active_settings_to_recycle():
    """Task 170j: 避免集成测试依赖未初始化的 setting_tracking 表."""
    with patch(
        "songyan.agents.creative_director._load_active_settings_to_recycle",
        new=AsyncMock(return_value=[]),
    ), patch(
        "songyan.agents.creative_director.build_concept_budget_constraint",
        new=AsyncMock(return_value=""),
    ):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_chapter_goal() -> ChapterGoal:
    return ChapterGoal(
        chapter_number=3,
        previous_summary="主角在拍卖会上与反派竞价",
        target_events=["争夺玄天剑", "剑灵觉醒"],
        emotional_arc="紧张→爆发",
        hooks=["剑灵开口说话"],
        obligations=["兑现母亲遗愿"],
        word_count_target=3000,
        chapter_type="战斗",
    )


def _make_genre() -> GenreProfile:
    return GenreProfile(
        id="xuanhuan",
        name="玄幻",
        chapter_types=["开篇", "升级", "战斗", "转折", "日常"],
        fatigue_words=["冷笑"],
        satisfaction_types=["实力提升", "打脸"],
        pacing_rule="每章至少一个小高潮",
        writer_rules=["对话简短有力"],
        reviewer_focus=["设定一致性"],
        active_audit_dimensions=["style_ai_tells"],
        taboos=["绿帽", "虐主"],
    )


def _make_mode() -> CreativeModeProfile:
    return CreativeModeProfile(
        id="webnovel",
        name="网文模式",
        enabled_agents={"pre_write": ["creative_director"]},
        audit_weights={"style_ai_tells": 0.3},
        active_audit_dimensions=["style_ai_tells"],
        revision_policy="standard",
        tolerance={"max_ai_tells": 2.0},
    )


def _make_project() -> ProjectSetting:
    return ProjectSetting(
        title="测试项目",
        genre_id="xuanhuan",
        id="webnovel",
        protagonist_name="林凡",
        protagonist_background="孤儿出身",
        core_hook="逆天改命",
        tone="热血",
    )


def _make_characters() -> list[Character]:
    return [
        Character(
            character_id="char_001",
            project_id="proj_123",
            name="林凡",
            role_type="protagonist",
            background="孤儿出身",
            personality_traits=["坚韧", "果断"],
            goals=["找到父母"],
        ),
        Character(
            character_id="char_002",
            project_id="proj_123",
            name="萧尘",
            role_type="antagonist",
            background="世家子弟",
            personality_traits=["傲慢", "阴险"],
        ),
    ]


def _make_valid_llm_response(**overrides: object) -> str:
    data = {
        "mode_id": "webnovel",
        "creative_intent": "让读者感受到主角在绝境中爆发的爽感",
        "required_tensions": [
            {
                "tension_id": "tension_001",
                "description": "主角与反派争夺玄天剑",
                "tension_type": "value_conflict",
                "characters_involved": ["林凡", "萧尘"],
                "intensity": 0.8,
            },
        ],
        "forbidden_patterns": [
            "不要使用'冷笑'",
            "避免空洞的环境描写",
            "禁止毫无铺垫的角色转变",
        ],
        "allowed_fissures": [
            "林凡突然放弃竞价可能暗示他另有打算",
        ],
        "style_constraints": [
            "节奏明快，爽点密集",
        ],
        "reader_contract": "读完本章，读者应该为主角的逆袭感到振奋",
    }
    data.update(overrides)  # type: ignore[arg-type]
    return json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------
class TestExtractJson:
    """Tests for JSON extraction."""

    def test_plain_json(self) -> None:
        text = '{"key": "value"}'
        assert _extract_json(text) == '{"key": "value"}'

    def test_markdown_code_block(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        assert _extract_json(text) == '{"key": "value"}'

    def test_extra_text(self) -> None:
        text = '说明\n{"key": "value"}\n结束'
        assert _extract_json(text) == '{"key": "value"}'


# ---------------------------------------------------------------------------
# _parse_llm_response
# ---------------------------------------------------------------------------
class TestParseLLMResponse:
    """Tests for LLM response parsing."""

    def test_valid_json(self) -> None:
        text = '{"key": "value"}'
        result = _parse_llm_response(text)
        assert result == {"key": "value"}

    def test_invalid_json(self) -> None:
        with pytest.raises(LLMResponseParseError) as exc_info:
            _parse_llm_response("not json")
        assert "无法解析" in str(exc_info.value)


# ---------------------------------------------------------------------------
# _validate_tension
# ---------------------------------------------------------------------------
class TestValidateTension:
    """Tests for tension validation."""

    def test_valid_tension(self) -> None:
        data = {
            "tension_id": "t1",
            "description": "描述",
            "tension_type": "value_conflict",
            "characters_involved": ["A", "B"],
            "intensity": 0.8,
        }
        tension = _validate_tension(data)
        assert tension is not None
        assert tension.tension_type == "value_conflict"
        assert tension.intensity == 0.8

    def test_invalid_tension_type(self) -> None:
        data = {
            "tension_id": "t1",
            "description": "描述",
            "tension_type": "invalid_type",
        }
        tension = _validate_tension(data)
        assert tension is None

    def test_intensity_clamp(self) -> None:
        data = {
            "tension_id": "t1",
            "description": "描述",
            "tension_type": "power_imbalance",
            "intensity": 1.5,
        }
        tension = _validate_tension(data)
        assert tension is not None
        assert tension.intensity == 1.0

    def test_intensity_default(self) -> None:
        data = {
            "tension_id": "t1",
            "description": "描述",
            "tension_type": "emotional_contrast",
        }
        tension = _validate_tension(data)
        assert tension is not None
        assert tension.intensity == 0.5

    def test_auto_generated_id(self) -> None:
        data = {
            "description": "描述",
            "tension_type": "temporal_pressure",
        }
        tension = _validate_tension(data)
        assert tension is not None
        assert tension.tension_id.startswith("tension_")


# ---------------------------------------------------------------------------
# _ensure_forbidden_patterns
# ---------------------------------------------------------------------------
class TestEnsureForbiddenPatterns:
    """Tests for forbidden patterns enforcement."""

    def test_sufficient_patterns(self) -> None:
        patterns = ["a", "b", "c", "d"]
        result = _ensure_forbidden_patterns(patterns)
        # 自动注入设定连续性约束
        assert len(result) == 5
        assert result[:4] == ["a", "b", "c", "d"]
        assert any("种子设定" in p for p in result)

    def test_insufficient_patterns_filled(self) -> None:
        patterns = ["a"]
        result = _ensure_forbidden_patterns(patterns)
        assert len(result) >= MIN_FORBIDDEN_PATTERNS
        assert result[0] == "a"

    def test_empty_list(self) -> None:
        result = _ensure_forbidden_patterns([])
        # 自动注入设定连续性约束 + 默认填充到至少 MIN_FORBIDDEN_PATTERNS
        assert len(result) >= MIN_FORBIDDEN_PATTERNS
        assert any("种子设定" in p for p in result)

    def test_filters_non_string(self) -> None:
        patterns = ["a", 123, None, "b"]
        result = _ensure_forbidden_patterns(patterns)
        assert "a" in result
        assert "b" in result
        assert "123" not in result  # 非字符串被过滤
        # 自动注入设定连续性约束
        assert any("种子设定" in p for p in result)


# ---------------------------------------------------------------------------
# _build_creative_brief
# ---------------------------------------------------------------------------
class TestBuildCreativeBrief:
    """Tests for CreativeBrief construction."""

    def test_full_data(self) -> None:
        data = json.loads(_make_valid_llm_response())
        goal = _make_chapter_goal()

        brief = _build_creative_brief(data, "webnovel", goal)

        assert brief.mode_id == "webnovel"
        assert brief.chapter_goal is goal
        assert brief.creative_intent == "让读者感受到主角在绝境中爆发的爽感"
        assert len(brief.required_tensions) == 1
        assert len(brief.forbidden_patterns) >= MIN_FORBIDDEN_PATTERNS
        assert brief.forbidden_patterns[0] == "不要使用'冷笑'"
        assert len(brief.allowed_fissures) == 1
        assert len(brief.style_constraints) == 1
        assert brief.reader_contract != ""

    def test_missing_fields_defaults(self) -> None:
        data = {"mode_id": "webnovel"}
        goal = _make_chapter_goal()

        brief = _build_creative_brief(data, "webnovel", goal)

        assert brief.creative_intent == ""
        assert brief.required_tensions == []
        assert len(brief.forbidden_patterns) >= MIN_FORBIDDEN_PATTERNS
        assert brief.allowed_fissures == []
        assert brief.style_constraints == []
        assert brief.reader_contract == ""

    def test_invalid_tensions_filtered(self) -> None:
        data = json.loads(
            _make_valid_llm_response(
                required_tensions=[
                    {
                        "tension_id": "t1",
                        "description": "有效",
                        "tension_type": "value_conflict",
                    },
                    {
                        "tension_id": "t2",
                        "description": "无效",
                        "tension_type": "invalid",
                    },
                ]
            )
        )
        goal = _make_chapter_goal()

        brief = _build_creative_brief(data, "webnovel", goal)

        assert len(brief.required_tensions) == 1
        assert brief.required_tensions[0].tension_id == "t1"

    def test_invalid_field_types_fallback(self) -> None:
        data = {
            "mode_id": "webnovel",
            "creative_intent": 123,
            "forbidden_patterns": "不是列表",
            "allowed_fissures": None,
            "style_constraints": 456,
            "reader_contract": ["列表"],
        }
        goal = _make_chapter_goal()

        brief = _build_creative_brief(data, "webnovel", goal)

        assert brief.creative_intent == ""
        assert len(brief.forbidden_patterns) >= MIN_FORBIDDEN_PATTERNS
        assert brief.allowed_fissures == []
        assert brief.style_constraints == []
        assert brief.reader_contract == ""

    def test_build_creative_brief_parses_voice_anchors(self) -> None:
        data = json.loads(
            _make_valid_llm_response(
                voice_anchors=[
                    {
                        "character_id": "char-1",
                        "emotional_register": "压抑但易怒",
                        "verbal_tick": "我没时间",
                        "taboo_phrase": "对不起",
                    }
                ]
            )
        )
        goal = _make_chapter_goal()

        brief = _build_creative_brief(data, "webnovel", goal)

        assert len(brief.voice_anchors) == 1
        assert brief.voice_anchors[0].character_id == "char-1"
        assert brief.voice_anchors[0].emotional_register == "压抑但易怒"
        assert brief.voice_anchors[0].verbal_tick == "我没时间"
        assert brief.voice_anchors[0].taboo_phrase == "对不起"

    def test_voice_anchors_invalid_entries_dropped(self) -> None:
        data = json.loads(
            _make_valid_llm_response(
                voice_anchors=[
                    {
                        "character_id": "char-1",
                        "emotional_register": "压抑但易怒",
                    },
                    {
                        "emotional_register": "缺少 character_id",
                    },
                    "不是字典",
                ]
            )
        )
        goal = _make_chapter_goal()

        brief = _build_creative_brief(data, "webnovel", goal)

        assert len(brief.voice_anchors) == 1
        assert brief.voice_anchors[0].character_id == "char-1"

    def test_build_creative_brief_parses_voice_samples(self) -> None:
        data = json.loads(
            _make_valid_llm_response(
                voice_samples=[
                    {
                        "character_id": "char-1",
                        "character_name": "角色一",
                        "sample_lines": ["你别过来。", "我早说过这不归我管。"],
                        "forbidden_patterns": ["换句话说", "不可否认的是"],
                        "mood_anchor": "压抑但易怒",
                    }
                ]
            )
        )
        goal = _make_chapter_goal()

        brief = _build_creative_brief(data, "webnovel", goal)

        assert len(brief.voice_samples) == 1
        assert brief.voice_samples[0].character_id == "char-1"
        assert brief.voice_samples[0].character_name == "角色一"
        assert brief.voice_samples[0].sample_lines == ["你别过来。", "我早说过这不归我管。"]
        assert brief.voice_samples[0].forbidden_patterns == ["换句话说", "不可否认的是"]
        assert brief.voice_samples[0].mood_anchor == "压抑但易怒"

    def test_voice_samples_invalid_entries_dropped(self) -> None:
        data = json.loads(
            _make_valid_llm_response(
                voice_samples=[
                    {
                        "character_id": "char-1",
                        "sample_lines": ["一句对白"],
                    },
                    {
                        "sample_lines": ["缺少 character_id"],
                    },
                    "不是字典",
                ]
            )
        )
        goal = _make_chapter_goal()

        brief = _build_creative_brief(data, "webnovel", goal)

        assert len(brief.voice_samples) == 1
        assert brief.voice_samples[0].character_id == "char-1"


# ---------------------------------------------------------------------------
# generate_creative_brief (integration with mock LLM)
# ---------------------------------------------------------------------------
class TestGenerateCreativeBrief:
    """Integration tests for generate_creative_brief."""

    async def test_successful_flow(self) -> None:
        """正常流程：Mock LLM → 解析 → 保存 → 返回."""
        goal = _make_chapter_goal()
        genre = _make_genre()
        mode = _make_mode()
        characters = _make_characters()
        llm_response = _make_valid_llm_response()

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            with patch(
                "songyan.agents.creative_director._load_prompt_template",
                return_value="test prompt",
            ):
                result = await generate_creative_brief(
                    project=_make_project(),
                    project_id="proj_123",
                    chapter_goal=goal,
                    genre_profile=genre,
                    mode_profile=mode,
                    characters=characters,
                    previous_summary="主角突破了筑基期",
                )

        assert isinstance(result, CreativeBrief)
        assert result.mode_id == "webnovel"
        assert result.chapter_goal is goal
        assert len(result.required_tensions) == 1
        assert len(result.forbidden_patterns) >= MIN_FORBIDDEN_PATTERNS

    async def test_prompt_contains_all_variables(self) -> None:
        """Prompt 模板应包含所有必要变量."""
        goal = _make_chapter_goal()
        genre = _make_genre()
        mode = _make_mode()
        characters = _make_characters()
        llm_response = _make_valid_llm_response()

        captured_prompt: str = ""

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return llm_response

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            await generate_creative_brief(
                project=_make_project(),
                project_id="proj_123",
                chapter_goal=goal,
                genre_profile=genre,
                mode_profile=mode,
                characters=characters,
                previous_summary="主角突破了筑基期",
            )

        # 验证关键变量已注入
        assert "玄幻" in captured_prompt
        assert "网文模式" in captured_prompt
        assert "林凡" in captured_prompt
        assert "萧尘" in captured_prompt
        assert "每章至少一个小高潮" in captured_prompt
        assert "主角突破了筑基期" in captured_prompt
        assert "战斗" in captured_prompt  # chapter_type in chapter_goal_json
        assert "绿帽" in captured_prompt  # taboos

    async def test_llm_parse_error(self) -> None:
        """LLM 返回非 JSON 时抛出 LLMResponseParseError."""
        goal = _make_chapter_goal()
        genre = _make_genre()
        mode = _make_mode()
        characters = _make_characters()

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            return_value="not json",
        ):
            with patch(
                "songyan.agents.creative_director._load_prompt_template",
                return_value="test",
            ):
                with pytest.raises(LLMResponseParseError):
                    await generate_creative_brief(
                        project=_make_project(),
                        project_id="proj_123",
                        chapter_goal=goal,
                        genre_profile=genre,
                        mode_profile=mode,
                        characters=characters,
                    )

        # Agent 不再内部保存，由调用方负责持久化

    async def test_llm_call_error(self) -> None:
        """LLM 调用失败时抛出 LLMError."""
        goal = _make_chapter_goal()
        genre = _make_genre()
        mode = _make_mode()
        characters = _make_characters()

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            side_effect=LLMError("API error"),
        ):
            with patch(
                "songyan.agents.creative_director._load_prompt_template",
                return_value="test",
            ):
                with pytest.raises(LLMError):
                    await generate_creative_brief(
                        project=_make_project(),
                        project_id="proj_123",
                        chapter_goal=goal,
                        genre_profile=genre,
                        mode_profile=mode,
                        characters=characters,
                    )

        # Agent 不再内部保存，由调用方负责持久化

    async def test_empty_characters(self) -> None:
        """无角色时使用默认文案."""
        goal = _make_chapter_goal()
        genre = _make_genre()
        mode = _make_mode()
        llm_response = _make_valid_llm_response()

        captured_prompt: str = ""

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return llm_response

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            await generate_creative_brief(
                project=_make_project(),
                project_id="proj_123",
                chapter_goal=goal,
                genre_profile=genre,
                mode_profile=mode,
                characters=[],
                previous_summary="",
            )

        assert "暂无角色信息" in captured_prompt
        assert "无前置剧情" in captured_prompt


class TestTemperatureParam:
    @pytest.mark.anyio
    async def test_temperature_forwarded(self) -> None:
        """temperature 参数应被传递给 call_llm."""
        llm_response = json.dumps(
            {
                "creative_intent": "测试",
                "core_hook": "钩子",
                "tone": "风格",
                "tensions": [],
                "forbidden_patterns": ["a", "b", "c"],
            }
        )
        captured_kwargs: dict = {}

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            captured_kwargs.update(kwargs)
            return llm_response

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            goal = ChapterGoal(chapter_number=1)
            genre = GenreProfile(
                id="xuanhuan",
                name="玄幻",
                writer_rules=["规则"],
            )
            mode = CreativeModeProfile(id="webnovel", name="网文")
            await generate_creative_brief(
                project=_make_project(),
                project_id="proj_123",
                chapter_goal=goal,
                genre_profile=genre,
                mode_profile=mode,
                characters=[],
                previous_summary="",
                temperature=0.99,
            )

        assert captured_kwargs.get("temperature") == 0.99


# ---------------------------------------------------------------------------
# Task 170j: literary optimization plugin wiring
# ---------------------------------------------------------------------------
class TestLiteraryPlugins:
    async def test_plugins_injected_when_has_skeleton(self) -> None:
        """有骨架且 mode 配置了插件时，prompt 应包含插件内容."""
        from songyan.workflows._narrative_context import NarrativeGoalContext

        goal = _make_chapter_goal()
        genre = _make_genre()
        mode = _make_mode()
        mode.literary_optimization_plugins = ["minimal_voice_anchor"]
        characters = _make_characters()
        llm_response = _make_valid_llm_response()

        narrative_ctx = NarrativeGoalContext(
            has_skeleton=True,
            open_threads=[{"thread_id": "t1", "title": "测试线索"}],
        )

        captured_prompt: str = ""

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return llm_response

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            await generate_creative_brief(
                project=_make_project(),
                project_id="proj_123",
                chapter_goal=goal,
                genre_profile=genre,
                mode_profile=mode,
                characters=characters,
                previous_summary="测试剧情",
                narrative_ctx=narrative_ctx,
            )

        assert "极简声纹锚定" in captured_prompt

    async def test_plugins_not_injected_without_skeleton(self) -> None:
        """无骨架时不应加载插件."""
        from songyan.workflows._narrative_context import NarrativeGoalContext

        goal = _make_chapter_goal()
        genre = _make_genre()
        mode = _make_mode()
        mode.literary_optimization_plugins = ["minimal_voice_anchor"]
        characters = _make_characters()
        llm_response = _make_valid_llm_response()

        narrative_ctx = NarrativeGoalContext(has_skeleton=False)

        captured_prompt: str = ""

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return llm_response

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            await generate_creative_brief(
                project=_make_project(),
                project_id="proj_123",
                chapter_goal=goal,
                genre_profile=genre,
                mode_profile=mode,
                characters=characters,
                previous_summary="测试剧情",
                narrative_ctx=narrative_ctx,
            )

        assert "极简声纹锚定" not in captured_prompt

    async def test_plugins_not_injected_when_empty(self) -> None:
        """插件列表为空时，prompt 与不使用插件时一致."""
        from songyan.workflows._narrative_context import NarrativeGoalContext

        goal = _make_chapter_goal()
        genre = _make_genre()
        mode = _make_mode()
        characters = _make_characters()
        llm_response = _make_valid_llm_response()

        narrative_ctx = NarrativeGoalContext(
            has_skeleton=True,
            open_threads=[{"thread_id": "t1", "title": "测试线索"}],
        )

        captured_prompt: str = ""

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return llm_response

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            await generate_creative_brief(
                project=_make_project(),
                project_id="proj_123",
                chapter_goal=goal,
                genre_profile=genre,
                mode_profile=mode,
                characters=characters,
                previous_summary="测试剧情",
                narrative_ctx=narrative_ctx,
            )

        assert "极简声纹锚定" not in captured_prompt
