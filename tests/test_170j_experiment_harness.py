"""Tests for the Task 170j experiment harness."""

from pathlib import Path

from scripts.run_170j_experiment import _resolve_db_path


def test_resolve_db_path() -> None:
    assert _resolve_db_path("minimal_voice_anchor") == Path(
        ".tmp/task170j_minimal_voice_anchor.db"
    )
    assert _resolve_db_path("other_strategy") == Path(".tmp/task170j_other_strategy.db")
