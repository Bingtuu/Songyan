"""M3 step 3: ``variant list`` shaping + ``variant diff`` (unified, read-only)."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass

from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.repository import ChapterVersionRepository
from songyan.models.variant import ChapterVariant

_FP_SHORT = 12


def fingerprint_short(fingerprint: str, *, n: int = _FP_SHORT) -> str:
    """Short display form for list / text (tech-m3 §4.3)."""
    if len(fingerprint) <= n:
        return fingerprint
    return fingerprint[:n]


def _optional_score(score_card_json: str | None) -> object | None:
    if not score_card_json:
        return None
    try:
        return json.loads(score_card_json)
    except json.JSONDecodeError:
        return None


def shape_list_row(row: ChapterVariant) -> dict[str, object]:
    """List surface: slot / status / stale / fingerprint / cost / content_ref / score."""
    return {
        "slot_index": row.slot_index,
        "status": row.status,
        "stale_vs_canon": row.stale_vs_canon,
        "fingerprint": fingerprint_short(row.parent_canon_fingerprint),
        "parent_canon_fingerprint": row.parent_canon_fingerprint,
        "cost_cny_estimate": row.cost_cny_estimate,
        "content_ref": row.content_ref,
        "score": _optional_score(row.score_card_json),
        "variant_id": row.variant_id,
    }


@dataclass(frozen=True)
class VariantDiffResult:
    """Unified diff of two chapter variant slots."""

    chapter: int
    a: int
    b: int
    content_ref_a: str
    content_ref_b: str
    diff: str


class MissingVariantSlotError(Exception):
    """Requested slot_index is absent for the chapter (business reject → exit 2)."""

    def __init__(self, slot_index: int, chapter: int) -> None:
        self.slot_index = slot_index
        self.chapter = chapter
        super().__init__(f"槽不存在: chapter={chapter} slot={slot_index}")


async def list_variant_rows(project_id: str, chapter: int) -> list[dict[str, object]]:
    rows = await ChapterVariantRepository().list_for_chapter(project_id, chapter)
    return [shape_list_row(row) for row in rows]


async def _content_for_slot(
    project_id: str, chapter: int, slot_index: int
) -> tuple[ChapterVariant, str]:
    variant = await ChapterVariantRepository().get_by_slot(
        project_id, chapter, slot_index
    )
    if variant is None:
        raise MissingVariantSlotError(slot_index, chapter)
    version = await ChapterVersionRepository().get(variant.content_ref)
    if version is None:
        raise MissingVariantSlotError(slot_index, chapter)
    return variant, version.content


def unified_content_diff(
    content_a: str,
    content_b: str,
    *,
    label_a: str,
    label_b: str,
) -> str:
    """Line-level unified diff (locked by CLI tests)."""
    return "".join(
        difflib.unified_diff(
            content_a.splitlines(keepends=True),
            content_b.splitlines(keepends=True),
            fromfile=label_a,
            tofile=label_b,
        )
    )


async def diff_variant_slots(
    project_id: str,
    chapter: int,
    slot_a: int,
    slot_b: int,
) -> VariantDiffResult:
    """Read-only unified diff of two slots' ``chapter_versions`` content."""
    variant_a, content_a = await _content_for_slot(project_id, chapter, slot_a)
    variant_b, content_b = await _content_for_slot(project_id, chapter, slot_b)
    diff_text = unified_content_diff(
        content_a,
        content_b,
        label_a=f"slot {slot_a}",
        label_b=f"slot {slot_b}",
    )
    return VariantDiffResult(
        chapter=chapter,
        a=slot_a,
        b=slot_b,
        content_ref_a=variant_a.content_ref,
        content_ref_b=variant_b.content_ref,
        diff=diff_text,
    )
