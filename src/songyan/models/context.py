"""Context package and sub-models — Writer 输入的上下文组装结构."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from songyan.models.chapter import ChapterGoal
from songyan.models.creative_mode import CreativeBrief


class HardConstraint(BaseModel):
    """硬约束 — 最高优先级."""

    type: Literal[
        "character_state",
        "setting_fact",
        "timeline",
        "taboo",
        "obligation",
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
    status: Literal["planted", "due", "overdue", "resolved"] = "planted"


class SoftReference(BaseModel):
    """软参考 — 最低优先级，超预算时先裁剪."""

    type: Literal["world_setting", "character_backstory", "style_sample"]
    content: str
    relevance_score: float = 0.0


class GenreRules(BaseModel):
    """题材规则 — 从 GenreProfile 注入 Writer."""

    genre_id: str = ""
    writer_rules: list[str] = Field(default_factory=list)
    fatigue_words: list[str] = Field(default_factory=list)
    satisfaction_types: list[str] = Field(default_factory=list)
    pacing_rule: str = ""
    taboos: list[str] = Field(default_factory=list)


class ModeRules(BaseModel):
    """创作模式规则 — 从 CreativeModeProfile 注入."""

    mode_id: str = ""
    revision_policy: str = "standard"
    tolerance_max_ai_tells: float = 2.0
    tolerance_max_fatigue_words: float = 3.0
    tolerance_max_cliche_risk: float = 2.0
    context_pruning_strategy: str = "default"


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

    # === 元信息 ===
    estimated_tokens: int = 0
    assembled_at: datetime = Field(default_factory=datetime.now)
    budget_used: float = 0.0
