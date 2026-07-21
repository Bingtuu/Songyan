"""Task 172a.2/172a.3/172i: GenreRuntimeProfile model + migration + loader tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from songyan.db.connection import get_db
from songyan.db.genre_runtime_profile_repo import (
    FALLBACK_GENRE,
    GenreRuntimeProfileRepository,
    load_profile,
    load_profile_from_registry,
)
from songyan.models import GenreRuntimeProfile, SettingEvaporationProfile

# --- model ---------------------------------------------------------------


def test_default_profile_is_sci_fi_baseline() -> None:
    profile = GenreRuntimeProfile(genre="scifi")
    assert profile.base_budget == 8000
    assert profile.ramp_per_chapter == 250
    assert profile.min_budget == 2000


def test_two_distinct_ratio_fields() -> None:
    p = GenreRuntimeProfile(genre="scifi")
    # 数值巧合都是 1.3，但是两个独立字段
    assert p.emergency_halt_ratio == 1.3
    assert p.hard_enforce_ratio == 1.3
    p2 = GenreRuntimeProfile(genre="x", emergency_halt_ratio=1.5)
    assert p2.emergency_halt_ratio == 1.5
    assert p2.hard_enforce_ratio == 1.3  # 不受影响


def test_partition_ratios_are_prunable_partitions_only() -> None:
    p = GenreRuntimeProfile(genre="scifi")
    assert set(p.partition_ratios) == {
        "character_states",
        "recent_plot",
        "soft_references",
        "foreshadowing",
    }


def test_dynamic_budget_matches_assembler_formula() -> None:
    p = GenreRuntimeProfile(genre="scifi")
    # 与 _assemblers._dynamic_budget 等价：Ch8 = 8000 + 8*250 = 10000
    assert p.dynamic_budget(8) == 10000
    assert p.dynamic_budget(100) == 33000


def test_xuanhuan_registry_has_higher_base_budget() -> None:
    xuanhuan = load_profile_from_registry("xuanhuan")
    scifi = load_profile_from_registry("scifi")
    # 真实杠杆是 base_budget（不可裁核心溢出），不是分区权重
    assert xuanhuan.base_budget > scifi.base_budget


def test_urban_registry_base_budget_is_ch25_calibrated() -> None:
    """187.p: urban Ch19 ContextEmergency requires a higher registry baseline."""
    urban = load_profile_from_registry("urban")

    assert urban.base_budget == 14000


def test_xuanhuan_registry_loads_more_character_state_for_consistency() -> None:
    xuanhuan = load_profile_from_registry("xuanhuan")
    scifi = load_profile_from_registry("scifi")
    assert xuanhuan.max_character_states == 8
    assert xuanhuan.max_character_states > scifi.max_character_states


def test_placeholder_strategy_switches_removed() -> None:
    """arc_summarization_enabled / outline_dimming_enabled 已从模型移除."""
    p = GenreRuntimeProfile(genre="scifi")
    assert not hasattr(p, "arc_summarization_enabled")
    assert not hasattr(p, "outline_dimming_enabled")


# --- registry fallback ---------------------------------------------------


def test_registry_unknown_genre_falls_back_to_scifi() -> None:
    unknown = load_profile_from_registry("nonexistent_genre")
    scifi = load_profile_from_registry(FALLBACK_GENRE)
    assert unknown.base_budget == scifi.base_budget
    assert unknown.genre == FALLBACK_GENRE


def test_registry_none_genre_falls_back() -> None:
    p = load_profile_from_registry(None)
    assert p.genre == FALLBACK_GENRE


# --- migration + repo ----------------------------------------------------


async def test_migration_creates_table(test_db: Path) -> None:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='genre_runtime_profiles'"
        )
        row = await cursor.fetchone()
    assert row is not None


async def test_repo_upsert_and_get_roundtrip(test_db: Path) -> None:
    repo = GenreRuntimeProfileRepository()
    profile = GenreRuntimeProfile(genre="xuanhuan", base_budget=13000)
    await repo.upsert(profile)
    loaded = await repo.get("xuanhuan")
    assert loaded is not None
    assert loaded.base_budget == 13000

    # 幂等 upsert：更新已有记录不报错，list 中仍只有一条 xuanhuan
    profile.base_budget = 14000
    await repo.upsert(profile)
    loaded2 = await repo.get("xuanhuan")
    assert loaded2 is not None
    assert loaded2.base_budget == 14000
    all_profiles = await repo.list_all()
    assert sum(1 for p in all_profiles if p.genre == "xuanhuan") == 1


async def test_repo_get_missing_returns_none(test_db: Path) -> None:
    repo = GenreRuntimeProfileRepository()
    assert await repo.get("wuxia") is None


async def test_load_profile_db_priority_then_registry(test_db: Path) -> None:
    repo = GenreRuntimeProfileRepository()
    # DB 无记录 -> 回退注册表 xuanhuan (base_budget=15000, 172a.7 calibrated)
    reg = await load_profile("xuanhuan")
    assert reg.base_budget == 15000

    # 写 DB 覆盖 -> DB 字段级覆盖注册表基线
    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", base_budget=18000))
    db_first = await load_profile("xuanhuan")
    assert db_first.base_budget == 18000
    # 未覆盖字段保留注册表基线值
    assert db_first.foreshadowing_horizon_floor == reg.foreshadowing_horizon_floor


async def test_load_profile_uses_registry_as_base_and_db_as_override(test_db: Path) -> None:
    """DB 只覆盖显式字段，其余保留代码注册表体裁默认值."""
    repo = GenreRuntimeProfileRepository()
    registry_xuanhuan = load_profile_from_registry("xuanhuan")
    assert registry_xuanhuan.foreshadowing_horizon_floor == 48

    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", base_budget=18000))
    loaded = await load_profile("xuanhuan")

    assert loaded.base_budget == 18000  # DB 覆盖
    assert loaded.foreshadowing_horizon_floor == registry_xuanhuan.foreshadowing_horizon_floor
    assert loaded.genre == "xuanhuan"


async def test_load_profile_overrides_nested_model_whole(test_db: Path) -> None:
    """DB 提供嵌套子模型时整体替换，不提供时保留注册表子模型."""
    repo = GenreRuntimeProfileRepository()
    registry_xuanhuan = load_profile_from_registry("xuanhuan")

    # 只覆盖顶层字段，不碰 setting_evaporation -> 保留注册表子模型
    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", base_budget=18000))
    loaded = await load_profile("xuanhuan")
    assert loaded.setting_evaporation == registry_xuanhuan.setting_evaporation

    # 覆盖整个 setting_evaporation -> 整体替换
    new_evap = SettingEvaporationProfile(
        legacy_archive_threshold=0.01, legacy_time_denominator=99
    )
    await repo.upsert(
        GenreRuntimeProfile(
            genre="xuanhuan",
            base_budget=18000,
            setting_evaporation=new_evap,
        )
    )
    loaded2 = await load_profile("xuanhuan")
    assert loaded2.setting_evaporation.legacy_time_denominator == 99
    assert loaded2.setting_evaporation.legacy_archive_threshold == 0.01
    assert loaded2.base_budget == 18000


async def test_load_profile_db_unavailable_falls_back_to_registry(test_db: Path) -> None:
    """DB 异常时回退注册表基线，不阻断生成."""
    from unittest.mock import AsyncMock, patch

    with patch.object(
        GenreRuntimeProfileRepository,
        "get",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db down"),
    ):
        loaded = await load_profile("xuanhuan")

    assert loaded.genre == "xuanhuan"
    assert loaded.base_budget == load_profile_from_registry("xuanhuan").base_budget


async def test_old_db_record_with_removed_fields_deserializes(test_db: Path) -> None:
    """DB 中仍含已移除字段的旧 profile_json 可正常加载（extra=ignore）."""
    old_payload = {
        "genre": "xuanhuan",
        "base_budget": 15000,
        "arc_summarization_enabled": True,
        "outline_dimming_enabled": True,
    }
    async with get_db() as conn:
        await conn.execute(
            "INSERT INTO genre_runtime_profiles (genre, version, profile_json) VALUES (?, ?, ?)",
            ("xuanhuan", "172a.2", json.dumps(old_payload)),
        )
        await conn.commit()

    loaded = await load_profile("xuanhuan")
    assert loaded.base_budget == 15000
    assert not hasattr(loaded, "arc_summarization_enabled")
    assert not hasattr(loaded, "outline_dimming_enabled")


async def test_load_profile_unknown_genre_returns_scifi(test_db: Path) -> None:
    p = await load_profile("totally_unknown")
    assert p.genre == FALLBACK_GENRE
    assert p.base_budget == 8000


@pytest.mark.parametrize("genre", ["scifi", "xuanhuan", "wuxia", "urban"])
def test_all_v8_target_genres_loadable(genre: str) -> None:
    p = load_profile_from_registry(genre)
    assert p.base_budget >= 8000
