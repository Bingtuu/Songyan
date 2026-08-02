"""Task 180: ``songyan doctor`` CLI tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.services.doctor_service import DoctorCheck


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def doctor_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://api.deepseek.com")
    monkeypatch.setattr(settings, "llm_model", "deepseek-chat")
    monkeypatch.setattr(settings, "llm_temperature", 0.7)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'songyan.db'}")
    monkeypatch.setattr(settings, "checkpointer_mode", "memory")
    return tmp_path


def test_doctor_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["doctor", "--help"])

    assert result.exit_code == 0, result.output
    assert "--json" in result.output
    assert "--check-llm" in result.output
    assert "--init-db" in result.output


def test_doctor_warns_when_env_file_missing_but_key_configured(
    runner: CliRunner,
    doctor_env: Path,
) -> None:
    result = runner.invoke(cli, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "[WARN] config.env" in result.output
    assert "[PASS] llm.key" in result.output
    assert "test-key" not in result.output


def test_doctor_fails_when_llm_key_missing(
    runner: CliRunner,
    doctor_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_api_key", "")

    result = runner.invoke(cli, ["doctor"])

    assert result.exit_code == 1
    assert "[FAIL] llm.key" in result.output
    assert "LLM_API_KEY" in result.output


def test_doctor_fails_on_non_sqlite_database_url(
    runner: CliRunner,
    doctor_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "database_url", "postgres://localhost/songyan")

    result = runner.invoke(cli, ["doctor"])

    assert result.exit_code == 1
    assert "[FAIL] db.url" in result.output
    assert "sqlite" in result.output


def test_doctor_warns_for_existing_db_with_missing_schema(
    runner: CliRunner,
    doctor_env: Path,
) -> None:
    db_path = doctor_env / "empty.db"
    db_path.write_bytes(b"")
    settings.database_url = f"sqlite:///{db_path}"

    result = runner.invoke(cli, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "[WARN] db.schema" in result.output
    assert "schema missing" in result.output


def test_doctor_init_db_creates_complete_schema(
    runner: CliRunner,
    doctor_env: Path,
) -> None:
    db_path = doctor_env / "init.db"
    settings.database_url = f"sqlite:///{db_path}"

    result = runner.invoke(cli, ["doctor", "--init-db"])

    assert result.exit_code == 0, result.output
    assert db_path.exists()
    assert "[PASS] db.schema: schema complete" in result.output


def test_doctor_warns_when_schema_has_migration_drift(
    runner: CliRunner,
    doctor_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = doctor_env / "drift.db"
    db_path.write_bytes(b"")
    settings.database_url = f"sqlite:///{db_path}"

    async def fake_verify_schema(conn) -> list[str]:
        return []

    async def fake_schema_drift(conn) -> list[str]:
        return ["projects.estimated_chapters"]

    monkeypatch.setattr("songyan.services.doctor_service.verify_schema", fake_verify_schema)
    monkeypatch.setattr("songyan.services.doctor_service._schema_drift", fake_schema_drift)

    result = runner.invoke(cli, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "[WARN] db.schema" in result.output
    assert "schema drift detected" in result.output
    assert "projects.estimated_chapters" in result.output


def test_doctor_package_resources_pass(
    runner: CliRunner,
    doctor_env: Path,
) -> None:
    result = runner.invoke(cli, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "[PASS] resources.package" in result.output
    assert "genres" in result.output
    assert "modes" in result.output


def test_doctor_json_output(
    runner: CliRunner,
    doctor_env: Path,
) -> None:
    result = runner.invoke(cli, ["doctor", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "warn"
    assert payload["summary"]["fail"] == 0
    assert any(item["id"] == "llm.key" for item in payload["checks"])


def test_doctor_subprocess_reports_invalid_checkpointer_without_traceback(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["CHECKPOINTER_MODE"] = "invalid"
    env["LLM_API_KEY"] = "task210-dummy-key"
    env["DATABASE_URL"] = f"sqlite:///{tmp_path / 'doctor.db'}"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from songyan.cli.main import cli; cli()",
            "doctor",
            "--json",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr
    payload = json.loads(result.stdout)
    checks = {item["id"]: item for item in payload["checks"]}
    assert payload["status"] == "fail"
    assert checks["config.load"]["status"] == "pass"
    assert checks["db.url"]["message"] == f"sqlite:///{tmp_path / 'doctor.db'}"
    assert checks["runtime.checkpointer"]["status"] == "fail"


def test_doctor_fails_for_invalid_run_cost_budget(
    runner: CliRunner,
    doctor_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SONGYAN_RUN_COST_BUDGET", "not-a-number")

    result = runner.invoke(cli, ["doctor", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    checks = {item["id"]: item for item in payload["checks"]}
    assert checks["runtime.budget"]["status"] == "fail"
    assert "not-a-number" in checks["runtime.budget"]["message"]


def test_doctor_does_not_probe_llm_by_default(
    runner: CliRunner,
    doctor_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_probe() -> DoctorCheck:
        raise AssertionError("LLM probe should be opt-in")

    monkeypatch.setattr("songyan.services.doctor_service._probe_llm_connectivity", fail_probe)

    result = runner.invoke(cli, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "llm.connectivity" not in result.output


def test_doctor_check_llm_runs_probe(
    runner: CliRunner,
    doctor_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_probe() -> DoctorCheck:
        return DoctorCheck("llm.connectivity", "pass", "mock probe ok")

    monkeypatch.setattr("songyan.services.doctor_service._probe_llm_connectivity", fake_probe)

    result = runner.invoke(cli, ["doctor", "--check-llm"])

    assert result.exit_code == 0, result.output
    assert "[PASS] llm.connectivity: mock probe ok" in result.output


def test_doctor_fails_for_invalid_checkpointer_mode(
    runner: CliRunner,
    doctor_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "checkpointer_mode", "invalid")

    result = runner.invoke(cli, ["doctor"])

    assert result.exit_code == 1
    assert "[FAIL] runtime.checkpointer" in result.output
