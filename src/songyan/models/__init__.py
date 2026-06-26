"""Songyan data models — Pydantic v2 domain models."""

from songyan.models.chapter import ChapterGoal, ChapterHead, ChapterVersion
from songyan.models.character import Character, CharacterState, DialogueStyleCard
from songyan.models.context import (
    ArcSummary,
    ChapterSummary,
    CharacterStateSnapshot,
    ContextPackage,
    ContextSnapshot,
    ForeshadowingItem,
    GenreRules,
    HardConstraint,
    ModeRules,
    OpenThread,
    PermanentScene,
    RecentPlot,
    SoftReference,
    VolumeSummary,
)
from songyan.models.continuity import (
    ContinuityReport,
    ForgottenItem,
    OrphanedSetting,
    OverdueForeshadowing,
    StateMismatch,
)
from songyan.models.creative_mode import (
    CreativeBrief,
    CreativeModeProfile,
    EmotionArcItem,
    HumanMemoryConfig,
    PunchPoint,
    Tension,
)
from songyan.models.gate_config import GateConfig
from songyan.models.genre import (
    EmotionArc,
    GenreProfile,
    PacingTemplate,
    PunchTypeDef,
    SensoryTemplate,
    StyleBaseline,
    SubGenre,
)
from songyan.models.human_instruction import HumanInstruction
from songyan.models.human_mark import HumanMark, SuggestedMark
from songyan.models.literary import LiteraryAuditResult, LiteraryObservation
from songyan.models.project import ProjectSetting
from songyan.models.project_run import ProjectRunResult, ProjectRunState
from songyan.models.rag import ChunkMetadata, RAGConfig, RetrievedChunk, TextChunk
from songyan.models.review import (
    AiTellMatch,
    FatigueWordMatch,
    GenericNameMatch,
    LLMAuditResult,
    MergedReviewReport,
    MetaTagLeakMatch,
    PunchCheck,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
)
from songyan.models.revision import Patch, RevisionInput, RevisionOutput
from songyan.models.run_log import ChapterRunLog
from songyan.models.score_card import ChapterScoreCard, DimensionScore, ScoreFlags
from songyan.models.settlement import (
    CharacterUpdate,
    Decrement,
    ForeshadowingUpdate,
    Increment,
    NewSetting,
    NumericalUpdate,
    StateSettlement,
)
from songyan.models.style_mimicry import StyleSample

__all__ = [
    # project
    "ProjectSetting",
    # character
    "Character",
    "CharacterState",
    "DialogueStyleCard",
    # chapter
    "ChapterGoal",
    "ChapterVersion",
    "ChapterHead",
    # genre
    "GenreProfile",
    "PacingTemplate",
    "SubGenre",
    "PunchTypeDef",
    "SensoryTemplate",
    "EmotionArc",
    "StyleBaseline",
    # creative_mode
    "CreativeModeProfile",
    "CreativeBrief",
    "Tension",
    "PunchPoint",
    "EmotionArcItem",
    "HumanMemoryConfig",
    "HumanInstruction",
    # continuity
    "ContinuityReport",
    "OrphanedSetting",
    "ForgottenItem",
    "StateMismatch",
    "OverdueForeshadowing",
    # context
    "ContextPackage",
    "ContextSnapshot",
    "HardConstraint",
    "CharacterStateSnapshot",
    "RecentPlot",
    "ChapterSummary",
    "ForeshadowingItem",
    "SoftReference",
    "GenreRules",
    "ModeRules",
    # Phase 4 新增
    "ArcSummary",
    "VolumeSummary",
    "PermanentScene",
    "OpenThread",
    # review
    "ReviewCategory",
    "ReviewIssue",
    "RuleAuditResult",
    "AiTellMatch",
    "FatigueWordMatch",
    "GenericNameMatch",
    "LLMAuditResult",
    "MetaTagLeakMatch",
    "MergedReviewReport",
    "PunchCheck",
    # literary
    "LiteraryObservation",
    "LiteraryAuditResult",
    # revision
    "RevisionInput",
    "Patch",
    "RevisionOutput",
    # settlement
    "StateSettlement",
    "CharacterUpdate",
    "NewSetting",
    "ForeshadowingUpdate",
    "NumericalUpdate",
    "Increment",
    "Decrement",
    # Phase 5 新增
    "StyleSample",
    # Phase 7 新增
    "HumanMark",
    "SuggestedMark",
    # Phase 8b 新增
    "TextChunk",
    "ChunkMetadata",
    "RetrievedChunk",
    "RAGConfig",
    # Task 058a 新增
    "ChapterRunLog",
    "ProjectRunResult",
    # Task 123 新增
    "GateConfig",
    "ProjectRunState",
    "ChapterScoreCard",
    "DimensionScore",
    "ScoreFlags",
]
