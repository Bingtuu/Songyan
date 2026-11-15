"""task 266：角色/设定编辑 CLI（character / setting 命令族）。

exit 码 B11 同形：0 = 成功；2 = 业务拒绝（不存在 id / 主角 remove）；
1 = 缺库 / 缺项目。list 默认不含软删行，--include-archived 可见。
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
from songyan.db.repository import CharacterRepository, ProjectRepository
from songyan.db.settlement_repo import SettingSnapshotRepository
from songyan.models.character import Character
from songyan.models.project import ProjectSetting

_PROJECT = "p-profile-cli"
_PROTAGONIST_ID = "char-p"
_ANTAGONIST_ID = "char-z"
_SETTING_ID = "set-s"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def profile_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "profile-cli.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="urban",
            mode_id="webnovel",
            protagonist_name="陈屿",
            title="profile cli",
        ),
        _PROJECT,
    )
    await CharacterRepository().create(
        Character(
            character_id=_PROTAGONIST_ID,
            project_id=_PROJECT,
            name="陈屿",
            role_type="protagonist",
        )
    )
    await CharacterRepository().create(
        Character(
            character_id=_ANTAGONIST_ID,
            project_id=_PROJECT,
            name="周牧野",
            role_type="antagonist",
        )
    )
    from songyan.models.settlement import NewSetting

    await SettingSnapshotRepository().create(
        NewSetting(setting_name="Echo", description="旧座钟", source_quote="", setting_key="echo"),
        _PROJECT,
        _SETTING_ID,
    )
    return db_path


class TestCharacterList:
    def test_lists_characters(self, runner: CliRunner, profile_db: Path) -> None:
        result = runner.invoke(cli, ["character", "list", "--project-id", _PROJECT, "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        names = {c["name"] for c in payload["characters"]}
        assert names == {"陈屿", "周牧野"}

    def test_archived_hidden_by_default_and_flag_shows(
        self, runner: CliRunner, profile_db: Path
    ) -> None:
        result = runner.invoke(
            cli, ["character", "remove", "--project-id", _PROJECT, "--character-id", _ANTAGONIST_ID]
        )
        assert result.exit_code == 0, result.output

        result = runner.invoke(cli, ["character", "list", "--project-id", _PROJECT, "--json"])
        names = {c["name"] for c in json.loads(result.stdout)["characters"]}
        assert "周牧野" not in names

        result = runner.invoke(
            cli,
            ["character", "list", "--project-id", _PROJECT, "--include-archived", "--json"],
        )
        names = {c["name"] for c in json.loads(result.stdout)["characters"]}
        assert "周牧野" in names


class TestCharacterEdit:
    def test_edit_name(self, runner: CliRunner, profile_db: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "character",
                "edit",
                "--project-id",
                _PROJECT,
                "--character-id",
                _ANTAGONIST_ID,
                "--name",
                "周德顺",
                "--traits",
                '["沉默"]',
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["action"] == "update"

        result = runner.invoke(cli, ["character", "list", "--project-id", _PROJECT, "--json"])
        char = next(
            c
            for c in json.loads(result.stdout)["characters"]
            if c["character_id"] == _ANTAGONIST_ID
        )
        assert char["name"] == "周德顺"
        assert char["personality_traits"] == ["沉默"]

    def test_edit_missing_id_exit_2(self, runner: CliRunner, profile_db: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "character",
                "edit",
                "--project-id",
                _PROJECT,
                "--character-id",
                "nope",
                "--name",
                "x",
            ],
        )
        assert result.exit_code == 2


class TestCharacterRemove:
    def test_remove_then_noop(self, runner: CliRunner, profile_db: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "character",
                "remove",
                "--project-id",
                _PROJECT,
                "--character-id",
                _ANTAGONIST_ID,
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["action"] == "remove"

        result = runner.invoke(
            cli,
            [
                "character",
                "remove",
                "--project-id",
                _PROJECT,
                "--character-id",
                _ANTAGONIST_ID,
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["action"] == "noop"

    def test_remove_protagonist_exit_2(self, runner: CliRunner, profile_db: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "character",
                "remove",
                "--project-id",
                _PROJECT,
                "--character-id",
                _PROTAGONIST_ID,
            ],
        )
        assert result.exit_code == 2

    def test_remove_missing_id_exit_2(self, runner: CliRunner, profile_db: Path) -> None:
        result = runner.invoke(
            cli, ["character", "remove", "--project-id", _PROJECT, "--character-id", "nope"]
        )
        assert result.exit_code == 2


class TestSettingCommands:
    def test_setting_list_edit_remove_cycle(self, runner: CliRunner, profile_db: Path) -> None:
        result = runner.invoke(cli, ["setting", "list", "--project-id", _PROJECT, "--json"])
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["settings"][0]["setting_name"] == "Echo"

        result = runner.invoke(
            cli,
            [
                "setting",
                "edit",
                "--project-id",
                _PROJECT,
                "--setting-id",
                _SETTING_ID,
                "--name",
                "座钟",
                "--description",
                "雨夜慢五分钟",
            ],
        )
        assert result.exit_code == 0, result.output

        result = runner.invoke(
            cli,
            [
                "setting",
                "remove",
                "--project-id",
                _PROJECT,
                "--setting-id",
                _SETTING_ID,
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["action"] == "remove"

        result = runner.invoke(cli, ["setting", "list", "--project-id", _PROJECT, "--json"])
        assert json.loads(result.stdout)["settings"] == []

        # 审计两笔（edit + remove）
        con = sqlite3.connect(profile_db)
        count = con.execute("SELECT COUNT(*) FROM profile_edit_history").fetchone()[0]
        con.close()
        assert count == 2

    def test_setting_remove_missing_exit_2(self, runner: CliRunner, profile_db: Path) -> None:
        result = runner.invoke(
            cli, ["setting", "remove", "--project-id", _PROJECT, "--setting-id", "nope"]
        )
        assert result.exit_code == 2

    def test_missing_project_exit_1(self, runner: CliRunner, profile_db: Path) -> None:
        result = runner.invoke(cli, ["character", "list", "--project-id", "p-missing"])
        assert result.exit_code == 1
