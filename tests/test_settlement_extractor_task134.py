"""Task 134: SettlementExtractor character/numerical extraction fixes."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from songyan.agents.settlement_extractor import (
    _build_character_update,
    _build_numerical_update,
    _render_character_profiles,
    _render_prompt,
)
from songyan.models import (
    Character,
    CharacterUpdate,
    NumericalUpdate,
    StateSettlement,
)
from songyan.workflows._nodes import (
    _is_effectively_empty_settlement,
    _should_block_empty_settlement,
)


class TestCharacterProfileRendering:
    def test_render_profiles_includes_background_and_goals(self) -> None:
        chars = [
            Character(
                character_id="char_001",
                project_id="p1",
                name="林凡",
                role_type="protagonist",
                background="孤儿出身",
                personality_traits=["冷静", "坚韧"],
                goals=["复仇", "寻找真相"],
                relationships={"师父": "敬重"},
            )
        ]
        rendered = _render_character_profiles(chars)
        assert "林凡" in rendered
        assert "孤儿出身" in rendered
        assert "冷静" in rendered
        assert "复仇" in rendered
        assert "师父" in rendered

    def test_render_profiles_empty(self) -> None:
        assert "无角色档案" in _render_character_profiles([])

    def test_prompt_includes_character_profiles(self) -> None:
        chars = [
            Character(
                character_id="char_001",
                project_id="p1",
                name="林凡",
                role_type="protagonist",
                background="测试背景",
            )
        ]
        prompt = _render_prompt("正文", "v1", [], [], [], None, characters=chars)
        assert "角色基线档案" in prompt
        assert "林凡" in prompt
        assert "测试背景" in prompt


class TestParserLogging:
    def test_build_character_update_missing_field_returns_none(self) -> None:
        result = _build_character_update({"character_id": "c1"})
        assert result is None

    def test_build_character_update_non_dict_returns_none(self) -> None:
        result = _build_character_update("bad")
        assert result is None

    def test_build_numerical_update_missing_attribute_returns_none(self) -> None:
        result = _build_numerical_update({"character_id": "c1"})
        assert result is None

    def test_build_numerical_update_parses_formula(self) -> None:
        data = {
            "character_id": "c1",
            "attribute_name": "level",
            "opening_value": 1.0,
            "increments": [],
            "decrements": [],
            "closing_value": 1.0,
            "formula": "1.0 + 0 = 1.0",
        }
        result = _build_numerical_update(data)
        assert isinstance(result, NumericalUpdate)
        assert result.formula == "1.0 + 0 = 1.0"


class TestEmptySettlementBlock:
    def test_empty_settlement_flag(self) -> None:
        empty = StateSettlement()
        assert _is_effectively_empty_settlement(empty) is True

        non_empty = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="c1", field="mood",
                    old_value="a", new_value="b", source_quote="q",
                )
            ]
        )
        assert _is_effectively_empty_settlement(non_empty) is False

    @pytest.mark.asyncio
    async def test_enforce_mode_blocks_empty_settlement(self) -> None:
        settlement = StateSettlement()
        with patch(
            "songyan.workflows._nodes.CharacterRepository.list_by_project",
            return_value=[Character(character_id="c1", project_id="p1", name="Test")],
        ):
            blocked = await _should_block_empty_settlement(
                settlement, "x" * 500, "p1", "enforce"
            )
        assert blocked is True

    @pytest.mark.asyncio
    async def test_observe_mode_allows_empty_settlement(self) -> None:
        settlement = StateSettlement()
        blocked = await _should_block_empty_settlement(
            settlement, "x" * 500, "p1", "observe"
        )
        assert blocked is False

    @pytest.mark.asyncio
    async def test_short_content_not_blocked(self) -> None:
        settlement = StateSettlement()
        blocked = await _should_block_empty_settlement(
            settlement, "短", "p1", "enforce"
        )
        assert blocked is False


class TestExtractSettlementFormula:
    async def test_extract_preserves_formula(self) -> None:
        from songyan.agents.settlement_extractor import _build_state_settlement

        data = json.loads('''
        {
            "character_updates": [],
            "new_settings": [],
            "foreshadowing_updates": [],
            "numerical_updates": [
                {
                    "character_id": "char_001",
                    "attribute_name": "cultivation_level",
                    "opening_value": 2.0,
                    "increments": [{"amount": 0.5, "source": "灵石", "source_quote": "灵气涌入"}],
                    "decrements": [],
                    "closing_value": 2.5,
                    "formula": "2.0 + 0.5 = 2.5"
                }
            ],
            "planted_hooks": [],
            "resolved_hooks": []
        }
        ''')
        settlement = _build_state_settlement(data)
        assert len(settlement.numerical_updates) == 1
        assert settlement.numerical_updates[0].formula == "2.0 + 0.5 = 2.5"
