"""Tests for SettlementExtractor Agent."""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.settlement_extractor import (
    MAX_PROMPT_CHARACTER_STATES,
    MAX_PROMPT_FORESHADOWINGS,
    MAX_PROMPT_SETTINGS,
    _build_character_update,
    _build_foreshadowing_update,
    _build_new_setting,
    _build_numerical_update,
    _build_state_settlement,
    _execute_with_db_retry,
    _render_genre_rules,
    _render_prompt,
    _select_prompt_facts,
    _validate_settlement,
    apply_settlement,
    extract_settlement,
)
from songyan.exceptions import LLMResponseParseError, SettlementError
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
                "setting_key": "xuanhuan.magic.spirit_stone",
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


class TestPromptFactSelection:
    def test_limits_prompt_facts_without_dropping_relevant_items(self) -> None:
        states = [
            CharacterState(character_id=f"char_{i}", field="mood", value=f"state-{i}")
            for i in range(MAX_PROMPT_CHARACTER_STATES + 10)
        ]
        settings = [
            NewSetting(
                setting_name=f"设定{i}",
                description=f"描述{i}",
                source_quote=f"quote-{i}",
                setting_key=f"world.setting.{i}",
                chapter_number=i,
            )
            for i in range(MAX_PROMPT_SETTINGS + 10)
        ]
        foreshadowings = [
            ForeshadowingItem(
                foreshadowing_id=f"fs-{i}",
                description=f"伏笔{i}",
                planted_in_chapter=i,
                expected_resolve_chapter=200 + i,
            )
            for i in range(MAX_PROMPT_FORESHADOWINGS + 10)
        ]
        foreshadowings[-1].expected_resolve_chapter = 12

        selected_states, selected_settings, selected_foreshadowings = _select_prompt_facts(
            "正文提到 char_49、设定49、fs-39",
            10,
            states,
            settings,
            foreshadowings,
        )

        assert len(selected_states) == MAX_PROMPT_CHARACTER_STATES
        assert len(selected_settings) == MAX_PROMPT_SETTINGS
        assert len(selected_foreshadowings) == MAX_PROMPT_FORESHADOWINGS
        assert any(state.character_id == "char_49" for state in selected_states)
        assert any(setting.setting_name == "设定49" for setting in selected_settings)
        assert any(item.foreshadowing_id == "fs-39" for item in selected_foreshadowings)


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

    async def test_setting_key_duplicate_skipped(self) -> None:
        """Task 094: 重复 key 在代码层去重，验证阶段不再报错."""
        content = "quote"
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="灵石", description="补充灵气",
                    source_quote="quote", setting_key="xuanhuan.magic.stone",
                )
            ]
        )
        current_settings = [
            NewSetting(
                setting_name="已有", description="已有设定",
                source_quote="q", setting_key="xuanhuan.magic.stone",
            )
        ]
        errors = await _validate_settlement(settlement, content, [], current_settings)
        # 重复 key 被代码层去重，验证阶段不报错
        assert len(errors) == 0

    async def test_setting_key_format_invalid(self) -> None:
        """Task 094: setting_key 格式必须符合 category.subcategory.name."""
        content = "quote"
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="灵石", description="补充灵气",
                    source_quote="quote", setting_key="xuanhuan.stone",  # 只有 2 段，格式错误
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert len(errors) == 1
        assert "格式" in errors[0]

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
        # list_by_project 需要返回有效角色列表，否则 character_update 会被跳过
        from songyan.models import Character
        mock_char.list_by_project.return_value = [
            Character(character_id="c1", project_id="p1", name="Test", role_type="protagonist")
        ]

        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="c1", field="mood",
                    old_value="a", new_value="b", source_quote="q",
                )
            ]
        )
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 3, "v1",
            conn=mock_conn,
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
        mock_setting.archive_by_key.return_value = 0
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="下品灵石",
                    description="修仙者使用灵石补充灵气",
                    source_quote="q",
                    setting_key="xuanhuan.magic.spirit_stone",
                )
            ]
        )
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 3, "v1",
            conn=mock_conn,
            char_repo=AsyncMock(),
            setting_repo=mock_setting,
            foreshadowing_repo=AsyncMock(),
            numerical_repo=AsyncMock(),
        )
        mock_setting.create.assert_called_once()
        setting = mock_setting.create.call_args[0][0]
        assert setting.setting_name == "下品灵石"
        assert setting.setting_key == "xuanhuan.magic.spirit_stone"

    async def test_normalizes_invalid_setting_key(self) -> None:
        mock_setting = AsyncMock()
        mock_setting.archive_by_key.return_value = 0
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="通信天线构造",
                    description="用于通信的天线结构",
                    source_quote="q",
                    setting_key="anomaly_x.communication.antenna.construction",
                )
            ]
        )
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 3, "v1",
            conn=mock_conn,
            char_repo=AsyncMock(),
            setting_repo=mock_setting,
            foreshadowing_repo=AsyncMock(),
            numerical_repo=AsyncMock(),
        )
        mock_setting.create.assert_called_once()
        setting = mock_setting.create.call_args[0][0]
        assert setting.setting_key == "anomaly_x_communication.antenna.construction"

    async def test_skips_setting_when_no_fallback_key(self) -> None:
        mock_setting = AsyncMock()
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="门",
                    description="一扇门",
                    source_quote="q",
                    setting_key="bad.key",
                )
            ]
        )
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 3, "v1",
            conn=mock_conn,
            char_repo=AsyncMock(),
            setting_repo=mock_setting,
            foreshadowing_repo=AsyncMock(),
            numerical_repo=AsyncMock(),
        )
        mock_setting.create.assert_not_called()

    async def test_archives_previous_setting_version(self) -> None:
        mock_setting = AsyncMock()
        mock_setting.archive_by_key.return_value = 1
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="通信天线构造",
                    description="用于通信的天线结构",
                    source_quote="q",
                    setting_key="anomaly_x.communication.antenna.construction",
                )
            ]
        )
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 3, "v1",
            conn=mock_conn,
            char_repo=AsyncMock(),
            setting_repo=mock_setting,
            foreshadowing_repo=AsyncMock(),
            numerical_repo=AsyncMock(),
        )
        mock_setting.archive_by_key.assert_called_once_with(
            project_id="p1",
            setting_key="anomaly_x_communication.antenna.construction",
            conn=mock_conn,
        )

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
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 3, "v1",
            conn=mock_conn,
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
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 3, "v1",
            conn=mock_conn,
            char_repo=AsyncMock(),
            setting_repo=AsyncMock(),
            foreshadowing_repo=mock_fs,
            numerical_repo=AsyncMock(),
        )
        from unittest.mock import ANY
        mock_fs.update_status.assert_called_once_with("fs1", "resolved", conn=ANY)

    async def test_applies_numerical_updates(self) -> None:
        mock_num = AsyncMock()
        mock_char = AsyncMock()
        from songyan.models import Character
        mock_char.list_by_project.return_value = [
            Character(character_id="c1", project_id="p1", name="角色1")
        ]
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="c1", attribute_name="level",
                    opening_value=1.0, closing_value=1.0,
                )
            ]
        )
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 3, "v1",
            conn=mock_conn,
            char_repo=mock_char,
            setting_repo=AsyncMock(),
            foreshadowing_repo=AsyncMock(),
            numerical_repo=mock_num,
        )
        mock_num.create.assert_called_once()

    async def test_empty_settlement_no_calls(self) -> None:
        mock_char = AsyncMock()
        mock_conn = AsyncMock()
        await apply_settlement(
            StateSettlement(), "p1", 3, "v1",
            conn=mock_conn,
            char_repo=mock_char,
            setting_repo=AsyncMock(),
            foreshadowing_repo=AsyncMock(),
            numerical_repo=AsyncMock(),
        )
        mock_char.add_state_snapshot.assert_not_called()

    async def test_invalid_settlement_does_not_call_repositories(self) -> None:
        mock_char = AsyncMock()
        mock_setting = AsyncMock()
        mock_fs = AsyncMock()
        mock_num = AsyncMock()
        mock_conn = AsyncMock()
        settlement = StateSettlement(validation_status="needs_human_review")

        with pytest.raises(SettlementError):
            await apply_settlement(
                settlement, "p1", 3, "v1",
                conn=mock_conn,
                char_repo=mock_char,
                setting_repo=mock_setting,
                foreshadowing_repo=mock_fs,
                numerical_repo=mock_num,
            )

        mock_char.list_by_project.assert_not_called()
        mock_char.add_state_snapshot.assert_not_called()
        mock_setting.create.assert_not_called()
        mock_fs.create.assert_not_called()
        mock_num.create.assert_not_called()

    async def test_sets_foreshadowing_pressure_high(self) -> None:
        mock_fs = AsyncMock()
        mock_fs.get_unresolved_ratio.return_value = 0.40
        settlement = StateSettlement()
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 50, "v1",
            conn=mock_conn,
            char_repo=AsyncMock(),
            setting_repo=AsyncMock(),
            foreshadowing_repo=mock_fs,
            numerical_repo=AsyncMock(),
        )
        mock_fs.mark_overdue.assert_called_once()
        mock_fs.get_unresolved_ratio.assert_called_once()
        assert settlement.foreshadowing_pressure == "high"

    async def test_sets_foreshadowing_pressure_low(self) -> None:
        mock_fs = AsyncMock()
        mock_fs.get_unresolved_ratio.return_value = 0.10
        settlement = StateSettlement()
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 50, "v1",
            conn=mock_conn,
            char_repo=AsyncMock(),
            setting_repo=AsyncMock(),
            foreshadowing_repo=mock_fs,
            numerical_repo=AsyncMock(),
        )
        assert settlement.foreshadowing_pressure == "low"

    async def test_sets_foreshadowing_pressure_medium(self) -> None:
        mock_fs = AsyncMock()
        mock_fs.get_unresolved_ratio.return_value = 0.25
        settlement = StateSettlement()
        mock_conn = AsyncMock()
        await apply_settlement(
            settlement, "p1", 50, "v1",
            conn=mock_conn,
            char_repo=AsyncMock(),
            setting_repo=AsyncMock(),
            foreshadowing_repo=mock_fs,
            numerical_repo=AsyncMock(),
        )
        assert settlement.foreshadowing_pressure == "medium"


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

    async def test_task112_normalizes_invalid_setting_key_before_validation(self) -> None:
        content = "实验室位置与历史被第一次完整揭示。"
        llm_response = _make_valid_llm_response(
            character_updates=[],
            new_settings=[
                {
                    "setting_name": "实验室位置与历史",
                    "description": "实验室位于旧矿井下方，曾用于权限实验",
                    "source_quote": "实验室位置与历史被第一次完整揭示",
                    "setting_key": "e.0.实验室.位置与历史",
                }
            ],
            foreshadowing_updates=[],
            numerical_updates=[],
            planted_hooks=[],
            resolved_hooks=[],
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
                            content=content,
                            project_id="p1",
                            chapter_number=97,
                            version_id="v97",
                        )

        assert result.validation_status == "valid"
        assert result.validation_errors == []
        assert result.new_settings[0].setting_key == "e_0.s_4ae2c4c7.n_ad166662"

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


# ---------------------------------------------------------------------------
# DB Retry Tests (Task 053)
# ---------------------------------------------------------------------------
class TestDbRetry:
    async def test_retry_max_retries_0_fails_immediately(self) -> None:
        """max_retries=0 时，第一次失败立即抛出."""
        call_count = 0

        async def _failing_func() -> None:
            nonlocal call_count
            call_count += 1
            raise sqlite3.OperationalError("database is locked")

        with pytest.raises(sqlite3.OperationalError):
            await _execute_with_db_retry(_failing_func, max_retries=0)
        assert call_count == 1

    async def test_retry_max_retries_1_succeeds_on_retry(self) -> None:
        """max_retries=1 时，第二次成功."""
        call_count = 0

        async def _eventually_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        result = await _execute_with_db_retry(
            _eventually_succeed, max_retries=1, backoff_ms=10
        )
        assert result == "success"
        assert call_count == 2

    async def test_retry_non_locked_error_not_retried(self) -> None:
        """非 locked/busy 的 OperationalError 不重试."""
        call_count = 0

        async def _wrong_error() -> None:
            nonlocal call_count
            call_count += 1
            raise sqlite3.OperationalError("no such table")

        with pytest.raises(sqlite3.OperationalError, match="no such table"):
            await _execute_with_db_retry(_wrong_error, max_retries=3)
        assert call_count == 1


# ---------------------------------------------------------------------------
# Concurrent Settlement Tests (Task 053)
# ---------------------------------------------------------------------------
class TestConcurrentSettlement:
    @pytest.mark.xfail(
        reason=(
            "SQLite on Windows does not guarantee concurrent writer progress "
            "across separate connections"
        ),
        strict=False,
    )
    async def test_concurrent_settlement_writes(self, tmp_path) -> None:
        """3 个协程同时向不同 project 写入 settlement，无异常."""
        import asyncio

        import songyan.db.connection as conn_mod
        from songyan.db.connection import get_db
        from songyan.db.migrations import init_schema

        db_path = tmp_path / "concurrent.db"
        original_settings = conn_mod.settings
        conn_mod.settings = type("S", (), {"database_url": f"sqlite:///{db_path}"})()

        try:
            await init_schema()

            # 创建 3 个不同的 project、角色和章节版本
            # character_states.source_version_id 是外键，必须先创建 chapter_versions
            async with get_db() as conn:
                for i in range(3):
                    await conn.execute(
                        """INSERT INTO projects (
                            project_id, title, genre_id, mode_id,
                            protagonist_name, estimated_chapters
                        ) VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            f"p{i}",
                            f"Project {i}",
                            "scifi",
                            "webnovel",
                            f"Protagonist {i}",
                            30,
                        ),
                    )
                    await conn.execute(
                        """INSERT INTO characters (
                            character_id, project_id, name, role_type
                        ) VALUES (?, ?, ?, ?)""",
                        (f"c{i}", f"p{i}", f"Char {i}", "protagonist"),
                    )
                    await conn.execute(
                        """INSERT INTO chapter_versions (
                            version_id, project_id, chapter_number, version_number,
                            version_type, content, word_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (f"v{i}", f"p{i}", 1, 1, "draft", "正文", 100),
                    )
                await conn.commit()

            async def _write_project(project_id: str, char_id: str, version_id: str) -> None:
                s = StateSettlement(
                    character_updates=[
                        CharacterUpdate(
                            character_id=char_id,
                            field="mood",
                            old_value="a",
                            new_value="b",
                            source_quote="q",
                        )
                    ]
                )
                async with get_db() as conn:
                    await apply_settlement(s, project_id, 1, version_id, conn=conn)
                    await conn.commit()

            # 并发执行
            await asyncio.gather(
                _write_project("p0", "c0", "v0"),
                _write_project("p1", "c1", "v1"),
                _write_project("p2", "c2", "v2"),
            )

            # 验证写入成功
            async with get_db() as conn:
                for i in range(3):
                    cursor = await conn.execute(
                        "SELECT COUNT(*) FROM character_states WHERE character_id = ?",
                        (f"c{i}",),
                    )
                    row = await cursor.fetchone()
                    assert row[0] == 1
        finally:
            conn_mod.settings = original_settings


# ---------------------------------------------------------------------------
# Atomicity Test (Task 054)
# ---------------------------------------------------------------------------
class TestSettlementAtomicity:
    async def test_settlement_atomic_rollback(self, tmp_path) -> None:
        """模拟子表写入失败，验证调用方 rollback 后无脏数据."""
        import songyan.db.connection as conn_mod
        from songyan.db.connection import get_db
        from songyan.db.migrations import init_schema
        from songyan.db.repository import CharacterRepository

        db_path = tmp_path / "atomic.db"
        original_settings = conn_mod.settings
        conn_mod.settings = type("S", (), {"database_url": f"sqlite:///{db_path}"})()

        try:
            await init_schema()

            # 创建 project、角色和 chapter_version
            async with get_db() as conn:
                await conn.execute(
                    """INSERT INTO projects (
                        project_id, title, genre_id, mode_id, protagonist_name
                    ) VALUES (?, ?, ?, ?, ?)""",
                    ("p1", "Test", "scifi", "webnovel", "Protagonist"),
                )
                await conn.execute(
                    """INSERT INTO characters (
                        character_id, project_id, name, role_type
                    ) VALUES (?, ?, ?, ?)""",
                    ("c1", "p1", "Char1", "protagonist"),
                )
                await conn.execute(
                    """INSERT INTO chapter_versions (
                        version_id, project_id, chapter_number, version_number,
                        version_type, content, word_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    ("v1", "p1", 1, 1, "draft", "正文", 100),
                )
                await conn.commit()

            # 模拟 setting_repo.create 失败
            mock_setting = AsyncMock()
            mock_setting.create.side_effect = sqlite3.OperationalError("simulated failure")

            settlement = StateSettlement(
                character_updates=[
                    CharacterUpdate(
                        character_id="c1",
                        field="mood",
                        old_value="a",
                        new_value="b",
                        source_quote="q",
                    )
                ],
                new_settings=[
                    NewSetting(
                        setting_name="古老灵石门",
                        description="补充灵气",
                        source_quote="q",
                        setting_key="xuanhuan.stone.lingshi",
                    )
                ],
            )

            async with get_db() as conn:
                await conn.execute("BEGIN")
                try:
                    await apply_settlement(
                        settlement,
                        "p1",
                        1,
                        "v1",
                        conn=conn,
                        char_repo=CharacterRepository(),
                        setting_repo=mock_setting,
                        foreshadowing_repo=AsyncMock(),
                        numerical_repo=AsyncMock(),
                    )
                    await conn.commit()
                except Exception:
                    await conn.rollback()

            # 验证 character_states 没有留下脏数据（事务已回滚）
            async with get_db() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM character_states WHERE character_id = ?",
                    ("c1",),
                )
                row = await cursor.fetchone()
                assert row[0] == 0
        finally:
            conn_mod.settings = original_settings
