"""Genre profile model."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class PacingTemplate(BaseModel):
    """节奏模板 — 定义特定章节类型组合的节奏策略."""

    chapter_types: list[str] = Field(default_factory=list)
    emotion_arc: str = ""  # 引用 emotion_arc_library 中的 arc_name
    punch_density: float = Field(default=0.0, ge=0.0, le=5.0)  # 每千字刺激点数
    info_release_strategy: str = ""


class SubGenre(BaseModel):
    """子类型定义 — 基于父类型的差异化规则."""

    sub_genre_id: str
    name: str
    parent_genre_id: str = ""
    differentiation_rules: list[str] = Field(default_factory=list)


class PunchTypeDef(BaseModel):
    """刺激点类型定义 — 可跨 Genre 复用."""

    punch_type_id: str
    description: str = ""
    genre_suitability: dict[str, float] = Field(default_factory=dict)  # genre_id -> 0.0~1.0
    sensory_requirements: list[str] = Field(default_factory=list)


class SensoryTemplate(BaseModel):
    """感官描写模板 — 定义特定感官的描写强度与密度."""

    sense: Literal[
        "visual",
        "auditory",
        "tactile",
        "pain",
        "proprioception",
        "olfactory",
        "gustatory",
    ]
    intensity_target: float = Field(default=0.5, ge=0.0, le=1.0)  # 0.0~1.0
    description_density: float = Field(default=0.0, ge=0.0)  # 每千字描写字数
    example_phrases: list[str] = Field(default_factory=list)


class EmotionArc(BaseModel):
    """情感弧线模板 — 定义章节内情感流转模式."""

    arc_name: str
    phases: list[dict[str, str]] = Field(default_factory=list)
    # 格式: [{"from": "...", "to": "..."}, ...]
    typical_length_words: int = Field(default=0, ge=0)
    suitable_chapter_types: list[str] = Field(default_factory=list)


class StyleBaseline(BaseModel):
    """风格基线 — 定义 Genre 的默认文风参数."""

    sentence_rhythm: str = ""  # "短促有力" / "绵长舒缓" / "错落有致"
    description_density: float = Field(default=0.3, ge=0.0, le=1.0)  # 描写占全文比例
    dialogue_ratio: float = Field(default=0.3, ge=0.0, le=1.0)  # 对话占全文比例
    inner_monologue: str = ""  # "丰富" / "克制" / "几乎没有"
    pov_depth: str = ""  # "深" / "中" / "浅"

    @model_validator(mode="after")
    def _check_density_sum(self) -> StyleBaseline:
        if self.description_density + self.dialogue_ratio > 1.0:
            raise ValueError(
                f"description_density ({self.description_density}) + "
                f"dialogue_ratio ({self.dialogue_ratio}) must not exceed 1.0"
            )
        return self


class GenreProfile(BaseModel):
    """题材配置文件 — 从 genres/*.json 加载."""

    model_config = {"extra": "ignore"}

    id: str
    name: str
    language: str = "zh"

    chapter_types: list[str] = Field(default_factory=list)
    fatigue_words: list[str] = Field(default_factory=list)
    satisfaction_types: list[str] = Field(default_factory=list)

    has_numerical_system: bool = False
    has_power_scaling: bool = False

    # deprecated: 保留 pacing_rule 以向后兼容旧配置
    pacing_rule: str = ""
    writer_rules: list[str] = Field(default_factory=list)
    # V4.0: 按 chapter_type 分组的 writer_rules，未分组时回退到 writer_rules
    writer_rules_by_type: dict[str, list[str]] = Field(default_factory=dict)
    reviewer_focus: list[str] = Field(default_factory=list)
    active_audit_dimensions: list[str] = Field(default_factory=list)
    taboos: list[str] = Field(default_factory=list)

    # Phase 5 新增字段
    pacing_templates: list[PacingTemplate] = Field(default_factory=list)
    sub_genres: list[SubGenre] = Field(default_factory=list)
    punch_type_defs: list[PunchTypeDef] = Field(default_factory=list)
    sensory_templates: list[SensoryTemplate] = Field(default_factory=list)
    emotion_arc_library: list[EmotionArc] = Field(default_factory=list)
    style_baseline: StyleBaseline | None = None
    reference_works: list[str] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenreProfile:
        """从 dict 加载（JSON 反序列化后调用）."""
        return cls(**data)
