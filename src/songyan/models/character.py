"""Character models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CharacterState(BaseModel):
    """角色状态快照 — 永远 INSERT 新记录，不 UPDATE 旧记录."""

    character_id: str
    field: str
    value: str
    source_version_id: str = ""
    created_at: str = ""


class Character(BaseModel):
    """角色档案."""

    character_id: str
    project_id: str
    name: str
    role_type: str = "protagonist"  # protagonist | supporting | antagonist
    background: str = ""
    personality_traits: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    relationships: dict[str, str] = Field(default_factory=dict)
    created_at: str = ""
