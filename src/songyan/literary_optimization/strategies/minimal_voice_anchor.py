# src/songyan/literary_optimization/strategies/minimal_voice_anchor.py
from __future__ import annotations

from songyan.literary_optimization.base import (
    LiteraryContext,
    LiteraryOptimizationResult,
    LiteraryOptimizationStrategy,
)


class MinimalVoiceAnchorStrategy(LiteraryOptimizationStrategy):
    """极简声纹锚定：为出场人类角色输出情绪基调+一句话口头禅/禁忌."""

    @property
    def strategy_id(self) -> str:
        return "minimal_voice_anchor"

    @property
    def applicable_agents(self) -> list[str]:
        return ["creative_director", "writer"]

    def apply(self, context: LiteraryContext) -> LiteraryOptimizationResult:
        return LiteraryOptimizationResult(
            prompt_fragments={
                "creative_director": ["插件要求见 minimal_voice_anchor/creative_director.yaml"],
                "writer": ["插件要求见 minimal_voice_anchor/writer.yaml"],
            }
        )
