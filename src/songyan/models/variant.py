"""Chapter-internal Variant (M3 draw) models.

Variant rows reference append-only ``chapter_versions`` via ``content_ref``.
They are not ChapterHead rows and not plan_* Canon.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

VariantStatus = Literal["generated", "picked", "abandoned", "archived"]


class ChapterVariant(BaseModel):
    """One slot draft for a chapter under a parent Canon fingerprint."""

    variant_id: str
    project_id: str
    chapter_number: int = Field(ge=1)
    slot_index: int = Field(ge=1)
    status: VariantStatus = "generated"
    parent_canon_fingerprint: str
    content_ref: str
    stale_vs_canon: int = Field(default=0, ge=0, le=1)
    score_card_json: str | None = None
    cost_cny_estimate: float = 0.0
    quality_flag: str | None = None
    created_at: str
    updated_at: str
