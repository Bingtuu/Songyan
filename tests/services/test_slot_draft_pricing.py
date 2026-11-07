"""task 231：default_slot_draft 按 writer 角色解析出的实际模型计价与回填。"""

from __future__ import annotations

from typing import Any

import pytest

from songyan.config import settings
from songyan.services.variant_generate import SlotDraft, default_slot_draft
from songyan.utils.cost_estimator import (
    count_tokens,
    estimate_cost_from_tokens,
)


@pytest.mark.asyncio
async def test_slot_draft_uses_resolved_writer_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SlotDraft.model = role='writer' 解析出的模型名，成本按该模型费率估算。"""
    captured: dict[str, Any] = {}

    async def _fake_call_llm(prompt: str, **kwargs: Any) -> str:
        captured["prompt"] = prompt
        return "草稿正文。"

    monkeypatch.setattr(settings, "llm_model", "deepseek-chat")
    # 隔离环境变量里可能配置的角色级覆盖，保证解析结果可预期
    monkeypatch.setattr(settings, "llm_role_overrides", {})
    monkeypatch.setattr("songyan.llm.call_llm", _fake_call_llm)

    slot = await default_slot_draft(
        project_id="p1",
        chapter=1,
        slot_index=1,
        bible_text="",
        fingerprint="fp",
    )
    assert isinstance(slot, SlotDraft)
    assert slot.model == "deepseek-chat"
    # 计价口径：按解析出的模型费率对同一份 token 数估算
    expected = estimate_cost_from_tokens(
        count_tokens(captured["prompt"]),
        count_tokens("草稿正文。"),
        "deepseek-chat",
    )
    assert slot.cost_cny_estimate == pytest.approx(float(expected))
