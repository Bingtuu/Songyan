"""M3 step 2: ``songyan variant generate`` (default N=2, mocked model)."""

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
from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClaim,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)
from songyan.models.project import ProjectSetting
from songyan.plan_checks.bible import load_chapter_plan_bible
from songyan.services.variant_fingerprint import fingerprint_chapter_parent_canon
from songyan.services.variant_generate import SlotDraft

_PROJECT = "p-gen-m3"
_CHAPTER = 1


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def gen_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "variant-generate.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="variant generate",
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
    # Pending must never leak into generate / bible / fingerprint (S8).
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-pending",
            project_id=_PROJECT,
            entity_type="prop",
            aliases=["不该进圣经"],
            approval_status="pending",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-pending",
            project_id=_PROJECT,
            entity_id="ent-chen",
            key="secret",
            value="pending-only-leak-probe",
            source="human",
            approval_status="pending",
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
    cost: float = 0.01,
    contents: list[str] | None = None,
) -> AsyncMock:
    texts = contents or ["草稿甲：南站夜色。" * 15, "草稿乙：南站雨幕。" * 15]
    calls = {"i": 0}

    async def _draft(**_kwargs: Any) -> SlotDraft:
        idx = calls["i"]
        calls["i"] += 1
        text = texts[idx] if idx < len(texts) else f"草稿{idx + 1}"
        return SlotDraft(content=text, cost_cny_estimate=cost)

    mock = AsyncMock(side_effect=_draft)
    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft",
        mock,
    )
    return mock


def test_generate_n2_writes_two_generated_no_pick(
    runner: CliRunner, gen_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock = _install_draft_mock(monkeypatch)
    before = asyncio.run(_plan_approved_snapshot(_PROJECT))
    fp_before = asyncio.run(fingerprint_chapter_parent_canon(_PROJECT, _CHAPTER))

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
    payload = json.loads(result.stdout)
    assert payload["n"] == 2
    assert len(payload["variants"]) == 2
    assert all(v["status"] == "generated" for v in payload["variants"])
    assert all(v["slot_index"] in (1, 2) for v in payload["variants"])
    assert {v["slot_index"] for v in payload["variants"]} == {1, 2}
    assert all(v["stale_vs_canon"] == 0 for v in payload["variants"])
    assert all(v["parent_canon_fingerprint"] == fp_before for v in payload["variants"])
    assert all(isinstance(v["cost_cny_estimate"], (int, float)) for v in payload["variants"])
    assert mock.await_count == 2

    rows = asyncio.run(
        ChapterVariantRepository().list_for_chapter(_PROJECT, _CHAPTER)
    )
    assert len(rows) == 2
    assert all(r.status == "generated" for r in rows)
    assert asyncio.run(ChapterVariantRepository().get_picked(_PROJECT, _CHAPTER)) is None

    versions = asyncio.run(
        ChapterVersionRepository().list_by_chapter(_PROJECT, _CHAPTER)
    )
    assert len(versions) == 2
    assert all(v.version_type == "draft" for v in versions)
    assert {r.content_ref for r in rows} == {v.version_id for v in versions}

    after = asyncio.run(_plan_approved_snapshot(_PROJECT))
    assert after == before
    assert asyncio.run(fingerprint_chapter_parent_canon(_PROJECT, _CHAPTER)) == fp_before


def test_generate_s8_pending_not_in_bible_or_draft_kwargs(
    runner: CliRunner, gen_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen_bibles: list[str] = []

    async def _draft(*, bible_text: str, **_kwargs: Any) -> SlotDraft:
        seen_bibles.append(bible_text)
        return SlotDraft(content="仅草稿。" * 30, cost_cny_estimate=0.0)

    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft",
        AsyncMock(side_effect=_draft),
    )

    bible = asyncio.run(load_chapter_plan_bible(_PROJECT, _CHAPTER))
    assert "pending-only-leak-probe" not in bible.text
    assert "不该进圣经" not in bible.text

    result = runner.invoke(
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
    assert result.exit_code == 0, result.output
    assert len(seen_bibles) == 2
    for text in seen_bibles:
        assert "pending-only-leak-probe" not in text
        assert "不该进圣经" not in text


def test_generate_budget_exhausted_keeps_written_exit_3(
    runner: CliRunner, gen_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_draft_mock(monkeypatch, cost=1.0)
    result = runner.invoke(
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
            "--budget-cny",
            "1.0",
            "--json",
        ],
    )
    assert result.exit_code == 3, result.output
    payload = json.loads(result.stdout)
    assert len(payload["variants"]) == 1
    assert payload["variants"][0]["status"] == "generated"
    assert payload["budget_exhausted"] is True

    rows = asyncio.run(
        ChapterVariantRepository().list_for_chapter(_PROJECT, _CHAPTER)
    )
    assert len(rows) == 1
    assert rows[0].status == "generated"


def test_generate_does_not_update_existing_picked_content(
    runner: CliRunner, gen_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-generate must INSERT new version rows; never UPDATE picked content."""
    from songyan.models.chapter import ChapterVersion
    from songyan.models.variant import ChapterVariant

    async def _seed_picked() -> str:
        await ChapterVersionRepository().create(
            ChapterVersion(
                version_id="v-picked-lock",
                project_id=_PROJECT,
                chapter_number=_CHAPTER,
                version_number=1,
                version_type="draft",
                content="LOCKED_PICKED_BODY",
                word_count=3,
            )
        )
        now = "2026-11-06T00:00:00Z"
        await ChapterVariantRepository().insert(
            ChapterVariant(
                variant_id="var-picked",
                project_id=_PROJECT,
                chapter_number=_CHAPTER,
                slot_index=1,
                status="picked",
                parent_canon_fingerprint="fp-old",
                content_ref="v-picked-lock",
                stale_vs_canon=0,
                cost_cny_estimate=0.0,
                created_at=now,
                updated_at=now,
            )
        )
        return "v-picked-lock"

    asyncio.run(_seed_picked())
    _install_draft_mock(
        monkeypatch,
        contents=["新槽草稿一：南城夜雨。" * 15, "新槽草稿二：北站晨雾。" * 15],
    )
    result = runner.invoke(
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
    assert result.exit_code == 0, result.output
    locked = asyncio.run(ChapterVersionRepository().get("v-picked-lock"))
    assert locked is not None
    assert locked.content == "LOCKED_PICKED_BODY"

    rows = asyncio.run(
        ChapterVariantRepository().list_for_chapter(_PROJECT, _CHAPTER)
    )
    assert len(rows) == 3  # 1 picked + 2 new generated
    generated = [r for r in rows if r.status == "generated"]
    assert len(generated) == 2
    assert all(r.content_ref != "v-picked-lock" for r in generated)
    assert asyncio.run(ChapterVariantRepository().get_picked(_PROJECT, _CHAPTER)) is not None


def test_variant_list_still_works_after_generate(
    runner: CliRunner, gen_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_draft_mock(monkeypatch)
    gen = runner.invoke(
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
    assert gen.exit_code == 0, gen.output
    listed = runner.invoke(
        cli,
        [
            "variant",
            "list",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--json",
        ],
    )
    assert listed.exit_code == 0, listed.output
    payload = json.loads(listed.stdout)
    assert len(payload["variants"]) == 2
    assert "未实现" not in listed.output


def test_generate_llm_failure_keeps_written_slots_and_reports(
    runner: CliRunner, gen_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tech-m3 §4.2 #4：模型失败——已写 slot 保留；失败信息进 stderr/退出码，无 traceback。"""
    from songyan.exceptions import LLMError

    calls = {"i": 0}

    async def _flaky(**_kwargs: Any) -> SlotDraft:
        calls["i"] += 1
        if calls["i"] >= 2:
            raise LLMError("model exploded")
        return SlotDraft(content="草稿一。" * 30, cost_cny_estimate=0.01)

    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft", _flaky
    )
    result = runner.invoke(
        cli,
        [
            "variant", "generate",
            "--project-id", _PROJECT,
            "--chapter", str(_CHAPTER),
        ],
    )
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "已保留 1" in result.output

    rows = asyncio.run(ChapterVariantRepository().list_for_chapter(_PROJECT, _CHAPTER))
    assert [r.slot_index for r in rows] == [1]
