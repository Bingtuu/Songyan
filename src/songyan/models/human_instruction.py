"""Human-in-the-Loop 指令模型 — 人类注入的修改意见、指令或完整内容."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HumanInstruction(BaseModel):
    """人类指令 — 在 Human Gate 节点产生，供下游 Agent 消费."""

    instruction_id: str
    # creative_director_output | writer_first_draft | audit_report | settlement_extraction
    gate_type: str
    action: Literal["edit", "inject", "rewrite"]
    # edit: 修改特定字段（如 creative_brief 的 punch_points）
    # inject: 注入自由指令文本
    # rewrite: 人类写完整内容替换 AI 输出
    target_field: str | None = None  # edit 时指定字段
    content: str  # 指令内容或改写内容
    created_at: datetime = Field(default_factory=datetime.utcnow)


def normalize_human_instruction(raw: Mapping[str, Any]) -> HumanInstruction:
    """统一 action/type 字段，保证 Writer prompt 稳定渲染动作标签."""
    action = raw.get("action") or raw.get("type") or "inject"
    if action not in {"edit", "inject", "rewrite"}:
        action = "inject"
    return HumanInstruction(
        instruction_id=str(raw.get("instruction_id") or "inst-normalized"),
        gate_type=str(raw.get("gate_type") or "unknown"),
        action=action,
        target_field=(
            str(raw["target_field"])
            if raw.get("target_field") is not None
            else None
        ),
        content=str(raw.get("content") or ""),
        created_at=raw.get("created_at") or datetime.utcnow(),
    )
