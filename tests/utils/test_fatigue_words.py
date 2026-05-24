"""Tests for fatigue-word detection."""

from __future__ import annotations

from songyan.utils.fatigue_words import (
    detect_fatigue_words,
    detect_fatigue_words_with_timing,
)


class TestDetectFatigueWords:
    """Tests for detect_fatigue_words."""

    def test_empty_text(self) -> None:
        result = detect_fatigue_words("", ["冷笑"])
        assert result == []

    def test_no_matches(self) -> None:
        result = detect_fatigue_words("这是一个正常的段落。", ["冷笑", "废物"])
        assert result == []

    def test_single_match(self) -> None:
        result = detect_fatigue_words("他冷笑一声。", ["冷笑"])
        assert len(result) == 1
        assert result[0].word == "冷笑"
        assert result[0].count == 1
        assert len(result[0].locations) == 1

    def test_multiple_matches_same_word(self) -> None:
        text = "他冷笑一声，对方也冷笑了一声。"
        result = detect_fatigue_words(text, ["冷笑"])
        assert len(result) == 1
        assert result[0].word == "冷笑"
        assert result[0].count == 2
        assert len(result[0].locations) == 2

    def test_multi_char_phrase(self) -> None:
        text = "他嘴角勾起一抹弧度，冷冷地看着对方。"
        result = detect_fatigue_words(text, ["嘴角勾起一抹弧度"])
        assert len(result) == 1
        assert result[0].word == "嘴角勾起一抹弧度"
        assert result[0].count == 1

    def test_multiple_words(self) -> None:
        text = "他冷笑一声，废物，跪下求饶吧。"
        words = ["冷笑", "废物", "跪下求饶"]
        result = detect_fatigue_words(text, words)
        assert len(result) == 3
        words_found = {m.word for m in result}
        assert words_found == {"冷笑", "废物", "跪下求饶"}

    def test_sorted_by_count_desc(self) -> None:
        text = "冷笑冷笑冷笑。废物废物。"
        result = detect_fatigue_words(text, ["冷笑", "废物"])
        assert result[0].word == "冷笑"
        assert result[0].count == 3
        assert result[1].word == "废物"
        assert result[1].count == 2

    def test_empty_word_list(self) -> None:
        result = detect_fatigue_words("他冷笑一声。", [])
        assert result == []

    def test_location_format(self) -> None:
        text = "他冷笑一声。"
        result = detect_fatigue_words(text, ["冷笑"])
        assert len(result) == 1
        assert "第" in result[0].locations[0]
        assert "段" in result[0].locations[0]
        assert "句" in result[0].locations[0]

    def test_performance_under_100ms(self) -> None:
        text = "他冷笑一声，废物，跪下求饶吧。" * 100
        words = ["冷笑", "废物", "跪下求饶", "恐怖如斯", "此子不可留"]
        result, elapsed = detect_fatigue_words_with_timing(text, words)
        assert elapsed < 100, f"Fatigue word detection took {elapsed}ms, expected < 100ms"

    def test_xuanhuan_fatigue_words(self) -> None:
        """Test with actual xuanhuan genre fatigue words."""
        from songyan.genres.loader import load_genre_profile

        genre = load_genre_profile("xuanhuan")
        text = (
            "他嘴角勾起一抹弧度，眼中闪过一丝寒芒。\n"
            "废物，跪地求饶吧。\n"
            "此子不可留，桀桀桀。"
        )
        result = detect_fatigue_words(text, genre.fatigue_words)
        assert len(result) >= 3
        words_found = {m.word for m in result}
        assert "嘴角勾起一抹弧度" in words_found
        assert "废物" in words_found
        assert "跪地求饶" in words_found
