"""Task 172a.5: gate threshold sourced from GenreRuntimeProfile.

Verifies the profile carries a distinct emergency_halt_ratio and that a
GateConfig can be overridden by it (the mechanism run_project_pipeline uses
after genre is known, fixing the build-ordering issue).
"""

from __future__ import annotations

from songyan.db.genre_runtime_profile_repo import (
    GenreRuntimeProfileRepository,
    load_profile,
)
from songyan.models import GateConfig, GenreRuntimeProfile


def test_gate_config_override_by_profile_ratio() -> None:
    gate_config = GateConfig.for_mode("enforce")
    assert gate_config.context_emergency_budget_ratio_threshold == 1.3

    # 模拟 run_project_pipeline 的覆盖逻辑
    profile = GenreRuntimeProfile(genre="xuanhuan", emergency_halt_ratio=1.5)
    if (
        profile.emergency_halt_ratio
        != gate_config.context_emergency_budget_ratio_threshold
    ):
        gate_config = gate_config.model_copy(
            update={
                "context_emergency_budget_ratio_threshold": profile.emergency_halt_ratio
            }
        )
    assert gate_config.context_emergency_budget_ratio_threshold == 1.5


def test_scifi_profile_ratio_is_noop_override() -> None:
    # scifi profile 阈值 = 1.3 = GateConfig 默认，覆盖为 no-op（行为不变）
    gate_config = GateConfig.for_mode("enforce")
    from songyan.db.genre_runtime_profile_repo import load_profile_from_registry

    scifi = load_profile_from_registry("scifi")
    assert scifi.emergency_halt_ratio == gate_config.context_emergency_budget_ratio_threshold


async def test_profile_ratio_from_db_applies(test_db) -> None:
    repo = GenreRuntimeProfileRepository()
    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", emergency_halt_ratio=1.6))
    loaded = await load_profile("xuanhuan")
    assert loaded.emergency_halt_ratio == 1.6
