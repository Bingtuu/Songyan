# tests/literary_optimization/test_base.py
from songyan.literary_optimization import (
    LiteraryContext,
    LiteraryOptimizationResult,
    LiteraryOptimizationStrategy,
    list_strategies,
    load_strategy,
)


class DummyStrategy(LiteraryOptimizationStrategy):
    @property
    def strategy_id(self) -> str:
        return "dummy"

    @property
    def applicable_agents(self) -> list[str]:
        return ["writer"]

    def apply(self, context: LiteraryContext) -> LiteraryOptimizationResult:
        return LiteraryOptimizationResult(
            prompt_fragments={"writer": ["dummy fragment"]}
        )


def test_strategy_interface():
    s = DummyStrategy()
    assert s.strategy_id == "dummy"
    assert s.applicable_agents == ["writer"]
    result = s.apply(LiteraryContext())
    assert result.prompt_fragments == {"writer": ["dummy fragment"]}


def test_registry_lists_built_in_strategies():
    strategies = list_strategies()
    assert "ai_tone_blocklist" in strategies
    assert "few_shot_voice_anchor" in strategies
    assert "minimal_voice_anchor" in strategies
    assert "opposing_goal_anchor" in strategies


def test_load_strategy():
    s = load_strategy("minimal_voice_anchor")
    assert s.strategy_id == "minimal_voice_anchor"
    assert "creative_director" in s.applicable_agents
    assert "writer" in s.applicable_agents


def test_load_opposing_goal_anchor_strategy():
    s = load_strategy("opposing_goal_anchor")
    assert s.strategy_id == "opposing_goal_anchor"
    assert "creative_director" in s.applicable_agents
    assert "writer" in s.applicable_agents
    result = s.apply(LiteraryContext())
    assert "creative_director" in result.prompt_fragments
    assert "writer" in result.prompt_fragments


def test_load_few_shot_voice_anchor_strategy():
    s = load_strategy("few_shot_voice_anchor")
    assert s.strategy_id == "few_shot_voice_anchor"
    assert s.applicable_agents == ["creative_director", "writer"]
    result = s.apply(LiteraryContext())
    assert "creative_director" in result.prompt_fragments
    assert "writer" in result.prompt_fragments


def test_load_ai_tone_blocklist_strategy():
    s = load_strategy("ai_tone_blocklist")
    assert s.strategy_id == "ai_tone_blocklist"
    assert s.applicable_agents == ["writer", "revision_handler"]
    result = s.apply(LiteraryContext())
    assert "writer" in result.prompt_fragments
    assert "revision_handler" in result.prompt_fragments
