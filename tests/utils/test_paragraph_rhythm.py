"""Tests for paragraph rhythm analysis."""

from __future__ import annotations

from songyan.utils.paragraph_rhythm import (
    RhythmScore,
    analyze_paragraph_rhythm,
    analyze_paragraph_rhythm_with_timing,
)


class TestAnalyzeParagraphRhythm:
    """Tests for analyze_paragraph_rhythm."""

    def test_empty_text(self) -> None:
        result = analyze_paragraph_rhythm("")
        assert result.score == 0.0
        assert len(result.issues) == 1
        assert "文本为空" in result.issues[0]

    def test_optimal_rhythm(self) -> None:
        """Well-balanced paragraphs should score high."""
        # Build longer paragraphs (~90-110 chars each) to avoid single-sentence classification
        text = (
            "这是一个长度适中的叙述段落，大约包含八九十字左右的叙述内容，"
            "描述了某个场景或事件的发展过程，节奏平稳自然流畅。"
            '\n"这是对话。"他又补充了一句。接着他继续说道："我们走吧。"\n'
            "接下来是另一个叙述段落，同样保持在合适的篇幅范围内，"
            "让读者能够顺畅地阅读下去，不会感到疲劳或断裂不适。"
            '\n"那接下来怎么办？"有人问道。另一个人回答："先休息吧。"\n'
            "第三个叙述段落也同样保持合适的篇幅，"
            "内容充实且节奏稳定，让读者能够沉浸其中。"
            '\n"我也不知道。"另一个人回答，"但总要试试。"\n'
            "最后一个叙述段落收尾，保持与前文一致的篇幅和节奏，"
            "让整章内容显得完整而连贯，没有突兀的断裂感。"
            '\n"那就走吧。"他说道，语气中带着一丝坚定。\n'
        )
        result = analyze_paragraph_rhythm(text)
        assert result.score >= 5.0
        assert result.ultra_long_ratio < 0.10

    def test_too_short_paragraphs(self) -> None:
        """Many very short paragraphs should score low."""
        text = "\n".join(["短。"] * 20)
        result = analyze_paragraph_rhythm(text)
        assert result.single_sentence_ratio > 0.5
        assert result.score < 5.0
        assert any("单句段落" in issue for issue in result.issues)

    def test_too_long_paragraphs(self) -> None:
        """Very long paragraphs should score low."""
        text = "这是一个超级长的段落。" * 50 + "\n"
        text += "这是另一个超级长的段落。" * 50
        result = analyze_paragraph_rhythm(text)
        assert result.ultra_long_ratio > 0.5
        assert result.score < 5.0
        assert any("超长段落" in issue for issue in result.issues)

    def test_no_dialogue(self) -> None:
        """No dialogue should flag as low dialogue ratio."""
        text = "\n".join(["这是一个叙述段落，没有任何对话内容。"] * 10)
        result = analyze_paragraph_rhythm(text)
        assert result.dialogue_ratio == 0.0
        assert any("对话段落" in issue for issue in result.issues)

    def test_too_much_dialogue(self) -> None:
        """Too much dialogue should also flag."""
        text = "\n".join(['"这是对话。"' * 5] * 10)
        result = analyze_paragraph_rhythm(text)
        assert result.dialogue_ratio > 0.4
        assert any("对话段落" in issue for issue in result.issues)

    def test_rhythm_score_model(self) -> None:
        """RhythmScore can be instantiated and serialized."""
        score = RhythmScore(
            average_length=100.0,
            max_length=200,
            min_length=50,
            single_sentence_ratio=0.1,
            ultra_long_ratio=0.05,
            dialogue_ratio=0.3,
            score=8.5,
            issues=[],
        )
        assert score.score == 8.5
        data = score.model_dump()
        assert data["average_length"] == 100.0

    def test_performance_under_30ms(self) -> None:
        text = "这是一个段落。" * 500 + "\n"
        text += "\"这是对话。\"" * 100 + "\n"
        result, elapsed = analyze_paragraph_rhythm_with_timing(text)
        assert elapsed < 30, f"Paragraph rhythm analysis took {elapsed}ms, expected < 30ms"
