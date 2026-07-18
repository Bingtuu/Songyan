"""Shared pytest fixtures for all test suites."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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


@pytest.fixture(autouse=True)
def _mute_llm_call_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 175: 默认把 call_llm 遥测落库掐成 no-op（防止污染开发库）.

    未隔离 DB 的既有测试（如 test_154 / test_llm_client 直调 call_llm）在 A2 后
    会向 settings.database_url 指向的开发库写入 run_id=NULL 的脏遥测行，甚至新建
    库文件；此处默认拦截。patch 点选 client 侧名字而非 repo.record：helper 定义在
    `songyan.llm._usage`（阶段 B 抽离），client import 后按模块属性查找
    `_record_llm_call_usage`，拦截后对 repo 直测
    （tests/db/test_llm_call_usage_repo.py）零影响。
    豁免：需要真实遥测落库的测试模块（tests/test_175_cost_tracking.py）在模块内
    autouse fixture 显式还原真实 helper。
    注意：run 级成本累计器（_llm_run_cost_cny）独立于该 helper，mute 不影响累计。
    """

    async def _noop(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr("songyan.llm.client._record_llm_call_usage", _noop)
