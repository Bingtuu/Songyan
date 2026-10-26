"""Read typed extracts and claim anchors from one chapter.

``run_plan_fact_gate`` does not invent these. The chapter review node
calls ``load_observed_review_inputs`` when the caller did not pin
``_plan_attribute_extracts`` and ``_plan_claim_anchors``, then passes the
rows in. Nothing here writes plan canon or settlement tables, and nothing
calls a model.

The reader only uses phrases already on the approved cards, plus the same
four typed keys the comparator already knows. It does not add a genre checker.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.models.plan_facts import PlanAttribute, PlanEntity, PlanEvent
from songyan.plan_checks.claim_check import ClaimAnchor
from songyan.plan_checks.typed_attributes import AttributeExtract

_KEY_ALIASES = {
    "direction": "direction",
    "count": "count",
    "quantity": "count",
    "time_anchor": "time_anchor",
    "ownership": "ownership",
}

_NEGATION = re.compile(r"(?:不是|不在|没有|并未|不能|并非|不准|不可|不会)([^，。；、\n]{2,24})")
_NEG_PREFIXES = (
    "并不能",
    "不是",
    "不在",
    "没有",
    "并未",
    "不能",
    "并非",
    "不准",
    "不可",
    "不会",
    "不要",
    "不",
    "没",
)
_HEDGES = ("应该", "应当", "必须", "须要", "仍应", "不能", "不是", "不可")
_GOVERNORS = ("走向", "方向", "朝向", "是", "为")
_COUNT_TOKEN = {
    "一": "1",
    "二": "2",
    "两": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
}
_COUNT_CHANGE = re.compile(
    r"从([一二两三四五六七八九十]|\d+)道变成了?([一二两三四五六七八九十]|\d+)道"
)
_COUNT_PHRASE = re.compile(r"(?:至少)?([一二两三四五六七八九十]|\d+)(?:道|处|人)")
_NAME_SLOT = (
    r"(?:记名(?:栏|归属)?|归属|属于|灵印记名)"
    r"(?:仍是|改为|改写为|为|是|：|:|\s){0,8}"
)

# One tuple is one direction family. Phrases in a family are the same shape
# as each other, so an approved value selects the family and not a story.
_DIRECTION_GROUPS: tuple[tuple[re.Pattern[str], ...], ...] = (
    (re.compile(r"面朝[东西南北]"),),
    (re.compile(r"[东西南北]向[东西南北]"),),
    (re.compile(r"自[内外]向[内外]"),),
    (re.compile(r"[左右上下]向[左右上下]"),),
    (
        re.compile(r"从[内外]往[内外](?:拉|推)"),
        re.compile(r"从[内外]向[内外](?:拉|推)"),
        re.compile(r"往[内外](?:拉|推)"),
        re.compile(r"向[内外](?:拉|推)"),
    ),
)
_FACING_GROUP = 0


class _Hit:
    def __init__(self, phrase: str, group: int, start: int, end: int) -> None:
        self.phrase = phrase
        self.group = group
        self.start = start
        self.end = end


def observe_plan_review_inputs(
    *,
    chapter: int,
    chapter_text: str,
    attributes: list[PlanAttribute],
    events: list[PlanEvent],
    entities: list[PlanEntity] | None = None,
) -> tuple[list[AttributeExtract], list[ClaimAnchor]]:
    """Return extracts and anchors for ``chapter`` from approved cards and prose.

    Pending rows are ignored. A phrase counts only when the chapter asserts
    it, not when the chapter only denies it.
    """
    if chapter < 1:
        raise ValueError("chapter must be >= 1")

    approved_entities = [row for row in entities or [] if row.approval_status == "approved"]
    aliases = {
        row.entity_id: [alias for alias in row.aliases if alias.strip()]
        for row in approved_entities
    }
    person_names = [
        alias
        for row in approved_entities
        if row.entity_type == "person"
        for alias in row.aliases
        if len(alias.strip()) >= 2
    ]
    in_force = [row for row in attributes if _in_force(row, chapter)]
    chapter_events = [
        row for row in events if row.approval_status == "approved" and row.ch == chapter
    ]
    claim_texts = [claim.text for event in chapter_events for claim in event.claims]
    hits = _direction_hits(chapter_text)
    extracts: list[AttributeExtract] = []

    def add(row: PlanAttribute, value: str) -> None:
        key = _canonical_key(row.key)
        cleaned = value.strip()
        if key is None or not cleaned:
            return
        if any(
            item.entity_id == row.entity_id and item.key == key and item.value == cleaned
            for item in extracts
        ):
            return
        extracts.append(
            AttributeExtract(
                entity_id=row.entity_id,
                key=key,
                value=cleaned,
                chapter=chapter,
            )
        )

    for row in in_force:
        key = _canonical_key(row.key)
        if key is None:
            continue
        if _asserted(chapter_text, row.value):
            add(row, row.value)
        if key == "direction":
            for phrase in _direction_alternatives(
                row,
                chapter_text,
                hits,
                aliases.get(row.entity_id, []),
            ):
                add(row, phrase)
        elif key == "count":
            for phrase in _count_alternatives(
                chapter_text,
                row.value,
                aliases.get(row.entity_id, []),
            ):
                add(row, phrase)
        elif key == "ownership" and _name_ownership(row.value, claim_texts, person_names):
            for name in person_names:
                if name != row.value.strip() and _name_asserted(chapter_text, name):
                    add(row, name)

    anchors: list[ClaimAnchor] = []
    seen: set[str] = set()
    for event in chapter_events:
        for claim in event.claims:
            if claim.claim_id in seen:
                continue
            seen.add(claim.claim_id)
            anchor = _anchor_for_claim(
                claim.claim_id,
                claim.text,
                chapter_text,
                event,
                in_force,
                extracts,
                add,
            )
            if anchor is not None:
                anchors.append(anchor)
    return extracts, anchors


async def load_observed_review_inputs(
    project_id: str,
    chapter: int,
    chapter_text: str,
) -> tuple[list[AttributeExtract], list[ClaimAnchor]]:
    """Load approved cards and observe one chapter. Read-only."""
    repo = PlanFactRepository()
    return observe_plan_review_inputs(
        chapter=chapter,
        chapter_text=chapter_text,
        attributes=await repo.list_canon_attributes(project_id),
        events=await repo.list_canon_events(project_id),
        entities=await repo.list_canon_entities(project_id),
    )


def _anchor_for_claim(
    claim_id: str,
    claim_text: str,
    chapter_text: str,
    event: PlanEvent,
    attributes: list[PlanAttribute],
    extracts: list[AttributeExtract],
    add: Callable[[PlanAttribute, str], None],
) -> ClaimAnchor | None:
    linked = [row for row in attributes if row.value and row.value in claim_text]
    support = _unique(row.value.strip() for row in linked if row.value.strip())
    contradict: list[str] = []
    for raw in _NEGATION.findall(claim_text):
        hit = _asserted_span(chapter_text, raw)
        if hit is None or any(hit == row.value or hit in row.value for row in linked):
            continue
        contradict.append(hit)
        target = _negation_target(linked, event, attributes)
        if target is not None:
            add(target, hit)
    for row in linked:
        key = _canonical_key(row.key)
        if key is None:
            continue
        for item in extracts:
            if item.entity_id == row.entity_id and item.key == key and item.value != row.value:
                contradict.append(item.value)
    contradict = _unique(contradict)
    if not contradict and not any(_asserted(chapter_text, term) for term in support):
        return None
    return ClaimAnchor(
        claim_id=claim_id,
        support_terms=support,
        contradict_terms=contradict,
    )


def _negation_target(
    linked: list[PlanAttribute],
    event: PlanEvent,
    attributes: list[PlanAttribute],
) -> PlanAttribute | None:
    if len(linked) == 1:
        return linked[0]
    if linked:
        return None
    participant_ids = set(event.participants)
    owned = [row for row in attributes if row.entity_id in participant_ids]
    if len(owned) == 1:
        return owned[0]
    return None


def _direction_alternatives(
    row: PlanAttribute,
    chapter_text: str,
    hits: list[_Hit],
    entity_aliases: list[str],
) -> list[str]:
    group = _group_for(row.value)
    found: list[str] = []
    for hit in hits:
        if hit.phrase == row.value or hit.phrase in row.value:
            continue
        same_family = group is not None and hit.group == group
        sentence = _sentence_at(chapter_text, hit.start)
        near_alias = any(alias in sentence for alias in entity_aliases)
        if same_family and hit.group == _FACING_GROUP:
            found.append(hit.phrase)
        elif same_family and _governed(chapter_text, hit.start):
            found.append(hit.phrase)
        elif near_alias and _governed(chapter_text, hit.start):
            found.append(hit.phrase)
    return _unique(found)


def _count_alternatives(text: str, approved: str, entity_aliases: list[str]) -> list[str]:
    approved_norm = _norm_count(approved)
    if approved_norm is None:
        return []
    found: list[str] = []
    for match in _COUNT_CHANGE.finditer(text):
        left = _norm_count(match.group(1))
        right = _norm_count(match.group(2))
        if left == approved_norm and right is not None and right != approved_norm:
            found.append(right)
    if entity_aliases:
        for sentence in re.split(r"[。！？\n]", text):
            if not any(alias in sentence for alias in entity_aliases):
                continue
            for match in _COUNT_PHRASE.finditer(sentence):
                norm = _norm_count(match.group(1))
                if norm is not None and norm != approved_norm:
                    found.append(norm)
    return _unique(found)


def _name_ownership(value: str, claim_texts: list[str], person_names: list[str]) -> bool:
    cleaned = value.strip()
    if cleaned in person_names:
        return True
    return any(
        re.search(rf"(?:记名|灵印记名).{{0,12}}{re.escape(cleaned)}", text) is not None
        for text in claim_texts
    )


def _name_asserted(text: str, name: str) -> bool:
    if not _asserted(text, name):
        return False
    return re.search(_NAME_SLOT + re.escape(name), text) is not None


def _direction_hits(text: str) -> list[_Hit]:
    hits: list[_Hit] = []
    for index, group in enumerate(_DIRECTION_GROUPS):
        for pattern in group:
            for match in pattern.finditer(text):
                hits.append(_Hit(match.group(), index, match.start(), match.end()))
    kept: list[_Hit] = []
    for hit in hits:
        covered = any(
            other.start <= hit.start
            and other.end >= hit.end
            and other.end - other.start > hit.end - hit.start
            for other in hits
        )
        if not covered:
            kept.append(hit)
    return kept


def _group_for(value: str) -> int | None:
    for index, group in enumerate(_DIRECTION_GROUPS):
        if any(pattern.fullmatch(value) for pattern in group):
            return index
    return None


def _governed(text: str, start: int) -> bool:
    window = text[max(0, start - 16) : start]
    if any(hedge in window for hedge in _HEDGES):
        return False
    return any(governor in window for governor in _GOVERNORS)


def _sentence_at(text: str, index: int) -> str:
    marks = "。！？\n"
    left = max(text.rfind(mark, 0, index) for mark in marks)
    rights = [text.find(mark, index) for mark in marks]
    rights = [pos for pos in rights if pos >= 0]
    right = min(rights) if rights else len(text)
    return text[left + 1 : right]


def _asserted(text: str, term: str) -> bool:
    if not term:
        return False
    start = 0
    while True:
        index = text.find(term, start)
        if index < 0:
            return False
        window = text[max(0, index - 6) : index]
        if any(window.endswith(prefix) for prefix in _NEG_PREFIXES):
            start = index + len(term)
            continue
        return True


def _asserted_span(text: str, span: str) -> str | None:
    cleaned = span.strip()
    cleaned = re.sub(r"[的了着过]+$", "", cleaned)
    cleaned = re.sub(r"[上里中]$", "", cleaned)
    if len(cleaned) < 2:
        return None
    if _asserted(text, cleaned):
        return cleaned
    if len(cleaned) < 4:
        return None
    for size in range(len(cleaned) - 1, 3, -1):
        suffix = cleaned[-size:]
        if _asserted(text, suffix):
            return suffix
    return None


def _norm_count(token: str) -> str | None:
    cleaned = token.strip()
    cleaned = re.sub(r"(?:道|处|人|个)$", "", cleaned)
    if cleaned.isdigit():
        return str(int(cleaned))
    return _COUNT_TOKEN.get(cleaned)


def _in_force(row: PlanAttribute, chapter: int) -> bool:
    if row.approval_status != "approved" or row.source not in ("plan", "human"):
        return False
    if _canonical_key(row.key) is None:
        return False
    if row.valid_from_ch is not None and chapter < row.valid_from_ch:
        return False
    if row.valid_to_ch is not None and chapter > row.valid_to_ch:
        return False
    return True


def _canonical_key(key: str) -> str | None:
    return _KEY_ALIASES.get(key.strip())


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
