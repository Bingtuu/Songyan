"""Human-in-the-Loop 指令模型 — 人类注入的修改意见、指令或完整内容."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HumanInstruction(BaseModel):
    """人类指令 — 在 Human Gate 节点产生，供下游 Agent 消费."""

    instruction_id: str
    gate_type: str  # creative_director_output | writer_first_draft | audit_report | settlement_extraction
    action: Literal["edit", "inject", "rewrite"]
    # edit: 修改特定字段（如 creative_brief 的 punch_points）
    # inject: 注入自由指令文本
    # rewrite: 人类写完整内容替换 AI 输出
    target_field: str | None = None  # edit 时指定字段
    content: str  # 指令内容或改写内容
    created_at: datetime = Field(default_factory=datetime.utcnow)
