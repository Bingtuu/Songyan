# Pass 5 — RAG 检索层 + Pydantic 数据模型审计报告

> **范围**: rag/（6 文件，717 行）+ models/（18 文件，70 模型，546 字段）
> **日期**: 2026-06-10
> **审查者**: Codex (Pass 5 — 模块级审计)
> **状态**: 完成

---

## 两模块快速评估

| 模块 | 文件数 | 行数 | 健康状况 | 关键发现 |
|------|--------|------|---------|---------|
| RAG 检索层 | 6 | 717 | ### 中等 | **零 try/except** — 全模块无错误处理 |
| Pydantic 模型 | 18 | 1,464 | ### 有缺口 | **零 field_validator** — 70 模型全无校验 |

---

## 第一部分：RAG 检索层

### 1.1 模块结构

```
retriever.py (209行)
  ├── RAGRetriever.build_query()     — 从 chapter_goal + recent_plot 构造查询
  ├── RAGRetriever.retrieve()        — encode → vector search
  └── RAGRetriever.retrieve_for_chapter() — load → query → search → keyword fallback

chunker.py (192行)
  └── Chunker.chunk_chapter()        — 按场景拆分 → 句边界保护 → 100 字符重叠

embedder.py (105行)
  └── Embedder.aembed()              — 线程池异步 encode，sentence-transformers

vector_store.py (163行)
  ├── load()                         — 从 SQLite 全量加载向量到内存 numpy 数组
  ├── search()                       — 余弦相似度，去重（每章最多 1 chunk）
  └── add_chunks()                   — 写入 SQLite + 更新内存缓存
```

### 1.2 测试覆盖

| 文件 | 测试数 | 断言数 |
|------|--------|--------|
| `tests/rag/test_chunker.py` | 8 | 18 |
| `tests/rag/test_retriever.py` | 8 | 15 |
| `tests/rag/test_vector_store.py` | 6 | 10 |
| `tests/rag/test_embedder.py` | 6 | 7 |
| `tests/rag/test_rag_indexing.py` | 5 | 12 |
| `tests/rag/test_utils.py` | 10 | 11 |
| **总计** | **43** | **73** |

### 1.3 发现的问题

#### R1 — 零 try/except（P1）
整个 RAG 层 6 个文件没有一行 try/except。对比 LLM 层（retry.py 有系统的重试 + 异常包装），RAG 是"裸奔"的。

**影响**:
- `embedder.aembed()` 中 `_load_model()` 调用 `SentenceTransformer()` 可能 throw（模型不存在、网络失败、OOM）
- `vector_store.load()` 调用 `repo.get_with_embeddings()` 可能 throw（DB 损坏、格式错误）
- 以上异常会直接穿透到调用方，而调用方（`_nodes.py:937` RAG 索引）有一个 `except Exception`，但 `retriever.py` 的检索路径（`_nodes.py:271` assemble_context_package）**没有保护**

**根因**: RAG 层当初的设计假设"RAG 是一个纯辅助功能，失败也不影响核心流程"，但实际代码中两个路径都有不同的错误保护水平。

#### R2 — 全量向量加载，每次检索都 reload（P2）
`retrieve_for_chapter()` 每次调用都执行 `vector_store.load()` — 从 SQLite 读取全部 chunks + embeddings 到内存 numpy 数组。

```
每次检索的代价:
Ch20: ~200 chunks × 768 dims × 4 bytes = ~0.6 MB 加载
Ch70: ~900 chunks × 768 dims × 4 bytes = ~2.8 MB 加载
Ch100: ~1300 chunks × 768 dims × 4 bytes = ~4.0 MB 加载
```

**影响**: 每个章节的写作需要 1~3 次 RAG 检索（Writer context + 连续 2 次 for each）。在 Ch100 附近，每次写作需要加载 ~4MB 数据 + 编码 query + 余弦相似度计算。总延迟可能达到 1-3 秒/次。

**建议**: 在 RAGRetriever 或调用方缓存 VectorStore 实例，或者使用增量加载（只加载新章节）。

#### R3 — sentence-transformers 懒加载无超时管理（P2）
`Embedder._load_model()` 在首次调用时同步加载模型。对于 `shibing624/text2vec-base-chinese`（约 400MB），首次加载可能耗时 5-20 秒（下载 + 加载到内存）。

```python
def _load_model(self) -> None:
    ...
    model = SentenceTransformer(self.model_name, device=self.device)  # ☠ 阻塞
```

**影响**: 第一个触发 RAG 检索的章节（通常是 Ch2）会额外增加 5-20 秒的加载时间。如果此时 LLM 调用也在进行，可能触发 `asyncio.wait_for` 总超时。

**建议**: 在项目初始化阶段提前调用 `Embedder._load_model()`（pipeline 启动时 warm up）。

#### R4 — 向量存储非持久化索引（P3）
当前 VectorStore 使用 numpy 内存数组 + SQLite BLOB。没有使用 faiss 或其他 ANN 索引。在 `_CHUNK_WARNING_THRESHOLD = 5000` 时有 warning（但不会触发任何行为）。

当前实现已经是 O(N) 的暴力搜索（`self._embeddings @ query_embedding` 是 numpy 向量化运算，不完全是 O(N)，但全量内存拷贝的开销）。

**建议**: 当 chunk 数超过 1000 时，可以评估切换到 faiss 的 `IndexFlatIP`（内积索引，与 L2 归一化兼容）。

---

## 第二部分：Pydantic 数据模型

### 2.1 模块结构

| 文件 | 模型数 | 字段数 | Field() | 校验器 | 行数 |
|------|--------|--------|---------|--------|------|
| context.py | 13 | 103 | 34 | 0 | 227 |
| review.py | 8 | 71 | 13 | 0 | 209 |
| creative_mode.py | 7 | 48 | 15 | 0 | 132 |
| genre.py | 7 | 46 | 27 | 0 | 121 |
| settlement.py | 7 | 37 | 10 | 0 | 93 |
| continuity.py | 5 | 34 | 6 | 0 | 69 |
| rag.py | 4 | 26 | 4 | 0 | 54 |
| chapter.py | 3 | 15 | 3 | 0 | 55 |
| character.py | 3 | 33 | 5 | 0 | 67 |
| 其他 9 文件 | ~13 | ~133 | ~26 | 0 | ~260 |
| **总计** | **70** | **546** | **143** | **0** | **1,464** |

### 2.2 发现的问题

#### M1 — 零 field_validator（P2，结构性）

**70 个模型，546 个字段，零个校验器。**

Pydantic v2 提供了强大的校验机制，但没有被使用：

```python
# 应该存在的（但不存在）：
word_count_target: int = Field(3000, ge=500, le=20000)      # 字数范围
chapter_number: int = Field(..., ge=1)                       # 章节号 ≥1
role_type: str = "protagonist"                               # 应是 Literal
word_count: int = Field(0, ge=0)                             # 字数 ≥0
impact_score: float = Field(0.0, ge=0.0, le=1.0)            # 评分 0~1
```

当前所有模型依赖于**应用层的分散验证**（Agent 内的 `_clamp_word_count`、`_validate_chapter_type` 等）。但这不是强制性的 — 如果新的 Agent 直接创建模型而不做验证，非法数据可以进入持久化层。

**影响**: 低到中。应用层验证在实际运行中能兜住大多数问题。但如果引入新的 Agent 或修改现有的 Agent，没有模型级别的安全网。

#### M2 — created_at 类型不一致（P2）

```
datetime 派:   ChapterVersion、ContinuityReport、HumanInstruction、
               HumanMark、ProjectRunState
str 派:        CharacterState.created_at: str = ""
               Character.created_at: str = ""
               DialogueStyleCard.generated_at: str = ""
```

同样一个 `created_at` 字段，Character 模型用 `str`，其他模型用 `datetime`。这意味着：

- Character 的时间戳无法在 Pydantic 层面排序或比较
- 序列化行为不一致（`datetime` → ISO 字符串 vs `str` → 原样输出）
- SQLite 中都是 TEXT，但反序列化到 Python 时行为不同

#### M3 — 关键字段缺少取值约束（P2）

| 模型 | 字段 | 当前类型 | 应该 |
|------|------|---------|------|
| `ChapterGoal` | `chapter_number` | `int` | `int = Field(ge=1)` |
| `ChapterGoal` | `word_count_target` | `int = 3000` | `int = Field(3000, ge=500, le=20000)` |
| `Character` | `role_type` | `str = "protagonist"` | `Literal["protagonist", "supporting", "antagonist"]` |
| `ChapterVersion` | `word_count` | `int = 0` | `int = Field(0, ge=0)` |
| `ChapterVersion` | `version_type` | `str = "draft"` | `Literal["draft", "revision", "accepted", "edited"]` |
| `StateSettlement` | `impact_score` | `float = 0.0` | `float = Field(0.0, ge=0.0, le=1.0)` |

#### M4 — JSON 字段缺少类型参数（P2）

Pydantic v2 要求泛型类型参数用于正确的校验：

```python
# 当前（宽松）：
scenes: list[dict] = Field(default_factory=list)             # → 接受任何 list
generation_metadata: dict = Field(default_factory=dict)       # → 接受任何 dict
key_events: list = Field(default_factory=list)                # → 无泛型参数

# 更严格的写法：
scenes: list[dict[str, Any]] = Field(default_factory=list)
generation_metadata: dict[str, Any] = Field(default_factory=dict)
key_events: list[str] = Field(default_factory=list)
```

**影响**: 当前写法下，如果某个 Agent 错误地向 `key_events` 中写入了 `int` 或 `dict`，Pydantic 不会报错。直到序列化到 JSON 时才可能发现问题。

#### M5 — ContextPackage 的 V3.x 预组装债务（P2，结构）

`context.py`（227 行）包含 13 个模型，103 个字段。`ContextPackage` 本身是一个**预组装大包**——包含了 Writer 需要的一切。

```python
class ContextPackage(BaseModel):
    chapter_goal: ChapterGoal | None = None
    creative_brief: CreativeBrief | None = None
    hard_constraints: list[HardConstraint] = []
    character_snapshots: list[CharacterStateSnapshot] = []
    recent_plot: RecentPlot | None = None
    soft_references: list[SoftReference] = []
    genre_rules: GenreRules | None = None
    mode_rules: ModeRules | None = None
    foreshadowing_items: list[ForeshadowingItem] = []
    ...
```

这是 V3.x 的"预组装上下文包"模式。V4.0 Phase C（ContextService）将改为 `AgentContext`（按需检索）。当前模型的耦合度意味着 Phase C 的迁移会涉及大量模型变更。

**影响**: 不会在 Phase B 出现问题，但 Phase C 启动时需要考虑。

---

## 3. 两模块交叉风险

| # | 问题 | RAG 影响 | Model 影响 |
|---|------|---------|-----------|
| X1 | Chunk 数据经过 JSON 序列化存入 DB，取出后需重建模型 | 地址已嵌入于 `TextChunk` 模型 | ✅ `rag.py` 模型设计合理 |
| X2 | RAG 检索结果通过 `ContextPackage.soft_references` 传递给 Writer | ✅ `RetrievedChunk` 有明确返回类型 | ⚠️ 但 `ContextPackage` 无 `rag_chunks` 字段，RAG 结果混在 `soft_references` 中 |
| X3 | Writer 使用 `generation_metadata` 记录 RAG 使用情况 | ⚠️ 无 RAG-specific 日志 | M4 已覆盖 `generation_metadata` 无类型约束 |

---

## 4. 修复建议

### RAG（高优先级）

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| R1 | 零 try/except | 检索路径无保护 | 在 `RAGRetriever.retrieve()` 和 `Embedder._load_model()` 添加 try/except → log warning → return [] |
| R2 | 全量向量每次 reload | Ch100 时 ~4MB/次 | 在 `retrieve_for_chapter()` 中缓存 VectorStore 实例，或在 RAGRetriever 内部做增量子加载 |
| R3 | 模型懒加载无超时 | 首次调用 5-20s 阻塞 | `_load_model()` 使用 `asyncio.wait_for` 设置 30s 超时，或在 pipeline 启动时预加载 |
| R4 | 无 ANN 索引 | Ch500+ 后性能问题 | 超过 1000 chunks 时考虑 faiss `IndexFlatIP` |

### Pydantic 模型（建议逐步修复）

| # | 问题 | 建议 | 工作量 |
|---|------|------|--------|
| M1 | 零校验器 | 核心模型优先加：`Field(ge=0)`、`Field(ge=0.0, le=1.0)`、`StringConstraints(min_length=1)` | 中（70 模型 × ~5 分钟/个）|
| M2 | created_at 不一致 | Character 模型改为 `created_at: datetime` 并与 SQLite 兼容 | 小（3 个字段）|
| M3 | 关键字段无约束 | 先修 `chapter_number`（ge=1）、`word_count`（ge=0）、`word_count_target`（ge=500）、`role_type`（Literal）| 小（4 个字段）|
| M4 | JSON 字段无类型参数 | 补全 `list[T]`、`dict[str, Any]` | 中（~30 个字段）|
| M5 | ContextPackage 过重 | Phase C 启动时再处理，当前不动 | Phase C 范围 |

### 建议修复顺序（Phase B 验证前可做的）

```
Phase B 前 (高影响/低风险):
  1. R1: RAGRetriever.retrieve() 加 try/except → return [] (15 行代码)
  2. M3: 4 个关键字段加约束 (不影响序列化, 向后兼容)
  
Phase B 后 (中风险):
  3. R2: 缓存 VectorStore 实例
  4. R3: _load_model 加超时
  5. M1: 核心模型加 Field(ge=0) 等简单约束
  6. M2: created_at 类型统一
  
后续:
  7. M4: JSON 字段补全类型参数
  8. R4: faiss 评估 (Ch500+ 场景)
```

---

> **松烟入墨，字句成锋。**
> 模型的约束定义了系统的安全边界 — 一个没有校验器的数据层，和一个没有兜底的检索层，都在同一个方向上增加了运行时的不确定性。
