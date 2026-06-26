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


class EmotionArcItem(BaseModel):
    """情绪曲线项 — 单场景的情绪目标."""

    scene: int
    from_emotion: str
    to_emotion: str


class PunchPoint(BaseModel):
    """刺激点定义 — Punch Engine 的核心输出."""

    punch_id: str
    description: str
    punch_type: Literal[
        "sensory_shock",
        "emotional_switch",
        "revelation",
        "physical_cost",
        "cognitive_twist",
    ]
    target_scene: int
    intensity: float = 0.5  # 0.0~1.0
    dominant_sense: Literal[
        "visual", "auditory", "tactile", "pain", "proprioception"
    ] | None = None


class CreativeBrief(BaseModel):
    """创作导演输出 — 创作意图与张力地图."""

    mode_id: str  # webnovel | literary | hybrid | webnovel_intense
    chapter_goal: ChapterGoal
    creative_intent: str = ""
    required_tensions: list[Tension] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    allowed_fissures: list[str] = Field(default_factory=list)
    style_constraints: list[str] = Field(default_factory=list)
    reader_contract: str = ""
    polyphony_notes: list[str] = Field(default_factory=list)
    punch_points: list[PunchPoint] = Field(default_factory=list)
    emotion_arc: list[EmotionArcItem] = Field(default_factory=list)

    # Task 098: 上下文压力计四信号
    # 叙事充满度 — 0.0 (线索未展开) ~ 1.0 (所有线索已展开)
    narrative_fullness: float = 0.0
    # 角色焦点 — 每个元素指定角色 ID 和详细度
    character_focus: list[dict] = Field(default_factory=list)
    # 到期伏笔列表 — foreshadowing_id 列表
    foreshadowing_due: list[str] = Field(default_factory=list)
    # 景深 — close(40%) / mid(40%) / wide(15%) / disruption(5%)
    focal_distance: str = "mid"


class HumanMemoryConfig(BaseModel):
    """人类辅助记忆配置 — Phase 7."""

    priority_threshold: int = 8  # priority >= threshold 的 marks 进入 ContextPackage
    max_marks_in_context: int = 10  # 硬上限
    chapter_window: int = 3  # 078: 只加载最近 N 章写入的 marks（priority=10 除外）


class RAGConfig(BaseModel):
    """RAG 层配置 — Phase 8b."""

    enabled: Literal["auto", "always", "never"] = "auto"
    threshold_chapters: int | None = None
    max_results: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 100
    min_similarity: float = 0.3
    embedding_model: str = "shibing624/text2vec-base-chinese"
    vector_store: str = "sqlite_numpy"


class CreativeModeProfile(BaseModel):
    """创作模式配置文件 — 决定 Agent 组合与参数."""

    model_config = {"extra": "ignore"}

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

    # Phase 7: Human-Augmented Memory
    human_memory: HumanMemoryConfig = Field(default_factory=HumanMemoryConfig)

    # Phase 8b: RAG 自动层
    rag_config: RAGConfig = Field(default_factory=RAGConfig)

    # Task 128b: 开局期质量爬坡窗口章节数（默认前 10 章使用更宽松阈值）
    quality_ramp_chapters: int = 10

    @classmethod
    def from_dict(cls, data: dict) -> "CreativeModeProfile":
        """从 dict 加载（JSON 反序列化后调用）."""
        return cls(**data)

