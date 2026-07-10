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


class NewCharacter(BaseModel):
    """Task 170p: 本章首次出场的具名配角/反派登记.

    seeding gap 根因：SettlementExtractor 只 UPDATE 已存在角色、从不 INSERT 新配角，
    导致 `characters` 表长期只有主角，声纹卡与 voice 量具对配角永远失效。
    本模型让结算识别新出场的具名角色并入库，作为声纹机制的落点。

    证据门禁（与 NewSetting.source_quote 同纪律）：
    - ``name`` 必须是正文中真实出现的具名角色（非代词、非旁白片段）。
    - ``source_quote`` 必须能在本章正文中找到，否则本条被过滤，不入库。
    """

    name: str
    role_type: Literal["supporting", "antagonist"] = "supporting"
    source_quote: str  # 原文证据：该角色出场/说话的引文
    background: str = ""  # 可选：从正文可推断的最小背景


class NewSetting(BaseModel):
    """新设定登记."""

    setting_name: str
    description: str
    source_quote: str
    setting_key: str = ""  # 设定唯一标识符，用于追踪演变
    chapter_number: int = 0  # 077a: 创建时的章节编号，由 repository 按 created_at 顺序推导


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
    """数值账本变更 — 所有题材通用."""

    character_id: str
    attribute_name: str  # 如 cultivation_level, spirit_stones
    opening_value: float
    increments: list[Increment] = Field(default_factory=list)
    decrements: list[Decrement] = Field(default_factory=list)
    closing_value: float
    formula: str = ""  # 可选：closing_value 的公式说明


class StateSettlement(BaseModel):
    """章节完成后的结构化状态结算."""

    # 角色状态变更
    character_updates: list[CharacterUpdate] = Field(default_factory=list)

    # Task 170p: 本章首次出场的具名配角/反派（证据门禁后入库）
    new_characters: list[NewCharacter] = Field(default_factory=list)

    # 新设定登记
    new_settings: list[NewSetting] = Field(default_factory=list)

    # Task 137: 本章回收/再次提及的已有 setting_key 列表（代码层也会二次校验）
    recycled_settings: list[str] = Field(default_factory=list)

    # 伏笔操作
    foreshadowing_updates: list[ForeshadowingUpdate] = Field(default_factory=list)

    # 数值变更（玄幻专用）
    numerical_updates: list[NumericalUpdate] = Field(default_factory=list)

    # 章末 Hook 状态
    planted_hooks: list[str] = Field(default_factory=list)
    resolved_hooks: list[str] = Field(default_factory=list)

    # 验证状态
    validation_status: Literal["valid", "needs_human_review", "failed"] = "valid"

    # Task 110: 伏笔压力监控 (low / medium / high)
    foreshadowing_pressure: str = "low"
    validation_errors: list[str] = Field(default_factory=list)

    # Phase 4 新增：影响力与开放线索
    impact_score: float = Field(0.0, ge=0.0, le=1.0)  # P2-11
    open_threads: list[str] = Field(default_factory=list)
