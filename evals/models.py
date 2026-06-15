"""评测集数据模型 — 种子项目配置 + 评测结果."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SeedCharacter(BaseModel):
    """种子项目中的角色配置."""

    name: str
    role: str = "protagonist"  # protagonist | supporting | antagonist
    age: int | None = None
    description: str = ""
    initial_state: dict[str, str | int | float] = Field(default_factory=dict)


class SeedSetting(BaseModel):
    """种子项目中的世界设定配置."""

    setting_key: str
    setting_name: str
    description: str = ""
    source_quote: str = ""


class SeedNumericalSystem(BaseModel):
    """种子项目中的数值体系配置（玄幻必填）."""

    name: str
    levels: list[str] = Field(default_factory=list)
    base_unit: str = ""
    formula_hint: str = ""


class SeedProjectConfig(BaseModel):
    """种子项目配置 — 可直接导入 SQLite."""

    project_name: str
    genre_id: str  # xuanhuan | urban | scifi
    mode_id: str = "webnovel"  # webnovel | hybrid | literary
    description: str = ""
    characters: list[SeedCharacter] = Field(default_factory=list)
    initial_settings: list[SeedSetting] = Field(default_factory=list)
    numerical_system: SeedNumericalSystem | None = None


class EvaluationResult(BaseModel):
    """单次评测原始结果."""

    project_id: str
    project_name: str
    genre_id: str
    mode_id: str
    seed_config_path: str
    seed_chapter_path: str
    success: bool
    chapter_version_id: str = ""
    merged_review_report_id: str = ""
    settlement_id: str = ""
    summary_id: str = ""
    duration_ms: int = 0
    metrics: dict[str, float | int | None] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)
    output_dir: str = ""
