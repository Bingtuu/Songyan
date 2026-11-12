"""M3 step 5: lazy stale_vs_canon + cost visibility (tech-m3 §5 步5 / B3 / B6)."""

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
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ChapterHeadRepository, ProjectRepository
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClaim,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)
from songyan.models.project import ProjectSetting
from songyan.services.variant_generate import SlotDraft

_PROJECT = "p-stale-cost-m3"
_CHAPTER = 1
_CONTENT_1 = "槽一：南站夜色。" * 15
_CONTENT_2 = "槽二：南站雨幕。" * 15


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def stale_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "variant-stale-cost.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="variant stale cost",
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


def _install_draft_mock(
    monkeypatch: pytest.MonkeyPatch,
    *,
    costs: list[float] | None = None,
) -> AsyncMock:
    texts = [_CONTENT_1, _CONTENT_2]
    cost_vals = costs if costs is not None else [0.01, 0.02]
    calls = {"i": 0}

    async def _draft(**_kwargs: Any) -> SlotDraft:
        idx = calls["i"]
        calls["i"] += 1
        text = texts[idx] if idx < len(texts) else f"草稿{idx + 1}"
        cost = cost_vals[idx] if idx < len(cost_vals) else 0.0
        return SlotDraft(content=text, cost_cny_estimate=cost)

    mock = AsyncMock(side_effect=_draft)
    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft",
        mock,
    )
    return mock


def _generate_two(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    *,
    costs: list[float] | None = None,
) -> dict[str, Any]:
    _install_draft_mock(monkeypatch, costs=costs)
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


async def _change_approved_location(new_value: str = "北站") -> None:
    """Mutate approved Canon so parent_canon_fingerprint drifts (B3)."""
    await PlanFactRepository().write_attribute(
        PlanAttribute(
            attribute_id="attr-loc",
            project_id=_PROJECT,
            entity_id="ent-chen",
            key="location",
            value=new_value,
            source="plan",
            approval_status="approved",
            valid_from_ch=1,
            valid_to_ch=5,
        )
    )


def test_list_marks_stale_after_approved_canon_change(
    runner: CliRunner, stale_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lazy mark (B3): list after Canon change → stale_vs_canon=1; content_stale untouched."""
    _generate_two(runner, monkeypatch)
    before = runner.invoke(
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
    assert before.exit_code == 0, before.output
    assert all(r["stale_vs_canon"] == 0 for r in json.loads(before.stdout)["variants"])

    asyncio.run(_change_approved_location())

    # DB may still show 0 until lazy refresh on list/diff/pick/generate.
    rows_raw = asyncio.run(
        ChapterVariantRepository().list_for_chapter(_PROJECT, _CHAPTER)
    )
    assert all(int(r.stale_vs_canon) == 0 for r in rows_raw)

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
    for row in payload["variants"]:
        assert row["stale_vs_canon"] == 1
        assert "cost_cny_estimate" in row
        assert isinstance(row["cost_cny_estimate"], (int, float))

    persisted = asyncio.run(
        ChapterVariantRepository().list_for_chapter(_PROJECT, _CHAPTER)
    )
    assert all(int(r.stale_vs_canon) == 1 for r in persisted)

    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, _CHAPTER))
    if head is not None:
        assert int(head.content_stale or 0) == 0


def test_pick_rejects_stale_after_canon_change_allow_stale_slot2(
    runner: CliRunner, stale_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After Canon drift: pick exit 2; --allow-stale + slot 2 (S4) ok; no content_stale."""
    payload = _generate_two(runner, monkeypatch)
    ref2 = next(v["content_ref"] for v in payload["variants"] if v["slot_index"] == 2)
    asyncio.run(_change_approved_location())

    rejected = runner.invoke(
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
    assert rejected.exit_code == 2, rejected.output
    assert (
        asyncio.run(ChapterVariantRepository().get_picked(_PROJECT, _CHAPTER)) is None
    )

    allowed = runner.invoke(
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
            "--allow-stale",
            "--json",
        ],
    )
    assert allowed.exit_code == 0, allowed.output
    out = json.loads(allowed.stdout)
    assert out["slot_index"] == 2
    assert out["status"] == "picked"
    assert out["current_version_id"] == ref2
    assert out["stale_vs_canon"] == 1

    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, _CHAPTER))
    assert head is not None
    assert head.current_version_id == ref2
    assert int(head.content_stale or 0) == 0


def test_list_exposes_cost_field_even_when_zero(
    runner: CliRunner, stale_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per-slot cost_cny_estimate must exist on list (fixture may be 0)."""
    _generate_two(runner, monkeypatch, costs=[0.0, 0.0])
    result = runner.invoke(
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
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout)["variants"]
    assert len(rows) == 2
    for row in rows:
        assert "cost_cny_estimate" in row
        assert row["cost_cny_estimate"] == 0.0

    text = runner.invoke(
        cli,
        ["variant", "list", "--project-id", _PROJECT, "--chapter", str(_CHAPTER)],
    )
    assert text.exit_code == 0, text.output
    assert "cost=" in text.output
    assert "cost=0" in text.output or "cost=0.0" in text.output


def test_diff_also_lazy_marks_stale(
    runner: CliRunner, stale_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lazy mark choice locked: diff path also refreshes stale_vs_canon."""
    _generate_two(runner, monkeypatch)
    asyncio.run(_change_approved_location())
    result = runner.invoke(
        cli,
        [
            "variant",
            "diff",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--a",
            "1",
            "--b",
            "2",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    persisted = asyncio.run(
        ChapterVariantRepository().list_for_chapter(_PROJECT, _CHAPTER)
    )
    assert all(int(r.stale_vs_canon) == 1 for r in persisted)
