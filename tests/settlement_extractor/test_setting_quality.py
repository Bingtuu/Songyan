"""Tests for setting quality control — Task 110b."""

from __future__ import annotations

from songyan.agents.settlement_extractor._setting_quality import (
    _generate_fallback_key,
    _is_valid_setting_key,
    _normalize_key_segments,
    _normalize_setting_key,
)


class TestIsValidSettingKey:
    def test_valid_three_part_key(self) -> None:
        assert _is_valid_setting_key("gaia_ring.protocol.zero_silence") is True

    def test_valid_with_numbers(self) -> None:
        assert _is_valid_setting_key("sector_7.engine.mk2") is True

    def test_invalid_four_part_key(self) -> None:
        assert _is_valid_setting_key("anomaly_x.communication.antenna.construction") is False

    def test_invalid_two_part_key(self) -> None:
        assert _is_valid_setting_key("dust_mothership.permission") is False

    def test_invalid_empty(self) -> None:
        assert _is_valid_setting_key("") is False

    def test_invalid_uppercase(self) -> None:
        assert _is_valid_setting_key("Gaia.Ring.Protocol") is False


class TestNormalizeKeySegments:
    def test_four_part_key_merged(self) -> None:
        assert (
            _normalize_key_segments("anomaly_x.communication.antenna.construction")
            == "anomaly_x_communication.antenna.construction"
        )

    def test_five_part_key_merged(self) -> None:
        assert (
            _normalize_key_segments("a.b.c.d.e")
            == "a_b_c.d.e"
        )

    def test_two_part_key_split_by_underscore(self) -> None:
        assert _normalize_key_segments("category.sub_name") == "category.sub.name"

    def test_two_part_key_no_underscore_returns_none(self) -> None:
        assert _normalize_key_segments("category.sub") is None

    def test_task112_mixed_invalid_key_sanitized(self) -> None:
        normalized = _normalize_key_segments("e.0.实验室.位置与历史")
        assert normalized == "e_0.s_4ae2c4c7.n_ad166662"
        assert _is_valid_setting_key(normalized) is True


class TestGenerateFallbackKey:
    def test_from_chinese_name(self) -> None:
        key = _generate_fallback_key("通信天线构造")
        assert key == "c_f97cb6b6.s_fe7a4c49.n_59176c56"
        assert _is_valid_setting_key(key) is True

    def test_from_mixed_name(self) -> None:
        key = _generate_fallback_key("青铜大门 ancient gate")
        assert key == "c_6dae199f.s_c4ae0f6e.ancient"
        assert _is_valid_setting_key(key) is True

    def test_stop_words_skipped(self) -> None:
        key = _generate_fallback_key("神秘的古老遗迹")
        assert key == "c_86878053.s_6bad1a9d.n_6c0ed487"
        assert _is_valid_setting_key(key) is True

    def test_too_short_returns_none(self) -> None:
        assert _generate_fallback_key("大门") is None

    def test_only_stop_words_returns_none(self) -> None:
        assert _generate_fallback_key("的和了") is None


class TestNormalizeSettingKey:
    def test_valid_key_unchanged(self) -> None:
        assert (
            _normalize_setting_key("gaia_ring.protocol.zero_silence", "任意名称")
            == "gaia_ring.protocol.zero_silence"
        )

    def test_four_part_key_normalized_from_key(self) -> None:
        assert (
            _normalize_setting_key(
                "anomaly_x.communication.antenna.construction", "通信天线构造"
            )
            == "anomaly_x_communication.antenna.construction"
        )

    def test_invalid_key_uses_name_fallback(self) -> None:
        assert (
            _normalize_setting_key("bad_key_without_dots", "通信天线构造")
            == "c_f97cb6b6.s_fe7a4c49.n_59176c56"
        )

    def test_invalid_key_no_fallback_returns_none(self) -> None:
        assert _normalize_setting_key("bad_key_without_dots", "大门") is None

    def test_empty_key_uses_name_fallback(self) -> None:
        assert (
            _normalize_setting_key("", "古老符文大门")
            == "c_6bad1a9d.s_52bd5ee2.n_c4ae0f6e"
        )

    def test_empty_key_and_short_name_returns_none(self) -> None:
        assert _normalize_setting_key("", "大门") is None

    def test_task112_ch97_key_normalized_before_validation(self) -> None:
        normalized = _normalize_setting_key("e.0.实验室.位置与历史", "实验室位置与历史")
        assert normalized == "e_0.s_4ae2c4c7.n_ad166662"
        assert _is_valid_setting_key(normalized) is True
