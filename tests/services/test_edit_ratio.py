"""task 253：S5 人改率 edit_ratio 纯函数（tech-m4-followup-s5 §4）。

口径：变更行数（difflib opcodes 的 insert/delete + replace 双侧）/
max(源稿行数, 1)。所有权代理，不是文学分（PRD :200）。
"""

from __future__ import annotations

from songyan.services.human_edit import compute_edit_ratio


class TestIdentical:
    def test_pure_copy_is_zero(self) -> None:
        text = "甲行\n乙行\n丙行\n"
        assert compute_edit_ratio(text, text) == 0.0

    def test_empty_both_zero(self) -> None:
        assert compute_edit_ratio("", "") == 0.0


class TestChanged:
    def test_one_line_changed_in_ten(self) -> None:
        source = "".join(f"第{i}行\n" for i in range(1, 11))
        edited = source.replace("第5行", "第五行改")
        ratio = compute_edit_ratio(source, edited)
        assert 0.05 < ratio < 0.3

    def test_append_only_small_ratio(self) -> None:
        source = "".join(f"第{i}行\n" for i in range(1, 21))
        edited = source + "尾声一行\n"
        ratio = compute_edit_ratio(source, edited)
        assert 0 < ratio <= 0.05 + 1e-9  # 1/21 < 5%

    def test_full_rewrite_one(self) -> None:
        assert compute_edit_ratio("甲\n", "完全不同\n") == 1.0


class TestEdge:
    def test_empty_source_non_empty_edited(self) -> None:
        assert compute_edit_ratio("", "新行\n") == 1.0

    def test_single_line_tweak_is_one(self) -> None:
        """单行源改一字 = 整行重写，ratio 1.0（行级口径固有粒度）。"""
        assert compute_edit_ratio("原句\n", "新句\n") == 1.0
