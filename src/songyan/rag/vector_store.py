"""向量存储 — SQLite 持久化 + numpy 内存数组."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import structlog

from songyan.models.rag import RetrievedChunk, TextChunk

if TYPE_CHECKING:
    from songyan.db.chunk_repo import ChunkRepository

logger = structlog.get_logger(__name__)

# 内存上限报警阈值
_CHUNK_WARNING_THRESHOLD = 5000


class VectorStore:
    """简单向量存储 — SQLite 存元数据 + 向量 BLOB，numpy 存内存副本用于检索."""

    def __init__(self, project_id: str, repo: ChunkRepository) -> None:
        self.project_id = project_id
        self._repo = repo
        self._chunks: list[TextChunk] = []
        self._embeddings: np.ndarray | None = None
        self._loaded_chapter: int = 0

    async def load(self) -> None:
        """从 SQLite 加载已有向量到内存."""
        chunks, embeddings = await self._repo.get_with_embeddings(self.project_id)
        self._chunks = chunks
        self._embeddings = embeddings
        total = len(chunks)
        emb_shape = embeddings.shape if embeddings is not None else None
        logger.info(
            "vector_store.loaded",
            project_id=self.project_id,
            total_chunks=total,
            embedding_shape=emb_shape,
        )
        if total > _CHUNK_WARNING_THRESHOLD:
            logger.warning(
                "vector_store.large_index",
                total_chunks=total,
                hint="考虑切换到 faiss",
            )

    async def load_incremental(self) -> None:
        """增量加载：首次全量加载，后续只加载新增 chunks 和 embeddings.

        保持 ``_chunks`` 与 ``_embeddings`` 索引严格一致，避免 RAG 检索时
        向量与文本错位。
        """
        if self._loaded_chapter == 0:
            await self.load()
            self._loaded_chapter = max((c.chapter_number for c in self._chunks), default=0)
            return

        all_chunks, all_embeddings = await self._repo.get_with_embeddings(self.project_id)
        if not all_chunks:
            return

        # 如果任一侧没有 embeddings，无法安全增量合并，回退到全量加载
        if all_embeddings is None or self._embeddings is None:
            await self.load()
            self._loaded_chapter = max((c.chapter_number for c in self._chunks), default=0)
            return

        existing_ids = {c.chunk_id for c in self._chunks}
        new_chunks: list[TextChunk] = []
        new_embeddings: list[np.ndarray] = []

        for chunk, embedding in zip(all_chunks, all_embeddings):
            if chunk.chunk_id not in existing_ids:
                new_chunks.append(chunk)
                new_embeddings.append(embedding)

        if not new_chunks:
            return

        self._chunks.extend(new_chunks)
        self._embeddings = np.vstack([self._embeddings, np.vstack(new_embeddings)])
        self._loaded_chapter = max((c.chapter_number for c in self._chunks), default=0)

    async def add_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: np.ndarray,
    ) -> None:
        """添加新章节的 chunks 和 embedding.

        Args:
            chunks: TextChunk 列表
            embeddings: (N, D) float32 数组
        """
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"chunks ({len(chunks)}) != embeddings ({embeddings.shape[0]})"
            )

        logger.info(
            "vector_store.add_start",
            project_id=self.project_id,
            chunk_count=len(chunks),
            embedding_shape=embeddings.shape,
        )

        # 写入 SQLite
        await self._repo.bulk_insert(chunks, embeddings)

        # 更新内存缓存
        self._chunks.extend(chunks)
        if self._embeddings is None:
            self._embeddings = embeddings.copy()
        else:
            self._embeddings = np.vstack([self._embeddings, embeddings])

        total = len(self._chunks)
        logger.info(
            "vector_store.add_done",
            project_id=self.project_id,
            total_chunks=total,
        )
        if total > _CHUNK_WARNING_THRESHOLD:
            logger.warning(
                "vector_store.large_index",
                total_chunks=total,
                hint="考虑切换到 faiss",
            )

    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[RetrievedChunk]:
        """余弦相似度检索，按章节去重（每章最多 1 个 chunk）.

        Args:
            query_embedding: (D,) 查询向量
            top_k: 最多返回结果数
            min_similarity: 最低相似度门槛

        Returns:
            RetrievedChunk 列表，按相似度降序
        """
        if self._embeddings is None or len(self._embeddings) == 0:
            return []

        # 向量已 L2 归一化，点积即余弦相似度
        similarities = self._embeddings @ query_embedding
        sorted_indices = np.argsort(similarities)[::-1]

        results: list[RetrievedChunk] = []
        seen_chapters: set[int] = set()
        for idx in sorted_indices:
            sim = float(similarities[idx])
            if sim < min_similarity:
                break
            ch = self._chunks[idx].chapter_number
            if ch in seen_chapters:
                continue
            seen_chapters.add(ch)
            chunk = self._chunks[idx]
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    chapter_number=ch,
                    similarity=sim,
                    metadata=chunk.metadata,
                )
            )
            if len(results) >= top_k:
                break

        return results

    async def delete_by_chapter(self, chapter_number: int) -> None:
        """删除指定章节的 chunks 并刷新内存."""
        await self._repo.delete_by_chapter(self.project_id, chapter_number)
        # 从内存中移除对应 chunks
        keep_indices = [
            i for i, c in enumerate(self._chunks)
            if c.chapter_number != chapter_number
        ]
        if keep_indices:
            self._chunks = [self._chunks[i] for i in keep_indices]
            self._embeddings = (
                self._embeddings[keep_indices] if self._embeddings is not None else None
            )
        else:
            self._chunks = []
            self._embeddings = None

    @property
    def total_chunks(self) -> int:
        """当前内存中的 chunk 总数."""
        return len(self._chunks)
