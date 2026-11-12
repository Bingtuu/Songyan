"""task 245 P1: 拒写/占位判定纯函数（字数兜底 <100 + 短文本硬信号）。

实证样本来自 2026-11-11 真实模型冒烟（`.tmp/smoke-m4-20261111/notes.md`
发现 3/4）：拒写产物 46–77 字；真实正文 ≥1337 字；章目标 3000 字。
"""

from __future__ import annotations

from songyan.services.variant_quality import classify_variant_draft

# 46 字含蓄拒写（冒烟项目 A 槽3 实证形态）
_REFUSAL_46 = "事实圣经缺少必要信息，写手无法完成本章草稿的生成工作。"
# 61 字空圣经拒写（冒烟发现 3 槽1 实证形态）
_REFUSAL_61 = "本章 canon 圣经为空，写手拒绝生成占位内容，请确认事实集后再试。"
# 77 字占位文本（冒烟发现 3 槽2 实证形态）
_PLACEHOLDER_77 = "草稿槽位 2 —— 待填充。请在 confirm 事实后重新生成本章内容。"
# ≥100 字真实正文形态（真实章节的缩比样本）
_REAL_DRAFT = (
    "夜色压向南站站台，陈屿攥紧末班铜牌的边角，指节泛白。"
    "末班车还有七分钟进站，广播里的女声被雨切得断断续续。"
    "他想起白天在档案馆看到的那页值班表，编号和铜牌背面一致。"
    "雨顺着顶棚接缝滴落，在地面敲出一串断续的记号。"
    "陈屿把铜牌翻过来，背面的刻痕比记忆里深了一分。"
)


class TestEmpty:
    def test_none_is_empty(self) -> None:
        assert classify_variant_draft(None) == "empty"

    def test_blank_is_empty(self) -> None:
        assert classify_variant_draft("   \n\t ") == "empty"


class TestLengthFloor:
    def test_refusal_46_chars_fails(self) -> None:
        assert len(_REFUSAL_46) < 100
        # 含「无法完成」关键词 → 报关键词原因（比 too_short 更 informative）
        assert classify_variant_draft(_REFUSAL_46) == "refusal_keyword"

    def test_refusal_61_chars_fails(self) -> None:
        assert len(_REFUSAL_61) < 100
        assert classify_variant_draft(_REFUSAL_61) == "too_short"

    def test_placeholder_77_chars_fails(self) -> None:
        assert len(_PLACEHOLDER_77) < 100
        assert classify_variant_draft(_PLACEHOLDER_77) == "too_short"

    def test_99_chars_fails(self) -> None:
        text = "短。" * 49 + "短"  # 99 字
        assert len(text) == 99
        assert classify_variant_draft(text) == "too_short"

    def test_100_chars_passes(self) -> None:
        text = "正。" * 50  # 100 字
        assert len(text) == 100
        assert classify_variant_draft(text) is None

    def test_real_draft_passes(self) -> None:
        assert len(_REAL_DRAFT) >= 100
        assert classify_variant_draft(_REAL_DRAFT) is None


class TestHardSignalsShortText:
    def test_empty_echo_fullwidth_fails(self) -> None:
        assert classify_variant_draft("（空）") == "empty_echo"

    def test_empty_echo_halfwidth_fails(self) -> None:
        assert classify_variant_draft("(空)") == "empty_echo"

    def test_keyword_refusal_short_text_fails(self) -> None:
        text = "无法完成本章草稿生成，因为事实集内容不足。" + "补充材料不足，暂时搁置。" * 7
        assert 100 <= len(text) <= 500
        assert classify_variant_draft(text) == "refusal_keyword"

    def test_keyword_refusal_english_fails(self) -> None:
        text = "I cannot fulfill this request because the canon is empty. " + "x" * 80
        assert 100 <= len(text) <= 500
        assert classify_variant_draft(text) == "refusal_keyword"


class TestHardSignalGuard:
    def test_keyword_inside_long_prose_passes(self) -> None:
        """防误伤：长正文里人物台词含「无法完成」不得被判失败。"""
        text = _REAL_DRAFT + "他无法完成当年的约定。" + "雨还在下。" * 80
        assert len(text) > 500
        assert classify_variant_draft(text) is None
