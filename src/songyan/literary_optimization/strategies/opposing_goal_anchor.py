# src/songyan/literary_optimization/strategies/opposing_goal_anchor.py
from __future__ import annotations

from songyan.literary_optimization.base import (
    LiteraryContext,
    LiteraryOptimizationResult,
    LiteraryOptimizationStrategy,
)


class OpposingGoalAnchorStrategy(LiteraryOptimizationStrategy):
    """对抗性目标锚定：为每个核心人类角色输出目标/恐惧/冲突，驱动对白从冲突中生长."""

    @property
    def strategy_id(self) -> str:
        return "opposing_goal_anchor"

    @property
    def applicable_agents(self) -> list[str]:
        return ["creative_director", "writer"]

    def apply(self, context: LiteraryContext) -> LiteraryOptimizationResult:
        return LiteraryOptimizationResult(
            prompt_fragments={
                "creative_director": ["插件要求见 opposing_goal_anchor/creative_director.yaml"],
                "writer": ["插件要求见 opposing_goal_anchor/writer.yaml"],
            }
        )
