"""Songyan data models — Pydantic v2 domain models."""

from songyan.models.adaptive_gate import (
    AdaptiveGateCleanlinessSignals,
    AdaptiveGateContextSignals,
    AdaptiveGateContinuitySignals,
    AdaptiveGateDataPlaneReport,
    AdaptiveGateLiterarySignals,
    AdaptiveGateNarrativeSignals,
    AdaptiveGateQualitySignals,
    AdaptiveGateSignalSnapshot,
    AdaptiveGateSignalSourceStatus,
    AdaptiveGateSignalWindow,
    AdaptiveGateTrendPoint,
)
from songyan.models.adaptive_halt import (
    AdaptiveHaltDecision,
    AdaptiveHaltDecisionStatus,
    AdaptiveHaltPolicy,
    AdaptiveHaltPolicyMode,
    AdaptiveHaltReason,
    AdaptiveHaltReasonCode,
)
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
    FatigueMotifReplacement,
    HumanMemoryConfig,
    NewConceptBudget,
    ProtagonistActiveChoice,
    PunchPoint,
    SupportingCharacterGoal,
    Tension,
    VoiceAnchor,
    VoiceSample,
)
from songyan.models.foreshadowing_schedule import (
    ForeshadowingScheduleItem,
    ForeshadowingSchedulePlan,
    ForeshadowingScheduleReason,
    ForeshadowingScheduleSourceType,
    ForeshadowingScheduleStatus,
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
from songyan.models.narrative import (
    ArcPlan,
    PlotThread,
    PlotThreadStatus,
    StoryOutline,
)
from songyan.models.project import ProjectSetting
from songyan.models.project_run import ProjectRunResult, ProjectRunState
from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeed,
    TemplateSeedCharacter,
    TemplateSeedNumericalSystem,
    TemplateSeedSetting,
)
from songyan.models.rag import ChunkMetadata, RAGConfig, RetrievedChunk, TextChunk
from songyan.models.replan import (
    ArcOutcomeEvaluation,
    ArcOutcomeRiskLevel,
    PlanningConstraint,
    PlanningConstraintStatus,
    PlanningConstraintType,
    ReplanAction,
    ReplanActionTargetType,
    ReplanApplicationResult,
    ReplanProposal,
    ReplanProposalStatus,
)
from songyan.models.review import (
    AiTellMatch,
    DuplicateParagraphMatch,
    ExpositionCarrierMatch,
    FatigueWordMatch,
    GenericNameMatch,
    LLMAuditResult,
    MergedReviewReport,
    MetaTagLeakMatch,
    MotifFatigueMatch,
    PunchCheck,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
    TextCleanlinessCleanIssue,
)
from songyan.models.revision import Patch, RevisionInput, RevisionOutput
from songyan.models.run_log import ChapterRunLog
from songyan.models.score_card import ChapterScoreCard, DimensionScore, ScoreFlags
from songyan.models.settlement import (
    CharacterUpdate,
    Decrement,
    ForeshadowingUpdate,
    Increment,
    NewCharacter,
    NewSetting,
    NumericalUpdate,
    StateSettlement,
)
from songyan.models.style_mimicry import StyleSample

__all__ = [
    # project
    "ProjectSetting",
    "ProjectTemplate",
    "TemplateSeed",
    "TemplateSeedCharacter",
    "TemplateSeedSetting",
    "TemplateSeedNumericalSystem",
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
    "VoiceAnchor",
    "VoiceSample",
    "ProtagonistActiveChoice",
    "NewConceptBudget",
    "FatigueMotifReplacement",
    "SupportingCharacterGoal",
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
    # V7 Task 167a: active foreshadowing scheduling
    "ForeshadowingSchedulePlan",
    "ForeshadowingScheduleItem",
    "ForeshadowingScheduleStatus",
    "ForeshadowingScheduleSourceType",
    "ForeshadowingScheduleReason",
    # V6 阶段 0 新增：叙事骨架（前置规划）
    "StoryOutline",
    "ArcPlan",
    "PlotThread",
    "PlotThreadStatus",
    # V7 Task 166a: re-plan proposal models
    "ArcOutcomeEvaluation",
    "ArcOutcomeRiskLevel",
    "ReplanProposal",
    "ReplanProposalStatus",
    "ReplanAction",
    "ReplanActionTargetType",
    "PlanningConstraint",
    "PlanningConstraintStatus",
    "PlanningConstraintType",
    "ReplanApplicationResult",
    # review
    "ReviewCategory",
    "ReviewIssue",
    "RuleAuditResult",
    "AiTellMatch",
    "DuplicateParagraphMatch",
    "ExpositionCarrierMatch",
    "FatigueWordMatch",
    "GenericNameMatch",
    "LLMAuditResult",
    "MetaTagLeakMatch",
    "MotifFatigueMatch",
    "TextCleanlinessCleanIssue",
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
    "NewCharacter",
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
    # V7 Task 168a: adaptive gate data plane snapshots
    "AdaptiveGateSignalSnapshot",
    "AdaptiveGateSignalSourceStatus",
    "AdaptiveGateContinuitySignals",
    "AdaptiveGateQualitySignals",
    "AdaptiveGateLiterarySignals",
    "AdaptiveGateCleanlinessSignals",
    "AdaptiveGateContextSignals",
    "AdaptiveGateNarrativeSignals",
    "AdaptiveGateTrendPoint",
    "AdaptiveGateSignalWindow",
    "AdaptiveGateDataPlaneReport",
    # V7 Task 169a: adaptive halt decision models
    "AdaptiveHaltPolicy",
    "AdaptiveHaltPolicyMode",
    "AdaptiveHaltDecision",
    "AdaptiveHaltDecisionStatus",
    "AdaptiveHaltReason",
    "AdaptiveHaltReasonCode",
]
