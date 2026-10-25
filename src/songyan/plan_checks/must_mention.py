"""Must-mention check: registered phrases for chapter N against that chapter."""

from __future__ import annotations

from pydantic import BaseModel, Field

from songyan.models.plan_facts import PlanClue


class MissingMention(BaseModel):
    """A plan point whose registered phrase is absent from the chapter."""

    point_id: str
    label: str
    chapter: int
    missing_terms: list[str] = Field(default_factory=list)


def check_must_mention(
    clues: list[PlanClue],
    chapter: int,
    chapter_text: str,
) -> list[MissingMention]:
    """Report approved clues that chapter ``chapter`` must mention but does not.

    A clue is in scope when it is approved and ``chapter`` is in
    ``must_mention_in``. Every ``mention_terms`` entry must occur as a
    substring. When the term list is empty, ``label`` is the single
    phrase. A clue with neither is skipped: there is nothing to find.

    Pending clues are ignored even if the caller passes them in.
    """
    if chapter < 1:
        raise ValueError("chapter must be >= 1")

    missing: list[MissingMention] = []
    for clue in clues:
        if clue.approval_status != "approved":
            continue
        if chapter not in clue.must_mention_in:
            continue
        terms = list(clue.mention_terms)
        if not terms and clue.label.strip():
            terms = [clue.label]
        if not terms:
            continue
        absent = [term for term in terms if term not in chapter_text]
        if not absent:
            continue
        missing.append(
            MissingMention(
                point_id=clue.clue_id,
                label=clue.label,
                chapter=chapter,
                missing_terms=absent,
            )
        )
    return missing
