"""Tests for CharacterStateRepository lifecycle methods (Task 085)."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db import (
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
    get_db,
)
from songyan.db.context_repo import CharacterStateRepository
from songyan.db.migrations import init_schema
from songyan.models import (
    ChapterVersion,
    Character,
    CharacterState,
    ProjectSetting,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.performance]


@pytest.fixture
async def state_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "state_lifecycle.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


async def _seed_project(project_id: str = "p1") -> None:
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="Lin Yuan",
        ),
        project_id,
    )


async def _seed_character(
    character_id: str,
    project_id: str = "p1",
    role_type: str = "supporting",
) -> None:
    await CharacterRepository().create(
        Character(
            character_id=character_id,
            project_id=project_id,
            name=character_id,
            role_type=role_type,
            personality_traits=["test"],
            goals=["test"],
            relationships={},
        )
    )


async def _seed_version(
    version_id: str,
    chapter_number: int = 1,
    project_id: str = "p1",
) -> None:
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter_number,
            version_number=1,
            content="test",
            word_count=100,
            scenes=[],
            generation_metadata={"source": "test"},
        )
    )


class TestCharacterStateLifecycle:
    async def _insert_state(
        self,
        character_id: str,
        version_id: str,
        field: str = "mood",
        value: str = "happy",
        lifecycle_status: str = "active",
    ) -> int:
        """Insert a character_state directly and return state_id."""
        state = CharacterState(
            character_id=character_id,
            field=field,
            value=value,
            source_version_id=version_id,
        )
        state_id = await CharacterRepository().add_state_snapshot(state)
        if lifecycle_status != "active":
            async with get_db() as conn:
                await conn.execute(
                    "UPDATE character_states SET lifecycle_status = ? WHERE state_id = ?",
                    (lifecycle_status, state_id),
                )
                await conn.commit()
        return state_id

    async def test_archive_stale_supporting_older_than_window(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("c1", role_type="supporting")
        await _seed_version("v1", chapter_number=1)
        await _seed_version("v2", chapter_number=10)

        await self._insert_state("c1", "v1")
        await self._insert_state("c1", "v2")

        repo = CharacterStateRepository()
        archived = await repo.archive_stale("p1", current_chapter=15, window=5)

        # Latest state for c1 is v2 (chapter 10), threshold = 15-5 = 10
        # 10 is NOT < 10, so not archived
        assert archived == 0

    async def test_archive_stale_supporting_below_threshold(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("c1", role_type="supporting")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("c1", "v1")

        repo = CharacterStateRepository()
        archived = await repo.archive_stale("p1", current_chapter=15, window=5)

        # threshold = 10, v1 chapter=1 < 10 → archived
        assert archived == 1

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM character_states WHERE character_id = ?",
                ("c1",),
            )
            row = await cursor.fetchone()
        assert row[0] == "dormant"

    async def test_archive_stale_skips_protagonist(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("hero", role_type="protagonist")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("hero", "v1")

        repo = CharacterStateRepository()
        archived = await repo.archive_stale("p1", current_chapter=15, window=5)

        assert archived == 0

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM character_states WHERE character_id = ?",
                ("hero",),
            )
            row = await cursor.fetchone()
        assert row[0] == "active"

    async def test_archive_stale_ignores_dormant(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("c1", role_type="supporting")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("c1", "v1", lifecycle_status="dormant")

        repo = CharacterStateRepository()
        archived = await repo.archive_stale("p1", current_chapter=15, window=5)

        assert archived == 0

    async def test_archive_very_stale_dormant_below_threshold(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("c1", role_type="supporting")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("c1", "v1", lifecycle_status="dormant")

        repo = CharacterStateRepository()
        archived = await repo.archive_very_stale("p1", current_chapter=20, window=15)

        # threshold = 5, v1 chapter=1 < 5 → archived
        assert archived == 1

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM character_states WHERE character_id = ?",
                ("c1",),
            )
            row = await cursor.fetchone()
        assert row[0] == "archived"

    async def test_archive_very_stale_skips_active(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("c1", role_type="supporting")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("c1", "v1", lifecycle_status="active")

        repo = CharacterStateRepository()
        archived = await repo.archive_very_stale("p1", current_chapter=20, window=15)

        assert archived == 0

    async def test_list_recent_excludes_dormant_supporting(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("c1", role_type="supporting")
        await _seed_character("hero", role_type="protagonist")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("c1", "v1", lifecycle_status="dormant")
        await self._insert_state("hero", "v1", lifecycle_status="dormant")

        repo = CharacterStateRepository()
        states = await repo.list_recent_by_project("p1")

        # hero is protagonist → included despite dormant
        # c1 is supporting + dormant → excluded
        assert len(states) == 1
        assert states[0].character_id == "hero"

    async def test_list_recent_includes_active_supporting(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("c1", role_type="supporting")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("c1", "v1", lifecycle_status="active")

        repo = CharacterStateRepository()
        states = await repo.list_recent_by_project("p1")

        assert len(states) == 1
        assert states[0].character_id == "c1"

    # -------------------------------------------------------------------------
    # Task 109: window calibration + antagonist protection
    # -------------------------------------------------------------------------

    async def test_archive_stale_default_window_30(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("c1", role_type="supporting")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("c1", "v1")

        repo = CharacterStateRepository()
        # default window = 30, threshold = 50 - 30 = 20
        archived = await repo.archive_stale("p1", current_chapter=50)
        assert archived == 1

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM character_states WHERE character_id = ?",
                ("c1",),
            )
            row = await cursor.fetchone()
        assert row[0] == "dormant"

    async def test_archive_stale_protects_antagonist(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("villain", role_type="antagonist")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("villain", "v1")

        repo = CharacterStateRepository()
        archived = await repo.archive_stale("p1", current_chapter=50)
        assert archived == 0

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM character_states WHERE character_id = ?",
                ("villain",),
            )
            row = await cursor.fetchone()
        assert row[0] == "active"

    async def test_archive_very_stale_default_window_60(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("c1", role_type="supporting")
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("c1", "v1", lifecycle_status="dormant")

        repo = CharacterStateRepository()
        # default window = 60, threshold = 70 - 60 = 10
        archived = await repo.archive_very_stale("p1", current_chapter=70)
        assert archived == 1

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM character_states WHERE character_id = ?",
                ("c1",),
            )
            row = await cursor.fetchone()
        assert row[0] == "archived"

    # -------------------------------------------------------------------------
    # Task 109: archive_overflow cap enforcement
    # -------------------------------------------------------------------------

    async def test_archive_overflow_enforces_cap(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("hero", role_type="protagonist")
        await _seed_version("v_hero", chapter_number=50)
        await self._insert_state("hero", "v_hero")

        for i in range(1, 13):
            cid = f"c{i}"
            await _seed_character(cid, role_type="supporting")
            vid = f"v{i}"
            await _seed_version(vid, chapter_number=i)
            await self._insert_state(cid, vid)

        repo = CharacterStateRepository()
        # 13 active (1 hero + 12 supporting), cap=10 → 3 should be archived
        archived = await repo.archive_overflow("p1", current_chapter=50, cap=10)
        assert archived == 3

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT character_id FROM character_states WHERE lifecycle_status = 'active'",
            )
            rows = await cursor.fetchall()
        active_ids = {r[0] for r in rows}
        assert "hero" in active_ids
        assert len(active_ids) == 10

    async def test_archive_overflow_sorts_by_last_appeared(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("hero", role_type="protagonist")
        await _seed_version("v_hero", chapter_number=20)
        await self._insert_state("hero", "v_hero")

        for i, ch in enumerate([1, 5, 10], start=1):
            cid = f"c{i}"
            await _seed_character(cid, role_type="supporting")
            vid = f"v{i}"
            await _seed_version(vid, chapter_number=ch)
            await self._insert_state(cid, vid)

        repo = CharacterStateRepository()
        # 4 active, cap=2 → 2 should be archived (c1 at ch1, c2 at ch5)
        archived = await repo.archive_overflow("p1", current_chapter=20, cap=2)
        assert archived == 2

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT character_id, lifecycle_status FROM character_states",
            )
            rows = await cursor.fetchall()
        status_by_id = {r[0]: r[1] for r in rows}
        assert status_by_id["hero"] == "active"
        assert status_by_id["c1"] == "dormant"
        assert status_by_id["c2"] == "dormant"
        assert status_by_id["c3"] == "active"

    async def test_archive_overflow_respects_antagonist(self, state_db: Path) -> None:
        await _seed_project("p1")
        await _seed_character("hero", role_type="protagonist")
        await _seed_character("villain", role_type="antagonist")
        await _seed_version("v_hero", chapter_number=50)
        await _seed_version("v_villain", chapter_number=11)
        await self._insert_state("hero", "v_hero")
        await self._insert_state("villain", "v_villain")

        for i in range(1, 11):
            cid = f"c{i}"
            await _seed_character(cid, role_type="supporting")
            vid = f"v{i}"
            await _seed_version(vid, chapter_number=i)
            await self._insert_state(cid, vid)

        repo = CharacterStateRepository()
        # 12 active (1 hero + 1 villain + 10 supporting), cap=10 → 2 supporting archived
        archived = await repo.archive_overflow("p1", current_chapter=50, cap=10)
        assert archived == 2

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT character_id, lifecycle_status FROM character_states",
            )
            rows = await cursor.fetchall()
        status_by_id = {r[0]: r[1] for r in rows}
        assert status_by_id["hero"] == "active"
        assert status_by_id["villain"] == "active"

    # -------------------------------------------------------------------------
    # Task 109 补充：功能性角色分层退场 + 动态 cap
    # -------------------------------------------------------------------------

    async def test_archive_stale_functional_evicts_tool_characters(
        self, state_db: Path
    ) -> None:
        await _seed_project("p1")
        await CharacterRepository().create(
            Character(
                character_id="npc",
                project_id="p1",
                name="NPC",
                role_type="supporting",
                personality_traits=[],
                goals=[],
                relationships={},
            )
        )
        await _seed_version("v1", chapter_number=1)

        await self._insert_state("npc", "v1")
        # npc has empty goals/relationships -> functional

        repo = CharacterStateRepository()
        # window=8, threshold = 15 - 8 = 7, chapter 1 < 7 -> dormant
        archived = await repo.archive_stale_functional(
            "p1", current_chapter=15
        )
        assert archived == 1

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM character_states WHERE character_id = ?",
                ("npc",),
            )
            row = await cursor.fetchone()
        assert row[0] == "dormant"

    async def test_archive_stale_functional_preserves_core_supporting(
        self, state_db: Path
    ) -> None:
        await _seed_project("p1")
        await CharacterRepository().create(
            Character(
                character_id="sidekick",
                project_id="p1",
                name="Sidekick",
                role_type="supporting",
                personality_traits=[],
                goals=["protect hero"],
                relationships={"hero": "ally"},
            )
        )
        await _seed_version("v1", chapter_number=1)
        await self._insert_state("sidekick", "v1")

        repo = CharacterStateRepository()
        # sidekick has goals/relationships -> core, not affected by functional archive
        archived = await repo.archive_stale_functional(
            "p1", current_chapter=15
        )
        assert archived == 0

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM character_states WHERE character_id = ?",
                ("sidekick",),
            )
            row = await cursor.fetchone()
        assert row[0] == "active"

    async def test_archive_overflow_prioritizes_functional(
        self, state_db: Path
    ) -> None:
        await _seed_project("p1")
        await _seed_character("hero", role_type="protagonist")
        await _seed_version("v_hero", chapter_number=50)
        await self._insert_state("hero", "v_hero")

        # core supporting: appeared at chapter 1 (long ago)
        await CharacterRepository().create(
            Character(
                character_id="sidekick",
                project_id="p1",
                name="Sidekick",
                role_type="supporting",
                personality_traits=[],
                goals=["protect hero"],
                relationships={"hero": "ally"},
            )
        )
        await _seed_version("v_sidekick", chapter_number=1)
        await self._insert_state("sidekick", "v_sidekick")

        # functional supporting: appeared at chapter 10 (more recent)
        await CharacterRepository().create(
            Character(
                character_id="npc",
                project_id="p1",
                name="NPC",
                role_type="supporting",
                personality_traits=[],
                goals=[],
                relationships={},
            )
        )
        await _seed_version("v_npc", chapter_number=10)
        await self._insert_state("npc", "v_npc")

        repo = CharacterStateRepository()
        # 3 active, cap=2 -> 1 should be archived
        # functional (npc) should be evicted first even though more recent
        archived = await repo.archive_overflow("p1", current_chapter=50, cap=2)
        assert archived == 1

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT character_id, lifecycle_status FROM character_states",
            )
            rows = await cursor.fetchall()
        status_by_id = {r[0]: r[1] for r in rows}
        assert status_by_id["hero"] == "active"
        assert status_by_id["sidekick"] == "active"
        assert status_by_id["npc"] == "dormant"
