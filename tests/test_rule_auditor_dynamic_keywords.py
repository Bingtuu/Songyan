"""Tests for RuleAuditor dynamic keyword injection (Task 170m)."""

from __future__ import annotations

from songyan.agents.rule_auditor import (
    detect_exposition_carriers,
    detect_human_voice_homogeneity,
    run_rule_audit,
)


class TestDynamicExpositionCarrierKeywords:
    """Verify detect_exposition_carriers adapts to project-specific keywords."""

    def test_dynamic_character_names_trigger_vision_dump(self) -> None:
        text = "陈默看见了建造者——他们站在一个巨大的空间里，周身流动着液态星光。"
        matches = detect_exposition_carriers(
            text, character_names={"陈默"}
        )
        assert any(m.carrier_type == "vision_dump" for m in matches)

    def test_hardcoded_names_not_scored_without_injection(self) -> None:
        """Task 171a 体裁解耦：未注入 character_names 时，不再对写死的本项目主角名误报.

        旧行为（`_DEFAULT_CHARACTER_NAMES={林渊,宋晚,苏晚}` fallback）会让 vision_dump
        在任何项目上都命中"林渊看见了…"，属体裁窄化失真。新契约：无注入 => 该维度不计分。
        注入后（见上一用例）应正常命中。
        """
        text = "林渊看见了建造者——他们站在一个巨大的空间里，周身流动着液态星光。"
        matches = detect_exposition_carriers(text)
        assert not any(m.carrier_type == "vision_dump" for m in matches)
        # 注入项目实际角色名后应恢复检测
        injected = detect_exposition_carriers(text, character_names={"林渊"})
        assert any(m.carrier_type == "vision_dump" for m in injected)

    def test_dynamic_non_character_entity_direct_revelation(self) -> None:
        text = (
            '织网者的声音在舱室里回荡："织网者文明没有灭绝，它们把自己分裂成七块意识碎片，'
            '嵌入了七把钥匙的基因序列之中，每一代钥匙的死亡都会释放一块碎片，等待最后的共鸣。"'
        )
        matches = detect_exposition_carriers(
            text, non_character_keywords={"织网者"}
        )
        assert any(m.carrier_type == "direct_revelation_monologue" for m in matches)

    def test_dynamic_non_character_entity_not_detected_without_injection(self) -> None:
        text = (
            '织网者的声音在舱室里回荡："织网者文明没有灭绝，它们把自己分裂成七块意识碎片，'
            '嵌入了七把钥匙的基因序列之中。"'
        )
        matches = detect_exposition_carriers(text)
        assert not any(
            m.carrier_type == "direct_revelation_monologue" for m in matches
        )

    def test_dynamic_setting_keyword_info_delivery(self) -> None:
        text = (
            '老雷平静地说："相位签名追踪是门后世界留下的唯一可读取痕迹，'
            '它会在每一次跃迁之后留下一段无法抹除的波形，这段波形就是坐标本身。"'
        )
        matches = detect_exposition_carriers(
            text, info_delivery_keywords={"相位签名", "跃迁"}
        )
        assert any(m.carrier_type == "info_delivery_dialogue" for m in matches)

    def test_dynamic_threshold_direct_revelation(self) -> None:
        text = '残影说："方舟是牢笼。"'  # 8 chars inside quotes, below default 50
        assert not any(
            m.carrier_type == "direct_revelation_monologue"
            for m in detect_exposition_carriers(text)
        )
        matches = detect_exposition_carriers(
            text,
            non_character_keywords={"方舟"},
            direct_revelation_quote_min_chars=5,
        )
        assert any(m.carrier_type == "direct_revelation_monologue" for m in matches)

    def test_run_rule_audit_passes_dynamic_keywords(self) -> None:
        text = (
            '织网者的声音在舱室里回荡："织网者文明没有灭绝，它们把自己分裂成七块意识碎片，'
            '嵌入了七把钥匙的基因序列之中，每一代钥匙的死亡都会释放一块碎片，等待最后的共鸣。"'
        )
        result = run_rule_audit(
            text,
            word_count_target=10,
            non_character_keywords={"织网者"},
        )
        assert any(
            m.carrier_type == "direct_revelation_monologue"
            for m in result.exposition_carrier_matches
        )


class TestDynamicHumanVoiceHomogeneity:
    """Verify non-human speaker filter can be injected."""

    def test_dynamic_non_character_filter(self) -> None:
        text = (
            '织网者说："你们必须马上离开这里。通道已经封死了。"\n'
            '陈薇说："你们必须马上离开这里。通道已经封死了。"\n'
            '老雷说："你们必须马上离开这里。通道已经封死了。"'
        )
        matches = detect_human_voice_homogeneity(
            text, non_character_keywords={"织网者"}
        )
        assert any(m.carrier_type == "human_voice_homogeneity" for m in matches)
        # The filtered-out entity should not appear in any match.
        for m in matches:
            assert "织网者" not in m.matched_text

    def test_default_non_character_filter_still_works(self) -> None:
        text = (
            '建造者说："你们必须马上离开这里。通道已经封死了。"\n'
            '陈薇说："你们必须马上离开这里。通道已经封死了。"\n'
            '老雷说："你们必须马上离开这里。通道已经封死了。"'
        )
        matches = detect_human_voice_homogeneity(text)
        assert any(m.carrier_type == "human_voice_homogeneity" for m in matches)
        for m in matches:
            assert "建造者" not in m.matched_text
