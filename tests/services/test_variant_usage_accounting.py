"""切片 2（task 226）：variant generate 的 llm_call_usage 记账不重复且归因正确。

真实 client 路径（fake langchain_litellm 驱动）：每槽只落一行遥测，
project_id / agent 归因非空；服务层不得再显式 record 第二行。
"""

from __future__ import annotations

import sys
import types
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any

import aiosqlite
import pytest
from structlog.contextvars import reset_contextvars

import songyan.db.connection as conn_mod
from songyan.config import settings
from songyan.db import ProjectRepository
from songyan.db.migrations import init_schema
from songyan.llm import client as llm_client
from songyan.models import ProjectSetting
from songyan.services.variant_generate import generate_chapter_variants

# 模块导入时捕获真实 helper（conftest 的 mute 发生在每个测试运行时，此刻未 patch）
_REAL_RECORD_USAGE = llm_client._record_llm_call_usage


class _FakeResponse:
    """模拟 langchain AIMessage：仅暴露 content（usage 提取走零值兜底）。"""

    def __init__(self, content: str = "草稿正文。" * 25) -> None:
        self.content = content


class _FakeChatLiteLLM:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    async def ainvoke(self, messages: list[Any]) -> Any:
        return _FakeResponse()


@pytest.fixture(autouse=True)
def _restore_llm_call_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """豁免 tests/conftest.py 的遥测 mute：本模块验证的就是真实落库路径."""
    monkeypatch.setattr(llm_client, "_record_llm_call_usage", _REAL_RECORD_USAGE)


@pytest.fixture(autouse=True)
def _fake_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.ModuleType("langchain_litellm")
    fake_module.__spec__ = ModuleSpec("langchain_litellm", loader=None)
    fake_module.ChatLiteLLM = _FakeChatLiteLLM  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_litellm", fake_module)
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.test")
    monkeypatch.setattr(settings, "llm_model", "fake-model")
    monkeypatch.setattr(settings, "llm_run_call_budget", 0)
    monkeypatch.setattr(settings, "run_cost_budget", 0)


@pytest.fixture(autouse=True)
def _clean_context() -> Any:
    reset_contextvars()
    yield
    reset_contextvars()


@pytest.fixture
async def isolated_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Point get_db() at a temporary initialized database with a seeded project."""
    db_path = tmp_path / "variant_usage.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="wuxia",
            mode_id="webnovel",
            protagonist_name="顾长风",
        ),
        "p1",
    )
    return db_path


async def _usage_rows(db_path: Path) -> list[tuple[Any, ...]]:
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT project_id, agent, chapter_number, model, success "
            "FROM llm_call_usage ORDER BY id"
        )
        return await cursor.fetchall()


async def test_generate_records_one_usage_row_per_slot_with_attribution(
    isolated_db: Path,
) -> None:
    result = await generate_chapter_variants("p1", 5, n=2)
    assert len(result.variants) == 2

    rows = await _usage_rows(isolated_db)
    # 每槽恰好一行：client 遥测；显式 record 不得造成第二行
    assert len(rows) == 2
    for project_id, agent, chapter_number, _model, success in rows:
        assert project_id == "p1"
        assert agent == "variant.generate"
        assert chapter_number == 5
        assert success == 1
