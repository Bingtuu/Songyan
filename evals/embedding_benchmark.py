"""Embedding 模型基准测试框架 — Task 048."""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import os
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from evals.chunking import Chunker, ChunkerConfig, ChapterChunk
from evals.metrics import (
    BenchmarkMetrics,
    RetrievalMetrics,
    aggregate_metrics,
    compute_retrieval_metrics,
)
from evals.queries import BenchmarkQuery, DEFAULT_QUERIES


@dataclass
class SearchResult:
    """单次检索结果."""

    chunk: ChapterChunk
    score: float
    rank: int


@dataclass
class BenchmarkConfig:
    """基准测试配置（可序列化复现）."""

    model_name: str
    project_id: str
    chapters_dir: str
    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k_values: list[int] = field(default_factory=lambda: [1, 3, 5])
    device: str = "cpu"
    queries: list[BenchmarkQuery] = field(default_factory=list)


@dataclass
class PerQueryResult:
    """单个查询的详细结果."""

    query: str
    query_type: str
    expected_chapters: list[int]
    hit_at_k: dict[str, bool]
    reciprocal_rank: float
    top_results: list[dict[str, Any]]


@dataclass
class BenchmarkReport:
    """完整评估报告."""

    model_name: str
    chunk_size: int
    chunk_overlap: int
    total_chunks: int
    top1_hit_rate: float
    top3_hit_rate: float
    top5_hit_rate: float
    mrr: float
    avg_latency_ms: float
    peak_memory_mb: float
    avg_first_hit_similarity: float
    avg_max_similarity: float
    per_query_results: list[PerQueryResult]

    def to_markdown(self) -> str:
        """生成 Markdown 格式报告."""
        lines = [
            "# Embedding 模型基准测试报告",
            "",
            f"**模型**: {self.model_name}",
            f"**Chunk 大小**: {self.chunk_size} 字",
            f"**Chunk 重叠**: {self.chunk_overlap} 字",
            f"**总 Chunks**: {self.total_chunks}",
            "",
            "## 汇总指标",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| Top-1 命中率 | {self.top1_hit_rate:.1%} |",
            f"| Top-3 命中率 | {self.top3_hit_rate:.1%} |",
            f"| Top-5 命中率 | {self.top5_hit_rate:.1%} |",
            f"| MRR | {self.mrr:.3f} |",
            f"| 平均首命中相似度 | {self.avg_first_hit_similarity:.3f} |",
            f"| 平均最大相似度 | {self.avg_max_similarity:.3f} |",
            f"| 平均查询延迟 | {self.avg_latency_ms:.1f} ms |",
            f"| 峰值内存 | {self.peak_memory_mb:.1f} MB |",
            "",
            "## 逐查询结果",
            "",
            "| 查询 | 类型 | 期望章节 | Top-1 | Top-3 | Top-5 | MRR | 首命中相似度 |",
            "|------|------|----------|-------|-------|-------|-----|-------------|",
        ]
        for r in self.per_query_results:
            hit = r.hit_at_k
            first_score = r.top_results[0].get("score", 0.0) if r.top_results else 0.0
            lines.append(
                f"| {r.query} | {r.query_type} | {r.expected_chapters} | "
                f"{'✅' if hit.get('top1') else '❌'} | "
                f"{'✅' if hit.get('top3') else '❌'} | "
                f"{'✅' if hit.get('top5') else '❌'} | "
                f"{r.reciprocal_rank:.3f} | "
                f"{first_score:.3f} |"
            )
        lines.append("")
        lines.append("---")
        lines.append(f"*报告生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*")
        return "\n".join(lines)


class Embedder:
    """Embedding 模型封装 — 支持真实模型和 Mock 模式."""

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        lazy_load: bool = True,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self._model: Any = None
        self._dimension = 0
        self._lazy_load = lazy_load
        if not lazy_load:
            self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        """懒加载模型."""
        if self._model is not None:
            return

        if self.model_name == "mock":
            self._dimension = 384
            return

        import torch

        # BGE-M3 因模型过大（2.3GB），在当前环境需特殊处理
        if "bge-m3" in self.model_name.lower():
            from transformers import AutoModel, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name).to(self.device)
            self._model.eval()
            self._dimension = 1024
            return

        # 其他 BGE 系列（bge-large-zh / bge-base-zh 等）用 sentence-transformers 全精度加载
        if "bge-" in self.model_name.lower():
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
            self._dimension = self._model.get_sentence_embedding_dimension()
            return

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name, device=self.device)
        self._dimension = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        self._ensure_loaded()
        return self._dimension

    def encode(self, texts: list[str]) -> np.ndarray:
        """同步编码（调用方负责线程池包装）."""
        self._ensure_loaded()
        if self.model_name == "mock":
            # Mock: 固定随机向量 + 文本哈希偏移，保证同一文本相同向量
            rng = np.random.default_rng(seed=42)
            base = rng.random((len(texts), self._dimension)).astype(np.float32)
            for i, text in enumerate(texts):
                base[i] += hash(text) % 1000 / 10000
            # L2 normalize
            norms = np.linalg.norm(base, axis=1, keepdims=True)
            return base / norms

        # BGE-M3 via transformers direct
        if hasattr(self, "_tokenizer"):
            import torch

            inputs = self._tokenizer(
                texts,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512,
            ).to(self.device)
            with torch.no_grad():
                outputs = self._model(**inputs)
            # Mean pooling
            attention_mask = inputs["attention_mask"]
            last_hidden = outputs.last_hidden_state
            mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
            sum_embeddings = torch.sum(last_hidden * mask_expanded, dim=1)
            sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
            embeddings = sum_embeddings / sum_mask
            # L2 normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            return embeddings.cpu().numpy().astype(np.float32)

        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)

    async def embed(self, texts: list[str]) -> np.ndarray:
        """异步编码 — 在线程池中执行同步 encode."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.encode, texts)


class InMemoryVectorStore:
    """内存向量存储 — SQLite 元数据 + numpy 数组."""

    def __init__(self) -> None:
        self.chunks: list[ChapterChunk] = []
        self.embeddings: np.ndarray | None = None

    def add_chunks(self, chunks: list[ChapterChunk], embeddings: np.ndarray) -> None:
        """添加 chunks 和对应向量."""
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"chunks ({len(chunks)}) != embeddings ({embeddings.shape[0]})")

        self.chunks.extend(chunks)
        if self.embeddings is None:
            self.embeddings = embeddings.copy()
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[SearchResult]:
        """余弦相似度检索，按章节去重（每章最多 1 个 chunk）."""
        if self.embeddings is None or len(self.embeddings) == 0:
            return []

        # 计算余弦相似度（向量已归一化，点积即相似度）
        similarities = self.embeddings @ query_embedding
        sorted_indices = np.argsort(similarities)[::-1]

        results: list[SearchResult] = []
        seen_chapters: set[int] = set()
        rank = 1
        for idx in sorted_indices:
            sim = float(similarities[idx])
            if sim < min_similarity:
                break
            ch = self.chunks[idx].chapter_num
            if ch in seen_chapters:
                continue
            seen_chapters.add(ch)
            results.append(
                SearchResult(
                    chunk=self.chunks[idx],
                    score=sim,
                    rank=rank,
                )
            )
            rank += 1
            if len(results) >= top_k:
                break

        return results


class EmbeddingBenchmark:
    """Embedding 模型基准测试框架."""

    def __init__(
        self,
        model_name: str,
        project_id: str,
        chapters_dir: str,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        device: str = "cpu",
        queries: list[BenchmarkQuery] | None = None,
    ) -> None:
        self.config = BenchmarkConfig(
            model_name=model_name,
            project_id=project_id,
            chapters_dir=chapters_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            device=device,
            queries=queries or DEFAULT_QUERIES,
        )
        self.chunker = Chunker(ChunkerConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap))
        self.embedder = Embedder(model_name=model_name, device=device)
        self.vector_store = InMemoryVectorStore()

    def load_chapters(self) -> list[ChapterChunk]:
        """从项目章节目录加载并切分."""
        return self.chunker.chunk_project_chapters(
            self.config.chapters_dir,
            project_id=self.config.project_id,
        )

    async def build_index(self, chunks: list[ChapterChunk]) -> None:
        """计算 embedding 并构建内存索引."""
        if not chunks:
            return

        texts = [c.text for c in chunks]
        embeddings = await self.embedder.embed(texts)
        self.vector_store.add_chunks(chunks, embeddings)

    async def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """执行检索."""
        query_emb = await self.embedder.embed([query])
        return self.vector_store.search(query_emb[0], top_k=top_k)

    async def run_benchmark(self) -> BenchmarkReport:
        """运行完整基准测试."""
        # 加载并索引
        chunks = self.load_chapters()
        await self.build_index(chunks)

        # 内存基准
        tracemalloc.start()
        baseline_mem = tracemalloc.get_traced_memory()[1] / 1024 / 1024

        per_query_metrics: list[RetrievalMetrics] = []
        per_query_results: list[PerQueryResult] = []
        latencies_ms: list[float] = []

        for q in self.config.queries:
            start = time.perf_counter()
            results = await self.search(q.query, top_k=5)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(latency_ms)

            result_chapters = [r.chunk.chapter_num for r in results]
            similarities = [r.score for r in results]

            metrics = compute_retrieval_metrics(
                result_chapters, similarities, q.expected_chapters
            )
            per_query_metrics.append(metrics)

            top_results = [
                {
                    "chapter": r.chunk.chapter_num,
                    "score": round(r.score, 3),
                    "text_preview": r.chunk.text[:80] + "...",
                }
                for r in results[:3]
            ]

            per_query_results.append(
                PerQueryResult(
                    query=q.query,
                    query_type=q.query_type,
                    expected_chapters=q.expected_chapters,
                    hit_at_k={
                        "top1": metrics.top1_hit,
                        "top3": metrics.top3_hit,
                        "top5": metrics.top5_hit,
                    },
                    reciprocal_rank=metrics.reciprocal_rank,
                    top_results=top_results,
                )
            )

        peak_mem = tracemalloc.get_traced_memory()[1] / 1024 / 1024
        tracemalloc.stop()
        peak_memory_mb = peak_mem - baseline_mem

        agg = aggregate_metrics(per_query_metrics, latencies_ms, peak_memory_mb)

        return BenchmarkReport(
            model_name=self.config.model_name,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            total_chunks=len(chunks),
            top1_hit_rate=agg.top1_hit_rate,
            top3_hit_rate=agg.top3_hit_rate,
            top5_hit_rate=agg.top5_hit_rate,
            mrr=agg.mrr,
            avg_latency_ms=agg.avg_latency_ms,
            peak_memory_mb=agg.peak_memory_mb,
            avg_first_hit_similarity=agg.avg_first_hit_similarity,
            avg_max_similarity=agg.avg_max_similarity,
            per_query_results=per_query_results,
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Embedding 模型基准测试")
    parser.add_argument("--model", default="mock", help="模型名称或 'mock'")
    parser.add_argument("--project-id", default="orbital_horror", help="项目 ID")
    parser.add_argument(
        "--chapters-dir",
        default="projects/orbital_horror/chapters",
        help="章节目录",
    )
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--chunk-overlap", type=int, default=100)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output-json", help="JSON 输出路径")
    parser.add_argument("--output-md", help="Markdown 报告路径")
    args = parser.parse_args()

    benchmark = EmbeddingBenchmark(
        model_name=args.model,
        project_id=args.project_id,
        chapters_dir=args.chapters_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        device=args.device,
    )

    report = await benchmark.run_benchmark()

    print(f"模型: {report.model_name}")
    print(f"总 Chunks: {report.total_chunks}")
    print(f"Top-1 命中率: {report.top1_hit_rate:.1%}")
    print(f"Top-3 命中率: {report.top3_hit_rate:.1%}")
    print(f"Top-5 命中率: {report.top5_hit_rate:.1%}")
    print(f"MRR: {report.mrr:.3f}")
    print(f"平均延迟: {report.avg_latency_ms:.1f} ms")
    print(f"峰值内存: {report.peak_memory_mb:.1f} MB")

    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(asdict(report), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"JSON 报告已保存: {args.output_json}")

    if args.output_md:
        Path(args.output_md).write_text(report.to_markdown(), encoding="utf-8")
        print(f"Markdown 报告已保存: {args.output_md}")


if __name__ == "__main__":
    asyncio.run(main())
