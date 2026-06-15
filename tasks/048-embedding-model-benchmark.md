# Task 048 — Embedding 模型选型基准测试（BGE-M3 验证）

> **目标**: 评估并选定 Songyan RAG 自动层的 Embedding 模型，建立可复现的基准测试脚本与质量报告。  
> **Phase**: 8b  
> **优先级**: P0  
> **依赖**: 无  
> **预计工作量**: 中（2~3 天）

---

## Context

Phase 8 的 RAG 自动层是 D+B 混合架构的关键组成部分。Task 039 长程架构调研的 MVP 实验使用 `all-MiniLM-L6-v2`（384 维）对《轨道上的怪谈》Ch2~Ch11 进行了 RAG 原型测试，结果暴露出三个核心问题：

1. **中文专有名词检索效果差**: "认知补丁"、"第6代实验体" 等概念相似度普遍 < 0.5
2. **Chunk 切分导致上下文断裂**: "电磁干扰器" 和 "120 赫兹" 分散在不同 chunk，无法联合检索
3. **无结构化过滤**: Top-5 结果常混入无关段落

调研报告明确建议："使用中文专用 embedding 模型（如 **BGE-M3**）"。本 Task 负责将该建议落地为可量化的选型决策。

**BGE-M3 优势预期**: 
- 多语言（中英）支持，对中文专有名词语义理解优于 MiniLM
- 1024 维向量，表达力更强
- 支持稠密向量 + 稀疏向量（lexical）混合检索，可缓解 "电磁干扰器" 与 "120 赫兹" 分散问题
- 本地运行，无 API 成本，与 Songyan "本地优先" 的架构原则一致

**对比候选**:
| 模型 | 维度 | 类型 | 本地/云 | 关注点 |
|------|------|------|---------|--------|
| BGE-M3 | 1024 | 稠密+稀疏 | 本地 | 主选，中文优化 |
| OpenAI text-embedding-3-small | 1536 | 稠密 | 云 | 对照组，质量 vs 成本 |
| all-MiniLM-L6-v2 | 384 | 稠密 | 本地 | 基线（Task 039 MVP 已验证，效果差） |

---

## Goal

建立一套**可复现的 Embedding 模型基准测试框架**，在 Songyan 的真实项目数据（《轨道上的怪谈》Ch2~Ch11）上量化评估 BGE-M3 的检索质量与性能，输出选型报告，为 Task 049 的 Chunker/Embedder 实现提供模型决策依据。

---

## In Scope（必须完成）

- [ ] **基准测试脚本** `evals/embedding_benchmark.py`
  - 自动加载项目章节文本（通过 `ChapterVersionRepository` 从 SQLite `chapter_versions` 表读取已接受的版本正文）
  - 统一的 chunking 策略（500 字 / chunk，100 字重叠，与 Task 039 MVP 一致，便于对比）
  - 元数据标注：章节号、chunk 序号、是否为章节边界
  - 支持多模型切换：BGE-M3、MiniLM（基线）、可选 OpenAI（云对照）
  
- [ ] **查询集定义**
  - 复用 Task 039 的 4 个核心查询："认知补丁", "第6代实验体", "120Hz干扰器", "守门人"
  - 新增 6 个扩展查询（覆盖：设定、人物、道具、伏笔、场景、情绪）
  - 每个查询标注：期望命中章节、查询类型（entity/relationship/semantic）
  
- [ ] **评估指标计算**
  - **Top-k 命中率**（k=1,3,5）：返回的 chunk 中是否包含期望章节
  - **MRR**（Mean Reciprocal Rank）
  - **语义相似度分布**：命中 vs 未命中的相似度均值/方差
  - **检索延迟**：单次查询平均耗时（本地 CPU / GPU）
  - **模型加载内存**：峰值 RSS
  
- [ ] **BGE-M3 专项验证**
  - 稠密向量检索基准测试（主项）
  - 验证 "电磁干扰器" + "120 赫兹" 分散 chunk 的召回改善
  - 不同 chunk 重叠度（0 / 100 / 200 字）对上下文断裂的缓解效果
  - ~~稀疏向量检索 vs 混合检索（0.5:0.5）对比~~（加分项，Task 049 暂不支持稀疏向量）
  
- [ ] **选型报告** `docs/review/embedding_benchmark_report.md`
  - 量化对比表格（BGE-M3 vs MiniLM vs OpenAI）
  - BGE-M3 的 chunking 与检索参数推荐（overlap / 混合权重 / Top-k）
  - 性能基线：CPU 下单次查询 < 200ms，模型加载 < 8GB RAM
  - 明确结论：是否选定 BGE-M3 作为 Phase 8b 默认模型

---

## Out of Scope（明确不做）

- 不实现 VectorStore 持久化（SQLite / Chroma / FAISS 等属于 Task 049）
- 不接入 ContextManager 或 Writer Prompt（属于 Task 050）
- 不做 A/B 质量评估（端到端生成分数对比属于 Task 051）
- 不做章节实时增量 embedding（属于 Task 049/050）
- 不引入多模态 embedding（仅文本）

---

## 接口契约

```python
# evals/embedding_benchmark.py

class EmbeddingBenchmark:
    """Embedding 模型基准测试框架."""

    def __init__(
        self,
        model_name: str,  # "BAAI/bge-m3" | "all-MiniLM-L6-v2" | "openai:text-embedding-3-small"
        project_id: str,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        device: str = "cpu",
    ) -> None: ...

    async def load_chapters(self) -> list[ChapterChunk]:
        """从 projects/{project_id}/chapters/ 加载章节并切分 chunk."""
        ...

    async def build_index(self, chunks: list[ChapterChunk]) -> None:
        """计算 embedding 并构建内存索引（不持久化）."""
        ...

    async def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """执行检索，返回排序后的 chunk 结果."""
        ...

    async def run_benchmark(self, queries: list[BenchmarkQuery]) -> BenchmarkReport:
        """运行完整基准测试，返回评估报告."""
        ...


@dataclass
class ChapterChunk:
    chunk_id: str          # "ch03_c05" 格式
    chapter_num: int
    chunk_index: int
    text: str
    is_chapter_boundary: bool  # 是否跨章边界


@dataclass
class BenchmarkQuery:
    query: str
    expected_chapters: list[int]   # 期望命中的章节号列表
    query_type: Literal["entity", "relationship", "semantic"]


@dataclass
class SearchResult:
    chunk: ChapterChunk
    score: float           # 相似度分数
    rank: int


@dataclass
class BenchmarkReport:
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
    per_query_results: list[PerQueryResult]

    def to_markdown(self) -> str: ...
```

---

## 数据模型

```python
# 本 Task 新增（放在 evals/models.py 或 benchmark 脚本内，视规模决定）

from pydantic import BaseModel

class EmbeddingBenchmarkConfig(BaseModel):
    """基准测试配置（可序列化复现）."""

    model_name: str
    project_id: str
    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k_values: list[int] = [1, 3, 5]
    device: str = "cpu"
    hybrid_alpha: float = 0.5  # 稠密:稀疏 混合权重，仅 BGE-M3 有效
    queries: list[BenchmarkQuery]

class PerQueryResult(BaseModel):
    """单个查询的详细结果."""

    query: str
    query_type: str
    expected_chapters: list[int]
    hit_at_k: dict[int, bool]   # {1: True, 3: True, 5: False}
    reciprocal_rank: float      # 1/rank_of_first_hit，无命中为 0
    top_results: list[dict]     # 前5结果的简要信息
```

---

## 实现清单

### 1. 依赖与环境
- [ ] 确认 `sentence-transformers>=3.0` 已安装（BGE-M3 需要较新版本）
- [ ] 确认 `FlagEmbedding` 或直接使用 `sentence-transformers` 加载 BGE-M3
- [ ] 更新 `pyproject.toml`：添加 `sentence-transformers>=3.0` 到 dependencies（如未添加）
- [ ] 文档说明：首次运行会自动下载模型（~2.4GB）

### 2. 基准测试脚本
- [ ] `evals/embedding_benchmark.py`: `EmbeddingBenchmark` 主类
- [ ] `evals/chunking.py`: 文本切分模块（与 Task 049 复用，先在本 Task 内实现）
- [ ] `evals/queries.py`: 查询集定义（10 个查询 + 标注）
- [ ] `evals/metrics.py`: 评估指标计算（命中率、MRR、延迟、内存）

### 3. BGE-M3 专项
- [ ] 稠密向量检索实现（`dense_search`）
- [ ] 稀疏向量检索实现（`sparse_search`，利用 BGE-M3 内置的 lexical 权重）
- [ ] 混合检索实现（`hybrid_search`，可调 alpha 权重）
- [ ] Chunk 重叠度对比实验（0 / 100 / 200 字三组）

### 4. 报告输出
- [ ] `docs/review/embedding_benchmark_report.md` 自动生成模板
- [ ] `evals/embedding_benchmark.py --output-json` 支持输出结构化结果

---

## 测试要求

### Layer 1: 模型测试
- [ ] `test_chapter_chunk_model`: `ChapterChunk` 可正确实例化，边界字段验证
- [ ] `test_benchmark_config_serialization`: `EmbeddingBenchmarkConfig` 可 JSON 序列化/反序列化

### Layer 2: 模块测试
- [ ] `test_chunking_500_no_overlap`: 500 字文本切分为 1 个 chunk
- [ ] `test_chunking_1200_100_overlap`: 1200 字文本按 500/100 切分为 3 个 chunk，验证重叠边界
- [ ] `test_chunking_chapter_boundary`: 多章节文本切分后，`is_chapter_boundary` 正确标记
- [ ] `test_metrics_hit_at_k`: 给定模拟的搜索结果，正确计算 hit@1/3/5
- [ ] `test_metrics_mrr`: MRR 计算边界（无命中=0，第1位=1.0，第3位=0.333）

### Layer 3: 集成测试（Mock 模型）
- [ ] `test_benchmark_run_with_mock_embedder`: 使用 Mock embedder（固定随机向量）验证完整 pipeline 无异常，输出报告格式正确
- [ ] `test_benchmark_report_markdown`: 报告 Markdown 包含所有必填字段

> **注意**: BGE-M3 真实模型测试标记为 `@pytest.mark.performance`，默认跳过（CI 不跑，本地手动跑）。

---

## 验收标准

- [ ] `pytest tests/test_embedding_benchmark.py -v` 全部通过（Mock 测试，~10 个）
- [ ] 本地手动运行 `python evals/embedding_benchmark.py --model BAAI/bge-m3 --project-id orbital_horror` 成功输出报告
- [ ] BGE-M3 Top-1 命中率 **>= 60%**（对比 MiniLM 基线约 25%），或提供明确的不达标分析与降级方案
- [ ] 单次查询延迟 **< 200ms**（CPU, i5/Ryzen5 级别）
- [ ] 模型峰值内存 **< 8GB**
- [ ] 验证 BGE-M3 输出维度为 **1024**，模型可正常下载加载
- [ ] 报告文档 `docs/review/embedding_benchmark_report.md` 已撰写并包含选型结论
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 更新了 `docs/STATUS.md`（Task 048 状态改为 ✅，并记录结论）
- [ ] 生成了 `tasks/048-embedding-model-benchmark-DONE.md` 交接文件

---

## 已知限制与风险

| 风险 | 说明 | 应对 |
|------|------|------|
| BGE-M3 首次下载慢 | ~2.4GB，国内网络可能超时 | 文档说明 HuggingFace 镜像配置 |
| CPU 推理速度慢 | 1024 维向量计算量大于 384 维 | 设置性能测试标记，允许 GPU 加速可选参数 |
| 稀疏向量实现复杂 | BGE-M3 的 lexical 权重需额外处理 | 先实现稠密向量，稀疏/混合作为加分项 |
| 项目数据不足 | 仅 10 章（~46k 字），统计显著性有限 | 明确报告为 "初步验证"，建议 30+ 章后复测 |

---

## 参考文档

- `docs/architecture/long_range_research_report.md` — Task 039 调研报告（含 MiniLM MVP 结果与优化建议）
- `docs/architecture/roadmap_v2_phases.md` — V2 完整路线图
- `docs/review/orbital_horror_ch2_ch11_assessment.md` — Ch2~Ch11 评估报告（查询集设计参考）
- `evals/consistency_test.py` — 随机一致性测试引擎（文本加载逻辑可参考复用）
- `scripts/long_range_research.py` — Task 039 MVP 实验脚本（RAG 原型实现）
- BGE-M3 官方文档: https://github.com/FlagOpen/FlagEmbedding/tree/master/FlagEmbedding/BGE_M3
