"""Task 138p: 克隆项目角色 ID alias 注册测试.

在 rehearsal/延续脚本中，源项目的角色 ID（如 char_001）会被克隆为新 ID
（如 char-abc123-001），但 Writer 生成的正文仍使用原始 ID。 SettlementExtractor
通过全局 alias 表将原始 ID 映射到目标项目 ID。本测试确保克隆工具正确建立并
注册该映射。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from songyan.db import CharacterRepository, ProjectRepository
from songyan.db.migrations import init_schema
from songyan.models import Character, ProjectSetting

pytestmark = pytest.mark.asyncio


async def _seed_project(project_id: str = "source-proj") -> None:
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
    project_id: str = "source-proj",
    role_type: str = "protagonist",
) -> None:
    await CharacterRepository().create(
        Character(
            character_id=character_id,
            project_id=project_id,
            name="Lin Yuan",
            role_type=role_type,
        )
    )


@pytest.fixture
async def clone_db(tmp_path: Path, monkeypatch: Any) -> Path:
    """为克隆测试创建独立的临时数据库."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "clone.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    from songyan.workflows.checkpointer import reset_checkpointer

    await reset_checkpointer()
    return db_path


class TestCloneCharacters:
    async def test_clone_characters_registers_alias(
        self, clone_db: Path, monkeypatch: Any
    ) -> None:
        """C1: 克隆角色后，源通用 ID char_001 必须映射到目标项目的新 ID."""
        source_id = "source-proj"
        target_id = "target-proj"

        await _seed_project(source_id)
        await _seed_project(target_id)
        await _seed_character("char_001", source_id)

        from songyan.agents.settlement_extractor import (
            _CHARACTER_ID_ALIASES,
            _normalize_character_id,
        )

        # 测试前清空全局 alias，避免其他测试污染
        _CHARACTER_ID_ALIASES.clear()

        # 待测试的 helper 函数
        from songyan.utils.project_clone import clone_characters

        aliases = await clone_characters(source_id, target_id)

        # 断言：返回了 alias 映射
        assert "char_001" in aliases
        target_char_id = aliases["char_001"]
        assert target_char_id.startswith(f"char-{target_id[:8]}-")

        # 断言：目标项目中存在对应角色
        target_chars = await CharacterRepository().list_by_project(target_id)
        assert any(c.character_id == target_char_id for c in target_chars)

        # 断言：alias 已注册到 SettlementExtractor 的全局映射
        assert _normalize_character_id("char_001") == target_char_id
        assert _normalize_character_id("char_002") == "char_002"  # 未注册保持不变

        # 清理
        _CHARACTER_ID_ALIASES.clear()

    async def test_clone_characters_empty_source(
        self, clone_db: Path, monkeypatch: Any
    ) -> None:
        """C2: 源项目没有角色时返回空映射，不报错."""
        source_id = "empty-proj"
        target_id = "target-empty-proj"
        await _seed_project(source_id)
        await _seed_project(target_id)

        from songyan.utils.project_clone import clone_characters

        aliases = await clone_characters(source_id, target_id)
        assert aliases == {}
