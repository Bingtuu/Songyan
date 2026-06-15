"""Project settings model."""

from __future__ import annotations

from typing import Literal

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

    # Phase 4 新增：Arc/Volume 人工配置
    arc_boundaries: list[int] = Field(default_factory=list)
    volume_boundaries: list[int] = Field(default_factory=list)

    # Phase 8a 新增：项目种子配置增强
    estimated_chapters: int = 30
    words_per_chapter: int = 3000
    story_structure: Literal["three_act", "five_act", "serial", "free"] = "free"
    arc_boundaries_auto: bool = False
    sub_genre_id: str | None = None

    @property
    def word_range(self) -> tuple[int, int]:
        """返回字数目标范围（±20%）."""
        lower = int(self.words_per_chapter * 0.8)
        upper = int(self.words_per_chapter * 1.2)
        return (lower, upper)


def derive_arc_boundaries(structure: str, chapters: int) -> list[int]:
    """基于故事结构和预估章数自动推导 Arc 边界.

    Args:
        structure: 故事结构类型
        chapters: 预估总章数

    Returns:
        Arc 边界章节号列表（每两个相邻数字之间为一个 Arc）
    """
    if structure == "three_act":
        # 三幕式：25% / 50% / 25%
        return [int(chapters * 0.25), int(chapters * 0.75)]
    elif structure == "five_act":
        # 五幕式：20% x 5
        step = chapters // 5
        return [step, step * 2, step * 3, step * 4]
    elif structure == "serial":
        # 序列化连载：每 25 章一个 Arc
        arc_size = 25
        return list(range(arc_size, chapters, arc_size))
    return []
