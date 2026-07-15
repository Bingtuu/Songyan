"""Task 172h: ContinuityAuditor field wiring + duplicate constant elimination."""

from __future__ import annotations

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.agents.continuity_auditor._scanners import (
    FORGOTTEN_THRESHOLD,
    ORPHANED_THRESHOLDS,
    STATE_MISMATCH_WINDOW,
    _find_forgotten_items,
    _find_orphaned_settings,
)
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models import ContinuityToleranceProfile, GenreRuntimeProfile


def _build_test_profile(**overrides) -> GenreRuntimeProfile:
    base = load_profile_from_registry("scifi")
    data = base.model_dump(mode="json")
    data.update(overrides)
    return GenreRuntimeProfile.model_validate(data)


def test_auditor_no_longer_defines_duplicate_constants() -> None:
    """__init__.py 不应再定义 FORGOTTEN_THRESHOLD / STATE_MISMATCH_WINDOW 类属性."""
    assert not hasattr(ContinuityAuditor, "FORGOTTEN_THRESHOLD")
    assert not hasattr(ContinuityAuditor, "STATE_MISMATCH_WINDOW")


async def test_find_orphaned_settings_uses_profile_thresholds(monkeypatch) -> None:
    """profile 修改 orphaned_thresholds 后，使用的阈值变化."""
    from unittest.mock import AsyncMock

    profile = _build_test_profile(
        continuity=ContinuityToleranceProfile(
            orphaned_thresholds={"critical": 99}
        )
    )

    called_thresholds: list[int] = []
    repo_mock = AsyncMock()
    repo_mock.active_setting_mark_keys = AsyncMock(return_value=set())
    repo_mock.find_orphaned = AsyncMock(return_value=[])

    async def capture_find_orphaned(*args, **kwargs):
        called_thresholds.append(kwargs["threshold"])
        return []

    repo_mock.find_orphaned = capture_find_orphaned

    await _find_orphaned_settings(
        "proj", 100, repo_mock, runtime_profile=profile
    )

    assert 99 in called_thresholds


async def test_find_forgotten_items_uses_profile_threshold(monkeypatch) -> None:
    """profile 修改 forgotten_threshold 后，判断 forgotten 的窗口变化."""
    profile = _build_test_profile(
        continuity=ContinuityToleranceProfile(forgotten_threshold=10)
    )

    from unittest.mock import AsyncMock

    rows = [
        {
            "status": "held",
            "last_used_chapter": 1,
            "acquired_in_chapter": 1,
            "track_id": "t1",
            "character_id": "c1",
            "item_name": "item",
        }
    ]
    repo_mock = AsyncMock()
    repo_mock.list_by_project = AsyncMock(return_value=rows)

    result = await _find_forgotten_items(
        "proj", 100, repo_mock, runtime_profile=profile
    )
    assert len(result) == 1  # 100 - 1 = 99 >= 10

    result_default = await _find_forgotten_items(
        "proj", 4, repo_mock, runtime_profile=profile
    )
    assert len(result_default) == 0  # 4 - 1 = 3 < 10


def test_scifi_profile_defaults_equal_legacy_constants() -> None:
    """scifi profile 默认值必须与旧常量等价."""
    scifi = load_profile_from_registry("scifi")
    assert scifi.continuity.orphaned_thresholds == ORPHANED_THRESHOLDS
    assert scifi.continuity.forgotten_threshold == FORGOTTEN_THRESHOLD
    assert scifi.continuity.state_mismatch_window == STATE_MISMATCH_WINDOW


async def test_no_profile_falls_back_to_legacy_constants(monkeypatch) -> None:
    """无 profile 时 _find_orphaned_settings 使用旧常量."""
    from unittest.mock import AsyncMock

    repo_mock = AsyncMock()
    repo_mock.active_setting_mark_keys = AsyncMock(return_value=set())
    called_categories: list[str] = []

    async def capture_find_orphaned(*args, **kwargs):
        called_categories.extend(kwargs["categories"])
        return []

    repo_mock.find_orphaned = capture_find_orphaned

    await _find_orphaned_settings("proj", 100, repo_mock, runtime_profile=None)

    assert set(called_categories) == set(ORPHANED_THRESHOLDS.keys())
