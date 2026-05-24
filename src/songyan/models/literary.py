"""Literary audit models — 文学性诊断，不阻塞流程."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LiteraryObservation(BaseModel):
    """文学性观察 — 诊断性输出."""

    observation_id: str
    observation_type: Literal[
        "character_tooling",
        "conceptual_idling",
        "excessive_smoothing",
        "valuable_fissure",
        "cliche_risk",
        "polyphony_weakness",
        "authorial_intrusion",
    ]
    description: str
    evidence_quote: str | None = None
    severity: Literal["notice", "suggestion", "highlight"] = "suggestion"
    recommendation: str = ""
    preserve: bool = False  # 是否建议保留（对 valuable_fissure）


class LiteraryAuditResult(BaseModel):
    """文学审计结果 — 不阻塞流程，供人工参考."""

    auditor_id: str = "literary_auditor"
    observations: list[LiteraryObservation] = Field(default_factory=list)

    # 综合评分（仅供参考，不阻塞）
    literary_quality_score: float = 0.0  # 0-10
    character_autonomy_score: float = 0.0  # 0-10
    conceptual_grounding_score: float = 0.0  # 概念落地度 0-10
    fissure_preservation_score: float = 0.0  # 裂隙保留度 0-10

    summary: str = ""
    duration_ms: int = 0
