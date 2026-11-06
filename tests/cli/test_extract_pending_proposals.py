"""M2 step 5: settlement/import extract → plan_* pending (source=extract) + S8."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.agents.settlement_extractor import apply_settlement
from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.settlement_repo import (
    UNTRUSTED_UNTIL_CONFIRMED,
    SettingSnapshotRepository,
)
from songyan.models import (
    ChapterVersion,
    Character,
    CharacterUpdate,
    NewSetting,
    ProjectSetting,
    StateSettlement,
)
from songyan.plan_checks.bible import load_chapter_plan_bible

_PROJECT_ID = "p-extract-m2"
_CHAR_ID = "char-chen"
_ATTR_KEY = "location"
_SETTING_KEY = "mystery.rule.token_return"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def extract_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "extract-pending.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="extract pending",
        ),
        _PROJECT_ID,
    )
    await CharacterRepository().create(
        Character(
            character_id=_CHAR_ID,
            project_id=_PROJECT_ID,
            name="陈照",
            role_type="protagonist",
        )
    )
    return db_path


def _settlement_with_char_update() -> StateSettlement:
    return StateSettlement(
        validation_status="valid",
        character_updates=[
            CharacterUpdate(
                character_id=_CHAR_ID,
                field=_ATTR_KEY,
                old_value="霞飞路",
                new_value="外滩",
                source_quote="陈照走到了外滩",
            )
        ],
        new_settings=[
            NewSetting(
                setting_name="铜牌交还规则",
                description="交还须面朝东",
                source_quote="交还须面朝东",
                setting_key=_SETTING_KEY,
            )
        ],
    )


async def _seed_version(version_id: str, chapter_number: int) -> None:
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=_PROJECT_ID,
            chapter_number=chapter_number,
            version_number=1,
            version_type="accepted",
            content="陈照走到了外滩。交还须面朝东。",
            word_count=12,
        )
    )


async def _apply(chapter_number: int, version_id: str) -> None:
    await _seed_version(version_id, chapter_number)
    settlement = _settlement_with_char_update()
    async with get_db() as conn:
        await apply_settlement(
            settlement,
            _PROJECT_ID,
            chapter_number=chapter_number,
            version_id=version_id,
            conn=conn,
            content="陈照走到了外滩。交还须面朝东。",
        )
        await conn.commit()


@pytest.mark.asyncio
async def test_apply_settlement_enqueues_pending_extract_not_canon(
    extract_db: Path,
) -> None:
    await _apply(2, "v-extract-2")

    repo = PlanFactRepository()
    pending = await repo.list_pending_attributes(_PROJECT_ID)
    canon = await repo.list_canon_attributes(_PROJECT_ID)
    assert pending, "extract path must enqueue pending plan attributes"
    assert all(a.source == "extract" for a in pending)
    assert all(a.approval_status == "pending" for a in pending)
    assert canon == []

    loc = [a for a in pending if a.key == _ATTR_KEY and a.entity_id == _CHAR_ID]
    assert len(loc) == 1
    assert loc[0].value == "外滩"
    assert loc[0].valid_from_ch == 2

    settings_pending = [a for a in pending if a.key == "description"]
    assert settings_pending, "new_settings must enqueue pending extract attributes"

    bible = await load_chapter_plan_bible(_PROJECT_ID, 2)
    for attr in pending:
        assert attr.attribute_id not in bible.attribute_ids
        assert attr.value not in bible.text
    assert "外滩" not in bible.text


@pytest.mark.asyncio
async def test_apply_settlement_never_approves_plan_rows(extract_db: Path) -> None:
    await _apply(3, "v-extract-3")

    repo = PlanFactRepository()
    async with get_db() as conn:
        cur = await conn.execute(
            """SELECT approval_status, source FROM plan_attributes
               WHERE project_id = ?""",
            (_PROJECT_ID,),
        )
        rows = await cur.fetchall()
    assert rows, "expected extract proposals"
    assert all(status == "pending" for status, _source in rows)
    assert all(source == "extract" for _status, source in rows)
    assert await repo.list_canon_attributes(_PROJECT_ID) == []


def test_confirm_extract_enters_canon_source_stays_extract(
    runner: CliRunner, extract_db: Path
) -> None:
    asyncio.run(_apply(2, "v-extract-2"))

    repo = PlanFactRepository()
    pending = asyncio.run(repo.list_pending_attributes(_PROJECT_ID))
    target = next(a for a in pending if a.key == _ATTR_KEY)
    assert target.source == "extract"

    result = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "attribute",
            "--project-id",
            _PROJECT_ID,
            "--attribute-id",
            target.attribute_id,
        ],
    )
    assert result.exit_code == 0, result.output
    assert "source=extract" in result.output

    canon = asyncio.run(repo.list_canon_attributes(_PROJECT_ID))
    assert any(a.attribute_id == target.attribute_id for a in canon)
    confirmed = next(a for a in canon if a.attribute_id == target.attribute_id)
    assert confirmed.source == "extract"
    assert confirmed.approval_status == "approved"

    # Bible only includes attributes on entities referenced by chapter events;
    # canon visibility is the hard gate for extract confirm (tech-m2 §4.4).
    assert confirmed.value == "外滩"
    still_pending_ids = [
        a.attribute_id
        for a in asyncio.run(repo.list_pending_attributes(_PROJECT_ID))
    ]
    assert target.attribute_id not in still_pending_ids


@pytest.mark.asyncio
async def test_settlement_tables_remain_untrusted_tag(extract_db: Path) -> None:
    assert UNTRUSTED_UNTIL_CONFIRMED == "untrusted_until_confirmed"
    await _apply(1, "v-extract-1")

    settings_rows = await SettingSnapshotRepository().list_by_project(_PROJECT_ID)
    assert settings_rows, "old settlement setting table must still receive rows"
    doc = SettingSnapshotRepository.list_by_project.__doc__ or ""
    assert UNTRUSTED_UNTIL_CONFIRMED in doc


def test_pending_extract_visible_in_canon_show_pending_not_canon_section(
    runner: CliRunner, extract_db: Path
) -> None:
    attr_id = asyncio.run(_seed_and_attr_id())
    show = runner.invoke(cli, ["canon", "show", "--project-id", _PROJECT_ID])
    assert show.exit_code == 0, show.output
    canon = show.output.split("# Pending（不是 Canon）")[0]
    pending = show.output.split("# Pending（不是 Canon）")[1].split("# Storyline")[0]
    assert attr_id not in canon
    assert attr_id in pending


async def _seed_and_attr_id() -> str:
    await _apply(2, "v-extract-2")
    pending = await PlanFactRepository().list_pending_attributes(_PROJECT_ID)
    return next(a.attribute_id for a in pending if a.key == _ATTR_KEY)
