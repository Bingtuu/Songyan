"""B1 前置①过滤级语义（task 244 / tech-m4 B1 章级口径）。

`_prior_unaccepted_picked` 只拦「目标章之前**未 accepted**且残留 picked 槽」的章；
已 accepted 章的残留 picked 槽（M3 pick 不改 variant 行的可达形态）不阻塞 continue。
"""

from __future__ import annotations

from songyan.models.variant import ChapterVariant
from songyan.services.chapter_continue import _prior_unaccepted_picked

_TS = "2026-11-11T00:00:00Z"


def _picked(chapter: int, slot: int) -> ChapterVariant:
    return ChapterVariant(
        variant_id=f"var-{chapter}-{slot}",
        project_id="p",
        chapter_number=chapter,
        slot_index=slot,
        status="picked",
        parent_canon_fingerprint="fp",
        content_ref=f"v-{chapter}-{slot}",
        created_at=_TS,
        updated_at=_TS,
    )


def test_residual_picked_on_accepted_chapter_returns_none() -> None:
    """已 accepted 章的 picked 槽不阻塞（冒烟发现 5 的核心回归）。"""
    slots = [_picked(1, 1)]
    assert _prior_unaccepted_picked(slots, accepted_chapters={1}, target=2) is None


def test_picked_on_unaccepted_prior_chapter_blocks() -> None:
    """目标章之前存在未 accepted 且 picked 的章 → 返回该槽（防御未来口径变化）。"""
    slots = [_picked(1, 1)]
    found = _prior_unaccepted_picked(slots, accepted_chapters=set(), target=2)
    assert found is not None
    assert found.chapter_number == 1


def test_picked_on_target_chapter_not_in_scope() -> None:
    """目标章自身的 picked 由前置②管，不在前置①范围。"""
    slots = [_picked(2, 1)]
    assert _prior_unaccepted_picked(slots, accepted_chapters={1}, target=2) is None


def test_no_picked_slots_returns_none() -> None:
    assert _prior_unaccepted_picked([], accepted_chapters=set(), target=3) is None
