# src/songyan/literary_optimization/registry.py
from __future__ import annotations

from typing import TYPE_CHECKING

from .strategies.minimal_voice_anchor import MinimalVoiceAnchorStrategy

if TYPE_CHECKING:
    from .base import LiteraryOptimizationStrategy

_REGISTRY: dict[str, type[LiteraryOptimizationStrategy]] = {
    MinimalVoiceAnchorStrategy().strategy_id: MinimalVoiceAnchorStrategy,
}


def list_strategies() -> list[str]:
    return list(_REGISTRY.keys())


def load_strategy(strategy_id: str) -> LiteraryOptimizationStrategy:
    cls = _REGISTRY.get(strategy_id)
    if cls is None:
        raise ValueError(f"Unknown literary optimization strategy: {strategy_id}")
    return cls()
