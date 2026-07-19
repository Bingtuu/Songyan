"""Tests for V9 Task 175 — 阶段 A2（usage 落库 + agent 归因）与阶段 B（成本熔断 + total_cost）."""

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
from structlog.testing import capture_logs

from songyan.cli.main import _render_cost_section
from songyan.config import Settings, settings
from songyan.db.llm_call_usage_repo import LlmCallUsageRepository
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.evals.cost_report import render_cost_section
from songyan.exceptions import LLMBudgetExceededError, LLMError
from songyan.llm import client as llm_client
from songyan.models import ChapterHead, ChapterVersion, ProjectRunState, ProjectSetting
from songyan.utils.cost_estimator import (
    count_tokens,
    estimate_cost_from_tokens,
    format_cost_estimate,
)
from songyan.workflows.phase2_graph import _refresh_run_total_cost, run_project_pipeline


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
    llm_client._llm_run_cost_cny.set(0.0)
    reset_contextvars()
    yield
    reset_contextvars()
    _FakeChatLiteLLM.responses.clear()
    llm_client._llm_run_cost_cny.set(0.0)
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
    monkeypatch.setattr(settings, "run_cost_budget", 0)


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
        # 两行遥测但成本只按成功尝试累计一次（失败尝试成本为零且不回传）
        assert llm_client.get_llm_run_cost() == pytest.approx(
            estimate_cost_from_tokens(10, 5, "fake-model")
        )


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
        # 取消的尝试不产生成本：累计器保持 0.0
        assert llm_client.get_llm_run_cost() == 0.0


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


# --------------------------------------------------------------------------- #
# 阶段 B：run 级成本累计器（独立于 telemetry 落库成败）
# --------------------------------------------------------------------------- #
class TestRunCostAccumulator:
    async def test_successful_call_accumulates_cost(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """成功调用计算出成本后立即累加进 _llm_run_cost_cny."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(
                usage_metadata={"input_tokens": 100, "output_tokens": 50},
                response_metadata={"response_cost": 0.005},
            )
        )

        result = await llm_client.call_llm("prompt")

        assert result == "fake-text"
        assert llm_client.get_llm_run_cost() == pytest.approx(0.005)

    async def test_record_failure_still_accumulates_cost(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """repo.record 抛异常被吞时 call_llm 正常返回，且累计器已增加（任务书关键语义）."""
        _install_fake_litellm(monkeypatch)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(response_metadata={"response_cost": 0.007})
        )

        async def _explode(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("db down")

        monkeypatch.setattr(LlmCallUsageRepository, "record", _explode)

        result = await llm_client.call_llm("prompt")

        assert result == "fake-text"
        assert await _fetch_rows(test_db) == []
        assert llm_client.get_llm_run_cost() == pytest.approx(0.007)


# --------------------------------------------------------------------------- #
# 阶段 B：成本预算双检查熔断
# --------------------------------------------------------------------------- #
class TestRunCostBudgetPreCheck:
    async def test_accumulated_cost_blocks_next_call(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """累计成本已达预算 → 下一次 call_llm 前置熔断（耗尽），且不产生新调用."""
        _install_fake_litellm(monkeypatch)
        monkeypatch.setattr(settings, "run_cost_budget", 0.01)
        _FakeChatLiteLLM.responses.extend(
            [
                _FakeResponse(response_metadata={"response_cost": 0.02}),
                _FakeResponse(response_metadata={"response_cost": 0.02}),
            ]
        )

        # 首次调用：前置 0 < 0.01 通过，单次成本打穿预算 → 后置熔断（详见 PostCheck）
        with pytest.raises(LLMBudgetExceededError, match="超限"):
            await llm_client.call_llm("prompt-1")

        # 第二次调用：前置检查 0.02 >= 0.01 → 直接熔断，不再发起 LLM 调用
        with pytest.raises(LLMBudgetExceededError) as exc_info:
            await llm_client.call_llm("prompt-2")

        exc = exc_info.value
        assert "耗尽" in str(exc)
        assert exc.used_cost == pytest.approx(0.02)
        assert exc.budget_cost == pytest.approx(0.01)
        assert exc.used_calls == 0  # llm_run_call_budget 未启用，计数保持 0
        assert exc.budget == 0
        # 未产生新调用：第二次响应未被消费，遥测行仍只有首次的 1 行
        assert len(_FakeChatLiteLLM.responses) == 1
        rows = await _fetch_rows(test_db)
        assert len(rows) == 1
        assert rows[0]["cost_cny"] == pytest.approx(0.02)


class TestRunCostBudgetPostCheck:
    async def test_single_expensive_call_trips_post_check(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """单次调用成本把预算打穿 → 累加后立即熔断，不向调用方返回文本."""
        _install_fake_litellm(monkeypatch)
        monkeypatch.setattr(settings, "run_cost_budget", 0.01)
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(response_metadata={"response_cost": 0.02})
        )

        with pytest.raises(LLMBudgetExceededError) as exc_info:
            await llm_client.call_llm("prompt")

        exc = exc_info.value
        assert "超限" in str(exc)
        assert exc.used_cost == pytest.approx(0.02)
        assert exc.budget_cost == pytest.approx(0.01)
        # 累计器已含本次成本；打穿预算的调用仍留遥测行（resume 合计与累计器一致）
        assert llm_client.get_llm_run_cost() == pytest.approx(0.02)
        rows = await _fetch_rows(test_db)
        assert len(rows) == 1
        assert rows[0]["success"] == 1
        assert rows[0]["cost_cny"] == pytest.approx(0.02)

    async def test_budget_zero_disables_cost_breaker(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """run_cost_budget=0（默认）→ 成本熔断不启用，累计器仍正常累加."""
        _install_fake_litellm(monkeypatch)
        monkeypatch.setattr(settings, "run_cost_budget", 0.0)
        _FakeChatLiteLLM.responses.extend(
            [_FakeResponse(response_metadata={"response_cost": 9.9}) for _ in range(3)]
        )

        for _ in range(3):
            assert await llm_client.call_llm("prompt") == "fake-text"

        assert llm_client.get_llm_run_cost() == pytest.approx(29.7)


# --------------------------------------------------------------------------- #
# 阶段 B：init_run_cost_from_db（resume 安全）
# --------------------------------------------------------------------------- #
class TestInitRunCostFromDb:
    async def test_new_run_initializes_to_zero(self, test_db: Path) -> None:
        """新 run 无用量行 → 累计器初始化为 0.0."""
        total = await llm_client.init_run_cost_from_db("run-new")

        assert total == 0.0
        assert llm_client.get_llm_run_cost() == 0.0

    async def test_resume_run_initializes_from_history(self, test_db: Path) -> None:
        """resume run → 累计器从 llm_call_usage 历史合计继续."""
        repo = LlmCallUsageRepository()
        for cost in (0.01, 0.02, 0.03):
            await repo.record(
                run_id="run-hist",
                model="fake-model",
                cost_cny=cost,
                token_source="estimate",
                cost_source="pricing_estimate",
            )

        total = await llm_client.init_run_cost_from_db("run-hist")

        assert total == pytest.approx(0.06)
        assert llm_client.get_llm_run_cost() == pytest.approx(0.06)

    async def test_preflight_uses_history_plus_new_cost(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """resume 初始化后，前置检查按「历史 + 新增」判定."""
        repo = LlmCallUsageRepository()
        await repo.record(
            run_id="run-hist",
            model="fake-model",
            cost_cny=0.03,
            token_source="estimate",
            cost_source="pricing_estimate",
        )
        await llm_client.init_run_cost_from_db("run-hist")
        _install_fake_litellm(monkeypatch)
        monkeypatch.setattr(settings, "run_cost_budget", 0.04)

        # 历史 0.03 < 0.04 → 前置通过；累计 0.035 ≤ 0.04 → 后置通过，正常返回
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(response_metadata={"response_cost": 0.005})
        )
        assert await llm_client.call_llm("prompt-1") == "fake-text"
        assert llm_client.get_llm_run_cost() == pytest.approx(0.035)

        # 0.035 < 0.04 前置仍通过；累计 0.041 > 0.04 → 后置熔断
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(response_metadata={"response_cost": 0.006})
        )
        with pytest.raises(LLMBudgetExceededError, match="超限"):
            await llm_client.call_llm("prompt-2")
        assert llm_client.get_llm_run_cost() == pytest.approx(0.041)

    async def test_init_failure_degrades_to_zero_with_warning(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """DB 读取失败 → warning + 回退 0.0（生成不可断；退化为仅统计当前进程新增成本）."""

        async def _explode(*args: Any, **kwargs: Any) -> float:
            raise RuntimeError("db down")

        monkeypatch.setattr(LlmCallUsageRepository, "sum_cost_for_run", _explode)
        llm_client._llm_run_cost_cny.set(0.5)  # 预置脏值，验证 init 覆盖语义

        with capture_logs() as logs:
            total = await llm_client.init_run_cost_from_db("run-x")

        assert total == 0.0
        assert llm_client.get_llm_run_cost() == 0.0
        assert any(
            entry.get("event") == "llm.run_cost_init_failed" for entry in logs
        )


# --------------------------------------------------------------------------- #
# 阶段 B：LLMBudgetExceededError 向后兼容 + 配置映射
# --------------------------------------------------------------------------- #
class TestBudgetExceededErrorCompat:
    def test_legacy_four_arg_construction(self) -> None:
        """旧式四参构造仍工作，新成本字段默认 None."""
        exc = LLMBudgetExceededError(
            "budget exceeded", used_calls=3, budget=2, last_chapter=5
        )

        assert exc.used_calls == 3
        assert exc.budget == 2
        assert exc.last_chapter == 5
        assert exc.used_cost is None
        assert exc.budget_cost is None

    def test_cost_fields_populated(self) -> None:
        """新式构造携带 used_cost / budget_cost."""
        exc = LLMBudgetExceededError(
            "cost budget exceeded",
            used_calls=3,
            budget=0,
            last_chapter=5,
            used_cost=1.2345,
            budget_cost=1.0,
        )

        assert exc.used_cost == pytest.approx(1.2345)
        assert exc.budget_cost == pytest.approx(1.0)


class TestRunCostBudgetConfig:
    def test_songyan_env_alias(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SONGYAN_RUN_COST_BUDGET 环境变量映射到 settings.run_cost_budget."""
        monkeypatch.setenv("SONGYAN_RUN_COST_BUDGET", "12.5")

        assert Settings().run_cost_budget == pytest.approx(12.5)

    def test_plain_env_alias(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RUN_COST_BUDGET 备选别名同样生效."""
        monkeypatch.delenv("SONGYAN_RUN_COST_BUDGET", raising=False)
        monkeypatch.setenv("RUN_COST_BUDGET", "3.5")

        assert Settings().run_cost_budget == pytest.approx(3.5)

    def test_default_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """未配置时默认 0.0（不启用成本熔断）."""
        monkeypatch.delenv("SONGYAN_RUN_COST_BUDGET", raising=False)
        monkeypatch.delenv("RUN_COST_BUDGET", raising=False)

        assert Settings().run_cost_budget == 0.0


# --------------------------------------------------------------------------- #
# 阶段 B：total_cost 接线与 pause 路径（phase2_graph 集成）
# --------------------------------------------------------------------------- #
_PID = "proj-175"


def _chapter_success(chapter_number: int) -> dict[str, Any]:
    """仿 test_153/test_154 的 _run_single_chapter 成功返回."""
    return {
        "success": True,
        "summary_text": f"summary-{chapter_number}",
        "error": None,
        "final_state": {},
        "final_version_id": f"v-{chapter_number}",
        "budget_used": 0.8,
        "context_emergency": False,
        "quality_gate_passed": True,
        "settlement_success": True,
        "summary_success": True,
    }


async def _record_chapter_cost(run_id: str, chapter_number: int, cost: float) -> None:
    """_run_single_chapter 被 mock 时不走 call_llm；直写遥测行模拟该章 LLM 成本."""
    await LlmCallUsageRepository().record(
        run_id=run_id,
        project_id=_PID,
        chapter_number=chapter_number,
        agent="writer",
        model="fake-model",
        prompt_tokens=10,
        completion_tokens=5,
        cost_cny=cost,
        token_source="response",
        cost_source="provider_cost",
    )


class TestTotalCostWiring:
    async def test_result_and_persisted_total_cost_equal_db_sum(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """ProjectRunResult.total_cost 与 project_runs.total_cost 均等于 llm_call_usage 合计."""
        await ProjectRepository().create(
            ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), _PID
        )

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            await _record_chapter_cost(kwargs["run_id"], kwargs["chapter_number"], 0.01)
            return _chapter_success(kwargs["chapter_number"])

        with (
            patch(
                "songyan.workflows.phase2_graph._run_single_chapter",
                side_effect=_fake_run,
            ),
            patch(
                "songyan.workflows.phase2_graph.reset_checkpointer",
                new_callable=AsyncMock,
            ),
        ):
            result = await run_project_pipeline(
                project_id=_PID,
                chapter_range=(1, 3),
                auto_confirm=True,
            )

        assert result.final_status == "completed"
        assert result.chapters_completed == [1, 2, 3]
        assert result.total_cost == pytest.approx(0.03)
        persisted = await ProjectRunRepository().get(result.run_id)
        assert persisted is not None
        assert persisted.total_cost == pytest.approx(0.03)

    async def test_run_without_usage_rows_keeps_zero_cost(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """无用量行的 run（旧 run 语义）：result 与 project_runs.total_cost 保持 0.0."""
        await ProjectRepository().create(
            ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), _PID
        )

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            return _chapter_success(kwargs["chapter_number"])

        with (
            patch(
                "songyan.workflows.phase2_graph._run_single_chapter",
                side_effect=_fake_run,
            ),
            patch(
                "songyan.workflows.phase2_graph.reset_checkpointer",
                new_callable=AsyncMock,
            ),
        ):
            result = await run_project_pipeline(
                project_id=_PID,
                chapter_range=(1, 2),
                auto_confirm=True,
            )

        assert result.total_cost == 0.0
        persisted = await ProjectRunRepository().get(result.run_id)
        assert persisted is not None
        assert persisted.total_cost == 0.0


class TestBudgetPauseCostWiring:
    async def test_budget_pause_persists_total_cost_and_log_fields(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """LLMBudgetExceededError pause 路径：total_cost 刷新落盘，日志含成本字段."""
        await ProjectRepository().create(
            ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), _PID
        )

        async def _fake_run(**kwargs: Any) -> dict[str, Any]:
            if kwargs["chapter_number"] == 1:
                await _record_chapter_cost(kwargs["run_id"], 1, 0.01)
                return _chapter_success(1)
            raise LLMBudgetExceededError(
                "单 run 成本预算超限（¥0.01），已用 ¥0.0105",
                used_calls=5,
                budget=0,
                last_chapter=2,
                used_cost=0.0105,
                budget_cost=0.01,
            )

        with (
            patch(
                "songyan.workflows.phase2_graph._run_single_chapter",
                side_effect=_fake_run,
            ),
            patch(
                "songyan.workflows.phase2_graph.reset_checkpointer",
                new_callable=AsyncMock,
            ),
            capture_logs() as logs,
        ):
            with pytest.raises(LLMBudgetExceededError):
                await run_project_pipeline(
                    project_id=_PID,
                    chapter_range=(1, 3),
                    auto_confirm=True,
                )

        runs = await ProjectRunRepository().list_by_project(_PID)
        assert len(runs) == 1
        assert runs[0].status == "paused"
        assert runs[0].completed_chapters == [1]
        assert runs[0].total_cost == pytest.approx(0.01)

        budget_logs = [
            entry
            for entry in logs
            if entry.get("event") == "project_pipeline.budget_exceeded"
        ]
        assert len(budget_logs) == 1
        entry = budget_logs[0]
        assert entry["used_calls"] == 5
        assert entry["budget"] == 0
        assert entry["last_chapter"] == 2
        assert entry["used_cost"] == pytest.approx(0.0105)
        assert entry["budget_cost"] == pytest.approx(0.01)


# --------------------------------------------------------------------------- #
# 阶段 B review 修复：短路分支 total_cost 透传 + 刷新失败保留既有值
# --------------------------------------------------------------------------- #
class TestResumeShortCircuitTotalCost:
    async def test_resume_already_completed_returns_persisted_total_cost(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """resume_already_completed 短路：result.total_cost 透传已持久化值（不落默认 0.0）."""
        await ProjectRepository().create(
            ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), _PID
        )
        await ProjectRunRepository().create(
            ProjectRunState(
                run_id="run-175-done",
                project_id=_PID,
                chapter_range_start=1,
                chapter_range_end=2,
                current_chapter=2,
                completed_chapters=[1, 2],
                total_cost=0.07,
                status="completed",
            )
        )
        # 请求范围全部 accepted → 命中短路分支
        version_repo = ChapterVersionRepository()
        head_repo = ChapterHeadRepository()
        for ch in (1, 2):
            await version_repo.create(
                ChapterVersion(
                    version_id=f"accepted-{ch}",
                    project_id=_PID,
                    chapter_number=ch,
                    version_number=1,
                    version_type="accepted",
                    content=f"accepted content {ch}",
                    word_count=10,
                )
            )
            await head_repo.update(
                ChapterHead(
                    project_id=_PID,
                    chapter_number=ch,
                    current_version_id=f"accepted-{ch}",
                    accepted_version_id=f"accepted-{ch}",
                    status="accepted",
                )
            )

        result = await run_project_pipeline(
            project_id=_PID,
            chapter_range=(1, 2),
            auto_confirm=True,
            resume=True,
        )

        assert result.run_id == "run-175-done"
        assert result.final_status == "completed"
        assert result.chapters_completed == [1, 2]
        assert result.total_cost == pytest.approx(0.07)


class TestRefreshRunTotalCost:
    async def test_refresh_failure_preserves_existing_value(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """sum 瞬时读失败（如 SQLite lock）→ 保留既有值，不把历史合计冲成 0.0."""

        async def _explode(*args: Any, **kwargs: Any) -> float:
            raise RuntimeError("sqlite locked")

        monkeypatch.setattr(LlmCallUsageRepository, "sum_cost_for_run", _explode)
        run_state = ProjectRunState(
            run_id="run-175-hist",
            project_id=_PID,
            chapter_range_start=1,
            chapter_range_end=2,
            total_cost=0.42,
        )

        await _refresh_run_total_cost(run_state)

        assert run_state.total_cost == pytest.approx(0.42)

    async def test_refresh_success_overwrites_with_db_sum(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """正常路径：run_state.total_cost 刷新为 llm_call_usage 合计."""
        await LlmCallUsageRepository().record(
            run_id="run-175-hist",
            model="fake-model",
            cost_cny=0.03,
            token_source="estimate",
            cost_source="pricing_estimate",
        )
        run_state = ProjectRunState(
            run_id="run-175-hist",
            project_id=_PID,
            chapter_range_start=1,
            chapter_range_end=2,
            total_cost=0.99,
        )

        await _refresh_run_total_cost(run_state)

        assert run_state.total_cost == pytest.approx(0.03)


# --------------------------------------------------------------------------- #
# 阶段 C：report 成本段渲染（纯函数 render_cost_section，数据进 → markdown 出）
# --------------------------------------------------------------------------- #
def _usage_group(
    key: str,
    value: Any,
    *,
    call_count: int,
    cost: float,
    prompt: int = 0,
    completion: int = 0,
) -> dict[str, Any]:
    """构造 aggregate_for_run 的单行分组结果（per_chapter / per_agent 同构）."""
    return {
        key: value,
        "call_count": call_count,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cost_cny": cost,
    }


def _stats(total: int, token_est: int = 0, cost_est: int = 0) -> dict[str, int]:
    """构造 source_stats_for_run 的返回（total_calls 为占比分母）."""
    return {
        "total_calls": total,
        "token_estimate_calls": token_est,
        "cost_pricing_estimate_calls": cost_est,
    }


class TestRenderCostSection:
    """render_cost_section：aggregate + source_stats → markdown 成本段，不碰 DB."""

    def _aggregate(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "per_chapter": [
                _usage_group(
                    "chapter_number", None,
                    call_count=1, cost=0.002, prompt=100, completion=50,
                ),
                _usage_group(
                    "chapter_number", 1,
                    call_count=2, cost=0.010, prompt=200, completion=100,
                ),
                _usage_group(
                    "chapter_number", 2,
                    call_count=1, cost=0.006, prompt=150, completion=80,
                ),
            ],
            "per_agent": [
                _usage_group(
                    "agent", "writer",
                    call_count=2, cost=0.014, prompt=300, completion=150,
                ),
                _usage_group(
                    "agent", "llm_auditor",
                    call_count=2, cost=0.004, prompt=150, completion=80,
                ),
            ],
        }

    def test_renders_all_segments(self) -> None:
        """有数据：run 总额 / 章节数 / 每章均 / per agent / 两个估算占比全部渲染."""
        text = render_cost_section(self._aggregate(), _stats(4, token_est=1, cost_est=2))

        assert "## 成本视图" in text
        # run 总成本 = 0.002 + 0.010 + 0.006 = 0.018（含 run 级分组）
        assert f"**run 总成本**: {format_cost_estimate(0.018)}" in text
        # 章节数只计非 NULL 分组，run 级调用次数以注释呈现
        assert "**章节数**: 2（另有 run 级调用 1 次）" in text
        # 每章均成本 = run 总成本 / 章节数 = 0.009
        assert f"**每章均成本**: {format_cost_estimate(0.009)}" in text
        # 两个估算占比：分子/分母齐全（估算占比高 = usage/成本提取要修的早期信号）
        assert "25.0% (1/4)" in text
        assert "50.0% (2/4)" in text
        # per agent 成本分布表
        assert "| writer | 2 | 300 | 150 |" in text
        assert "| llm_auditor | 2 | 150 | 80 |" in text

    def test_no_data_renders_hint_without_tables(self) -> None:
        """无 usage 数据的旧 run：输出「无成本数据」提示，不渲染表格，不报错."""
        text = render_cost_section({"per_chapter": [], "per_agent": []}, _stats(0))

        assert "## 成本视图" in text
        assert "无成本数据" in text
        assert "|" not in text

    def test_null_chapter_group_rendered_as_run_level(self) -> None:
        """chapter_number=None 分组（run 级调用）渲染为「run 级」，不出现 None 字样."""
        text = render_cost_section(self._aggregate(), _stats(4))

        assert "| run 级 | 1 | 100 | 50 |" in text
        assert "| Ch1 | 2 | 200 | 100 |" in text
        assert "None" not in text

    def test_per_agent_top_n_merges_rest(self) -> None:
        """>top_n 个 agent：按成本降序取 Top N，其余合并为一行「其他（k 个 agent）」."""
        per_agent = [
            _usage_group(
                "agent", f"agent-{i}",
                call_count=1, cost=0.001 * i, prompt=10 * i, completion=5 * i,
            )
            for i in range(1, 8)  # 7 个 agent，成本 0.001..0.007
        ]
        aggregate = {
            "per_chapter": [_usage_group("chapter_number", 1, call_count=7, cost=0.028)],
            "per_agent": per_agent,
        }

        text = render_cost_section(aggregate, _stats(7), top_n=3)

        assert "（Top 3）" in text
        # 成本降序前三：agent-7 / agent-6 / agent-5
        assert "| agent-7 |" in text
        assert "| agent-6 |" in text
        assert "| agent-5 |" in text
        assert "| agent-4 |" not in text
        # 其余 4 个合并：call_count=4、prompt=100、completion=50、cost=0.010
        assert f"| 其他（4 个 agent） | 4 | 100 | 50 | {format_cost_estimate(0.010)} |" in text

    def test_per_agent_within_top_n_has_no_others_row(self) -> None:
        """agent 数 ≤ top_n 时不出现「其他」合并行，标题也不带「Top N」后缀."""
        text = render_cost_section(self._aggregate(), _stats(4))
        assert "其他" not in text
        assert "（Top" not in text

    def test_error_param_renders_distinct_failure_line(self) -> None:
        """error 参数（取数失败降级）：渲染可区分的错误行，不伪装成「无成本数据」."""
        text = render_cost_section(
            {"per_chapter": [], "per_agent": []},
            _stats(0),
            error="no such table: llm_call_usage",
        )

        assert "## 成本视图" in text
        assert "成本数据读取失败：no such table: llm_call_usage" in text
        assert "无成本数据" not in text
        assert "|" not in text

    def test_run_level_only_renders_dash_avg_cost(self) -> None:
        """全部调用都是 run 级（chapter_count=0）：章节数 0，每章均成本渲染为 -."""
        aggregate = {
            "per_chapter": [
                _usage_group(
                    "chapter_number", None,
                    call_count=2, cost=0.004, prompt=100, completion=50,
                ),
            ],
            "per_agent": [
                _usage_group("agent", "summary_writer", call_count=2, cost=0.004),
            ],
        }

        text = render_cost_section(aggregate, _stats(2))

        assert f"**run 总成本**: {format_cost_estimate(0.004)}" in text
        assert "**章节数**: 0（另有 run 级调用 2 次）" in text
        assert "**每章均成本**: -" in text


class TestRenderCostSectionFetchFallback:
    """_render_cost_section（cli.main）：取数失败的降级形状（不触碰 tests/cli）."""

    def test_fetch_failure_renders_distinct_error_line(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SQL 错/schema 漂移/DB 锁死 → 报告中是可区分错误行 + console 警告，不伪装成旧 run."""

        async def _explode(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("no such table: llm_call_usage")

        monkeypatch.setattr(LlmCallUsageRepository, "aggregate_for_run", _explode)

        text = _render_cost_section("run-x")

        assert "## 成本视图" in text
        assert "成本数据读取失败" in text
        assert "no such table" in text
        assert "无成本数据" not in text
        # console 警告保留（report_cmd 既有警告均为 click.echo 风格）
        assert "成本数据读取失败" in capsys.readouterr().out
