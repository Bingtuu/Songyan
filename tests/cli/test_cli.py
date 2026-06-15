"""CLI 命令测试."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli

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
