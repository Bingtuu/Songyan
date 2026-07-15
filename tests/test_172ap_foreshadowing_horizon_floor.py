"""Task 172a.p: per-genre foreshadowing horizon-floor clamp tests.

Proves the S-dimension fix: plant-time expected_resolve_chapter is clamped to
>= planted + genre horizon_floor (only raised, never lowered), scifi (floor=0)
is a strict no-op, and the floor is wired through apply_settlement.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.agents.settlement_extractor._apply import (
    _clamp_foreshadowing_horizon,
    apply_settlement,
)
from songyan.db import ProjectRepository
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.db.migrations import init_schema
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import GenreRuntimeProfile, ProjectSetting
from songyan.models.settlement import ForeshadowingUpdate, StateSettlement

# --- pure clamp helper ---------------------------------------------------


def test_clamp_raises_short_horizon() -> None:
    # planted Ch4, LLM said Ch6 (horizon 2), floor 12 -> Ch16
    assert _clamp_foreshadowing_horizon(6, planted_in_chapter=4, horizon_floor=12) == 16


def test_clamp_keeps_longer_horizon() -> None:
    # LLM already gave horizon 15 (Ch4 -> Ch19) > floor 12 -> unchanged
    assert _clamp_foreshadowing_horizon(19, planted_in_chapter=4, horizon_floor=12) == 19


def test_clamp_floor_zero_is_noop() -> None:
    # scifi default floor=0 -> never mutate
    assert _clamp_foreshadowing_horizon(6, planted_in_chapter=4, horizon_floor=0) == 6
    assert _clamp_foreshadowing_horizon(6, planted_in_chapter=4, horizon_floor=-3) == 6


def test_clamp_none_horizon_passthrough() -> None:
    # unknown horizon stays None regardless of floor
    assert _clamp_foreshadowing_horizon(None, planted_in_chapter=4, horizon_floor=12) is None


def test_clamp_exact_floor_boundary() -> None:
    # horizon exactly at floor -> unchanged
    assert _clamp_foreshadowing_horizon(16, planted_in_chapter=4, horizon_floor=12) == 16


def test_clamp_172bp_long_window_floor() -> None:
    # 172b.p: Ch100 xuanhuan uses a longer floor; still only raises short horizons.
    assert _clamp_foreshadowing_horizon(16, planted_in_chapter=4, horizon_floor=48) == 52
    assert _clamp_foreshadowing_horizon(60, planted_in_chapter=4, horizon_floor=48) == 60


# --- profile field + registry wiring -------------------------------------


def test_scifi_horizon_floor_is_zero() -> None:
    assert GenreRuntimeProfile(genre="scifi").foreshadowing_horizon_floor == 0
    assert load_profile_from_registry("scifi").foreshadowing_horizon_floor == 0


def test_xuanhuan_registry_has_horizon_floor() -> None:
    assert load_profile_from_registry("xuanhuan").foreshadowing_horizon_floor == 48


def test_wuxia_registry_has_horizon_floor() -> None:
    # 172a.p: wuxia horizon 比 xuanhuan 更短，同机制设 floor=12（172c 准备）
    assert load_profile_from_registry("wuxia").foreshadowing_horizon_floor == 12


def test_unknown_genre_floor_falls_back_to_scifi() -> None:
    # no-profile genres must behave like scifi (floor 0 -> no clamp)
    assert load_profile_from_registry("nonexistent").foreshadowing_horizon_floor == 0


# --- end-to-end apply_settlement -----------------------------------------


@pytest.fixture
async def app_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "app.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


async def _seed(project_id: str, version_id: str, chapter_number: int) -> None:
    from songyan.db.connection import get_db

    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", mode_id="webnovel", protagonist_name="陆沉"),
        project_id,
    )
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES (?, ?, ?, ?, ?)""",
            (version_id, project_id, chapter_number, 1, "accepted"),
        )
        await conn.commit()


def _settlement_planting(expected: int) -> StateSettlement:
    return StateSettlement(
        chapter_number=4,
        validation_status="valid",
        foreshadowing_updates=[
            ForeshadowingUpdate(
                operation="plant",
                description="短 horizon 伏笔",
                expected_resolve_chapter=expected,
                source_version_id="v1",
            )
        ],
    )


async def test_apply_settlement_clamps_with_floor(app_db: Path) -> None:
    from songyan.db.connection import get_db

    await _seed("p1", "v1", 4)
    # LLM planted at Ch4 with expected Ch6 (horizon 2); floor 12 -> Ch16
    async with get_db() as conn:
        await apply_settlement(
            settlement=_settlement_planting(6),
            project_id="p1",
            chapter_number=4,
            version_id="v1",
            conn=conn,
            foreshadowing_horizon_floor=12,
        )
        await conn.commit()
    active = await ForeshadowingRepository().list_active("p1")
    assert len(active) == 1
    assert active[0].expected_resolve_chapter == 16


async def test_apply_settlement_floor_zero_preserves_llm_horizon(app_db: Path) -> None:
    from songyan.db.connection import get_db

    await _seed("p1", "v1", 4)
    async with get_db() as conn:
        await apply_settlement(
            settlement=_settlement_planting(6),
            project_id="p1",
            chapter_number=4,
            version_id="v1",
            conn=conn,
            foreshadowing_horizon_floor=0,
        )
        await conn.commit()
    active = await ForeshadowingRepository().list_active("p1")
    assert len(active) == 1
    # scifi behavior: expected stays exactly what the LLM said
    assert active[0].expected_resolve_chapter == 6
