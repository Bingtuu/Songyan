"""VectorStore 单元测试."""

from __future__ import annotations

import numpy as np
import pytest

from songyan.db.chunk_repo import ChunkRepository
from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.models import ChapterVersion, ProjectSetting
from songyan.models.rag import ChunkMetadata, TextChunk
from songyan.rag.vector_store import VectorStore

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seeded_db(test_db) -> None:
    """创建项目和章节版本，满足外键约束."""
    project = ProjectSetting(
        title="Test",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="Alice",
    )
    await ProjectRepository().create(project, "proj1")
    for ch in range(1, 5):
        version = ChapterVersion(
            version_id=f"v{ch}",
            project_id="proj1",
            chapter_number=ch,
            version_number=1,
            version_type="accepted",
            content=f"chapter {ch} content",
        )
        await ChapterVersionRepository().create(version)


def _make_chunks(n: int, project_id: str = "proj1") -> list[TextChunk]:
    """创建测试 chunks."""
    chunks = []
    for i in range(n):
        ch_num = (i // 2) + 1  # 每章 2 个 chunk
        chunks.append(
            TextChunk(
                chunk_id=f"{project_id}_{ch_num}_{i % 2}",
                project_id=project_id,
                chapter_number=ch_num,
                version_id=f"v{ch_num}",
                chunk_index=i % 2,
                text=f"chunk text {i}",
                metadata=ChunkMetadata(),
            )
        )
    return chunks


def _make_embeddings(n: int, dim: int = 768) -> np.ndarray:
    """创建测试向量（L2 归一化）."""
    rng = np.random.default_rng(seed=42)
    emb = rng.random((n, dim)).astype(np.float32)
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    return emb / np.maximum(norms, 1e-9)


class TestVectorStore:
    """VectorStore 核心测试."""

    async def test_vector_store_add_and_search(self, test_db, seeded_db) -> None:
        """添加固定向量后，query 与自身相似度 ≈ 1.0."""
        store = VectorStore(project_id="proj1", repo=ChunkRepository())
        chunks = _make_chunks(4)
        embeddings = _make_embeddings(4)

        await store.add_chunks(chunks, embeddings)

        # 用第一个向量查询自己
        results = await store.search(embeddings[0], top_k=1)
        assert len(results) == 1
        assert results[0].chunk_id == chunks[0].chunk_id
        assert results[0].similarity > 0.99

    async def test_vector_store_chapter_dedup(self, test_db, seeded_db) -> None:
        """同一章多个高相似 chunk 只返回最高分的一个."""
        store = VectorStore(project_id="proj1", repo=ChunkRepository())
        chunks = _make_chunks(4)  # 2 章，每章 2 个 chunk
        embeddings = _make_embeddings(4)
        # 让第 0 和第 1 个向量非常接近（同章）
        embeddings[1] = embeddings[0] + np.random.normal(0, 0.01, 768).astype(np.float32)
        embeddings[1] /= np.linalg.norm(embeddings[1])

        await store.add_chunks(chunks, embeddings)

        results = await store.search(embeddings[0], top_k=5)
        # 应该有 2 个结果（2 章），不是 4 个
        chapter_counts = [r.chapter_number for r in results]
        assert len(set(chapter_counts)) == len(chapter_counts), "同一章不应出现两次"

    async def test_vector_store_min_similarity(self, test_db, seeded_db) -> None:
        """低于门槛的结果被过滤."""
        store = VectorStore(project_id="proj1", repo=ChunkRepository())
        chunks = _make_chunks(2)
        embeddings = _make_embeddings(2)

        await store.add_chunks(chunks, embeddings)

        # 用一个无关向量查询（随机生成）
        query = np.random.random(768).astype(np.float32)
        query /= np.linalg.norm(query)
        results = await store.search(query, top_k=5, min_similarity=0.99)
        assert results == []

    async def test_vector_store_empty_search(self, test_db) -> None:
        """空存储返回空列表."""
        store = VectorStore(project_id="proj1", repo=ChunkRepository())
        query = np.ones(768, dtype=np.float32) / np.sqrt(768)
        results = await store.search(query)
        assert results == []

    async def test_vector_store_persistence(self, test_db, seeded_db) -> None:
        """写入后 reload，搜索结果一致."""
        repo = ChunkRepository()
        store = VectorStore(project_id="proj1", repo=repo)
        chunks = _make_chunks(3)
        embeddings = _make_embeddings(3)

        await store.add_chunks(chunks, embeddings)
        results1 = await store.search(embeddings[0], top_k=3)

        # 新建 VectorStore 实例，从 DB reload
        store2 = VectorStore(project_id="proj1", repo=repo)
        await store2.load()
        results2 = await store2.search(embeddings[0], top_k=3)

        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.chunk_id == r2.chunk_id
            assert abs(r1.similarity - r2.similarity) < 1e-5

    async def test_vector_store_delete_by_chapter(self, test_db, seeded_db) -> None:
        """删除后该章节 chunks 为空."""
        store = VectorStore(project_id="proj1", repo=ChunkRepository())
        chunks = _make_chunks(4)
        embeddings = _make_embeddings(4)

        await store.add_chunks(chunks, embeddings)
        await store.delete_by_chapter(1)

        query = embeddings[0]
        results = await store.search(query, top_k=5)
        assert not any(r.chapter_number == 1 for r in results)
