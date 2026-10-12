from __future__ import annotations

import asyncio
import json
from typing import Any

from songyan.llm.client import call_llm
from songyan.llm.parsing import extract_json


async def ask_json(prompt: str, *, max_tokens: int = 3000, hard_timeout: float = 240) -> dict[str, Any]:
    """LLM JSON call with a hard wall-clock timeout (works around observed hangs)."""
    last: Exception | None = None
    for _ in range(2):
        try:
            txt = await asyncio.wait_for(
                call_llm(prompt, temperature=0.1, max_tokens=max_tokens, timeout=120,
                         role="settlement_extractor"),
                timeout=hard_timeout,
            )
            return json.loads(extract_json(txt))
        except (asyncio.TimeoutError, json.JSONDecodeError, ValueError) as exc:
            last = exc
    raise RuntimeError(f"canon LLM call failed: {last}")
