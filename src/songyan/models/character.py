"""Character models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CharacterState(BaseModel):
    """角色状态快照 — 永远 INSERT 新记录，不 UPDATE 旧记录."""

    character_id: str
    field: str
    value: str
    source_version_id: str = ""
    lifecycle_status: str = "active"
    created_at: str = ""


class DialogueStyleCard(BaseModel):
    """角色对话风格卡 — 由 CreativeDirector 生成，注入 Writer Prompt."""

    character_id: str
    project_id: str

    # 句式特征
    sentence_length_preference: Literal["short", "medium", "long", "mixed"] = "mixed"
    common_openers: list[str] = Field(default_factory=list)
    common_closers: list[str] = Field(default_factory=list)

    # 情绪表达
    anger_expression: str = ""
    fear_expression: str = ""
    joy_expression: str = ""
    sadness_expression: str = ""

    # 修辞习惯
    metaphor_frequency: Literal["rare", "moderate", "frequent"] = "moderate"
    irony_usage: bool = False
    rhetorical_question_habit: bool = False

    # 互动特征
    interrupt_frequency: Literal["rare", "moderate", "frequent"] = "moderate"
    pause_habit: str = ""

    # 背景影响
    education_level_hint: str = ""
    social_role_speech_pattern: str = ""

    generated_at: str = ""


class Character(BaseModel):
    """角色档案."""

    character_id: str
    project_id: str
    name: str
    role_type: Literal["protagonist", "supporting", "antagonist"] = "protagonist"
    background: str = ""
    personality_traits: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    relationships: dict[str, str] = Field(default_factory=dict)
    dialogue_style_card: DialogueStyleCard | None = None
    created_at: str = ""
