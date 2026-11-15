"""task 266 验收：urban 模板新项目清场——模板角色/设定逐个软删后，
list、上下文组装（character_roster）与设定加载出口都不再出现这些名字。
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.models.chapter import ChapterGoal
from songyan.workflows._helpers import (
    assemble_context_package,
    load_characters,
    load_setting_snapshots,
)

_REMOVED_CHARS = ("周牧野", "林知遥", "老张")
_REMOVED_SETTINGS = ("Echo原型", "陈屿的债务", "老张网吧")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def urban_project(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> str:
    db_path = tmp_path / "urban-cleanup.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    asyncio.run(init_schema(db_path))
    result = runner.invoke(
        cli, ["create-project", "--template", "urban", "--title", "雨幕钟表店"]
    )
    assert result.exit_code == 0, result.output
    return re.search(r"[0-9a-f]{32}", result.output).group(0)


def _ids(runner: CliRunner, pid: str, kind: str) -> dict[str, str]:
    result = runner.invoke(cli, [kind, "list", "--project-id", pid, "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout)["characters" if kind == "character" else "settings"]
    name_key = "name" if kind == "character" else "setting_name"
    id_key = f"{kind}_id"
    return {row[name_key]: row[id_key] for row in rows}


def test_template_cast_listed_then_cleanup_hides_everywhere(
    runner: CliRunner, urban_project: str
) -> None:
    pid = urban_project

    char_ids = _ids(runner, pid, "character")
    assert "陈屿" in char_ids
    for name in _REMOVED_CHARS:
        assert name in char_ids
    set_ids = _ids(runner, pid, "setting")
    for name in _REMOVED_SETTINGS:
        assert name in set_ids

    # 主角拒绝 remove
    result = runner.invoke(
        cli, ["character", "remove", "--project-id", pid, "--character-id", char_ids["陈屿"]]
    )
    assert result.exit_code == 2

    # 逐个软删模板班子与设定
    for name in _REMOVED_CHARS:
        result = runner.invoke(
            cli,
            ["character", "remove", "--project-id", pid, "--character-id", char_ids[name]],
        )
        assert result.exit_code == 0, result.output
    for name in _REMOVED_SETTINGS:
        result = runner.invoke(
            cli,
            ["setting", "remove", "--project-id", pid, "--setting-id", set_ids[name]],
        )
        assert result.exit_code == 0, result.output

    # list 出口
    char_ids = _ids(runner, pid, "character")
    assert list(char_ids) == ["陈屿"]
    assert _ids(runner, pid, "setting") == {}

    # 组装出口：角色名册 + 设定加载
    loaded = asyncio.run(load_characters(pid))
    assert {c.name for c in loaded} == {"陈屿"}
    assert asyncio.run(load_setting_snapshots(pid)) == []

    package = asyncio.run(
        assemble_context_package(pid, 1, ChapterGoal(chapter_number=1), None)
    )
    assert "陈屿" in package.character_roster
    for name in _REMOVED_CHARS:
        assert name not in package.character_roster
