"""V12 startup supervision spec models.

The spec is a structured startup contract for Ch1-Ch3 calibration. It keeps
redlines and beat sheets out of prose ``arc_goal`` so deterministic tooling can
review plans before Writer runs.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WordCountPolicy(BaseModel):
    """Word-count policy for a startup stage."""

    model_config = ConfigDict(extra="forbid")

    target: int = Field(gt=0)
    hard_min: int = Field(ge=0)
    hard_max: int = Field(gt=0)
    soft_min: int | None = Field(default=None, ge=0)
    soft_max: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_window(self) -> WordCountPolicy:
        """Ensure hard and soft windows are internally consistent."""
        if self.hard_min > self.target:
            msg = "hard_min must be <= target"
            raise ValueError(msg)
        if self.target > self.hard_max:
            msg = "target must be <= hard_max"
            raise ValueError(msg)
        if self.soft_min is not None and self.soft_min < self.hard_min:
            msg = "soft_min must be >= hard_min"
            raise ValueError(msg)
        if self.soft_max is not None and self.soft_max > self.hard_max:
            msg = "soft_max must be <= hard_max"
            raise ValueError(msg)
        if (
            self.soft_min is not None
            and self.soft_max is not None
            and self.soft_min > self.soft_max
        ):
            msg = "soft_min must be <= soft_max"
            raise ValueError(msg)
        return self


class BeatSpec(BaseModel):
    """One Writer-consumable beat in the startup beat sheet."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    visible_action: str = Field(min_length=1)
    current_friction: str = Field(min_length=1)
    feedback: str = Field(min_length=1)
    micro_decision: str = Field(min_length=1)
    landing: str = Field(min_length=1)


class StagePolicy(BaseModel):
    """Startup-stage policy flags used by deterministic plan review."""

    model_config = ConfigDict(extra="forbid")

    allow_new_characters: bool = False
    allow_past_backstory: bool = False
    allow_cross_location_chase: bool = False
    allow_identity_secret_reveal: bool = False
    allow_relative_time: bool = False
    allow_coordinates: bool = False


class ReviewPolicy(BaseModel):
    """Human supervision GO/STOP criteria for a stage or chapter."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    go_conditions: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)

    @field_validator("go_conditions", "stop_conditions")
    @classmethod
    def strip_empty_items(cls, values: list[str]) -> list[str]:
        """Reject empty condition entries."""
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            msg = "review conditions must not contain empty strings"
            raise ValueError(msg)
        return cleaned


class ChapterSupervisionSpec(BaseModel):
    """Structured supervision contract for one chapter."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    allowed_beats: list[BeatSpec] = Field(min_length=1)
    required_phrases: list[str] = Field(default_factory=list)
    forbidden_literals: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    stage_policy: StagePolicy = Field(default_factory=StagePolicy)
    review: ReviewPolicy = Field(default_factory=ReviewPolicy)

    @field_validator(
        "required_phrases", "forbidden_literals", "forbidden_patterns", mode="after"
    )
    @classmethod
    def validate_string_list(cls, values: list[str]) -> list[str]:
        """Strip and reject empty strings."""
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            msg = "string lists must not contain empty strings"
            raise ValueError(msg)
        return cleaned

    @field_validator("forbidden_patterns")
    @classmethod
    def validate_regex_patterns(cls, values: list[str]) -> list[str]:
        """Validate regex patterns at load time."""
        for value in values:
            try:
                re.compile(value)
            except re.error as exc:
                msg = f"invalid forbidden pattern {value!r}: {exc}"
                raise ValueError(msg) from exc
        return values


class SupervisionSpec(BaseModel):
    """V12 startup supervision spec.

    ``arc_goal`` can still carry creative intent, but startup redlines and beat
    sheets should be read from this model by downstream tools.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: str = Field(default="v12.1", min_length=1)
    stage: Literal["startup_ch1_3", "startup_ch1_only"]
    word_count: WordCountPolicy
    chapters: dict[int, ChapterSupervisionSpec] = Field(min_length=1)
    review: ReviewPolicy = Field(default_factory=ReviewPolicy)

    @field_validator("chapters")
    @classmethod
    def validate_chapter_numbers(
        cls, chapters: dict[int, ChapterSupervisionSpec]
    ) -> dict[int, ChapterSupervisionSpec]:
        """Chapter keys must be positive integers."""
        invalid = [chapter for chapter in chapters if chapter <= 0]
        if invalid:
            msg = f"chapter numbers must be positive integers: {invalid}"
            raise ValueError(msg)
        return chapters

    def chapter(self, chapter_number: int) -> ChapterSupervisionSpec:
        """Return the supervision contract for one chapter."""
        try:
            return self.chapters[chapter_number]
        except KeyError as exc:
            msg = f"supervision spec does not define chapter {chapter_number}"
            raise KeyError(msg) from exc

    def forbidden_literals_for_chapter(self, chapter_number: int) -> list[str]:
        """Return scanner-ready literal forbidden terms for one chapter."""
        return list(self.chapter(chapter_number).forbidden_literals)

    def forbidden_patterns_for_chapter(self, chapter_number: int) -> list[re.Pattern[str]]:
        """Compile regex redlines for deterministic plan or text review."""
        return [
            re.compile(pattern)
            for pattern in self.chapter(chapter_number).forbidden_patterns
        ]

    def required_phrases_for_chapter(self, chapter_number: int) -> list[str]:
        """Return deterministic required phrases for one chapter."""
        return list(self.chapter(chapter_number).required_phrases)

    def beat_sheet_for_chapter(self, chapter_number: int) -> list[BeatSpec]:
        """Return Writer-consumable beats for one chapter."""
        return list(self.chapter(chapter_number).allowed_beats)


class PlanOnlyArtifact(BaseModel):
    """IDs created by a plan-only pass for one chapter."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str = Field(min_length=1)
    chapter_number: int = Field(ge=1)
    chapter_goal_id: str = Field(min_length=1)
    creative_brief_id: str = Field(min_length=1)


class PlanOnlyResult(BaseModel):
    """Plan-only output for a chapter range."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str = Field(min_length=1)
    artifacts: list[PlanOnlyArtifact] = Field(min_length=1)

    @property
    def chapters(self) -> list[int]:
        """Return chapter numbers covered by this result."""
        return [artifact.chapter_number for artifact in self.artifacts]


class PlanReviewFinding(BaseModel):
    """One deterministic review finding for a plan artifact."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    chapter_number: int = Field(ge=1)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    evidence: str = Field(default="")
    severity: Literal["blocker", "warning"] = "blocker"


class PlanReviewResult(BaseModel):
    """Deterministic review result for plan-only artifacts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str = Field(min_length=1)
    artifacts: list[PlanOnlyArtifact] = Field(default_factory=list)
    findings: list[PlanReviewFinding] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return whether no blocker was found."""
        return not any(finding.severity == "blocker" for finding in self.findings)


class ApprovedPlan(BaseModel):
    """Approval marker for a reviewed plan-only result."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str = Field(min_length=1)
    chapters: list[int] = Field(min_length=1)
    artifact_token: str = Field(min_length=1)
    approved_by: str = Field(default="deterministic-review", min_length=1)
    approved_at: datetime = Field(default_factory=datetime.now)
