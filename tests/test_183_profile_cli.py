"""Task 183 tests for ``songyan profile`` CLI."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.genre_runtime_profile_repo import load_profile
from songyan.db.migrations import init_schema
from songyan.services.profile_service import upsert_profile_overrides


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def profile_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "profile.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "checkpointer_mode", "memory")
    return db_path


def _row(payload: dict[str, Any], field: str) -> dict[str, Any]:
    for row in payload["rows"]:
        if row["field"] == field:
            return row
    pytest.fail(f"missing row: {field}")


def _db_profile_json(db_path: Path, genre: str) -> dict[str, Any]:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT profile_json FROM genre_runtime_profiles WHERE genre = ?",
            (genre,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return json.loads(row[0])


def test_profile_show_json_does_not_create_missing_db(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(cli, ["profile", "show", "--genre", "xuanhuan", "--json"])

    assert result.exit_code == 0, result.output
    assert not profile_db.exists()
    payload = json.loads(result.output)
    assert payload["genre"] == "xuanhuan"
    assert _row(payload, "base_budget")["registry_value"] == 15000
    assert _row(payload, "base_budget")["db_override_present"] is False
    assert _row(payload, "base_budget")["effective_value"] == 15000


def test_profile_upsert_writes_default_plus_explicit_override(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "profile",
            "upsert",
            "--genre",
            "xuanhuan",
            "--set",
            "ramp_per_chapter=300",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    db_payload = _db_profile_json(profile_db, "xuanhuan")
    assert db_payload["base_budget"] == 8000
    assert db_payload["ramp_per_chapter"] == 300
    assert db_payload["foreshadowing_horizon_floor"] == 0

    loaded = asyncio.run(load_profile("xuanhuan"))
    assert loaded.base_budget == 15000
    assert loaded.ramp_per_chapter == 300
    assert loaded.foreshadowing_horizon_floor == 48

    payload = json.loads(result.output)
    ramp = _row(payload, "ramp_per_chapter")
    assert ramp["registry_value"] == 250
    assert ramp["db_override_value"] == 300
    assert ramp["effective_value"] == 300


def test_profile_nested_set_marks_whole_submodel_replacement(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "profile",
            "upsert",
            "--genre",
            "wuxia",
            "--set",
            "continuity.health_overdue_weight=0.2",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    weight = _row(payload, "continuity.health_overdue_weight")
    threshold = _row(payload, "continuity.forgotten_threshold")

    assert weight["db_override_present"] is True
    assert weight["nested_replacement"] is True
    assert weight["registry_value"] == 0.15
    assert weight["db_override_value"] == 0.2
    assert weight["effective_value"] == 0.2
    assert threshold["db_override_present"] is True
    assert threshold["nested_replacement"] is True


def test_profile_reset_clears_override_intent(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    first = runner.invoke(
        cli,
        ["profile", "upsert", "--genre", "urban", "--set", "base_budget=12000"],
    )
    assert first.exit_code == 0, first.output
    assert asyncio.run(load_profile("urban")).base_budget == 12000

    reset = runner.invoke(
        cli,
        ["profile", "upsert", "--genre", "urban", "--reset", "--json"],
    )

    assert reset.exit_code == 0, reset.output
    assert json.loads(reset.output)["rows"] == []
    assert asyncio.run(load_profile("urban")).base_budget == 14000


def test_profile_upsert_rejects_unknown_genre(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        ["profile", "upsert", "--genre", "unknown", "--set", "base_budget=12000"],
    )

    assert result.exit_code == 1
    assert "unknown genre" in result.output
    assert profile_db.exists()


def test_profile_upsert_rejects_duplicate_json_and_set_field(
    runner: CliRunner,
    profile_db: Path,
    tmp_path: Path,
) -> None:
    overrides = tmp_path / "overrides.json"
    overrides.write_text(json.dumps({"base_budget": 12000}), encoding="utf-8")

    result = runner.invoke(
        cli,
        [
            "profile",
            "upsert",
            "--genre",
            "urban",
            "--from-json",
            str(overrides),
            "--set",
            "base_budget=13000",
        ],
    )

    assert result.exit_code == 1
    assert "duplicate override field" in result.output
    assert not profile_db.exists()


def test_profile_upsert_rejects_unknown_nested_field(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        ["profile", "upsert", "--genre", "wuxia", "--set", "continuity.typo=0.2"],
    )

    assert result.exit_code == 1
    assert "unknown profile field" in result.output
    assert profile_db.exists()


def test_profile_validate_current_passes(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        ["profile", "validate", "--genre", "xuanhuan", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "pass"
    assert payload["target"] == "effective"
    assert payload["summary"]["error"] == 0


def test_profile_validate_current_reports_unreadable_db_override(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    first = runner.invoke(
        cli,
        ["profile", "upsert", "--genre", "urban", "--set", "base_budget=15000"],
    )
    assert first.exit_code == 0, first.output
    conn = sqlite3.connect(profile_db)
    try:
        conn.execute(
            "UPDATE genre_runtime_profiles SET profile_json = ? WHERE genre = ?",
            ("{bad json", "urban"),
        )
        conn.commit()
    finally:
        conn.close()

    result = runner.invoke(
        cli,
        ["profile", "validate", "--genre", "urban", "--json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "fail"
    assert payload["issues"][0]["field"] == "db_override"


def test_profile_validate_pending_warns_for_nested_replacement(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "profile",
            "validate",
            "--genre",
            "wuxia",
            "--set",
            "continuity.health_overdue_weight=0.8",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "warn"
    fields = {issue["field"] for issue in payload["issues"]}
    assert "continuity" in fields
    assert "continuity.health_overdue_weight" in fields


def test_profile_validate_pending_error_exits_nonzero(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "profile",
            "validate",
            "--genre",
            "scifi",
            "--set",
            "partition_ratios.character_states=-0.1",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "fail"
    assert any(
        issue["field"] == "partition_ratios.character_states"
        for issue in payload["issues"]
    )


def test_profile_validate_rejects_non_finite_float(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "profile",
            "validate",
            "--genre",
            "scifi",
            "--set",
            "partition_ratios.character_states=NaN",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "fail"
    assert any(
        issue["field"] == "partition_ratios.character_states"
        and "finite" in issue["message"]
        for issue in payload["issues"]
    )


def test_profile_validate_reports_pydantic_error_as_json_fail(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "profile",
            "validate",
            "--genre",
            "scifi",
            "--set",
            "base_budget=500",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "fail"
    assert payload["summary"]["error"] == 1
    assert payload["issues"][0]["field"] == "profile_override"


def test_profile_upsert_dry_run_does_not_write(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "profile",
            "upsert",
            "--genre",
            "urban",
            "--set",
            "base_budget=15000",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["dry_run"] is True
    assert payload["history"] is None
    assert not profile_db.exists()


def test_profile_upsert_rejects_validation_error_before_write(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "profile",
            "upsert",
            "--genre",
            "scifi",
            "--set",
            "character_decay.archive_window=20",
            "--set",
            "character_decay.dormant_window=30",
        ],
    )

    assert result.exit_code == 1
    assert "profile validation failed" in result.output


def test_profile_upsert_rolls_back_when_history_write_fails(
    profile_db: Path,
) -> None:
    asyncio.run(init_schema(profile_db))
    conn = sqlite3.connect(profile_db)
    try:
        conn.execute("DROP TABLE genre_runtime_profile_history")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(Exception, match="failed to upsert genre runtime profile"):
        asyncio.run(upsert_profile_overrides("urban", {"base_budget": 15000}))

    conn = sqlite3.connect(profile_db)
    try:
        row = conn.execute(
            "SELECT profile_json FROM genre_runtime_profiles WHERE genre = ?",
            ("urban",),
        ).fetchone()
    finally:
        conn.close()
    assert row is None


def test_profile_history_and_rollback(
    runner: CliRunner,
    profile_db: Path,
) -> None:
    first = runner.invoke(
        cli,
        [
            "profile",
            "upsert",
            "--genre",
            "urban",
            "--set",
            "base_budget=15000",
            "--json",
        ],
    )
    assert first.exit_code == 0, first.output
    first_payload = json.loads(first.output)
    first_history_id = first_payload["history"]["history_id"]
    assert asyncio.run(load_profile("urban")).base_budget == 15000

    history = runner.invoke(
        cli,
        ["profile", "history", "--genre", "urban", "--json"],
    )
    assert history.exit_code == 0, history.output
    history_payload = json.loads(history.output)
    assert history_payload["rows"][0]["history_id"] == first_history_id

    rollback = runner.invoke(
        cli,
        [
            "profile",
            "rollback",
            "--genre",
            "urban",
            "--history-id",
            first_history_id,
            "--json",
        ],
    )
    assert rollback.exit_code == 0, rollback.output
    rollback_payload = json.loads(rollback.output)
    assert rollback_payload["history"]["action"].startswith("rollback:")
    assert asyncio.run(load_profile("urban")).base_budget == 14000
