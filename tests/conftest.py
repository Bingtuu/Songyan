"""Shared pytest fixtures for all test suites."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.config import settings
from songyan.db.migrations import init_schema


@pytest.fixture
async def test_db(tmp_path: Path) -> Path:
    """Create an isolated temp database for each test."""
    db_file = tmp_path / "test.db"
    original_url = settings.database_url
    original_mode = settings.checkpointer_mode
    settings.database_url = f"sqlite:///{db_file}"
    settings.checkpointer_mode = "memory"
    await init_schema(db_file)
    from songyan.workflows.checkpointer import reset_checkpointer
    await reset_checkpointer()
    yield db_file
    settings.database_url = original_url
    settings.checkpointer_mode = original_mode


@pytest.fixture
def mock_llm():
    """P2-7: Unified mock LLM fixture for all test suites."""
    from unittest.mock import patch

    with patch("songyan.llm.client.call_llm") as mock:
        mock.return_value = '{"result": "test"}'
        yield mock
