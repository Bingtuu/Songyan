"""Repository layer tests."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from songyan.db import (
    ChapterGoalRepository,
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
    get_db,
)
from songyan.db.migrations import init_schema
from songyan.models import (
    ChapterGoal,
    ChapterHead,
    ChapterVersion,
    Character,
    CharacterState,
    ProjectSetting,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def repo_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point repository get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "repo.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


def _project(title: str = "Test Novel") -> ProjectSetting:
    return ProjectSetting(
        title=title,
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="Lin Feng",
        protagonist_background="fallen clan",
        core_hook="return to the peak",
        target_reader_expectation="fast growth",
        taboos=["ntr"],
        target_word_count=200_000,
        tone="热血",
        reference_works=["classic"],
    )


async def _seed_project(project_id: str = "p1") -> None:
    await ProjectRepository().create(_project(), project_id)


async def _seed_character(character_id: str = "c1", project_id: str = "p1") -> None:
    await CharacterRepository().create(
        Character(
            character_id=character_id,
            project_id=project_id,
            name="Lin Feng",
            personality_traits=["stubborn"],
            goals=["protect family"],
            relationships={"master": "Elder Wang"},
        )
    )


async def _seed_version(
    version_id: str = "v1",
    project_id: str = "p1",
    version_number: int = 1,
    parent_version_id: str | None = None,
) -> None:
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=1,
            version_number=version_number,
            content=f"content {version_number}",
            word_count=100 * version_number,
            scenes=[{"scene": version_number}],
            generation_metadata={"source": "test"},
            parent_version_id=parent_version_id,
        )
    )


class TestProjectRepository:
    async def test_create_and_get_round_trip(self, repo_db: Path) -> None:
        await ProjectRepository().create(_project(), "p1")

        project = await ProjectRepository().get("p1")

        assert project is not None
        assert project.title == "Test Novel"
        assert project.taboos == ["ntr"]
        assert project.reference_works == ["classic"]

    async def test_get_missing_returns_none(self, repo_db: Path) -> None:
        assert await ProjectRepository().get("missing") is None

    async def test_json_defaults_stored_as_arrays(self, repo_db: Path) -> None:
        await ProjectRepository().create(
            ProjectSetting(genre_id="xuanhuan", protagonist_name="Lin Feng"),
            "p1",
        )

        async with get_db() as conn:
            cursor = await conn.execute("SELECT taboos, reference_works FROM projects")
            row = await cursor.fetchone()

        assert row == ("[]", "[]")

    async def test_create_with_seed_fields_round_trip(self, repo_db: Path) -> None:
        project = ProjectSetting(
            genre_id="scifi",
            protagonist_name="Zhang",
            estimated_chapters=50,
            words_per_chapter=3500,
            story_structure="three_act",
            arc_boundaries_auto=True,
            sub_genre_id="cosmic_horror",
        )
        await ProjectRepository().create(project, "p1")

        saved = await ProjectRepository().get("p1")
        assert saved is not None
        assert saved.estimated_chapters == 50
        assert saved.words_per_chapter == 3500
        assert saved.story_structure == "three_act"
        assert saved.arc_boundaries_auto is True
        assert saved.sub_genre_id == "cosmic_horror"

    async def test_create_with_defaults_round_trip(self, repo_db: Path) -> None:
        project = ProjectSetting(genre_id="scifi", protagonist_name="Zhang")
        await ProjectRepository().create(project, "p1")

        saved = await ProjectRepository().get("p1")
        assert saved is not None
        assert saved.estimated_chapters == 30
        assert saved.words_per_chapter == 3000
        assert saved.story_structure == "free"
        assert saved.arc_boundaries_auto is False
        assert saved.sub_genre_id is None

    async def test_update_seed_config(self, repo_db: Path) -> None:
        await ProjectRepository().create(_project(), "p1")

        await ProjectRepository().update_seed_config(
            "p1",
            estimated_chapters=60,
            words_per_chapter=4000,
            story_structure="serial",
            sub_genre_id="space_opera",
            arc_boundaries_auto=True,
            arc_boundaries=[20, 40],
        )

        saved = await ProjectRepository().get("p1")
        assert saved is not None
        assert saved.estimated_chapters == 60
        assert saved.words_per_chapter == 4000
        assert saved.story_structure == "serial"
        assert saved.sub_genre_id == "space_opera"
        assert saved.arc_boundaries_auto is True
        assert saved.arc_boundaries == [20, 40]

    async def test_update_seed_config_partial(self, repo_db: Path) -> None:
        project = ProjectSetting(
            genre_id="scifi",
            protagonist_name="Zhang",
            estimated_chapters=30,
            words_per_chapter=3000,
        )
        await ProjectRepository().create(project, "p1")

        await ProjectRepository().update_seed_config(
            "p1",
            estimated_chapters=45,
        )

        saved = await ProjectRepository().get("p1")
        assert saved is not None
        assert saved.estimated_chapters == 45
        assert saved.words_per_chapter == 3000
        assert saved.story_structure == "free"

    async def test_update_seed_config_noop(self, repo_db: Path) -> None:
        await ProjectRepository().create(_project(), "p1")

        # 空更新不应报错
        await ProjectRepository().update_seed_config("p1")

        saved = await ProjectRepository().get("p1")
        assert saved is not None
        assert saved.title == "Test Novel"


class TestMigration:
    async def test_migration_adds_seed_columns(self, repo_db: Path) -> None:
        """验证 Phase 8a 迁移已添加所有列."""
        async with get_db() as conn:
            cursor = await conn.execute("PRAGMA table_info(projects)")
            cols = {row[1] for row in await cursor.fetchall()}

        assert "estimated_chapters" in cols
        assert "words_per_chapter" in cols
        assert "story_structure" in cols
        assert "sub_genre_id" in cols
        assert "arc_boundaries_auto" in cols

    async def test_migration_idempotent(self, repo_db: Path) -> None:
        """多次调用 init_schema 不应报错."""
        await init_schema(repo_db)
        await init_schema(repo_db)

        async with get_db() as conn:
            cursor = await conn.execute("PRAGMA table_info(projects)")
            cols = {row[1] for row in await cursor.fetchall()}
        assert "estimated_chapters" in cols


class TestCharacterRepository:
    async def test_create_get_and_json_fields(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_character()

        character = await CharacterRepository().get("c1")

        assert character is not None
        assert character.personality_traits == ["stubborn"]
        assert character.goals == ["protect family"]
        assert character.relationships == {"master": "Elder Wang"}

    async def test_list_by_project_filters_rows(self, repo_db: Path) -> None:
        await _seed_project("p1")
        await _seed_project("p2")
        await _seed_character("c1", "p1")
        await _seed_character("c2", "p2")

        characters = await CharacterRepository().list_by_project("p1")

        assert [c.character_id for c in characters] == ["c1"]

    async def test_foreign_key_violation_is_not_swallowed(self, repo_db: Path) -> None:
        with pytest.raises(aiosqlite.IntegrityError):
            await _seed_character("bad", "missing")

    async def test_add_state_snapshot_insert_only(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_character()
        await _seed_version()

        repo = CharacterRepository()
        first = await repo.add_state_snapshot(
            CharacterState(character_id="c1", field="power", value="10", source_version_id="v1")
        )
        second = await repo.add_state_snapshot(
            CharacterState(character_id="c1", field="power", value="20", source_version_id="v1")
        )

        assert second > first
        async with get_db() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM character_states")
            row = await cursor.fetchone()
        assert row[0] == 2
        assert not hasattr(repo, "update")
        assert not hasattr(repo, "update_state_snapshot")


class TestChapterRepositories:
    async def test_chapter_goal_create_and_get_by_chapter(self, repo_db: Path) -> None:
        await _seed_project()
        goal = ChapterGoal(
            chapter_number=1,
            target_events=["win duel"],
            hooks=["mystery token"],
            obligations=["introduce sect"],
        )

        await ChapterGoalRepository().create(goal, "g1", "p1")
        saved = await ChapterGoalRepository().get_by_chapter("p1", 1)

        assert saved is not None
        assert saved.target_events == ["win duel"]
        assert saved.hooks == ["mystery token"]
        assert saved.obligations == ["introduce sect"]

    async def test_chapter_version_create_and_get(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_version()

        version = await ChapterVersionRepository().get("v1")

        assert version is not None
        assert version.scenes == [{"scene": 1}]
        assert version.generation_metadata == {"source": "test"}
        assert version.content == "content 1"

    async def test_list_by_chapter_orders_by_version_number(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_version("v2", version_number=2)
        await _seed_version("v1", version_number=1)

        versions = await ChapterVersionRepository().list_by_chapter("p1", 1)

        assert [v.version_id for v in versions] == ["v1", "v2"]

    async def test_get_chain_returns_root_to_current(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_version("v1", version_number=1)
        await _seed_version("v2", version_number=2, parent_version_id="v1")
        await _seed_version("v3", version_number=3, parent_version_id="v2")

        chain = await ChapterVersionRepository().get_chain("v3")

        assert [v.version_id for v in chain] == ["v1", "v2", "v3"]

    async def test_get_chain_missing_returns_empty_list(self, repo_db: Path) -> None:
        assert await ChapterVersionRepository().get_chain("missing") == []

    async def test_chapter_head_get_missing_returns_none(self, repo_db: Path) -> None:
        assert await ChapterHeadRepository().get("p1", 1) is None

    async def test_chapter_head_update_upserts(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_version("v1", version_number=1)
        await _seed_version("v2", version_number=2, parent_version_id="v1")
        repo = ChapterHeadRepository()

        await repo.update(ChapterHead(project_id="p1", chapter_number=1, current_version_id="v1"))
        await repo.update(
            ChapterHead(
                project_id="p1",
                chapter_number=1,
                current_version_id="v2",
                accepted_version_id="v2",
                status="accepted",
            )
        )

        head = await repo.get("p1", 1)
        assert head is not None
        assert head.current_version_id == "v2"
        assert head.accepted_version_id == "v2"
        assert head.status == "accepted"
