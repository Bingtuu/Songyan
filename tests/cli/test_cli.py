"""CLI 命令测试."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.models.project_run import ProjectRunResult

# ---------------------------------------------------------------------------
#  fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    """Click CliRunner 实例."""
    return CliRunner()


@pytest.fixture
def db_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """将数据库指向临时文件，返回 db_path."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "cli_test.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    return db_path


# ---------------------------------------------------------------------------
#  Layer 1: CLI 命令注册
# ---------------------------------------------------------------------------


class TestCommandRegistration:
    """验证命令可被引用且 help 文本正确."""

    def test_create_project_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["create-project", "--help"])
        assert result.exit_code == 0
        assert "创建小说项目" in result.output

    def test_list_projects_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["list-projects", "--help"])
        assert result.exit_code == 0
        assert "列出" in result.output

    def test_index_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["index", "--help"])
        assert result.exit_code == 0
        assert "--project-id" in result.output
        assert "--chapters" in result.output
        assert "--rebuild" in result.output


# ---------------------------------------------------------------------------
#  Layer 2: create-project 交互测试
# ---------------------------------------------------------------------------


class TestCreateProject:
    """create-project 交互向导测试."""

    # 输入序列：
    # 1. 模式序号 3 → webnovel (hybrid=1, literary=2, webnovel=3, webnovel_intense=4)
    # 2. 题材序号 7 → xuanhuan
    #    (mystery_noir=1, post_apocalyptic=2, scifi=3, urban=4,
    #     urban_fantasy=5, wuxia=6, xuanhuan=7)
    # 3. 标题: 测试项目
    # 4. 主角姓名: 林凡
    # 5. 主角背景: (空)
    # 6. 核心钩子: (空)
    # 7. 目标读者预期: (空)
    # 8. 目标字数: (空，默认 100000)
    # 9. 基调: (空，默认 热血)
    # 10. 预估总章数: (空，默认 30)
    # 11. 每章目标字数: (空，默认 3000)
    # 12. 故事结构: 4 → free (回车默认)
    # 13. 子类型: 无（当前 genre 无 sub_genres，自动跳过）
    _INPUT = "3\n7\n测试项目\n林凡\n\n\n\n\n\n\n\n4\n"

    # 三幕式输入（用于测试 arc_boundaries 自动推导）
    _INPUT_THREE_ACT = "3\n7\n测试项目\n林凡\n\n\n\n\n\n40\n3000\n1\n"

    def test_creates_project_in_db(
        self,
        runner: CliRunner,
        db_settings: Path,
    ) -> None:
        result = runner.invoke(
            cli,
            ["create-project"],
            input=self._INPUT,
        )
        assert result.exit_code == 0, result.output
        assert "项目已创建" in result.output
        assert "webnovel" in result.output
        assert "xuanhuan" in result.output

        # 从输出中提取 project_id
        project_id = self._extract_project_id(result.output)

        # 使用同步 sqlite3 验证数据库
        conn = sqlite3.connect(str(db_settings))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["title"] == "测试项目"
        assert row["genre_id"] == "xuanhuan"
        assert row["mode_id"] == "webnovel"
        assert row["protagonist_name"] == "林凡"
        assert row["target_word_count"] == 100_000
        assert row["tone"] == "热血"

    def test_project_id_is_unique(
        self,
        runner: CliRunner,
        db_settings: Path,
    ) -> None:
        result1 = runner.invoke(
            cli, ["create-project"], input=self._INPUT
        )
        result2 = runner.invoke(
            cli, ["create-project"], input=self._INPUT
        )
        assert result1.exit_code == 0
        assert result2.exit_code == 0

        id1 = self._extract_project_id(result1.output)
        id2 = self._extract_project_id(result2.output)
        assert id1 != id2
        assert len(id1) == 32  # uuid.hex
        assert len(id2) == 32

    def test_seed_fields_stored_in_db(
        self,
        runner: CliRunner,
        db_settings: Path,
    ) -> None:
        result = runner.invoke(
            cli,
            ["create-project"],
            input=self._INPUT,
        )
        assert result.exit_code == 0
        project_id = self._extract_project_id(result.output)

        conn = sqlite3.connect(str(db_settings))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["estimated_chapters"] == 30
        assert row["words_per_chapter"] == 3000
        assert row["story_structure"] == "free"
        assert row["arc_boundaries_auto"] == 0
        assert row["sub_genre_id"] is None

    def test_three_act_derives_arc_boundaries(
        self,
        runner: CliRunner,
        db_settings: Path,
    ) -> None:
        result = runner.invoke(
            cli,
            ["create-project"],
            input=self._INPUT_THREE_ACT,
        )
        assert result.exit_code == 0, result.output
        project_id = self._extract_project_id(result.output)

        conn = sqlite3.connect(str(db_settings))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["story_structure"] == "three_act"
        assert row["estimated_chapters"] == 40
        assert row["arc_boundaries_auto"] == 1
        import json
        assert json.loads(row["arc_boundaries"]) == [10, 30]
        assert "Arc 边界" in result.output

    @staticmethod
    def _extract_project_id(output: str) -> str:
        for line in output.splitlines():
            if line.startswith("✓ 项目已创建:"):
                return line.split(":", 1)[1].strip()
        pytest.fail("未在输出中找到 project_id")


# ---------------------------------------------------------------------------
#  Task 179: run 命令体验修复
# ---------------------------------------------------------------------------


def _task179_result(project_id: str = "proj-179") -> ProjectRunResult:
    return ProjectRunResult(
        project_id=project_id,
        run_id="run-179",
        chapters_completed=[1, 2],
        chapters_failed=[],
        total_duration_sec=1.25,
        final_status="completed",
    )


class TestRunCommandExperience:
    def test_run_outputs_run_id(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def fake_resolve_mode(project_id: str, explicit_mode_id: str | None) -> str:
            assert project_id == "proj-179"
            assert explicit_mode_id is None
            return "webnovel_intense"

        async def fake_run_project_pipeline(**kwargs):
            return _task179_result(project_id=kwargs["project_id"])

        monkeypatch.setattr("songyan.cli.main._resolve_run_mode_id", fake_resolve_mode)
        monkeypatch.setattr("songyan.cli.main.run_project_pipeline", fake_run_project_pipeline)

        result = runner.invoke(
            cli,
            [
                "run",
                "--project-id",
                "proj-179",
                "--chapters",
                "1-2",
                "--auto-confirm",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "run_id: run-179" in result.output

    def test_run_uses_project_mode_when_mode_not_explicit(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: dict[str, object] = {}

        class FakeProjectRepository:
            async def get(self, project_id: str):
                calls["repo_project_id"] = project_id
                return SimpleNamespace(mode_id="webnovel_intense")

        async def fake_run_project_pipeline(**kwargs):
            calls["pipeline"] = kwargs
            return _task179_result(project_id=kwargs["project_id"])

        monkeypatch.setattr("songyan.cli.main.ProjectRepository", FakeProjectRepository)
        monkeypatch.setattr("songyan.cli.main.run_project_pipeline", fake_run_project_pipeline)

        result = runner.invoke(
            cli,
            [
                "run",
                "--project-id",
                "proj-179",
                "--chapters",
                "1-2",
                "--auto-confirm",
            ],
        )

        assert result.exit_code == 0, result.output
        assert calls["repo_project_id"] == "proj-179"
        pipeline = calls["pipeline"]
        assert isinstance(pipeline, dict)
        assert pipeline["mode_id"] == "webnovel_intense"

    def test_run_explicit_mode_overrides_project_mode(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: dict[str, object] = {}

        class FakeProjectRepository:
            async def get(self, project_id: str):
                calls["repo_called"] = True
                return SimpleNamespace(mode_id="webnovel_intense")

        async def fake_run_project_pipeline(**kwargs):
            calls["pipeline"] = kwargs
            return _task179_result(project_id=kwargs["project_id"])

        monkeypatch.setattr("songyan.cli.main.ProjectRepository", FakeProjectRepository)
        monkeypatch.setattr("songyan.cli.main.run_project_pipeline", fake_run_project_pipeline)

        result = runner.invoke(
            cli,
            [
                "run",
                "--project-id",
                "proj-179",
                "--chapters",
                "1-2",
                "--mode-id",
                "hybrid",
                "--auto-confirm",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "repo_called" not in calls
        pipeline = calls["pipeline"]
        assert isinstance(pipeline, dict)
        assert pipeline["mode_id"] == "hybrid"

    def test_run_fails_when_project_mode_cannot_be_loaded(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class FakeProjectRepository:
            async def get(self, project_id: str):
                return None

        async def fake_run_project_pipeline(**kwargs):
            raise AssertionError("pipeline should not run")

        monkeypatch.setattr("songyan.cli.main.ProjectRepository", FakeProjectRepository)
        monkeypatch.setattr("songyan.cli.main.run_project_pipeline", fake_run_project_pipeline)

        result = runner.invoke(
            cli,
            [
                "run",
                "--project-id",
                "missing",
                "--chapters",
                "1",
                "--auto-confirm",
            ],
        )

        assert result.exit_code != 0
        assert "无法读取项目 mode_id" in result.output


# ---------------------------------------------------------------------------
#  Layer 3: list-projects 测试
# ---------------------------------------------------------------------------


class TestListProjects:
    """list-projects 命令测试."""

    _CREATE_INPUT = "3\n7\n测试项目\n林凡\n\n\n\n\n\n\n\n\n"

    def test_empty_db_shows_hint(
        self,
        runner: CliRunner,
        db_settings: Path,
    ) -> None:
        result = runner.invoke(cli, ["list-projects"])
        assert result.exit_code == 0
        assert "暂无项目" in result.output

    def test_lists_created_project(
        self,
        runner: CliRunner,
        db_settings: Path,
    ) -> None:
        # 先创建一个项目
        runner.invoke(cli, ["create-project"], input=self._CREATE_INPUT)

        result = runner.invoke(cli, ["list-projects"])
        assert result.exit_code == 0
        assert "测试项目" in result.output
        assert "xuanhuan" in result.output
        assert "webnovel" in result.output
        assert "林凡" in result.output
