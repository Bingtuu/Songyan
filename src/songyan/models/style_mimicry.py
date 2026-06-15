"""Style mimicry models — 风格模仿引擎数据模型."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StyleSample(BaseModel):
    """风格样本 — 从参考作品提取的风格特征."""

    work_name: str
    author: str = ""
    excerpt: str = ""  # 200~500 字代表性段落
    analysis: str = ""  # 风格特征分析
    genre_tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
