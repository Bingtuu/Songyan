"""M3 step 3: ``variant list`` fields + ``variant diff`` (unified), JSON surface."""

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
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ProjectRepository
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClaim,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)
from songyan.models.project import ProjectSetting
from songyan.services.variant_generate import SlotDraft

_PROJECT = "p-list-diff"
_CHAPTER = 1
_CONTENT_A = "第一行甲\n第二行甲\n共用行\n"
_CONTENT_B = "第一行乙\n第二行乙\n共用行\n"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def list_diff_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "variant-list-diff.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="variant list diff",
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


def _install_draft_mock(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    texts = [_CONTENT_A, _CONTENT_B]
    calls = {"i": 0}

    async def _draft(**_kwargs: Any) -> SlotDraft:
        idx = calls["i"]
        calls["i"] += 1
        text = texts[idx] if idx < len(texts) else f"草稿{idx + 1}"
        return SlotDraft(content=text, cost_cny_estimate=0.02)

    mock = AsyncMock(side_effect=_draft)
    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft",
        mock,
    )
    return mock


def _generate_two(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_list_after_generate_exposes_slot_fields(
    runner: CliRunner, list_diff_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generate_two(runner, monkeypatch)
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
    payload = json.loads(result.stdout)
    assert "variants" in payload
    assert len(payload["variants"]) == 2
    slots = {row["slot_index"] for row in payload["variants"]}
    assert slots == {1, 2}
    for row in payload["variants"]:
        assert row["status"] == "generated"
        assert row["stale_vs_canon"] == 0
        assert isinstance(row["fingerprint"], str) and len(row["fingerprint"]) >= 8
        assert isinstance(row["cost_cny_estimate"], (int, float))
        assert isinstance(row["content_ref"], str) and row["content_ref"]
        assert "score" in row  # optional; null ok


def test_list_text_shows_fingerprint_short(
    runner: CliRunner, list_diff_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generate_two(runner, monkeypatch)
    result = runner.invoke(
        cli,
        ["variant", "list", "--project-id", _PROJECT, "--chapter", str(_CHAPTER)],
    )
    assert result.exit_code == 0, result.output
    assert "slot=1" in result.output
    assert "slot=2" in result.output
    assert "fp=" in result.output
    assert "未实现" not in result.output


def test_diff_two_slots_unified_json(
    runner: CliRunner, list_diff_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generate_two(runner, monkeypatch)
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
    payload = json.loads(result.stdout)
    assert payload["chapter"] == _CHAPTER
    assert payload["a"] == 1
    assert payload["b"] == 2
    diff_text = payload["diff"]
    assert isinstance(diff_text, str)
    # unified_diff markers locked
    assert "---" in diff_text
    assert "+++" in diff_text
    assert "第一行甲" in diff_text or "-第一行甲" in diff_text
    assert "第一行乙" in diff_text or "+第一行乙" in diff_text


def test_diff_two_slots_text(
    runner: CliRunner, list_diff_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generate_two(runner, monkeypatch)
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
        ],
    )
    assert result.exit_code == 0, result.output
    assert "---" in result.output
    assert "+++" in result.output
    assert "未实现" not in result.output


def test_diff_missing_slot_exits_2(
    runner: CliRunner, list_diff_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generate_two(runner, monkeypatch)
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
            "99",
            "--json",
        ],
    )
    assert result.exit_code == 2, result.output
    assert "99" in result.output or "槽" in result.output


def test_diff_illegal_args_exit_1(runner: CliRunner, list_diff_db: Path) -> None:
    result = runner.invoke(
        cli,
        [
            "variant",
            "diff",
            "--project-id",
            _PROJECT,
            "--chapter",
            "0",
            "--a",
            "1",
            "--b",
            "2",
        ],
    )
    assert result.exit_code == 1, result.output


def test_list_diff_are_readonly_no_plan_write(
    runner: CliRunner, list_diff_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """list/diff must not mutate plan_* (read-only knife)."""
    from songyan.db.connection import get_db

    _generate_two(runner, monkeypatch)

    async def _approved_count() -> int:
        async with get_db() as conn:
            cur = await conn.execute(
                "SELECT COUNT(*) FROM plan_attributes WHERE project_id = ?",
                (_PROJECT,),
            )
            row = await cur.fetchone()
            return int(row[0])

    before = asyncio.run(_approved_count())
    list_r = runner.invoke(
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
    diff_r = runner.invoke(
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
    assert list_r.exit_code == 0, list_r.output
    assert diff_r.exit_code == 0, diff_r.output
    after = asyncio.run(_approved_count())
    assert after == before
