"""M3 step 1: chapter_variants migration + repo insert/list + single-picked guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
from songyan.db.migrations import _EXPECTED_TABLES, init_schema, run_migrations
from songyan.db.repository import ProjectRepository
from songyan.exceptions import DuplicatePickedVariantError
from songyan.models.project import ProjectSetting
from songyan.models.variant import ChapterVariant


@pytest.fixture
async def variant_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "variants.db"
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
        "p-var",
    )
    return db_path


def _row(
    *,
    variant_id: str,
    slot: int,
    status: str = "generated",
    content_ref: str | None = None,
) -> ChapterVariant:
    return ChapterVariant(
        variant_id=variant_id,
        project_id="p-var",
        chapter_number=1,
        slot_index=slot,
        status=status,  # type: ignore[arg-type]
        parent_canon_fingerprint="fp-aaa",
        content_ref=content_ref or f"ver-{variant_id}",
        created_at="2026-11-06T00:00:00Z",
        updated_at="2026-11-06T00:00:00Z",
    )


@pytest.mark.asyncio
async def test_chapter_variants_in_expected_tables(variant_db: Path) -> None:
    assert "chapter_variants" in _EXPECTED_TABLES
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chapter_variants'"
        )
        assert await cursor.fetchone() is not None


@pytest.mark.asyncio
async def test_migrate_chapter_variants_idempotent(variant_db: Path) -> None:
    async with get_db() as conn:
        await run_migrations(conn)
        await conn.commit()
        await run_migrations(conn)
        await conn.commit()
        cursor = await conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='chapter_variants'"
        )
        row = await cursor.fetchone()
    assert row is not None
    assert "parent_canon_fingerprint" in row[0]
    assert "stale_vs_canon" in row[0]


@pytest.mark.asyncio
async def test_insert_and_list_for_chapter(variant_db: Path) -> None:
    repo = ChapterVariantRepository()
    await repo.insert(_row(variant_id="v1", slot=1))
    await repo.insert(_row(variant_id="v2", slot=2))
    rows = await repo.list_for_chapter("p-var", 1)
    assert [r.variant_id for r in rows] == ["v1", "v2"]
    assert await repo.list_for_chapter("p-var", 2) == []


@pytest.mark.asyncio
async def test_double_picked_insert_fails(variant_db: Path) -> None:
    repo = ChapterVariantRepository()
    await repo.insert(_row(variant_id="v-pick-1", slot=1, status="picked"))
    with pytest.raises(DuplicatePickedVariantError):
        await repo.insert(_row(variant_id="v-pick-2", slot=2, status="picked"))
    rows = await repo.list_for_chapter("p-var", 1)
    assert len(rows) == 1
    assert rows[0].status == "picked"


@pytest.mark.asyncio
async def test_generated_then_one_picked_ok(variant_db: Path) -> None:
    repo = ChapterVariantRepository()
    await repo.insert(_row(variant_id="v-g1", slot=1, status="generated"))
    await repo.insert(_row(variant_id="v-p1", slot=2, status="picked"))
    rows = await repo.list_for_chapter("p-var", 1)
    assert {r.status for r in rows} == {"generated", "picked"}


@pytest.mark.asyncio
async def test_quality_flag_column_exists(variant_db: Path) -> None:
    """task 245: chapter_variants.quality_flag 可空列（NULL = 通过质量门）。"""
    async with get_db() as conn:
        cursor = await conn.execute("PRAGMA table_info(chapter_variants)")
        cols = {row[1] for row in await cursor.fetchall()}
    assert "quality_flag" in cols


@pytest.mark.asyncio
async def test_quality_flag_migration_repairs_dropped_column(
    variant_db: Path,
) -> None:
    """旧库（无该列）重跑 run_migrations 后列被补回；幂等。"""
    async with get_db() as conn:
        await conn.execute(
            "ALTER TABLE chapter_variants DROP COLUMN quality_flag"
        )
        await conn.commit()
        await run_migrations(conn)
        await conn.commit()
        cursor = await conn.execute("PRAGMA table_info(chapter_variants)")
        cols = {row[1] for row in await cursor.fetchall()}
        assert "quality_flag" in cols
        # 幂等：再跑一次不炸
        await run_migrations(conn)
        await conn.commit()


@pytest.mark.asyncio
async def test_quality_flag_roundtrip(variant_db: Path) -> None:
    repo = ChapterVariantRepository()
    flagged = _row(variant_id="var-q1", slot=1)
    flagged.quality_flag = "too_short"
    await repo.insert(flagged)
    plain = _row(variant_id="var-q2", slot=2)
    await repo.insert(plain)

    loaded = await repo.get_by_slot("p-var", 1, 1)
    assert loaded is not None
    assert loaded.quality_flag == "too_short"
    loaded_plain = await repo.get_by_slot("p-var", 1, 2)
    assert loaded_plain is not None
    assert loaded_plain.quality_flag is None
