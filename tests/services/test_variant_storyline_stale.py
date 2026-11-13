"""task 252：stale_vs_storyline 懒刷新 + generate 落指纹（tech-m4-followup-s5 §3.3）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import songyan.db.connection as conn_mod
from songyan.db import ProjectRepository
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.models import ProjectSetting
from songyan.models.narrative import ArcPlan
from songyan.models.variant import ChapterVariant
from songyan.services.storyline_fingerprint import storyline_fingerprint
from songyan.services.variant_generate import SlotDraft, generate_chapter_variants
from songyan.services.variant_stale import refresh_stale_vs_storyline

GOOD = "夜色沉得像一块铁，" * 12  # 108 字，过 245 质量门


@pytest.fixture
async def story_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> str:
    db_path = tmp_path / "storyline_stale.db"
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
        "p-story",
    )
    return "p-story"


async def _seed_arc(pid: str, goal: str = "弧目标") -> None:
    await NarrativeRepository().add_arc_plan(
        ArcPlan(
            arc_id="arc-1",
            project_id=pid,
            arc_index=0,
            start_chapter=1,
            end_chapter=10,
            arc_goal=goal,
        )
    )


async def _seed_variant(
    pid: str,
    ch: int,
    slot: int,
    *,
    stale: int = 0,
    storyline_fp: str | None,
) -> ChapterVariant:
    row = ChapterVariant(
        variant_id=f"var-s{slot}",
        project_id=pid,
        chapter_number=ch,
        slot_index=slot,
        status="generated",
        parent_canon_fingerprint="fp-canon",
        content_ref=f"ver-s{slot}",
        stale_vs_storyline=stale,
        storyline_fingerprint=storyline_fp,
        created_at="2026-11-13T00:00:00Z",
        updated_at="2026-11-13T00:00:00Z",
    )
    await ChapterVariantRepository().insert(row)
    return row


class TestRefresh:
    async def test_null_fingerprint_backfilled_not_marked(
        self, story_db: str
    ) -> None:
        await _seed_arc(story_db)
        await _seed_variant(story_db, 5, 1, storyline_fp=None)
        current = await storyline_fingerprint(story_db, 5)

        marked = await refresh_stale_vs_storyline(story_db, 5)

        assert marked == 0  # B3：旧行只补指纹不标脏
        loaded = await ChapterVariantRepository().get_by_slot(story_db, 5, 1)
        assert loaded is not None
        assert loaded.storyline_fingerprint == current
        assert loaded.stale_vs_storyline == 0

    async def test_changed_fingerprint_marks_stale(self, story_db: str) -> None:
        await _seed_arc(story_db, goal="旧目标")
        await _seed_variant(story_db, 5, 1, storyline_fp=None)
        await refresh_stale_vs_storyline(story_db, 5)  # 建立基线

        await NarrativeRepository().update_arc_goal("arc-1", "新目标")
        marked = await refresh_stale_vs_storyline(story_db, 5)

        assert marked == 1
        loaded = await ChapterVariantRepository().get_by_slot(story_db, 5, 1)
        assert loaded is not None
        assert loaded.stale_vs_storyline == 1

    async def test_unchanged_fingerprint_no_op(self, story_db: str) -> None:
        await _seed_arc(story_db)
        await _seed_variant(story_db, 5, 1, storyline_fp=None)
        await refresh_stale_vs_storyline(story_db, 5)
        marked = await refresh_stale_vs_storyline(story_db, 5)
        assert marked == 0

    async def test_already_stale_stays_and_fp_synced(self, story_db: str) -> None:
        await _seed_arc(story_db, goal="旧目标")
        await _seed_variant(
            story_db, 5, 1, stale=1, storyline_fp="fp-旧"
        )
        await NarrativeRepository().update_arc_goal("arc-1", "又改了")
        marked = await refresh_stale_vs_storyline(story_db, 5)
        assert marked == 0  # 已标不重复计
        loaded = await ChapterVariantRepository().get_by_slot(story_db, 5, 1)
        assert loaded is not None
        assert loaded.stale_vs_storyline == 1
        assert loaded.storyline_fingerprint == await storyline_fingerprint(
            story_db, 5
        )

    async def test_non_covering_arc_change_does_not_mark(
        self, story_db: str
    ) -> None:
        """第 5 章的槽不受第 11-20 章弧改动影响（切片粒度）。"""
        await _seed_arc(story_db)
        await NarrativeRepository().add_arc_plan(
            ArcPlan(
                arc_id="arc-far",
                project_id=story_db,
                arc_index=1,
                start_chapter=11,
                end_chapter=20,
                arc_goal="远弧",
            )
        )
        await _seed_variant(story_db, 5, 1, storyline_fp=None)
        await refresh_stale_vs_storyline(story_db, 5)

        await NarrativeRepository().update_arc_goal("arc-far", "远弧改")
        marked = await refresh_stale_vs_storyline(story_db, 5)
        assert marked == 0


class TestGenerateWiring:
    async def test_generate_records_storyline_fingerprint(
        self, story_db: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        await _seed_arc(story_db)

        async def _draft(**_kwargs: Any) -> SlotDraft:
            return SlotDraft(content=GOOD, cost_cny_estimate=0.01)

        result = await generate_chapter_variants(
            story_db, 5, n=1, draft_fn=_draft
        )
        assert len(result.variants) == 1
        row = result.variants[0]
        assert row.stale_vs_storyline == 0
        assert row.storyline_fingerprint == await storyline_fingerprint(
            story_db, 5
        )

        # 故事线演进后再 generate：旧槽标脏，新槽干净
        await NarrativeRepository().update_arc_goal("arc-1", "演进后")
        result2 = await generate_chapter_variants(
            story_db, 5, n=1, draft_fn=_draft
        )
        old = await ChapterVariantRepository().get_by_slot(story_db, 5, 1)
        assert old is not None
        assert old.stale_vs_storyline == 1
        assert result2.variants[0].stale_vs_storyline == 0
