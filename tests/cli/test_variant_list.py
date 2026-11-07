"""M3 step 1: ``songyan variant list`` returns empty list when no variants."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.models.project import ProjectSetting

_PROJECT = "p-list"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def project_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "variant-list.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
        ),
        _PROJECT,
    )
    return db_path


def test_variant_list_empty_json(runner: CliRunner, project_db: Path) -> None:
    result = runner.invoke(
        cli,
        ["variant", "list", "--project-id", _PROJECT, "--chapter", "1", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {"variants": []}


def test_variant_list_empty_text(runner: CliRunner, project_db: Path) -> None:
    result = runner.invoke(
        cli,
        ["variant", "list", "--project-id", _PROJECT, "--chapter", "1"],
    )
    assert result.exit_code == 0, result.output
    assert "（空）" in result.output
    assert "未实现" not in result.output


def test_variant_list_text_uses_stale_vs_canon_column_name(
    runner: CliRunner, project_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """task 231：文本输出列名 stale_vs_canon，与 content_stale 防混（STATUS 文案纪律）。"""
    from songyan.services.variant_generate import SlotDraft

    async def _draft(**_kwargs: object) -> SlotDraft:
        return SlotDraft(content="草稿一", cost_cny_estimate=0.01)

    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft", _draft
    )
    gen = runner.invoke(
        cli,
        ["variant", "generate", "--project-id", _PROJECT, "--chapter", "1", "--json"],
    )
    assert gen.exit_code == 0, gen.output

    result = runner.invoke(
        cli, ["variant", "list", "--project-id", _PROJECT, "--chapter", "1"]
    )
    assert result.exit_code == 0, result.output
    assert "stale_vs_canon=" in result.output
