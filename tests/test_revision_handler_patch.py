"""Tests for RevisionHandler patch matching improvements (Task 025)."""

from __future__ import annotations

from songyan.agents.revision_handler import _apply_patches, _find_text_span
from songyan.models import Patch


class TestFindTextSpan:
    def test_exact_match(self) -> None:
        text = "这是一段测试文本，用于验证 patch 匹配功能。"
        target = "patch 匹配功能"
        span = _find_text_span(text, target)
        assert span is not None
        start, end = span
        assert text[start:end] == target

    def test_fuzzy_match_90_percent(self) -> None:
        """90% 相似度应该能找到（差异 1 个字符 / 20 字符 = 5%）."""
        text = "陆沉攥紧了袖口。\n\n第二个，第三个，第四个。测灵石依次亮起灰白、淡黄、浅蓝的光"
        # LLM 返回的 original_text 可能有微小差异
        target = "陆沉攥紧了袖口。\n\n第二个，第三个，第四个。测灵石依次亮起灰白、淡黄、浅篮的光"
        span = _find_text_span(text, target, fuzzy_threshold=0.85)
        assert span is not None, "90% 相似文本应通过 fuzzy match 找到"

    def test_fuzzy_match_70_percent_should_fail(self) -> None:
        """70% 相似度不应找到（低于 0.85 阈值）."""
        text = "这是一段完全不同的文本内容，没有任何相似之处。"
        target = "patch 匹配功能测试用例"
        span = _find_text_span(text, target, fuzzy_threshold=0.85)
        assert span is None, "70% 相似文本不应找到"

    def test_not_found_empty_target(self) -> None:
        span = _find_text_span("some text", "")
        assert span is None

    def test_multiple_occurrences_last_one(self) -> None:
        """rfind 语义：返回最后一个匹配."""
        text = "abc def abc ghi"
        span = _find_text_span(text, "abc")
        assert span == (8, 11)  # 第二个 "abc" 在索引 8


class TestApplyPatchesFuzzy:
    def test_apply_patch_with_fuzzy_match(self) -> None:
        """patch 的 original_text 与 content 有微小差异时仍能应用."""
        content = (
            "开头\n\n陆沉攥紧了袖口。\n\n"
            "第二个，第三个，第四个。测灵石依次亮起灰白、淡黄、浅蓝的光\n\n"
            "结尾"
        )
        patch = Patch(
            issue_id="i1",
            original_text="陆沉攥紧了袖口。\n\n第二个，第三个，第四个。测灵石依次亮起灰白、淡黄、浅篮的光",
            revised_text="陆沉攥紧了袖口。\n\n第二个，第三个，第四个。测灵石依次亮起灰白、淡黄、浅蓝的光，但没有一道能撑过三息",
            location="第2段",
        )
        result, applied = _apply_patches(content, [patch])
        assert len(applied) == 1
        assert "但没有一道能撑过三息" in result

    def test_apply_multiple_patches_from_back(self) -> None:
        """多个 patch 从后往前应用，避免位置偏移."""
        content = "AAA BBB CCC DDD"
        patches = [
            Patch(issue_id="i1", original_text="BBB", revised_text="XXX", location=""),
            Patch(issue_id="i2", original_text="DDD", revised_text="YYY", location=""),
        ]
        result, applied = _apply_patches(content, patches)
        assert len(applied) == 2
        assert result == "AAA XXX CCC YYY"

    def test_patch_collision_skipped(self) -> None:
        """重叠 patch 应跳过."""
        content = "AAA BBB CCC"
        patches = [
            Patch(issue_id="i1", original_text="AAA BBB", revised_text="XXX", location=""),
            Patch(issue_id="i2", original_text="BBB CCC", revised_text="YYY", location=""),
        ]
        result, applied = _apply_patches(content, patches)
        # BBB CCC 先处理（靠后），然后 AAA BBB 重叠应跳过
        assert len(applied) == 1
        assert "YYY" in result
