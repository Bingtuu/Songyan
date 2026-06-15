# Task 049 — Chunker + Embedder + VectorStore 实现

> **目标**: 实现 RAG 自动层的数据基础设施——章节切分、向量计算、向量存储，为 Task 050 的检索与集成提供底层支持。  
> **Phase**: 8b  
> **优先级**: P0  
> **依赖**: Task 048（BGE-M3 选型确认）  
> **预计工作量**: 大（3~4 天）

---

## Context

Phase 8b 的 RAG 自动层需要三个核心组件：
1. **Chunker**: 将章节正文切分为语义连贯的文本片段（~500 字/chunk，100 字重叠）
2. **Embedder**: 用 BGE-M3 将 chunk 转换为 1024 维向量
3. **VectorStore**: 存储向量 + 元数据，支持余弦相似度检索

Task 048 将确认 BGE-M3 在真实项目数据上的检索质量。本 Task 负责将选型结论落地为可运行的基础设施。

**关键约束**（来自 `docs/architecture/phase8b_rag_layer.md`）：
- ≤30 章项目默认不启用 RAG（零成本）
- 使用本地模型（BGE-M3），无 API 依赖
- 向量存储用 SQLite + numpy 内存数组（与现有架构兼容，100 章仅 ~2.4MB）
- 所有组件必须支持异步（与现有 DB repository 模式一致）

---

## Goal

实现完整的 RAG 数据层：章节自动切分 → BGE-M3 向量计算 → SQLite/numpy 存储，并提供增量更新能力（每完成一章自动 indexing）。

---

## In Scope（必须完成）

### 1. 数据模型（`src/songyan/models/rag.py`）
- [ ] `TextChunk` — 章节切片模型
- [ ] `ChunkMetadata` — 切片元数据（场景号、提及角色、设定 key、chunk 类型、字符位置）
- [ ] `RetrievedChunk` — 检索结果模型
- [ ] `RAGConfig` — 创作模式中的 RAG 配置（enabled / threshold_chapters / max_results / chunk_size / chunk_overlap / min_similarity / embedding_model / vector_store）

### 2. Chunker（`src/songyan/rag/chunker.py`）
- [ ] `Chunker` 类，支持配置 `chunk_size` / `chunk_overlap`
- [ ] 场景边界感知：优先按场景标记分割
  - 定义 `SCENE_MARKER_PATTERN = re.compile(r"^#{3,4}\s+Scene\s+\d+", re.IGNORECASE)`
  - 有标记时按场景预分割；无标记时退化为按空行分段落
  - 测试中覆盖三种情况：规范标记、无标记、标记格式不规范
- [ ] 句子边界保护：不在句子中间切断
- [ ] 重叠缓冲：相邻 chunk 保留 overlap 字数，防止关键信息被切分
- [ ] 元数据提取（基础版本）:
  - `characters_mentioned`: 从 chunk 文本中匹配已知的角色名列表（通过正则或简单包含检查）
  - `setting_keys_mentioned`: 匹配已知设定 key（从 `setting_tracking` 表获取）
  - `chunk_type`: 基于文本特征简单分类——对话行数 > 50% 标记为 "dialogue"，描写性形容词密度高标记为 "description"，动作动词多标记为 "action"，否则 "narrative"

### 3. Embedder（`src/songyan/rag/embedder.py`）
- [ ] `Embedder` 类，封装 `sentence-transformers` 加载 BGE-M3
- [ ] `embed(texts: list[str]) -> np.ndarray` — 批量编码
- [ ] **异步包装**: sentence-transformers 的 `encode()` 是同步 CPU 密集型，必须用 `asyncio.get_event_loop().run_in_executor(None, ...)` 分派到线程池，避免阻塞事件循环
- [ ] **懒加载**: 模型仅在首次调用 `embed()` 时才加载，禁止在 `__init__` 中预加载。≤30 章项目（永不启用 RAG）应完全零成本
- [ ] 模型单例管理（进程内复用，避免重复加载 ~2.3GB 模型）
- [ ] 首次加载提示与错误处理（ HuggingFace 镜像回退）
- [ ] 支持 CPU 推理（默认），可选 GPU 加速

### 4. VectorStore（`src/songyan/rag/vector_store.py`）
- [ ] `VectorStore` 类，SQLite 存元数据 + numpy 内存数组存向量
- [ ] `add_chunks(chunks, embeddings)` — 写入新章节的 chunks
- [ ] `search(query_embedding, top_k, min_similarity) -> list[RetrievedChunk]` — 余弦相似度检索
- [ ] **章节去重**：同一章多个高相似 chunk 只返回最高分的那一个
- [ ] `load_project(project_id)` — 从 SQLite 加载已有向量到内存
- [ ] 内存上限监控：chunks > 5000 时报警（提示切换 faiss）

### 5. DB 层
- [ ] `src/songyan/db/schema.sql`: 新增 `chapter_chunks` 表
  ```sql
  CREATE TABLE chapter_chunks (
      chunk_id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      chapter_number INTEGER NOT NULL,
      version_id TEXT NOT NULL,
      chunk_index INTEGER NOT NULL,
      text TEXT NOT NULL,
      metadata_json TEXT DEFAULT '{}',
      embedding_blob BLOB,          -- 向量二进制（numpy float32）
      created_at TEXT DEFAULT (datetime('now'))
  );
  CREATE INDEX idx_chunks_project ON chapter_chunks(project_id, chapter_number);
  ```
- [ ] `src/songyan/db/migrations.py`: 新增 `_migrate_chapter_chunks()` 增量迁移
- [ ] `init_schema()` 中调用新迁移

### 6. Repository 层（`src/songyan/db/repositories/chunk_repo.py`）
- [ ] `ChunkRepository` 类（async）
- [ ] `bulk_insert(chunks, embeddings)` — 批量写入 chunks + 向量
- [ ] `get_by_project(project_id) -> list[TextChunk]` — 加载项目全部 chunks
- [ ] `delete_by_chapter(project_id, chapter_number)` — 重跑章节时清理旧向量

### 7. Settlement 集成点
- [ ] `src/songyan/workflows/_nodes.py`: `settlement_extractor_node` 完成后触发 chunking + embedding
- [ ] 新增辅助函数 `_index_accepted_chapter(state)` — 调用 Chunker → Embedder → VectorStore.add_chunks
- [ ] **Indexing 条件**: 以 `version_type == "accepted"` 为必要条件。若 SettlementExtractor 标记了 `needs_human_review`，只要 accepted 版本存在仍应索引；若 human_confirm 选择了 edit，索引 edited 版本（人工确认的最终版本）；reject/back 不索引
- [ ] 仅在 `rag_config.enabled != "never"` 时执行 indexing

### 8. CLI 支持
- [ ] `songyan index --project-id xxx --chapters 1-10` — 手动为已有章节建立向量索引
- [ ] `songyan index --project-id xxx --rebuild` — 重建整个项目的向量索引
  - 步骤 1: 调用 `delete_by_project(project_id)` 清空已有 chunks
  - 步骤 2: 遍历项目全部章节，通过 `ChapterVersionRepository.get_latest_accepted_by_chapter()` 获取每章最新 accepted 版本
  - 步骤 3: 对每章重新执行 chunk + embed + store

---

## Out of Scope（明确不做）

- 不实现稀疏向量检索（BGE-M3 的 lexical 权重属于优化项，后续迭代）
- 不引入 faiss / chromadb（当前用 numpy，超限后再评估）
- 不接入 ContextManager（属于 Task 050）
- 不修改 Writer Prompt（属于 Task 050）
- 不做 RAG 查询构造（属于 Task 050）
- 不做 A/B 测试（属于 Task 051）

---

## 接口契约

```python
# src/songyan/rag/chunker.py

class Chunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None: ...

    def chunk_chapter(
        self,
        content: str,
        project_id: str,
        chapter_number: int,
        version_id: str,
    ) -> list[TextChunk]: ...


# src/songyan/rag/embedder.py

class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu") -> None: ...

    async def embed(self, texts: list[str]) -> np.ndarray:
        """返回 (N, 1024) float32 数组.

        实现注意:
        1. sentence-transformers 的 encode() 是同步 CPU 密集型调用，
           必须在线程池中执行，避免阻塞 asyncio 事件循环。
        2. 模型懒加载：首次调用时才执行 _load_model()，禁止在 __init__ 中预加载。
        """
        ...

    @property
    def dimension(self) -> int: ...


# src/songyan/rag/vector_store.py

class VectorStore:
    def __init__(self, project_id: str, repo: ChunkRepository) -> None: ...

    async def load(self) -> None:
        """从 SQLite 加载已有向量到内存."""
        ...

    async def add_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: np.ndarray,
    ) -> None: ...

    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[RetrievedChunk]: ...

    async def delete_by_chapter(self, chapter_number: int) -> None: ...
```

---

## 数据模型

```python
# src/songyan/models/rag.py

from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    scene_number: int | None = None
    characters_mentioned: list[str] = Field(default_factory=list)
    setting_keys_mentioned: list[str] = Field(default_factory=list)
    chunk_type: Literal["narrative", "dialogue", "description", "action"] = "narrative"
    start_char: int = 0
    end_char: int = 0

class TextChunk(BaseModel):
    chunk_id: str           # "{project_id}_{chapter_number}_{index}"
    project_id: str
    chapter_number: int
    version_id: str
    chunk_index: int
    text: str
    metadata: ChunkMetadata

class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    chapter_number: int
    similarity: float       # 0.0~1.0
    metadata: ChunkMetadata

class RAGConfig(BaseModel):
    enabled: Literal["auto", "always", "never"] = "auto"
    threshold_chapters: int | None = None   # auto 时从 estimated_chapters 计算
    max_results: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 100
    min_similarity: float = 0.3
    embedding_model: str = "bge-m3"
    vector_store: str = "sqlite_numpy"
```

---

## 实现清单

### 1. 依赖更新
- [ ] `pyproject.toml`: 添加 `sentence-transformers>=3.0` 到 dependencies
- [ ] `pyproject.toml`: 添加 `numpy>=1.24` 到 dependencies（如未添加）
- [ ] 文档说明首次运行自动下载模型

### 2. 模型层
- [ ] `src/songyan/models/rag.py`: 上述 4 个模型
- [ ] `src/songyan/models/__init__.py`: 导出新增模型

### 3. RAG 核心模块
- [ ] `src/songyan/rag/__init__.py`
- [ ] `src/songyan/rag/chunker.py`: Chunker 实现
- [ ] `src/songyan/rag/embedder.py`: Embedder 实现
- [ ] `src/songyan/rag/vector_store.py`: VectorStore 实现

### 4. DB 层
- [ ] `src/songyan/db/schema.sql`: `chapter_chunks` 表
- [ ] `src/songyan/db/migrations.py`: `_migrate_chapter_chunks()`
- [ ] `src/songyan/db/repositories/chunk_repo.py`: ChunkRepository

### 5. 流水线集成
- [ ] `src/songyan/workflows/_nodes.py`: settlement 后触发 indexing
- [ ] `src/songyan/workflows/_helpers.py`: `_index_accepted_chapter()` 辅助函数

### 6. CLI
- [ ] `src/songyan/cli/commands/index.py`: index / rebuild 命令
- [ ] `src/songyan/cli/main.py`: 注册子命令

---

## 测试要求

### Layer 1: 模型测试
- [ ] `test_text_chunk_model`: `TextChunk` 可正确实例化，chunk_id 格式验证
- [ ] `test_chunk_metadata_defaults`: 默认字段正确
- [ ] `test_rag_config_defaults`: 默认值与文档一致

### Layer 2: Chunker 测试
- [ ] `test_chunk_short_chapter`: <500 字章节 → 1 个 chunk
- [ ] `test_chunk_1200_with_overlap`: 1200 字 → 3 个 chunk，验证 overlap 边界
- [ ] `test_chunk_scene_boundary`: 含 `### Scene` 标记时优先按场景分割
- [ ] `test_chunk_no_scene_fallback`: 无场景标记时按段落分割
- [ ] `test_chunk_sentence_protection`: 不会在句子中间切断
- [ ] `test_chunk_metadata_extraction`: 从文本中提取角色名、设定 key

### Layer 3: Embedder 测试（Mock）
- [ ] `test_embedder_dimension`: Mock 后返回正确维度（1024）
- [ ] `test_embedder_batch`: 批量编码返回 (N, 1024) 形状
- [ ] `test_embedder_singleton`: 两次创建 Embedder 复用同一模型实例
- [ ] `test_embedder_async_not_blocking`: 验证 embed() 不会阻塞事件循环（通过并发调用多个 embed 并检查总耗时）

### Layer 4: VectorStore 测试
- [ ] `test_vector_store_add_and_search`: 添加固定向量后，query 与自身相似度 ≈ 1.0
- [ ] `test_vector_store_chapter_dedup`: 同一章多个 chunk 只返回最高分的一个
- [ ] `test_vector_store_min_similarity`: 低于门槛的结果被过滤
- [ ] `test_vector_store_empty_search`: 空存储返回空列表
- [ ] `test_vector_store_persistence`: 写入后 reload，搜索结果一致

### Layer 5: Repository 测试
- [ ] `test_chunk_repo_bulk_insert`: 批量写入后读取验证
- [ ] `test_chunk_repo_delete_by_chapter`: 删除后该章节 chunks 为空

### Layer 6: 集成测试
- [ ] `test_settlement_triggers_indexing`: Mock Embedder，验证 settlement 后 chunk 入库

> **注意**: BGE-M3 真实模型测试标记为 `@pytest.mark.performance`，默认跳过。

---

## 验收标准

- [ ] `pytest tests/rag/ -v` 全部通过（Mock 测试，~20 个）
- [ ] `pytest tests/db/test_chunk_repo.py -v` 全部通过
- [ ] `songyan index --project-id orbital_horror --rebuild` 在已有项目上成功运行（使用 Mock embedder 或真实 BGE-M3）
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] `chunker.py` / `embedder.py` / `vector_store.py` 均 < 400 行
- [ ] 更新了 `docs/STATUS.md`（Task 049 状态改为 ✅）
- [ ] 生成了 `tasks/049-chunker-embedder-vector-store-DONE.md` 交接文件

---

## 已知限制与风险

| 风险 | 说明 | 应对 |
|------|------|------|
| BGE-M3 模型体积大 | ~2.3GB，首次下载慢 | 文档说明 HuggingFace 镜像配置；Embedder 单例复用 |
| numpy 内存膨胀 | 5000+ chunks 时 ~1GB | 监控报警；当前 100 章仅 ~2.4MB，风险低 |
| CPU 推理慢 | 1024 维计算量大于 384 维 | Settlement 阶段异步计算，不阻塞 Writer |
| 元数据提取不准确 | characters_mentioned 依赖简单正则 | 先实现基础版本，Task 050 后可引入 LLM 辅助提取 |

---

## 参考文档

- `docs/architecture/phase8b_rag_layer.md` — Phase 8b 完整设计文档
- `docs/architecture/long_range_research_report.md` — Task 039 调研报告
- `tasks/048-embedding-model-benchmark.md` — Task 048 选型基准
- `src/songyan/agents/context_manager.py` — ContextManager 现有实现（了解 soft_references）
