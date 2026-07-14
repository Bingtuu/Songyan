"""Tests for SettlementExtractor Agent."""

from __future__ import annotations

import json
import math
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.settlement_extractor import (
    MAX_PROMPT_CHARACTER_STATES,
    MAX_PROMPT_FORESHADOWINGS,
    MAX_PROMPT_SETTINGS,
    _backfill_foreshadowing_source_version_ids,
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

    def test_non_positive_expected_resolve_chapter_becomes_none(self) -> None:
        """Task 114c: LLM 用 0 表示未知时不得触发章节硬校验."""
        data = {
            "operation": "plant",
            "description": "伏笔",
            "expected_resolve_chapter": 0,
        }
        result = _build_foreshadowing_update(data)
        assert result is not None
        assert result.expected_resolve_chapter is None

    def test_positive_expected_resolve_chapter_is_preserved(self) -> None:
        data = {
            "operation": "plant",
            "description": "伏笔",
            "expected_resolve_chapter": "130",
        }
        result = _build_foreshadowing_update(data)
        assert result is not None
        assert result.expected_resolve_chapter == 130

    def test_invalid_operation(self) -> None:
        assert _build_foreshadowing_update({"operation": "invalid"}) is None


class TestBackfillForeshadowingSourceVersionIds:
    def test_missing_source_version_id_uses_accepted_version(self) -> None:
        """Task 114c: 伏笔来源版本由代码回填，不依赖 LLM 精确输出."""
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(operation="plant", description="伏笔"),
                ForeshadowingUpdate(
                    operation="resolve",
                    description="回收伏笔",
                    source_version_id="existing-version",
                ),
            ]
        )

        updated = _backfill_foreshadowing_source_version_ids(
            settlement, "accepted-version"
        )

        assert updated == 1
        assert settlement.foreshadowing_updates[0].source_version_id == "accepted-version"
        assert settlement.foreshadowing_updates[1].source_version_id == "existing-version"


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

    def test_closing_zero_autofixed_from_formula(self) -> None:
        """171w-d: closing_value=0.0 但公式可计算为非零时，从公式推导."""
        data = {
            "character_id": "c1",
            "attribute_name": "escape_pod_communication_array_integrity",
            "opening_value": 0.0,
            "increments": [
                {"amount": 30.0, "source": "repair", "source_quote": "修复通讯阵列"},
                {"amount": 33.0, "source": "boost", "source_quote": "增强信号"},
            ],
            "decrements": [],
            "closing_value": 0.0,
        }
        result = _build_numerical_update(data)
        assert result is not None
        assert result.closing_value == 63.0

    def test_closing_zero_not_autofixed_when_formula_zero(self) -> None:
        """opening=0、无增减 → formula=0，closing_value=0.0 不被误修."""
        data = {
            "character_id": "c1",
            "attribute_name": "health",
            "opening_value": 0.0,
            "increments": [],
            "decrements": [],
            "closing_value": 0.0,
        }
        result = _build_numerical_update(data)
        assert result is not None
        assert result.closing_value == 0.0

    def test_closing_valid_preserved(self) -> None:
        """closing_value 与公式一致时，不做任何修改."""
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
        assert result.closing_value == 1.5

    @pytest.mark.parametrize("empty_value", ["无", "", None])
    def test_empty_values_do_not_crash_build(self, empty_value: object) -> None:
        data = {
            "character_id": "c1",
            "attribute_name": "level",
            "opening_value": empty_value,
            "increments": [],
            "decrements": [],
            "closing_value": empty_value,
        }

        result = _build_numerical_update(data)

        assert result is not None
        assert result.opening_value == 0.0
        assert math.isinf(result.closing_value)


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
        """Task 114a: old_value mismatch 不再报错，而是由代码回填 DB 事实源值."""
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
        # Task 114a: old_value 被自动回填，不再报错
        assert errors == []
        # 验证 old_value 已被回填为 DB 中的值
        assert settlement.character_updates[0].old_value == "悲伤"

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

    async def test_numerical_formula_wrong_autocorrected(self) -> None:
        """171w-d: closing_value=0.0 但有 opening 证据时自动纠正."""
        content = "正文"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="c1", attribute_name="level",
                    opening_value=1.0, increments=[],
                    decrements=[], closing_value=0.0,
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert errors == []
        assert settlement.numerical_updates[0].closing_value == 1.0

    async def test_numerical_formula_wrong_still_errors(self) -> None:
        """closing_value 非默认值时不匹配仍报错."""
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

    async def test_numerical_formula_wrong_no_evidence_still_errors(self) -> None:
        """无 opening/increments/decrements 证据时，closing_value 不匹配仍报错."""
        content = "正文"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="c1", attribute_name="level",
                    opening_value=0.0, increments=[],
                    decrements=[], closing_value=5.0,
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert len(errors) == 1
        assert "closing_value" in errors[0]

    async def test_empty_closing_value_reaches_formula_validation(self) -> None:
        update = _build_numerical_update({
            "character_id": "c1",
            "attribute_name": "level",
            "opening_value": "无",
            "increments": [],
            "decrements": [],
            "closing_value": "无",
        })
        assert update is not None

        errors = await _validate_settlement(
            StateSettlement(numerical_updates=[update]),
            "正文",
            [],
            [],
        )

        assert len(errors) == 1
        assert "closing_value" in errors[0]

    async def test_temperature_reading_normalized_as_snapshot(self) -> None:
        """Task 137: 科幻温度读数不应被过度台账化为增减公式."""
        content = "义肢温度达到四十七点三度，神经接口传来过载警告。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="义肢温度",
                    opening_value=37.0,
                    increments=[
                        {
                            "amount": 14.0,
                            "source": "量子谐振过载",
                            "source_quote": "义肢温度达到四十七点三度",
                        }
                    ],
                    decrements=[],
                    closing_value=47.0,
                    formula="37 + 14 = 47",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == 47.3
        assert update.closing_value == 47.3
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == "telemetry_snapshot: 47.3"

    @pytest.mark.parametrize(
        ("content", "source_quote", "closing_value"),
        [
            ("左腿义肢的温度继续下降。52.0，51.3，50.6。", "", 50.6),
            ("", "左腿义肢的温度继续下降。52.0。", 52.0),
        ],
    )
    async def test_task138d_r2_temperature_decimal_series_normalized_as_snapshot(
        self,
        content: str,
        source_quote: str,
        closing_value: float,
    ) -> None:
        """Task 138d-R2: 温度关键词后的无单位小数读数可规整为 snapshot."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="left_leg_prosthetic_temperature",
                    opening_value=54.0,
                    increments=[],
                    decrements=[
                        {
                            "amount": 1.0,
                            "usage": "散热读数",
                            "source_quote": source_quote,
                        }
                    ],
                    closing_value=closing_value,
                    formula="54 - 2 = snapshot",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == closing_value
        assert update.closing_value == closing_value
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == f"telemetry_snapshot: {closing_value}"

    async def test_task138f_temperature_without_reading_evidence_is_filtered(
        self,
    ) -> None:
        """Task 138f: 温度字段没有正文/source_quote 明确读数时被过滤."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="left_leg_prosthetic_temperature",
                    opening_value=54.0,
                    increments=[],
                    decrements=[],
                    closing_value=50.6,
                    formula="left_leg_prosthetic_temperature telemetry_snapshot: 50.6",
                )
            ]
        )

        errors = await _validate_settlement(
            settlement,
            "左腿义肢的温度继续下降，但正文没有给出具体读数。",
            [],
            [],
        )

        assert errors == []
        assert settlement.numerical_updates == []

    async def test_task138d_r2_real_resource_ledger_formula_error_still_fails(
        self,
    ) -> None:
        """Task 138d-R2: 真实资源数值不能借温度 snapshot 规则绕过硬校验."""
        content = "冷却剂库存为 50.6，清点记录只显示消耗 2 单位。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="coolant_inventory",
                    opening_value=54.0,
                    increments=[],
                    decrements=[
                        {
                            "amount": 2.0,
                            "usage": "消耗",
                            "source_quote": "清点记录只显示消耗 2 单位",
                        }
                    ],
                    closing_value=50.6,
                    formula="54 - 2 = 50.6",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        assert len(errors) == 1
        assert "coolant_inventory" in errors[0]
        assert "closing_value" in errors[0]

    @pytest.mark.parametrize(
        ("character_id", "content", "closing_value"),
        [
            (
                "lin_shen",
                "系统正在分析她的选择，然后将这些数据与林深的神经模式进行比对。"
                "“匹配度：68.1%。”",
                68.1,
            ),
            (
                "ss_047",
                "您的神经模式匹配度为——数字浮现。“47.3%。”"
                "SS-047低声重复：匹配度47.3%。",
                47.3,
            ),
        ],
    )
    async def test_task138d_r2_neural_match_rate_normalized_as_snapshot(
        self,
        character_id: str,
        content: str,
        closing_value: float,
    ) -> None:
        """Task 138d-R2: neural_pattern_match_rate 明确百分比读数可规整为 snapshot."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id=character_id,
                    attribute_name="neural_pattern_match_rate",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=closing_value,
                    formula="0 + 0 = snapshot",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == closing_value
        assert update.closing_value == closing_value
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == f"telemetry_snapshot: {closing_value}"

    async def test_task138d_r2_chinese_hour_countdown_normalized_as_snapshot(
        self,
    ) -> None:
        """Task 138d-R2: 中文小时/分钟/秒倒计时读数统一换算为秒."""
        content = "倒计时还在跳动。47小时21分03秒。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="artifact_mega_ruin",
                    attribute_name="beacon_core_countdown",
                    opening_value=170533.0,
                    increments=[],
                    decrements=[],
                    closing_value=170463.0,
                    formula="170533 + 0 = snapshot",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == 170463.0
        assert update.closing_value == 170463.0
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == "telemetry_snapshot: 170463.0"

    async def test_countdown_reading_normalized_as_snapshot(self) -> None:
        """Task 137: 倒计时读数按秒记录为快照，而不是要求编造增减台账."""
        content = "装置表面浮现出一行倒计时数字——00:59:47，且数字开始跳动。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="义肢倒计时",
                    opening_value=3600.0,
                    increments=[],
                    decrements=[
                        {
                            "amount": 1.0,
                            "usage": "倒计时跳动",
                            "source_quote": "倒计时数字——00:59:47",
                        }
                    ],
                    closing_value=3587.0,
                    formula="3600 - 1 = 3587",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == 3587.0
        assert update.closing_value == 3587.0
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == "telemetry_snapshot: 3587.0"

    async def test_progress_percent_reading_normalized_as_snapshot(self) -> None:
        """Task 137: 完成度百分比读数不应被编造成增减台账."""
        content = "数据同步完成度稳定在 94.0%，备用链路没有继续推进。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="数据同步完成度",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=94.0,
                    formula="0 + 0 = 94%",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == 94.0
        assert update.closing_value == 94.0
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == "telemetry_snapshot: 94.0"

    async def test_chinese_progress_reading_normalized_as_snapshot(self) -> None:
        """Task 137: 中文百分比读数可作为 progress snapshot 证据."""
        content = "同步进度已经抵达百分之九十四，界面只剩最后一道灰色校验线。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="同步进度",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=94.0,
                    formula="0 + 0 = 94",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == 94.0
        assert update.closing_value == 94.0
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == "telemetry_snapshot: 94.0"

    @pytest.mark.parametrize(
        ("attribute_name", "content", "source_quote", "closing_value"),
        [
            ("舱壁文字数量", "舱壁文字数量稳定在 128，剩余笔画不再重排。", "", 128.0),
            ("破译文字数量", "林深确认破译文字数量达到七十二，语义链开始闭合。", "", 72.0),
            ("自毁指令脉冲数", "", "自毁指令脉冲数为七，随后进入静默。", 7.0),
            ("新组织生长速度", "新组织生长速度达到 2.4，创面边缘出现银色纤维。", "", 2.4),
        ],
    )
    async def test_ch11_specific_telemetry_readings_normalized_as_snapshot(
        self,
        attribute_name: str,
        content: str,
        source_quote: str,
        closing_value: float,
    ) -> None:
        """Task 3R.3: 仅 Ch11 明确读数类属性可作为 telemetry snapshot."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name=attribute_name,
                    opening_value=0.0,
                    increments=[
                        {
                            "amount": 1.0,
                            "source": "读数变化",
                            "source_quote": source_quote,
                        }
                    ],
                    decrements=[],
                    closing_value=closing_value,
                    formula="0 + 1 = snapshot",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == closing_value
        assert update.closing_value == closing_value
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == f"telemetry_snapshot: {closing_value}"

    @pytest.mark.parametrize(
        ("attribute_name", "content", "closing_value"),
        [
            ("remaining_lifespan_days", "赵六冷笑，他活不过三日。", 3.0),
            ("remaining_lifespan_days", "医师摇头：余寿三日，无药可医。", 3.0),
            ("remaining_lifespan_days", "生机耗尽，他跌坐在地。", 0.0),
            ("寿命", "令牌显示，陆沉的寿命只剩三天。", 3.0),
        ],
    )
    async def test_lifespan_telemetry_reading_normalized_as_snapshot(
        self,
        attribute_name: str,
        content: str,
        closing_value: float,
    ) -> None:
        """玄幻/武侠中‘寿命/余寿/remaining_lifespan_days’是叙事读数，不是台账。"""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char-7f60fa1d",
                    attribute_name=attribute_name,
                    opening_value=4745.0,
                    increments=[],
                    decrements=[],
                    closing_value=closing_value,
                    formula="4745 - 4742 = snapshot",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == closing_value
        assert update.closing_value == closing_value
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == f"telemetry_snapshot: {closing_value}"

    @pytest.mark.parametrize(
        ("attribute_name", "content", "source_quote", "closing_value"),
        [
            ("heart_rate", "林深腕上的心率读数稳定在 142，警报还没解除。", "", 142.0),
            (
                "oxygen_concentration",
                "氧气浓度降到 18.5%，面罩内侧凝出一层雾。",
                "",
                18.5,
            ),
            (
                "chamber_pressure",
                "",
                "舱压维持在 0.74 个标准大气压，密封环没有继续泄漏。",
                0.74,
            ),
            (
                "emp_countdown",
                "EMP倒计时剩余 73 秒，蓝色电弧开始沿舱壁爬行。",
                "",
                73.0,
            ),
        ],
    )
    async def test_task3s_telemetry_readings_normalized_as_snapshot(
        self,
        attribute_name: str,
        content: str,
        source_quote: str,
        closing_value: float,
    ) -> None:
        """Task 3S.3: run-9e54a36d Ch11 遥测读数可规整为 snapshot."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name=attribute_name,
                    opening_value=0.0,
                    increments=[
                        {
                            "amount": 1.0,
                            "source": "遥测读数",
                            "source_quote": source_quote,
                        }
                    ],
                    decrements=[],
                    closing_value=closing_value,
                    formula="0 + 1 = snapshot",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == closing_value
        assert update.closing_value == closing_value
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == f"telemetry_snapshot: {closing_value}"

    @pytest.mark.parametrize(
        ("attribute_name", "content", "source_quote", "closing_value"),
        [
            ("sensor_frequency", "传感器频率稳定在 17.5 赫兹，墙内回声不再漂移。", "", 17.5),
            ("calibration_ratio", "校准比例被锁定在 0.83，误差线随即收束。", "", 0.83),
            (
                "phase_offset",
                "",
                "相位偏移读数停在 -0.25，舱壁纹路停止抖动。",
                -0.25,
            ),
        ],
    )
    async def test_task3t_generic_telemetry_readings_normalized_as_snapshot(
        self,
        attribute_name: str,
        content: str,
        source_quote: str,
        closing_value: float,
    ) -> None:
        """Task 3T.3: frequency/ratio/phase_offset 读数可规整为 snapshot."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name=attribute_name,
                    opening_value=0.0,
                    increments=[
                        {
                            "amount": 1.0,
                            "source": "遥测读数",
                            "source_quote": source_quote,
                        }
                    ],
                    decrements=[],
                    closing_value=closing_value,
                    formula="0 + 1 = snapshot",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == closing_value
        assert update.closing_value == closing_value
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == f"telemetry_snapshot: {closing_value}"

    @pytest.mark.parametrize(
        ("attribute_name", "content", "source_quote", "closing_value"),
        [
            (
                "laser_cutter_activation_time",
                "laser_cutter_activation_time=0.8 秒，刀头随即完成预热。",
                "",
                0.8,
            ),
            (
                "laser_cutter_activation_time",
                "",
                "激光切割器激活时间为 0.8 秒，控制台亮起绿色确认灯。",
                0.8,
            ),
            ("cooling_duration", "冷却耗时稳定在 12 秒，霜线不再蔓延。", "", 12.0),
            ("时间读数", "时间读数停在 3.5 秒，舱门锁芯终于松开。", "", 3.5),
        ],
    )
    async def test_task4b_time_telemetry_readings_normalized_as_snapshot(
        self,
        attribute_name: str,
        content: str,
        source_quote: str,
        closing_value: float,
    ) -> None:
        """Task 4B.3: 明确时间/耗时/激活时间读数可规整为 snapshot."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name=attribute_name,
                    opening_value=0.0,
                    increments=[
                        {
                            "amount": 1.0,
                            "source": "遥测读数",
                            "source_quote": source_quote,
                        }
                    ],
                    decrements=[],
                    closing_value=closing_value,
                    formula="0 + 1 = snapshot",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == closing_value
        assert update.closing_value == closing_value
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == f"telemetry_snapshot: {closing_value}"

    async def test_task4b_time_formula_text_is_filtered_without_evidence(self) -> None:
        """Task 138f: formula 自证的时间读数被过滤，不阻断结算."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="laser_cutter_activation_time",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=0.8,
                    formula="laser_cutter_activation_time telemetry_snapshot: 0.8",
                )
            ]
        )

        errors = await _validate_settlement(
            settlement,
            "切割器完成激活，但正文没有给出具体激活时间读数。",
            [],
            [],
        )

        assert errors == []
        assert settlement.numerical_updates == []

    @pytest.mark.parametrize(
        ("attribute_name", "content", "source_quote", "closing_value"),
        [
            (
                "core_chamber_door_gap",
                "core_chamber_door_gap=2.5 厘米，门轴随即停止颤动。",
                "",
                2.5,
            ),
            (
                "core_chamber_door_gap",
                "",
                "核心舱门缝读数稳定在 1.2 厘米，锁舌没有继续回弹。",
                1.2,
            ),
            ("密封间隙", "密封间隙只剩 0.4 毫米，冷雾被挡在外侧。", "", 0.4),
            ("conversion_countdown", "conversion_countdown 已经归零，红色倒计时熄灭。", "", 0.0),
            ("conversion_countdown", "", "倒计时清零，转换舱的警报随之中止。", 0.0),
        ],
    )
    async def test_task4c_gap_and_zero_countdown_normalized_as_snapshot(
        self,
        attribute_name: str,
        content: str,
        source_quote: str,
        closing_value: float,
    ) -> None:
        """Task 4C.3: 门缝/间隙与倒计时归零读数可规整为 snapshot."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name=attribute_name,
                    opening_value=10.0,
                    increments=[],
                    decrements=[
                        {
                            "amount": 1.0,
                            "usage": "遥测变化",
                            "source_quote": source_quote,
                        }
                    ],
                    closing_value=closing_value,
                    formula="10 - 1 = snapshot",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == closing_value
        assert update.closing_value == closing_value
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == f"telemetry_snapshot: {closing_value}"

    async def test_task4c_formula_text_is_filtered_without_evidence(self) -> None:
        """Task 138f: gap/countdown 无正文读数证据时被过滤."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="core_chamber_door_gap",
                    opening_value=10.0,
                    increments=[],
                    decrements=[],
                    closing_value=1.2,
                    formula="core_chamber_door_gap telemetry_snapshot: 1.2",
                ),
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="conversion_countdown",
                    opening_value=10.0,
                    increments=[],
                    decrements=[],
                    closing_value=0.0,
                    formula="conversion_countdown telemetry_snapshot: 0",
                ),
            ]
        )

        errors = await _validate_settlement(
            settlement,
            "核心舱门仍在闭合，转换倒计时也已经停止，但正文没有给出具体读数。",
            [],
            [],
        )

        assert errors == []
        assert settlement.numerical_updates == []

    async def test_task3t_generic_telemetry_without_evidence_is_filtered(self) -> None:
        """Task 138f: 读数类字段没有正文/source_quote 证据时不进入有效结算."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="phase_offset",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=-0.25,
                    formula="phase_offset telemetry_snapshot: -0.25",
                )
            ]
        )

        errors = await _validate_settlement(
            settlement,
            "相位仍在偏移，但正文没有给出具体相位偏移读数。",
            [],
            [],
        )

        assert errors == []
        assert settlement.numerical_updates == []

    async def test_task3s_formula_text_is_filtered_without_evidence(self) -> None:
        """Task 138f: formula 自身不能作为读数证据，候选被过滤."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="heart_rate",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=142.0,
                    formula="heart_rate telemetry_snapshot: 142",
                )
            ]
        )

        errors = await _validate_settlement(
            settlement,
            "林深的心跳明显加快，但正文没有给出具体心率读数。",
            [],
            [],
        )

        assert errors == []
        assert settlement.numerical_updates == []

    async def test_specific_telemetry_without_reading_evidence_is_filtered(self) -> None:
        """Task 138f: 白名单属性也必须有正文或 source_quote 明确读数."""
        content = "舱壁文字继续重排，林深看见破译结果正在逼近完整。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="舱壁文字数量",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=128.0,
                    formula="0 + 0 = 128",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        assert errors == []
        assert settlement.numerical_updates == []

    async def test_generic_quantity_still_requires_real_ledger_formula(self) -> None:
        """Task 3R.3: 不能把所有“数量”类属性静默当作 snapshot."""
        content = "物资数量为 7，清点记录仍显示只有一次补给入库。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="物资数量",
                    opening_value=3.0,
                    increments=[
                        {
                            "amount": 1.0,
                            "source": "补给入库",
                            "source_quote": "清点记录仍显示只有一次补给入库",
                        }
                    ],
                    decrements=[],
                    closing_value=7.0,
                    formula="3 + 1 = 7",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        assert len(errors) == 1
        assert "closing_value" in errors[0]

    async def test_task3t_real_ledger_formula_error_still_fails(self) -> None:
        """Task 3T.3: 真实数量台账不能借 snapshot 规则绕过公式硬校验."""
        content = "灵石数量为 7，清点记录只显示一次补给入库。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="灵石数量",
                    opening_value=3.0,
                    increments=[
                        {
                            "amount": 1.0,
                            "source": "补给入库",
                            "source_quote": "清点记录只显示一次补给入库",
                        }
                    ],
                    decrements=[],
                    closing_value=7.0,
                    formula="3 + 1 = 7",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        assert len(errors) == 1
        assert "closing_value" in errors[0]

    async def test_unevidenced_telemetry_formula_is_filtered(self) -> None:
        """Task 138f: 没有正文读数证据时，不写入有效 telemetry 数值."""
        content = "义肢过热，但正文没有给出具体读数。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="义肢温度",
                    opening_value=37.0,
                    increments=[],
                    decrements=[],
                    closing_value=47.0,
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        assert errors == []
        assert settlement.numerical_updates == []

    async def test_unevidenced_progress_formula_is_filtered(self) -> None:
        """Task 138f: 完成度没有读数证据时，过滤无证据 numerical_update."""
        content = "数据同步仍在进行，但正文没有给出完成度读数。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="数据同步完成度",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=94.0,
                    formula="0 + 0 = 94",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        assert errors == []
        assert settlement.numerical_updates == []

    async def test_task138f_consciousness_upload_progress_without_reading_is_filtered(
        self,
    ) -> None:
        """Task 138f: `run-9f87da6f` 类概念性进度条不能生成有效数值."""
        content = (
            "舱壁上的文字开始显示进度条。不是数字，而是图形——一个圆环正在缓慢地填满，"
            "从底部开始，顺时针旋转。现在已经填满了大约三分之一。"
        )
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="consciousness_upload_progress",
                    opening_value=0.0,
                    increments=[{"amount": 33.3, "source": "图形进度", "source_quote": ""}],
                    decrements=[],
                    closing_value=60.0,
                    formula="0 + 33.3 = 60.0",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        assert errors == []
        assert settlement.numerical_updates == []

    async def test_task138f_consciousness_upload_progress_with_reading_snapshot(
        self,
    ) -> None:
        """Task 138f: 有明确百分比读数时，意识上传进度可规整为 snapshot."""
        content = "舱壁显示意识上传进度达到 60%，红色圆环随即停住。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="consciousness_upload_progress",
                    opening_value=0.0,
                    increments=[{"amount": 33.3, "source": "图形进度", "source_quote": ""}],
                    decrements=[],
                    closing_value=60.0,
                    formula="0 + 33.3 = 60.0",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == 60.0
        assert update.closing_value == 60.0
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == "telemetry_snapshot: 60.0"

    @pytest.mark.parametrize(
        ("attribute_name", "content", "closing_value"),
        [
            (
                "left_leg_prosthetic_temperature",
                "左腿义肢的温度继续下降。52.0，51.3，50.6。",
                50.6,
            ),
            ("neural_pattern_match_rate", "系统显示匹配度：68.1%。", 68.1),
            ("beacon_core_countdown", "倒计时还在跳动。47小时21分03秒。", 170463.0),
        ],
    )
    async def test_task138f_replay_known_evidenced_telemetry_blockers(
        self,
        attribute_name: str,
        content: str,
        closing_value: float,
    ) -> None:
        """Task 138f replay/eval: 既有有证据 telemetry 阻断样本仍可通过."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name=attribute_name,
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=closing_value,
                    formula="0 + 0 = wrong",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        assert errors == []
        assert settlement.numerical_updates[0].closing_value == closing_value
        assert settlement.numerical_updates[0].formula == (
            f"telemetry_snapshot: {closing_value}"
        )

    @pytest.mark.parametrize(
        ("attribute_name", "content", "closing_value"),
        [
            (
                "channel_wall_contraction_period",
                "舱壁上浮出新的节律读数。收缩周期：1.7秒。",
                1.7,
            ),
            (
                "channel_wall_relaxation_period",
                "另一行读数随即亮起。舒张周期：1.1秒。",
                1.1,
            ),
            (
                "knife_sheath_spring_tension_decay",
                "刀鞘卡扣的弹簧张力衰减了12%。",
                12.0,
            ),
            (
                "vertical_pipe_depth",
                "通道底部有微弱的蓝光，距离大约二十米。",
                20.0,
            ),
            (
                "liquid_metal_tentacle_distance",
                "银白色液态金属的距离：大约八米。",
                8.0,
            ),
        ],
    )
    async def test_task138d_r2_environment_snapshot_allowlist(
        self,
        attribute_name: str,
        content: str,
        closing_value: float,
    ) -> None:
        """Task 138d-R2: 明确环境/结构读数 allowlist 可规整为 snapshot."""
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name=attribute_name,
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=closing_value,
                    formula="0 + 0 = wrong",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == closing_value
        assert update.closing_value == closing_value
        assert update.increments == []
        assert update.decrements == []
        assert update.formula == f"telemetry_snapshot: {closing_value}"

    async def test_task138d_r2_allowlist_without_reading_is_filtered(self) -> None:
        """Task 138d-R2: allowlist 字段无明确读数时仍不能进入有效结算."""
        content = "舱壁的收缩周期变得紊乱，但正文没有给出秒数读数。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="lin_shen",
                    attribute_name="channel_wall_contraction_period",
                    opening_value=2.0,
                    increments=[],
                    decrements=[],
                    closing_value=1.7,
                    formula="2.0 + 0 = 1.7",
                )
            ]
        )

        errors = await _validate_settlement(settlement, content, [], [])

        assert errors == []
        assert settlement.numerical_updates == []

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

    async def test_foreshadowing_current_chapter_expected_backfilled(self) -> None:
        """Task 121e: 同章 expected_resolve_chapter 可安全回填为下一章."""
        content = "正文"
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="plant",
                    description="当前章新埋伏笔",
                    expected_resolve_chapter=8,
                    source_version_id="v8",
                )
            ]
        )

        errors = await _validate_settlement(
            settlement,
            content,
            [],
            [],
            chapter_number=8,
            project_id="proj-test",
        )

        assert errors == []
        assert settlement.foreshadowing_updates[0].expected_resolve_chapter == 9

    async def test_foreshadowing_past_expected_still_fails(self) -> None:
        """Task 121e: 早于当前章节的预计回收仍是硬错误."""
        content = "正文"
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="plant",
                    description="过期伏笔",
                    expected_resolve_chapter=7,
                    source_version_id="v8",
                )
            ]
        )

        errors = await _validate_settlement(
            settlement,
            content,
            [],
            [],
            chapter_number=8,
            project_id="proj-test",
        )

        assert len(errors) == 1
        assert "必须大于当前章节" in errors[0]

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

    # -----------------------------------------------------------------------
    # Task 114a: Ch103 回归测试
    # -----------------------------------------------------------------------
    async def test_ch103_old_value_backfill_from_db(self) -> None:
        """Ch103 回归：old_value 由 DB 事实源回填，不依赖 LLM 精确复现.

        复现场景：LLM 输出截断的 old_value，但 DB 中有完整值。
        修复后：验证通过，old_value 被自动回填为 DB 中的完整值。
        """
        db_full_value = (
            "警觉，专注，震惊（发现守门人版本协议被修改、自己出现在失踪名单上），"
            "决绝（决定带走终端），困惑（守门人行为诡异），警觉（观察窗出现异常暗线），"
            "认知不适（右眼刺痛），震惊（手套在说话），愤怒（守门人封锁他），"
            "决绝（主动接触门扉表面读取异物记忆碎片），"
            "震惊（看到三十年前事故真相——17名研究员被空间压缩闷杀，日志被篡改），"
            "愤怒（发现盖亚环高层掩盖真相）"
        )
        llm_truncated_value = (
            "警觉（观察窗出现异常暗线），认知不适（右眼刺痛），震惊（手套在说话），"
            "愤怒（守门人封锁他），决绝（主动接触门扉表面读取异物记忆碎片），"
            "震惊（看到三十年前事故真相——17名研究员被空间压缩闷杀，日志被篡改），"
            "愤怒（发现盖亚环高层掩盖真相）"
        )
        content = "宋言震惊地发现真相，愤怒地冲向守门人。"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char-ce09ac00",
                    field="mental_state",
                    old_value=llm_truncated_value,  # LLM 输出的截断值
                    new_value="愤怒，决绝",
                    source_quote="宋言震惊地发现真相",
                )
            ]
        )
        current_states = [
            CharacterState(
                character_id="char-ce09ac00",
                field="mental_state",
                value=db_full_value,  # DB 中的完整事实源
            )
        ]

        # 修复前：验证失败，报错 old_value mismatch
        # 修复后：验证通过，old_value 被回填为 db_full_value
        errors = await _validate_settlement(settlement, content, current_states, [])
        assert errors == [], f"预期无错误，实际: {errors}"
        assert settlement.character_updates[0].old_value == db_full_value, (
            "old_value 应被回填为 DB 中的完整值"
        )

    async def test_ch103_old_value_backfill_multiple_fields(self) -> None:
        """Ch103 回归：多个字段同时回填 old_value."""
        content = "宋言感到身体不适，背包里的物品散落一地。"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char-ce09ac00",
                    field="mental_state",
                    old_value="截断的心理状态",
                    new_value="愤怒",
                    source_quote="宋言感到身体不适",
                ),
                CharacterUpdate(
                    character_id="char-ce09ac00",
                    field="physical_state",
                    old_value="截断的身体状态",
                    new_value="虚弱",
                    source_quote="身体不适",
                ),
                CharacterUpdate(
                    character_id="char-ce09ac00",
                    field="inventory",
                    old_value="截断的物品列表",
                    new_value="终端、手套",
                    source_quote="物品散落一地",
                ),
            ]
        )
        current_states = [
            CharacterState(
                character_id="char-ce09ac00",
                field="mental_state",
                value="完整的心理状态：警觉、专注、震惊",
            ),
            CharacterState(
                character_id="char-ce09ac00",
                field="physical_state",
                value="完整的身体状态：健康、有力",
            ),
            CharacterState(
                character_id="char-ce09ac00",
                field="inventory",
                value="完整的物品列表：终端、手套、笔记本",
            ),
        ]

        errors = await _validate_settlement(settlement, content, current_states, [])
        assert errors == []
        # 验证所有 old_value 都被回填
        for i, field in enumerate(["mental_state", "physical_state", "inventory"]):
            assert settlement.character_updates[i].old_value == current_states[i].value, (
                f"{field} 的 old_value 未被正确回填"
            )

    async def test_ch103_old_value_backfill_with_warning(self) -> None:
        """Ch103 回归：未知角色/字段触发校验警告，不静默掩盖.

        当 LLM 输出的 old_value 与 DB 值差异过大（非截断关系），
        或涉及未知角色/字段时，应触发警告但不阻断。
        """
        content = "新角色林凡出现。"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char-unknown",  # 未知角色
                    field="mood",
                    old_value="完全不相关的值",
                    new_value="好奇",
                    source_quote="新角色林凡出现",
                )
            ]
        )
        current_states = []  # DB 中无此角色状态

        # 未知角色：验证跳过，不报错
        errors = await _validate_settlement(settlement, content, current_states, [])
        assert errors == []

    async def test_task138l_signal_pulse_latency_coordinate_telemetry_normalized(self) -> None:
        """Task 138l: 信号/脉冲/延迟/坐标类遥测属性按 snapshot 归一化."""
        content = (
            "外部信号脉冲宽度 2.7 毫秒，传输计数 6 次，"
            "坐标误差 0.0003 角秒，节点响应延迟 11.3 毫秒。"
        )
        cases = [
            ("external_signal_pulse_width_ms", 2.7),
            ("external_signal_transmission_count", 6.0),
            ("coordinate_error_arcseconds", 0.0003),
            ("format_conversion_node_response_latency", 11.3),
        ]
        for attr_name, closing_value in cases:
            settlement = StateSettlement(
                numerical_updates=[
                    NumericalUpdate(
                        character_id="char_lin_shen",
                        attribute_name=attr_name,
                        opening_value=0.0,
                        increments=[],
                        decrements=[],
                        closing_value=closing_value,
                        formula="0 + 0 = 0",
                    )
                ]
            )
            errors = await _validate_settlement(settlement, content, [], [])
            update = settlement.numerical_updates[0]
            assert errors == [], f"{attr_name} should not error"
            assert update.opening_value == closing_value
            assert update.closing_value == closing_value
            assert update.formula == f"telemetry_snapshot: {closing_value}"

    async def test_task138l_telemetry_formula_fallback_filters_without_evidence(self) -> None:
        """Task 138l: 公式声明 telemetry snapshot 但正文无读数时过滤，不报错."""
        content = "外部信号存在，但正文没有给出脉冲宽度读数。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_lin_shen",
                    attribute_name="external_signal_pulse_width_ms",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=2.7,
                    formula="telemetry snapshot",
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert errors == []
        assert settlement.numerical_updates == []

    async def test_task138l_unknown_attribute_name_but_telemetry_formula_normalized(self) -> None:
        """Task 138l: 属性名不在关键词列表但公式声明 telemetry 时仍按 snapshot 处理."""
        content = "custom_alpha_metric 读数为 42。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="custom_alpha_metric",
                    opening_value=0.0,
                    increments=[],
                    decrements=[],
                    closing_value=42.0,
                    formula="telemetry snapshot",
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        update = settlement.numerical_updates[0]
        assert errors == []
        assert update.opening_value == 42.0
        assert update.closing_value == 42.0
        assert update.formula == "telemetry_snapshot: 42.0"

    async def test_task138l_real_ledger_with_telemetry_formula_still_validated(self) -> None:
        """Task 138l: 真实台账字段即便 formula 含 telemetry 也不绕过硬校验（当正文无读数时）."""
        content = "灵石数量没有读数。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char_001",
                    attribute_name="spirit_stone_count",
                    opening_value=3.0,
                    increments=[
                        {"amount": 1.0, "source": "采集", "source_quote": "采集到一块灵石"}
                    ],
                    decrements=[],
                    closing_value=7.0,
                    formula="telemetry snapshot",
                )
            ]
        )
        errors = await _validate_settlement(settlement, content, [], [])
        assert len(errors) == 1
        assert "closing_value" in errors[0]


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
        """Task 114a: old_value mismatch 不再导致 validation 失败，而是自动回填.

        原测试期望 old_value='错误的旧值' 与 DB 值='冷静' 不匹配时 validation 失败。
        修复后：old_value 被自动回填为 DB 值='冷静'，validation 通过。
        """
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

        # Task 114a: old_value 被自动回填，validation 通过
        assert result.validation_status == "valid"
        assert len(result.validation_errors) == 0
        # 验证 old_value 已被回填为 DB 中的值
        assert result.character_updates[0].old_value == "冷静"

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
    @pytest.mark.performance
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



class TestInferSettingCategory:
    """Task 138n: critical 分类启发式收紧."""

    def _category(
        self, *, protagonist_names: set[str] | None = None, **kwargs: object
    ) -> str:
        from songyan.agents.settlement_extractor._apply import _infer_setting_category
        from songyan.models import NewSetting

        kwargs.setdefault("source_quote", "")
        return _infer_setting_category(
            NewSetting(**kwargs),  # type: ignore[arg-type]
            protagonist_names=protagonist_names,
        )

    def test_protagonist_ability_is_critical(self) -> None:
        assert (
            self._category(
                setting_key="protagonist.ability.flame",
                setting_name="主角能力：焚天烈焰",
                description="林渊觉醒后获得的能力",
            )
            == "critical"
        )

    def test_protagonist_talent_bloodline_is_critical(self) -> None:
        assert (
            self._category(
                setting_key="linyuan.bloodline",
                setting_name="林渊血脉",
                description="传承自上古的血脉力量",
                protagonist_names={"林渊"},
            )
            == "critical"
        )

    def test_english_main_protagonist_state_is_critical(self) -> None:
        assert (
            self._category(
                setting_key="main_character.state",
                setting_name="protagonist status",
                description="描述主角当前状态",
            )
            == "critical"
        )

    def test_core_anchor_alone_is_background(self) -> None:
        """仅命中核心/锚/anchor/core 不再判为 critical."""
        assert (
            self._category(
                setting_key="ruins.core.anchor",
                setting_name="遗迹核心锚点",
                description="维持空间稳定的锚点",
            )
            == "background"
        )

    def test_bloodline_without_protagonist_is_background(self) -> None:
        assert (
            self._category(
                setting_key="world.bloodline.old",
                setting_name="古血脉",
                description="一种古老传承",
            )
            == "background"
        )

    def test_technical_still_overrides_critical(self) -> None:
        """technical 关键词优先于 critical 判定."""
        assert (
            self._category(
                setting_key="protagonist.ability.omega",
                setting_name="主角能力 Ω",
                description="型号 Ω 的引擎参数",
            )
            == "technical"
        )
