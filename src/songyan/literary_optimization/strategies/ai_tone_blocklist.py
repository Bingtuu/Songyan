# src/songyan/literary_optimization/strategies/ai_tone_blocklist.py
from __future__ import annotations

from songyan.literary_optimization.base import (
    LiteraryContext,
    LiteraryOptimizationResult,
    LiteraryOptimizationStrategy,
)


class AiToneBlocklistStrategy(LiteraryOptimizationStrategy):
    """AI 腔禁用表：为 Writer / RevisionHandler 提供禁用模式与替换方向."""

    @property
    def strategy_id(self) -> str:
        return "ai_tone_blocklist"

    @property
    def applicable_agents(self) -> list[str]:
        return ["writer", "revision_handler"]

    def apply(self, context: LiteraryContext) -> LiteraryOptimizationResult:
        return LiteraryOptimizationResult(
            prompt_fragments={
                "writer": ["插件要求见 ai_tone_blocklist/writer.yaml"],
                "revision_handler": ["插件要求见 ai_tone_blocklist/revision_handler.yaml"],
            }
        )
