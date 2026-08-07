"""Creative mode profile and creative brief models."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

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


class VoiceAnchor(BaseModel):
    """Task 170j: 极简声纹锚定 — 每个核心人类角色的情绪基调+口头禅/禁忌."""

    character_id: str
    emotional_register: str = ""
    verbal_tick: str = ""
    taboo_phrase: str = ""


class VoiceSample(BaseModel):
    """Task 170l: 角色声纹样例 — 示例台词、禁忌与情绪基调."""

    character_id: str
    character_name: str = ""
    sample_lines: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    mood_anchor: str = ""


class ProtagonistActiveChoice(BaseModel):
    """Task 171v: 主角主动选择护栏."""

    choice: str = ""
    alternatives: list[str] = Field(default_factory=list)
    cost: str = ""
    irreversible_consequence: str = ""


class NewConceptBudget(BaseModel):
    """Task 171v: 新概念预算与落地约束."""

    max_new_core_concepts: int = Field(default=1, ge=0, le=3)
    grounding_scene: str = ""
    forbidden_mode: str = "禁止连续解释协议机制"


class FatigueMotifReplacement(BaseModel):
    """Task 171v: 高频母题替代表达建议."""

    overused: str
    alternatives: list[str] = Field(default_factory=list)


class SupportingCharacterGoal(BaseModel):
    """Task 171v: 配角独立目标护栏."""

    character: str = ""
    goal: str = ""
    conflict_with_protagonist: str = ""
    scene_consequence: str = ""


class CreativeBrief(BaseModel):
    """创作导演输出 — 创作意图与张力地图."""

    mode_id: str  # webnovel | literary | hybrid | webnovel_intense
    chapter_goal: ChapterGoal | None = None
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
    character_focus: list[dict[str, Any]] = Field(default_factory=list)
    # 到期伏笔列表 — foreshadowing_id 列表
    foreshadowing_due: list[str] = Field(default_factory=list)
    # 景深 — close(40%) / mid(40%) / wide(15%) / disruption(5%)
    focal_distance: str = "mid"

    # Task 170j: 极简声纹锚定
    voice_anchors: list[VoiceAnchor] = Field(default_factory=list)

    # Task 170l: 角色声纹样例库
    voice_samples: list[VoiceSample] = Field(default_factory=list)

    # Task 171v: Ch200+ 文学性与可读性护栏（observe-first）
    protagonist_active_choice: ProtagonistActiveChoice | None = None
    new_concept_budget: NewConceptBudget | None = None
    fatigue_motif_replacements: list[FatigueMotifReplacement] = Field(default_factory=list)
    supporting_character_goal: SupportingCharacterGoal | None = None


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

    @model_validator(mode="after")
    def validate_chunk_window(self) -> "RAGConfig":
        """Prevent non-advancing chunk windows during long paragraph splitting."""
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")
        return self


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

    # Task 170j: 启用的文学优化策略插件 ID 列表
    literary_optimization_plugins: list[str] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CreativeModeProfile":
        """从 dict 加载（JSON 反序列化后调用）."""
        return cls(**data)
