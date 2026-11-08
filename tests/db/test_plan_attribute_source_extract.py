"""M2 step 5: plan_attributes.source CHECK includes extract; canon lists accept it."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from songyan.db.connection import get_db
from songyan.db.migrations import (
    _migrate_plan_attribute_source_extract,
    _plan_table_sql,
    init_schema,
    run_migrations,
)
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ProjectRepository
from songyan.models.plan_facts import PlanAttribute, PlanEntity
from songyan.models.project import ProjectSetting


@pytest.fixture
async def fact_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "extract-source.db"
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
        "p1",
    )
    return db_path


def _knife() -> PlanEntity:
    return PlanEntity(
        entity_id="ent-knife",
        project_id="p1",
        entity_type="object",
        aliases=["银刀"],
        approval_status="approved",
    )


def test_plan_attribute_accepts_extract_source() -> None:
    attr = PlanAttribute(
        attribute_id="attr-ext",
        project_id="p1",
        entity_id="ent-knife",
        key="direction",
        value="东",
        source="extract",
        approval_status="pending",
    )
    assert attr.source == "extract"


def test_plan_attribute_still_rejects_extracted_typo() -> None:
    with pytest.raises(ValidationError):
        PlanAttribute.model_validate(
            {
                "attribute_id": "attr-bad",
                "project_id": "p1",
                "entity_id": "ent-knife",
                "key": "direction",
                "value": "东",
                "source": "extracted",
            }
        )


@pytest.mark.asyncio
async def test_fresh_schema_source_check_allows_extract(fact_db: Path) -> None:
    async with get_db() as conn:
        sql = await _plan_table_sql(conn, "plan_attributes")
    assert sql is not None
    assert "'extract'" in sql
    assert "'plan'" in sql
    assert "'human'" in sql


@pytest.mark.asyncio
async def test_migration_rebuilds_old_source_check_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate pre-extract CHECK and ensure rebuild accepts extract, keeps rows."""
    import aiosqlite

    import songyan.db.connection as conn_mod

    db_path = tmp_path / "old-source.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = OFF")
        await conn.execute("ALTER TABLE plan_attributes RENAME TO plan_attributes__old")
        await conn.execute(
            """CREATE TABLE plan_attributes (
            attribute_id     TEXT PRIMARY KEY,
            project_id       TEXT NOT NULL,
            entity_id        TEXT NOT NULL,
            key              TEXT NOT NULL,
            value            TEXT NOT NULL,
            valid_from_ch    INTEGER,
            valid_to_ch      INTEGER,
            source           TEXT NOT NULL CHECK (source IN ('plan', 'human')),
            approval_status  TEXT NOT NULL DEFAULT 'approved'
                             CHECK (approval_status IN ('approved', 'pending', 'rejected')),
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
        )
        await conn.execute(
            """INSERT INTO plan_attributes (
                attribute_id, project_id, entity_id, key, value, source, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("attr-keep", "p1", "ent-knife", "direction", "东", "plan", "approved"),
        )
        await conn.execute("DROP TABLE plan_attributes__old")
        await conn.commit()
        await conn.execute("PRAGMA foreign_keys = ON")

        sql_before = await _plan_table_sql(conn, "plan_attributes")
        assert sql_before is not None
        assert "'extract'" not in sql_before

        await _migrate_plan_attribute_source_extract(conn)
        await conn.commit()
        sql_after = await _plan_table_sql(conn, "plan_attributes")
        assert sql_after is not None
        assert "'extract'" in sql_after

        await conn.execute(
            """INSERT INTO plan_attributes (
                attribute_id, project_id, entity_id, key, value, source, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("attr-ext", "p1", "ent-knife", "owner", "陈照", "extract", "pending"),
        )
        await conn.commit()

        await _migrate_plan_attribute_source_extract(conn)
        await conn.commit()

        cur = await conn.execute(
            "SELECT attribute_id, source FROM plan_attributes ORDER BY attribute_id"
        )
        rows = await cur.fetchall()
        assert rows == [("attr-ext", "extract"), ("attr-keep", "plan")]


@pytest.mark.asyncio
async def test_pending_extract_not_in_canon_approved_extract_is(
    fact_db: Path,
) -> None:
    repo = PlanFactRepository()
    await repo.write_entity(_knife())
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-pending-ext",
            project_id="p1",
            entity_id="ent-knife",
            key="direction",
            value="东",
            source="extract",
            approval_status="pending",
            valid_from_ch=1,
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-approved-ext",
            project_id="p1",
            entity_id="ent-knife",
            key="owner",
            value="陈照",
            source="extract",
            approval_status="approved",
            valid_from_ch=1,
        )
    )

    canon_ids = [a.attribute_id for a in await repo.list_canon_attributes("p1")]
    pending_ids = [a.attribute_id for a in await repo.list_pending_attributes("p1")]
    assert "attr-pending-ext" not in canon_ids
    assert "attr-approved-ext" in canon_ids
    assert "attr-pending-ext" in pending_ids
    canon_attrs = await repo.list_canon_attributes("p1")
    approved = next(a for a in canon_attrs if a.attribute_id == "attr-approved-ext")
    assert approved.source == "extract"


@pytest.mark.asyncio
async def test_run_migrations_registers_extract_migration(fact_db: Path) -> None:
    import songyan.db.migrations as migrations_mod

    names = [name for name, _ in migrations_mod._MIGRATIONS]
    assert "_migrate_plan_attribute_source_extract" in names

    async with get_db() as conn:
        await run_migrations(conn)
        await conn.commit()
        sql = await _plan_table_sql(conn, "plan_attributes")
    assert sql is not None
    assert "'extract'" in sql


@pytest.mark.asyncio
async def test_check_still_rejects_unknown_source(fact_db: Path) -> None:
    repo = PlanFactRepository()
    await repo.write_entity(_knife())
    with pytest.raises(sqlite3.IntegrityError):
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO plan_attributes (
                    attribute_id, project_id, entity_id, key, value, source
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                ("attr-bad", "p1", "ent-knife", "direction", "东", "extracted"),
            )
            await conn.commit()
