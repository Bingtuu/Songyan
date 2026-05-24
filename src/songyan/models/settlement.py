"""Settlement models — Chapter acceptance后的状态结算."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CharacterUpdate(BaseModel):
    """角色状态变更."""

    character_id: str
    field: str
    old_value: str
    new_value: str
    source_quote: str  # 原文证据


class NewSetting(BaseModel):
    """新设定登记."""

    setting_name: str
    description: str
    source_quote: str
    setting_key: str = ""  # 设定唯一标识符，用于追踪演变


class ForeshadowingUpdate(BaseModel):
    """伏笔操作."""

    foreshadowing_id: str | None = None
    operation: Literal["plant", "resolve", "update_status"]
    description: str
    expected_resolve_chapter: int | None = None
    source_version_id: str = ""  # 关联版本


class Increment(BaseModel):
    """数值增量."""

    amount: float
    source: str
    source_quote: str


class Decrement(BaseModel):
    """数值消耗."""

    amount: float
    usage: str
    source_quote: str


class NumericalUpdate(BaseModel):
    """数值账本变更 — 玄幻专用."""

    character_id: str
    attribute_name: str  # 如 cultivation_level, spirit_stones
    opening_value: float
    increments: list[Increment] = Field(default_factory=list)
    decrements: list[Decrement] = Field(default_factory=list)
    closing_value: float


class StateSettlement(BaseModel):
    """章节完成后的结构化状态结算."""

    # 角色状态变更
    character_updates: list[CharacterUpdate] = Field(default_factory=list)

    # 新设定登记
    new_settings: list[NewSetting] = Field(default_factory=list)

    # 伏笔操作
    foreshadowing_updates: list[ForeshadowingUpdate] = Field(default_factory=list)

    # 数值变更（玄幻专用）
    numerical_updates: list[NumericalUpdate] = Field(default_factory=list)

    # 章末 Hook 状态
    planted_hooks: list[str] = Field(default_factory=list)
    resolved_hooks: list[str] = Field(default_factory=list)

    # 验证状态
    validation_status: Literal["valid", "needs_human_review", "failed"] = "valid"
    validation_errors: list[str] = Field(default_factory=list)
