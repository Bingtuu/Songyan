"""Task 193.v tests — setting tracking 正文引用词条匹配修复.

验收用例来自 193.s 诊断报告（archive/v10/reports/193s-setting-tracking-root-cause.md）
的逐章证据：F1 词条生成（《》拆分 + core phrase 下限）、F2 虚字归一化、
F3 name 派生 term CJK 后缀放宽；共享 `_term_in_content` 默认行为必须不变。
"""

from __future__ import annotations

from songyan.agents.settlement_extractor._apply import (
    _detect_setting_references,
    _setting_reference_terms,
    _term_in_content,
)


def _setting(
    tracking_id: str,
    setting_key: str,
    setting_name: str,
    description: str = "",
    category: str = "critical",
) -> dict:
    return {
        "tracking_id": tracking_id,
        "setting_key": setting_key,
        "setting_name": setting_name,
        "description": description,
        "category": category,
        "status": "active",
    }


class TestF1TermGeneration:
    def test_book_title_marks_split_from_name(self) -> None:
        """诊断 B 案例：`灵渊《灵渊拳》第一式` 必须拆出短核心词."""
        setting = _setting(
            "t1",
            "xuanhuan_lingyuan.technique.lingyuan_quan_first_form",
            "灵渊《灵渊拳》第一式",
        )
        terms = _setting_reference_terms(setting)
        assert "灵渊拳" in terms
        assert "第一式" in terms

    def test_two_char_core_phrases_still_excluded(self) -> None:
        """core phrase 下限 3：description 拆出的 2 字词仍排除（name 拆分件 len>=2 为既有语义）."""
        setting = _setting("t1", "x.y", "灵渊《灵渊拳》第一式", "血脉")
        terms = _setting_reference_terms(setting)
        assert "血脉" not in terms

    def test_short_core_phrase_floor_three(self) -> None:
        """诊断 C 案例：`守门者后人·母亲血脉` 必须产出 3 字核心词 `守门者`."""
        setting = _setting("t1", "x.mother_descendant", "守门者后人·母亲血脉")
        terms = _setting_reference_terms(setting)
        assert "守门者" in terms
        assert "母亲血脉" in terms

    def test_detect_lingyuan_quan_ch104_book_title(self) -> None:
        """诊断 B-Ch104 正文原句：`《灵渊拳》第一式从他右拳中轰出`."""
        setting = _setting(
            "t1",
            "xuanhuan_lingyuan.technique.lingyuan_quan_first_form",
            "灵渊《灵渊拳》第一式",
        )
        refs = _detect_setting_references(
            "《灵渊拳》第一式从他右拳中轰出，空气都在震颤。", [setting]
        )
        assert refs == {"t1": "xuanhuan_lingyuan.technique.lingyuan_quan_first_form"}

    def test_detect_lingyuan_quan_ch150_plain(self) -> None:
        """诊断 B-Ch150：`灵渊拳第一式` 无书名号连写也必须命中."""
        setting = _setting(
            "t1",
            "xuanhuan_lingyuan.technique.lingyuan_quan_first_form",
            "灵渊《灵渊拳》第一式",
        )
        refs = _detect_setting_references(
            "你找到灵渊拳第一式的运行路线，就能激活它。", [setting]
        )
        assert refs == {"t1": "xuanhuan_lingyuan.technique.lingyuan_quan_first_form"}

    def test_detect_guardian_bloodline_particle_boundary(self) -> None:
        """诊断 C1-Ch120：`守门者的血脉` 中 `守门者` 后接 的（语法边界）."""
        setting = _setting("t1", "x.mother_descendant", "守门者后人·母亲血脉")
        refs = _detect_setting_references("记住——守门者的血脉还没有断干净。", [setting])
        assert refs == {"t1": "x.mother_descendant"}


class TestF2ParticleNormalization:
    def test_particle_insertion_match(self) -> None:
        """诊断 A-Ch93：`与守灵交易` ↔ `与守灵的交易` 插字命中."""
        setting = _setting("t1", "x.guardian_hunter_deception", "猎渊者·与守灵交易")
        refs = _detect_setting_references(
            "黑令长老狞笑：'与守灵的交易换来的，专克你们这些守门者'", [setting]
        )
        assert refs == {"t1": "x.guardian_hunter_deception"}

    def test_shared_term_in_content_default_unchanged(self) -> None:
        """共享 `_term_in_content` 默认行为不变（_scanners 消费者零影响）."""
        assert _term_in_content("与守灵交易", "与守灵的交易换来的") is False


class TestF3NameDerivedSuffix:
    def test_hunter_mark_suffix(self) -> None:
        """诊断 A-Ch93：`猎渊者`（name 派生）命中 `猎渊者印记`."""
        setting = _setting("t1", "x.guardian_hunter_deception", "猎渊者·与守灵交易")
        refs = _detect_setting_references("左臂的猎渊者印记在火光中一闪。", [setting])
        assert refs == {"t1": "x.guardian_hunter_deception"}

    def test_shared_term_in_content_boundary_unchanged(self) -> None:
        """共享 `_term_in_content` 的 CJK 后缀拒绝规则不变."""
        assert _term_in_content("猎渊者", "左臂的猎渊者印记在火光中一闪。") is False

    def test_two_char_name_term_not_relaxed(self) -> None:
        """2 字 term 不适用后缀放宽（避免 `灵渊` 类过泛命中）."""
        setting = _setting("t1", "x.y", "灵渊《灵渊拳》第一式")
        refs = _detect_setting_references("灵渊兽从深渊里爬出来。", [setting])
        assert refs == {}


class TestNegativeGuards:
    def test_metaphor_bloodline_not_matched(self) -> None:
        """诊断 C1-Ch119 比喻句不得误刷 mother_descendant（F4 误刷红线）."""
        setting = _setting(
            "t1",
            "x.mother_descendant",
            "守门者后人·母亲血脉",
            "灵渊本源渡入腹中的陆沉，血脉封印本应代代相传",
        )
        refs = _detect_setting_references("血丝像血脉一样在眼球表面游走。", [setting])
        assert refs == {}

    def test_unrelated_content_not_matched(self) -> None:
        setting = _setting(
            "t1",
            "xuanhuan_lingyuan.technique.lingyuan_quan_first_form",
            "灵渊《灵渊拳》第一式",
        )
        refs = _detect_setting_references("他在集市上买了两个馒头。", [setting])
        assert refs == {}

    def test_empty_inputs(self) -> None:
        setting = _setting("t1", "x.y", "灵渊《灵渊拳》第一式")
        assert _detect_setting_references("", [setting]) == {}
        assert _detect_setting_references("正文", []) == {}
