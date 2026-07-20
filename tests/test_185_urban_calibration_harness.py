"""Tests for V9 Task 185 short-window calibration harness plumbing."""

from __future__ import annotations

import asyncio
from pathlib import Path

from scripts import run_172a7_genre_validation as harness
from songyan.config import settings
from songyan.db.genre_runtime_profile_repo import load_profile
from songyan.db.migrations import init_schema
from songyan.services.profile_service import upsert_profile_overrides


def test_configure_database_url_uses_explicit_db_path(tmp_path: Path) -> None:
    old_url = settings.database_url
    db_path = tmp_path / "urban.db"
    try:
        resolved = harness._configure_database_url("urban", db_path)

        assert resolved == db_path
        assert settings.database_url == f"sqlite:///{db_path}"
        assert db_path.parent.is_dir()
    finally:
        settings.database_url = old_url


def test_configure_database_url_keeps_temp_db_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    old_url = settings.database_url
    temp_dir = tmp_path / "task172a7_urban_test"
    monkeypatch.setattr(harness.tempfile, "mkdtemp", lambda prefix: str(temp_dir))
    try:
        resolved = harness._configure_database_url("urban", None)

        assert resolved == temp_dir / "songyan.db"
        assert settings.database_url == f"sqlite:///{temp_dir / 'songyan.db'}"
    finally:
        settings.database_url = old_url


def test_exit_code_for_results_detects_template_errors() -> None:
    assert harness._exit_code_for_results([{"template_id": "urban", "status": "completed"}]) == 0
    assert harness._exit_code_for_results([{"template_id": "urban", "error": "boom"}]) == 1
    assert (
        harness._exit_code_for_results(
            [
                {"template_id": "urban", "status": "completed"},
                {"template_id": "scifi", "error": "boom"},
            ]
        )
        == 1
    )


def test_db_override_visible_through_harness_db(tmp_path: Path) -> None:
    """Task book TDD item 4: an override written to DB X is read via `--db X`."""
    old_url = settings.database_url
    db_path = tmp_path / "urban.db"
    try:
        # Mirror the CLI flow: init schema, then upsert into the same DB.
        settings.database_url = f"sqlite:///{db_path}"
        asyncio.run(init_schema())
        asyncio.run(upsert_profile_overrides("urban", {"base_budget": 12000}))

        resolved = harness._configure_database_url("urban", db_path)

        assert resolved == db_path
        assert asyncio.run(load_profile("urban")).base_budget == 12000
    finally:
        settings.database_url = old_url
