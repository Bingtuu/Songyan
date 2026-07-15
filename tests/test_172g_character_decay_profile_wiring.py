"""Task 172g: Character decay archive windows are wired from GenreRuntimeProfile."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from songyan.db.context_repo import CharacterStateRepository
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models import CharacterDecayProfile, GenreRuntimeProfile


def _build_test_profile(**overrides) -> GenreRuntimeProfile:
    base = load_profile_from_registry("scifi")
    data = base.model_dump(mode="json")
    data.update(overrides)
    return GenreRuntimeProfile.model_validate(data)


@pytest.mark.asyncio
async def test_archive_stale_uses_profile_dormant_window(test_db: Path) -> None:
    """profile 修改 dormant_window 后，archive_stale 使用的阈值变化."""
    repo = CharacterStateRepository()
    profile = _build_test_profile(
        character_decay=CharacterDecayProfile(dormant_window=5)
    )

    called_threshold: int | None = None
    original_execute = aiosqlite.Connection.execute

    async def spy_execute(self, sql, parameters=None):
        nonlocal called_threshold
        if "cv.chapter_number < ?" in sql and parameters is not None:
            called_threshold = parameters[-1]
        return await original_execute(self, sql, parameters)

    aiosqlite.Connection.execute = spy_execute
    try:
        await repo.archive_stale(
            project_id="test-project",
            current_chapter=100,
            runtime_profile=profile,
        )
    finally:
        aiosqlite.Connection.execute = original_execute

    assert called_threshold == 95  # 100 - 5


@pytest.mark.asyncio
async def test_archive_very_stale_uses_profile_archive_window(test_db: Path) -> None:
    """profile 修改 archive_window 后，archive_very_stale 使用的阈值变化."""
    repo = CharacterStateRepository()
    profile = _build_test_profile(
        character_decay=CharacterDecayProfile(archive_window=10)
    )

    called_threshold: int | None = None
    original_execute = aiosqlite.Connection.execute

    async def spy_execute(self, sql, parameters=None):
        nonlocal called_threshold
        if "cv.chapter_number < ?" in sql and parameters is not None:
            called_threshold = parameters[-1]
        return await original_execute(self, sql, parameters)

    aiosqlite.Connection.execute = spy_execute
    try:
        await repo.archive_very_stale(
            project_id="test-project",
            current_chapter=100,
            runtime_profile=profile,
        )
    finally:
        aiosqlite.Connection.execute = original_execute

    assert called_threshold == 90  # 100 - 10


@pytest.mark.asyncio
async def test_archive_stale_functional_uses_profile_functional_window(
    test_db: Path,
) -> None:
    """profile 修改 functional_window 后，archive_stale_functional 使用的阈值变化."""
    repo = CharacterStateRepository()
    profile = _build_test_profile(
        character_decay=CharacterDecayProfile(functional_window=3)
    )

    called_threshold: int | None = None
    original_execute = aiosqlite.Connection.execute

    async def spy_execute(self, sql, parameters=None):
        nonlocal called_threshold
        if "cv.chapter_number < ?" in sql and parameters is not None:
            called_threshold = parameters[-1]
        return await original_execute(self, sql, parameters)

    aiosqlite.Connection.execute = spy_execute
    try:
        await repo.archive_stale_functional(
            project_id="test-project",
            current_chapter=100,
            runtime_profile=profile,
        )
    finally:
        aiosqlite.Connection.execute = original_execute

    assert called_threshold == 97  # 100 - 3


def test_scifi_profile_defaults_equal_legacy_constants() -> None:
    """scifi profile 默认值必须与旧常量等价."""
    scifi = load_profile_from_registry("scifi")
    assert scifi.character_decay.dormant_window == 30
    assert scifi.character_decay.archive_window == 60
    assert scifi.character_decay.functional_window == 8


@pytest.mark.asyncio
async def test_no_profile_falls_back_to_legacy_windows(test_db: Path) -> None:
    """无 profile 时 archive_stale 使用旧默认 30."""
    repo = CharacterStateRepository()

    called_threshold: int | None = None
    original_execute = aiosqlite.Connection.execute

    async def spy_execute(self, sql, parameters=None):
        nonlocal called_threshold
        if "cv.chapter_number < ?" in sql and parameters is not None:
            called_threshold = parameters[-1]
        return await original_execute(self, sql, parameters)

    aiosqlite.Connection.execute = spy_execute
    try:
        await repo.archive_stale(
            project_id="test-project",
            current_chapter=100,
            runtime_profile=None,
        )
    finally:
        aiosqlite.Connection.execute = original_execute

    assert called_threshold == 70  # 100 - 30
