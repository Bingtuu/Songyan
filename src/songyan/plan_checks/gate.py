"""Read-only gate: approved plan cards versus one chapter.

The chapter review path calls ``run_plan_fact_gate`` after a draft exists.
The gate loads ``approval_status=approved`` clues, events, and attributes
for that project only, then runs the three existing checkers. It does not
write plan canon, does not read or write settlement tables, and does not
turn chapter extracts into canon rows. Extracts and claim anchors are
inputs from the caller. The default claim judge is deterministic and does
not call a model.

Recording the report does not change review routing or
SettlementExtractor's authority.
"""

from __future__ import annotations

from typing import TypeVar

import structlog
from pydantic import BaseModel, Field

from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.plan_checks.claim_check import (
    AnchoredClaimJudge,
    ClaimAnchor,
    ClaimVerdict,
    verify_chapter_claims,
)
from songyan.plan_checks.must_mention import MissingMention, check_must_mention
from songyan.plan_checks.typed_attributes import (
    AttributeExtract,
    AttributeMismatch,
    compare_typed_attributes,
)

logger = structlog.get_logger(__name__)


class PlanFactGateReport(BaseModel):
    """Findings from one read-only pass. ``passed`` is false when any check flags."""

    project_id: str
    chapter: int
    missing_mentions: list[MissingMention] = Field(default_factory=list)
    claim_verdicts: list[ClaimVerdict] = Field(default_factory=list)
    attribute_mismatches: list[AttributeMismatch] = Field(default_factory=list)
    passed: bool = True


def plan_attribute_extracts_from_state(raw: object) -> list[AttributeExtract]:
    """Parse ``_plan_attribute_extracts``. ``None`` means the caller has none.

    The gate does not invent extracts from prose. A list item may be a
    model or a dict. Anything else is rejected so a bad payload cannot
    silently skip the comparison.
    """
    return _coerce(raw, AttributeExtract, "_plan_attribute_extracts")


def claim_anchors_from_state(raw: object) -> list[ClaimAnchor]:
    """Parse ``_plan_claim_anchors``. ``None`` means verbatim claim text only."""
    return _coerce(raw, ClaimAnchor, "_plan_claim_anchors")


async def run_plan_fact_gate(
    project_id: str,
    chapter: int,
    chapter_text: str,
    *,
    extracts: list[AttributeExtract] | None = None,
    anchors: list[ClaimAnchor] | None = None,
) -> PlanFactGateReport:
    """Check one chapter against the active project's approved plan cards.

    Pending rows and other projects are not loaded. Typed comparison uses
    only extracts for this chapter (an extract with no chapter applies).
    An extract with no in-force attribute is ignored, not stored.
    """
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id must be non-empty")

    repo = PlanFactRepository()
    clues = await repo.list_canon_clues(project_id)
    events = await repo.list_canon_events(project_id)
    attributes = await repo.list_canon_attributes(project_id)
    scoped = _extracts_for_chapter(extracts or [], chapter)
    missing = check_must_mention(clues, chapter, chapter_text)
    verdicts = await verify_chapter_claims(
        events,
        chapter,
        chapter_text,
        judge=AnchoredClaimJudge(anchors or []),
    )
    mismatches = compare_typed_attributes(attributes, scoped)
    report = PlanFactGateReport(
        project_id=project_id,
        chapter=chapter,
        missing_mentions=missing,
        claim_verdicts=verdicts,
        attribute_mismatches=mismatches,
        passed=_passed(missing, verdicts, mismatches),
    )
    logger.info(
        "plan_fact_gate.checked",
        project_id=project_id,
        chapter=chapter,
        passed=report.passed,
        missing_mentions=len(missing),
        claim_verdicts=len(verdicts),
        attribute_mismatches=len(mismatches),
    )
    return report


def _extracts_for_chapter(
    extracts: list[AttributeExtract],
    chapter: int,
) -> list[AttributeExtract]:
    return [row for row in extracts if row.chapter is None or row.chapter == chapter]


def _passed(
    missing: list[MissingMention],
    verdicts: list[ClaimVerdict],
    mismatches: list[AttributeMismatch],
) -> bool:
    if missing or mismatches:
        return False
    return all(row.status == "supported" for row in verdicts)


ModelT = TypeVar("ModelT", bound=BaseModel)


def _coerce(raw: object, model: type[ModelT], key: str) -> list[ModelT]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{key} must be a list")
    parsed: list[ModelT] = []
    for item in raw:
        if isinstance(item, model):
            parsed.append(item)
            continue
        parsed.append(model.model_validate(item))
    return parsed
