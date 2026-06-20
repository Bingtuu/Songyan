"""Tests for GoalPlanner Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.goal_planner import (
    MAX_WORD_COUNT,
    MIN_WORD_COUNT,
    _build_chapter_goal,
    define_chapter_goal,
)
from songyan.exceptions import LLMResponseParseError
from songyan.models.chapter import ChapterGoal
from songyan.models.creative_mode import CreativeModeProfile
from songyan.models.genre import GenreProfile
from songyan.models.project import ProjectSetting


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_project() -> ProjectSetting:
    return ProjectSetting(
        title="测试项目",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="林凡",
        protagonist_background="孤儿出身",
        core_hook="逆天改命",
        tone="热血",
        target_reader_expectation="爽文读者",
        taboos=["绿帽", "虐主"],
    )


def _make_genre() -> GenreProfile:
    return GenreProfile(
        id="xuanhuan",
        name="玄幻",
        chapter_types=["开篇", "升级", "战斗", "转折", "日常"],
        fatigue_words=["冷笑", "嘴角勾起"],
        satisfaction_types=["实力提升", "打脸", "收获宝物"],
        pacing_rule="每章至少一个小高潮",
        writer_rules=["对话简短有力", "描写具体"],
        reviewer_focus=["设定一致性", "节奏"],
        active_audit_dimensions=["style_ai_tells", "style_fatigue_words"],
    )


def _make_mode() -> CreativeModeProfile:
    return CreativeModeProfile(
        id="webnovel",
        name="网文模式",
        enabled_agents={"pre_write": ["goal_planner"]},
        audit_weights={"style_ai_tells": 0.3},
        active_audit_dimensions=["style_ai_tells"],
        revision_policy="standard",
        tolerance={"max_ai_tells": 2.0, "max_fatigue_words": 3.0},
    )


def _make_valid_llm_response(**overrides: object) -> str:
    data = {
        "chapter_number": 1,
        "previous_summary": "上一章结尾",
        "target_events": ["事件A", "事件B"],
        "emotional_arc": "压抑→爆发",
        "hooks": ["一个神秘人出现"],
        "obligations": ["兑现主角母亲的遗愿"],
        "word_count_target": 3000,
        "chapter_type": "开篇",
    }
    data.update(overrides)  # type: ignore[arg-type]
    return json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# _build_chapter_goal
# ---------------------------------------------------------------------------
class TestBuildChapterGoal:
    """Tests for ChapterGoal construction from parsed data."""

    def test_full_data(self) -> None:
        """完整数据构建成功."""
        data = json.loads(_make_valid_llm_response())
        genre = _make_genre()

        goal = _build_chapter_goal(data, 1, genre)

        assert goal.chapter_number == 1
        assert goal.target_events == ["事件A", "事件B"]
        assert goal.word_count_target == 3000
        assert goal.chapter_type == "开篇"

    def test_word_count_clamp_high(self) -> None:
        """字数超过上限时 clamp."""
        data = json.loads(_make_valid_llm_response(word_count_target=10000))
        genre = _make_genre()

        goal = _build_chapter_goal(data, 1, genre)

        assert goal.word_count_target == MAX_WORD_COUNT

    def test_word_count_clamp_low(self) -> None:
        """字数低于下限时 clamp."""
        data = json.loads(_make_valid_llm_response(word_count_target=500))
        genre = _make_genre()

        goal = _build_chapter_goal(data, 1, genre)

        assert goal.word_count_target == MIN_WORD_COUNT

    def test_invalid_chapter_type_fallback(self) -> None:
        """无效章节类型回退到第一个允许值."""
        data = json.loads(_make_valid_llm_response(chapter_type="不存在的类型"))
        genre = _make_genre()

        goal = _build_chapter_goal(data, 1, genre)

        assert goal.chapter_type == "开篇"

    def test_missing_fields_use_defaults(self) -> None:
        """缺失字段使用默认值."""
        data = {"chapter_number": 2, "word_count_target": 2500}
        genre = _make_genre()

        goal = _build_chapter_goal(data, 2, genre)

        assert goal.chapter_number == 2
        assert goal.target_events == []
        assert goal.emotional_arc == ""
        assert goal.hooks == []
        assert goal.obligations == []
        assert goal.word_count_target == 2500

    def test_invalid_field_types_fallback(self) -> None:
        """字段类型错误时回退到默认值."""
        data = {
            "chapter_number": 1,
            "target_events": "不是列表",
            "emotional_arc": 123,
            "hooks": None,
            "word_count_target": "not a number",
        }
        genre = _make_genre()

        goal = _build_chapter_goal(data, 1, genre)

        assert goal.target_events == []
        assert goal.emotional_arc == ""
        assert goal.hooks == []
        assert goal.word_count_target == 3000  # DEFAULT_WORD_COUNT

    def test_no_allowed_chapter_types(self) -> None:
        """题材无章节类型时，保留原始值."""
        data = json.loads(_make_valid_llm_response())
        genre = GenreProfile(id="test", name="测试", chapter_types=[])

        goal = _build_chapter_goal(data, 1, genre)

        assert goal.chapter_type == "开篇"


# ---------------------------------------------------------------------------
# define_chapter_goal (integration with mock LLM)
# ---------------------------------------------------------------------------
class TestDefineChapterGoal:
    """Integration tests for define_chapter_goal with mocked LLM."""

    async def test_successful_flow(self) -> None:
        """正常流程：LLM 返回合法 JSON → 保存 → 返回 ChapterGoal."""
        project = _make_project()
        genre = _make_genre()
        mode = _make_mode()
        llm_response = _make_valid_llm_response()

        with patch(
            "songyan.agents.goal_planner.call_llm",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            tpl = (
                "{{ chapter_number }} {{ genre_name }} {{ mode_name }} "
                "{{ protagonist_name }} {{ genre_pacing_rule }} "
                "{{ mode_constraints }} {{ recent_summaries }}"
            )
            with patch(
                "songyan.agents.goal_planner._load_prompt_template",
                return_value=tpl,
            ):
                result = await define_chapter_goal(
                    project_id="proj_123",
                    project=project,
                    genre_profile=genre,
                    mode_profile=mode,
                    chapter_number=1,
                    previous_summary="上一章结尾",
                )

        assert isinstance(result, ChapterGoal)
        assert result.chapter_number == 1
        assert result.word_count_target == 3000
        assert result.chapter_type == "开篇"
        assert len(result.target_events) == 2

    async def test_prompt_contains_all_variables(self) -> None:
        """Prompt 模板应包含所有必要变量."""
        project = _make_project()
        genre = _make_genre()
        mode = _make_mode()
        llm_response = _make_valid_llm_response()

        captured_prompt: str = ""

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return llm_response

        with patch(
            "songyan.agents.goal_planner.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            await define_chapter_goal(
                project_id="proj_123",
                project=project,
                genre_profile=genre,
                mode_profile=mode,
                chapter_number=3,
                previous_summary="主角突破了筑基期",
            )

        # 验证关键变量已注入
        assert "林凡" in captured_prompt
        assert "玄幻" in captured_prompt
        assert "网文模式" in captured_prompt
        assert "逆天改命" in captured_prompt
        assert "每章至少一个小高潮" in captured_prompt
        assert "主角突破了筑基期" in captured_prompt
        assert "standard" in captured_prompt  # revision_policy in mode_constraints
        assert "3" in captured_prompt  # chapter_number

    async def test_llm_parse_error(self) -> None:
        """LLM 返回非 JSON 时抛出 LLMResponseParseError."""
        project = _make_project()
        genre = _make_genre()
        mode = _make_mode()

        with patch(
            "songyan.agents.goal_planner.call_llm",
            new_callable=AsyncMock,
            return_value="not json at all",
        ):
            with patch(
                "songyan.agents.goal_planner._load_prompt_template",
                return_value="test",
            ):
                with pytest.raises(LLMResponseParseError):
                    await define_chapter_goal(
                        project_id="proj_123",
                        project=project,
                        genre_profile=genre,
                        mode_profile=mode,
                        chapter_number=1,
                    )

    async def test_llm_call_error(self) -> None:
        """LLM 调用失败时抛出 LLMError."""
        from songyan.exceptions import LLMError

        project = _make_project()
        genre = _make_genre()
        mode = _make_mode()

        with patch(
            "songyan.agents.goal_planner.call_llm",
            new_callable=AsyncMock,
            side_effect=LLMError("API error"),
        ):
            with patch(
                "songyan.agents.goal_planner._load_prompt_template",
                return_value="test",
            ):
                with pytest.raises(LLMError):
                    await define_chapter_goal(
                        project_id="proj_123",
                        project=project,
                        genre_profile=genre,
                        mode_profile=mode,
                        chapter_number=1,
                    )

    async def test_empty_previous_summary(self) -> None:
        """无最近剧情摘要时使用默认文案."""
        project = _make_project()
        genre = _make_genre()
        mode = _make_mode()
        llm_response = _make_valid_llm_response()

        captured_prompt: str = ""

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return llm_response

        with patch(
            "songyan.agents.goal_planner.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            await define_chapter_goal(
                project_id="proj_123",
                project=project,
                genre_profile=genre,
                mode_profile=mode,
                chapter_number=1,
                previous_summary="",
            )

        assert "无前置剧情" in captured_prompt


class TestTemperatureParam:
    @pytest.mark.anyio
    async def test_temperature_forwarded(self) -> None:
        """temperature 参数应被传递给 call_llm."""
        llm_response = json.dumps(
            {
                "chapter_type": "过渡",
                "word_count_target": 3000,
                "target_events": [],
                "emotional_arc": "平静",
                "hooks": [],
                "obligations": [],
            }
        )
        captured_kwargs: dict = {}

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            captured_kwargs.update(kwargs)
            return llm_response

        with patch(
            "songyan.agents.goal_planner.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            project = _make_project()
            genre = _make_genre()
            mode = _make_mode()
            await define_chapter_goal(
                project_id="proj_123",
                project=project,
                genre_profile=genre,
                mode_profile=mode,
                chapter_number=1,
                previous_summary="",
                temperature=0.99,
            )

        assert captured_kwargs.get("temperature") == 0.99
