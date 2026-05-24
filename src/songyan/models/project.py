"""Project settings model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectSetting(BaseModel):
    """小说项目配置."""

    title: str | None = None
    genre_id: str
    mode_id: str = "webnovel"
    protagonist_name: str
    protagonist_background: str = ""
    core_hook: str = ""
    target_reader_expectation: str = ""
    taboos: list[str] = Field(default_factory=list)
    target_word_count: int = 100_000
    tone: str = "热血"
    reference_works: list[str] = Field(default_factory=list)
