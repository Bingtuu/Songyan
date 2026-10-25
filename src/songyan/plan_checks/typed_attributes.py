"""Code comparison for direction, quantity, time-anchor, and ownership."""

from __future__ import annotations

from pydantic import BaseModel, Field

from songyan.models.plan_facts import PlanAttribute

TYPED_ATTRIBUTE_KEYS = frozenset({"direction", "count", "time_anchor", "ownership"})

_KEY_ALIASES = {
    "direction": "direction",
    "count": "count",
    "quantity": "count",
    "time_anchor": "time_anchor",
    "ownership": "ownership",
}


class AttributeExtract(BaseModel):
    """One structured field taken from a chapter, or written as a fixture annotation.

    This checker does not read prose. The caller supplies the extract.
    """

    entity_id: str
    key: str
    value: str
    chapter: int | None = Field(default=None, ge=1)


class AttributeMismatch(BaseModel):
    """An extract that disagrees with the approved attribute in force."""

    attribute_id: str
    entity_id: str
    key: str
    approved_value: str
    extract_value: str
    chapter: int | None = None


def compare_typed_attributes(
    approved: list[PlanAttribute],
    extracts: list[AttributeExtract],
) -> list[AttributeMismatch]:
    """Compare typed fields. Other keys are ignored.

    Only ``approved`` rows with ``source`` of ``plan`` or ``human`` are
    in force. A row applies to an extract when the extract chapter falls
    inside ``valid_from_ch`` / ``valid_to_ch`` (open ends are unbounded).
    ``quantity`` is compared as ``count``.

    An extract with no in-force attribute is not a mismatch: absence is
    the must-mention checker's job, and new facts are not absorbed here.
    If several in-force values exist, a match against any of them passes.
    """
    mismatches: list[AttributeMismatch] = []
    for extract in extracts:
        key = _KEY_ALIASES.get(extract.key.strip())
        if key is None:
            continue
        applicable = [
            row
            for row in approved
            if row.approval_status == "approved"
            and row.source in ("plan", "human")
            and row.entity_id == extract.entity_id
            and _KEY_ALIASES.get(row.key.strip()) == key
            and _in_window(row, extract.chapter)
        ]
        if not applicable:
            continue
        extract_value = extract.value.strip()
        if any(row.value.strip() == extract_value for row in applicable):
            continue
        chosen = sorted(applicable, key=lambda row: row.attribute_id)[0]
        mismatches.append(
            AttributeMismatch(
                attribute_id=chosen.attribute_id,
                entity_id=extract.entity_id,
                key=key,
                approved_value=chosen.value.strip(),
                extract_value=extract_value,
                chapter=extract.chapter,
            )
        )
    return mismatches


def _in_window(row: PlanAttribute, chapter: int | None) -> bool:
    if chapter is None:
        return True
    if row.valid_from_ch is not None and chapter < row.valid_from_ch:
        return False
    if row.valid_to_ch is not None and chapter > row.valid_to_ch:
        return False
    return True
