"""Tests for SettlementExtractor Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.settlement_extractor import (
    _build_character_update,
    _build_foreshadowing_update,
    _build_new_setting,
    _build_numerical_update,
    _build_state_settlement,
    _render_genre_rules,
    _render_prompt,
    _validate_settlement,
    apply_settlement,
    extract_settlement,
)
from songyan.exceptions import LLMResponseParseError
from songyan.models import (
    CharacterState,
    CharacterUpdate,
    ForeshadowingItem,
    ForeshadowingUpdate,
    GenreRules,
    NewSetting,
    NumericalUpdate,
    StateSettlement,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_valid_llm_response(**overrides: object) -> str:
    data = {
        "character_updates": [
            {
                "character_id": "char_001",
                "field": "emotional_state",
                "old_value": "冷静",
                "new_value": "愤怒",
                "source_quote": "林凡握紧双拳，眼中燃起怒火",
            }
        ],
        "new_settings": [
            {
                "setting_name": "灵石系统",
                "description": "修仙者使用灵石补充灵气",
                "source_quote": "他取出一枚下品灵石，开始吸收其中的灵气",
                "setting_key": "xuanhuan.spirit_stone",
            }
        ],
        "foreshadowing_updates": [
            {
                "operation": "plant",
                "description": "上古遗迹的线索",
                "expected_resolve_chapter": 15,
                "source_version_id": "v_001",
            }
        ],
        "numerical_updates": [
            {
                "character_id": "char_001",
                "attribute_name": "cultivation_level",
                "opening_value": 3.0,
                "increments": [
                    {"amount": 0.5, "source": "吸收灵石", "source_quote": "灵气涌入体内"}
                ],
                "decrements": [],
                "closing_value": 3.5,
            }
        ],
        "planted_hooks": ["hook_1"],
        "resolved_hooks": [],
    }
    data.update(overrides)  # type: ignore[arg-type]
    return json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Prompt Rendering Tests
# ---------------------------------------------------------------------------
class TestRenderPrompt:
    def test_loads_template(self) -> None:
        prompt = _render_prompt("正文", "v1", [], [], [], None)
        assert "状态结算" in prompt or "提取" in prompt

    def test_includes_content(self) -> None:
        prompt = _render_prompt("这是测试正文", "v1", [], [], [], None)
        assert "这是测试正文" in prompt

    def test_includes_character_states(self) -> None:
        states = [CharacterState(character_id="c1", field="mood", value="happy")]
        prompt = _render_prompt("正文", "v1", states, [], [], None)
        assert "c1" in prompt
        assert "mood" in prompt

    def test_includes_settings(self) -> None:
        settings = [
            NewSetting(
                setting_name="灵石", description="补充灵气",
                source_quote="quote", setting_key="stone",
            )
        ]
        prompt = _render_prompt("正文", "v1", [], settings, [], None)
        assert "灵石" in prompt

    def test_includes_foreshadowings(self) -> None:
        items = [
            ForeshadowingItem(foreshadowing_id="fs1", description="伏笔", planted_in_chapter=1)
        ]
        prompt = _render_prompt("正文", "v1", [], [], items, None)
        assert "伏笔" in prompt

    def test_includes_genre_rules(self) -> None:
        rules = GenreRules(pacing_rule="快节奏", writer_rules=["不要废话"])
        prompt = _render_prompt("正文", "v1", [], [], [], rules)
        assert "快节奏" in prompt
        assert "不要废话" in prompt


class TestRenderGenreRules:
    def test_none(self) -> None:
        assert _render_genre_rules(None) == "（无特殊题材规则）"

    def test_with_rules(self) -> None:
        rules = GenreRules(pacing_rule="快节奏", fatigue_words=["冷笑"])
        result = _render_genre_rules(rules)
        assert "快节奏" in result
        assert "冷笑" in result

    def test_empty(self) -> None:
        assert _render_genre_rules(GenreRules()) == "（无特殊题材规则）"


# ---------------------------------------------------------------------------
# Building Tests
# ---------------------------------------------------------------------------
class TestBuildCharacterUpdate:
    def test_valid(self) -> None:
        data = {
            "character_id": "c1",
            "field": "mood",
            "old_value": "a",
            "new_value": "b",
            "source_quote": "quote",
        }
        result = _build_character_update(data)
        assert result is not None
        assert result.character_id == "c1"
        assert result.field == "mood"

    def test_missing_id(self) -> None:
        assert _build_character_update({"field": "mood"}) is None

    def test_missing_field(self) -> None:
        assert _build_character_update({"character_id": "c1"}) is None


class TestBuildNewSetting:
    def test_valid(self) -> None:
        data = {
            "setting_name": "灵石",
            "description": "补充灵气",
            "source_quote": "quote",
            "setting_key": "key",
        }
        result = _build_new_setting(data)
        assert result is not None
        assert result.setting_name == "灵石"

    def test_missing_name(self) -> None:
        assert _build_new_setting({"description": "desc"}) is None


class TestBuildForeshadowingUpdate:
    def test_valid_plant(self) -> None:
        data = {"operation": "plant", "description": "伏笔"}
        result = _build_foreshadowing_update(data)
        assert result is not None
        assert result.operation == "plant"

    def test_invalid_operation(self) -> None:
        assert _build_foreshadowing_update({"operation": "invalid"}) is None


class TestBuildNumericalUpdate:
    def test_valid(self) -> None:
        data = {
            "character_id": "c1",
            "attribute_name": "level",
            "opening_value": 1.0,
            "increments": [{"amount": 0.5, "source": "s", "source_quote": "q"}],
            "decrements": [],
            "closing_value": 1.5,
        }
        result = _build_numerical_update(data)
        assert result is not None
        assert result.character_id == "c1"
        assert result.closing_value == 1.5

    def test_missing_id(self) -> None:
        assert _build_numerical_update({"attribute_name": "level"}) is None


class TestBuildStateSettlement:
    def test_full(self) -> None:
        data = json.loads(_make_valid_llm_response())
        result = _build_state_settlement(data)
        assert len(result.character_updates) == 1
        assert len(result.new_settings) == 1
        assert len(result.foreshadowing_updates) == 1
        assert len(result.numerical_updates) == 1
        assert result.planted_hooks == ["hook_1"]

    def test_empty(self) -> None:
        data = json.loads(_make_valid_llm_response(
            character_updates=[], new_settings=[], foreshadowing_updates=[],
            numerical_updates=[], planted_hooks=[], resolved_hooks=[],
        ))
        result = _build_state_settlement(data)
        assert result.character_updates == []
        assert result.new_settings == []

    def test_invalid_items_filtered(self) -> None:
        data = json.loads(_make_valid_llm_response())
        data["character_updates"].append({"field": "mood"})  # 缺少 character_id
        result = _build_state_settlement(data)
        assert len(result.character_updates) == 1  # 无效的被过滤


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------
class TestValidateSettlement:
    async def test_old_value_mismatch(self) -> None:
        content = "林凡握紧双拳，眼中燃起怒火"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="c1", field="mood",
                    old_value="冷静", new_value="愤怒",
                    source_quote="林凡握紧双拳，眼中燃起怒火",
                )
            ]
        )
        current_states = [CharacterState(character_id="c1", field="mood", value="悲伤")]
        errors = await _validate_settlement(settlement, content, current_states, [])
        assert len(errors) == 1
        assert "当前值为 '悲伤'" in errors[0]

    async def test_old_value_match(self) -> None:
        content = "林凡握紧双拳"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="c1", field="mood",
                    old_value="冷静", new_value="愤怒",
                    source_quote="林凡握紧双拳",
                )
            ]
        )
        current_states = [CharacterState(character_id="c1", field="mood", value="冷静")]
        errors = await _validate_settlement(settlement, content, current_states, [])
        assert errors == []

    async def test_source_quote_not_in_content(self) -> None:
        content = "正文内容"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="c1", field="mood",
                    old_value="a", new_value="b",
                    source_quote="不存在的引用",
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert len(errors) == 1
        assert "未在正文中找到" in errors[0]

    async def test_setting_key_duplicate(self) -> None:
        content = "quote"
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="灵石", description="补充灵气",
                    source_quote="quote", setting_key="xuanhuan.stone",
                )
            ]
        )
        current_settings = [
            NewSetting(
                setting_name="已有", description="已有设定",
                source_quote="q", setting_key="xuanhuan.stone",
            )
        ]
        errors = await _validate_settlement(settlement, content, [], current_settings)
        assert len(errors) == 1
        assert "已存在" in errors[0]

    async def test_numerical_formula_ok(self) -> None:
        content = "正文"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="c1", attribute_name="level",
                    opening_value=1.0, increments=[],
                    decrements=[], closing_value=1.0,
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert errors == []

    async def test_numerical_formula_wrong(self) -> None:
        content = "正文"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="c1", attribute_name="level",
                    opening_value=1.0, increments=[],
                    decrements=[], closing_value=2.0,
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert len(errors) == 1
        assert "closing_value" in errors[0]

    async def test_foreshadowing_empty_version_id(self) -> None:
        content = "正文"
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(operation="plant", description="伏笔")
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert len(errors) == 1
        assert "source_version_id" in errors[0]

    async def test_no_current_state_no_error(self) -> None:
        """当角色在 DB 中没有状态时，old_value 验证跳过."""
        content = "正文"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="c1", field="mood",
                    old_value="任意", new_value="愤怒",
                    source_quote="正文",
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert errors == []


# ---------------------------------------------------------------------------
# Apply Settlement Tests
# ---------------------------------------------------------------------------
class TestApplySettlement:
    async def test_applies_character_updates(self) -> None:
        mock_char = AsyncMock()
        mock_char.add_state_snapshot.return_value = 1

        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="c1", field="mood",
                    old_value="a", new_value="b", source_quote="q",
                )
            ]
        )
        await apply_settlement(
            settlement, "p1", 3, "v1",
            char_repo=mock_char,
            setting_repo=AsyncMock(),
            foreshadowing_repo=AsyncMock(),
            numerical_repo=AsyncMock(),
        )
        mock_char.add_state_snapshot.assert_called_once()
        state = mock_char.add_state_snapshot.call_args[0][0]
        assert state.character_id == "c1"
        assert state.value == "b"
        assert state.source_version_id == "v1"

    async def test_applies_new_settings(self) -> None:
        mock_setting = AsyncMock()
        settlement = StateSettlement(
            new_settings=[
                NewSetting(setting_name="灵石", description="补充灵气", source_quote="q")
            ]
        )
        await apply_settlement(
            settlement, "p1", 3, "v1",
            char_repo=AsyncMock(),
            setting_repo=mock_setting,
            foreshadowing_repo=AsyncMock(),
            numerical_repo=AsyncMock(),
        )
        mock_setting.create.assert_called_once()
        setting = mock_setting.create.call_args[0][0]
        assert setting.setting_name == "灵石"

    async def test_applies_foreshadowing_plant(self) -> None:
        mock_fs = AsyncMock()
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="plant", description="伏笔", expected_resolve_chapter=5,
                    source_version_id="v1",
                )
            ]
        )
        await apply_settlement(
            settlement, "p1", 3, "v1",
            char_repo=AsyncMock(),
            setting_repo=AsyncMock(),
            foreshadowing_repo=mock_fs,
            numerical_repo=AsyncMock(),
        )
        mock_fs.create.assert_called_once()

    async def test_applies_foreshadowing_resolve(self) -> None:
        mock_fs = AsyncMock()
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="resolve", description="回收",
                    foreshadowing_id="fs1", source_version_id="v1",
                )
            ]
        )
        await apply_settlement(
            settlement, "p1", 3, "v1",
            char_repo=AsyncMock(),
            setting_repo=AsyncMock(),
            foreshadowing_repo=mock_fs,
            numerical_repo=AsyncMock(),
        )
        mock_fs.update_status.assert_called_once_with("fs1", "resolved")

    async def test_applies_numerical_updates(self) -> None:
        mock_num = AsyncMock()
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="c1", attribute_name="level",
                    opening_value=1.0, closing_value=1.0,
                )
            ]
        )
        await apply_settlement(
            settlement, "p1", 3, "v1",
            char_repo=AsyncMock(),
            setting_repo=AsyncMock(),
            foreshadowing_repo=AsyncMock(),
            numerical_repo=mock_num,
        )
        mock_num.create.assert_called_once()

    async def test_empty_settlement_no_calls(self) -> None:
        mock_char = AsyncMock()
        await apply_settlement(
            StateSettlement(), "p1", 3, "v1",
            char_repo=mock_char,
            setting_repo=AsyncMock(),
            foreshadowing_repo=AsyncMock(),
            numerical_repo=AsyncMock(),
        )
        mock_char.add_state_snapshot.assert_not_called()


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------
class TestExtractSettlement:
    async def test_full_flow(self) -> None:
        content = "林凡握紧双拳，眼中燃起怒火。他取出一枚下品灵石，开始吸收其中的灵气。"
        llm_response = _make_valid_llm_response()

        with patch("songyan.agents.settlement_extractor.call_llm", return_value=llm_response):
            with patch(
                "songyan.agents.settlement_extractor._load_current_character_states",
                return_value=[
                    CharacterState(character_id="char_001", field="emotional_state", value="冷静")
                ],
            ):
                with patch(
                    "songyan.agents.settlement_extractor._load_current_settings",
                    return_value=[],
                ):
                    with patch(
                        "songyan.agents.settlement_extractor._load_current_foreshadowings",
                        return_value=[],
                    ):
                        result = await extract_settlement(
                            content=content,
                            project_id="p1",
                            chapter_number=3,
                            version_id="v_001",
                        )

        assert len(result.character_updates) == 1
        assert len(result.new_settings) == 1
        assert len(result.foreshadowing_updates) == 1
        assert len(result.numerical_updates) == 1
        assert result.validation_status == "valid"
        assert result.validation_errors == []

    async def test_empty_settlement(self) -> None:
        llm_response = _make_valid_llm_response(
            character_updates=[], new_settings=[], foreshadowing_updates=[],
            numerical_updates=[], planted_hooks=[], resolved_hooks=[],
        )

        with patch("songyan.agents.settlement_extractor.call_llm", return_value=llm_response):
            with patch(
                "songyan.agents.settlement_extractor._load_current_character_states",
                return_value=[],
            ):
                with patch(
                    "songyan.agents.settlement_extractor._load_current_settings",
                    return_value=[],
                ):
                    with patch(
                        "songyan.agents.settlement_extractor._load_current_foreshadowings",
                        return_value=[],
                    ):
                        result = await extract_settlement(
                            content="正文", project_id="p1",
                            chapter_number=3, version_id="v1",
                        )

        assert result.character_updates == []
        assert result.validation_status == "valid"

    async def test_invalid_json_raises(self) -> None:
        with patch(
            "songyan.agents.settlement_extractor.call_llm", return_value="不是 JSON"
        ):
            with patch(
                "songyan.agents.settlement_extractor._load_current_character_states",
                return_value=[],
            ):
                with patch(
                    "songyan.agents.settlement_extractor._load_current_settings",
                    return_value=[],
                ):
                    with patch(
                        "songyan.agents.settlement_extractor._load_current_foreshadowings",
                        return_value=[],
                    ):
                        with pytest.raises(LLMResponseParseError):
                            await extract_settlement("正文", "p1", 3, "v1")

    async def test_validation_fails(self) -> None:
        content = "林凡握紧双拳，眼中燃起怒火。"
        llm_response = _make_valid_llm_response(
            character_updates=[
                {
                    "character_id": "char_001",
                    "field": "emotional_state",
                    "old_value": "错误的旧值",  # DB 中是"冷静"
                    "new_value": "愤怒",
                    "source_quote": "林凡握紧双拳，眼中燃起怒火",
                }
            ]
        )

        with patch("songyan.agents.settlement_extractor.call_llm", return_value=llm_response):
            with patch(
                "songyan.agents.settlement_extractor._load_current_character_states",
                return_value=[
                    CharacterState(
                        character_id="char_001", field="emotional_state", value="冷静"
                    )
                ],
            ):
                with patch(
                    "songyan.agents.settlement_extractor._load_current_settings",
                    return_value=[],
                ):
                    with patch(
                        "songyan.agents.settlement_extractor._load_current_foreshadowings",
                        return_value=[],
                    ):
                        result = await extract_settlement(
                            content=content, project_id="p1",
                            chapter_number=3, version_id="v1",
                        )

        assert result.validation_status == "needs_human_review"
        assert len(result.validation_errors) > 0

    async def test_temperature_param(self) -> None:
        llm_response = _make_valid_llm_response(
            character_updates=[], new_settings=[], foreshadowing_updates=[],
            numerical_updates=[], planted_hooks=[], resolved_hooks=[],
        )
        with patch(
            "songyan.agents.settlement_extractor.call_llm", return_value=llm_response
        ) as mock:
            with patch(
                "songyan.agents.settlement_extractor._load_current_character_states",
                return_value=[],
            ):
                with patch(
                    "songyan.agents.settlement_extractor._load_current_settings",
                    return_value=[],
                ):
                    with patch(
                        "songyan.agents.settlement_extractor._load_current_foreshadowings",
                        return_value=[],
                    ):
                        await extract_settlement(
                            "正文", "p1", 3, "v1", temperature=0.4
                        )
        mock.assert_called_once()
        assert mock.call_args[1]["temperature"] == 0.4
