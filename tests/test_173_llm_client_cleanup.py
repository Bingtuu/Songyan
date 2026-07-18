from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import types
from importlib.machinery import ModuleSpec
from pathlib import Path

import pytest

from songyan.config import Settings, settings
from songyan.llm import client as llm_client
from songyan.utils.process_exit import force_exit_after_run_if_requested


class _FakeAsyncResource:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class _FakeChatLiteLLM:
    instances: list[_FakeChatLiteLLM] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.async_client = _FakeAsyncResource()
        self.closed = False
        self.instances.append(self)

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
async def _clear_llm_cache() -> None:
    await llm_client.aclose_llm_clients()
    _FakeChatLiteLLM.instances.clear()
    yield
    await llm_client.aclose_llm_clients()
    _FakeChatLiteLLM.instances.clear()


def _install_fake_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.ModuleType("langchain_litellm")
    fake_module.__spec__ = ModuleSpec("langchain_litellm", loader=None)
    fake_module.ChatLiteLLM = _FakeChatLiteLLM  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_litellm", fake_module)
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.test")
    monkeypatch.setattr(settings, "llm_model", "fake-model")


@pytest.mark.asyncio
async def test_aclose_llm_clients_closes_registered_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_litellm(monkeypatch)

    llm_client.get_llm(temperature=0.2, max_tokens=128, timeout=5)
    assert len(_FakeChatLiteLLM.instances) == 1
    fake_client = _FakeChatLiteLLM.instances[0]

    await llm_client.aclose_llm_clients()

    assert fake_client.async_client.closed is True
    assert fake_client.closed is True
    assert llm_client._get_llm_cached.cache_info().currsize == 0


@pytest.mark.asyncio
async def test_aclose_llm_clients_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_litellm(monkeypatch)

    llm_client.get_llm()
    await llm_client.aclose_llm_clients()
    await llm_client.aclose_llm_clients()

    assert llm_client._get_llm_cached.cache_info().currsize == 0


@pytest.mark.asyncio
async def test_aclose_llm_clients_with_no_clients_is_noop() -> None:
    await llm_client.aclose_llm_clients()

    assert llm_client._get_llm_cached.cache_info().currsize == 0


class _FakeBadCloseResource:
    async def aclose(self) -> None:
        raise KeyError("unexpected-close-error")


@pytest.mark.asyncio
async def test_aclose_llm_clients_swallows_unexpected_close_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """关闭抛出未预期异常类型时不得传播（清理路径不屏蔽 pipeline 原异常）."""
    _install_fake_litellm(monkeypatch)
    llm_client.get_llm(temperature=0.3, max_tokens=64, timeout=5)
    fake_client = _FakeChatLiteLLM.instances[0]
    fake_client.async_client = _FakeBadCloseResource()

    await llm_client.aclose_llm_clients()  # KeyError 不得传播

    assert fake_client.closed is True  # client 自身关闭仍执行
    assert llm_client._get_llm_cached.cache_info().currsize == 0


def test_songyan_force_exit_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SONGYAN_FORCE_EXIT", "1")

    assert Settings().force_exit_after_run is True


def test_force_exit_helper_flushes_before_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int | None]] = []

    def fake_flush(*, close: bool = False) -> None:
        calls.append(("flush", int(close)))

    def fake_exit(code: int) -> None:
        calls.append(("exit", code))

    monkeypatch.setattr("songyan.utils.process_exit.flush_logging_handlers", fake_flush)

    invoked = force_exit_after_run_if_requested(
        enabled=True,
        exit_code=7,
        exit_func=fake_exit,
    )

    assert invoked is True
    assert calls == [("flush", 1), ("exit", 7)]


def test_force_exit_helper_disabled_does_not_exit() -> None:
    called = False

    def fake_exit(code: int) -> None:
        nonlocal called
        called = True

    invoked = force_exit_after_run_if_requested(enabled=False, exit_func=fake_exit)

    assert invoked is False
    assert called is False


def test_force_exit_subprocess_terminates_non_daemon_thread(tmp_path: Path) -> None:
    marker = tmp_path / "result.txt"
    code = textwrap.dedent(
        """
        from __future__ import annotations

        import sys
        import threading
        import time
        from pathlib import Path

        from songyan.utils.process_exit import force_exit_after_run_if_requested

        marker = Path(sys.argv[1])
        marker.write_text("done", encoding="utf-8")
        thread = threading.Thread(target=time.sleep, args=(60,), daemon=False)
        thread.start()
        force_exit_after_run_if_requested(enabled=True, exit_code=0)
        """
    )
    env = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    completed = subprocess.run(
        [sys.executable, "-c", code, str(marker)],
        env=env,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0
    assert marker.read_text(encoding="utf-8") == "done"
