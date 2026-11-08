"""M0 workbench CLI: ``canon show`` and ``today`` (read-only)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.plan_fact_loader import (
    DUSHI_LINGYI_PROJECT_ID,
    bundled_dushi_lingyi_fixture,
    load_plan_fact_fixture,
)
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline
from songyan.models.plan_facts import PlanEntity
from songyan.models.variant import ChapterVariant
from songyan.plan_checks.bible import load_chapter_plan_bible

_PENDING_ID = "dly-pending-not-canon"
_CONFLICT = "只属于故事线的冲突句甲"
_ARC_ID = "dly-arc-storyline-only"
_THREAD_ID = "dly-thread-storyline-only"
_APPROVED = {
    "entity": "dly-shen",
    "attribute": "dly-attr-notch-direction",
    "event": "dly-evt-ch1-intake",
    "time_anchor": "dly-ta-day",
    "clue": "dly-clue-notch",
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def dushi_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """都市灵异夹具，外加一条测试自己写入的 pending 实体."""
    db_path = tmp_path / "workbench.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
    await PlanFactRepository().write_entity(
        PlanEntity(
            entity_id=_PENDING_ID,
            project_id=DUSHI_LINGYI_PROJECT_ID,
            entity_type="prop",
            approval_status="pending",
        )
    )
    return db_path


@pytest.fixture
async def dushi_with_storyline(dushi_db: Path) -> Path:
    """测试夹具写入大纲、弧和线索。命令本身不得写这些表."""
    repo = NarrativeRepository()
    await repo.upsert_outline(
        StoryOutline(project_id=DUSHI_LINGYI_PROJECT_ID, core_conflict=_CONFLICT)
    )
    await repo.add_arc_plan(
        ArcPlan(
            arc_id=_ARC_ID,
            project_id=DUSHI_LINGYI_PROJECT_ID,
            arc_index=0,
            start_chapter=1,
            end_chapter=3,
            arc_goal="弧目标不进Canon",
        )
    )
    await repo.add_thread(
        PlotThread(
            thread_id=_THREAD_ID,
            project_id=DUSHI_LINGYI_PROJECT_ID,
            title="线索标题不进Canon",
            status="opened",
        )
    )
    return dushi_db


def _between(text: str, start: str, end: str | None) -> str:
    begin = text.index(start) + len(start)
    if end is None:
        return text[begin:]
    return text[begin : text.index(end, begin)]


async def _storyline_counts() -> tuple[int, int, int]:
    async with get_db() as conn:
        counts: list[int] = []
        for table in ("story_outlines", "arc_plans", "plot_threads"):
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            counts.append(int(row[0]))
    return counts[0], counts[1], counts[2]


async def _entity_count() -> int:
    async with get_db() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM plan_entities")
        row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


def test_canon_show_splits_approved_and_pending(
    runner: CliRunner, dushi_db: Path
) -> None:
    before = asyncio.run(_entity_count())
    result = runner.invoke(
        cli,
        ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID],
    )
    after = asyncio.run(_entity_count())

    assert result.exit_code == 0, result.output
    canon = _between(result.output, "# Canon（approved）", "# Pending（不是 Canon）")
    pending = _between(
        result.output,
        "# Pending（不是 Canon）",
        "# Storyline（规划骨架，不是已确认事实）",
    )
    storyline = _between(result.output, "# Storyline（规划骨架，不是已确认事实）", None)

    for kind, card_id in _APPROVED.items():
        assert f"## {kind}" in canon
        assert card_id in canon
        assert card_id not in pending
    assert _PENDING_ID not in canon
    assert _PENDING_ID in pending
    assert "approval_status=pending" in pending
    assert "approval_status=pending" not in canon
    assert storyline.strip() == "（空）"
    assert after == before

    bible = asyncio.run(load_chapter_plan_bible(DUSHI_LINGYI_PROJECT_ID, 1))
    assert "dly-shen" in bible.entity_ids
    assert _PENDING_ID not in bible.entity_ids
    assert _PENDING_ID not in bible.text


def test_canon_show_storyline_is_not_canon(
    runner: CliRunner, dushi_with_storyline: Path
) -> None:
    before = asyncio.run(_storyline_counts())
    result = runner.invoke(
        cli,
        ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID],
    )
    after = asyncio.run(_storyline_counts())

    assert result.exit_code == 0, result.output
    canon = _between(result.output, "# Canon（approved）", "# Pending（不是 Canon）")
    storyline = _between(result.output, "# Storyline（规划骨架，不是已确认事实）", None)
    assert _CONFLICT in storyline
    assert "arcs: 1" in storyline
    assert "opened=1" in storyline
    assert "approval_status" not in storyline
    assert _CONFLICT not in canon
    assert "dly-shen" in canon
    assert after == before


def test_canon_show_json_storyline_empty(runner: CliRunner, dushi_db: Path) -> None:
    result = runner.invoke(
        cli,
        ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID, "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert set(payload) == {"project_id", "canon", "pending", "storyline"}
    assert payload["storyline"] == {"outline": None, "arcs": [], "threads": []}


def test_canon_show_json_storyline_filled(
    runner: CliRunner, dushi_with_storyline: Path
) -> None:
    result = runner.invoke(
        cli,
        ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID, "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["storyline"]["outline"]["core_conflict"] == _CONFLICT
    assert payload["storyline"]["arcs"][0]["arc_id"] == _ARC_ID
    assert payload["storyline"]["threads"][0]["thread_id"] == _THREAD_ID
    assert payload["storyline"]["threads"][0]["status"] == "opened"
    assert _CONFLICT not in json.dumps(payload["canon"], ensure_ascii=False)


_NEXT = (
    "可用 canon confirm 入典或销账承诺；硬确认可用 --hard/--mark-stale；"
    "章内草稿走 variant generate 抽卡（默认 N=2，不 auto-pick）。"
)
_PLAN_TABLES = (
    "plan_entities",
    "plan_attributes",
    "plan_events",
    "plan_time_anchors",
    "plan_clues",
)


async def _plan_table_counts() -> dict[str, int]:
    async with get_db() as conn:
        out: dict[str, int] = {}
        for table in _PLAN_TABLES:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            out[table] = int(row[0])
    return out


def test_today_counts_and_next_sentence(
    runner: CliRunner, dushi_with_storyline: Path
) -> None:
    before = asyncio.run(_plan_table_counts())
    result = runner.invoke(
        cli,
        ["today", "--project-id", DUSHI_LINGYI_PROJECT_ID],
    )
    after = asyncio.run(_plan_table_counts())

    assert result.exit_code == 0, result.output
    assert "canon_rows" in result.output
    assert "pending_rows" in result.output
    assert "storyline_arcs" in result.output
    assert "promise_planted: 0" in result.output
    assert "promise_due: 0" in result.output
    assert "promise_overdue: 0" in result.output
    assert _NEXT in result.output
    assert after == before


def test_today_json_shape(runner: CliRunner, dushi_with_storyline: Path) -> None:
    before = asyncio.run(_plan_table_counts())
    result = runner.invoke(
        cli,
        ["today", "--project-id", DUSHI_LINGYI_PROJECT_ID, "--json"],
    )
    after = asyncio.run(_plan_table_counts())

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert set(payload) == {
        "project_id",
        "canon_counts",
        "pending_counts",
        "promise_counts",
        "storyline",
        "next",
        "chapter_progress",
    }
    assert payload["chapter_progress"] == {
        "next_chapter": None,
        "next_state": None,
        "pending_confirm": 0,
        "counts": {
            "stale": 0,
            "settled": 0,
            "picked": 0,
            "variants_ready": 0,
            "drafting": 0,
            "empty": 0,
        },
    }
    assert payload["promise_counts"] == {"planted": 0, "due": 0, "overdue": 0}
    assert payload["project_id"] == DUSHI_LINGYI_PROJECT_ID
    assert payload["next"] == _NEXT
    for key in ("entity", "attribute", "event", "time_anchor", "clue"):
        assert key in payload["canon_counts"]
        assert key in payload["pending_counts"]
        assert isinstance(payload["canon_counts"][key], int)
        assert isinstance(payload["pending_counts"][key], int)
    assert payload["pending_counts"]["entity"] == 1
    assert payload["canon_counts"]["entity"] >= 1
    storyline = payload["storyline"]
    assert set(storyline) == {"has_outline", "arc_count", "thread_counts"}
    assert storyline["has_outline"] is True
    assert storyline["arc_count"] == 1
    assert storyline["thread_counts"]["opened"] == 1
    assert after == before


def test_canon_show_missing_db_exits_1_without_creating_file(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "no-such.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{missing}")
    assert not missing.exists()

    result = runner.invoke(cli, ["canon", "show", "--project-id", "any-id"])

    assert result.exit_code == 1, result.output
    assert "找不到数据库" in result.output
    assert not missing.exists()


def test_today_missing_db_exits_1_without_creating_file(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "no-such-today.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{missing}")
    assert not missing.exists()

    result = runner.invoke(cli, ["today", "--project-id", "any-id"])

    assert result.exit_code == 1, result.output
    assert "找不到数据库" in result.output
    assert not missing.exists()


@pytest.fixture
async def empty_schema_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Schema 已初始化，但没有任何项目行."""
    db_path = tmp_path / "empty-projects.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    return db_path


def test_canon_show_missing_project_exits_1(
    runner: CliRunner, empty_schema_db: Path
) -> None:
    result = runner.invoke(cli, ["canon", "show", "--project-id", "no-such-project"])

    assert result.exit_code == 1, result.output
    assert "项目不存在" in result.output
    assert "no-such-project" in result.output


def test_today_missing_project_exits_1(
    runner: CliRunner, empty_schema_db: Path
) -> None:
    result = runner.invoke(cli, ["today", "--project-id", "no-such-project"])

    assert result.exit_code == 1, result.output
    assert "项目不存在" in result.output
    assert "no-such-project" in result.output


# --- M4 步 1: today 章进度摘要（task 238；next 文案不动） --------------------

_PROGRESS_TABLES = (
    "chapter_heads",
    "chapter_variants",
    "chapter_versions",
    "context_snapshots",
)


async def _chapter_table_counts() -> dict[str, int]:
    async with get_db() as conn:
        out: dict[str, int] = {}
        for table in _PROGRESS_TABLES:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            out[table] = int(row[0])
    return out


async def _seed_chapter_progress() -> None:
    """ch1 accepted；ch2 两个 generated 槽（无 head）。"""
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="v-acc",
            project_id=DUSHI_LINGYI_PROJECT_ID,
            chapter_number=1,
            version_number=1,
            content="第1章定稿",
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=DUSHI_LINGYI_PROJECT_ID,
            chapter_number=1,
            current_version_id="v-acc",
            accepted_version_id="v-acc",
            content_stale=0,
        )
    )
    for slot in (1, 2):
        await ChapterVersionRepository().create(
            ChapterVersion(
                version_id=f"v-ch2-{slot}",
                project_id=DUSHI_LINGYI_PROJECT_ID,
                chapter_number=2,
                version_number=slot,
                content=f"第2章槽{slot}",
            )
        )
        await ChapterVariantRepository().insert(
            ChapterVariant(
                variant_id=f"var-ch2-{slot}",
                project_id=DUSHI_LINGYI_PROJECT_ID,
                chapter_number=2,
                slot_index=slot,
                status="generated",
                parent_canon_fingerprint="fp",
                content_ref=f"v-ch2-{slot}",
                created_at="2026-11-08T00:00:00Z",
                updated_at="2026-11-08T00:00:00Z",
            )
        )


@pytest.fixture
async def dushi_with_progress(dushi_db: Path) -> Path:
    await _seed_chapter_progress()
    return dushi_db


def test_today_chapter_progress_line(runner: CliRunner, dushi_with_progress: Path) -> None:
    before = asyncio.run(_chapter_table_counts())
    result = runner.invoke(
        cli,
        ["today", "--project-id", DUSHI_LINGYI_PROJECT_ID],
    )
    after = asyncio.run(_chapter_table_counts())

    assert result.exit_code == 0, result.output
    assert (
        "chapter_progress: next_chapter=2 next_state=variants_ready "
        "pending_confirm=0 stale=0 settled=1 picked=0 variants_ready=1 "
        "drafting=0 empty=0"
    ) in result.output
    assert _NEXT in result.output
    assert after == before


def test_today_json_chapter_progress(runner: CliRunner, dushi_with_progress: Path) -> None:
    before = asyncio.run(_chapter_table_counts())
    result = runner.invoke(
        cli,
        ["today", "--project-id", DUSHI_LINGYI_PROJECT_ID, "--json"],
    )
    after = asyncio.run(_chapter_table_counts())

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["chapter_progress"] == {
        "next_chapter": 2,
        "next_state": "variants_ready",
        "pending_confirm": 0,
        "counts": {
            "stale": 0,
            "settled": 1,
            "picked": 0,
            "variants_ready": 1,
            "drafting": 0,
            "empty": 0,
        },
    }
    assert payload["next"] == _NEXT
    assert after == before
