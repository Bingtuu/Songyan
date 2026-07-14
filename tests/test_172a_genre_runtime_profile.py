"""Task 172a.2/172a.3: GenreRuntimeProfile model + migration + loader tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.connection import get_db
from songyan.db.genre_runtime_profile_repo import (
    FALLBACK_GENRE,
    GenreRuntimeProfileRepository,
    load_profile,
    load_profile_from_registry,
)
from songyan.models import GenreRuntimeProfile

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
    # DB 无记录 -> 回退注册表 xuanhuan (base_budget=12000)
    reg = await load_profile("xuanhuan")
    assert reg.base_budget == 12000

    # 写 DB 覆盖 -> DB 优先
    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", base_budget=15000))
    db_first = await load_profile("xuanhuan")
    assert db_first.base_budget == 15000


async def test_load_profile_unknown_genre_returns_scifi(test_db: Path) -> None:
    p = await load_profile("totally_unknown")
    assert p.genre == FALLBACK_GENRE
    assert p.base_budget == 8000


@pytest.mark.parametrize("genre", ["scifi", "xuanhuan", "wuxia", "urban"])
def test_all_v8_target_genres_loadable(genre: str) -> None:
    p = load_profile_from_registry(genre)
    assert p.base_budget >= 8000
