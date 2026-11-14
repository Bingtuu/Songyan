"""task 261：``create-project --title``——书名作者可定（dogfood 洞察 ③）。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _title_of(db_path: Path, pid: str) -> str | None:
    con = sqlite3.connect(db_path)
    row = con.execute(
        "SELECT title FROM projects WHERE project_id=?", (pid,)
    ).fetchone()
    con.close()
    return None if row is None else row[0]


def test_create_with_title(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "t.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    import asyncio

    asyncio.run(init_schema(db_path))

    result = runner.invoke(
        cli, ["create-project", "--template", "urban", "--title", "夜班回声"]
    )
    assert result.exit_code == 0, result.output
    import re

    pid = re.search(r"[0-9a-f]{32}", result.output).group(0)
    assert _title_of(db_path, pid) == "夜班回声"


def test_create_without_title_keeps_template_default(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "t2.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    import asyncio
    import re

    asyncio.run(init_schema(db_path))
    result = runner.invoke(cli, ["create-project", "--template", "urban"])
    assert result.exit_code == 0, result.output
    pid = re.search(r"[0-9a-f]{32}", result.output).group(0)
    title = _title_of(db_path, pid)
    assert title is not None and title != "夜班回声"  # 模板默认名
