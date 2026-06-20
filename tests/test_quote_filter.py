"""Tests for settlement source_quote filtering (Task 072)."""

from __future__ import annotations

from songyan.agents.settlement_extractor._quote_filter import (
    _contains_keyword,
    _is_valid_source_quote,
    filter_settlement_source_quotes,
)
from songyan.models import (
    CharacterUpdate,
    Increment,
    NewSetting,
    NumericalUpdate,
    StateSettlement,
)


class TestContainsKeyword:
    """关键词匹配测试."""

    def test_exact_match(self) -> None:
        assert _contains_keyword("林凡吸收了灵石", "灵石") is True

    def test_partial_char_match(self) -> None:
        # "灵石" -> 至少一半字（1/2=1）出现在 quote 中
        assert _contains_keyword("灵气涌动", "灵石") is True

    def test_no_match(self) -> None:
        assert _contains_keyword("天气晴朗", "灵石") is False

    def test_empty_keyword(self) -> None:
        assert _contains_keyword("任何文本", "") is True


class TestIsValidSourceQuote:
    """单条 source_quote 有效性测试."""

    def test_valid_quote(self) -> None:
        content = "林凡握紧双拳，眼中燃起怒火。"
        assert _is_valid_source_quote("林凡握紧双拳", content, "林凡") is True

    def test_too_short(self) -> None:
        content = "正文"
        assert _is_valid_source_quote("短", content) is False

    def test_too_long(self) -> None:
        content = "x" * 200
        assert _is_valid_source_quote("x" * 100, content) is False

    def test_not_in_content(self) -> None:
        content = "林凡在修炼"
        assert _is_valid_source_quote("萧尘在战斗", content) is False

    def test_missing_keyword(self) -> None:
        content = "林凡在修炼"
        assert _is_valid_source_quote("林凡在修炼", content, "萧尘") is False

    def test_empty_quote(self) -> None:
        assert _is_valid_source_quote("", "正文") is True


class TestFilterSettlementSourceQuotes:
    """Settlement 级别过滤测试."""

    async def test_filters_long_quote(self) -> None:
        content = "林凡握紧双拳，眼中燃起怒火。"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="林凡",
                    field="情绪",
                    old_value="冷静",
                    new_value="愤怒",
                    source_quote="林凡握紧双拳，眼中燃起怒火，这股怒火仿佛要将整个世界吞噬殆尽" * 3,
                )
            ]
        )
        count = await filter_settlement_source_quotes(settlement, content)
        assert count == 1
        assert settlement.character_updates[0].source_quote == ""

    async def test_filters_short_quote(self) -> None:
        content = "正文"
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="灵石",
                    description="灵气结晶",
                    source_quote="灵",
                    setting_key="spirit_stone",
                )
            ]
        )
        count = await filter_settlement_source_quotes(settlement, content)
        assert count == 1
        assert settlement.new_settings[0].source_quote == ""

    async def test_filters_quote_not_in_content(self) -> None:
        content = "林凡在山上修炼"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="林凡",
                    field="位置",
                    old_value="山下",
                    new_value="山上",
                    source_quote="萧尘在海里游泳",
                )
            ]
        )
        count = await filter_settlement_source_quotes(settlement, content)
        assert count == 1
        assert settlement.character_updates[0].source_quote == ""

    async def test_deduplicates_same_setting_key(self) -> None:
        """同一 setting_key 保留最短 quote."""
        content = "他取出一枚灵石。灵石发出微光。"
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="灵石",
                    description="灵气结晶",
                    source_quote="他取出一枚灵石",
                    setting_key="spirit_stone",
                ),
                NewSetting(
                    setting_name="灵石",
                    description="灵气结晶",
                    source_quote="灵石发出微光",
                    setting_key="spirit_stone",
                ),
            ]
        )
        count = await filter_settlement_source_quotes(settlement, content)
        assert count == 1
        quotes = [s.source_quote for s in settlement.new_settings]
        assert "" in quotes
        assert "灵石" in "".join(quotes)

    async def test_keeps_valid_quotes(self) -> None:
        content = "林凡握紧双拳，眼中燃起怒火。他取出一枚灵石。"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="林凡",
                    field="情绪",
                    old_value="冷静",
                    new_value="愤怒",
                    source_quote="林凡握紧双拳",
                )
            ],
            new_settings=[
                NewSetting(
                    setting_name="灵石",
                    description="灵气结晶",
                    source_quote="取出一枚灵石",
                    setting_key="spirit_stone",
                )
            ],
        )
        count = await filter_settlement_source_quotes(settlement, content)
        assert count == 0
        assert settlement.character_updates[0].source_quote == "林凡握紧双拳"
        assert settlement.new_settings[0].source_quote == "取出一枚灵石"

    async def test_filters_numerical_quotes(self) -> None:
        content = "灵气涌入体内，修为提升。"
        settlement = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="林凡",
                    attribute_name="修为",
                    opening_value=1.0,
                    closing_value=2.0,
                    increments=[
                        Increment(amount=1.0, source="修炼", source_quote="灵气涌入体内"),
                        Increment(amount=0.5, source="丹药", source_quote="这句话不在正文中"),
                    ],
                )
            ]
        )
        count = await filter_settlement_source_quotes(settlement, content)
        assert count == 1
        assert settlement.numerical_updates[0].increments[0].source_quote == "灵气涌入体内"
        assert settlement.numerical_updates[0].increments[1].source_quote == ""

    async def test_reduces_total_quotes(self) -> None:
        """模拟 30 条 quote -> 过滤后 <= 15 条保留."""
        content = "林凡在修炼。他取出一枚灵石。灵气在体内涌动。"

        character_updates = []
        for i in range(10):
            # 5 条有效（含关键词），5 条过长
            quote = "林凡在修炼" if i < 5 else "林凡在修炼" * 20
            character_updates.append(
                CharacterUpdate(
                    character_id="林凡",
                    field="状态",
                    old_value="旧",
                    new_value="新",
                    source_quote=quote,
                )
            )

        new_settings = []
        for i in range(10):
            # 5 条有效（含关键词），5 条不存在于正文
            quote = "取出一枚灵石" if i < 5 else "不存在的内容"
            new_settings.append(
                NewSetting(
                    setting_name="灵石",
                    description="描述",
                    source_quote=quote,
                    setting_key=f"spirit_stone_{i}",  # 不同 key，避免去重
                )
            )

        numerical_updates = []
        for i in range(10):
            # 5 条有效，5 条过短
            quote = "灵气在体内涌动" if i < 5 else "短"
            numerical_updates.append(
                NumericalUpdate(
                    character_id="林凡",
                    attribute_name="修为",
                    opening_value=1.0,
                    closing_value=2.0,
                    increments=[Increment(amount=1.0, source="修炼", source_quote=quote)],
                )
            )

        settlement = StateSettlement(
            character_updates=character_updates,
            new_settings=new_settings,
            numerical_updates=numerical_updates,
        )

        count = await filter_settlement_source_quotes(settlement, content)
        assert count == 15  # 15 条被过滤

        # 统计剩余非空 quote
        remaining = 0
        for cu in settlement.character_updates:
            if cu.source_quote:
                remaining += 1
        for ns in settlement.new_settings:
            if ns.source_quote:
                remaining += 1
        for nu in settlement.numerical_updates:
            for inc in nu.increments:
                if inc.source_quote:
                    remaining += 1

        assert remaining == 15  # 30 - 15 = 15 条保留

    # -----------------------------------------------------------------------
    # Task 114a: Ch103 回归测试
    # -----------------------------------------------------------------------
    async def test_ch103_quote_filter_uses_character_name_not_id(self) -> None:
        """Ch103 回归：quote_filter 使用角色名而非内部 character_id 做关键词校验.

        复现场景：CharacterUpdate 使用内部 ID 'char-ce09ac00'，
        但中文正文中只会出现角色名 '宋言'，不会出现内部 ID。
        修复前：合法引用被误杀（因为 quote 中不含 'char-ce09ac00'）。
        修复后：使用角色名 '宋言' 做关键词校验，合法引用保留。
        """
        from unittest.mock import AsyncMock, patch

        from songyan.db.repository import CharacterRepository
        from songyan.models import Character

        content = "宋言握紧双拳，眼中燃起怒火。他决定要查出真相。"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char-ce09ac00",  # 内部 ID，不会出现在正文中
                    field="mental_state",
                    old_value="冷静",
                    new_value="愤怒",
                    source_quote="宋言握紧双拳，眼中燃起怒火",  # 含角色名，合法
                )
            ]
        )

        # Mock CharacterRepository.get 返回角色名 '宋言'
        mock_char_repo = AsyncMock(spec=CharacterRepository)
        mock_char_repo.get.return_value = Character(
            character_id="char-ce09ac00",
            project_id="proj-test",
            name="宋言",
            role_type="protagonist",
        )

        with patch(
            "songyan.agents.settlement_extractor._quote_filter.CharacterRepository",
            return_value=mock_char_repo,
        ):
            count = await filter_settlement_source_quotes(settlement, content)

        # 修复前：count == 1（quote 被误杀，因为不含 'char-ce09ac00'）
        # 修复后：count == 0（使用 '宋言' 做关键词，匹配成功）
        assert count == 0, f"预期 0 条被过滤，实际 {count} 条"
        assert settlement.character_updates[0].source_quote != "", (
            "合法引用不应被清空"
        )

    async def test_ch103_quote_filter_fallback_to_length_check(self) -> None:
        """Ch103 回归：角色名缺失时回退至长度与存在性校验.

        当无法通过 character_id 查询到角色名时，不应阻断，
        而应回退至仅做长度和存在性校验。
        """
        from unittest.mock import AsyncMock, patch

        from songyan.db.repository import CharacterRepository

        content = "神秘人出现在门口，手中握着发光的物体。"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char-unknown-001",  # 未知角色，查不到名字
                    field="position",
                    old_value="室外",
                    new_value="室内",
                    source_quote="神秘人出现在门口",  # 合法引用
                )
            ]
        )

        # Mock CharacterRepository.get 返回 None（查不到角色名）
        mock_char_repo = AsyncMock(spec=CharacterRepository)
        mock_char_repo.get.return_value = None

        with patch(
            "songyan.agents.settlement_extractor._quote_filter.CharacterRepository",
            return_value=mock_char_repo,
        ):
            count = await filter_settlement_source_quotes(settlement, content)

        # 回退至长度和存在性校验，合法引用不应被过滤
        assert count == 0
        assert settlement.character_updates[0].source_quote != ""

    async def test_ch103_quote_filter_internal_id_still_filtered(self) -> None:
        """Ch103 回归：内部 ID 本身作为 quote 仍应被过滤.

        如果 quote 中真的包含内部 ID（如 'char-ce09ac00'），
        这显然是错误的，应该被过滤。
        """
        from unittest.mock import AsyncMock, patch

        from songyan.db.repository import CharacterRepository
        from songyan.models import Character

        content = "宋言握紧双拳。char-ce09ac00 是内部 ID 不应出现。"
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char-ce09ac00",
                    field="mood",
                    old_value="冷静",
                    new_value="愤怒",
                    source_quote="char-ce09ac00 状态变化",  # 含内部 ID，非法
                )
            ]
        )

        mock_char_repo = AsyncMock(spec=CharacterRepository)
        mock_char_repo.get.return_value = Character(
            character_id="char-ce09ac00",
            project_id="proj-test",
            name="宋言",
            role_type="protagonist",
        )

        with patch(
            "songyan.agents.settlement_extractor._quote_filter.CharacterRepository",
            return_value=mock_char_repo,
        ):
            count = await filter_settlement_source_quotes(settlement, content)

        # quote 中含内部 ID，且不含角色名，应被过滤
        assert count == 1
        assert settlement.character_updates[0].source_quote == ""
