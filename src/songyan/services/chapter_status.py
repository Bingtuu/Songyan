"""tech-m4-followup 步 1：``chapter status`` 只读章进度面（B1/B2）。纯只读。

不承载 ContextEmergency（tech-m4 B10 分工句：它只挂项目级 ``status``）。
不触发 ``refresh_stale_vs_canon`` 懒标定——status 是观察面不是结算面，
stale 读当前值。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.models.chapter_progress import (
    ChapterProgressState,
    derive_chapter_progress,
)
from songyan.models.variant import ChapterVariant
from songyan.services.review_report import (
    build_chapter_review,
    list_chapter_universe,
)

_FINDING_SEVERITIES = ("hard", "warning", "info")


class ChapterStatusReport(BaseModel):
    """一章的只读进度面（中薄面，tech-m4-followup §3.2）。"""

    project_id: str
    chapter: int
    state: ChapterProgressState
    has_head: bool = True
    current_version_id: str | None = None
    accepted_version_id: str | None = None
    content_stale: int = 0
    variants: list[ChapterVariant] = Field(default_factory=list)
    slot_cost_sum: float = 0.0
    llm_cost_sum: float = 0.0
    review_findings: dict[str, int] = Field(default_factory=dict)
    edit_ratio: float | None = None


async def load_chapter_status(
    project_id: str, chapter: int
) -> ChapterStatusReport | None:
    """组装一章的只读进度面；章不在章宇宙（heads 口径，同 ``review``）返回 None。

    全程只读，零写库。
    """
    if chapter < 1:
        raise ValueError("chapter must be >= 1")

    universe = await list_chapter_universe(project_id)
    if chapter not in universe:
        return None

    head = await ChapterHeadRepository().get(project_id, chapter)
    variants = await ChapterVariantRepository().list_for_chapter(project_id, chapter)
    has_version = bool(
        await ChapterVersionRepository().list_by_chapter(
            project_id, chapter, include_abandoned=True
        )
    )
    state = derive_chapter_progress(head, variants, has_version=has_version)

    llm_cost_sum = 0.0
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(cost_cny), 0.0) FROM llm_call_usage "
            "WHERE project_id = ? AND chapter_number = ?",
            (project_id, chapter),
        )
        row = await cursor.fetchone()
        if row is not None:
            llm_cost_sum = float(row[0] or 0.0)

    review = await build_chapter_review(project_id, chapter)
    findings = {sev: 0 for sev in _FINDING_SEVERITIES}
    for finding in review.findings:
        findings[finding.severity] = findings.get(finding.severity, 0) + 1

    # task 253 / S5：settled/stale 章现算人改率（同 accept 口径：edited 行
    # 上溯一级比原工作稿；纯复制比 parent draft 恒 0）。
    edit_ratio: float | None = None
    if head is not None and head.accepted_version_id:
        versions = ChapterVersionRepository()
        accepted_row = await versions.get(head.accepted_version_id)
        if accepted_row is not None and accepted_row.parent_version_id:
            from songyan.services.human_edit import compute_edit_ratio

            parent_row = await versions.get(accepted_row.parent_version_id)
            if parent_row is not None and parent_row.version_type == "edited":
                original = (
                    await versions.get(parent_row.parent_version_id)
                    if parent_row.parent_version_id
                    else None
                )
                if original is not None:
                    edit_ratio = compute_edit_ratio(
                        original.content, parent_row.content
                    )
            elif parent_row is not None:
                edit_ratio = compute_edit_ratio(
                    parent_row.content, accepted_row.content
                )

    return ChapterStatusReport(
        project_id=project_id,
        chapter=chapter,
        state=state,
        has_head=head is not None,
        current_version_id=None if head is None else head.current_version_id,
        accepted_version_id=None if head is None else head.accepted_version_id,
        content_stale=0 if head is None else int(head.content_stale),
        variants=variants,
        slot_cost_sum=sum(v.cost_cny_estimate for v in variants),
        llm_cost_sum=llm_cost_sum,
        review_findings=findings,
        edit_ratio=edit_ratio,
    )
