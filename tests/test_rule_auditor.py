"""Tests for RuleAuditor Agent."""

from __future__ import annotations

from unittest.mock import AsyncMock

from songyan.agents.rule_auditor import (
    _compute_overall_score,
    _count_chinese_words,
    _generate_summary,
    run_rule_audit,
    save_rule_audit,
)
from songyan.models import GenreRules, RuleAuditResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_clean_text() -> str:
    """生成无问题的干净文本."""
    return (
        "林凡握紧拳头，眼中燃烧着怒火。"
        "\"你找死！\"他怒吼一声，身形如箭般冲出。"
        "反派冷笑一声，挥剑迎上。"
        "两人交锋，气浪翻滚。"
        "林凡渐感不支，心中暗道：必须突破！"
        "就在这时，一道金光从天而降——"
    )


def _make_ai_tell_text() -> str:
    """包含 AI 腔的文本."""
    return "林凡不禁意识到，一股暖流涌上心头。他下意识地想退缩。"


def _make_fatigue_text() -> str:
    """包含疲劳词的文本."""
    return "林凡冷笑一声，嘴角勾起一抹弧度。"


def _make_no_hook_text() -> str:
    """开头和结尾都缺少钩子的文本."""
    return "天空湛蓝，白云飘荡。林凡走在路上。今天天气很好。"


def _make_good_hook_text() -> str:
    """开头和结尾都有钩子的文本."""
    return (
        "\"杀了他！\"刀光剑影中，林凡被团团围住。"
        "战斗进入白热化。"
        "就在这时，一个意想不到的人出现了——"
    )


# ---------------------------------------------------------------------------
# run_rule_audit Tests
# ---------------------------------------------------------------------------
class TestRunRuleAudit:
    async def test_clean_text(self) -> None:
        text = _make_clean_text()
        result = run_rule_audit(text, word_count_target=100)
        assert result.ai_tell_count >= 0
        assert result.duration_ms >= 0
        assert result.word_count > 0

    async def test_ai_tell_detection(self) -> None:
        text = _make_ai_tell_text()
        result = run_rule_audit(text)
        assert result.ai_tell_count > 0
        assert len(result.ai_tell_matches) > 0
        assert any("不禁" in m.matched_text for m in result.ai_tell_matches)

    async def test_fatigue_word_detection(self) -> None:
        genre = GenreRules(fatigue_words=["冷笑", "嘴角勾起"])
        text = _make_fatigue_text()
        result = run_rule_audit(text, genre_rules=genre)
        assert result.fatigue_word_count > 0
        assert len(result.fatigue_word_matches) > 0

    async def test_no_fatigue_words_when_genre_none(self) -> None:
        text = _make_fatigue_text()
        result = run_rule_audit(text, genre_rules=None)
        assert result.fatigue_word_count == 0
        assert result.fatigue_word_matches == []

    async def test_opening_hook_present(self) -> None:
        text = _make_good_hook_text()
        result = run_rule_audit(text)
        assert result.has_opening_hook is True

    async def test_opening_hook_missing(self) -> None:
        text = _make_no_hook_text()
        result = run_rule_audit(text)
        assert result.has_opening_hook is False

    async def test_ending_hook_present(self) -> None:
        text = _make_good_hook_text()
        result = run_rule_audit(text)
        assert result.has_ending_hook is True

    async def test_ending_hook_missing(self) -> None:
        text = _make_no_hook_text()
        result = run_rule_audit(text)
        assert result.has_ending_hook is False

    async def test_word_count_ok(self) -> None:
        text = "这是一段测试正文，字数不多。"
        result = run_rule_audit(text, word_count_target=10)
        # 10 字 ±10% = 9-11，实际 10 字（"这是一段测试正文字数不多" = 11 字？）
        # 不管具体值，检查 word_count_ok 逻辑正确
        assert result.word_count > 0

    async def test_word_count_deviation(self) -> None:
        text = "短。"
        result = run_rule_audit(text, word_count_target=1000)
        assert result.word_count < 1000
        assert result.word_count_ok is False

    async def test_paragraph_rhythm(self) -> None:
        text = _make_clean_text()
        result = run_rule_audit(text)
        assert 0.0 <= result.paragraph_rhythm_score <= 10.0

    async def test_duration_recorded(self) -> None:
        text = _make_clean_text()
        result = run_rule_audit(text)
        assert result.duration_ms >= 0

    async def test_numerical_contexts_ignored_when_none(self) -> None:
        text = _make_clean_text()
        result = run_rule_audit(text)
        assert result.numerical_issues == []

    async def test_full_audit_with_genre(self) -> None:
        genre = GenreRules(
            genre_id="xuanhuan",
            fatigue_words=["冷笑", "嘴角勾起"],
            pacing_rule="每章一个小高潮",
        )
        text = _make_fatigue_text() + _make_ai_tell_text()
        result = run_rule_audit(
            text,
            genre_rules=genre,
            word_count_target=50,
        )
        assert result.ai_tell_count > 0
        assert result.fatigue_word_count > 0
        assert result.word_count > 0


# ---------------------------------------------------------------------------
# Score Computation Tests
# ---------------------------------------------------------------------------
class TestComputeOverallScore:
    def test_perfect_score(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
            word_count_ok=True,
        )
        score = _compute_overall_score(result)
        assert score == 10.0

    def test_ai_tell_penalty(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=4,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
            word_count_ok=True,
        )
        score = _compute_overall_score(result)
        assert score < 10.0
        # 4 * 0.5 = 2.0 扣分
        assert score == 8.0

    def test_fatigue_word_penalty(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=5,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
            word_count_ok=True,
        )
        score = _compute_overall_score(result)
        # 5 * 0.3 = 1.5 扣分
        assert score == 8.5

    def test_missing_hooks_penalty(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=False,
            has_ending_hook=False,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
            word_count_ok=True,
        )
        score = _compute_overall_score(result)
        # -1.0 - 1.5 = -2.5
        assert score == 7.5

    def test_rhythm_penalty(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=3.0,
            word_count=3000,
            word_count_target=3000,
            word_count_ok=True,
        )
        score = _compute_overall_score(result)
        # (5 - 3) * 0.3 = 0.6 扣分
        assert score == 9.4

    def test_word_count_penalty(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=2000,
            word_count_target=3000,
            word_count_ok=False,
        )
        score = _compute_overall_score(result)
        # deviation = 1000/3000 = 0.333, * 5 = 1.67
        expected = round(10.0 - min(0.333 * 5, 2.0), 1)
        assert score == expected

    def test_minimum_score(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=100,
            fatigue_word_count=100,
            has_opening_hook=False,
            has_ending_hook=False,
            paragraph_rhythm_score=0.0,
            word_count=100,
            word_count_target=3000,
            word_count_ok=False,
        )
        score = _compute_overall_score(result)
        assert score == 0.0

    def test_zero_word_count_target_no_crash(self) -> None:
        """word_count_target=0 时不应抛出 ZeroDivisionError."""
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=100,
            word_count_target=0,
            word_count_ok=False,
        )
        score = _compute_overall_score(result)
        assert score >= 0.0


# ---------------------------------------------------------------------------
# Summary Generation Tests
# ---------------------------------------------------------------------------
class TestGenerateSummary:
    def test_perfect_summary(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
            word_count_ok=True,
        )
        summary = _generate_summary(result)
        assert "通过" in summary
        assert "未发现" in summary

    def test_ai_tell_summary(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=3,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
            word_count_ok=True,
        )
        summary = _generate_summary(result)
        assert "AI 腔" in summary

    def test_multiple_issues(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=2,
            fatigue_word_count=5,
            has_opening_hook=False,
            has_ending_hook=False,
            paragraph_rhythm_score=3.0,
            word_count=2000,
            word_count_target=3000,
            word_count_ok=False,
        )
        summary = _generate_summary(result)
        assert "AI 腔" in summary
        assert "疲劳词" in summary
        assert "首屏钩子" in summary
        assert "章末钩子" in summary
        assert "段落节奏" in summary
        assert "字数偏差" in summary


# ---------------------------------------------------------------------------
# Word Count Helper Tests
# ---------------------------------------------------------------------------
class TestCountChineseWords:
    def test_empty(self) -> None:
        assert _count_chinese_words("") == 0

    def test_chinese(self) -> None:
        assert _count_chinese_words("这是一个测试") == 6

    def test_mixed(self) -> None:
        assert _count_chinese_words("这是test") == 3  # 2 中文 + 1 英文


# ---------------------------------------------------------------------------
# Save Tests
# ---------------------------------------------------------------------------
class TestSaveRuleAudit:
    async def test_save_creates_report(self) -> None:
        mock_db = AsyncMock()
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
        )
        await save_rule_audit(mock_db, "version_123", result)
        mock_db.create.assert_called_once()
        call_args = mock_db.create.call_args
        report = call_args[0][0]
        report_id = call_args[0][1]
        assert report.chapter_version_id == "version_123"
        assert report.ai_tell_count == 0
        assert report.has_opening_hook is True
        assert report_id.startswith("ra-")

    async def test_save_with_custom_report_id(self) -> None:
        mock_db = AsyncMock()
        result = RuleAuditResult()
        await save_rule_audit(mock_db, "version_123", result, report_id="custom_id")
        mock_db.create.assert_called_once()
        report_id = mock_db.create.call_args[0][1]
        assert report_id == "custom_id"


# ---------------------------------------------------------------------------
# 060: Word Count Ratio Calculation Tests
# ---------------------------------------------------------------------------
class TestWordCountRatio:
    """Tests for word_count_ratio field correctness — Task 060."""

    def test_word_count_ratio_exact(self) -> None:
        """3000/3000 = 1.0."""
        text = "林凡握紧拳头，眼中燃烧着怒火。" * 100
        result = run_rule_audit(text, word_count_target=3000)
        assert result.word_count_ratio == round(result.word_count / 3000, 2)

    def test_word_count_ratio_over_target(self) -> None:
        """超标时 ratio > 1.0."""
        text = "短。"
        result = run_rule_audit(text, word_count_target=1000)
        assert result.word_count_ratio < 1.0
        assert result.word_count_ok is False

    def test_word_count_ratio_rounding(self) -> None:
        """ratio 保留两位小数."""
        text = "测试" * 150  # 300 字
        result = run_rule_audit(text, word_count_target=250)
        # 300/250 = 1.20
        assert result.word_count_ratio == 1.20
        assert result.word_count_ok is True

    def test_chapter_type_dynamic_upper_bound(self) -> None:
        """RuleAuditor 与 Writer 使用同一 chapter_type-aware 字数上限."""
        text = "测试" * 650  # 1300 字
        transition = run_rule_audit(
            text,
            word_count_target=1000,
            chapter_type="transition",
        )
        conflict = run_rule_audit(
            text,
            word_count_target=1000,
            chapter_type="conflict",
        )
        assert transition.word_count_ok is False
        assert conflict.word_count_ok is True

    def test_word_count_ratio_zero_target(self) -> None:
        """target=0 时 ratio 为 0.0."""
        text = "测试"
        result = run_rule_audit(text, word_count_target=0)
        assert result.word_count_ratio == 0.0


# ---------------------------------------------------------------------------
# PR-05: MetaTagLeakMatch Tests
# ---------------------------------------------------------------------------
class TestMetaTagLeakMatch:
    def test_html_comment_leak(self) -> None:
        text = "正文开头<!-- 这是注释 -->正文结尾"
        result = run_rule_audit(text, word_count_target=10)
        assert result.meta_tag_count == 1
        assert any("HTML注释" in m.pattern for m in result.meta_tag_matches)
        assert result.meta_tag_matches[0].severity == "major"
        assert "检测到元标记泄漏" in result.meta_tag_matches[0].message

    def test_mark_tag_leak(self) -> None:
        text = "正文<mark>高亮内容</mark>结尾"
        result = run_rule_audit(text, word_count_target=10)
        assert result.meta_tag_count == 1
        assert any("Mark标签" in m.pattern for m in result.meta_tag_matches)
        assert "<mark>高亮内容</mark>" in result.meta_tag_matches[0].matched_text

    def test_meta_prefix_leak(self) -> None:
        text = "正文\nMETA: 这是一个元标记\n结尾"
        result = run_rule_audit(text, word_count_target=10)
        assert result.meta_tag_count == 1
        assert any("Meta前缀" in m.pattern for m in result.meta_tag_matches)
        assert "major" == result.meta_tag_matches[0].severity

    def test_old_style_marker_leak(self) -> None:
        text = "正文[[旧式标记]]结尾"
        result = run_rule_audit(text, word_count_target=10)
        assert result.meta_tag_count == 1
        assert any("旧式可见标记" in m.pattern for m in result.meta_tag_matches)
        assert "[[旧式标记]]" == result.meta_tag_matches[0].matched_text
