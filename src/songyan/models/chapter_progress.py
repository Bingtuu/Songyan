"""章进度视图模型（M4 步 1；tech-m4 B1 推导的可判定子集）。

六态（全局优先级自上而下首个匹配）：

- ``stale`` = 章已 accepted 且 ``content_stale=1``
- ``settled`` = 章已 accepted 且 ``content_stale=0``（accepted 系吸收所有 accepted 章）
- ``picked`` = 未 accepted 且存在 ``status='picked'`` 槽
- ``variants_ready`` = 未 accepted、无 picked 槽、存在活动 ``generated`` 槽
- ``drafting`` = 未 accepted、无活动 variant、存在版本（head 工作指针或版本表有行）
- ``empty`` = 以上皆否（head 双指针 NULL 且无版本/variant 的罕见行）

「已 accepted」按 B1 口径 = ``chapter_heads.accepted_version_id IS NOT NULL``。
不可判定态（outlined / human_rewriting / in_review / needs_settlement）不映射。
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel, Field

from songyan.models.chapter import ChapterHead
from songyan.models.variant import ChapterVariant


class ChapterProgressState(StrEnum):
    """六态；值即 ``status`` / JSON 输出中的字符串。"""

    STALE = "stale"
    SETTLED = "settled"
    PICKED = "picked"
    VARIANTS_READY = "variants_ready"
    DRAFTING = "drafting"
    EMPTY = "empty"


#: accepted 系两态（B1「下一章」= 第一个非 accepted 章）。
ACCEPTED_STATES: frozenset[ChapterProgressState] = frozenset(
    {ChapterProgressState.STALE, ChapterProgressState.SETTLED}
)

#: 渲染顺序 = 全局优先级顺序（accepted 系 > picked > variants_ready > drafting > empty）。
STATE_PRIORITY: tuple[ChapterProgressState, ...] = (
    ChapterProgressState.STALE,
    ChapterProgressState.SETTLED,
    ChapterProgressState.PICKED,
    ChapterProgressState.VARIANTS_READY,
    ChapterProgressState.DRAFTING,
    ChapterProgressState.EMPTY,
)


def derive_chapter_progress(
    head: ChapterHead | None,
    variants: Sequence[ChapterVariant] = (),
    *,
    has_version: bool = False,
) -> ChapterProgressState:
    """纯函数：由 head（可 None）+ 该章 variant 槽 + 版本存在性推导单章进度态。

    无写库、无 IO，输入全部来自调用方已读出的行。
    """
    if head is not None and head.accepted_version_id is not None:
        if head.content_stale == 1:
            return ChapterProgressState.STALE
        return ChapterProgressState.SETTLED
    if any(variant.status == "picked" for variant in variants):
        return ChapterProgressState.PICKED
    if any(variant.status == "generated" for variant in variants):
        return ChapterProgressState.VARIANTS_READY
    if has_version or (head is not None and head.current_version_id is not None):
        return ChapterProgressState.DRAFTING
    return ChapterProgressState.EMPTY


class ChapterProgressEntry(BaseModel):
    """章宇宙中的一章及其推导态。"""

    chapter_number: int
    state: ChapterProgressState


class ChapterProgressSummary(BaseModel):
    """项目级章进度视图（章宇宙 = heads ∪ variants ∪ versions 的章号并集）。"""

    project_id: str
    chapters: list[ChapterProgressEntry] = Field(default_factory=list)
    distribution: dict[ChapterProgressState, int]
    #: 待确认 picked 数（处于 picked 态的章数，均未被 accept）。
    pending_confirm: int
    #: B1 口径「下一章」：章号升序第一个非 accepted 章；全 accepted 为 None。
    next_chapter: int | None = None
    next_state: ChapterProgressState | None = None


class ContextEmergencySummary(BaseModel):
    """ContextEmergency 触发统计（读 ``context_snapshots``；B10）。"""

    count: int = 0
    last_chapter: int | None = None
    budget_used_before: float | None = None
