"""RAGRetriever 测试."""

from __future__ import annotations

import pytest

from songyan.models.chapter import ChapterGoal
from songyan.models.context import ChapterSummary, RecentPlot
from songyan.models.rag import ChunkMetadata, RAGConfig, TextChunk
from songyan.rag.embedder import Embedder
from songyan.rag.retriever import RAGRetriever
from songyan.rag.vector_store import VectorStore


class _MockChunkRepo:
    """Mock ChunkRepository for testing."""

    def __init__(self, chunks=None, embeddings=None):
        self._chunks = chunks or []
        self._embeddings = embeddings

    async def get_with_embeddings(self, project_id):
        return self._chunks, self._embeddings

    async def bulk_insert(self, chunks, embeddings, conn=None):
        pass

    async def delete_by_chapter(self, project_id, chapter_number, conn=None):
        pass


class TestBuildQuery:
    """Query 构造测试."""

    def test_target_events_weighted(self) -> None:
        """target_events 应被重复（自然加权）."""
        retriever = RAGRetriever(
            embedder=Embedder("mock"),
            vector_store=None,  # type: ignore[arg-type]
            rag_config=RAGConfig(),
        )
        goal = ChapterGoal(
            chapter_number=1,
            target_events=["事件A", "事件B"],
            obligations=[],
        )
        query = retriever.build_query(goal)
        assert query.count("事件A") == 2
        assert query.count("事件B") == 2

    def test_obligations_included(self) -> None:
        """obligations 中的实体指令应被包含."""
        retriever = RAGRetriever(
            embedder=Embedder("mock"),
            vector_store=None,  # type: ignore[arg-type]
            rag_config=RAGConfig(),
        )
        goal = ChapterGoal(
            chapter_number=1,
            target_events=["事件A"],
            obligations=["方远舟必须出场", "揭示认知补丁的秘密"],
        )
        query = retriever.build_query(goal)
        assert "方远舟必须出场" in query
        assert "认知补丁" in query

    def test_meta_instructions_filtered(self) -> None:
        """元指令应被过滤."""
        retriever = RAGRetriever(
            embedder=Embedder("mock"),
            vector_store=None,  # type: ignore[arg-type]
            rag_config=RAGConfig(),
        )
        goal = ChapterGoal(
            chapter_number=1,
            target_events=["事件A"],
            obligations=["必须精彩", "节奏不能慢", "方远舟出场"],
        )
        query = retriever.build_query(goal)
        assert "必须精彩" not in query
        assert "节奏不能慢" not in query
        assert "方远舟出场" in query

    def test_recent_plot_appended(self) -> None:
        """最近剧情摘要应被追加."""
        retriever = RAGRetriever(
            embedder=Embedder("mock"),
            vector_store=None,  # type: ignore[arg-type]
            rag_config=RAGConfig(),
        )
        goal = ChapterGoal(
            chapter_number=1,
            target_events=["事件A"],
            obligations=[],
        )
        recent = RecentPlot(
            summaries=[
                ChapterSummary(chapter_number=1, summary="上一章剧情"),
            ]
        )
        query = retriever.build_query(goal, recent)
        assert "上一章剧情" in query

    def test_empty_goal(self) -> None:
        """空 goal 返回空字符串."""
        retriever = RAGRetriever(
            embedder=Embedder("mock"),
            vector_store=None,  # type: ignore[arg-type]
            rag_config=RAGConfig(),
        )
        goal = ChapterGoal(chapter_number=1)
        query = retriever.build_query(goal)
        assert query == ""


class TestRetrieve:
    """检索流程测试."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        Embedder.clear_cache()

    @pytest.mark.asyncio
    async def test_retrieve_mock(self) -> None:
        """Mock 向量检索流程."""
        embedder = Embedder("mock")
        # 创建测试 chunks 和 embeddings
        chunks = [
            TextChunk(
                chunk_id="c1", project_id="p1", chapter_number=1,
                version_id="v1", chunk_index=0, text="chunk one",
                metadata=ChunkMetadata(),
            ),
            TextChunk(
                chunk_id="c2", project_id="p1", chapter_number=2,
                version_id="v1", chunk_index=0, text="chunk two",
                metadata=ChunkMetadata(),
            ),
        ]
        embeddings = embedder.embed([c.text for c in chunks])
        repo = _MockChunkRepo(chunks, embeddings)
        store = VectorStore("p1", repo)  # type: ignore[arg-type]
        await store.load()

        retriever = RAGRetriever(
            embedder=embedder,
            vector_store=store,
            rag_config=RAGConfig(max_results=5, min_similarity=0.0),
        )

        results = await retriever.retrieve("chunk one", top_k=2)
        assert len(results) >= 1
        assert results[0].chunk_id == "c1"
        assert results[0].similarity > 0.99

    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self) -> None:
        """空查询返回空列表."""
        embedder = Embedder("mock")
        store = VectorStore("p1", _MockChunkRepo())  # type: ignore[arg-type]
        retriever = RAGRetriever(
            embedder=embedder,
            vector_store=store,
            rag_config=RAGConfig(),
        )
        results = await retriever.retrieve("")
        assert results == []


class TestRetrieveForChapter:
    """完整章节检索测试."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        Embedder.clear_cache()

    @pytest.mark.asyncio
    async def test_retrieve_for_chapter_full_flow(self) -> None:
        """完整流程：load → build query → embed → search."""
        embedder = Embedder("mock")
        chunks = [
            TextChunk(
                chunk_id="c1", project_id="p1", chapter_number=1,
                version_id="v1", chunk_index=0, text="认知补丁生效",
                metadata=ChunkMetadata(),
            ),
        ]
        embeddings = embedder.embed([c.text for c in chunks])
        repo = _MockChunkRepo(chunks, embeddings)
        store = VectorStore("p1", repo)  # type: ignore[arg-type]

        retriever = RAGRetriever(
            embedder=embedder,
            vector_store=store,
            rag_config=RAGConfig(max_results=5, min_similarity=0.0),
        )

        goal = ChapterGoal(
            chapter_number=2,
            target_events=["认知补丁"],
            obligations=[],
        )
        results = await retriever.retrieve_for_chapter(
            "p1", 2, goal, None
        )
        assert len(results) >= 1
        assert results[0].text == "认知补丁生效"


class TestCacheReuse:
    """VectorStore 跨 Retriever 实例缓存复用测试."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        Embedder.clear_cache()
        RAGRetriever._store_cache.clear()

    @pytest.mark.asyncio
    async def test_retriever_reuses_cached_store(self) -> None:
        """同一 project 的第二个 RAGRetriever 复用缓存实例，避免重复全量加载."""
        embedder = Embedder("mock")
        chunks = [
            TextChunk(
                chunk_id="c1", project_id="p1", chapter_number=1,
                version_id="v1", chunk_index=0, text="认知补丁生效",
                metadata=ChunkMetadata(),
            ),
        ]
        embeddings = embedder.embed([c.text for c in chunks])
        repo = _MockChunkRepo(chunks, embeddings)
        store1 = VectorStore("p1", repo)  # type: ignore[arg-type]

        retriever1 = RAGRetriever(
            embedder=embedder,
            vector_store=store1,
            rag_config=RAGConfig(max_results=5, min_similarity=0.0),
        )

        goal = ChapterGoal(
            chapter_number=2,
            target_events=["认知补丁"],
            obligations=[],
        )

        results1 = await retriever1.retrieve_for_chapter("p1", 2, goal)
        assert len(results1) >= 1
        cached_store = RAGRetriever._store_cache["p1"]
        assert retriever1.vector_store is cached_store

        # 第二个 retriever + 全新 store 实例，应复用缓存
        store2 = VectorStore("p1", repo)  # type: ignore[arg-type]
        retriever2 = RAGRetriever(
            embedder=embedder,
            vector_store=store2,
            rag_config=RAGConfig(max_results=5, min_similarity=0.0),
        )
        results2 = await retriever2.retrieve_for_chapter("p1", 2, goal)
        assert retriever2.vector_store is cached_store
        assert len(results2) >= 1
