"""Tests for AI-tell detection."""

from __future__ import annotations

import pytest

from songyan.utils.ai_tells import detect_ai_tells, detect_ai_tells_with_timing


class TestDetectAiTells:
    """Tests for detect_ai_tells."""

    def test_empty_text(self) -> None:
        result = detect_ai_tells("")
        assert result == []

    def test_no_matches(self) -> None:
        text = "这是一个非常正常的中文段落，没有任何AI腔的痕迹。"
        result = detect_ai_tells(text)
        assert result == []

    def test_detects_mechanical_consciousness(self) -> None:
        text = "他不禁猛然意识到，自己已经被包围了。"
        result = detect_ai_tells(text)
        assert len(result) >= 1
        assert any("不禁" in m.matched_text for m in result)

    def test_detects_eye_flash(self) -> None:
        text = "张三眼中闪过一丝寒芒，冷冷地看着对方。"
        result = detect_ai_tells(text)
        assert len(result) >= 1
        assert any("眼中闪过" in m.matched_text for m in result)

    def test_detects_warm_current(self) -> None:
        text = "一股暖流涌上心头，让他感到无比温暖。"
        result = detect_ai_tells(text)
        assert len(result) >= 1
        assert any("暖流" in m.matched_text for m in result)

    def test_detects_time_freeze(self) -> None:
        text = "在这一刻，仿佛时间静止了。"
        result = detect_ai_tells(text)
        assert len(result) >= 1
        assert any("时间静止" in m.matched_text for m in result)

    def test_detects_deep_heart(self) -> None:
        text = "内心深处涌起一股强烈的不安。"
        result = detect_ai_tells(text)
        assert len(result) >= 1
        assert any("内心深处" in m.matched_text for m in result)

    def test_detects_five_flavors(self) -> None:
        text = "听到这个消息，他心中五味杂陈。"
        result = detect_ai_tells(text)
        assert len(result) >= 1
        assert any("五味杂陈" in m.matched_text for m in result)

    def test_detects_multiple_patterns(self) -> None:
        text = (
            "他不禁猛然意识到危险。\n"
            "眼中闪过一丝寒芒。\n"
            "一股暖流涌上心头。"
        )
        result = detect_ai_tells(text)
        assert len(result) >= 3

    def test_location_format(self) -> None:
        text = "他不禁猛然意识到，自己已经被包围了。"
        result = detect_ai_tells(text)
        assert len(result) >= 1
        assert "第" in result[0].location
        assert "段" in result[0].location
        assert "句" in result[0].location

    def test_performance_under_200ms(self) -> None:
        text = "他不禁猛然意识到危险。眼中闪过一丝寒芒。" * 100
        result, elapsed = detect_ai_tells_with_timing(text)
        assert elapsed < 200, f"AI-tell detection took {elapsed}ms, expected < 200ms"


class TestAiTellPatternsCoverage:
    """Verify that the built-in pattern set covers known AI-tell phrases."""

    KNOWN_PHRASES = [
        "他不禁猛然意识到",
        "她突然意识到情况不对",
        "不知为何，他开始感到不安",
        "眼中闪过一丝寒芒",
        "眸中闪过一抹异色",
        "一股怒火涌上心头",
        "内心深处涌起一股恐惧",
        "心中五味杂陈",
        "某种难以名状的感觉",
        "下意识地后退了一步",
        "仿佛时间静止了一般",
        "一切都变得缓慢起来",
        "一股暖流涌上心头",
        "心中一震",
        "仿佛看到了一幅画面",
        "脑海中浮现出一段记忆",
    ]

    @pytest.mark.parametrize("phrase", KNOWN_PHRASES)
    def test_known_phrase_detected(self, phrase: str) -> None:
        result = detect_ai_tells(phrase)
        assert len(result) >= 1, f"Failed to detect: {phrase}"
