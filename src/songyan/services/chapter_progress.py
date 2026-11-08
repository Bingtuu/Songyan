"""章进度视图服务（M4 步 1；tech-m4 §5 步 1 / B1 / B10）。纯只读。"""

from __future__ import annotations

from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ContextSnapshotRepository,
)
from songyan.models.chapter_progress import (
    ACCEPTED_STATES,
    ChapterProgressEntry,
    ChapterProgressState,
    ChapterProgressSummary,
    ContextEmergencySummary,
    derive_chapter_progress,
)
from songyan.models.variant import ChapterVariant


async def load_chapter_progress(project_id: str) -> ChapterProgressSummary:
    """组装项目级章进度视图；章宇宙 = heads ∪ variants ∪ versions 章号并集。

    全程只读；不虚构 ``1..max_chapter``。
    """
    heads = await ChapterHeadRepository().list_by_project(project_id)
    variants = await ChapterVariantRepository().list_by_project(project_id)
    version_chapters = set(
        await ChapterVersionRepository().list_chapter_numbers_by_project(project_id)
    )

    variants_by_chapter: dict[int, list[ChapterVariant]] = {}
    for row in variants:
        variants_by_chapter.setdefault(row.chapter_number, []).append(row)
    heads_by_chapter = {head.chapter_number: head for head in heads}

    universe = set(heads_by_chapter) | set(variants_by_chapter) | version_chapters

    chapters: list[ChapterProgressEntry] = []
    for number in sorted(universe):
        state = derive_chapter_progress(
            heads_by_chapter.get(number),
            variants_by_chapter.get(number, ()),
            has_version=number in version_chapters,
        )
        chapters.append(ChapterProgressEntry(chapter_number=number, state=state))

    distribution = {state: 0 for state in ChapterProgressState}
    for entry in chapters:
        distribution[entry.state] += 1

    pending_confirm = sum(
        1 for entry in chapters if entry.state == ChapterProgressState.PICKED
    )
    nxt = next((entry for entry in chapters if entry.state not in ACCEPTED_STATES), None)
    return ChapterProgressSummary(
        project_id=project_id,
        chapters=chapters,
        distribution=distribution,
        pending_confirm=pending_confirm,
        next_chapter=None if nxt is None else nxt.chapter_number,
        next_state=None if nxt is None else nxt.state,
    )


async def load_context_emergency(project_id: str) -> ContextEmergencySummary:
    """ContextEmergency 触发次数 / 最近触发章 / 触发前预算（B10）。只读。"""
    rows = await ContextSnapshotRepository().list_by_project(project_id)
    emergency_rows = [row for row in rows if row.context_emergency]
    if not emergency_rows:
        return ContextEmergencySummary()
    last = emergency_rows[-1]
    return ContextEmergencySummary(
        count=len(emergency_rows),
        last_chapter=last.chapter_number,
        budget_used_before=last.budget_used_before_emergency,
    )
