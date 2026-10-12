"""fix #2: per-attempt hard timeout + retry of the single call."""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from songyan.llm import client
from songyan.llm.client import call_llm, effective_attempt_timeout


def test_effective_attempt_timeout_scales_with_output():
    assert effective_attempt_timeout(60, 800) == 60
    assert effective_attempt_timeout(60, 6000) == 300
    assert effective_attempt_timeout(60, 100000) == 600


@pytest.mark.asyncio
async def test_hung_attempt_is_retried_not_whole_call_failed(monkeypatch):
    calls = {"n": 0}

    class Resp:
        content = "ok"
        response_metadata: dict = {}
        usage_metadata = None

    async def ainvoke(_msgs):
        calls["n"] += 1
        if calls["n"] == 1:
            await asyncio.sleep(10)  # hang
        return Resp()

    llm = MagicMock()
    llm.ainvoke = ainvoke
    monkeypatch.setattr(client, "effective_attempt_timeout", lambda t, m: 0.2)
    monkeypatch.setattr(client, "_BACKOFF_BASE", 0.01)
    monkeypatch.setattr(client, "_BACKOFF_MAX", 0.02)
    with patch("songyan.llm.client.get_llm", return_value=llm):
        out = await asyncio.wait_for(call_llm("hi", max_retries=3, timeout=1), timeout=5)
    assert out == "ok" and calls["n"] == 2
