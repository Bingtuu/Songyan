"""Task 235/237: songyan import CLI 测试."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.db.migrations import init_schema
from songyan.exceptions import ImportReplayError
from songyan.models.import_replay import ChapterReplayOutcome, ReplayReport
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


# ---------------------------------------------------------------------------
# Task 237-3: import replay
# ---------------------------------------------------------------------------


def _make_manifest(tmp_path: Path) -> Path:
    """replay_import 已被 mock，仅需满足 click.Path(exists=True) 的占位清单."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    return manifest


def _patch_replay_import(
    monkeypatch: pytest.MonkeyPatch,
    fake: Any,
) -> None:
    # 命令内 lazy import replay_import，patch 服务层引用源即可生效
    monkeypatch.setattr(
        "songyan.services.import_replay_service.replay_import", fake
    )


def _applied_outcome(chapter_number: int, title: str) -> ChapterReplayOutcome:
    return ChapterReplayOutcome(
        chapter_number=chapter_number, title=title, status="applied"
    )


def test_replay_passes_args_and_echoes_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _make_manifest(tmp_path)
    captured: dict[str, Any] = {}

    async def fake_replay_import(
        project_id: str,
        manifest_path: Path,
        *,
        chapters: set[int] | None = None,
        run_id: str | None = None,
    ) -> ReplayReport:
        captured.update(
            project_id=project_id,
            manifest_path=manifest_path,
            chapters=chapters,
            run_id=run_id,
        )
        return ReplayReport(
            run_id="run-test123",
            project_id=project_id,
            outcomes=[
                _applied_outcome(1, "风起"),
                _applied_outcome(2, "雨夜"),
            ],
        )

    _patch_replay_import(monkeypatch, fake_replay_import)

    result = CliRunner().invoke(
        cli,
        ["import", "replay", "--project", "proj-1", "--manifest", str(manifest)],
    )
    assert result.exit_code == 0, result.output
    assert captured == {
        "project_id": "proj-1",
        "manifest_path": manifest,
        "chapters": None,
        "run_id": None,
    }
    assert "导入回放报告" in result.output
    assert "run-test123" in result.output
    assert "applied=2" in result.output


def test_replay_chapters_and_run_id_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _make_manifest(tmp_path)
    captured: dict[str, Any] = {}

    async def fake_replay_import(
        project_id: str,
        manifest_path: Path,
        *,
        chapters: set[int] | None = None,
        run_id: str | None = None,
    ) -> ReplayReport:
        captured.update(chapters=chapters, run_id=run_id)
        return ReplayReport(run_id=run_id or "generated", project_id=project_id)

    _patch_replay_import(monkeypatch, fake_replay_import)

    result = CliRunner().invoke(
        cli,
        [
            "import", "replay",
            "--project", "proj-1",
            "--manifest", str(manifest),
            "--chapters", "1,3,5",
            "--run-id", "run-resume",
        ],
    )
    assert result.exit_code == 0, result.output
    assert captured == {"chapters": {1, 3, 5}, "run_id": "run-resume"}


def test_replay_chapters_invalid_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _make_manifest(tmp_path)

    async def fake_replay_import(*args: Any, **kwargs: Any) -> ReplayReport:
        raise AssertionError("非法 --chapters 不应到达服务层")

    _patch_replay_import(monkeypatch, fake_replay_import)

    result = CliRunner().invoke(
        cli,
        [
            "import", "replay",
            "--project", "proj-1",
            "--manifest", str(manifest),
            "--chapters", "1,a",
        ],
    )
    assert result.exit_code != 0
    assert "1,2,3" in result.output  # 格式示例
    assert "逗号分隔" in result.output


def test_replay_failed_chapters_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _make_manifest(tmp_path)

    async def fake_replay_import(
        project_id: str,
        manifest_path: Path,
        *,
        chapters: set[int] | None = None,
        run_id: str | None = None,
    ) -> ReplayReport:
        return ReplayReport(
            run_id="run-fail",
            project_id=project_id,
            outcomes=[
                _applied_outcome(1, "风起"),
                ChapterReplayOutcome(
                    chapter_number=2,
                    title="雨夜",
                    status="failed",
                    error="settlement 验证失败",
                ),
            ],
        )

    _patch_replay_import(monkeypatch, fake_replay_import)

    result = CliRunner().invoke(
        cli,
        ["import", "replay", "--project", "proj-1", "--manifest", str(manifest)],
    )
    assert result.exit_code == 1
    assert "失败章节" in result.output
    assert "第 2 章" in result.output
    assert "恢复建议" in result.output


def test_replay_import_error_becomes_click_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _make_manifest(tmp_path)

    async def fake_replay_import(*args: Any, **kwargs: Any) -> ReplayReport:
        raise ImportReplayError("回放被拒绝：清单未确认")

    _patch_replay_import(monkeypatch, fake_replay_import)

    result = CliRunner().invoke(
        cli,
        ["import", "replay", "--project", "proj-1", "--manifest", str(manifest)],
    )
    assert result.exit_code != 0
    assert "回放被拒绝：清单未确认" in result.output


# ---------------------------------------------------------------------------
# Task 237-4: import synthesize / publish
# ---------------------------------------------------------------------------


def _seed_project(
    db_path: Path,
    project_id: str,
    *,
    genre_id: str = "scifi",
    lifecycle_status: str = "importing",
    title: str = "导入小说",
    protagonist: str = "林渊",
    with_world: bool = True,
) -> None:
    """直插项目与回放后世界观数据（sqlite3 默认不开 FK，供 CLI 只读统计）."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO projects (
                project_id, title, genre_id, protagonist_name, lifecycle_status
            ) VALUES (?, ?, ?, ?, ?)""",
            (project_id, title, genre_id, protagonist, lifecycle_status),
        )
        conn.execute(
            """INSERT INTO characters (
                character_id, project_id, name, role_type, background
            ) VALUES (?, ?, ?, 'protagonist', ?)""",
            (f"char-{project_id}", project_id, protagonist, "星河码头长大的拾荒少年"),
        )
        if with_world:
            for i, status in enumerate(("active", "active", "dormant"), start=1):
                conn.execute(
                    """INSERT INTO setting_snapshots (
                        setting_id, project_id, setting_name, setting_key, lifecycle_status
                    ) VALUES (?, ?, ?, ?, ?)""",
                    (f"set-{i}", project_id, f"设定{i}", f"key-{i}", status),
                )
            conn.execute(
                """INSERT INTO foreshadowings (
                    foreshadowing_id, project_id, description,
                    planted_in_chapter, status, lifecycle_status, source_version_id
                ) VALUES (?, ?, ?, 1, 'planted', 'active', 'ver-1')""",
                (f"fore-{project_id}", project_id, "神秘芯片的来历"),
            )
            for chapter in (1, 2):
                conn.execute(
                    """INSERT INTO summaries (
                        summary_id, project_id, chapter_number, plot_summary
                    ) VALUES (?, ?, ?, ?)""",
                    (
                        f"sum-{project_id}-{chapter}",
                        project_id,
                        chapter,
                        f"第{chapter}章摘要",
                    ),
                )
            conn.execute(
                """INSERT INTO character_states (
                    character_id, field, value, source_version_id
                ) VALUES (?, 'mood', '平静', 'ver-1')""",
                (f"char-{project_id}",),
            )
            for chapter in (1, 2):
                conn.execute(
                    """INSERT INTO import_replay_marks (
                        project_id, run_id, chapter_number, draft_version_id,
                        accepted_version_id, source_fingerprint
                    ) VALUES (?, 'run-1', ?, ?, ?, ?)""",
                    (
                        project_id,
                        chapter,
                        f"draft-{chapter}",
                        f"acc-{chapter}",
                        f"fp-{chapter}",
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def test_synthesize_happy_path(tmp_path: Path, import_cli_db: Path) -> None:
    _seed_project(import_cli_db, "proj-syn")

    result = CliRunner().invoke(
        cli, ["import", "synthesize", "--project", "proj-syn", "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert "scifi" in result.output
    assert "科幻" in result.output  # 体裁 profile 名称
    assert "林渊" in result.output
    assert "拾荒少年" in result.output
    assert "设定快照  : 3 条" in result.output
    assert "active=2" in result.output and "dormant=1" in result.output
    assert "活跃伏笔  : 1 条" in result.output
    assert "角色状态  : 1 条" in result.output
    assert "摘要覆盖至: 第 2 章" in result.output
    assert "已回放章数: 2" in result.output
    assert "import publish" in result.output


def test_synthesize_unknown_genre_fails(tmp_path: Path, import_cli_db: Path) -> None:
    _seed_project(import_cli_db, "proj-bad", genre_id="nonexistent", with_world=False)

    result = CliRunner().invoke(
        cli, ["import", "synthesize", "--project", "proj-bad", "--yes"]
    )
    assert result.exit_code != 0
    assert "nonexistent" in result.output


def test_synthesize_missing_project_fails(tmp_path: Path, import_cli_db: Path) -> None:
    result = CliRunner().invoke(
        cli, ["import", "synthesize", "--project", "ghost", "--yes"]
    )
    assert result.exit_code != 0
    assert "项目不存在" in result.output


def test_synthesize_confirm_rejected_exits_1(
    tmp_path: Path, import_cli_db: Path
) -> None:
    _seed_project(import_cli_db, "proj-syn", with_world=False)

    result = CliRunner().invoke(
        cli, ["import", "synthesize", "--project", "proj-syn"], input="n\n"
    )
    assert result.exit_code == 1
    assert "已取消" in result.output


def test_publish_activates_importing_project(
    tmp_path: Path, import_cli_db: Path
) -> None:
    _seed_project(import_cli_db, "proj-pub")

    result = CliRunner().invoke(
        cli, ["import", "publish", "--project", "proj-pub", "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert "已回放章数: 2" in result.output
    assert "songyan run" in result.output
    rows = _query(
        import_cli_db,
        "SELECT lifecycle_status FROM projects WHERE project_id = ?",
        ("proj-pub",),
    )
    assert rows == [("active",)]


def test_publish_already_active_is_idempotent(
    tmp_path: Path, import_cli_db: Path
) -> None:
    _seed_project(import_cli_db, "proj-pub")
    first = CliRunner().invoke(
        cli, ["import", "publish", "--project", "proj-pub", "--yes"]
    )
    assert first.exit_code == 0, first.output

    result = CliRunner().invoke(
        cli, ["import", "publish", "--project", "proj-pub", "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert "已是 active" in result.output


def test_publish_missing_project_fails(tmp_path: Path, import_cli_db: Path) -> None:
    result = CliRunner().invoke(
        cli, ["import", "publish", "--project", "ghost", "--yes"]
    )
    assert result.exit_code != 0
    assert "项目不存在" in result.output


def test_publish_confirm_rejected_keeps_importing(
    tmp_path: Path, import_cli_db: Path
) -> None:
    _seed_project(import_cli_db, "proj-pub")

    result = CliRunner().invoke(
        cli, ["import", "publish", "--project", "proj-pub"], input="n\n"
    )
    assert result.exit_code == 1
    assert "已取消" in result.output
    rows = _query(
        import_cli_db,
        "SELECT lifecycle_status FROM projects WHERE project_id = ?",
        ("proj-pub",),
    )
    assert rows == [("importing",)]
