"""task 268：create-project --no-seed + urban_horror 薄模板。

验收：
- --template urban --no-seed：只有主角档案（模板 protagonist_name），无配角、无设定。
- --template urban_horror：薄模板可加载；只有主角档案；无职场种子。
- 不加 --no-seed 的既有模板行为不变（由 test_profile_urban_cleanup 回归覆盖）。
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.project_templates.loader import ProjectTemplateLoader
from songyan.services.profile_edit import list_characters, list_settings

_FORBIDDEN_CHARS = {"周牧野", "林知遥", "老张"}
_FORBIDDEN_SETTINGS = {"Echo原型", "陈屿的债务", "老张网吧"}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _mk_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> Path:
    db_path = tmp_path / name
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    asyncio.run(init_schema(db_path))
    return db_path


def _create(runner: CliRunner, *args: str) -> str:
    result = runner.invoke(cli, ["create-project", *args])
    assert result.exit_code == 0, result.output
    return re.search(r"[0-9a-f]{32}", result.output).group(0)


def test_urban_no_seed_keeps_only_protagonist(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mk_db(tmp_path, monkeypatch, "noseed.db")
    pid = _create(runner, "--template", "urban", "--no-seed", "--title", "雨幕钟表店")

    chars = asyncio.run(list_characters(pid))
    names = {c.name for c in chars}
    assert names == {"陈屿"}, f"模板配角不得入库: {names - {'陈屿'}}"
    assert _FORBIDDEN_CHARS.isdisjoint(names)

    settings_rows = asyncio.run(list_settings(pid, include_archived=True))
    assert settings_rows == []
    assert _FORBIDDEN_SETTINGS.isdisjoint(
        {r["setting_name"] for r in settings_rows}
    )


def test_urban_horror_template_thin_seed(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mk_db(tmp_path, monkeypatch, "horror.db")
    assert "urban_horror" in ProjectTemplateLoader().list_templates()

    pid = _create(runner, "--template", "urban_horror", "--title", "末班电梯")
    chars = asyncio.run(list_characters(pid))
    assert len(chars) == 1
    protagonist = chars[0]
    assert protagonist.role_type == "protagonist"
    assert protagonist.name  # 主角档案以模板为准
    # 薄模板不得种子化职场班子
    assert _FORBIDDEN_CHARS.isdisjoint({c.name for c in chars})
    assert asyncio.run(list_settings(pid, include_archived=True)) == []


def test_urban_with_seed_unchanged(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """回归：不加 --no-seed 时 urban 仍种职场班子。"""
    _mk_db(tmp_path, monkeypatch, "withseed.db")
    pid = _create(runner, "--template", "urban", "--title", "带种子")
    names = {c.name for c in asyncio.run(list_characters(pid))}
    assert _FORBIDDEN_CHARS <= names
