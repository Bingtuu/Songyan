"""task 245 P2: variant generate 拒写质量门接线（判定 → 同槽重试 1 次 → 打标）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import songyan.db.connection as conn_mod
from songyan.db import ProjectRepository
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.migrations import init_schema
from songyan.models import ProjectSetting
from songyan.services.variant_generate import SlotDraft, generate_chapter_variants

GOOD = "夜色沉得像一块铁，" * 12  # 108 字，通过质量门
REFUSAL = "事实圣经不足，无法完成草稿。"  # <100 字 + 关键词
REFUSAL_2 = "仍然无法完成：缺少事实，暂不生成。"


@pytest.fixture
async def isolated_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    db_path = tmp_path / "variant_quality_gate.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
        ),
        "p-qg",
    )
    return db_path


def _seq_draft(
    drafts: list[SlotDraft], seen_kwargs: list[dict[str, Any]]
) -> Any:
    it = iter(drafts)

    async def _draft(**kwargs: Any) -> SlotDraft:
        seen_kwargs.append(kwargs)
        return next(it)

    return _draft


@pytest.mark.asyncio
async def test_refusal_retried_once_then_success_unflagged(
    isolated_db: Path,
) -> None:
    seen: list[dict[str, Any]] = []
    draft_fn = _seq_draft(
        [
            SlotDraft(content=REFUSAL, cost_cny_estimate=0.01),
            SlotDraft(content=GOOD, cost_cny_estimate=0.02),
        ],
        seen,
    )

    result = await generate_chapter_variants("p-qg", 3, n=1, draft_fn=draft_fn)

    assert len(result.variants) == 1
    variant = result.variants[0]
    assert variant.quality_flag is None
    assert len(seen) == 2
    assert seen[0].get("retry_reason") is None
    assert seen[1].get("retry_reason") == "refusal_keyword"
    loaded = await ChapterVariantRepository().get_by_slot("p-qg", 3, 1)
    assert loaded is not None
    assert loaded.quality_flag is None


@pytest.mark.asyncio
async def test_refusal_persists_after_retry_gets_flag(isolated_db: Path) -> None:
    seen: list[dict[str, Any]] = []
    draft_fn = _seq_draft(
        [
            SlotDraft(content=REFUSAL, cost_cny_estimate=0.01),
            SlotDraft(content=REFUSAL_2, cost_cny_estimate=0.02),
        ],
        seen,
    )

    result = await generate_chapter_variants("p-qg", 3, n=1, draft_fn=draft_fn)

    assert len(result.variants) == 1
    variant = result.variants[0]
    assert variant.quality_flag == "refusal_keyword"
    assert len(seen) == 2  # 恰好重试 1 次，不多
    loaded = await ChapterVariantRepository().get_by_slot("p-qg", 3, 1)
    assert loaded is not None
    assert loaded.quality_flag == "refusal_keyword"


@pytest.mark.asyncio
async def test_good_draft_not_retried(isolated_db: Path) -> None:
    seen: list[dict[str, Any]] = []
    draft_fn = _seq_draft(
        [SlotDraft(content=GOOD, cost_cny_estimate=0.01)], seen
    )

    result = await generate_chapter_variants("p-qg", 3, n=1, draft_fn=draft_fn)

    assert result.variants[0].quality_flag is None
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_slot_cost_sums_retry_attempts(isolated_db: Path) -> None:
    seen: list[dict[str, Any]] = []
    draft_fn = _seq_draft(
        [
            SlotDraft(content=REFUSAL, cost_cny_estimate=0.01),
            SlotDraft(content=GOOD, cost_cny_estimate=0.02),
        ],
        seen,
    )

    result = await generate_chapter_variants("p-qg", 3, n=1, draft_fn=draft_fn)

    assert result.variants[0].cost_cny_estimate == pytest.approx(0.03)
