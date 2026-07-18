"""Tests for V9 Task 175 阶段 A2 — call_llm usage 拦截落库与 agent 归因."""

from __future__ import annotations

import ast
import asyncio
import sys
import types
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest
from structlog.contextvars import bind_contextvars, reset_contextvars

from songyan.config import settings
from songyan.db.llm_call_usage_repo import LlmCallUsageRepository
from songyan.exceptions import LLMError
from songyan.llm import client as llm_client
from songyan.utils.cost_estimator import count_tokens, estimate_cost_from_tokens


class _FakeResponse:
    """模拟 langchain AIMessage：仅按测试需要暴露相应属性."""

    def __init__(
        self,
        content: str = "fake-text",
        usage_metadata: dict[str, Any] | None = None,
        response_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.content = content
        if usage_metadata is not None:
            self.usage_metadata = usage_metadata
        if response_metadata is not None:
            self.response_metadata = response_metadata


class _FakeChatLiteLLM:
    """ainvoke 按队列吐出 response 或抛出异常（仿 test_173 注入模式）."""

    responses: list[Any] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    async def ainvoke(self, messages: list[Any]) -> Any:
        item = self.responses.pop(0)
        if item is _HANG:
            await asyncio.Event().wait()  # 永不完成，直到外部取消
        if isinstance(item, Exception):
            raise item
        return item


_HANG = object()


@pytest.fixture(autouse=True)
async def _clean_state() -> Any:
    await llm_client.aclose_llm_clients()
    _FakeChatLiteLLM.responses.clear()
    reset_contextvars()
    yield
    reset_contextvars()
    _FakeChatLiteLLM.responses.clear()
    await llm_client.aclose_llm_clients()


# 模块导入时捕获真实 helper（conftest 的 mute 发生在每个测试运行时，此刻未 patch）
_REAL_RECORD_USAGE = llm_client._record_llm_call_usage


@pytest.fixture(autouse=True)
def _restore_llm_call_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """豁免 tests/conftest.py 的遥测 mute：本模块验证的就是真实落库路径.

    conftest autouse fixture 先于本 fixture 执行（同 scope 下 conftest 优先），
    此处重新绑回真实 `_record_llm_call_usage`，teardown 由同一 monkeypatch 统一还原。
    """
    monkeypatch.setattr(llm_client, "_record_llm_call_usage", _REAL_RECORD_USAGE)


def _install_fake_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.ModuleType("langchain_litellm")
    fake_module.__spec__ = ModuleSpec("langchain_litellm", loader=None)
    fake_module.ChatLiteLLM = _FakeChatLiteLLM  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_litellm", fake_module)
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.test")
    monkeypatch.setattr(settings, "llm_model", "fake-model")
    monkeypatch.setattr(settings, "llm_run_call_budget", 0)


async def _fetch_rows(db_file: Path) -> list[dict[str, Any]]:
    async with aiosqlite.connect(str(db_file)) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT * FROM llm_call_usage ORDER BY id")
        return [dict(row) for row in await cursor.fetchall()]


# --------------------------------------------------------------------------- #
# usage 提取与落库
# --------------------------------------------------------------------------- #
class TestUsageRecording:
    async def test_usage_metadata_recorded(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """langchain-core usage_metadata → token_source='response' + pricing estimate."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(usage_metadata={"input_tokens": 100, "output_tokens": 50})
        )

        result = await llm_client.call_llm("prompt")

        assert result == "fake-text"
        rows = await _fetch_rows(test_db)
        assert len(rows) == 1
        row = rows[0]
        assert row["token_source"] == "response"
        assert row["prompt_tokens"] == 100
        assert row["completion_tokens"] == 50
        assert row["cost_source"] == "pricing_estimate"
        assert row["cost_cny"] == pytest.approx(
            estimate_cost_from_tokens(100, 50, "fake-model")
        )
        assert row["model"] == "fake-model"
        assert row["success"] == 1
        assert row["retry_attempt"] == 0
        assert row["error"] is None
        assert row["latency_ms"] >= 0

    async def test_provider_cost_recorded(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """响应元数据带 provider cost（litellm response_cost）→ cost_source='provider_cost'."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(
                usage_metadata={"input_tokens": 100, "output_tokens": 50},
                response_metadata={"response_cost": 0.005},
            )
        )

        await llm_client.call_llm("prompt")

        row = (await _fetch_rows(test_db))[0]
        assert row["token_source"] == "response"
        assert row["cost_source"] == "provider_cost"
        assert row["cost_cny"] == pytest.approx(0.005)

    async def test_cache_tokens_from_deepseek_native_fields(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """litellm token_usage 的 DeepSeek cache hit/miss 字段落库."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(
                response_metadata={
                    "token_usage": {
                        "prompt_tokens": 200,
                        "completion_tokens": 80,
                        "prompt_cache_hit_tokens": 150,
                        "prompt_cache_miss_tokens": 50,
                    }
                }
            )
        )

        await llm_client.call_llm("prompt")

        row = (await _fetch_rows(test_db))[0]
        assert row["token_source"] == "response"
        assert row["prompt_tokens"] == 200
        assert row["completion_tokens"] == 80
        assert row["cached_tokens"] == 150
        assert row["cache_miss_tokens"] == 50

    async def test_cache_tokens_from_prompt_tokens_details(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """prompt_tokens_details.cached_tokens 作为 cache hit 来源（无 miss 字段时为 NULL）."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(
                response_metadata={
                    "token_usage": {
                        "prompt_tokens": 200,
                        "completion_tokens": 80,
                        "prompt_tokens_details": {"cached_tokens": 120},
                    }
                }
            )
        )

        await llm_client.call_llm("prompt")

        row = (await _fetch_rows(test_db))[0]
        assert row["token_source"] == "response"
        assert row["cached_tokens"] == 120
        assert row["cache_miss_tokens"] is None

    async def test_missing_usage_falls_back_to_estimate(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """response 无任何 usage → 文本估算，token_source='estimate'."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(_FakeResponse(content="无用量响应"))
        prompt = "估算路径提示"

        await llm_client.call_llm(prompt)

        row = (await _fetch_rows(test_db))[0]
        assert row["token_source"] == "estimate"
        assert row["cost_source"] == "pricing_estimate"
        assert row["prompt_tokens"] == count_tokens(prompt, "fake-model")
        assert row["completion_tokens"] == count_tokens("无用量响应", "fake-model")
        assert row["prompt_tokens"] > 0
        assert row["completion_tokens"] > 0
        assert row["cached_tokens"] is None
        assert row["cache_miss_tokens"] is None


# --------------------------------------------------------------------------- #
# 重试语义：每次尝试一行
# --------------------------------------------------------------------------- #
class TestRetryAttemptRecording:
    async def test_first_failure_then_success_records_two_rows(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """首次失败 + 二次成功 → attempt 0 失败行 + attempt 1 成功行."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.extend(
            [
                ConnectionError("boom"),
                _FakeResponse(usage_metadata={"input_tokens": 10, "output_tokens": 5}),
            ]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await llm_client.call_llm("prompt")

        assert result == "fake-text"
        rows = await _fetch_rows(test_db)
        assert len(rows) == 2
        first, second = rows
        assert first["retry_attempt"] == 0
        assert first["success"] == 0
        assert "boom" in first["error"]
        assert first["prompt_tokens"] == 0
        assert first["completion_tokens"] == 0
        assert first["cost_cny"] == pytest.approx(0.0)
        assert second["retry_attempt"] == 1
        assert second["success"] == 1
        assert second["prompt_tokens"] == 10
        assert second["completion_tokens"] == 5
        assert second["error"] is None


# --------------------------------------------------------------------------- #
# agent 归因（174 contextvars 字段链）
# --------------------------------------------------------------------------- #
class TestAgentAttribution:
    async def test_bound_context_recorded(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """bind_contextvars 后落库行带 agent 与 174 关联字段."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(usage_metadata={"input_tokens": 1, "output_tokens": 1})
        )
        bind_contextvars(
            agent="writer",
            run_id="run-1",
            project_id="proj-1",
            chapter_number=3,
            stage="write",
            version_id="v-1",
        )

        await llm_client.call_llm("prompt")

        row = (await _fetch_rows(test_db))[0]
        assert row["agent"] == "writer"
        assert row["run_id"] == "run-1"
        assert row["project_id"] == "proj-1"
        assert row["chapter_number"] == 3
        assert row["stage"] == "write"
        assert row["version_id"] == "v-1"

    async def test_agent_unknown_without_binding(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """无绑定上下文 → agent='unknown'，可空字段为 NULL."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(usage_metadata={"input_tokens": 1, "output_tokens": 1})
        )

        await llm_client.call_llm("prompt")

        row = (await _fetch_rows(test_db))[0]
        assert row["agent"] == "unknown"
        assert row["run_id"] is None
        assert row["project_id"] is None
        assert row["chapter_number"] is None
        assert row["stage"] is None
        assert row["version_id"] is None


# --------------------------------------------------------------------------- #
# telemetry 不阻断生成
# --------------------------------------------------------------------------- #
class TestTelemetryNeverBlocks:
    async def test_record_failure_does_not_break_call(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """repo.record 抛异常时 call_llm 仍正常返回文本."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(usage_metadata={"input_tokens": 1, "output_tokens": 1})
        )

        async def _explode(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("db down")

        monkeypatch.setattr(LlmCallUsageRepository, "record", _explode)

        result = await llm_client.call_llm("prompt")

        assert result == "fake-text"
        assert await _fetch_rows(test_db) == []


# --------------------------------------------------------------------------- #
# agent 静态覆盖：所有 call_llm 调用点必须具备 agent 绑定
# --------------------------------------------------------------------------- #
def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _find_unbound_call_sites(path: Path, root: Path) -> list[str]:
    """扫描单个文件：call_llm 调用的任一层外层函数无 bind_contextvars(agent=...) 即违规."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    func_stack: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    bind_func_ids: set[int] = set()

    class _Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            func_stack.append(node)
            self.generic_visit(node)
            func_stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            func_stack.append(node)
            self.generic_visit(node)
            func_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            name = _call_name(node)
            if (
                name == "bind_contextvars"
                and any(kw.arg == "agent" for kw in node.keywords)
                and func_stack
            ):
                bind_func_ids.add(id(func_stack[-1]))
            if name == "call_llm" and not any(
                id(func) in bind_func_ids for func in func_stack
            ):
                violations.append(f"{path.relative_to(root)}:{node.lineno}")
            self.generic_visit(node)

    _Visitor().visit(tree)
    return violations


def test_all_agent_call_llm_sites_bind_agent() -> None:
    """src/songyan/agents/** 中每个 call_llm( 调用点，所在函数或其外层入口必须绑 agent.

    局限：只静态检查绑定的存在性（调用点任一层外层函数含 bind_contextvars(agent=...)），
    不校验 agent 绑定值与模块的对应关系，也不做运行时调用顺序/可达性分析。
    """
    project_root = Path(__file__).resolve().parents[1]
    agents_root = project_root / "src" / "songyan" / "agents"
    violations: list[str] = []
    for path in sorted(agents_root.rglob("*.py")):
        violations.extend(_find_unbound_call_sites(path, agents_root))
    assert violations == [], f"以下 call_llm 调用点缺少 agent 绑定: {violations}"


# --------------------------------------------------------------------------- #
# A2 review 修复回归：取消落行 + 提取路径补盲
# --------------------------------------------------------------------------- #
class TestCancelledAttemptRecording:
    async def test_cancelled_attempt_recorded(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """in-flight 尝试被取消（总超时/外部取消）→ success=0 + cancelled/timeout 落行."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(_HANG)

        task = asyncio.create_task(llm_client.call_llm("prompt"))
        await asyncio.sleep(0.05)  # 让调用进入 ainvoke
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        rows = await _fetch_rows(test_db)
        assert len(rows) == 1
        row = rows[0]
        assert row["success"] == 0
        assert "cancel" in row["error"].lower()
        assert row["prompt_tokens"] == 0
        assert row["completion_tokens"] == 0
        assert row["latency_ms"] >= 0


class TestExtractionEdgeCases:
    async def test_cache_read_from_langchain_usage_metadata(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """langchain input_token_details.cache_read → cached_tokens（miss 无来源为 NULL）."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(
                usage_metadata={
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "input_token_details": {"cache_read": 60},
                }
            )
        )

        await llm_client.call_llm("prompt")

        row = (await _fetch_rows(test_db))[0]
        assert row["token_source"] == "response"
        assert row["cached_tokens"] == 60
        assert row["cache_miss_tokens"] is None

    async def test_usage_from_response_metadata_usage_key(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """response_metadata 的备选 "usage" 键 → token_source='response'."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(
                response_metadata={
                    "usage": {"prompt_tokens": 90, "completion_tokens": 40}
                }
            )
        )

        await llm_client.call_llm("prompt")

        row = (await _fetch_rows(test_db))[0]
        assert row["token_source"] == "response"
        assert row["prompt_tokens"] == 90
        assert row["completion_tokens"] == 40

    async def test_extraction_failure_records_zero_estimate(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """usage 提取抛异常 → 记零值 estimate，call_llm 正常返回."""

        class _ExplodingResponse:
            content = "explode-text"

            @property
            def usage_metadata(self) -> Any:
                raise RuntimeError("boom")

        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(_ExplodingResponse())

        result = await llm_client.call_llm("prompt")

        assert result == "explode-text"
        row = (await _fetch_rows(test_db))[0]
        assert row["success"] == 1
        assert row["token_source"] == "estimate"
        assert row["cost_source"] == "pricing_estimate"
        assert row["prompt_tokens"] == 0
        assert row["completion_tokens"] == 0
        assert row["cost_cny"] == pytest.approx(0.0)

    async def test_error_truncated_to_500_chars(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """失败尝试的 error 摘要截断到 500 字符."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(ConnectionError("x" * 600))

        with pytest.raises(LLMError, match="LLM 调用失败"):
            await llm_client.call_llm("prompt", max_retries=1)

        row = (await _fetch_rows(test_db))[0]
        assert row["success"] == 0
        assert len(row["error"]) == 500
