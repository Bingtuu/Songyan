"""Tests for CLI report command — Task 119.

Layer 1: 报告入口测试
Layer 2: 一致性检查测试
Layer 3: 文档引用测试（脚本级）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.evals.__main__ import _validate_report_consistency
from songyan.evals.__main__ import main as evals_main
from songyan.models.run_log import ChapterRunLog


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _make_log(
    chapter: int,
    success: bool = True,
    budget_used: float | None = 0.95,
    context_emergency: bool = False,
    **overrides: Any,
) -> ChapterRunLog:
    """创建测试用 ChapterRunLog。"""
    from datetime import datetime

    defaults: dict[str, Any] = {
        "log_id": f"log-{chapter}",
        "run_id": "test-run",
        "project_id": "proj-test",
        "chapter_number": chapter,
        "started_at": datetime(2026, 1, 1),
        "finished_at": datetime(2026, 1, 1, 0, 1),
        "success": success,
        "word_count": 3200,
        "budget_used": budget_used,
        "context_emergency": context_emergency,
        "character_states_loaded": 5,
        "soft_refs_loaded": 3,
        "settlement_success": True,
        "summary_success": True,
        "quality_gate_passed": True,
        "revision_rounds": 1,
    }
    defaults.update(overrides)
    return ChapterRunLog(**defaults)


class TestReportCli:
    """Layer 1: 报告入口测试."""

    def test_report_cli_requires_run_id(self, runner: CliRunner) -> None:
        """无参数时应报错。"""
        result = runner.invoke(cli, ["report"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "Required" in result.output

    def test_report_cli_no_jsonl_warns(self, runner: CliRunner) -> None:
        """JSONL 不存在时应返回非 0，并提示恢复路径。"""
        with patch(
            "songyan.cli.main.read_run_logs",
            return_value=[],
        ):
            result = runner.invoke(cli, ["report", "--run-id", "nonexistent-run-id"])
        assert result.exit_code == 1
        assert "未找到运行日志" in result.output
        assert "[missing_artifact]" in result.output
        assert "Get-ChildItem logs/chapter_runs" in result.output

    def test_report_cli_generates_report(self, runner: CliRunner, tmp_path: Path) -> None:
        """传入有效的 run-id（mock read_run_logs）时应生成报告。"""
        logs = [_make_log(101), _make_log(102), _make_log(103)]

        with patch(
            "songyan.evals.streaming_report.read_run_logs",
            return_value=logs,
        ), patch(
            "songyan.cli.main.read_run_logs",
            return_value=logs,
        ), patch(
            "songyan.cli.main.write_report",
            return_value=tmp_path / "report-test.md",
        ):
            result = runner.invoke(
                cli,
                ["report", "--run-id", "test-run"],
            )
            assert "报告已生成" in result.output or result.exit_code == 0

    def test_report_cli_no_logs_warning(self, runner: CliRunner) -> None:
        """JSONL 无日志时应警告。"""
        with patch(
            "songyan.cli.main.read_run_logs",
            return_value=[],
        ):
            result = runner.invoke(cli, ["report", "--run-id", "empty-run"])
            assert result.exit_code == 1
            assert "[missing_artifact]" in result.output

    def test_report_cli_rejects_path_like_run_id(self, runner: CliRunner) -> None:
        """run_id 不允许参与路径拼接。"""
        result = runner.invoke(cli, ["report", "--run-id", "../outside"])

        assert result.exit_code != 0
        assert "invalid run_id" in result.output


class TestValidateReportConsistency:
    """Layer 2: 一致性检查测试."""

    def test_consistency_ok(self) -> None:
        """章节数匹配、无缺失字段时无警告。"""
        logs = [_make_log(101), _make_log(102)]
        report = "# Ch101-Ch102 流式验证报告\n\n总章节数: 2\n"
        warnings = _validate_report_consistency(logs, report)
        assert len(warnings) == 0

    def test_consistency_missing_budget(self) -> None:
        """成功章节缺少 budget_used 时应警告。"""
        logs = [_make_log(101, budget_used=None), _make_log(102, budget_used=0.9)]
        report = "# Ch101-Ch102 流式验证报告\n\n总章节数: 2\n"
        warnings = _validate_report_consistency(logs, report)
        assert any("budget_used" in w for w in warnings)

    def test_consistency_context_emergency(self) -> None:
        """有 ContextEmergency 章节时应警告。"""
        logs = [
            _make_log(101, context_emergency=True),
            _make_log(102, context_emergency=False),
        ]
        report = "# Ch101-Ch102 流式验证报告\n\n总章节数: 2\n"
        warnings = _validate_report_consistency(logs, report)
        assert any("ContextEmergency" in w for w in warnings)

    def test_consistency_chapter_range_mismatch(self) -> None:
        """报告章节范围与 JSONL 条目数不符时应警告。"""
        logs = [_make_log(101), _make_log(102), _make_log(103)]
        # 报告声称 Ch101-Ch102（2章）但实际3章
        report = "# Ch101-Ch102 流式验证报告\n\n总章节数: 2\n"
        warnings = _validate_report_consistency(logs, report)
        assert any("不符" in w or "不匹配" in w for w in warnings)


class TestEvalsMainModule:
    """Layer 1: evals/__main__.py 模块入口测试."""

    def test_evals_main_missing_jsonl(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JSONL 文件不存在时应返回 1。"""
        # 切换到 tmp_path 使其无 logs/chapter_runs
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["x", "--run-id", "nonexistent"]):
            result = evals_main()
        assert result == 1

    def test_evals_main_valid_run_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """有效 run-id 应生成报告并返回 0。"""
        # 创建假的 JSONL
        jsonl_dir = tmp_path / "logs" / "chapter_runs"
        jsonl_dir.mkdir(parents=True)
        log = _make_log(101)
        jsonl_path = jsonl_dir / "test-run.jsonl"
        jsonl_path.write_text(log.model_dump_json() + "\n", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        output_path = str(tmp_path / "report.md")
        with patch("sys.argv", ["x", "--run-id", "test-run", "--output", output_path]):
            result = evals_main()
        assert result == 0


class TestWrapperResultCodes:
    """Layer 2: PowerShell wrapper 结果码测试（功能层面）。"""

    def test_passing_chapters_all_success(self) -> None:
        """全部成功章节应无警告。"""
        logs = [
            _make_log(101, success=True, budget_used=0.95, context_emergency=False),
            _make_log(102, success=True, budget_used=0.88, context_emergency=False),
        ]
        report = (
            "# Ch101-Ch102\n\n"
            "| 章节 | 成功 | budget_used |\n"
            "| Ch101 | Y | 0.950 |\n"
            "| Ch102 | Y | 0.880 |\n"
        )
        warnings = _validate_report_consistency(logs, report)
        assert len(warnings) == 0

    def test_failed_chapter_in_report(self) -> None:
        """有失败章节时不应触发一致性警告（一致性检查只关注报告格式与数据匹配）。"""
        logs = [
            _make_log(101, success=True, budget_used=0.95),
            _make_log(102, success=False, budget_used=None),
        ]
        report = "# Ch101-Ch102\n\n| 章节 | 成功 |\n| Ch101 | Y |\n| Ch102 | N |\n"
        warnings = _validate_report_consistency(logs, report)
        # 无 budget_used 缺失警告（失败章节允许无 budget_used）
        budget_warnings = [w for w in warnings if "budget_used" in w]
        assert len(budget_warnings) == 0
