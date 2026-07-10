# src/songyan/literary_optimization/strategies/few_shot_voice_anchor.py
from __future__ import annotations

from songyan.literary_optimization.base import (
    LiteraryContext,
    LiteraryOptimizationResult,
    LiteraryOptimizationStrategy,
)


class FewShotVoiceAnchorStrategy(LiteraryOptimizationStrategy):
    """少样本声纹锚定：为核心人类角色输出 voice_samples，驱动对白风格复刻."""

    @property
    def strategy_id(self) -> str:
        return "few_shot_voice_anchor"

    @property
    def applicable_agents(self) -> list[str]:
        return ["creative_director", "writer"]

    def apply(self, context: LiteraryContext) -> LiteraryOptimizationResult:
        return LiteraryOptimizationResult(
            prompt_fragments={
                "creative_director": ["插件要求见 few_shot_voice_anchor/creative_director.yaml"],
                "writer": ["插件要求见 few_shot_voice_anchor/writer.yaml"],
            }
        )
