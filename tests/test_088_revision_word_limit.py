"""Tests for Task 093: RevisionHandler word count hard limit (1.20x / 0.80x)."""

from __future__ import annotations

from songyan.agents.revision_handler._segmented_revision import (
    _enforce_revision_word_count,
)
from songyan.utils.word_count import count_chinese_words


class TestEnforceRevisionWordCount:
    """验证 RevisionHandler 字数硬约束：上限 1.20x，下限 0.80x (Task 093 收紧)."""

    def test_normal_range_no_adjustment(self) -> None:
        """revision 在 [0.80x, 1.20x] 范围内 → 不变."""
        content = "正文" * 1500  # 3000 字（"正文"=2字 × 1500）
        scenes = [{"content": content}]
        original = content
        target = 3000

        result_content, result_scenes, wc, adjusted, reason = (
            _enforce_revision_word_count(content, scenes, original, target)
        )

        assert adjusted is False
        assert reason == "revision_accepted"
        assert result_content == content

    def test_upper_limit_boundary(self) -> None:
        """刚好 1.20x → 不截断."""
        target = 3000
        upper_chars = int(target * 1.20) // 2  # 3600 / 2 = 1800
        content = "正文" * upper_chars  # 刚好 3600 字
        scenes = [{"content": content}]

        _, _, _, adjusted, reason = _enforce_revision_word_count(
            content, scenes, content, target
        )

        assert adjusted is False
        assert reason == "revision_accepted"

    def test_above_upper_gets_truncated(self) -> None:
        """> 1.20x → 二次截断."""
        target = 3000
        # 构造 4 个等长 scene，总计 ~4000 字（> 1.20x = 3600）
        # 截断到第 3 个 scene 前 ≈ 3000 字，保留率 0.75 < 0.85
        # Task 100a: 保留率 < 0.85 时回退到原始 draft
        content = (
            "### Scene 1\n" + "正文" * 500 + "\n\n"
            "### Scene 2\n" + "正文" * 500 + "\n\n"
            "### Scene 3\n" + "正文" * 500 + "\n\n"
            "### Scene 4\n" + "正文" * 500
        )
        scenes = [
            {"content": "### Scene 1\n" + "正文" * 500},
            {"content": "### Scene 2\n" + "正文" * 500},
            {"content": "### Scene 3\n" + "正文" * 500},
            {"content": "### Scene 4\n" + "正文" * 500},
        ]
        original = content

        result_content, result_scenes, wc, adjusted, reason = (
            _enforce_revision_word_count(content, scenes, original, target)
        )

        assert adjusted is True
        assert "revision_truncated_preservation_too_low_fallback" in reason
        assert result_content == original  # 回退到原始内容

    def test_below_lower_severe_underflow_needs_human_review(self) -> None:
        """< 0.80x target 且 < 0.85x original → 标记 needs_human_review，不回退 (Task 100a)."""
        target = 3000
        original = "正文" * 1500  # 3000 字
        revision = "正文" * 500   # 1000 字 < 0.80x = 2400，且 < 2550 (0.85x original)
        scenes = [{"content": revision}]

        result_content, result_scenes, wc, adjusted, reason = (
            _enforce_revision_word_count(revision, scenes, original, target)
        )

        assert adjusted is True
        assert reason == "revision_underflow_needs_human_review"
        assert result_content == revision  # 保持 revision 内容，让 quality gate 处理
        assert wc == count_chinese_words(revision)

    def test_below_lower_moderate_fallback(self) -> None:
        """< 0.80x target 但 >= 0.85x original → 回退到原始 draft."""
        target = 3000
        # original = 2500 字 (>= lower=2400, 0.85x=2125)
        # revision = 2300 字 (< lower=2400, 但 >= 0.85x original=2125)
        original = "正文" * 1250
        revision = "正文" * 1150
        scenes = [{"content": revision}]

        result_content, result_scenes, wc, adjusted, reason = (
            _enforce_revision_word_count(revision, scenes, original, target)
        )

        assert adjusted is True
        assert reason == "revision_underflow_fallback"
        assert result_content == original
        assert wc == count_chinese_words(original)

    def test_lower_limit_boundary(self) -> None:
        """刚好 0.80x → 不回退."""
        target = 3000
        lower_chars = int(target * 0.80) // 2  # 2400 / 2 = 1200
        content = "正文" * lower_chars  # 刚好 2400 字
        scenes = [{"content": content}]

        _, _, _, adjusted, reason = _enforce_revision_word_count(
            content, scenes, content, target
        )

        assert adjusted is False
        assert reason == "revision_accepted"

    def test_no_scene_headers_hard_truncated(self) -> None:
        """Writer 1.1.0 使用空行分场景（无 ### Scene 头）时，revision 超标应硬截断兜底."""
        target = 3000
        upper = int(target * 1.20)
        # 模拟无 scene header 的正文：连续段落，总计 4000 字
        paragraphs = ["正文" * 100 for _ in range(20)]
        content = "\n\n".join(paragraphs)
        scenes = [{"content": content}]
        original = "正文" * 1500

        result_content, result_scenes, wc, adjusted, reason = (
            _enforce_revision_word_count(content, scenes, original, target)
        )

        assert adjusted is True
        assert reason == "revision_hard_truncated_at_boundary"
        assert wc <= upper
        assert count_chinese_words(result_content) == wc

    def test_short_original_keeps_truncated_expansion(self) -> None:
        """短原文扩写达标时，不因截断保留率低回退到短章."""
        target = 3000
        lower = int(target * 0.80)
        upper = int(target * 1.20)
        original = "正文" * 900  # 1800 字，低于 lower=2400
        revision = "\n\n".join(["正文" * 250 for _ in range(10)])  # 5000 字，超上限
        scenes = [{"content": revision}]

        result_content, _result_scenes, wc, adjusted, reason = (
            _enforce_revision_word_count(revision, scenes, original, target)
        )

        assert adjusted is True
        assert reason == "revision_truncated_short_original_expansion_kept"
        assert result_content != original
        assert lower <= wc <= upper
        assert count_chinese_words(result_content) == wc

    def test_ch1_3_calibration_upper_is_3300(self) -> None:
        """前三章校准窗口截断上限使用 3300，而不是通用 1.20x."""
        target = 3000
        original = "正文" * 1500
        revision = "\n\n".join(["正文" * 190 for _ in range(10)])  # 3800 字
        scenes = [{"content": revision}]

        result_content, _result_scenes, wc, adjusted, reason = (
            _enforce_revision_word_count(
                revision,
                scenes,
                original,
                target,
                min_preserve_ratio=0.5,
                chapter_number=1,
            )
        )

        assert adjusted is True
        assert reason in {
            "revision_hard_truncated_at_boundary",
            "revision_truncated_preservation_too_low_fallback",
        }
        assert wc <= 3300
        assert count_chinese_words(result_content) == wc

    def test_short_original_expansion_keeps_calibration_truncated_result(self) -> None:
        """短原文扩写保留时也不能超过前三章 3300 上限."""
        target = 3000
        original = "正文" * 1182  # 2364 字，低于 calibration lower=2700
        revision = "\n\n".join(["正文" * 245 for _ in range(10)])  # 4900 字
        scenes = [{"content": revision}]

        result_content, _result_scenes, wc, adjusted, reason = (
            _enforce_revision_word_count(
                revision,
                scenes,
                original,
                target,
                chapter_number=3,
            )
        )

        assert adjusted is True
        assert reason == "revision_truncated_short_original_expansion_kept"
        assert result_content != original
        assert 2700 <= wc <= 3300
        assert count_chinese_words(result_content) == wc

    def test_scene_truncation_result_is_clamped_to_calibration_upper(self) -> None:
        """scene 边界截断后仍超过 3300 时，继续硬截断到校准上限."""
        target = 3000
        original = "正" * 1000
        revision = "\n\n".join(
            f"### Scene {idx}\n" + ("正" * 1150)
            for idx in range(1, 5)
        )
        scenes = [{"content": revision}]

        result_content, _result_scenes, wc, adjusted, reason = (
            _enforce_revision_word_count(
                revision,
                scenes,
                original,
                target,
                min_preserve_ratio=0.5,
                chapter_number=1,
            )
        )

        assert adjusted is True
        assert "calibration_hard_truncated" in reason
        assert wc <= 3300
        assert count_chinese_words(result_content) == wc
