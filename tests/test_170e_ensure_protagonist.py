"""Task 170e: ensure_protagonist_character 幂等契约测试.

根因回归：未 seed 的项目 characters 表为空 → 声纹机制永不激活。
本组测试锁定"建项目/启动流水线时补建 protagonist"的幂等行为，
确保不干扰已 seed 的项目与既有测试。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.repository import CharacterRepository, ProjectRepository
from songyan.models.character import Character
from songyan.models.project import ProjectSetting
from songyan.workflows._helpers import ensure_protagonist_character


def _project(name: str = "林渊") -> ProjectSetting:
    return ProjectSetting(
        genre_id="scifi",
        mode_id="webnovel_intense",
        protagonist_name=name,
        protagonist_background="前星际考古学家",
    )


@pytest.mark.asyncio
async def test_creates_protagonist_when_missing(test_db: Path) -> None:
    """空 characters 表 → 补建一条 protagonist."""
    project_id = "p-missing"
    await ProjectRepository().create(_project(), project_id)

    created = await ensure_protagonist_character(project_id)

    assert created is True
    chars = await CharacterRepository().list_by_project(project_id)
    assert len(chars) == 1
    assert chars[0].role_type == "protagonist"
    assert chars[0].name == "林渊"
    assert chars[0].background == "前星际考古学家"


@pytest.mark.asyncio
async def test_noop_when_protagonist_exists(test_db: Path) -> None:
    """已有 protagonist → 不新建、不改名."""
    project_id = "p-has-proto"
    await ProjectRepository().create(_project("新名字"), project_id)
    await CharacterRepository().create(
        Character(
            character_id="char-existing",
            project_id=project_id,
            name="旧主角",
            role_type="protagonist",
        )
    )

    created = await ensure_protagonist_character(project_id)

    assert created is False
    chars = await CharacterRepository().list_by_project(project_id)
    assert len(chars) == 1
    assert chars[0].character_id == "char-existing"
    assert chars[0].name == "旧主角"


@pytest.mark.asyncio
async def test_creates_even_when_only_supporting_exists(test_db: Path) -> None:
    """只有配角、无 protagonist → 仍补建 protagonist（配角不算主角）."""
    project_id = "p-only-support"
    await ProjectRepository().create(_project(), project_id)
    await CharacterRepository().create(
        Character(
            character_id="char-support",
            project_id=project_id,
            name="医疗官",
            role_type="supporting",
        )
    )

    created = await ensure_protagonist_character(project_id)

    assert created is True
    chars = await CharacterRepository().list_by_project(project_id)
    roles = sorted(c.role_type for c in chars)
    assert roles == ["protagonist", "supporting"]


@pytest.mark.asyncio
async def test_idempotent_on_repeat_calls(test_db: Path) -> None:
    """连续两次调用只建一条，第二次 no-op."""
    project_id = "p-repeat"
    await ProjectRepository().create(_project(), project_id)

    first = await ensure_protagonist_character(project_id)
    second = await ensure_protagonist_character(project_id)

    assert first is True
    assert second is False
    chars = await CharacterRepository().list_by_project(project_id)
    assert len(chars) == 1


@pytest.mark.asyncio
async def test_noop_when_project_absent(test_db: Path) -> None:
    """项目不存在 → 返回 False，不写任何数据."""
    created = await ensure_protagonist_character("does-not-exist")
    assert created is False
    chars = await CharacterRepository().list_by_project("does-not-exist")
    assert chars == []


@pytest.mark.asyncio
async def test_noop_when_protagonist_name_empty(test_db: Path) -> None:
    """protagonist_name 为空白 → 不新建（无有效名字可用）."""
    project_id = "p-empty-name"
    # 绕过 create 的交互，直接构造空名项目设置
    await ProjectRepository().create(_project("   "), project_id)

    created = await ensure_protagonist_character(project_id)

    assert created is False
    chars = await CharacterRepository().list_by_project(project_id)
    assert chars == []


@pytest.mark.asyncio
async def test_passing_project_avoids_reload(test_db: Path) -> None:
    """显式传入 project 时用传入值（含 background），不依赖二次加载."""
    project_id = "p-passed"
    proj = _project("苏晚")
    await ProjectRepository().create(proj, project_id)

    created = await ensure_protagonist_character(project_id, proj)

    assert created is True
    chars = await CharacterRepository().list_by_project(project_id)
    assert chars[0].name == "苏晚"
