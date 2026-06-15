"""Tests for CLI mark commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.models import ProjectSetting

pytestmark = pytest.mark.asyncio


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def mark_cli_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "cli_mark.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="Lin Yuan",
        ),
        "p1",
    )
    return db_path


class TestMarkAdd:
    def test_add_mark_success(self, runner: CliRunner, mark_cli_db: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "mark", "add",
                "--project-id", "p1",
                "--type", "setting",
                "--target", "120Hz干扰器",
                "--note", "核心道具",
                "--priority", "9",
                "--chapter", "8",
            ],
        )
        assert result.exit_code == 0
        assert "标记已创建" in result.output
        assert "120Hz干扰器" in result.output

    def test_add_mark_priority_clamped(self, runner: CliRunner, mark_cli_db: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "mark", "add",
                "--project-id", "p1",
                "--type", "custom",
                "--target", "x",
                "--priority", "15",
            ],
        )
        assert result.exit_code == 0
        assert "priority=10" in result.output


class TestMarkList:
    def test_list_empty(self, runner: CliRunner, mark_cli_db: Path) -> None:
        result = runner.invoke(cli, ["mark", "list", "--project-id", "p1"])
        assert result.exit_code == 0
        assert "暂无标记" in result.output

    def test_list_with_marks(self, runner: CliRunner, mark_cli_db: Path) -> None:
        # Seed marks
        runner.invoke(
            cli,
            ["mark", "add", "--project-id", "p1", "--type", "setting", "--target", "A", "--priority", "9"],
        )
        runner.invoke(
            cli,
            ["mark", "add", "--project-id", "p1", "--type", "character", "--target", "B", "--priority", "5"],
        )

        result = runner.invoke(cli, ["mark", "list", "--project-id", "p1"])
        assert result.exit_code == 0
        assert "A" in result.output
        assert "B" in result.output

    def test_list_filter_by_type(self, runner: CliRunner, mark_cli_db: Path) -> None:
        runner.invoke(
            cli,
            ["mark", "add", "--project-id", "p1", "--type", "setting", "--target", "A"],
        )
        runner.invoke(
            cli,
            ["mark", "add", "--project-id", "p1", "--type", "character", "--target", "B"],
        )

        result = runner.invoke(
            cli, ["mark", "list", "--project-id", "p1", "--type", "setting"]
        )
        assert result.exit_code == 0
        assert "A" in result.output
        assert "B" not in result.output

    def test_list_suggested_no_report(self, runner: CliRunner, mark_cli_db: Path) -> None:
        result = runner.invoke(
            cli, ["mark", "list", "--project-id", "p1", "--suggested"]
        )
        assert result.exit_code == 0
        assert "暂无系统建议标记" in result.output


class TestMarkRemove:
    def test_remove_existing(self, runner: CliRunner, mark_cli_db: Path) -> None:
        add_result = runner.invoke(
            cli,
            ["mark", "add", "--project-id", "p1", "--type", "setting", "--target", "X"],
        )
        assert add_result.exit_code == 0
        mark_id = add_result.output.split("标记已创建: ")[1].split(" [")[0].strip()

        result = runner.invoke(
            cli, ["mark", "remove", "--project-id", "p1", "--mark-id", mark_id]
        )
        assert result.exit_code == 0
        assert "标记已删除" in result.output

    def test_remove_missing(self, runner: CliRunner, mark_cli_db: Path) -> None:
        result = runner.invoke(
            cli, ["mark", "remove", "--project-id", "p1", "--mark-id", "missing"]
        )
        assert result.exit_code == 0
        assert "未找到标记" in result.output


class TestMarkUpdatePriority:
    def test_update_priority(self, runner: CliRunner, mark_cli_db: Path) -> None:
        add_result = runner.invoke(
            cli,
            ["mark", "add", "--project-id", "p1", "--type", "setting", "--target", "X", "--priority", "5"],
        )
        assert add_result.exit_code == 0
        mark_id = add_result.output.split("标记已创建: ")[1].split(" [")[0].strip()

        result = runner.invoke(
            cli,
            ["mark", "update-priority", "--project-id", "p1", "--mark-id", mark_id, "--priority", "10"],
        )
        assert result.exit_code == 0
        assert "优先级已更新" in result.output
        assert "→ 10" in result.output

    def test_update_priority_missing(self, runner: CliRunner, mark_cli_db: Path) -> None:
        result = runner.invoke(
            cli,
            ["mark", "update-priority", "--project-id", "p1", "--mark-id", "missing", "--priority", "10"],
        )
        assert result.exit_code == 0
        assert "未找到标记" in result.output
