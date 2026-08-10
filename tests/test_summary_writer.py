"""Tests for SummaryWriter Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.summary_writer import (
    _build_prompt,
    _normalize_summary,
    _validate_summary_facts,
    write_chapter_summary,
    write_chapter_summary_with_fact_check,
)
from songyan.models import ChapterSummary, StateSettlement
from songyan.models.settlement import ForeshadowingUpdate, NewSetting


@pytest.fixture
def _make_settlement() -> StateSettlement:
    return StateSettlement()


class TestTemperatureParam:
    @pytest.mark.anyio
    async def test_temperature_forwarded(self) -> None:
        """temperature 参数应被传递给 call_llm."""
        llm_response = json.dumps(
            {
                "plot_summary": "主角突破",
                "emotional_tone": "激昂",
                "key_events": ["突破"],
                "characters_appeared": ["主角"],
            }
        )
        captured_kwargs: dict = {}

        async def _capture_call(prompt: str, **kwargs: object) -> str:
            captured_kwargs.update(kwargs)
            return llm_response

        with patch(
            "songyan.agents.summary_writer.call_llm",
            new_callable=AsyncMock,
            side_effect=_capture_call,
        ):
            with patch("songyan.agents.summary_writer._save_summary"):
                mock_db = AsyncMock()
                settlement = StateSettlement()
                await write_chapter_summary(
                    content="正文",
                    settlement=settlement,
                    project_id="proj_123",
                    chapter_number=1,
                    db=mock_db,
                    temperature=0.99,
                )

        assert captured_kwargs.get("temperature") == 0.99


class TestBuildPrompt:
    def test_includes_content(self) -> None:
        prompt = _build_prompt("这是正文", StateSettlement())
        assert "这是正文" in prompt

    def test_includes_settlement(self) -> None:
        from songyan.models.settlement import CharacterUpdate

        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="c1",
                    field="level",
                    old_value="1",
                    new_value="2",
                    source_quote="突破到二级",
                )
            ]
        )
        prompt = _build_prompt("正文", settlement)
        assert "c1" in prompt
        assert "level" in prompt

    def test_truncates_long_content(self) -> None:
        long_content = "a" * 5000
        prompt = _build_prompt(long_content, StateSettlement())
        assert "..." in prompt or len(prompt) < len(long_content) + 500


class TestNormalizeSummary:
    def test_plot_summary_truncated(self) -> None:
        long_summary = "a" * 400
        summary = ChapterSummary(
            chapter_number=1,
            summary=long_summary,
            emotional_tone="激昂",
        )
        settlement = StateSettlement()
        result = _normalize_summary(summary, settlement)
        # 模板化后总长度不超过 500 字
        assert len(result.summary) <= 500
        assert "【关键事件】" in result.summary

    def test_emotional_tone_truncated(self) -> None:
        summary = ChapterSummary(
            chapter_number=1,
            summary="短摘要",
            emotional_tone="非常复杂的情绪变化",
        )
        settlement = StateSettlement()
        result = _normalize_summary(summary, settlement)
        assert len(result.emotional_tone) <= 20

    def test_short_summary_template_formatted(self) -> None:
        summary = ChapterSummary(
            chapter_number=1,
            summary="主角突破",
            emotional_tone="激昂",
        )
        settlement = StateSettlement()
        result = _normalize_summary(summary, settlement)
        # 即使是短摘要也会被模板化
        assert "【关键事件】" in result.summary
        assert "【情绪转折】激昂" in result.summary


class TestTemplateSummary:
    def test_template_contains_all_sections(self) -> None:
        from songyan.models.settlement import CharacterUpdate, ForeshadowingUpdate, NewSetting

        summary = ChapterSummary(
            chapter_number=1,
            summary="主角决定离开宗门。他在路上遇到了神秘老人。",
            emotional_tone="压抑中暗藏希望",
        )
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="c1",
                    field="level",
                    old_value="1",
                    new_value="2",
                    source_quote="突破",
                )
            ],
            new_settings=[
                NewSetting(
                    setting_name="青铜大门",
                    description="古老门户",
                    source_quote="出现大门",
                    setting_key="gate",
                )
            ],
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="plant",
                    description="古老符文的秘密",
                    expected_resolve_chapter=10,
                    source_version_id="v1",
                )
            ],
        )
        result = _normalize_summary(summary, settlement)
        assert "【关键事件】" in result.summary
        assert "【角色变化】" in result.summary
        assert "【新设定伏笔】" in result.summary
        assert "【情绪转折】" in result.summary
        assert "【下章钩子】" in result.summary

    def test_key_events_length_limited(self) -> None:
        summary = ChapterSummary(
            chapter_number=1,
            summary="a" * 300,
            emotional_tone="激昂",
        )
        settlement = StateSettlement()
        result = _normalize_summary(summary, settlement)
        key_events_part = result.summary.split("\n")[0]
        assert key_events_part.startswith("【关键事件】")
        # 关键事件部分（含标记）不超过 200 + 6 = 206 字
        assert len(key_events_part) <= 210

    def test_hook_extracted_from_last_sentence(self) -> None:
        summary = ChapterSummary(
            chapter_number=1,
            summary="主角进入秘境。发现隐藏宝藏。大战即将开始。",
            emotional_tone="紧张",
        )
        settlement = StateSettlement()
        result = _normalize_summary(summary, settlement)
        assert "【下章钩子】大战即将开始" in result.summary

    def test_total_length_not_exceed_500(self) -> None:
        summary = ChapterSummary(
            chapter_number=1,
            summary="x" * 1000,
            emotional_tone="激昂",
        )
        settlement = StateSettlement()
        result = _normalize_summary(summary, settlement)
        assert len(result.summary) <= 500


class TestValidateSummaryFacts:
    def test_missing_decision_warning(self) -> None:
        summary = ChapterSummary(chapter_number=1, summary="环境描写", emotional_tone="平静")
        settlement = StateSettlement()
        missing = _validate_summary_facts(summary, settlement)
        assert any("决策" in m for m in missing)

    def test_content_protagonist_decision_counts_as_fact_coverage(self) -> None:
        summary = ChapterSummary(chapter_number=1, summary="环境描写", emotional_tone="平静")
        settlement = StateSettlement()
        content = "沈砚复核完当前数值链。沈砚决定先保存离线记录，再关闭外部同步。"

        missing = _validate_summary_facts(summary, settlement, content=content)

        assert missing == []

    def test_pronoun_decision_counts_when_protagonist_context_is_clear(self) -> None:
        summary = ChapterSummary(chapter_number=1, summary="环境描写", emotional_tone="平静")
        settlement = StateSettlement()
        content = "沈砚把终端转到本地模式，反复确认责任质量缺口。他决定先保存当前数值链。"

        missing = _validate_summary_facts(summary, settlement, content=content)

        assert missing == []

    def test_non_protagonist_decision_in_content_does_not_count(self) -> None:
        summary = ChapterSummary(chapter_number=1, summary="环境描写", emotional_tone="平静")
        settlement = StateSettlement()
        content = "系统决定延迟刷新缓存。走廊里的提示灯保持静止，没有人改变行动。"

        missing = _validate_summary_facts(summary, settlement, content=content)

        assert missing == ["缺少主角决策/认知变化"]

    def test_new_setting_not_recorded(self) -> None:
        summary = ChapterSummary(chapter_number=1, summary="主角决定离开", emotional_tone="紧张")
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="青铜大门",
                    description="古老门户",
                    source_quote="出现大门",
                    setting_key="bronze_gate",
                )
            ]
        )
        missing = _validate_summary_facts(summary, settlement)
        assert any("青铜大门" in m for m in missing)

    def test_foreshadowing_not_recorded(self) -> None:
        summary = ChapterSummary(chapter_number=1, summary="主角决定离开", emotional_tone="紧张")
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="plant",
                    description="古老符文的秘密",
                    expected_resolve_chapter=10,
                    source_version_id="v1",
                )
            ]
        )
        missing = _validate_summary_facts(summary, settlement)
        assert any("伏笔" in m for m in missing)

    def test_structured_key_events_count_as_fact_coverage(self) -> None:
        summary = ChapterSummary(
            chapter_number=1,
            summary="主角决定继续调查",
            key_events=[
                "揭示新设定：协议0003",
                "埋下伏笔：沈弥留下的校验尾标",
            ],
            emotional_tone="紧张",
        )
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="协议0003",
                    description="临时见证人机制",
                    source_quote="协议0003启动",
                    setting_key="protocol.0003",
                )
            ],
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="plant",
                    description="沈弥留下的校验尾标",
                    expected_resolve_chapter=10,
                    source_version_id="v1",
                )
            ],
        )

        missing = _validate_summary_facts(summary, settlement)

        assert missing == []

    def test_key_events_decision_counts_as_fact_coverage(self) -> None:
        summary = ChapterSummary(
            chapter_number=1,
            summary="环境描写",
            key_events=["沈砚决定保存当前数值链"],
            emotional_tone="克制",
        )
        settlement = StateSettlement()

        missing = _validate_summary_facts(summary, settlement)

        assert missing == []


class TestWriteChapterSummary:
    @pytest.mark.anyio
    async def test_full_flow(self) -> None:
        llm_response = json.dumps(
            {
                "plot_summary": "主角突破筑基期",
                "emotional_tone": "激昂",
                "key_events": ["突破", "战斗"],
                "characters_appeared": ["林凡", "萧尘"],
            }
        )

        with patch(
            "songyan.agents.summary_writer.call_llm",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            with patch("songyan.agents.summary_writer._save_summary"):
                mock_db = AsyncMock()
                settlement = StateSettlement()
                summary_id, result = await write_chapter_summary(
                    content="正文内容",
                    settlement=settlement,
                    project_id="proj_123",
                    chapter_number=3,
                    db=mock_db,
                )

        assert summary_id.startswith("sum-proj_123-3-")
        assert result.chapter_number == 3
        assert result.chapter_number == 3
        # Task 110b: 模板化输出
        assert "【关键事件】" in result.summary
        assert "主角突破筑基期" in result.summary
        assert "【情绪转折】激昂" in result.summary
        assert "林凡" in result.characters_appeared

    @pytest.mark.anyio
    async def test_fallback_when_llm_empty(self) -> None:
        with patch(
            "songyan.agents.summary_writer.call_llm",
            new_callable=AsyncMock,
            return_value="{}",
        ):
            with patch("songyan.agents.summary_writer._save_summary"):
                mock_db = AsyncMock()
                settlement = StateSettlement()
                summary_id, result = await write_chapter_summary(
                    content="正文",
                    settlement=settlement,
                    project_id="proj_123",
                    chapter_number=5,
                    db=mock_db,
                )

        assert summary_id.startswith("sum-proj_123-5-")
        assert result.chapter_number == 5
        assert "第5章" in result.summary

    @pytest.mark.anyio
    async def test_invalid_json_raises(self) -> None:
        from songyan.exceptions import LLMResponseParseError

        with patch(
            "songyan.agents.summary_writer.call_llm",
            new_callable=AsyncMock,
            return_value="not json",
        ):
            mock_db = AsyncMock()
            settlement = StateSettlement()
            with pytest.raises(LLMResponseParseError):
                await write_chapter_summary(
                    content="正文",
                    settlement=settlement,
                    project_id="proj_123",
                    chapter_number=1,
                    db=mock_db,
                )

    @pytest.mark.anyio
    async def test_fact_check_result_returned(self) -> None:
        llm_response = json.dumps(
            {
                "plot_summary": "主角观察环境",
                "emotional_tone": "紧张",
                "key_events": ["观察"],
                "characters_appeared": ["主角"],
            }
        )
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="协议0003",
                    description="临时见证人机制",
                    source_quote="协议0003启动",
                    setting_key="protocol.0003",
                )
            ]
        )

        with patch(
            "songyan.agents.summary_writer.call_llm",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            with patch("songyan.agents.summary_writer._save_summary"):
                mock_db = AsyncMock()
                summary_id, _summary, missing = await write_chapter_summary_with_fact_check(
                    content="沈砚复核完当前数值链。沈砚决定先保存离线记录。",
                    settlement=settlement,
                    project_id="proj_123",
                    chapter_number=1,
                    db=mock_db,
                )

        assert summary_id.startswith("sum-proj_123-1-")
        assert missing == []

    @pytest.mark.anyio
    async def test_fact_check_still_reports_missing_decision_when_content_lacks_it(self) -> None:
        llm_response = json.dumps(
            {
                "plot_summary": "主角观察环境",
                "emotional_tone": "紧张",
                "key_events": ["观察"],
                "characters_appeared": ["主角"],
            }
        )

        with patch(
            "songyan.agents.summary_writer.call_llm",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            with patch("songyan.agents.summary_writer._save_summary"):
                mock_db = AsyncMock()
                _summary_id, _summary, missing = await write_chapter_summary_with_fact_check(
                    content="终端持续刷新，沈砚站在门边观察。",
                    settlement=StateSettlement(),
                    project_id="proj_123",
                    chapter_number=1,
                    db=mock_db,
                )

        assert missing == ["缺少主角决策/认知变化"]
