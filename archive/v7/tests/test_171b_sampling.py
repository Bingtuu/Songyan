"""Tests for Task 171b dialogue-density sampling utility."""

from __future__ import annotations

from songyan.utils.sampling import (
    classify_dialogue_layer,
    dialogue_density,
    is_voice_applicable,
)


class TestDialogueDensity:
    def test_zero_chars_no_crash(self) -> None:
        assert dialogue_density(0, 5) == 0.0

    def test_negative_chars_no_crash(self) -> None:
        assert dialogue_density(-10, 5) == 0.0

    def test_basic_ratio(self) -> None:
        # 20 quotes / 2000 chars = 10 per 1k
        assert dialogue_density(2000, 20) == 10.0

    def test_no_quotes(self) -> None:
        assert dialogue_density(3000, 0) == 0.0


class TestClassifyDialogueLayer:
    def test_sparse_below_threshold(self) -> None:
        # 7 quotes / 4769 chars ≈ 1.47 per 1k -> sparse (170i ch5 real value)
        layer, density = classify_dialogue_layer(4769, 7)
        assert layer == "sparse"
        assert density < 3.0

    def test_mixed_middle_band(self) -> None:
        # 18 quotes / 3898 chars ≈ 4.62 per 1k -> mixed (170p scifi ch4 real value)
        layer, density = classify_dialogue_layer(3898, 18)
        assert layer == "mixed"
        assert 3.0 <= density < 8.0

    def test_dialogue_high_density(self) -> None:
        # 57 quotes / 3370 chars ≈ 16.9 per 1k -> dialogue (170p scifi ch1 real value)
        layer, density = classify_dialogue_layer(3370, 57)
        assert layer == "dialogue"
        assert density >= 8.0

    def test_boundary_sparse_to_mixed(self) -> None:
        # exactly 3.0 -> mixed (sparse is strictly < 3.0)
        layer, _ = classify_dialogue_layer(1000, 3)
        assert layer == "mixed"

    def test_boundary_mixed_to_dialogue(self) -> None:
        # exactly 8.0 -> dialogue (dialogue_min inclusive)
        layer, _ = classify_dialogue_layer(1000, 8)
        assert layer == "dialogue"

    def test_custom_thresholds(self) -> None:
        layer, _ = classify_dialogue_layer(
            1000, 5, sparse_max=6.0, dialogue_min=10.0
        )
        assert layer == "sparse"


class TestIsVoiceApplicable:
    def test_sparse_not_applicable(self) -> None:
        assert is_voice_applicable("sparse") is False

    def test_mixed_applicable(self) -> None:
        assert is_voice_applicable("mixed") is True

    def test_dialogue_applicable(self) -> None:
        assert is_voice_applicable("dialogue") is True

    def test_matches_metric_gate_semantics(self) -> None:
        """稀疏章即使通过量具章级门 (quote>=2)，voice 采样也应剔除。"""
        # 170i ch18: 7 quotes / 3364 chars ≈ 2.08 -> sparse, but quote_count >= 2
        layer, _ = classify_dialogue_layer(3364, 7)
        assert layer == "sparse"
        assert is_voice_applicable(layer) is False
