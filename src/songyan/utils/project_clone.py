"""项目克隆/延续工具函数.

Task 138p: rehearsal 与延续验证脚本需要从源项目克隆角色档案到目标项目。
由于 `characters.character_id` 是全局主键，克隆时必须生成新 ID；
同时 Writer 生成的正文仍使用原始通用 ID（如 char_001），因此需要把
通用 ID -> 新项目 ID 的映射注册到 SettlementExtractor，保证 settlement
阶段的角色更新和数值台账能正确落库。
"""

from __future__ import annotations

from datetime import datetime

from songyan.agents.settlement_extractor import register_character_aliases
from songyan.db.repository import CharacterRepository
from songyan.models import Character


async def clone_characters(
    source_project_id: str,
    target_project_id: str,
) -> dict[str, str]:
    """将源项目的角色档案克隆到目标项目，并注册通用 ID alias.

    Args:
        source_project_id: 源项目 ID.
        target_project_id: 目标项目 ID.

    Returns:
        通用 ID（如 char_001）到目标项目角色 ID 的映射。
    """
    char_repo = CharacterRepository()
    source_chars = await char_repo.list_by_project(source_project_id)
    if not source_chars:
        return {}

    aliases: dict[str, str] = {}
    for i, char in enumerate(source_chars):
        generic_id = f"char_{i + 1:03d}"
        new_id = f"char-{target_project_id[:8]}-{i + 1:03d}"
        aliases[generic_id] = new_id
        clone = Character.model_validate(
            char.model_dump()
            | {
                "character_id": new_id,
                "project_id": target_project_id,
                "created_at": datetime.now().isoformat(),
            }
        )
        await char_repo.create(clone)

    register_character_aliases(aliases)
    return aliases
