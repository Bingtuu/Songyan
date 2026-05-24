"""CreativeModeProfile 注册表测试."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from songyan.creative_modes.registry import (
    _MODES_DIR,
    CreativeModeProfileError,
    CreativeModeProfileLoader,
    CreativeModeProfileNotFoundError,
    clear_cache,
    list_creative_mode_profiles,
    load_creative_mode_profile,
    set_modes_dir,
)
from songyan.models.creative_mode import CreativeModeProfile
from songyan.models.review import ReviewCategory

# ---------------------------------------------------------------------------
#  fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache_and_dir(monkeypatch) -> None:
    """每个测试前重置缓存和目录到默认值."""
    clear_cache()
    monkeypatch.setattr(
        "songyan.creative_modes.registry._MODES_DIR",
        _MODES_DIR,
    )


# ---------------------------------------------------------------------------
#  Layer 1: 配置文件测试
# ---------------------------------------------------------------------------


class TestConfigFiles:
    """三个 JSON 配置文件的基础校验."""

    @pytest.mark.parametrize("mode_id", ["webnovel", "literary", "hybrid"])
    def test_json_is_valid(self, mode_id: str) -> None:
        """JSON 文件可解析为 dict."""
        path = _MODES_DIR / f"{mode_id}.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("mode_id", ["webnovel", "literary", "hybrid"])
    def test_can_instantiate_creative_mode_profile(self, mode_id: str) -> None:
        """JSON 可实例化为 CreativeModeProfile."""
        profile = load_creative_mode_profile(mode_id)
        assert isinstance(profile, CreativeModeProfile)

    @pytest.mark.parametrize("mode_id", ["webnovel", "literary", "hybrid"])
    def test_id_matches_filename(self, mode_id: str) -> None:
        """JSON 中的 id 与文件名一致."""
        profile = load_creative_mode_profile(mode_id)
        assert profile.id == mode_id

    @pytest.mark.parametrize("mode_id", ["webnovel", "literary", "hybrid"])
    def test_required_fields_present(self, mode_id: str) -> None:
        """所有必填字段均存在且非 None."""
        profile = load_creative_mode_profile(mode_id)
        assert profile.id is not None
        assert profile.name is not None
        assert profile.enabled_agents is not None
        assert profile.audit_weights is not None
        assert profile.active_audit_dimensions is not None
        assert profile.revision_policy is not None
        assert profile.tolerance is not None
        assert profile.context_pruning_strategy is not None
        assert profile.success_metrics is not None

    @pytest.mark.parametrize("mode_id", ["webnovel", "literary", "hybrid"])
    def test_active_audit_dimensions_from_review_category(self, mode_id: str) -> None:
        """active_audit_dimensions 全部来自 ReviewCategory."""
        profile = load_creative_mode_profile(mode_id)
        valid_values = {c.value for c in ReviewCategory}
        for dim in profile.active_audit_dimensions:
            assert dim in valid_values, f"{dim} is not a valid ReviewCategory"


class TestWebnovelCompleteness:
    """webnovel.json 完整度要求."""

    def test_enabled_agents_stages(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        agents = profile.enabled_agents
        assert agents.get("pre_write") == ["goal_planner", "creative_director"]
        assert agents.get("write") == ["writer"]
        assert agents.get("post_write") == [
            "rule_auditor",
            "llm_auditor",
            "literary_auditor",
        ]
        assert agents.get("revision") == ["revision_handler"]
        assert agents.get("settlement") == ["settlement_extractor"]

    def test_audit_weights_count(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        assert len(profile.audit_weights) >= 6

    def test_audit_weights_range(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        for weight in profile.audit_weights.values():
            assert 0.0 <= weight <= 2.0

    def test_active_audit_dimensions_count(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        assert len(profile.active_audit_dimensions) >= 8

    def test_active_audit_dimensions_includes_required(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        assert "narrative_pacing" in profile.active_audit_dimensions
        assert "narrative_hook" in profile.active_audit_dimensions
        assert "genre_numerical" in profile.active_audit_dimensions

    def test_revision_policy(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        assert profile.revision_policy == "standard"

    def test_tolerance_keys(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        tolerance = profile.tolerance
        assert "max_ai_tells" in tolerance
        assert "max_fatigue_words" in tolerance
        assert "max_cliche_risk" in tolerance

    def test_success_metrics_count(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        assert len(profile.success_metrics) >= 3


# ---------------------------------------------------------------------------
#  Layer 2: 加载器测试
# ---------------------------------------------------------------------------


class TestLoaderFunctions:
    """load_creative_mode_profile / list_creative_mode_profiles 行为测试."""

    def test_load_webnovel(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        assert profile.id == "webnovel"

    def test_load_literary(self) -> None:
        profile = load_creative_mode_profile("literary")
        assert profile.id == "literary"

    def test_load_hybrid(self) -> None:
        profile = load_creative_mode_profile("hybrid")
        assert profile.id == "hybrid"

    def test_list_creative_mode_profiles_sorted(self) -> None:
        result = list_creative_mode_profiles()
        assert result == ["hybrid", "literary", "webnovel"]

    def test_invalid_mode_raises_not_found(self) -> None:
        with pytest.raises(CreativeModeProfileNotFoundError) as exc_info:
            load_creative_mode_profile("nonexistent")
        msg = str(exc_info.value)
        assert "nonexistent" in msg
        assert "webnovel" in msg
        assert "literary" in msg
        assert "hybrid" in msg

    def test_invalid_json_raises_creative_mode_error(self, tmp_path: Path) -> None:
        bad_dir = tmp_path / "creative_modes"
        bad_dir.mkdir()
        (bad_dir / "broken.json").write_text("not json", encoding="utf-8")
        set_modes_dir(bad_dir)
        with pytest.raises(CreativeModeProfileError) as exc_info:
            load_creative_mode_profile("broken")
        assert "parse JSON" in str(exc_info.value)

    def test_invalid_model_raises_creative_mode_error(self, tmp_path: Path) -> None:
        bad_dir = tmp_path / "creative_modes"
        bad_dir.mkdir()
        (bad_dir / "badmodel.json").write_text(
            json.dumps({"id": "badmodel"}), encoding="utf-8"
        )
        set_modes_dir(bad_dir)
        with pytest.raises(CreativeModeProfileError) as exc_info:
            load_creative_mode_profile("badmodel")
        assert "validate" in str(exc_info.value).lower() or "Failed" in str(
            exc_info.value
        )

    def test_cache_reuse(self) -> None:
        p1 = load_creative_mode_profile("webnovel")
        p2 = load_creative_mode_profile("webnovel")
        assert p1 is p2

    def test_clear_cache(self) -> None:
        p1 = load_creative_mode_profile("webnovel")
        clear_cache()
        p2 = load_creative_mode_profile("webnovel")
        assert p1 is not p2
        assert p1 == p2


class TestCreativeModeProfileLoader:
    """CreativeModeProfileLoader 类封装测试."""

    def test_load(self) -> None:
        profile = CreativeModeProfileLoader.load("webnovel")
        assert profile.id == "webnovel"

    def test_list_modes(self) -> None:
        result = CreativeModeProfileLoader.list_modes()
        assert result == ["hybrid", "literary", "webnovel"]

    def test_clear_cache(self) -> None:
        p1 = CreativeModeProfileLoader.load("webnovel")
        CreativeModeProfileLoader.clear_cache()
        p2 = CreativeModeProfileLoader.load("webnovel")
        assert p1 is not p2


# ---------------------------------------------------------------------------
#  Layer 3: 集成测试
# ---------------------------------------------------------------------------


class TestIntegration:
    """与现有模型的集成验证."""

    def test_project_setting_can_load_profile(self) -> None:
        """模拟创建项目后可用 mode_id 加载对应配置."""
        from songyan.models.project import ProjectSetting

        setting = ProjectSetting(
            title="测试项目",
            genre_id="xuanhuan",
            mode_id="webnovel",
            protagonist_name="林凡",
        )
        profile = load_creative_mode_profile(setting.mode_id)
        assert profile.id == "webnovel"

    def test_webnovel_non_empty_lists(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        assert len(profile.enabled_agents) > 0
        assert len(profile.audit_weights) > 0
        assert len(profile.tolerance) > 0

    def test_webnovel_post_write_includes_literary_auditor(self) -> None:
        profile = load_creative_mode_profile("webnovel")
        assert "literary_auditor" in profile.enabled_agents.get("post_write", [])
