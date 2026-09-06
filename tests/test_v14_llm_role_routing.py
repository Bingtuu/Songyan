"""Tests for V14 Task 231 — per-role LLM 配置路由（LLM_<ROLE>_* 覆盖）."""

from __future__ import annotations

import sys
import types
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any
from unittest.mock import patch

import aiosqlite
import pytest
from structlog.contextvars import bind_contextvars, reset_contextvars
from structlog.testing import capture_logs

from songyan.config import RoleLlmOverride, Settings, collect_llm_role_overrides, settings
from songyan.llm import client as llm_client
from songyan.llm.client import resolve_llm_config
from songyan.services.doctor_service import _check_llm_config


# --------------------------------------------------------------------------- #
# Settings 收集层（collect_llm_role_overrides / Settings model_validator）
# --------------------------------------------------------------------------- #
class TestCollectLlmRoleOverrides:
    def test_collect_from_env(self) -> None:
        overrides = collect_llm_role_overrides({"LLM_WRITER_MODEL": "writer-m"}, {})
        assert overrides["writer"].model == "writer-m"
        assert overrides["writer"].base_url is None
        assert overrides["writer"].api_key is None

    def test_role_name_normalized_lowercase(self) -> None:
        overrides = collect_llm_role_overrides({"LLM_LLM_AUDITOR_MODEL": "m"}, {})
        assert "llm_auditor" in overrides

    def test_env_priority_over_dotenv(self) -> None:
        overrides = collect_llm_role_overrides(
            {"LLM_WRITER_MODEL": "from-env"},
            {"LLM_WRITER_MODEL": "from-dotenv"},
        )
        assert overrides["writer"].model == "from-env"

    def test_dotenv_only(self) -> None:
        overrides = collect_llm_role_overrides(
            {}, {"LLM_WRITER_BASE_URL": "https://role.example"}
        )
        assert overrides["writer"].base_url == "https://role.example"

    def test_empty_value_skipped(self) -> None:
        overrides = collect_llm_role_overrides({"LLM_WRITER_MODEL": ""}, {})
        assert overrides == {}

    def test_unknown_role_collected_without_validation(self) -> None:
        # 加载期不校验合法性（避免 config ↔ llm 循环 import）；未知角色在
        # resolve_llm_config / doctor 侧告警
        overrides = collect_llm_role_overrides({"LLM_NOPE_MODEL": "m"}, {})
        assert "nope" in overrides

    def test_settings_collects_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(Settings.model_config, "env_file", None)
        monkeypatch.setenv("LLM_WRITER_MODEL", "writer-m")
        s = Settings()
        assert s.llm_role_overrides["writer"].model == "writer-m"

    def test_settings_collects_from_dotenv(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("LLM_WRITER_MODEL=dotenv-model\n", encoding="utf-8")
        monkeypatch.setitem(Settings.model_config, "env_file", str(env_file))
        monkeypatch.delenv("LLM_WRITER_MODEL", raising=False)
        s = Settings()
        assert s.llm_role_overrides["writer"].model == "dotenv-model"


# --------------------------------------------------------------------------- #
# 解析层（resolve_llm_config 两级回退）
# --------------------------------------------------------------------------- #
@pytest.fixture
def _global_llm_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_api_key", "global-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://global.example")
    monkeypatch.setattr(settings, "llm_model", "global-model")
    monkeypatch.setattr(settings, "llm_role_overrides", {})


class TestResolveLlmConfig:
    def test_no_override_regression(self, _global_llm_settings: None) -> None:
        """无覆盖时解析结果 == 既有全局行为（验收矩阵 A）."""
        r = resolve_llm_config()
        assert r.role is None
        assert r.model == "global-model"
        assert r.model_source == "global"
        assert r.api_key == "global-key"
        assert r.base_url == "https://global.example"

    def test_builtin_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "llm_api_key", "")
        monkeypatch.setattr(settings, "llm_base_url", "")
        monkeypatch.setattr(settings, "llm_model", "")
        monkeypatch.setattr(settings, "llm_role_overrides", {})
        r = resolve_llm_config()
        assert r.model == "deepseek-chat"
        assert r.model_source == "default"
        assert r.base_url == "https://api.deepseek.com"

    def test_role_model_only_falls_back_per_field(
        self, _global_llm_settings: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            settings,
            "llm_role_overrides",
            {"writer": RoleLlmOverride(model="writer-m")},
        )
        r = resolve_llm_config("writer")
        assert r.role == "writer"
        assert r.model == "writer-m"
        assert r.model_source == "role"
        assert r.api_key == "global-key"
        assert r.base_url == "https://global.example"

    def test_role_full_override(
        self, _global_llm_settings: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            settings,
            "llm_role_overrides",
            {
                "writer": RoleLlmOverride(
                    model="writer-m",
                    base_url="https://role.example",
                    api_key="role-key",
                )
            },
        )
        r = resolve_llm_config("writer")
        assert r.model == "writer-m"
        assert r.api_key == "role-key"
        assert r.base_url == "https://role.example"

    def test_unknown_role_falls_back_with_warning(
        self, _global_llm_settings: None
    ) -> None:
        with capture_logs() as logs:
            r = resolve_llm_config("not_a_role")
        assert r.role is None
        assert r.model == "global-model"
        assert any(log["event"] == "llm.unknown_role_fallback" for log in logs)


# --------------------------------------------------------------------------- #
# get_llm 构造参数路由
# --------------------------------------------------------------------------- #
class TestGetLlmRoleRouting:
    def test_get_llm_uses_role_model(
        self, _global_llm_settings: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            settings,
            "llm_role_overrides",
            {"writer": RoleLlmOverride(model="writer-m")},
        )
        with patch("songyan.llm.client._get_llm_cached") as mock_cached:
            llm_client.get_llm(role="writer")
        kwargs = mock_cached.call_args.kwargs
        assert kwargs["model"] == "writer-m"
        assert kwargs["api_key"] == "global-key"
        assert kwargs["base_url"] == "https://global.example"

    def test_get_llm_without_role_uses_global(
        self, _global_llm_settings: None
    ) -> None:
        with patch("songyan.llm.client._get_llm_cached") as mock_cached:
            llm_client.get_llm()
        assert mock_cached.call_args.kwargs["model"] == "global-model"


# --------------------------------------------------------------------------- #
# call_llm 端到端路由 + llm_call_usage.model 落库（验收矩阵 B）
# --------------------------------------------------------------------------- #
class _FakeResponse:
    """模拟 langchain AIMessage：仅按测试需要暴露相应属性."""

    def __init__(
        self,
        content: str = "fake-text",
        usage_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.content = content
        if usage_metadata is not None:
            self.usage_metadata = usage_metadata


class _FakeChatLiteLLM:
    """ainvoke 按队列吐出 response（仿 test_175 注入模式）."""

    responses: list[Any] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    async def ainvoke(self, messages: list[Any]) -> Any:
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


# 模块导入时捕获真实 helper（conftest 的 mute 发生在每个测试运行时，此刻未 patch）
_REAL_RECORD_USAGE = llm_client._record_llm_call_usage


@pytest.fixture(autouse=True)
def _restore_llm_call_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """豁免 tests/conftest.py 的遥测 mute：本模块验证真实落库路径."""
    monkeypatch.setattr(llm_client, "_record_llm_call_usage", _REAL_RECORD_USAGE)


@pytest.fixture(autouse=True)
async def _clean_state() -> Any:
    await llm_client.aclose_llm_clients()
    _FakeChatLiteLLM.responses.clear()
    reset_contextvars()
    yield
    reset_contextvars()
    _FakeChatLiteLLM.responses.clear()
    await llm_client.aclose_llm_clients()


def _install_fake_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.ModuleType("langchain_litellm")
    fake_module.__spec__ = ModuleSpec("langchain_litellm", loader=None)
    fake_module.ChatLiteLLM = _FakeChatLiteLLM  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_litellm", fake_module)
    monkeypatch.setattr(settings, "llm_api_key", "global-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://global.example")
    monkeypatch.setattr(settings, "llm_model", "global-model")
    monkeypatch.setattr(settings, "llm_run_call_budget", 0)
    monkeypatch.setattr(settings, "run_cost_budget", 0)


async def _fetch_rows(db_file: Path) -> list[dict[str, Any]]:
    async with aiosqlite.connect(str(db_file)) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT * FROM llm_call_usage ORDER BY id")
        return [dict(row) for row in await cursor.fetchall()]


class TestCallLlmRoleRouting:
    async def test_agent_attribution_routes_to_role_model(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """bind_contextvars(agent='writer') 后 call_llm 自动按角色解析，

        遥测落库 model 为角色模型（验收矩阵 B 验证路径）。
        """
        _install_fake_litellm(monkeypatch)
        monkeypatch.setattr(
            settings,
            "llm_role_overrides",
            {"writer": RoleLlmOverride(model="writer-role-model")},
        )
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(usage_metadata={"input_tokens": 1, "output_tokens": 1})
        )
        bind_contextvars(agent="writer")

        result = await llm_client.call_llm("prompt")

        assert result == "fake-text"
        rows = await _fetch_rows(test_db)
        assert rows[0]["agent"] == "writer"
        assert rows[0]["model"] == "writer-role-model"

    async def test_unbound_context_uses_global_model(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """无归因上下文时保持全局模型（验收矩阵 A）."""
        _install_fake_litellm(monkeypatch)
        monkeypatch.setattr(
            settings,
            "llm_role_overrides",
            {"writer": RoleLlmOverride(model="writer-role-model")},
        )
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(usage_metadata={"input_tokens": 1, "output_tokens": 1})
        )

        await llm_client.call_llm("prompt")

        rows = await _fetch_rows(test_db)
        assert rows[0]["agent"] == "unknown"
        assert rows[0]["model"] == "global-model"

    async def test_explicit_role_beats_context(
        self, monkeypatch: pytest.MonkeyPatch, test_db: Path
    ) -> None:
        """显式 role 参数优先于 contextvars 归因."""
        _install_fake_litellm(monkeypatch)
        monkeypatch.setattr(
            settings,
            "llm_role_overrides",
            {"writer": RoleLlmOverride(model="writer-role-model")},
        )
        _FakeChatLiteLLM.responses.append(
            _FakeResponse(usage_metadata={"input_tokens": 1, "output_tokens": 1})
        )
        bind_contextvars(agent="llm_auditor")

        await llm_client.call_llm("prompt", role="writer")

        rows = await _fetch_rows(test_db)
        assert rows[0]["model"] == "writer-role-model"


# --------------------------------------------------------------------------- #
# doctor 逐角色校验（验收矩阵 C）
# --------------------------------------------------------------------------- #
def _doctor_config(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    """构造与加载期环境隔离的 Settings，仅含给定 LLM_* 环境变量."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(
        llm_api_key="test-key",
        llm_base_url="https://global.example",
        llm_model="global-model",
    )


class TestDoctorRoleChecks:
    def test_legal_role_override_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        config = _doctor_config(monkeypatch, LLM_WRITER_MODEL="writer-m")
        checks = {c.id: c for c in _check_llm_config(config)}
        assert checks["llm.role.writer"].status == "pass"

    def test_invalid_base_url_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        config = _doctor_config(monkeypatch, LLM_WRITER_BASE_URL="ftp://bad")
        checks = {c.id: c for c in _check_llm_config(config)}
        assert checks["llm.role.writer"].status == "fail"

    def test_unknown_role_warns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        config = _doctor_config(monkeypatch, LLM_NOPE_MODEL="m")
        checks = {c.id: c for c in _check_llm_config(config)}
        assert checks["llm.role.nope"].status == "warn"

    def test_role_base_url_without_any_key_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(Settings.model_config, "env_file", None)
        for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("LLM_WRITER_BASE_URL", "https://role.example")
        config = Settings(
            llm_api_key="",
            llm_base_url="https://global.example",
            llm_model="global-model",
        )
        checks = {c.id: c for c in _check_llm_config(config)}
        assert checks["llm.role.writer"].status == "fail"
