"""Creative mode profile and creative brief models."""

from typing import Literal

from pydantic import BaseModel, Field

from songyan.models.chapter import ChapterGoal


class Tension(BaseModel):
    """张力定义 — CreativeBrief 的组成部分."""

    tension_id: str
    description: str
    tension_type: Literal[
        "value_conflict",
        "information_asymmetry",
        "power_imbalance",
        "emotional_contrast",
        "temporal_pressure",
    ]
    characters_involved: list[str] = Field(default_factory=list)
    resolution: str = ""  # 预期解决方式，或 "unresolved"
    intensity: float = 0.5


class CreativeBrief(BaseModel):
    """创作导演输出 — 创作意图与张力地图."""

    mode_id: str  # webnovel | literary | hybrid
    chapter_goal: ChapterGoal
    creative_intent: str = ""
    required_tensions: list[Tension] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    allowed_fissures: list[str] = Field(default_factory=list)
    style_constraints: list[str] = Field(default_factory=list)
    reader_contract: str = ""
    polyphony_notes: list[str] = Field(default_factory=list)


class CreativeModeProfile(BaseModel):
    """创作模式配置文件 — 决定 Agent 组合与参数."""

    id: str
    name: str

    enabled_agents: dict[str, list[str]] = Field(default_factory=dict)
    # {
    #   "pre_write": ["goal_planner", "creative_director"],
    #   "write": ["writer"],
    #   "post_write": ["rule_auditor", "llm_auditor", "literary_auditor"],
    #   "revision": ["revision_handler"],
    #   "settlement": ["settlement_extractor"],
    # }

    audit_weights: dict[str, float] = Field(default_factory=dict)
    active_audit_dimensions: list[str] = Field(default_factory=list)
    revision_policy: str = "standard"  # standard | selective | minimal

    tolerance: dict[str, float] = Field(default_factory=dict)
    # {
    #   "max_ai_tells": 2.0,
    #   "max_fatigue_words": 3.0,
    #   "max_cliche_risk": 1.0,
    # }

    context_pruning_strategy: str = "default"  # default | character_focused | theme_focused
    success_metrics: dict[str, float] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "CreativeModeProfile":
        """从 dict 加载（JSON 反序列化后调用）."""
        return cls(**data)
