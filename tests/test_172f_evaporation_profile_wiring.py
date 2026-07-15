"""Task 172f: SettingEvaporator / foreshadowing ranking field wiring tests.

Prove that `setting_evaporation` and `foreshadowing_evaporation` fields on
`GenreRuntimeProfile` actually change behavior, and that `runtime_profile=None`
falls back to legacy constants exactly.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.context_manager import _rank_foreshadowings
from songyan.agents.setting_evaporator import (
    CATEGORY_TIME_DENOMINATORS,
    CONFIDENCE_ARCHIVE_THRESHOLD,
    CONFIDENCE_ARCHIVE_THRESHOLDS,
    TIME_DECAY_DENOMINATOR,
    SettingEvaporator,
    _calculate_resolve_confidence,
)
from songyan.models import (
    ForeshadowingEvaporationProfile,
    ForeshadowingItem,
    GenreRuntimeProfile,
    SettingEvaporationProfile,
)

# ---------------------------------------------------------------------------
# _calculate_resolve_confidence
# ---------------------------------------------------------------------------

def _background_setting(last_mentioned: int = 0) -> dict[str, Any]:
    return {
        "setting_key": "world.mist",
        "setting_name": "mist",
        "category": "background",
        "last_mentioned_chapter": last_mentioned,
        "description": "a thick mist",
        "source_quote": "the mist rolled in",
    }


def test_calculate_resolve_confidence_legacy_background_denominator() -> None:
    """无 profile 时 background 类别使用 CATEGORY_TIME_DENOMINATORS['background']=25."""
    conf = _calculate_resolve_confidence(
        _background_setting(last_mentioned=0),
        current_chapter=50,
        chapter_goal=None,
    )
    # time_factor clamped to 0, relevance default 0.3, hard 0 -> 0.09
    assert conf == pytest.approx(0.09, abs=1e-4)


def test_calculate_resolve_confidence_uses_profile_time_denominator() -> None:
    """profile 提供更大的 time_denominator 时，confidence 显著升高."""
    profile = GenreRuntimeProfile(
        genre="test",
        setting_evaporation=SettingEvaporationProfile(
            time_denominators={"background": 100},
        ),
    )
    conf = _calculate_resolve_confidence(
        _background_setting(last_mentioned=0),
        current_chapter=50,
        chapter_goal=None,
        runtime_profile=profile,
    )
    # time_factor = 1 - 50/100 = 0.5; relevance 0.3; hard 0 -> 0.34
    assert conf == pytest.approx(0.34, abs=1e-4)


def test_calculate_resolve_confidence_legacy_time_denominator_fallback() -> None:
    """profile 未覆盖某类别时，回退到 profile 的 legacy_time_denominator."""
    profile = GenreRuntimeProfile(
        genre="test",
        setting_evaporation=SettingEvaporationProfile(
            legacy_time_denominator=200,
            time_denominators={},
        ),
    )
    conf = _calculate_resolve_confidence(
        _background_setting(last_mentioned=0),
        current_chapter=50,
        chapter_goal=None,
        runtime_profile=profile,
    )
    # time_factor = 1 - 50/200 = 0.75 -> 0.5*0.75 + 0.3*0.3 = 0.465
    assert conf == pytest.approx(0.465, abs=1e-4)


def test_calculate_resolve_confidence_none_profile_equals_legacy() -> None:
    """显式传 None 与省略参数结果一致."""
    row = _background_setting(last_mentioned=10)
    conf1 = _calculate_resolve_confidence(row, current_chapter=35, chapter_goal=None)
    conf2 = _calculate_resolve_confidence(
        row, current_chapter=35, chapter_goal=None, runtime_profile=None
    )
    assert conf1 == conf2


# ---------------------------------------------------------------------------
# SettingEvaporator
# ---------------------------------------------------------------------------

def test_setting_evaporator_stores_runtime_profile() -> None:
    profile = GenreRuntimeProfile(genre="xuanhuan")
    evaporator = SettingEvaporator(runtime_profile=profile)
    assert evaporator.runtime_profile is profile


def test_setting_evaporator_default_profile_is_none() -> None:
    evaporator = SettingEvaporator()
    assert evaporator.runtime_profile is None


@pytest.mark.asyncio
async def test_setting_evaporator_uses_profile_archive_thresholds() -> None:
    """profile 的 archive_thresholds 改变哪些 setting 被 archive."""
    profile = GenreRuntimeProfile(
        genre="test",
        setting_evaporation=SettingEvaporationProfile(
            archive_thresholds={"background": 0.50},
            legacy_archive_threshold=0.50,
        ),
    )
    evaporator = SettingEvaporator(runtime_profile=profile)

    # 0.34 < 0.50 -> 应被 archive
    active = [_background_setting(last_mentioned=0)]
    with patch.object(
        evaporator.repo, "list_active_with_tracking", new_callable=AsyncMock
    ) as mock_list, patch.object(
        evaporator.repo, "archive_by_confidence", new_callable=AsyncMock
    ) as mock_archive:
        mock_list.return_value = active
        mock_archive.return_value = 1
        archived = await evaporator.run("proj-1", current_chapter=50)

    assert archived == ["world.mist"]
    mock_archive.assert_awaited_once_with("proj-1", ["world.mist"])


@pytest.mark.asyncio
async def test_setting_evaporator_legacy_archive_threshold_with_none_profile() -> None:
    """无 profile 时 background 阈值使用 CONFIDENCE_ARCHIVE_THRESHOLDS['background']=0.15."""
    evaporator = SettingEvaporator()
    # 0.09 < 0.15 -> 应被 archive
    active = [_background_setting(last_mentioned=0)]
    with patch.object(
        evaporator.repo, "list_active_with_tracking", new_callable=AsyncMock
    ) as mock_list, patch.object(
        evaporator.repo, "archive_by_confidence", new_callable=AsyncMock
    ) as mock_archive:
        mock_list.return_value = active
        mock_archive.return_value = 1
        archived = await evaporator.run("proj-1", current_chapter=50)

    assert archived == ["world.mist"]


@pytest.mark.asyncio
async def test_setting_evaporator_does_not_archive_when_above_threshold() -> None:
    """profile 把阈值设得很低时，不应 archive."""
    profile = GenreRuntimeProfile(
        genre="test",
        setting_evaporation=SettingEvaporationProfile(
            archive_thresholds={"background": 0.01},
        ),
    )
    evaporator = SettingEvaporator(runtime_profile=profile)
    active = [_background_setting(last_mentioned=0)]
    with patch.object(
        evaporator.repo, "list_active_with_tracking", new_callable=AsyncMock
    ) as mock_list, patch.object(
        evaporator.repo, "archive_by_confidence", new_callable=AsyncMock
    ) as mock_archive:
        mock_list.return_value = active
        archived = await evaporator.run("proj-1", current_chapter=50)

    assert archived == []
    mock_archive.assert_not_awaited()


# ---------------------------------------------------------------------------
# _rank_foreshadowings
# ---------------------------------------------------------------------------

def _make_items() -> tuple[ForeshadowingItem, ForeshadowingItem]:
    due_item = ForeshadowingItem(
        foreshadowing_id="fs-due",
        description="due foreshadowing",
        planted_in_chapter=1,
        expected_resolve_chapter=20,
        status="due",
    )
    soon_item = ForeshadowingItem(
        foreshadowing_id="fs-soon",
        description="soon foreshadowing",
        planted_in_chapter=2,
        expected_resolve_chapter=7,
        status="planted",
    )
    return due_item, soon_item


def test_rank_foreshadowings_legacy_weights() -> None:
    """无 profile 时：2 章内回收的伏笔优先于 status=due."""
    due_item, soon_item = _make_items()
    ranked = _rank_foreshadowings(
        [due_item, soon_item],
        foreshadowing_due=[],
        current_chapter=5,
    )
    assert ranked[0].foreshadowing_id == "fs-soon"
    assert ranked[1].foreshadowing_id == "fs-due"


def test_rank_foreshadowings_profile_weights_swap_order() -> None:
    """profile 提高 urgency_due_soft 后，status=due 的伏笔排在 2 章内之前."""
    due_item, soon_item = _make_items()
    profile = GenreRuntimeProfile(
        genre="test",
        foreshadowing_evaporation=ForeshadowingEvaporationProfile(
            urgency_due_soft=5.0,
            urgency_within_2_bump=1.0,
        ),
    )
    ranked = _rank_foreshadowings(
        [due_item, soon_item],
        foreshadowing_due=[],
        current_chapter=5,
        runtime_profile=profile,
    )
    assert ranked[0].foreshadowing_id == "fs-due"
    assert ranked[1].foreshadowing_id == "fs-soon"


def test_rank_foreshadowings_due_list_bump_profile() -> None:
    """profile 的 urgency_due_bump 改变 due 列表中伏笔的排序."""
    due_list_item = ForeshadowingItem(
        foreshadowing_id="fs-listed",
        description="listed due",
        planted_in_chapter=1,
        expected_resolve_chapter=20,
        status="planted",
    )
    overdue_item = ForeshadowingItem(
        foreshadowing_id="fs-overdue",
        description="overdue",
        planted_in_chapter=1,
        expected_resolve_chapter=20,
        status="overdue",
    )

    # Legacy: due_list bump 3.0 > overdue 2.5 -> listed first
    ranked_legacy = _rank_foreshadowings(
        [overdue_item, due_list_item],
        foreshadowing_due=["fs-listed"],
        current_chapter=5,
    )
    assert ranked_legacy[0].foreshadowing_id == "fs-listed"

    # Profile: lower due bump below overdue bump -> overdue first
    profile = GenreRuntimeProfile(
        genre="test",
        foreshadowing_evaporation=ForeshadowingEvaporationProfile(
            urgency_due_bump=2.0,
            urgency_overdue_bump=4.0,
        ),
    )
    ranked_profile = _rank_foreshadowings(
        [overdue_item, due_list_item],
        foreshadowing_due=["fs-listed"],
        current_chapter=5,
        runtime_profile=profile,
    )
    assert ranked_profile[0].foreshadowing_id == "fs-overdue"


def test_rank_foreshadowings_none_profile_equals_legacy() -> None:
    """显式传 None 与省略参数结果一致."""
    due_item, soon_item = _make_items()
    ranked1 = _rank_foreshadowings(
        [due_item, soon_item], foreshadowing_due=[], current_chapter=5
    )
    ranked2 = _rank_foreshadowings(
        [due_item, soon_item],
        foreshadowing_due=[],
        current_chapter=5,
        runtime_profile=None,
    )
    assert [i.foreshadowing_id for i in ranked1] == [
        i.foreshadowing_id for i in ranked2
    ]


# ---------------------------------------------------------------------------
# Legacy constants preserved
# ---------------------------------------------------------------------------

def test_legacy_constants_unchanged() -> None:
    """172f 不删除/修改模块常量；无 profile 时行为与旧代码一致."""
    assert CONFIDENCE_ARCHIVE_THRESHOLDS["background"] == 0.15
    assert CONFIDENCE_ARCHIVE_THRESHOLD == 0.15
    assert CATEGORY_TIME_DENOMINATORS["background"] == 25
    assert TIME_DECAY_DENOMINATOR == 50
