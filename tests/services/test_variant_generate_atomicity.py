"""切片 4（task 226）：variant generate 每槽写入的原子性。

slot 的 ``chapter_versions`` + ``chapter_variants`` 两行写入必须同事务：
第二行失败时第一行不得残留（孤儿 draft version）。
"""

from __future__ import annotations

from pathlib import Path
from sqlite3 import IntegrityError
from typing import Any

import pytest

import songyan.db.connection as conn_mod
from songyan.db import ProjectRepository
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.migrations import init_schema
from songyan.db.repository import ChapterVersionRepository
from songyan.models import ProjectSetting
from songyan.services.variant_generate import SlotDraft, generate_chapter_variants


@pytest.fixture
async def isolated_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    db_path = tmp_path / "variant_atomic.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="wuxia",
            mode_id="webnovel",
            protagonist_name="顾长风",
        ),
        "p1",
    )
    return db_path


async def test_slot_write_is_atomic_no_orphan_version(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """第二槽 variant insert 撞唯一索引时，第一槽保留、第二槽 version 不留孤儿。"""
    drafts = iter(
        [
            SlotDraft(content="草稿一", cost_cny_estimate=0.01),
            SlotDraft(content="草稿二", cost_cny_estimate=0.01),
        ]
    )

    async def _draft(**_kwargs: Any) -> SlotDraft:
        return next(drafts)

    original_insert = ChapterVariantRepository.insert
    calls = {"n": 0}

    async def _flaky_insert(
        self: ChapterVariantRepository, variant: Any, **kwargs: Any
    ) -> Any:
        calls["n"] += 1
        if calls["n"] == 2:
            raise IntegrityError(
                "UNIQUE constraint failed: idx_chapter_variants_active_slot"
            )
        return await original_insert(self, variant, **kwargs)

    monkeypatch.setattr(ChapterVariantRepository, "insert", _flaky_insert)

    with pytest.raises(IntegrityError):
        await generate_chapter_variants("p1", 5, n=2, draft_fn=_draft)

    versions = await ChapterVersionRepository().list_by_chapter(
        "p1", 5, include_abandoned=True
    )
    assert len(versions) == 1
