"""Songyan data models — Pydantic v2 domain models."""

from songyan.models.chapter import ChapterGoal, ChapterHead, ChapterVersion
from songyan.models.character import Character, CharacterState
from songyan.models.context import (
    ChapterSummary,
    CharacterStateSnapshot,
    ContextPackage,
    ForeshadowingItem,
    GenreRules,
    HardConstraint,
    ModeRules,
    RecentPlot,
    SoftReference,
)
from songyan.models.creative_mode import CreativeBrief, CreativeModeProfile, Tension
from songyan.models.genre import GenreProfile
from songyan.models.literary import LiteraryAuditResult, LiteraryObservation
from songyan.models.project import ProjectSetting
from songyan.models.review import (
    AiTellMatch,
    FatigueWordMatch,
    LLMAuditResult,
    MergedReviewReport,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
)
from songyan.models.revision import Patch, RevisionInput, RevisionOutput
from songyan.models.settlement import (
    CharacterUpdate,
    Decrement,
    ForeshadowingUpdate,
    Increment,
    NewSetting,
    NumericalUpdate,
    StateSettlement,
)

__all__ = [
    # project
    "ProjectSetting",
    # character
    "Character",
    "CharacterState",
    # chapter
    "ChapterGoal",
    "ChapterVersion",
    "ChapterHead",
    # genre
    "GenreProfile",
    # creative_mode
    "CreativeModeProfile",
    "CreativeBrief",
    "Tension",
    # context
    "ContextPackage",
    "HardConstraint",
    "CharacterStateSnapshot",
    "RecentPlot",
    "ChapterSummary",
    "ForeshadowingItem",
    "SoftReference",
    "GenreRules",
    "ModeRules",
    # review
    "ReviewCategory",
    "ReviewIssue",
    "RuleAuditResult",
    "AiTellMatch",
    "FatigueWordMatch",
    "LLMAuditResult",
    "MergedReviewReport",
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
]
