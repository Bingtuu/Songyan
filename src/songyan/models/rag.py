"""RAG (Retrieval-Augmented Generation) 数据模型."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Chunk 元数据 — 用于过滤和展示."""

    scene_number: int | None = None
    characters_mentioned: list[str] = Field(default_factory=list)
    setting_keys_mentioned: list[str] = Field(default_factory=list)
    chunk_type: Literal["narrative", "dialogue", "description", "action"] = "narrative"
    start_char: int = 0
    end_char: int = 0


class TextChunk(BaseModel):
    """章节文本切片 — RAG 的基本单元."""

    chunk_id: str
    project_id: str
    chapter_number: int
    version_id: str
    chunk_index: int
    text: str
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)


class RetrievedChunk(BaseModel):
    """RAG 检索结果 — 注入 ContextPackage 的形式."""

    chunk_id: str
    text: str
    chapter_number: int
    similarity: float
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)


class RAGConfig(BaseModel):
    """RAG 层配置 — 按创作模式差异化."""

    enabled: Literal["auto", "always", "never"] = "auto"
    threshold_chapters: int | None = None
    max_results: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 100
    min_similarity: float = 0.3
    embedding_model: str = "shibing624/text2vec-base-chinese"
    vector_store: str = "sqlite_numpy"
