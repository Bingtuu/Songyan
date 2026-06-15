"""Task 035: GenreProfile 模型升级测试."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from songyan.genres.loader import (
    _GENRES_DIR,
    clear_cache,
    load_genre_profile,
    set_genres_dir,
)
from songyan.models.genre import (
    EmotionArc,
    GenreProfile,
    PacingTemplate,
    PunchTypeDef,
    SensoryTemplate,
    StyleBaseline,
    SubGenre,
)

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
#  Layer 1: 模型测试
# ---------------------------------------------------------------------------


class TestPacingTemplate:
    """PacingTemplate 模型测试."""

    def test_minimal_instantiation(self) -> None:
        pt = PacingTemplate()
        assert pt.chapter_types == []
        assert pt.punch_density == 0.0

    def test_full_instantiation(self) -> None:
        pt = PacingTemplate(
            chapter_types=["combat", "transition"],
            emotion_arc="生死搏杀",
            punch_density=2.5,
            info_release_strategy="快速进入对抗",
        )
        assert pt.punch_density == 2.5
        assert pt.emotion_arc == "生死搏杀"

    def test_punch_density_too_high(self) -> None:
        with pytest.raises(ValidationError):
            PacingTemplate(punch_density=5.1)

    def test_punch_density_negative(self) -> None:
        with pytest.raises(ValidationError):
            PacingTemplate(punch_density=-0.1)

    def test_punch_density_boundary(self) -> None:
        pt = PacingTemplate(punch_density=5.0)
        assert pt.punch_density == 5.0


class TestStyleBaseline:
    """StyleBaseline 模型测试."""

    def test_minimal_instantiation(self) -> None:
        sb = StyleBaseline()
        assert sb.sentence_rhythm == ""
        assert sb.description_density == 0.3
        assert sb.dialogue_ratio == 0.3

    def test_density_sum_valid(self) -> None:
        sb = StyleBaseline(description_density=0.5, dialogue_ratio=0.4)
        assert sb.description_density + sb.dialogue_ratio == 0.9

    def test_density_sum_exactly_one(self) -> None:
        sb = StyleBaseline(description_density=0.6, dialogue_ratio=0.4)
        assert sb.description_density + sb.dialogue_ratio == 1.0

    def test_density_sum_exceeds_one(self) -> None:
        with pytest.raises(ValidationError):
            StyleBaseline(description_density=0.7, dialogue_ratio=0.4)

    def test_description_density_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            StyleBaseline(description_density=1.1)

    def test_dialogue_ratio_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            StyleBaseline(dialogue_ratio=-0.1)


class TestSensoryTemplate:
    """SensoryTemplate 模型测试."""

    def test_valid_sense(self) -> None:
        st = SensoryTemplate(sense="visual", intensity_target=0.7)
        assert st.sense == "visual"

    def test_invalid_sense(self) -> None:
        with pytest.raises(ValidationError):
            SensoryTemplate(sense="telepathy")

    def test_intensity_boundary(self) -> None:
        st = SensoryTemplate(sense="pain", intensity_target=1.0)
        assert st.intensity_target == 1.0


class TestEmotionArc:
    """EmotionArc 模型测试."""

    def test_instantiation(self) -> None:
        arc = EmotionArc(
            arc_name="升级突破",
            phases=[
                {"from": "积累", "to": "瓶颈"},
                {"from": "瓶颈", "to": "突破"},
            ],
            typical_length_words=3000,
            suitable_chapter_types=["cultivation_breakthrough"],
        )
        assert len(arc.phases) == 2
        assert arc.typical_length_words == 3000


class TestSubGenre:
    """SubGenre 模型测试."""

    def test_instantiation(self) -> None:
        sg = SubGenre(
            sub_genre_id="xianxia",
            name="仙侠",
            parent_genre_id="xuanhuan",
            differentiation_rules=["侧重道法自然", "强调长生大道"],
        )
        assert sg.sub_genre_id == "xianxia"


class TestPunchTypeDef:
    """PunchTypeDef 模型测试."""

    def test_instantiation(self) -> None:
        ptd = PunchTypeDef(
            punch_type_id="reversal",
            description="身份/立场反转",
            genre_suitability={"xuanhuan": 0.8, "scifi": 0.6},
            sensory_requirements=["visual"],
        )
        assert ptd.punch_type_id == "reversal"


class TestGenreProfileBackwardsCompatibility:
    """向后兼容测试 — 旧 dict 加载不报错."""

    def test_old_dict_loads(self) -> None:
        """旧 dict（无新字段）可正常加载，新字段为默认值."""
        data = {
            "id": "legacy",
            "name": " legacy genre",
            "chapter_types": ["a", "b"],
            "fatigue_words": ["word"],
            "pacing_rule": "旧节奏规则",
        }
        gp = GenreProfile.from_dict(data)
        assert gp.id == "legacy"
        assert gp.pacing_rule == "旧节奏规则"
        assert gp.pacing_templates == []
        assert gp.style_baseline is None
        assert gp.sensory_templates == []
        assert gp.emotion_arc_library == []
        assert gp.reference_works == []

    def test_full_dict_loads(self) -> None:
        """完整 dict（含所有新字段）可正常加载."""
        data = {
            "id": "full",
            "name": "完整类型",
            "pacing_templates": [
                {
                    "chapter_types": ["combat"],
                    "emotion_arc": "生死搏杀",
                    "punch_density": 2.0,
                    "info_release_strategy": "快速",
                }
            ],
            "style_baseline": {
                "sentence_rhythm": "短促有力",
                "description_density": 0.3,
                "dialogue_ratio": 0.3,
                "inner_monologue": "克制",
                "pov_depth": "中",
            },
            "sensory_templates": [
                {"sense": "visual", "intensity_target": 0.8, "description_density": 100.0}
            ],
            "emotion_arc_library": [
                {
                    "arc_name": "测试弧线",
                    "phases": [{"from": "a", "to": "b"}],
                    "typical_length_words": 2000,
                    "suitable_chapter_types": ["opening"],
                }
            ],
            "reference_works": ["作品A", "作品B"],
        }
        gp = GenreProfile.from_dict(data)
        assert len(gp.pacing_templates) == 1
        assert gp.pacing_templates[0].punch_density == 2.0
        assert gp.style_baseline is not None
        assert gp.style_baseline.sentence_rhythm == "短促有力"
        assert len(gp.sensory_templates) == 1
        assert gp.sensory_templates[0].sense == "visual"
        assert len(gp.emotion_arc_library) == 1
        assert gp.reference_works == ["作品A", "作品B"]


# ---------------------------------------------------------------------------
#  Layer 2: 模块测试 — Loader
# ---------------------------------------------------------------------------


class TestLoaderWithUpgradedConfig:
    """Loader 加载升级后的配置文件."""

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_load_upgraded_profile(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        assert isinstance(profile, GenreProfile)
        assert profile.pacing_templates is not None
        assert len(profile.pacing_templates) >= 1

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_pacing_template_valid(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        for pt in profile.pacing_templates:
            assert 0.0 <= pt.punch_density <= 5.0

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_style_baseline_valid(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        if profile.style_baseline is not None:
            sb = profile.style_baseline
            assert sb.description_density + sb.dialogue_ratio <= 1.0

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_sensory_templates_present(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        assert len(profile.sensory_templates) >= 3

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_emotion_arc_library_present(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        assert len(profile.emotion_arc_library) >= 3

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_reference_works_present(self, genre_id: str) -> None:
        profile = load_genre_profile(genre_id)
        assert len(profile.reference_works) >= 1

    def test_pacing_rule_retained(self) -> None:
        """旧 pacing_rule 字段仍保留（向后兼容）."""
        profile = load_genre_profile("xuanhuan")
        assert profile.pacing_rule != ""
        assert "情绪钩子" in profile.pacing_rule

    def test_pacing_rule_retained_and_templates_exist(self) -> None:
        """pacing_rule 保留，且 pacing_templates 已扩展."""
        profile = load_genre_profile("xuanhuan")
        assert profile.pacing_rule != ""
        assert len(profile.pacing_templates) >= 1


# ---------------------------------------------------------------------------
#  Layer 3: 集成测试
# ---------------------------------------------------------------------------


class TestIntegrationOldConfig:
    """旧配置（无新字段）集成测试."""

    def test_old_json_fields_default(self, tmp_path: Path) -> None:
        """模拟旧 genre JSON（无新字段）加载后新字段为默认值."""
        old_dir = tmp_path / "genres"
        old_dir.mkdir()
        old_data = {
            "id": "oldgenre",
            "name": "旧类型",
            "language": "zh",
            "chapter_types": ["a"],
            "fatigue_words": [],
            "satisfaction_types": [],
            "has_numerical_system": False,
            "has_power_scaling": False,
            "pacing_rule": "旧规则",
            "writer_rules": [],
            "reviewer_focus": [],
            "active_audit_dimensions": [],
            "taboos": [],
        }
        (old_dir / "oldgenre.json").write_text(json.dumps(old_data), encoding="utf-8")
        set_genres_dir(old_dir)
        profile = load_genre_profile("oldgenre")
        assert profile.pacing_templates == []
        assert profile.style_baseline is None
        assert profile.sensory_templates == []
        assert profile.emotion_arc_library == []
        assert profile.sub_genres == []
        assert profile.punch_type_defs == []
        assert profile.reference_works == []


class TestIntegrationMigratedConfig:
    """迁移后的配置集成测试."""

    @pytest.mark.parametrize("genre_id", ["xuanhuan", "urban", "scifi"])
    def test_migrated_config_has_data(self, genre_id: str) -> None:
        """迁移后的配置文件新字段均有有效数据."""
        profile = load_genre_profile(genre_id)
        assert len(profile.pacing_templates) >= 1
        assert profile.style_baseline is not None
        assert profile.style_baseline.sentence_rhythm != ""
        assert len(profile.sensory_templates) >= 3
        assert len(profile.emotion_arc_library) >= 3
        assert len(profile.reference_works) >= 1

    def test_load_upgraded_scifi(self) -> None:
        """加载器能正确加载升级后的 scifi 配置."""
        profile = load_genre_profile("scifi")
        assert profile.style_baseline is not None
        assert profile.style_baseline.inner_monologue == "克制"

    def test_xuanhuan_punch_density_high(self) -> None:
        """xuanhuan 的 punch_density 显著高于其他 genre."""
        xuan = load_genre_profile("xuanhuan")
        urban = load_genre_profile("urban")
        scifi = load_genre_profile("scifi")
        assert xuan.pacing_templates[0].punch_density > urban.pacing_templates[0].punch_density
        assert xuan.pacing_templates[0].punch_density > scifi.pacing_templates[0].punch_density
