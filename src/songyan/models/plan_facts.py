"""Plan-first fact cards — ADR-0001 minimal canon records.

The plan layer and a human write these rows. Chapter prose is checked
against them later; this module does not absorb settlement extracts.

``approval_status`` is the pending-queue flag. ``approved`` rows are
canon. ``pending`` rows may be stored, but canon readers must ignore
them. An attribute's ``source`` stays ``plan`` or ``human`` even while
the row is pending: that value is the intended authority, not a third
source type.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PlanFactSource = Literal["plan", "human"]
PlanApprovalStatus = Literal["approved", "pending"]
TimeAnchorKind = Literal["story", "history"]


class PlanEntity(BaseModel):
    """entity(id, type, aliases). ``entity_id`` is the stable id."""

    entity_id: str
    project_id: str
    entity_type: str
    aliases: list[str] = Field(default_factory=list)
    approval_status: PlanApprovalStatus = "approved"


class PlanAttribute(BaseModel):
    """attribute(entity_id, key, value, valid_from_ch, valid_to_ch, source)."""

    attribute_id: str
    project_id: str
    entity_id: str
    key: str
    value: str
    valid_from_ch: int | None = Field(default=None, ge=1)
    valid_to_ch: int | None = Field(default=None, ge=1)
    source: PlanFactSource
    approval_status: PlanApprovalStatus = "approved"

    @model_validator(mode="after")
    def validate_validity_window(self) -> PlanAttribute:
        """Reject a window that ends before it starts."""
        if (
            self.valid_from_ch is not None
            and self.valid_to_ch is not None
            and self.valid_to_ch < self.valid_from_ch
        ):
            raise ValueError("valid_to_ch must be >= valid_from_ch")
        return self


class PlanTimeAnchor(BaseModel):
    """time_anchor(date, kind=story|history). ``anchor_id`` is the stable id."""

    anchor_id: str
    project_id: str
    date: str
    kind: TimeAnchorKind
    approval_status: PlanApprovalStatus = "approved"


class PlanEvent(BaseModel):
    """event(id, ch, time_anchor, participants, causes, reveals_evidence[]).

    ``time_anchor_id`` points at a ``PlanTimeAnchor``. ``participants``,
    ``causes``, and ``reveals_evidence`` are stable ids, not free text.
    """

    event_id: str
    project_id: str
    ch: int = Field(ge=1)
    time_anchor_id: str | None = None
    participants: list[str] = Field(default_factory=list)
    causes: list[str] = Field(default_factory=list)
    reveals_evidence: list[str] = Field(default_factory=list)
    approval_status: PlanApprovalStatus = "approved"


class PlanClue(BaseModel):
    """clue(id, planted_ch, revealed_ch, must_mention_in[]) for mystery."""

    clue_id: str
    project_id: str
    planted_ch: int = Field(ge=1)
    revealed_ch: int | None = Field(default=None, ge=1)
    must_mention_in: list[int] = Field(default_factory=list)
    approval_status: PlanApprovalStatus = "approved"

    @field_validator("must_mention_in")
    @classmethod
    def chapters_are_positive(cls, value: list[int]) -> list[int]:
        """Chapter numbers in the must-mention list start at 1."""
        if any(chapter < 1 for chapter in value):
            raise ValueError("must_mention_in chapters must be >= 1")
        return value

    @model_validator(mode="after")
    def validate_reveal_chapter(self) -> PlanClue:
        """A clue cannot be revealed before it is planted."""
        if self.revealed_ch is not None and self.revealed_ch < self.planted_ch:
            raise ValueError("revealed_ch must be >= planted_ch")
        return self
