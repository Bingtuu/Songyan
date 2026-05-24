"""Genre Profile 加载器测试."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from songyan.genres.loader import (
    _GENRES_DIR,
    GenreProfileError,
    GenreProfileLoader,
    GenreProfileNotFoundError,
    clear_cache,
    list_genre_profiles,
    load_genre_profile,
    set_genres_dir,
)
from songyan.models.genre import GenreProfile
from songyan.models.review import ReviewCategory

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
#  Layer 1: 配置文件测试
# ---------------------------------------------------------------------------


class TestConfigFiles:
    """三个 JSON 配置文件的基础校验."""

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_json_is_valid(self, genre_id: str) -> None:
        """JSON 文件可解析为 dict."""
        path = _GENRES_DIR / f"{genre_id}.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_can_instantiate_genre_profile(self, genre_id: str) -> None:
        """JSON 可实例化为 GenreProfile."""
        profile = load_genre_profile(genre_id)
        assert isinstance(profile, GenreProfile)

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_id_matches_filename(self, genre_id: str) -> None:
        """JSON 中的 id 与文件名一致."""
        profile = load_genre_profile(genre_id)
        assert profile.id == genre_id

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
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

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_active_audit_dimensions_from_review_category(self, genre_id: str) -> None:
        """active_audit_dimensions 全部来自 ReviewCategory."""
        profile = load_genre_profile(genre_id)
        valid_values = {c.value for c in ReviewCategory}
        for dim in profile.active_audit_dimensions:
            assert dim in valid_values, f"{dim} is not a valid ReviewCategory"


class TestXuanhuanCompleteness:
    """xuanhuan.json 完整度要求."""

    def test_has_numerical_and_power_scaling(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert profile.has_numerical_system is True
        assert profile.has_power_scaling is True

    def test_chapter_types(self) -> None:
        profile = load_genre_profile("xuanhuan")
        required = {
            "opening",
            "cultivation_breakthrough",
            "combat",
            "sect_conflict",
            "treasure_hunt",
            "transition",
        }
        assert required.issubset(set(profile.chapter_types))

    def test_satisfaction_types(self) -> None:
        profile = load_genre_profile("xuanhuan")
        required = {"升级", "打脸", "夺宝", "宗门压迫", "师徒/传承", "伏笔回收"}
        assert required.issubset(set(profile.satisfaction_types))

    def test_fatigue_words_count(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert len(profile.fatigue_words) >= 20

    def test_writer_rules_count(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert len(profile.writer_rules) >= 8

    def test_reviewer_focus_count(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert len(profile.reviewer_focus) >= 6

    def test_active_audit_dimensions_includes_genre_numerical(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert "genre_numerical" in profile.active_audit_dimensions


# ---------------------------------------------------------------------------
#  Layer 2: 加载器测试
# ---------------------------------------------------------------------------


class TestLoaderFunctions:
    """load_genre_profile / list_genre_profiles 行为测试."""

    def test_load_xuanhuan(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert profile.id == "xuanhuan"

    def test_load_urban(self) -> None:
        profile = load_genre_profile("urban")
        assert profile.id == "urban"

    def test_load_scifi(self) -> None:
        profile = load_genre_profile("scifi")
        assert profile.id == "scifi"

    def test_list_genre_profiles_sorted(self) -> None:
        result = list_genre_profiles()
        assert result == ["scifi", "urban", "xuanhuan"]

    def test_invalid_genre_raises_not_found(self) -> None:
        with pytest.raises(GenreProfileNotFoundError) as exc_info:
            load_genre_profile("nonexistent")
        msg = str(exc_info.value)
        assert "nonexistent" in msg
        assert "xuanhuan" in msg
        assert "urban" in msg
        assert "scifi" in msg

    def test_invalid_json_raises_genre_profile_error(self, tmp_path: Path) -> None:
        bad_dir = tmp_path / "genres"
        bad_dir.mkdir()
        (bad_dir / "broken.json").write_text("not json", encoding="utf-8")
        set_genres_dir(bad_dir)
        with pytest.raises(GenreProfileError) as exc_info:
            load_genre_profile("broken")
        assert "parse JSON" in str(exc_info.value)

    def test_invalid_model_raises_genre_profile_error(self, tmp_path: Path) -> None:
        bad_dir = tmp_path / "genres"
        bad_dir.mkdir()
        (bad_dir / "badmodel.json").write_text(
            json.dumps({"id": "badmodel"}), encoding="utf-8"
        )
        set_genres_dir(bad_dir)
        with pytest.raises(GenreProfileError) as exc_info:
            load_genre_profile("badmodel")
        assert "validate" in str(exc_info.value).lower() or "Failed" in str(exc_info.value)

    def test_cache_reuse(self) -> None:
        p1 = load_genre_profile("xuanhuan")
        p2 = load_genre_profile("xuanhuan")
        assert p1 is p2

    def test_clear_cache(self) -> None:
        p1 = load_genre_profile("xuanhuan")
        clear_cache()
        p2 = load_genre_profile("xuanhuan")
        assert p1 is not p2
        assert p1 == p2


class TestGenreProfileLoader:
    """GenreProfileLoader 类封装测试."""

    def test_load(self) -> None:
        profile = GenreProfileLoader.load("xuanhuan")
        assert profile.id == "xuanhuan"

    def test_list_genres(self) -> None:
        result = GenreProfileLoader.list_genres()
        assert result == ["scifi", "urban", "xuanhuan"]

    def test_clear_cache(self) -> None:
        p1 = GenreProfileLoader.load("xuanhuan")
        GenreProfileLoader.clear_cache()
        p2 = GenreProfileLoader.load("xuanhuan")
        assert p1 is not p2


# ---------------------------------------------------------------------------
#  Layer 3: 集成测试
# ---------------------------------------------------------------------------


class TestIntegration:
    """与现有模型的集成验证."""

    def test_project_setting_can_load_profile(self) -> None:
        """模拟创建项目后可用 genre_id 加载对应配置."""
        from songyan.models.project import ProjectSetting

        setting = ProjectSetting(
            title="测试玄幻",
            genre_id="xuanhuan",
            mode_id="webnovel",
            protagonist_name="林凡",
        )
        profile = load_genre_profile(setting.genre_id)
        assert profile.id == "xuanhuan"

    def test_xuanhuan_non_empty_lists(self) -> None:
        profile = load_genre_profile("xuanhuan")
        assert len(profile.fatigue_words) > 0
        assert len(profile.writer_rules) > 0
        assert len(profile.reviewer_focus) > 0
