"""RAG 检索器 — Query 构造 + 向量检索."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from songyan.models.chapter import ChapterGoal
from songyan.models.context import RecentPlot
from songyan.models.rag import RAGConfig, RetrievedChunk
from songyan.rag.embedder import Embedder
from songyan.rag.vector_store import VectorStore

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# 元指令关键词 — 不含实体信息，应排除
_META_INSTRUCTION_PATTERNS = {
    "必须精彩",
    "节奏不能慢",
    "节奏要快",
    "必须吸引人",
    "不能平淡",
    "要有张力",
    "要有冲突",
    "要精彩",
    "要紧凑",
    "本章必须",
    "确保",
    "注意",
    "切记",
    "务必",
}


def _is_meta_instruction(text: str) -> bool:
    """判断 obligations 中的某条是否为元指令（不含实体信息）."""
    for pattern in _META_INSTRUCTION_PATTERNS:
        if pattern in text:
            return True
    # 纯感叹/评价性语句（无名词实体）也视为元指令
    if len(text) < 10 and ("!" in text or "！" in text or "要" in text):
        return True
    return False


class RAGRetriever:
    _store_cache: dict = {}

    """RAG 检索器 — 封装 query 构造、编码、检索全流程."""

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        rag_config: RAGConfig,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.rag_config = rag_config

    def build_query(
        self,
        chapter_goal: ChapterGoal,
        recent_plot: RecentPlot | None = None,
    ) -> str:
        """从章节目标和最近剧情构造检索 query.

        加权策略:
        1. target_events 重复一次（利用 mean pooling 自然加权）
        2. obligations 过滤元指令后追加
        3. 最近剧情摘要追加
        """
        parts: list[str] = []

        # target_events 重复 = 自然加权
        for event in (chapter_goal.target_events or []):
            parts.append(event)
            parts.append(event)

        # obligations 过滤元指令
        for obligation in (chapter_goal.obligations or []):
            if not _is_meta_instruction(obligation):
                parts.append(obligation)

        # 最近剧情摘要
        if recent_plot and recent_plot.summaries:
            last_summary = recent_plot.summaries[-1].summary
            if last_summary:
                parts.append(last_summary)

        return " ".join(parts)

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievedChunk]:
        """编码 query 并执行向量检索.

        Args:
            query: 检索查询文本
            top_k: 最多返回结果数（默认从 rag_config）
            min_similarity: 最低相似度门槛（默认从 rag_config）

        Returns:
            RetrievedChunk 列表
        """
        top_k = top_k or self.rag_config.max_results
        min_similarity = min_similarity or self.rag_config.min_similarity

        if not query.strip():
            return []

        try:
            query_embedding = await self.embedder.aembed([query])
            results = await self.vector_store.search(
                query_embedding=query_embedding[0],
                top_k=top_k,
                min_similarity=min_similarity,
            )
            return results
        except Exception as exc:
            logger.warning(
                "rag.retrieve_failed",
                error=str(exc),
                query_preview=query[:100],
            )
            return []

    async def retrieve_for_chapter(
        self,
        project_id: str,
        chapter_number: int,
        chapter_goal: ChapterGoal,
        recent_plot: RecentPlot | None = None,
    ) -> list[RetrievedChunk]:
        """为指定章节执行完整 RAG 检索.

        步骤:
        1. 从 SQLite 加载向量索引
        2. 构造 query
        3. 编码 + 检索
        4. 若结果为空，降级到关键词匹配
        """
        try:
            cache_key = self.vector_store.project_id
            if cache_key in self._store_cache:
                cached = self._store_cache[cache_key]
                await cached.load_incremental()
                # 让当前 retriever 的后续检索走缓存实例，避免重复全量加载
                self.vector_store = cached
            else:
                await self.vector_store.load()
                self._store_cache[cache_key] = self.vector_store
        except Exception as exc:
            logger.warning(
                "rag.vector_store_load_failed",
                error=str(exc),
                project_id=project_id,
                chapter_number=chapter_number,
            )
            return []

        query = self.build_query(chapter_goal, recent_plot)
        logger.info(
            "rag.query_built",
            project_id=project_id,
            chapter_number=chapter_number,
            query_length=len(query),
        )

        results = await self.retrieve(query)

        # 降级策略：若向量检索结果为空或质量过低，尝试关键词匹配
        if not results or all(r.similarity < 0.4 for r in results):
            try:
                fallback = await self._keyword_fallback(chapter_goal, recent_plot)
                if fallback:
                    logger.info(
                        "rag.keyword_fallback",
                        project_id=project_id,
                        chapter_number=chapter_number,
                        fallback_count=len(fallback),
                    )
                    # 合并，去重（优先保留向量检索结果）
                    seen = {r.chunk_id for r in results}
                    for r in fallback:
                        if r.chunk_id not in seen:
                            results.append(r)
                    results.sort(key=lambda x: x.similarity, reverse=True)
                    results = results[: self.rag_config.max_results]
            except Exception as exc:
                logger.warning(
                    "rag.keyword_fallback_failed",
                    error=str(exc),
                    project_id=project_id,
                    chapter_number=chapter_number,
                )

        logger.info(
            "rag.retrieved",
            project_id=project_id,
            chapter_number=chapter_number,
            result_count=len(results),
        )
        return results

    async def _keyword_fallback(
        self,
        chapter_goal: ChapterGoal,
        recent_plot: RecentPlot | None,
    ) -> list[RetrievedChunk]:
        """关键词降级检索 — 对上一章全文做简单关键词匹配.

        简化实现：从 vector_store 的内存缓存中扫描包含 target_events 关键词的 chunks。
        """
        keywords = list(chapter_goal.target_events or [])
        if not keywords:
            return []

        fallback_results: list[RetrievedChunk] = []
        for chunk in self.vector_store._chunks:
            score = 0.0
            for kw in keywords:
                if kw in chunk.text:
                    score += 0.25  # 每个匹配关键词 +0.25
            if score > 0:
                fallback_results.append(
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        text=chunk.text,
                        chapter_number=chunk.chapter_number,
                        similarity=min(score, 0.95),
                        metadata=chunk.metadata,
                    )
                )

        fallback_results.sort(key=lambda x: x.similarity, reverse=True)
        return fallback_results[: self.rag_config.max_results]
