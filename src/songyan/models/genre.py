"""Genre profile model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GenreProfile(BaseModel):
    """题材配置文件 — 从 genres/*.json 加载."""

    id: str
    name: str
    language: str = "zh"

    chapter_types: list[str] = Field(default_factory=list)
    fatigue_words: list[str] = Field(default_factory=list)
    satisfaction_types: list[str] = Field(default_factory=list)

    has_numerical_system: bool = False
    has_power_scaling: bool = False

    pacing_rule: str = ""
    writer_rules: list[str] = Field(default_factory=list)
    reviewer_focus: list[str] = Field(default_factory=list)
    active_audit_dimensions: list[str] = Field(default_factory=list)
    taboos: list[str] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> GenreProfile:
        """从 dict 加载（JSON 反序列化后调用）."""
        return cls(**data)
