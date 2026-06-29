"""Context package and sub-models — Writer 输入的上下文组装结构."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from songyan.models.chapter import ChapterGoal
from songyan.models.character import DialogueStyleCard
from songyan.models.creative_mode import CreativeBrief
from songyan.models.genre import StyleBaseline
from songyan.models.human_mark import HumanMark


class HardConstraint(BaseModel):
    """硬约束 — 最高优先级."""

    type: Literal[
        "character_state",
        "setting_fact",
        "timeline",
        "taboo",
        "obligation",
        "human_mark",
    ]
    description: str
    source: str


class CharacterStateSnapshot(BaseModel):
    """角色状态快照 — ContextPackage 分区 2."""

    character_id: str
    name: str
    current_location: str | None = None
    current_cultivation: str | None = None
    emotional_state: str | None = None
    active_relationships: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    importance_score: float = 0.0  # 本章重要性：主角=1.0，出场=0.8，关联=0.5


class ChapterSummary(BaseModel):
    """章节摘要 — RecentPlot 的组成部分."""

    chapter_number: int
    summary: str
    key_events: list[str] = Field(default_factory=list)
    characters_appeared: list[str] = Field(default_factory=list)
    emotional_tone: str = ""
    impact_score: float = 0.0  # 本章影响力评分（0.0~1.0）
    source_type: Literal["chapter", "arc", "volume"] = "chapter"


class RecentPlot(BaseModel):
    """最近剧情 — ContextPackage 分区 3."""

    summaries: list[ChapterSummary] = Field(default_factory=list)
    last_chapter_ending: str = ""
    open_threads: list[str] = Field(default_factory=list)


class ForeshadowingItem(BaseModel):
    """伏笔线索 — ContextPackage 分区 4."""

    foreshadowing_id: str
    description: str
    planted_in_chapter: int
    expected_resolve_chapter: int | None = None
    status: Literal["planted", "due", "overdue", "resolved", "archived"] = "planted"
    source_version_id: str | None = None


class SoftReference(BaseModel):
    """软参考 — 最低优先级，超预算时先裁剪."""

    type: Literal[
        "world_setting",
        "character_backstory",
        "style_sample",
        "rag_retrieval",  # Phase 8b 新增
    ]
    content: str
    relevance_score: float = 0.0
    last_mentioned_chapter: int | None = None  # 最后提及章节（用于动态相关性计算）
    is_critical: bool = False  # 人类标记的关键设定（不衰减）
    source_chapter: int | None = None  # Phase 8b: RAG 结果来源章节
    similarity: float | None = None  # Phase 8b: RAG 相似度分数


class GenreRules(BaseModel):
    """题材规则 — 从 GenreProfile 注入 Writer."""

    genre_id: str = ""
    writer_rules: list[str] = Field(default_factory=list)
    fatigue_words: list[str] = Field(default_factory=list)
    satisfaction_types: list[str] = Field(default_factory=list)
    pacing_rule: str = ""
    taboos: list[str] = Field(default_factory=list)
    style_baseline: StyleBaseline | None = None
    pacing_templates: list[dict] = Field(default_factory=list)
    sensory_templates: list[dict] = Field(default_factory=list)
    # Phase 8a: 子类型差异化规则
    sub_genre_rules: list[str] = Field(default_factory=list)
    # V3.1: 审查焦点（按章节类型按需注入）
    reviewer_focus: list[str] = Field(default_factory=list)


class ModeRules(BaseModel):
    """创作模式规则 — 从 CreativeModeProfile 注入."""

    mode_id: str = ""
    revision_policy: str = "standard"
    tolerance_max_ai_tells: float = 2.0
    tolerance_max_fatigue_words: float = 3.0
    tolerance_max_cliche_risk: float = 2.0
    context_pruning_strategy: str = "default"


# ---------------------------------------------------------------------------
# Phase 4: 分层上下文模型
# ---------------------------------------------------------------------------

class ArcSummary(BaseModel):
    """Arc 摘要 — 中等粒度上下文."""

    arc_id: str
    project_id: str = ""
    start_chapter: int
    end_chapter: int
    arc_title: str = ""
    arc_summary: str = ""  # ~500 字
    key_events: list[str] = Field(default_factory=list)
    resolved_threads: list[str] = Field(default_factory=list)
    new_threads: list[str] = Field(default_factory=list)
    character_arcs: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)


class VolumeSummary(BaseModel):
    """卷摘要 — 宏观上下文."""

    volume_id: str
    project_id: str = ""
    start_chapter: int
    end_chapter: int
    volume_title: str = ""
    volume_summary: str = ""  # ~1000 字
    major_revelations: list[str] = Field(default_factory=list)
    world_state: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)


class PermanentScene(BaseModel):
    """关键场景 — 永久保留的高影响力段落."""

    scene_id: str
    chapter_number: int
    scene_number: int = 1
    excerpt: str = ""  # ~200 字核心段落
    impact_tags: list[str] = Field(default_factory=list)
    referenced_by: list[int] = Field(default_factory=list)


class OpenThread(BaseModel):
    """未完结线索 — 从 settlement 提取的开放线程."""

    thread_id: str
    description: str
    source_type: Literal["foreshadowing", "setting", "character_goal", "conflict"]
    source_chapter: int
    priority: float = 0.5


# ---------------------------------------------------------------------------
# ContextPackage
# ---------------------------------------------------------------------------

class ContextPackage(BaseModel):
    """写作上下文包 — 按 Token 预算组装，超出时按优先级裁剪."""

    chapter_goal: ChapterGoal
    creative_brief: CreativeBrief | None = None

    # === 分区 1：硬约束 ===
    hard_constraints: list[HardConstraint] = Field(default_factory=list)

    # === 分区 2：角色状态快照 ===
    character_states: list[CharacterStateSnapshot] = Field(default_factory=list)

    # === 分区 3：最近剧情 ===
    recent_plot: RecentPlot = Field(default_factory=RecentPlot)

    # === 分区 4：伏笔线索 ===
    foreshadowing: list[ForeshadowingItem] = Field(default_factory=list)

    # === 分区 5：软参考 ===
    soft_references: list[SoftReference] = Field(default_factory=list)

    # === 分区 6：题材规则 ===
    genre_rules: GenreRules | None = None

    # === 分区 7：创作模式规则 ===
    mode_rules: ModeRules | None = None

    # === 人类指令（HITL）===
    human_instructions: list[dict] = Field(default_factory=list)

    # === Phase 4 新增：分层上下文 ===
    arc_context: ArcSummary | None = None
    volume_context: VolumeSummary | None = None
    permanent_scenes: list[PermanentScene] = Field(default_factory=list)
    open_threads: list[OpenThread] = Field(default_factory=list)

    # === Phase 7 新增：人类辅助记忆标记 ===
    human_marks: list[HumanMark] = Field(default_factory=list)

    # === Task 074: 角色对话风格卡 ===
    dialogue_style_cards: list[DialogueStyleCard] = Field(default_factory=list)

    # === Task 138h: 强制连续性约束（critical orphan 硬回收）===
    mandatory_references: list[dict] = Field(default_factory=list)

    # === 元信息 ===
    estimated_tokens: int = 0
    _budget_enforced: bool = False  # 077b: 是否触发了 BudgetPruner 硬断言
    assembled_at: datetime = Field(default_factory=datetime.now)
    budget_used: float = 0.0
    character_states_total: int = 0  # 080: DB 中总角色状态数（监控用）
    # Task 100c: 上下文压力指标（供后期复盘）
    context_pressure: dict = Field(default_factory=dict)
    # Task 104: 是否触发了 ContextEmergency（预算硬天花板）
    context_emergency: bool = False
    # Task 110c: ContextEmergency 降级级别（1/2/3）
    context_emergency_level: int = 0
    # Task 115: Emergency 触发前的 budget_used（用于可观测性）
    budget_used_before_emergency: float | None = None


class ContextSnapshot(BaseModel):
    """裁剪后上下文快照 — 供 Writer/Auditor 复用与 prompt 回放."""

    snapshot_id: str
    project_id: str
    chapter_number: int
    chapter_goal_id: str | None = None
    creative_brief_id: str | None = None
    budget_used: float | None = None
    context_emergency: bool = False
    context_emergency_level: int = 0
    budget_used_before_emergency: float | None = None
    payload: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
