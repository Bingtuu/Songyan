"""task 255：storyline 编辑 CLI（tech-post-m4 v2 §A）。

切片 1：审计表 + edit outline（upsert，读-改-写，审计行同事务）。
切片 2：edit arc / edit thread（校验拒绝）。
切片 3：remove（软删 archived）+ show --json 结构。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.models.project import ProjectSetting

_PROJECT = "p-storyline"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def story_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "storyline-cli.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="storyline cli",
        ),
        _PROJECT,
    )
    return db_path


def _history(db_path: Path) -> list[tuple]:
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT target_type, target_id, action, before_json, after_json "
        "FROM storyline_edit_history ORDER BY rowid"
    ).fetchall()
    con.close()
    return rows


class TestEditOutline:
    def test_create_writes_row_and_audit(
        self, runner: CliRunner, story_db: Path
    ) -> None:
        result = runner.invoke(
            cli,
            [
                "storyline",
                "edit",
                "outline",
                "--project-id",
                _PROJECT,
                "--core-conflict",
                "末班车的秘密",
                "--mainline-synopsis",
                "陈屿追查铜牌",
                "--themes",
                '["都市","灵异"]',
                "--intended-ending",
                "真相公开",
            ],
        )
        assert result.exit_code == 0, result.output

        con = sqlite3.connect(story_db)
        row = con.execute(
            "SELECT core_conflict, mainline_synopsis, themes, intended_ending "
            "FROM story_outlines WHERE project_id=?",
            (_PROJECT,),
        ).fetchone()
        con.close()
        assert row is not None
        assert row[0] == "末班车的秘密"
        assert json.loads(row[2]) == ["都市", "灵异"]

        history = _history(story_db)
        assert len(history) == 1
        assert history[0][0] == "outline"
        assert history[0][2] == "create"
        assert history[0][3] is None  # before_json 空
        assert "末班车的秘密" in history[0][4]

    def test_partial_update_preserves_other_fields(
        self, runner: CliRunner, story_db: Path
    ) -> None:
        base = [
            "storyline", "edit", "outline",
            "--project-id", _PROJECT,
            "--core-conflict", "旧冲突",
            "--mainline-synopsis", "旧主线",
        ]
        assert runner.invoke(cli, base).exit_code == 0
        result = runner.invoke(
            cli,
            [
                "storyline", "edit", "outline",
                "--project-id", _PROJECT,
                "--core-conflict", "新冲突",
            ],
        )
        assert result.exit_code == 0, result.output

        con = sqlite3.connect(story_db)
        row = con.execute(
            "SELECT core_conflict, mainline_synopsis FROM story_outlines "
            "WHERE project_id=?",
            (_PROJECT,),
        ).fetchone()
        con.close()
        assert row == ("新冲突", "旧主线")

        history = _history(story_db)
        assert [h[2] for h in history] == ["create", "update"]
        assert "旧冲突" in history[1][3]  # before_json
        assert "新冲突" in history[1][4]  # after_json


class TestShow:
    def test_show_json_structure(
        self, runner: CliRunner, story_db: Path
    ) -> None:
        runner.invoke(
            cli,
            [
                "storyline", "edit", "outline",
                "--project-id", _PROJECT,
                "--core-conflict", "冲突",
            ],
        )
        result = runner.invoke(
            cli,
            ["storyline", "show", "--project-id", _PROJECT, "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert set(payload.keys()) >= {"outline", "arcs", "threads"}
        assert payload["outline"]["core_conflict"] == "冲突"
        assert payload["arcs"] == []
        assert payload["threads"] == []


class TestEditArc:
    def test_create_and_audit(self, runner: CliRunner, story_db: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "storyline", "edit", "arc",
                "--project-id", _PROJECT,
                "--arc-id", "arc-1",
                "--arc-index", "0",
                "--start-chapter", "1",
                "--end-chapter", "10",
                "--arc-goal", "找到铜牌",
                "--is-mainline",
            ],
        )
        assert result.exit_code == 0, result.output
        con = sqlite3.connect(story_db)
        row = con.execute(
            "SELECT start_chapter, end_chapter, arc_goal, is_mainline "
            "FROM arc_plans WHERE arc_id='arc-1'"
        ).fetchone()
        con.close()
        assert row == (1, 10, "找到铜牌", 1)
        history = _history(story_db)
        assert history[-1][0] == "arc" and history[-1][2] == "create"

    def test_rejects_start_after_end(self, runner: CliRunner, story_db: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "storyline", "edit", "arc",
                "--project-id", _PROJECT,
                "--arc-id", "arc-bad",
                "--start-chapter", "10",
                "--end-chapter", "5",
            ],
        )
        assert result.exit_code == 2
        assert "start" in result.stderr.lower() or "范围" in result.stderr

    def test_rejects_unknown_thread_ref(self, runner: CliRunner, story_db: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "storyline", "edit", "arc",
                "--project-id", _PROJECT,
                "--arc-id", "arc-1",
                "--open-thread", "ghost-thread",
            ],
        )
        assert result.exit_code == 2
        assert "ghost-thread" in result.stderr

    def test_rejects_duplicate_arc_index(self, runner: CliRunner, story_db: Path) -> None:
        base = [
            "storyline", "edit", "arc",
            "--project-id", _PROJECT,
            "--arc-index", "0",
        ]
        assert runner.invoke(cli, base + ["--arc-id", "arc-a"]).exit_code == 0
        result = runner.invoke(cli, base + ["--arc-id", "arc-b"])
        assert result.exit_code == 2


class TestEditThread:
    def test_upsert_and_update(self, runner: CliRunner, story_db: Path) -> None:
        create = runner.invoke(
            cli,
            [
                "storyline", "edit", "thread",
                "--project-id", _PROJECT,
                "--thread-id", "t-1",
                "--title", "铜牌来历",
                "--description", "铜牌从哪来",
            ],
        )
        assert create.exit_code == 0, create.output
        update = runner.invoke(
            cli,
            [
                "storyline", "edit", "thread",
                "--project-id", _PROJECT,
                "--thread-id", "t-1",
                "--status", "opened",
                "--opened-chapter", "2",
            ],
        )
        assert update.exit_code == 0, update.output
        con = sqlite3.connect(story_db)
        row = con.execute(
            "SELECT title, description, status, opened_chapter "
            "FROM plot_threads WHERE thread_id='t-1'"
        ).fetchone()
        con.close()
        assert row == ("铜牌来历", "铜牌从哪来", "opened", 2)
        history = _history(story_db)
        assert [h[2] for h in history[-2:]] == ["create", "update"]

    def test_rejects_unknown_resolve_arc(
        self, runner: CliRunner, story_db: Path
    ) -> None:
        runner.invoke(
            cli,
            [
                "storyline", "edit", "thread",
                "--project-id", _PROJECT,
                "--thread-id", "t-1",
            ],
        )
        result = runner.invoke(
            cli,
            [
                "storyline", "edit", "thread",
                "--project-id", _PROJECT,
                "--thread-id", "t-1",
                "--expected-resolve-arc", "99",
            ],
        )
        assert result.exit_code == 2


class TestRemove:
    def _mk_arc(self, runner: CliRunner, arc_id: str = "arc-1") -> None:
        result = runner.invoke(
            cli,
            [
                "storyline", "edit", "arc",
                "--project-id", _PROJECT,
                "--arc-id", arc_id,
                "--arc-index", "0",
                "--start-chapter", "1",
                "--end-chapter", "10",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_remove_arc_soft_deletes_and_audits(
        self, runner: CliRunner, story_db: Path
    ) -> None:
        self._mk_arc(runner)
        result = runner.invoke(
            cli,
            [
                "storyline", "remove", "arc",
                "--project-id", _PROJECT,
                "--arc-id", "arc-1",
            ],
        )
        assert result.exit_code == 0, result.output
        con = sqlite3.connect(story_db)
        row = con.execute(
            "SELECT archived FROM arc_plans WHERE arc_id='arc-1'"
        ).fetchone()
        con.close()
        assert row == (1,)
        history = _history(story_db)
        assert history[-1][0] == "arc" and history[-1][2] == "remove"

    def test_remove_arc_idempotent(self, runner: CliRunner, story_db: Path) -> None:
        self._mk_arc(runner)
        args = [
            "storyline", "remove", "arc",
            "--project-id", _PROJECT,
            "--arc-id", "arc-1",
        ]
        assert runner.invoke(cli, args).exit_code == 0
        again = runner.invoke(cli, args)
        assert again.exit_code == 0, again.output

    def test_remove_thread_soft_deletes(
        self, runner: CliRunner, story_db: Path
    ) -> None:
        runner.invoke(
            cli,
            [
                "storyline", "edit", "thread",
                "--project-id", _PROJECT,
                "--thread-id", "t-1",
                "--title", "线索",
            ],
        )
        result = runner.invoke(
            cli,
            [
                "storyline", "remove", "thread",
                "--project-id", _PROJECT,
                "--thread-id", "t-1",
            ],
        )
        assert result.exit_code == 0, result.output
        con = sqlite3.connect(story_db)
        row = con.execute(
            "SELECT archived FROM plot_threads WHERE thread_id='t-1'"
        ).fetchone()
        con.close()
        assert row == (1,)

    def test_fingerprint_changes_after_remove(self, runner: CliRunner, story_db: Path) -> None:
        """软删从故事线切片排除 → 本章指纹变化（252 标脏联动入口）。"""
        import asyncio

        from songyan.services.storyline_fingerprint import storyline_fingerprint

        self._mk_arc(runner)
        before = asyncio.run(storyline_fingerprint(_PROJECT, 5))
        runner.invoke(
            cli,
            [
                "storyline", "remove", "arc",
                "--project-id", _PROJECT,
                "--arc-id", "arc-1",
            ],
        )
        after = asyncio.run(storyline_fingerprint(_PROJECT, 5))
        assert before != after

    def test_show_marks_archived(self, runner: CliRunner, story_db: Path) -> None:
        self._mk_arc(runner)
        runner.invoke(
            cli,
            [
                "storyline", "remove", "arc",
                "--project-id", _PROJECT,
                "--arc-id", "arc-1",
            ],
        )
        result = runner.invoke(
            cli,
            ["storyline", "show", "--project-id", _PROJECT, "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        arc = payload["arcs"][0]
        assert arc["archived"] is True
