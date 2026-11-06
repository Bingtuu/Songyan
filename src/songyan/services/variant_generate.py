"""M3 step 2: ``variant generate`` orchestration (tech-m3 §4.2 / B2 / B6 / S8).

Writes N append-only ``ChapterVersion`` rows + ``chapter_variants`` slots.
Reads approved Canon only. Never auto-picks. Never writes ``plan_*``.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.llm_call_usage_repo import LlmCallUsageRepository
from songyan.db.repository import ChapterVersionRepository
from songyan.models.chapter import ChapterVersion
from songyan.models.variant import ChapterVariant
from songyan.plan_checks.bible import load_chapter_plan_bible
from songyan.services.variant_fingerprint import fingerprint_chapter_parent_canon
from songyan.utils.cost_estimator import count_tokens, estimate_cost_from_tokens

logger = structlog.get_logger(__name__)

DraftFn = Callable[..., Awaitable["SlotDraft"]]


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SlotDraft:
    """One model draft for a variant slot (content + cost estimate)."""

    content: str
    cost_cny_estimate: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = "variant-mock"


@dataclass
class GenerateResult:
    """Outcome of ``variant generate`` (partial ok when budget exhausted)."""

    variants: list[ChapterVariant] = field(default_factory=list)
    fingerprint: str = ""
    budget_exhausted: bool = False
    n_requested: int = 0


async def default_slot_draft(
    *,
    project_id: str,
    chapter: int,
    slot_index: int,
    bible_text: str,
    fingerprint: str,
) -> SlotDraft:
    """Thin LLM draft for one slot. Tests monkeypatch this symbol.

    Uses approved bible text only (caller must pass ``load_chapter_plan_bible``
    output). Cost estimate uses S7 owner rates (¥2/M in, ¥8/M out).
    """
    from songyan.llm import call_llm

    prompt = (
        f"你是松烟的章内抽卡写手。根据下列已批准 Canon 圣经，"
        f"为项目 {project_id} 第 {chapter} 章写一版可丢弃草稿"
        f"（slot {slot_index}）。不要引用未入典事实。\n\n"
        f"【Canon 指纹】{fingerprint}\n\n"
        f"【圣经】\n{bible_text or '（空）'}\n\n"
        f"请直接输出章节正文，不要前言后语。"
    )
    content = await call_llm(prompt, role="writer")
    prompt_tokens = count_tokens(prompt)
    completion_tokens = count_tokens(content)
    cost = estimate_cost_from_tokens(prompt_tokens, completion_tokens)
    return SlotDraft(
        content=content,
        cost_cny_estimate=float(cost),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model="writer",
    )


async def _next_slot_start(project_id: str, chapter: int) -> int:
    rows = await ChapterVariantRepository().list_for_chapter(project_id, chapter)
    if not rows:
        return 1
    return max(row.slot_index for row in rows) + 1


async def generate_chapter_variants(
    project_id: str,
    chapter: int,
    *,
    n: int = 2,
    budget_cny: float | None = None,
    draft_fn: DraftFn | None = None,
) -> GenerateResult:
    """Generate ``n`` variant slots for one chapter.

    - Computes ``parent_canon_fingerprint`` from approved bible-visible Canon.
    - Each slot: INSERT new ``ChapterVersion`` + ``chapter_variants`` row
      with ``status=generated`` (never ``picked``).
    - Does not write ``plan_*``; does not UPDATE existing version content.
    - When ``budget_cny`` is set and spent already meets/exceeds it before a
      slot, stop; keep written slots; ``budget_exhausted=True``.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    if chapter < 1:
        raise ValueError("chapter must be >= 1")

    draft = draft_fn or default_slot_draft
    fingerprint = await fingerprint_chapter_parent_canon(project_id, chapter)
    bible = await load_chapter_plan_bible(project_id, chapter)
    bible_text = bible.text

    start_slot = await _next_slot_start(project_id, chapter)
    version_repo = ChapterVersionRepository()
    variant_repo = ChapterVariantRepository()
    usage_repo = LlmCallUsageRepository()

    written: list[ChapterVariant] = []
    spent = 0.0
    budget_exhausted = False

    for offset in range(n):
        if budget_cny is not None and spent >= budget_cny:
            budget_exhausted = True
            break

        slot_index = start_slot + offset
        slot_draft = await draft(
            project_id=project_id,
            chapter=chapter,
            slot_index=slot_index,
            bible_text=bible_text,
            fingerprint=fingerprint,
        )
        cost = float(slot_draft.cost_cny_estimate)
        content = slot_draft.content or ""
        word_count = len(content)

        version_number = await version_repo.get_next_version_number(project_id, chapter)
        version_id = f"v-{uuid.uuid4().hex[:12]}"
        variant_id = f"var-{uuid.uuid4().hex[:12]}"
        now = _utc_now()

        await version_repo.create(
            ChapterVersion(
                version_id=version_id,
                project_id=project_id,
                chapter_number=chapter,
                version_number=version_number,
                version_type="draft",
                content=content,
                word_count=word_count,
                generation_metadata={
                    "source": "variant.generate",
                    "slot_index": slot_index,
                    "parent_canon_fingerprint": fingerprint,
                },
            )
        )
        variant = ChapterVariant(
            variant_id=variant_id,
            project_id=project_id,
            chapter_number=chapter,
            slot_index=slot_index,
            status="generated",
            parent_canon_fingerprint=fingerprint,
            content_ref=version_id,
            stale_vs_canon=0,
            cost_cny_estimate=cost,
            created_at=now,
            updated_at=now,
        )
        await variant_repo.insert(variant)
        await usage_repo.record(
            model=slot_draft.model,
            token_source="estimate",
            cost_source="pricing_estimate",
            project_id=project_id,
            chapter_number=chapter,
            agent="variant.generate",
            stage=f"slot-{slot_index}",
            version_id=version_id,
            prompt_tokens=int(slot_draft.prompt_tokens),
            completion_tokens=int(slot_draft.completion_tokens),
            cost_cny=cost,
            success=True,
        )
        written.append(variant)
        spent += cost
        logger.info(
            "variant.generate.slot",
            project_id=project_id,
            chapter=chapter,
            slot_index=slot_index,
            version_id=version_id,
            cost_cny_estimate=cost,
            spent=spent,
        )

    if (
        budget_cny is not None
        and len(written) < n
        and (budget_exhausted or spent >= budget_cny)
    ):
        budget_exhausted = True

    return GenerateResult(
        variants=written,
        fingerprint=fingerprint,
        budget_exhausted=budget_exhausted,
        n_requested=n,
    )
