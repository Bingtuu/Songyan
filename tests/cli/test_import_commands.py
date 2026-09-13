"""Task 235/237: songyan import CLI 测试."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.db.migrations import init_schema
from songyan.utils.hashing import sha256_file

SAMPLE = (
    "第一章 风起\n\n松烟初入城。\n\n"
    "第二章\n\n雨下了一夜。\n"
)


def _make_source(tmp_path: Path) -> Path:
    src = tmp_path / "book.txt"
    src.write_text(SAMPLE, encoding="utf-8")
    return src


def test_segment_confirm_status_flow(tmp_path: Path) -> None:
    runner = CliRunner()
    src = _make_source(tmp_path)
    out = tmp_path / "import-out"

    result = runner.invoke(cli, ["import", "segment", "--source", str(src), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert "章节数" in result.output and ": 2" in result.output

    manifest = out / "manifest.json"
    result = runner.invoke(cli, ["import", "status", "--manifest", str(manifest)])
    assert result.exit_code == 1  # 未确认

    result = runner.invoke(cli, ["import", "confirm", "--manifest", str(manifest)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["import", "status", "--manifest", str(manifest)])
    assert result.exit_code == 0


def test_segment_missing_source_fails(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "import", "segment",
            "--source", str(tmp_path / "none.txt"),
            "--output", str(tmp_path / "o"),
        ],
    )
    assert result.exit_code != 0


def test_segment_no_chapter_header_fails(tmp_path: Path) -> None:
    runner = CliRunner()
    src = tmp_path / "plain.txt"
    src.write_text("没有任何章节标题。" * 50, encoding="utf-8")
    result = runner.invoke(
        cli,
        ["import", "segment", "--source", str(src), "--output", str(tmp_path / "o")],
    )
    assert result.exit_code != 0
    assert "章节标题" in result.output


def test_segment_over_confirmed_manifest_warns(tmp_path: Path) -> None:
    runner = CliRunner()
    src = _make_source(tmp_path)
    out = tmp_path / "import-out"
    manifest = out / "manifest.json"

    result = runner.invoke(cli, ["import", "segment", "--source", str(src), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert "已覆盖" not in result.output
    result = runner.invoke(cli, ["import", "confirm", "--manifest", str(manifest)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["import", "segment", "--source", str(src), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert "已覆盖先前已确认的清单" in result.output
    result = runner.invoke(cli, ["import", "status", "--manifest", str(manifest)])
    assert result.exit_code == 1  # 覆盖后回到未确认状态


# ---------------------------------------------------------------------------
# Task 237-2: import ingest
# ---------------------------------------------------------------------------


@pytest.fixture
async def import_cli_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """将连接层指向临时数据库并初始化 schema（惯例同 test_mark_commands）."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "cli_import.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


def _query(db_path: Path, sql: str, params: tuple = ()) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _ingest_args(src: Path, **overrides: str) -> list[str]:
    args = [
        "import", "ingest",
        "--source", str(src),
        "--genre", "scifi",
        "--protagonist-name", "林渊",
    ]
    for key, value in overrides.items():
        args += [f"--{key.replace('_', '-')}", value]
    return args


def test_ingest_happy_path(tmp_path: Path, import_cli_db: Path) -> None:
    runner = CliRunner()
    src = _make_source(tmp_path)

    result = runner.invoke(cli, _ingest_args(src))
    assert result.exit_code == 0, result.output

    projects = _query(
        import_cli_db,
        "SELECT project_id, genre_id, lifecycle_status, title FROM projects",
    )
    assert len(projects) == 1
    project_id, genre_id, lifecycle_status, title = projects[0]
    assert genre_id == "scifi"
    assert lifecycle_status == "importing"
    assert title == "book"  # 缺省取源文件名 stem

    chars = _query(
        import_cli_db,
        "SELECT role_type, name FROM characters WHERE project_id = ?",
        (project_id,),
    )
    assert chars == [("protagonist", "林渊")]

    assert project_id in result.output
    assert "importing" in result.output
    assert sha256_file(src) in result.output


def test_ingest_explicit_title(tmp_path: Path, import_cli_db: Path) -> None:
    runner = CliRunner()
    src = _make_source(tmp_path)

    result = runner.invoke(cli, _ingest_args(src, title="星港遗民"))
    assert result.exit_code == 0, result.output
    rows = _query(import_cli_db, "SELECT title FROM projects")
    assert rows == [("星港遗民",)]


def test_ingest_undecodable_source_fails(tmp_path: Path, import_cli_db: Path) -> None:
    runner = CliRunner()
    src = tmp_path / "bad.txt"
    src.write_bytes(b"\xff\xfe\x00\x01\x8f\x8e")

    result = runner.invoke(cli, _ingest_args(src))
    assert result.exit_code != 0
    assert "UTF-8" in result.output  # 恢复建议：另存为 UTF-8
    assert _query(import_cli_db, "SELECT COUNT(*) FROM projects") == [(0,)]


def test_ingest_unknown_genre_lists_available(tmp_path: Path, import_cli_db: Path) -> None:
    runner = CliRunner()
    src = _make_source(tmp_path)

    result = runner.invoke(cli, _ingest_args(src, genre="not-a-genre"))
    assert result.exit_code != 0
    assert "可用体裁" in result.output
    assert "scifi" in result.output
    assert _query(import_cli_db, "SELECT COUNT(*) FROM projects") == [(0,)]


def test_ingest_missing_required_option(tmp_path: Path, import_cli_db: Path) -> None:
    runner = CliRunner()
    src = _make_source(tmp_path)

    result = runner.invoke(
        cli,
        ["import", "ingest", "--source", str(src), "--genre", "scifi"],
    )
    assert result.exit_code != 0  # 缺 --protagonist-name，click 自带报错


def test_ingest_twice_creates_separate_projects(tmp_path: Path, import_cli_db: Path) -> None:
    runner = CliRunner()
    src = _make_source(tmp_path)

    first = runner.invoke(cli, _ingest_args(src, protagonist_name="林渊"))
    second = runner.invoke(cli, _ingest_args(src, protagonist_name="苏黎"))
    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output

    projects = _query(import_cli_db, "SELECT project_id FROM projects ORDER BY rowid")
    assert len(projects) == 2
    assert projects[0][0] != projects[1][0]

    chars = _query(
        import_cli_db,
        "SELECT project_id, role_type, name FROM characters ORDER BY rowid",
    )
    assert chars == [
        (projects[0][0], "protagonist", "林渊"),
        (projects[1][0], "protagonist", "苏黎"),
    ]
