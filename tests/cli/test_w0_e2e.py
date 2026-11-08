"""M1 step 5: W0 CLI loop show → edit → confirm/dismiss → show again."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_loader import (
    DUSHI_LINGYI_PROJECT_ID,
    bundled_dushi_lingyi_fixture,
    load_plan_fact_fixture,
)

_E2E_ENTITY_ID = "m1-w0-entity-loop"
_E2E_ATTR_ID = "m1-w0-attr-loop"
_NEXT = (
    "可用 canon confirm 入典或销账承诺；硬确认可用 --hard/--mark-stale；"
    "续写下一章走 chapter continue，"
    "章内草稿可 variant generate 抽卡（默认 N=2，不 auto-pick）。"
)
_CANON_HEAD = "# Canon（approved）"
_PENDING_HEAD = "# Pending（不是 Canon）"
_STORYLINE_HEAD = "# Storyline（规划骨架，不是已确认事实）"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def dushi_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "w0-e2e.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await load_plan_fact_fixture(bundled_dushi_lingyi_fixture())
    return db_path


def _between(text: str, start: str, end: str | None) -> str:
    begin = text.index(start) + len(start)
    if end is None:
        return text[begin:]
    return text[begin : text.index(end, begin)]


def _show(runner: CliRunner) -> str:
    result = runner.invoke(
        cli, ["canon", "show", "--project-id", DUSHI_LINGYI_PROJECT_ID]
    )
    assert result.exit_code == 0, result.output
    return result.output


def _canon_pending(output: str) -> tuple[str, str]:
    canon = _between(output, _CANON_HEAD, _PENDING_HEAD)
    pending = _between(output, _PENDING_HEAD, _STORYLINE_HEAD)
    return canon, pending


def test_w0_show_edit_confirm_dismiss_show_entity_and_attribute(
    runner: CliRunner, dushi_db: Path
) -> None:
    """W0: see → edit → confirm entity / dismiss attribute → see again."""
    before = _show(runner)
    canon0, pending0 = _canon_pending(before)
    assert _E2E_ENTITY_ID not in canon0
    assert _E2E_ENTITY_ID not in pending0
    assert _E2E_ATTR_ID not in canon0
    assert _E2E_ATTR_ID not in pending0

    edit_entity = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            _E2E_ENTITY_ID,
            "--type",
            "prop",
            "--alias",
            "闭环刀",
        ],
    )
    assert edit_entity.exit_code == 0, edit_entity.output

    edit_attr = runner.invoke(
        cli,
        [
            "canon",
            "edit",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _E2E_ATTR_ID,
            "--entity-id",
            _E2E_ENTITY_ID,
            "--key",
            "edge",
            "--value",
            "单面开刃",
            "--valid-from-ch",
            "1",
        ],
    )
    assert edit_attr.exit_code == 0, edit_attr.output

    after_edit = _show(runner)
    canon1, pending1 = _canon_pending(after_edit)
    assert _E2E_ENTITY_ID not in canon1
    assert _E2E_ENTITY_ID in pending1
    assert _E2E_ATTR_ID not in canon1
    assert _E2E_ATTR_ID in pending1

    confirm = runner.invoke(
        cli,
        [
            "canon",
            "confirm",
            "entity",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--entity-id",
            _E2E_ENTITY_ID,
        ],
    )
    assert confirm.exit_code == 0, confirm.output
    assert "已入典" in confirm.output

    dismiss = runner.invoke(
        cli,
        [
            "canon",
            "dismiss",
            "attribute",
            "--project-id",
            DUSHI_LINGYI_PROJECT_ID,
            "--attribute-id",
            _E2E_ATTR_ID,
        ],
    )
    assert dismiss.exit_code == 0, dismiss.output

    after = _show(runner)
    canon2, pending2 = _canon_pending(after)
    assert _E2E_ENTITY_ID in canon2
    assert _E2E_ENTITY_ID not in pending2
    assert _E2E_ATTR_ID not in canon2
    assert _E2E_ATTR_ID not in pending2

    today = runner.invoke(
        cli, ["today", "--project-id", DUSHI_LINGYI_PROJECT_ID, "--json"]
    )
    assert today.exit_code == 0, today.output
    assert _NEXT in today.output
    assert "确认入典和生成都不在本命令" not in today.output
