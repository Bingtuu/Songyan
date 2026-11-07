"""M3 step 4: ``variant pick`` / ``variant abandon`` (tech-m3 §5 步4 / B4 / B5)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClaim,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)
from songyan.models.project import ProjectSetting
from songyan.services.variant_generate import SlotDraft

_PROJECT = "p-pick-m3"
_CHAPTER = 1
_CONTENT_1 = "草稿槽一：南站夜色。"
_CONTENT_2 = "草稿槽二：南站雨幕。"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def pick_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "variant-pick.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="variant pick abandon",
        ),
        _PROJECT,
    )
    repo = PlanFactRepository()
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-chen",
            project_id=_PROJECT,
            entity_type="person",
            aliases=["陈照"],
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-loc",
            project_id=_PROJECT,
            entity_id="ent-chen",
            key="location",
            value="南站",
            source="plan",
            approval_status="approved",
            valid_from_ch=1,
            valid_to_ch=5,
        )
    )
    await repo.write_time_anchor(
        PlanTimeAnchor(
            anchor_id="ta-1",
            project_id=_PROJECT,
            date="第一天黄昏",
            kind="story",
            approval_status="approved",
        )
    )
    await repo.write_event(
        PlanEvent(
            event_id="evt-1",
            project_id=_PROJECT,
            ch=_CHAPTER,
            time_anchor_id="ta-1",
            participants=["ent-chen"],
            causes=[],
            reveals_evidence=[],
            claims=[PlanClaim(claim_id="c1", text="陈照到南站")],
            approval_status="approved",
        )
    )
    return db_path


async def _plan_approved_snapshot(project_id: str) -> dict[str, list[tuple[Any, ...]]]:
    async with get_db() as conn:
        tables = (
            "plan_entities",
            "plan_attributes",
            "plan_events",
            "plan_clues",
            "plan_time_anchors",
        )
        out: dict[str, list[tuple[Any, ...]]] = {}
        for table in tables:
            cur = await conn.execute(
                f"SELECT * FROM {table} WHERE project_id = ? AND approval_status = 'approved' "
                f"ORDER BY 1",
                (project_id,),
            )
            out[table] = [tuple(row) for row in await cur.fetchall()]
        return out


def _install_draft_mock(
    monkeypatch: pytest.MonkeyPatch,
    *,
    contents: list[str] | None = None,
) -> AsyncMock:
    texts = contents or [_CONTENT_1, _CONTENT_2]
    calls = {"i": 0}

    async def _draft(**_kwargs: Any) -> SlotDraft:
        idx = calls["i"]
        calls["i"] += 1
        text = texts[idx] if idx < len(texts) else f"草稿{idx + 1}"
        return SlotDraft(content=text, cost_cny_estimate=0.01)

    mock = AsyncMock(side_effect=_draft)
    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft",
        mock,
    )
    return mock


def _generate_two(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    _install_draft_mock(monkeypatch)
    result = runner.invoke(
        cli,
        [
            "variant",
            "generate",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def test_pick_slot2_moves_head_archives_prior_plan_unchanged(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PRD M3: pick slot 2; one picked; head→content_ref; plan_* approved unchanged."""
    payload = _generate_two(runner, monkeypatch)
    by_slot = {v["slot_index"]: v for v in payload["variants"]}
    ref2 = by_slot[2]["content_ref"]

    # Pick slot 1 first so subsequent pick of slot 2 must archive it.
    first = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            "1",
            "--json",
        ],
    )
    assert first.exit_code == 0, first.output

    before = asyncio.run(_plan_approved_snapshot(_PROJECT))
    result = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            "2",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    out = json.loads(result.stdout)
    assert out["slot_index"] == 2
    assert out["status"] == "picked"
    assert out["content_ref"] == ref2
    assert out["current_version_id"] == ref2

    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, _CHAPTER))
    assert head is not None
    assert head.current_version_id == ref2

    rows = asyncio.run(ChapterVariantRepository().list_for_chapter(_PROJECT, _CHAPTER))
    picked = [r for r in rows if r.status == "picked"]
    assert len(picked) == 1
    assert picked[0].slot_index == 2
    archived = [r for r in rows if r.status == "archived"]
    assert any(r.slot_index == 1 for r in archived)

    after = asyncio.run(_plan_approved_snapshot(_PROJECT))
    assert after == before

    version = asyncio.run(ChapterVersionRepository().get(ref2))
    assert version is not None
    assert version.content == _CONTENT_2


def test_pick_stale_rejects_without_allow_stale(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _generate_two(runner, monkeypatch)
    slot = payload["variants"][0]["slot_index"]

    async def _mark_stale() -> None:
        async with get_db() as conn:
            await conn.execute(
                """
                UPDATE chapter_variants
                SET stale_vs_canon = 1
                WHERE project_id = ? AND chapter_number = ? AND slot_index = ?
                """,
                (_PROJECT, _CHAPTER, slot),
            )
            await conn.commit()

    asyncio.run(_mark_stale())
    before = asyncio.run(_plan_approved_snapshot(_PROJECT))
    result = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            str(slot),
            "--json",
        ],
    )
    assert result.exit_code == 2, result.output
    assert asyncio.run(ChapterVariantRepository().get_picked(_PROJECT, _CHAPTER)) is None
    after = asyncio.run(_plan_approved_snapshot(_PROJECT))
    assert after == before


def test_pick_stale_allow_stale_ok_no_canon_write(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _generate_two(runner, monkeypatch)
    slot = payload["variants"][1]["slot_index"]
    ref = payload["variants"][1]["content_ref"]

    async def _mark_stale() -> None:
        async with get_db() as conn:
            await conn.execute(
                """
                UPDATE chapter_variants
                SET stale_vs_canon = 1
                WHERE project_id = ? AND chapter_number = ? AND slot_index = ?
                """,
                (_PROJECT, _CHAPTER, slot),
            )
            await conn.commit()

    asyncio.run(_mark_stale())
    before = asyncio.run(_plan_approved_snapshot(_PROJECT))
    result = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            str(slot),
            "--allow-stale",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    out = json.loads(result.stdout)
    assert out["status"] == "picked"
    assert out["current_version_id"] == ref
    after = asyncio.run(_plan_approved_snapshot(_PROJECT))
    assert after == before
    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, _CHAPTER))
    assert head is not None
    assert int(head.content_stale or 0) == 0


def test_abandon_soft_keeps_content_readable(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _generate_two(runner, monkeypatch)
    slot = 1
    ref = next(v["content_ref"] for v in payload["variants"] if v["slot_index"] == slot)
    before_content = asyncio.run(ChapterVersionRepository().get(ref))
    assert before_content is not None
    locked = before_content.content

    result = runner.invoke(
        cli,
        [
            "variant",
            "abandon",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            str(slot),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    out = json.loads(result.stdout)
    assert out["status"] == "abandoned"
    assert out["slot_index"] == slot

    row = asyncio.run(ChapterVariantRepository().get_by_slot(_PROJECT, _CHAPTER, slot))
    assert row is not None
    assert row.status == "abandoned"
    assert row.content_ref == ref

    version = asyncio.run(ChapterVersionRepository().get(ref))
    assert version is not None
    assert version.content == locked
    # Soft abandon may mark is_abandoned; content must remain readable either way.
    listed = asyncio.run(
        ChapterVersionRepository().list_by_chapter(
            _PROJECT, _CHAPTER, include_abandoned=True
        )
    )
    assert any(v.version_id == ref and v.content == locked for v in listed)


def test_abandon_picked_rejects_exit_2(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generate_two(runner, monkeypatch)
    pick = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            "2",
            "--json",
        ],
    )
    assert pick.exit_code == 0, pick.output
    result = runner.invoke(
        cli,
        [
            "variant",
            "abandon",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            "2",
            "--json",
        ],
    )
    assert result.exit_code == 2, result.output
    picked = asyncio.run(ChapterVariantRepository().get_picked(_PROJECT, _CHAPTER))
    assert picked is not None
    assert picked.slot_index == 2


def test_after_pick_generate_does_not_update_picked_content(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _generate_two(runner, monkeypatch)
    ref2 = next(v["content_ref"] for v in payload["variants"] if v["slot_index"] == 2)
    pick = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            "2",
            "--json",
        ],
    )
    assert pick.exit_code == 0, pick.output
    locked = asyncio.run(ChapterVersionRepository().get(ref2))
    assert locked is not None
    locked_body = locked.content

    _install_draft_mock(monkeypatch, contents=["新槽三", "新槽四"])
    gen = runner.invoke(
        cli,
        [
            "variant",
            "generate",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--n",
            "2",
            "--json",
        ],
    )
    assert gen.exit_code == 0, gen.output
    still = asyncio.run(ChapterVersionRepository().get(ref2))
    assert still is not None
    assert still.content == locked_body
    rows = asyncio.run(ChapterVariantRepository().list_for_chapter(_PROJECT, _CHAPTER))
    assert any(r.status == "picked" and r.content_ref == ref2 for r in rows)
    new_gen = [r for r in rows if r.status == "generated"]
    assert len(new_gen) >= 2
    assert all(r.content_ref != ref2 for r in new_gen)


def test_pick_missing_slot_exit_2(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generate_two(runner, monkeypatch)
    result = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            "99",
            "--json",
        ],
    )
    assert result.exit_code == 2, result.output


def test_abandon_missing_slot_exit_2(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generate_two(runner, monkeypatch)
    result = runner.invoke(
        cli,
        [
            "variant",
            "abandon",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            "99",
            "--json",
        ],
    )
    assert result.exit_code == 2, result.output


def test_pick_illegal_args_exit_1(runner: CliRunner, pick_db: Path) -> None:
    result = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            "0",
            "--slot",
            "1",
        ],
    )
    assert result.exit_code == 1, result.output
    result2 = runner.invoke(
        cli,
        [
            "variant",
            "abandon",
            "--project-id",
            _PROJECT,
            "--chapter",
            "1",
            "--slot",
            "0",
        ],
    )
    assert result2.exit_code == 1, result2.output


def test_pick_missing_project_exit_1(runner: CliRunner, pick_db: Path) -> None:
    result = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            "no-such-project",
            "--chapter",
            "1",
            "--slot",
            "1",
        ],
    )
    assert result.exit_code == 1, result.output


def test_pick_preserves_existing_head_accepted_and_status(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pick only moves current_version_id; accepted_version_id stays."""
    payload = _generate_two(runner, monkeypatch)
    ref2 = next(v["content_ref"] for v in payload["variants"] if v["slot_index"] == 2)

    async def _seed_head() -> None:
        await ChapterVersionRepository().create(
            ChapterVersion(
                version_id="v-accepted-keep",
                project_id=_PROJECT,
                chapter_number=_CHAPTER,
                version_number=99,
                version_type="accepted",
                content="正式稿保留",
                word_count=4,
            )
        )
        await ChapterVersionRepository().create(
            ChapterVersion(
                version_id="v-old-work",
                project_id=_PROJECT,
                chapter_number=_CHAPTER,
                version_number=98,
                version_type="draft",
                content="旧工作稿",
                word_count=3,
            )
        )
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=_PROJECT,
                chapter_number=_CHAPTER,
                current_version_id="v-old-work",
                accepted_version_id="v-accepted-keep",
                status="under_review",
            )
        )

    asyncio.run(_seed_head())
    result = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            "2",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, _CHAPTER))
    assert head is not None
    assert head.current_version_id == ref2
    assert head.accepted_version_id == "v-accepted-keep"
    assert head.status == "under_review"


def test_pick_abandoned_slot_rejected_cleanly(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """task 226 切片 3：abandoned 槽不可被 pick 复活——干净拒绝 exit 2，头指针不动。"""
    _generate_two(runner, monkeypatch)
    abandon = runner.invoke(
        cli,
        [
            "variant", "abandon",
            "--project-id", _PROJECT,
            "--chapter", str(_CHAPTER),
            "--slot", "1",
            "--json",
        ],
    )
    assert abandon.exit_code == 0, abandon.output

    result = runner.invoke(
        cli,
        [
            "variant", "pick",
            "--project-id", _PROJECT,
            "--chapter", str(_CHAPTER),
            "--slot", "1",
            "--json",
        ],
    )
    assert result.exit_code == 2
    assert "abandon" in result.output.lower() or "已放弃" in result.output

    # 工作指针不得指向被 abandon 的正文；is_abandoned 残留不被复活
    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, _CHAPTER))
    assert head is None

    async def _slot_flag() -> tuple[str, int]:
        row = await ChapterVariantRepository().get_by_slot(_PROJECT, _CHAPTER, 1)
        assert row is not None
        version = await ChapterVersionRepository().get(row.content_ref)
        assert version is not None
        return row.status, int(version.is_abandoned)

    status, flag = asyncio.run(_slot_flag())
    assert status == "abandoned"
    assert flag == 1


def test_pick_archived_slot_revives_head(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """task 226 切片 3：archived（被顶替的 picked）槽允许重新 pick，正文标记不残留。"""
    payload = _generate_two(runner, monkeypatch)
    by_slot = {v["slot_index"]: v for v in payload["variants"]}
    ref1 = by_slot[1]["content_ref"]

    for slot in ("1", "2"):
        r = runner.invoke(
            cli,
            [
                "variant", "pick",
                "--project-id", _PROJECT,
                "--chapter", str(_CHAPTER),
                "--slot", slot,
                "--json",
            ],
        )
        assert r.exit_code == 0, r.output

    # 回头 pick 已被顶替为 archived 的 slot 1
    result = runner.invoke(
        cli,
        [
            "variant", "pick",
            "--project-id", _PROJECT,
            "--chapter", str(_CHAPTER),
            "--slot", "1",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, _CHAPTER))
    assert head is not None
    assert head.current_version_id == ref1

    async def _flag() -> int:
        version = await ChapterVersionRepository().get(ref1)
        assert version is not None
        return int(version.is_abandoned)

    assert asyncio.run(_flag()) == 0


def test_pick_duplicate_picked_race_reports_exit_2(
    runner: CliRunner, pick_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """task 226 切片 4：pick 撞单 picked 唯一守卫（并发种族）→ 干净业务拒绝 exit 2。"""
    from songyan.exceptions import DuplicatePickedVariantError

    _generate_two(runner, monkeypatch)

    async def _boom(self: Any, project_id: str, chapter: int, slot: int) -> Any:
        raise DuplicatePickedVariantError("race: chapter already has a picked variant")

    monkeypatch.setattr(ChapterVariantRepository, "pick_slot", _boom)
    result = runner.invoke(
        cli,
        [
            "variant", "pick",
            "--project-id", _PROJECT,
            "--chapter", str(_CHAPTER),
            "--slot", "1",
            "--json",
        ],
    )
    assert result.exit_code == 2
    assert "Traceback" not in result.output
