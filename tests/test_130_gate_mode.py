"""Task 130: --gate-mode CLI 参数测试."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.models.gate_config import GateConfig
from songyan.models.project_run import ProjectRunResult


@pytest.fixture
def runner() -> CliRunner:
    """Click CliRunner 实例."""
    return CliRunner()


def _mock_pipeline_result() -> ProjectRunResult:
    """返回一个可用的 run_project_pipeline 结果."""
    return ProjectRunResult(
        project_id="proj-test",
        run_id="run-test",
        chapters_completed=[1, 2, 3],
        chapters_failed=[],
        final_status="completed",
        total_duration_sec=1.0,
    )


class TestGateModeHelp:
    """help 文本测试."""

    def test_run_help_includes_gate_mode(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0, result.output
        assert "--gate-mode" in result.output
        assert "observe" in result.output
        assert "enforce" in result.output


class TestGateModeDefault:
    """默认 enforce 模式测试."""

    @patch("songyan.cli.main.run_project_pipeline")
    def test_default_uses_enforce(
        self,
        mock_pipeline: AsyncMock,
        runner: CliRunner,
    ) -> None:
        mock_pipeline.return_value = _mock_pipeline_result()
        result = runner.invoke(
            cli,
            [
                "run",
                "--project-id",
                "proj-test",
                "--chapters",
                "1-3",
                "--auto-confirm",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "门禁模式: enforce" in result.output
        assert mock_pipeline.called
        _, kwargs = mock_pipeline.call_args
        gate_config = kwargs.get("gate_config")
        assert gate_config is not None
        assert gate_config.is_enforce()
        assert gate_config.health_low_gate_enabled
        assert gate_config.health_low_p1_halt
        assert gate_config.health_low_streak_halt
        assert gate_config.health_low_score_halt_enabled
        assert gate_config.context_emergency_gate_enabled
        assert gate_config.context_emergency_single_halt
        assert gate_config.context_emergency_failure_halt


class TestGateModeObserve:
    """observe 模式测试."""

    @patch("songyan.cli.main.run_project_pipeline")
    def test_explicit_observe(
        self,
        mock_pipeline: AsyncMock,
        runner: CliRunner,
    ) -> None:
        mock_pipeline.return_value = _mock_pipeline_result()
        result = runner.invoke(
            cli,
            [
                "run",
                "--project-id",
                "proj-test",
                "--chapters",
                "1-3",
                "--auto-confirm",
                "--gate-mode",
                "observe",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "门禁模式: observe" in result.output
        _, kwargs = mock_pipeline.call_args
        assert kwargs["gate_config"].is_observe()


class TestGateModeEnforce:
    """enforce 模式测试."""

    @patch("songyan.cli.main.run_project_pipeline")
    def test_enforce_enables_candidate_gates(
        self,
        mock_pipeline: AsyncMock,
        runner: CliRunner,
    ) -> None:
        mock_pipeline.return_value = _mock_pipeline_result()
        result = runner.invoke(
            cli,
            [
                "run",
                "--project-id",
                "proj-test",
                "--chapters",
                "1-3",
                "--auto-confirm",
                "--gate-mode",
                "enforce",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "门禁模式: enforce" in result.output
        _, kwargs = mock_pipeline.call_args
        gate_config = kwargs.get("gate_config")
        assert gate_config is not None
        assert gate_config.is_enforce()
        assert gate_config.health_low_gate_enabled
        assert gate_config.health_low_p1_halt
        assert gate_config.health_low_streak_halt
        assert gate_config.health_low_score_halt_enabled
        assert gate_config.context_emergency_gate_enabled
        assert gate_config.context_emergency_single_halt
        assert gate_config.context_emergency_failure_halt

    def test_invalid_gate_mode_rejected(self, runner: CliRunner) -> None:
        result = runner.invoke(
            cli,
            [
                "run",
                "--project-id",
                "proj-test",
                "--chapters",
                "1-3",
                "--auto-confirm",
                "--gate-mode",
                "strict",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "无效" in result.output


class TestGateConfigFactory:
    """GateConfig.for_mode 工厂方法测试."""

    def test_for_mode_observe_is_default(self) -> None:
        cfg = GateConfig.for_mode("observe")
        assert cfg.is_observe()
        assert not cfg.health_low_gate_enabled
        assert not cfg.context_emergency_gate_enabled

    def test_for_mode_enforce_enables_gates(self) -> None:
        cfg = GateConfig.for_mode("enforce")
        assert cfg.is_enforce()
        assert cfg.health_low_gate_enabled
        assert cfg.health_low_p1_halt
        assert cfg.health_low_streak_halt
        assert cfg.health_low_score_halt_enabled
        assert cfg.context_emergency_gate_enabled
        assert cfg.context_emergency_single_halt
        assert cfg.context_emergency_failure_halt
