"""Tests for ProjectInitializer."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.settlement_repo import SettingSnapshotRepository
from songyan.models.project import ProjectSetting
from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeed,
    TemplateSeedCharacter,
    TemplateSeedSetting,
)
from songyan.project_templates.initializer import ProjectInitializer


@pytest.fixture
async def clean_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path=db_path)
    return db_path


async def test_initialize_minimal_project(clean_db: Path) -> None:
    project = ProjectSetting(
        title="Test",
        genre_id="scifi",
        mode_id="webnovel",
        protagonist_name="Lin",
    )
    template = ProjectTemplate(id="scifi", project_setting=project)
    project_id, setting = await ProjectInitializer.from_template(template)

    assert project_id
    assert setting.genre_id == "scifi"

    loaded = await ProjectRepository().get(project_id)
    assert loaded is not None
    assert loaded.genre_id == "scifi"


def test_init_sync_wrapper(clean_db: Path) -> None:
    project = ProjectSetting(
        title="Test",
        genre_id="scifi",
        mode_id="webnovel",
        protagonist_name="Lin",
    )
    template = ProjectTemplate(id="scifi", project_setting=project)
    project_id, setting = asyncio.run(ProjectInitializer.from_template(template))
    assert setting.protagonist_name == "Lin"


async def test_initialize_with_seed(clean_db: Path) -> None:
    project = ProjectSetting(
        title="Xuanhuan",
        genre_id="xuanhuan",
        mode_id="webnovel_intense",
        protagonist_name="Lu",
    )
    template = ProjectTemplate(
        id="xuanhuan",
        project_setting=project,
        seed=TemplateSeed(
            characters=[TemplateSeedCharacter(name="Lu", role="protagonist")],
            initial_settings=[
                TemplateSeedSetting(
                    setting_key="town",
                    setting_name="Qingyan",
                    description="a town",
                )
            ],
        ),
    )
    project_id, _ = await ProjectInitializer.from_template(template)
    assert project_id

    # verify seed characters/settings were written
    chars = await CharacterRepository().list_by_project(project_id)
    assert any(c.name == "Lu" for c in chars)
    settings_repo = SettingSnapshotRepository()
    settings_list = await settings_repo.list_by_project(project_id)
    assert any(s.setting_key == "town" for s in settings_list)
