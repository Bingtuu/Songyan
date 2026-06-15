"""Tests for SummaryWriter Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.summary_writer import _build_prompt, write_chapter_summary
from songyan.models import StateSettlement


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
                result = await write_chapter_summary(
                    content="正文内容",
                    settlement=settlement,
                    project_id="proj_123",
                    chapter_number=3,
                    db=mock_db,
                )

        assert result.chapter_number == 3
        assert result.chapter_number == 3
        assert result.summary == "主角突破筑基期"
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
                result = await write_chapter_summary(
                    content="正文",
                    settlement=settlement,
                    project_id="proj_123",
                    chapter_number=5,
                    db=mock_db,
                )

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
