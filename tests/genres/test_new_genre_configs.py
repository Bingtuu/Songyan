"""Task 036: 新 Genre 配置测试."""

from __future__ import annotations

import json

import pytest

from songyan.genres.loader import (
    _GENRES_DIR,
    clear_cache,
    list_genre_profiles,
    load_genre_profile,
)
from songyan.models.genre import GenreProfile

# ---------------------------------------------------------------------------
#  fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache_and_dir(monkeypatch) -> None:
    """每个测试前重置缓存和目录到默认值."""
    clear_cache()
    monkeypatch.setattr(
        "songyan.genres.loader._GENRES_DIR",
        _GENRES_DIR,
    )


# ---------------------------------------------------------------------------
#  Layer 1: 配置文件基础验证
# ---------------------------------------------------------------------------


class TestNewConfigFiles:
    """4 个新 JSON 配置文件的基础校验."""

    NEW_GENRES = ["urban_fantasy", "post_apocalyptic", "mystery_noir", "wuxia"]

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_json_is_valid(self, genre_id: str) -> None:
        """JSON 文件可解析为 dict."""
        path = _GENRES_DIR / f"{genre_id}.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_can_instantiate_genre_profile(self, genre_id: str) -> None:
        """JSON 可实例化为 GenreProfile."""
        profile = load_genre_profile(genre_id)
        assert isinstance(profile, GenreProfile)

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_id_matches_filename(self, genre_id: str) -> None:
        """JSON 中的 id 与文件名一致."""
        profile = load_genre_profile(genre_id)
        assert profile.id == genre_id

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_required_fields_present(self, genre_id: str) -> None:
        """所有必填字段均存在且非 None."""
        profile = load_genre_profile(genre_id)
        assert profile.id is not None
        assert profile.name is not None
        assert profile.language is not None
        assert profile.chapter_types is not None
        assert profile.fatigue_words is not None
        assert profile.satisfaction_types is not None
        assert profile.has_numerical_system is not None
        assert profile.has_power_scaling is not None
        assert profile.pacing_rule is not None
        assert profile.writer_rules is not None
        assert profile.reviewer_focus is not None
        assert profile.active_audit_dimensions is not None
        assert profile.taboos is not None


# ---------------------------------------------------------------------------
#  Layer 2: 新配置完整性验证
# ---------------------------------------------------------------------------


class TestNewGenreCompleteness:
    """4 个新 Genre 的完整度要求."""

    NEW_GENRES = ["urban_fantasy", "post_apocalyptic", "mystery_noir", "wuxia"]

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_pacing_templates_not_empty(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        assert len(profile.pacing_templates) >= 1

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_style_baseline_complete(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        assert profile.style_baseline is not None
        sb = profile.style_baseline
        assert sb.sentence_rhythm != ""
        assert 0.0 <= sb.description_density <= 1.0
        assert 0.0 <= sb.dialogue_ratio <= 1.0
        assert sb.inner_monologue != ""
        assert sb.pov_depth != ""

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_sensory_templates_at_least_three(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        assert len(profile.sensory_templates) >= 3

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_emotion_arc_library_at_least_three(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        assert len(profile.emotion_arc_library) >= 3

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_reference_works_not_empty(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        assert len(profile.reference_works) >= 1

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_punch_density_in_range(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        for pt in profile.pacing_templates:
            assert 0.0 <= pt.punch_density <= 5.0

    @pytest.mark.parametrize("genre_id", NEW_GENRES)
    def test_density_sum_valid(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        sb = profile.style_baseline
        if sb is not None:
            assert sb.description_density + sb.dialogue_ratio <= 1.0


class TestXuanhuanEnhanced:
    """xuanhuan.json 增强验证."""

    def test_fatigue_words_at_least_25(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert len(profile.fatigue_words) >= 25

    def test_pacing_templates_four(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert len(profile.pacing_templates) == 4

    def test_pacing_template_types(self) -> None:
        profile = load_genre_profile("xuanhuan")
        arcs = {pt.emotion_arc for pt in profile.pacing_templates}
        assert "升级爽点" in arcs
        assert "绝境逆袭" in arcs
        assert "师徒传承" in arcs
        assert "平稳过渡" in arcs

    def test_style_baseline_updated(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert profile.style_baseline is not None
        assert profile.style_baseline.description_density == 0.35
        assert profile.style_baseline.dialogue_ratio == 0.25

    def test_sensory_templates_updated(self) -> None:
        profile = load_genre_profile("xuanhuan")
        senses = {st.sense for st in profile.sensory_templates}
        assert "proprioception" in senses
        assert "pain" in senses
        assert "gustatory" in senses

    def test_emotion_arc_library_updated(self) -> None:
        profile = load_genre_profile("xuanhuan")
        arcs = {ea.arc_name for ea in profile.emotion_arc_library}
        assert "升级爽点" in arcs
        assert "绝境逆袭" in arcs
        assert "师徒传承" in arcs


# ---------------------------------------------------------------------------
#  Layer 3: 集成测试
# ---------------------------------------------------------------------------


class TestIntegrationAllGenres:
    """全部 7 个配置集成验证."""

    ALL_GENRES = [
        "scifi",
        "urban",
        "urban_fantasy",
        "post_apocalyptic",
        "mystery_noir",
        "wuxia",
        "xuanhuan",
    ]

    def test_list_returns_seven(self) -> None:
        result = list_genre_profiles()
        assert len(result) == 7
        assert sorted(result) == sorted(self.ALL_GENRES)

    def test_all_genres_load_without_conflict(self) -> None:
        profiles = [load_genre_profile(g) for g in self.ALL_GENRES]
        ids = {p.id for p in profiles}
        assert len(ids) == 7

    @pytest.mark.parametrize("genre_id", ALL_GENRES)
    def test_each_has_valid_style_baseline(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        if profile.style_baseline is not None:
            sb = profile.style_baseline
            assert sb.description_density + sb.dialogue_ratio <= 1.0

    def test_list_genre_profiles_returns_all(self) -> None:
        result = list_genre_profiles()
        assert len(result) == 7
        assert sorted(result) == sorted(self.ALL_GENRES)

    def test_xuanhuan_has_highest_punch_density(self) -> None:
        """xuanhuan 的整体 punch_density 最高."""
        xuanhuan = load_genre_profile("xuanhuan")
        max_xh = max(pt.punch_density for pt in xuanhuan.pacing_templates)
        for gid in ["scifi", "urban", "urban_fantasy", "post_apocalyptic", "mystery_noir", "wuxia"]:
            other = load_genre_profile(gid)
            max_other = max((pt.punch_density for pt in other.pacing_templates), default=0)
            assert max_xh >= max_other
