# src/songyan/literary_optimization/registry.py
from __future__ import annotations

from typing import TYPE_CHECKING

from .strategies.ai_tone_blocklist import AiToneBlocklistStrategy
from .strategies.few_shot_voice_anchor import FewShotVoiceAnchorStrategy
from .strategies.minimal_voice_anchor import MinimalVoiceAnchorStrategy
from .strategies.opposing_goal_anchor import OpposingGoalAnchorStrategy

if TYPE_CHECKING:
    from .base import LiteraryOptimizationStrategy

_REGISTRY: dict[str, type[LiteraryOptimizationStrategy]] = {
    AiToneBlocklistStrategy().strategy_id: AiToneBlocklistStrategy,
    FewShotVoiceAnchorStrategy().strategy_id: FewShotVoiceAnchorStrategy,
    MinimalVoiceAnchorStrategy().strategy_id: MinimalVoiceAnchorStrategy,
    OpposingGoalAnchorStrategy().strategy_id: OpposingGoalAnchorStrategy,
}


def list_strategies() -> list[str]:
    return list(_REGISTRY.keys())


def load_strategy(strategy_id: str) -> LiteraryOptimizationStrategy:
    cls = _REGISTRY.get(strategy_id)
    if cls is None:
        raise ValueError(f"Unknown literary optimization strategy: {strategy_id}")
    return cls()
