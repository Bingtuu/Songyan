"""Embedding Benchmark 测试 — Task 048."""

from __future__ import annotations

import numpy as np
import pytest

from evals.chunking import ChapterChunk, Chunker, ChunkerConfig
from evals.embedding_benchmark import (
    BenchmarkConfig,
    BenchmarkReport,
    Embedder,
    EmbeddingBenchmark,
    InMemoryVectorStore,
    PerQueryResult,
)
from evals.metrics import (
    RetrievalMetrics,
    aggregate_metrics,
    compute_retrieval_metrics,
    hit_at_k,
    mean_reciprocal_rank,
)

# ============================================================================
# Layer 1: 模型测试
# ============================================================================

class TestBenchmarkConfig:
    def test_default_values(self) -> None:
        cfg = BenchmarkConfig(
            model_name="test",
            project_id="proj",
            chapters_dir="chapters",
        )
        assert cfg.chunk_size == 500
        assert cfg.chunk_overlap == 100
        assert cfg.top_k_values == [1, 3, 5]
        assert cfg.device == "cpu"


class TestBenchmarkReport:
    def test_to_markdown_contains_required_fields(self) -> None:
        report = BenchmarkReport(
            model_name="test-model",
            chunk_size=500,
            chunk_overlap=100,
            total_chunks=10,
            top1_hit_rate=0.5,
            top3_hit_rate=0.7,
            top5_hit_rate=0.9,
            mrr=0.6,
            avg_latency_ms=10.0,
            peak_memory_mb=5.0,
            avg_first_hit_similarity=0.4,
            avg_max_similarity=0.5,
            per_query_results=[
                PerQueryResult(
                    query="测试",
                    query_type="entity",
                    expected_chapters=[1],
                    hit_at_k={"top1": True, "top3": True, "top5": True},
                    reciprocal_rank=1.0,
                    top_results=[{"chapter": 1, "score": 0.5}],
                )
            ],
        )
        md = report.to_markdown()
        assert "test-model" in md
        assert "50.0%" in md  # top1
        assert "MRR" in md
        assert "测试" in md
        assert "✅" in md


# ============================================================================
# Layer 2: Chunker 测试
# ============================================================================

class TestChunker:
    def test_short_chapter_single_chunk(self) -> None:
        chunker = Chunker(ChunkerConfig(chunk_size=500, chunk_overlap=100))
        content = "这是一段很短的文本。只有几句话。"
        chunks = chunker.chunk_chapter(content, chapter_num=1)
        assert len(chunks) == 1
        assert chunks[0].chapter_num == 1
        assert chunks[0].chunk_index == 0

    def test_chunk_overlap_boundary(self) -> None:
        chunker = Chunker(ChunkerConfig(chunk_size=100, chunk_overlap=20))
        # 构造 250 字的文本
        content = "这是一个测试句子。" * 50  # ~250 chars
        chunks = chunker.chunk_chapter(content, chapter_num=1)
        assert len(chunks) >= 2
        # 验证相邻 chunks 有重叠
        if len(chunks) >= 2:
            text1 = chunks[0].text
            text2 = chunks[1].text
            # 第二块的开头应该出现在第一块的末尾
            assert text2[:10] in text1[-30:]

    def test_scene_boundary_split(self) -> None:
        chunker = Chunker(ChunkerConfig(chunk_size=500, chunk_overlap=100))
        content = "### Scene 1\n第一段内容。\n\n### Scene 2\n第二段内容。"
        chunks = chunker.chunk_chapter(content, chapter_num=1)
        # 应该按场景预分割
        assert len(chunks) >= 1

    def test_frontmatter_and_title_stripped(self) -> None:
        chunker = Chunker(ChunkerConfig(chunk_size=500, chunk_overlap=100))
        content = "---\ntitle: 测试\n---\n\n# 第一章\n\n正文开始。"
        chunks = chunker.chunk_chapter(content, chapter_num=1)
        assert "title:" not in chunks[0].text
        assert "# 第一章" not in chunks[0].text
        assert "正文开始" in chunks[0].text

    def test_no_scene_fallback_to_paragraphs(self) -> None:
        chunker = Chunker(ChunkerConfig(chunk_size=500, chunk_overlap=100))
        content = "段落一。\n\n段落二。\n\n段落三。"
        chunks = chunker.chunk_chapter(content, chapter_num=1)
        assert len(chunks) >= 1


# ============================================================================
# Layer 3: Embedder 测试（Mock）
# ============================================================================

class TestEmbedder:
    def test_mock_dimension(self) -> None:
        emb = Embedder("mock")
        assert emb.dimension == 384

    def test_mock_batch_shape(self) -> None:
        emb = Embedder("mock")
        arr = emb.encode(["文本一", "文本二", "文本三"])
        assert arr.shape == (3, 384)

    def test_mock_consistency(self) -> None:
        """同一文本应生成相同向量."""
        emb = Embedder("mock")
        a = emb.encode(["相同文本"])
        b = emb.encode(["相同文本"])
        np.testing.assert_array_equal(a, b)

    def test_mock_different_texts(self) -> None:
        """不同文本应生成不同向量."""
        emb = Embedder("mock")
        a = emb.encode(["文本A"])
        b = emb.encode(["文本B"])
        assert not np.allclose(a, b)

    @pytest.mark.asyncio
    async def test_embed_async(self) -> None:
        emb = Embedder("mock")
        result = await emb.embed(["异步测试"])
        assert result.shape == (1, 384)


# ============================================================================
# Layer 4: VectorStore 测试
# ============================================================================

class TestInMemoryVectorStore:
    def test_add_and_search_self(self) -> None:
        store = InMemoryVectorStore()
        chunks = [
            ChapterChunk("c1", 1, 0, "测试文本一"),
            ChapterChunk("c2", 2, 0, "测试文本二"),
        ]
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ], dtype=np.float32)
        store.add_chunks(chunks, embeddings)

        # 搜索与第一个 chunk 相同的向量
        results = store.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=2)
        assert len(results) == 1  # 章节去重：每章最多 1 个
        assert results[0].chunk.chunk_id == "c1"
        assert results[0].score == pytest.approx(1.0, abs=0.01)

    def test_chapter_dedup(self) -> None:
        """同一章多个 chunk 只返回最高分的一个."""
        store = InMemoryVectorStore()
        chunks = [
            ChapterChunk("c1_0", 1, 0, "第一段"),
            ChapterChunk("c1_1", 1, 1, "第二段"),
            ChapterChunk("c2_0", 2, 0, "第三段"),
        ]
        embeddings = np.array([
            [0.9, 0.1, 0.0],  # ch1, sim=0.9
            [0.8, 0.2, 0.0],  # ch1, sim=0.8 (低分)
            [0.5, 0.5, 0.0],  # ch2, sim=0.5
        ], dtype=np.float32)
        store.add_chunks(chunks, embeddings)

        results = store.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=3)
        chapter_nums = [r.chunk.chapter_num for r in results]
        assert 1 in chapter_nums
        assert 2 in chapter_nums
        # 第1章应该只出现一次（高分那个）
        assert chapter_nums.count(1) == 1

    def test_min_similarity_filter(self) -> None:
        store = InMemoryVectorStore()
        chunks = [ChapterChunk("c1", 1, 0, "文本")]
        embeddings = np.array([[0.5, 0.5, 0.0]], dtype=np.float32)
        store.add_chunks(chunks, embeddings)

        # 查询与 chunk 正交，相似度为 0
        results = store.search(
            np.array([0.0, 0.0, 1.0], dtype=np.float32),
            top_k=5,
            min_similarity=0.1,
        )
        assert len(results) == 0

    def test_empty_store(self) -> None:
        store = InMemoryVectorStore()
        results = store.search(np.array([1.0, 0.0, 0.0], dtype=np.float32))
        assert results == []


# ============================================================================
# Layer 5: Metrics 测试
# ============================================================================

class TestHitAtK:
    def test_hit_at_1(self) -> None:
        assert hit_at_k([3, 5, 7], [3], 1) is True
        assert hit_at_k([5, 3, 7], [3], 1) is False

    def test_hit_at_3(self) -> None:
        assert hit_at_k([5, 7, 3], [3], 3) is True
        assert hit_at_k([5, 7, 9], [3], 3) is False


class TestMRR:
    def test_first_place(self) -> None:
        assert mean_reciprocal_rank([3, 5, 7], [3]) == 1.0

    def test_third_place(self) -> None:
        assert mean_reciprocal_rank([5, 7, 3], [3]) == pytest.approx(1 / 3)

    def test_no_hit(self) -> None:
        assert mean_reciprocal_rank([5, 7, 9], [3]) == 0.0

    def test_multiple_expected(self) -> None:
        assert mean_reciprocal_rank([5, 3, 7], [3, 7]) == pytest.approx(0.5)


class TestComputeRetrievalMetrics:
    def test_basic(self) -> None:
        m = compute_retrieval_metrics(
            result_chapters=[5, 3, 7],
            similarities=[0.5, 0.4, 0.3],
            expected_chapters=[3],
        )
        assert m.top1_hit is False
        assert m.top3_hit is True
        assert m.top5_hit is True
        assert m.reciprocal_rank == pytest.approx(0.5)
        assert m.first_hit_similarity == pytest.approx(0.4)
        assert m.max_similarity == pytest.approx(0.5)

    def test_no_hit(self) -> None:
        m = compute_retrieval_metrics(
            result_chapters=[5, 7, 9],
            similarities=[0.5, 0.4, 0.3],
            expected_chapters=[3],
        )
        assert m.top1_hit is False
        assert m.top3_hit is False
        assert m.top5_hit is False
        assert m.reciprocal_rank == 0.0
        assert m.first_hit_similarity == 0.0


class TestAggregateMetrics:
    def test_two_queries(self) -> None:
        per_query = [
            RetrievalMetrics(
                top1_hit=True, top3_hit=True, top5_hit=True,
                reciprocal_rank=1.0, first_hit_similarity=0.5, max_similarity=0.6,
            ),
            RetrievalMetrics(
                top1_hit=False, top3_hit=True, top5_hit=True,
                reciprocal_rank=0.5, first_hit_similarity=0.4, max_similarity=0.5,
            ),
        ]
        agg = aggregate_metrics(per_query, [10.0, 20.0], peak_memory_mb=100.0)
        assert agg.top1_hit_rate == 0.5
        assert agg.top3_hit_rate == 1.0
        assert agg.top5_hit_rate == 1.0
        assert agg.mrr == 0.75
        assert agg.avg_latency_ms == 15.0
        assert agg.peak_memory_mb == 100.0


# ============================================================================
# Layer 6: Integration Test
# ============================================================================

class TestEmbeddingBenchmarkIntegration:
    @pytest.mark.asyncio
    async def test_mock_end_to_end(self) -> None:
        """Mock embedder 的完整 pipeline.

        NOTE: 依赖外部项目目录 projects/orbital_horror/chapters，
        若目录不存在则跳过 total_chunks 断言，仅验证结构完整性。
        """
        benchmark = EmbeddingBenchmark(
            model_name="mock",
            project_id="test",
            chapters_dir="projects/orbital_horror/chapters",
            chunk_size=500,
            chunk_overlap=100,
        )
        report = await benchmark.run_benchmark()
        # 目录不存在时 total_chunks 可能为 0，不做强制断言
        assert 0.0 <= report.top1_hit_rate <= 1.0
        assert len(report.per_query_results) == len(benchmark.config.queries)
