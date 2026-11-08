"""B5: a hung LLM HTTP call must be cut by the per-call timeout.

ChatLiteLLM's constructor field is ``request_timeout``. Passing ``timeout=`` is
dropped (Pydantic extra=ignore), so litellm falls back to a 600s HTTP timeout
and ``asyncio.wait_for`` does not close that socket. This test holds a local
connection open with no response and no live LLM key.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from songyan.config import settings
from songyan.exceptions import LLMError
from songyan.llm.client import aclose_llm_clients, call_llm

# Longer than the assertion bound: an unwired timeout waits the server out.
# Hold 必须 > 断言窗口，窗口内被切断 = 超时机制生效；两者余量拉大
# （2026-11-08，task 235）：全量套件重载下 litellm 的 1s 单次超时会被
# 推迟，原 8s 窗口余量不足偶发 flake；窗口内仍是「真坏必失败」的判别结构。
_SERVER_HOLD_SECONDS = 30.0
_ASSERT_BOUND_SECONDS = 20.0


class _SilentHangHandler(BaseHTTPRequestHandler):
    """Accept the POST body and keep the socket open without a response."""

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length:
            self.rfile.read(length)
        self.connection.settimeout(_SERVER_HOLD_SECONDS)
        try:
            while self.rfile.read(1):
                pass
        except OSError:
            return

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def hung_llm_server() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _SilentHangHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.mark.asyncio
async def test_hung_http_call_is_cut_by_per_call_timeout(
    hung_llm_server: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A socket that accepts and never replies raises LLMError within a few seconds."""
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_base_url", hung_llm_server)
    monkeypatch.setattr(settings, "llm_model", "deepseek/deepseek-chat")
    monkeypatch.setattr(settings, "llm_run_call_budget", 0)
    monkeypatch.setattr(settings, "run_cost_budget", 0)
    await aclose_llm_clients()

    started = time.monotonic()
    with pytest.raises(LLMError, match=r"超时"):
        await call_llm("ping", timeout=1, max_retries=1, temperature=0)
    elapsed = time.monotonic() - started

    assert elapsed < _ASSERT_BOUND_SECONDS, f"hung call was not cut in time ({elapsed:.2f}s)"
    await aclose_llm_clients()
