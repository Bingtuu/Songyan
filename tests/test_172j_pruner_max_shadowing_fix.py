"""Task 172j: profile max_* 作为体裁级收紧上限接入生产路径.

证明：
- 无 profile / scifi 全默认 profile → 生产路径硬上限与旧章节动态曲线逐值等价（零漂移）。
- profile 调低到旧常量基线以下 → 立即收紧生效。
- profile 调高（含 wuxia/xuanhuan 注册表的 max_character_states=8）→ 不生效，
  由章节动态曲线接管（保证 scifi 基线不被 min 语义静默收紧）。
"""

from __future__ import annotations

from songyan.agents.context_manager import (
    MAX_CHARACTER_STATES,
    MAX_FORESHADOWING,
    _dynamic_max_for_chapter,
    _dynamic_max_soft_refs,
    _effective_hard_caps,
)
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models import GenreRuntimeProfile


def _profile_with(**overrides: object) -> GenreRuntimeProfile:
    base = load_profile_from_registry("scifi")
    return base.model_copy(update=overrides)


def test_none_profile_returns_legacy_dynamic() -> None:
    for ch in (1, 80, 81, 100):
        caps = _effective_hard_caps(ch, total_settings=100, runtime_profile=None)
        legacy = _dynamic_max_for_chapter(ch)
        assert caps["max_character_states"] == legacy["max_character_states"]
        assert caps["max_foreshadowing"] == legacy["max_foreshadowing"]
        assert caps["max_setting_input"] == legacy["max_setting_input"]
        assert caps["max_soft_refs"] == _dynamic_max_soft_refs(100)


def test_scifi_profile_caps_equal_legacy_dynamic() -> None:
    """scifi 全默认 profile 必须与无 profile 逐值等价（含 soft_refs 动态 10-16 区间）."""
    scifi = load_profile_from_registry("scifi")
    for ch in (1, 80, 81, 100):
        for settings in (0, 20, 100):
            caps = _effective_hard_caps(ch, settings, scifi)
            legacy = _dynamic_max_for_chapter(ch)
            assert caps["max_character_states"] == legacy["max_character_states"]
            assert caps["max_foreshadowing"] == legacy["max_foreshadowing"]
            assert caps["max_soft_refs"] == _dynamic_max_soft_refs(settings)


def test_profile_clamp_down_character_states() -> None:
    profile = _profile_with(max_character_states=3)
    caps = _effective_hard_caps(1, 0, profile)
    assert caps["max_character_states"] == 3


def test_profile_clamp_down_respects_dynamic_when_dynamic_lower() -> None:
    """Ch81+ 动态值 3 已低于 profile 收紧值时，取更低者."""
    profile = _profile_with(max_character_states=3)
    caps = _effective_hard_caps(81, 0, profile)
    assert caps["max_character_states"] == 3
    profile2 = _profile_with(max_character_states=3)
    caps2 = _effective_hard_caps(100, 0, profile2)
    assert caps2["max_character_states"] == 3


def test_profile_raise_character_states_no_effect() -> None:
    """调高不生效：profile=8（= wuxia/xuanhuan 注册表值）不改变动态曲线."""
    profile = _profile_with(max_character_states=8)
    assert _effective_hard_caps(1, 0, profile)["max_character_states"] == 4
    assert _effective_hard_caps(81, 0, profile)["max_character_states"] == 3


def test_profile_equal_legacy_returns_dynamic() -> None:
    profile = _profile_with(max_character_states=MAX_CHARACTER_STATES)
    assert _effective_hard_caps(1, 0, profile)["max_character_states"] == 4
    assert _effective_hard_caps(81, 0, profile)["max_character_states"] == 3


def test_profile_clamp_down_foreshadowing() -> None:
    profile = _profile_with(max_foreshadowing=6)
    assert _effective_hard_caps(1, 0, profile)["max_foreshadowing"] == 6
    # Ch81+ 动态 5 低于 6，取动态值
    assert _effective_hard_caps(81, 0, profile)["max_foreshadowing"] == 5


def test_profile_clamp_down_soft_refs_below_legacy() -> None:
    """profile 收紧到旧常量以下时，即使动态曲线放宽到 16 也压到 8."""
    profile = _profile_with(max_soft_refs=8)
    assert _effective_hard_caps(1, 100, profile)["max_soft_refs"] == 8
    assert _effective_hard_caps(1, 0, profile)["max_soft_refs"] == 8


def test_profile_soft_refs_above_legacy_no_effect() -> None:
    """soft_refs 动态区间 10-16 超过旧常量 10：profile=12 不生效（防 scifi 漂移）."""
    profile = _profile_with(max_soft_refs=12)
    assert _effective_hard_caps(1, 0, profile)["max_soft_refs"] == _dynamic_max_soft_refs(0)
    assert _effective_hard_caps(1, 100, profile)["max_soft_refs"] == _dynamic_max_soft_refs(100)


def test_wuxia_xuanhuan_registry_caps_unchanged() -> None:
    """注册表 wuxia/xuanhuan max_character_states=8 按当前语义不生效（172j 固化）."""
    for genre in ("wuxia", "xuanhuan"):
        profile = load_profile_from_registry(genre)
        caps = _effective_hard_caps(1, 100, profile)
        assert caps["max_character_states"] == MAX_CHARACTER_STATES
        assert caps["max_foreshadowing"] == MAX_FORESHADOWING
        assert caps["max_soft_refs"] == _dynamic_max_soft_refs(100)
