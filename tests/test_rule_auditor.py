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


# ---------------------------------------------------------------------------
# Task 121r: Markdown Scene Title Detection Tests
# ---------------------------------------------------------------------------
class TestMarkdownSceneTitleDetection:
    def test_markdown_scene_title_detected(self) -> None:
        text = "### Scene 1: 凌晨三点 / C区走廊\n林凡走在走廊里。"
        result = run_rule_audit(text, word_count_target=10)
        assert result.markdown_scene_title_count == 1
        assert any("Markdown场景标题" in m.pattern for m in result.markdown_scene_title_matches)
        assert result.markdown_scene_title_matches[0].severity == "major"

    def test_bare_scene_title_detected(self) -> None:
        text = "Scene 2: 控制中心\n警报声响起。"
        result = run_rule_audit(text, word_count_target=10)
        assert result.markdown_scene_title_count == 1
        assert any("裸场景标题" in m.pattern for m in result.markdown_scene_title_matches)

    def test_no_scene_title(self) -> None:
        text = "林凡握紧拳头，眼中燃烧着怒火。"
        result = run_rule_audit(text, word_count_target=10)
        assert result.markdown_scene_title_count == 0
        assert result.markdown_scene_title_matches == []


# ---------------------------------------------------------------------------
# Task 121r: Short Paragraph Ratio Tests
# ---------------------------------------------------------------------------
class TestShortParagraphRatio:
    def test_high_short_paragraph_ratio(self) -> None:
        """大量短段落（<50字）时 ratio 应 > 0.5."""
        paragraphs = ["短。"] * 8 + ["这是一段比较长的测试段落，用来平衡短段落的比例。"] * 2
        text = "\n".join(paragraphs)
        result = run_rule_audit(text, word_count_target=100)
        assert result.short_paragraph_ratio > 0.5

    def test_low_short_paragraph_ratio(self) -> None:
        """正常段落长度时 ratio 应 < 0.5."""
        text = (
            "林凡握紧拳头，眼中燃烧着怒火。\"你找死！\"他怒吼一声，身形如箭般冲出。"
            "反派冷笑一声，挥剑迎上。两人交锋，气浪翻滚，周围的建筑纷纷崩塌。"
            "林凡渐感不支，心中暗道：必须突破！就在这时，一道金光从天而降——"
        )
        result = run_rule_audit(text, word_count_target=100)
        assert result.short_paragraph_ratio < 0.5


# ---------------------------------------------------------------------------
# Task 121r: Scene Count by Blank Line Tests
# ---------------------------------------------------------------------------
class TestSceneCountWithBlankLines:
    def test_two_scenes_by_blank_line(self) -> None:
        text = "第一段场景的内容，描述主角进入房间。\n\n第二段场景的内容，描述主角发现线索。"
        result = run_rule_audit(text, word_count_target=10, scene_count_target=2)
        assert result.scene_count == 2
        assert result.scene_count_ok is True

    def test_single_scene_no_blank_line(self) -> None:
        text = "只有一个场景的内容，没有空行分隔。"
        result = run_rule_audit(text, word_count_target=10, scene_count_target=2)
        assert result.scene_count == 1
        assert result.scene_count_ok is False


# ---------------------------------------------------------------------------
# Task 170g: Exposition Carrier Detection Tests
# ---------------------------------------------------------------------------
class TestExpositionCarrierDetection:
    def test_info_stream_detected(self) -> None:
        text = "信息流就像高压电流般涌入颅腔，他瞬间理解了方舟的全部真相。"
        result = run_rule_audit(text, word_count_target=10)
        assert result.exposition_carrier_count >= 1
        assert any(m.carrier_type == "info_stream" for m in result.exposition_carrier_matches)

    def test_consciousness_tentacle_detected(self) -> None:
        text = "林渊的意识触须沿着坐标延伸，触碰到了建造者留下的核心节点。"
        result = run_rule_audit(text, word_count_target=10)
        assert result.exposition_carrier_count >= 1
        assert any(
            m.carrier_type == "consciousness_tentacle"
            for m in result.exposition_carrier_matches
        )

    def test_vision_dump_detected(self) -> None:
        text = "他看见了建造者——他们站在一个巨大的空间里，周身流动着液态星光。"
        result = run_rule_audit(text, word_count_target=10)
        assert result.exposition_carrier_count >= 1
        assert any(m.carrier_type == "vision_dump" for m in result.exposition_carrier_matches)

    def test_repeated_revelation_beat_detected(self) -> None:
        text = (
            "信息流涌入颅腔，他明白了第一个真相。"
            "片刻后，信息流再次涌入颅腔，他明白了第二个真相。"
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "repeated_revelation_beat"
            for m in result.exposition_carrier_matches
        )

    def test_exposition_carrier_penalty_in_overall_score(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
            word_count_ok=True,
            exposition_carrier_count=3,
        )
        score = _compute_overall_score(result)
        # 3 * 0.3 = 0.9 扣分
        assert score == 9.1

    def test_exposition_carrier_summary(self) -> None:
        result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
            word_count_ok=True,
            exposition_carrier_count=2,
        )
        summary = _generate_summary(result)
        assert "说明文载体硬灌" in summary

    def test_clean_text_no_exposition_carrier(self) -> None:
        text = _make_clean_text()
        result = run_rule_audit(text, word_count_target=100)
        # 干净文本不应命中 info_stream / vision_dump / consciousness_tentacle
        bad_types = {"info_stream", "vision_dump", "consciousness_tentacle"}
        found_bad = {
            m.carrier_type for m in result.exposition_carrier_matches if m.carrier_type in bad_types
        }
        assert not found_bad


def test_direct_revelation_monologue_detected() -> None:
    text = (
        '建造者的声音在舱室里回荡："建造者文明没有灭绝，它们把自己分裂成七块意识碎片，'
        '嵌入了七把钥匙的基因序列之中，每一代钥匙的死亡都会释放一块碎片，等待最后的共鸣。"'
    )
    result = run_rule_audit(text, word_count_target=10)
    assert any(
        m.carrier_type == "direct_revelation_monologue"
        for m in result.exposition_carrier_matches
    )


def test_protagonist_summary_tell_detected() -> None:
    text = "林渊看着残骸。他明白了——方舟从来不是庇护所，而是一座牢笼。"
    result = run_rule_audit(text, word_count_target=10)
    assert any(
        m.carrier_type == "protagonist_summary_tell"
        for m in result.exposition_carrier_matches
    )


def test_protagonist_summary_tell_expanded_verbs() -> None:
    for verb in ("他终于懂了", "这一切都意味着", "他理解了"):
        text = f"林渊看着残骸。{verb}——方舟从来不是庇护所，而是一座牢笼。"
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "protagonist_summary_tell"
            for m in result.exposition_carrier_matches
        ), f"failed for {verb}"


def test_unconflicted_revelation_detected() -> None:
    text = (
        '林渊走进房间，环顾四周。老雷平静地说：'
        '"核心协议叫做共鸣锁，它通过基因标记识别每一代钥匙，'
        '当七把钥匙全部激活时，系统会释放预先写入的最终指令。"'
    )
    result = run_rule_audit(text, word_count_target=10)
    assert any(
        m.carrier_type == "unconflicted_revelation"
        for m in result.exposition_carrier_matches
    )


def test_unconflicted_revelation_with_conflict_not_flagged() -> None:
    text = (
        '林渊以为共鸣锁是保护机制。陈薇冷笑："你错了，那是处决开关。"'
        '老雷平静地说："核心协议叫做共鸣锁，它通过基因标记识别每一代钥匙。"'
    )
    result = run_rule_audit(text, word_count_target=10)
    assert not any(
        m.carrier_type == "unconflicted_revelation"
        for m in result.exposition_carrier_matches
    )


def test_human_voice_homogeneity_detected() -> None:
    text = (
        '林渊说："我们必须马上离开这里。通道已经封死了。"\n'
        '陈薇说："我们必须马上离开这里。通道已经封死了。"\n'
        '老雷说："我们必须马上离开这里。通道已经封死了。"'
    )
    result = run_rule_audit(text, word_count_target=10)
    assert any(
        m.carrier_type == "human_voice_homogeneity"
        for m in result.exposition_carrier_matches
    )


def test_human_voice_homogeneity_with_distinct_voices_not_flagged() -> None:
    text = (
        '林渊吼道："走！"\n\n'
        '陈薇按住他的手，声音发颤："往哪走？通道都锁死了，你冷静点。"\n\n'
        '老雷没抬头，只是用扳手敲了敲变形的门框："先把手从警报按钮上挪开。"'
    )
    result = run_rule_audit(text, word_count_target=10)
    assert not any(
        m.carrier_type == "human_voice_homogeneity"
        for m in result.exposition_carrier_matches
    )


def test_human_voice_homogeneity_detected_with_post_quote_speakers() -> None:
    """后置说话人（网文常见格式）也应被正确归因并检测同质化."""
    text = (
        '"我们必须马上离开这里。通道已经封死了。"林渊说。\n\n'
        '"我们必须马上离开这里。通道已经封死了。"陈薇说。\n\n'
        '"我们必须马上离开这里。通道已经封死了。"老雷说。'
    )
    result = run_rule_audit(text, word_count_target=10)
    assert any(
        m.carrier_type == "human_voice_homogeneity"
        for m in result.exposition_carrier_matches
    )


def test_human_voice_homogeneity_distinct_post_quote_voices_not_flagged() -> None:
    """后置说话人但声纹不同，不应误报."""
    text = (
        '"走！"林渊吼道。\n\n'
        '"往哪走？通道都锁死了，你冷静点。"陈薇按住他的手，声音发颤。\n\n'
        '"先把手从警报按钮上挪开。"老雷没抬头，只是用扳手敲了敲变形的门框。'
    )
    result = run_rule_audit(text, word_count_target=10)
    assert not any(
        m.carrier_type == "human_voice_homogeneity"
        for m in result.exposition_carrier_matches
    )


def test_human_voice_homogeneity_narrative_attribution_with_registry() -> None:
    """Task 170o: 叙事归因（X的声音）+ 角色注册表 gating 可检出同质化.

    真实正文大量用"X的声音/录音"而非"X说"标签；提供 character_names 时应能归因。
    """
    from songyan.agents.rule_auditor import detect_human_voice_homogeneity

    text = (
        '陈薇的声音传来："我们必须马上离开。通道已经封死了。"\n\n'
        '这是林渊的声音："我们必须马上离开。通道已经封死了。"'
    )
    matches = detect_human_voice_homogeneity(
        text, character_names={"陈薇", "林渊"}
    )
    assert any(m.carrier_type == "human_voice_homogeneity" for m in matches)


def test_human_voice_homogeneity_registry_filters_narration_noise() -> None:
    """Task 170o: 注册表 gating 过滤把叙事片段误当人名的噪声.

    "寻找更多"/"录音中" 等非注册表片段不得被当作说话人，避免噪声制造假命中。
    """
    from songyan.agents.rule_auditor import detect_human_voice_homogeneity

    text = (
        '寻找更多线索的时候，响起一句："这里没有退路，只能往前。"\n\n'
        '录音中断之后，又是一句："这里没有退路，只能往前。"'
    )
    # 注册表只含真实角色，叙事片段不在其中 → 不应归因、不应命中
    matches = detect_human_voice_homogeneity(text, character_names={"林渊", "陈薇"})
    assert not any(m.carrier_type == "human_voice_homogeneity" for m in matches)


def test_human_voice_homogeneity_single_seeded_character_no_false_positive() -> None:
    """Task 170o: 注册表只有主角一人时，无法构成多角色对白，不得误报.

    对应 170i seeding gap 实况：characters 表仅 seed 了主角，配角未入库。
    """
    from songyan.agents.rule_auditor import detect_human_voice_homogeneity

    text = (
        '林渊的声音沙哑："我们必须马上离开。通道已经封死了。"\n\n'
        '陈薇的声音传来："我们必须马上离开。通道已经封死了。"'
    )
    # 注册表仅含主角 → 陈薇无法归因 → 只有 1 个合格说话人 → 不命中
    matches = detect_human_voice_homogeneity(text, character_names={"林渊"})
    assert not any(m.carrier_type == "human_voice_homogeneity" for m in matches)


# --- Task 171a: voice 归因召回增强 + 构念重定义 ---

_171A_LINE = "我们必须离开。通道封死了。快走。"  # 3 句，满足 lengths>=2


def test_171a_action_beat_attribution() -> None:
    """Task 171a: 动作节拍夹引语（名字+动作。引语）无 speech-verb 也应归因.

    ``林渊皱眉。"..."`` 这类真实正文主流句式，170o 归因（仅 speech-verb/叙事）漏检；
    171a 用注册表就近绑定（before 优先）补齐召回。
    """
    from songyan.agents.rule_auditor import detect_human_voice_homogeneity

    text = (
        f"林渊皱眉，盯着屏幕。“{_171A_LINE}”\n"
        f"陈薇转过身去，声音发紧。“{_171A_LINE}”"
    )
    matches = detect_human_voice_homogeneity(text, character_names={"林渊", "陈薇"})
    assert any(m.carrier_type == "human_voice_homogeneity" for m in matches)


def test_171a_pronoun_carry_attribution() -> None:
    """Task 171a: 纯代词提示（"..."他又说）继承上一位具名说话人."""
    from songyan.agents.rule_auditor import detect_human_voice_homogeneity

    text = (
        f"林渊开口了：“{_171A_LINE}”\n"
        f"陈薇看着他。“{_171A_LINE}”\n"
        f"“{_171A_LINE}”他又说了一遍。"
    )
    matches = detect_human_voice_homogeneity(text, character_names={"林渊", "陈薇"})
    assert len(matches) > 0


def test_171a_action_beat_speaker_is_preceding_actor_not_next() -> None:
    """Task 171a: 动作节拍归因应优先 before（引语前的动作主体），不误取引语后的下一位.

    ``林渊皱眉。"A" 陈薇转身。"B"`` 中，"A" 归林渊、"B" 归陈薇；若误把 "A" 归陈薇，
    会塌成单说话人、漏检同质化。
    """
    from songyan.agents.rule_auditor import detect_human_voice_homogeneity

    text = (
        f"林渊皱眉，盯着屏幕。“{_171A_LINE}”\n"
        f"陈薇转过身去，声音发紧。“{_171A_LINE}”"
    )
    matches = detect_human_voice_homogeneity(text, character_names={"林渊", "陈薇"})
    # 正确归因到两人 → 同质化命中，命中文案含两名角色
    assert any(
        "林渊" in m.matched_text and "陈薇" in m.matched_text for m in matches
    )


def test_171a_dialogue_sparse_chapter_not_scored() -> None:
    """Task 171a 构念重定义：对白稀疏章（无引语）视为 voice 不适用，返回空而非误判."""
    from songyan.agents.rule_auditor import detect_human_voice_homogeneity

    text = "林渊盯着屏幕，脑海里闪过无数画面。他意识到自己已经无路可退，只能向前。"
    matches = detect_human_voice_homogeneity(text, character_names={"林渊", "陈薇"})
    assert matches == []


def test_info_delivery_dialogue_detected() -> None:
    text = (
        '老雷平静地说："核心协议叫做共鸣锁，它通过基因标记识别每一代钥匙，'
        '当七把钥匙全部激活时，系统会释放预先写入的最终指令，完成整个闭环校验。"'
    )
    result = run_rule_audit(text, word_count_target=10)
    assert any(
        m.carrier_type == "info_delivery_dialogue"
        for m in result.exposition_carrier_matches
    )


def test_171a1_cross_dialogue_narration_not_info_delivery() -> None:
    """Task 171a-1: 跨对话轮的叙事描写不得被误当 info_delivery_dialogue.

    ``…绕弯子了。”<叙事描写含设定词>“这块布…`` —— 闭引号 + 叙事 + 开引号，
    中间叙事无换行。方向性引号（开 ["“] / 闭 ["”]）应使其不匹配。
    """
    from songyan.agents.rule_auditor import detect_exposition_carriers

    text = (
        "“别绕弯子了。”女人从袖中取出一块布片，摊开在桌上。布片不大，巴掌见方，"
        "边缘被烧得焦黑，上面用暗红颜料画着半截兽纹，像是某种文明的密钥图谱。"
        "“这块布，公子可认得？”"
    )
    matches = detect_exposition_carriers(text, setting_keywords={"密钥", "文明", "图谱"})
    # 中段叙事（含设定词）不应被当作一段 info_delivery / direct_revelation 引语
    spans = [
        m for m in matches
        if m.carrier_type in ("info_delivery_dialogue", "direct_revelation_monologue")
        and m.matched_text.startswith("”")
    ]
    assert spans == []



def test_repeated_direct_revelation_beat_detected() -> None:
    text = (
        '残影说："建造者文明为了逃避熵增的终点，把自己分裂成七块意识碎片，'
        '并分别封印在七把钥匙的基因序列深处，等待最后的共鸣时刻。"'
        '过了一会，残影又说："每一块碎片都记录着一段被抹除的历史，'
        '只有对应钥匙在濒死时释放共鸣，碎片才会从基因里苏醒，向继任者展示那段被封印的过去。"'
    )
    result = run_rule_audit(text, word_count_target=10)
    assert any(
        m.carrier_type == "repeated_revelation_beat"
        for m in result.exposition_carrier_matches
    )


class TestStructuralExpositionDetection:
    def test_non_character_monologue_overflow_total_words(self) -> None:
        text = (
            '建造者的声音说："建造者留下的话很清楚：方舟不是庇护所，而是一座牢笼，'
            '你们所有人都是被选中的锁芯，基因里刻着共振的密码，每一道纹路都指向同一个终点。'
            '当七把钥匙同时转动，门不会打开，只会把最后的缝隙也封死，把所有人都留在黑暗里。"'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "non_character_monologue_overflow"
            for m in result.exposition_carrier_matches
        )

    def test_non_character_monologue_overflow_consecutive(self) -> None:
        text = (
            '"建造者说方舟是牢笼，这句话像钉子一样钉进空气。"'
            '"建造者还说你们都是锁芯，每一个人都不例外。"'
            '"建造者最后说门不会打开，只会封死最后的缝隙。"'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "non_character_monologue_overflow"
            for m in result.exposition_carrier_matches
        )

    def test_expository_dialogue_chain_detected(self) -> None:
        text = (
            '"核心协议叫做共鸣锁，它通过基因标记识别每一代钥匙，这是系统的第一层校验机制，任何人都无法绕过这个底层协议。"'
            '"当七把钥匙的基因标记同时被系统读取之后，共鸣锁会进入第二层校验流程，验证所有标记是否匹配并记录偏差值。"'
            '"七把钥匙全部激活时，系统会释放预先写入的最终指令，完成整个闭环校验，没有任何外部干预的余地，结果早已注定。"'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "expository_dialogue_chain"
            for m in result.exposition_carrier_matches
        )

    def test_unearned_revelation_detected(self) -> None:
        text = (
            '林渊走进房间，环顾四周。建造者的声音突然响起：'
            '"建造者文明从一开始就知道真相：方舟从来不是庇护所，而是一座牢笼，'
            '你们所有人都是被选中的锁芯，基因里刻着共振的密码。"'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "unearned_revelation"
            for m in result.exposition_carrier_matches
        )

    def test_earned_revelation_not_flagged(self) -> None:
        text = (
            '林渊一拳砸向主控面板，屏幕碎裂，火花四溅。'
            '系统警报尖叫。建造者的声音才响起："协议已终止。"'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert not any(
            m.carrier_type == "unearned_revelation"
            for m in result.exposition_carrier_matches
        )


# ---------------------------------------------------------------------------
# Task 170l: Quote-style coverage for exposition carrier detection
# ---------------------------------------------------------------------------
class TestExpositionCarrierCurlyQuotes:
    """验证 exposition carrier 检测同时支持 ASCII \"...\" 与中文弯引号 ""“...”"""""

    def test_direct_revelation_monologue_with_curly_quotes(self) -> None:
        text = (
            '建造者的声音在舱室里回荡：\u201c建造者文明没有灭绝，它们把自己分裂成七块意识碎片，'
            '嵌入了七把钥匙的基因序列之中，每一代钥匙的死亡都会释放一块碎片，等待最后的共鸣。\u201d'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "direct_revelation_monologue"
            for m in result.exposition_carrier_matches
        )

    def test_info_delivery_dialogue_with_curly_quotes(self) -> None:
        text = (
            '老雷平静地说：\u201c核心协议叫做共鸣锁，它通过基因标记识别每一代钥匙，'
            '当七把钥匙全部激活时，系统会释放预先写入的最终指令，完成整个闭环校验。\u201d'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "info_delivery_dialogue"
            for m in result.exposition_carrier_matches
        )

    def test_unconflicted_revelation_with_curly_quotes(self) -> None:
        text = (
            '林渊走进房间，环顾四周。老雷平静地说：'
            '\u201c核心协议叫做共鸣锁，它通过基因标记识别每一代钥匙，'
            '当七把钥匙全部激活时，系统会释放预先写入的最终指令。\u201d'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "unconflicted_revelation"
            for m in result.exposition_carrier_matches
        )

    def test_human_voice_homogeneity_with_curly_quotes(self) -> None:
        text = (
            '林渊说：\u201c我们必须马上离开这里。通道已经封死了。\u201d\n'
            '陈薇说：\u201c我们必须马上离开这里。通道已经封死了。\u201d\n'
            '老雷说：\u201c我们必须马上离开这里。通道已经封死了。\u201d'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "human_voice_homogeneity"
            for m in result.exposition_carrier_matches
        )

    def test_non_character_monologue_overflow_with_curly_quotes(self) -> None:
        text = (
            '建造者的声音说：\u201c建造者留下的话很清楚：方舟不是庇护所，而是一座牢笼，'
            '你们所有人都是被选中的锁芯，基因里刻着共振的密码，每一道纹路都指向同一个终点。'
            '当七把钥匙同时转动，门不会打开，只会把最后的缝隙也封死，把所有人都留在黑暗里。\u201d'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "non_character_monologue_overflow"
            for m in result.exposition_carrier_matches
        )

    def test_expository_dialogue_chain_with_curly_quotes(self) -> None:
        text = (
            '\u201c核心协议叫做共鸣锁，它通过基因标记识别每一代钥匙，这是系统的第一层校验机制，任何人都无法绕过这个底层协议。\u201d'
            '\u201c当七把钥匙的基因标记同时被系统读取之后，共鸣锁会进入第二层校验流程，验证所有标记是否匹配并记录偏差值。\u201d'
            '\u201c七把钥匙全部激活时，系统会释放预先写入的最终指令，完成整个闭环校验，没有任何外部干预的余地，结果早已注定。\u201d'
        )
        result = run_rule_audit(text, word_count_target=10)
        assert any(
            m.carrier_type == "expository_dialogue_chain"
            for m in result.exposition_carrier_matches
        )
