# 备忘：VectorStore 全量加载问题

> **ID**: MEMO-001
> **创建**: 2026-06-10
> **来源**: Code Review Pass 5 (R2)
> **状态**: 已修复（2026-06-16）

---

## 问题

`RAGRetriever.retrieve_for_chapter()` 每次被调用时都执行 `vector_store.load()`，
从 SQLite 读取**全部** chunks + embeddings 到内存 numpy 数组。

## 影响

| 章节区间 | chunks 数 | 内存加载量 | 单次检索延迟 (估) |
|---------|-----------|-----------|------------------|
| Ch1~20 | ~200 | ~0.6 MB | < 100ms |
| Ch51~70 | ~900 | ~2.8 MB | ~200ms |
| Ch71~100 | ~1300 | ~4.0 MB | ~500ms |

每章写作触发 1~3 次 RAG 检索（Writer context 组装阶段）。
在 Ch100 附近，每章仅 RAG 加载就要 4~12 MB 的数据读取 + 余弦相似度计算。

## 根因

`VectorStore` 实例没有跨请求的缓存策略。每次 `retrieve_for_chapter()` 调用
都创建一个新的隐式上下文，导致 `load()` 被重复执行。

关键代码路径：

```
_nodes.py:271  assemble_context_package
  → _helpers.py:402  _build_rag_soft_references
    → retriever.py:124  retrieve_for_chapter
      → vector_store.py:49  load()        ← 每次全量加载
```

## 修复方向

### 方案 A：在 RAGRetriever 内部缓存 VectorStore（推荐）

```python
class RAGRetriever:
    _store_cache: dict[str, VectorStore] = {}  # project_id → VectorStore

    async def retrieve_for_chapter(self, project_id, ...):
        if project_id not in self._store_cache:
            store = VectorStore(project_id, repo)
            await store.load()
            self._store_cache[project_id] = store
        # 增量加载当前章节之后写入的新 chunks
        await self._store_cache[project_id].load_incremental(...)
```

需要在 VectorStore 中增加 `load_incremental()` 方法，只加载 `last_loaded_chapter` 之后的 chunks，避免每次全量 reload。

### 方案 B：ContextManager 缓存 VectorStore 引用

在 `ContextManager` 实例化时预加载 VectorStore，在整章 pipeline 中复用同一实例。

---

## 相关文件

- `src/songyan/rag/vector_store.py` — `load()` 方法 (L49)
- `src/songyan/rag/retriever.py` — `retrieve_for_chapter()` 方法 (L124)
- `src/songyan/workflows/_helpers.py` — `_build_rag_soft_references()` (L402)

## 验证方法

1. 在 Ch70 种子项目上运行 pipeline，对比修复前后的 `vector_store.load()` 调用次数
2. 确认每次写作的 `assemble_context_package` 延迟显著下降
3. 回归测试：`pytest tests/rag/ -v` 全部通过


---

## 修复记录（2026-06-16）

### 修复内容

| 文件 | 修复点 |
|------|--------|
| `src/songyan/rag/vector_store.py` | `load_incremental()` 增量加载时同步追加 `_chunks` 与 `_embeddings`，保持索引一致；首次加载等价于 `load()`；无新数据时幂等 |
| `src/songyan/rag/retriever.py` | `retrieve_for_chapter()` 缓存命中后将 `self.vector_store` 指向缓存实例，确保后续检索真正复用缓存 |

### 关键代码变更

**vector_store.py**
```python
# 增量加载新增 chunks 时，同步用 np.vstack 合并对应 embeddings
self._chunks.extend(new_chunks)
self._embeddings = np.vstack([self._embeddings, np.vstack(new_embeddings)])
```

**retriever.py**
```python
if cache_key in self._store_cache:
    cached = self._store_cache[cache_key]
    await cached.load_incremental()
    self.vector_store = cached  # ← 关键：后续 search 走缓存实例
else:
    await self.vector_store.load()
    self._store_cache[cache_key] = self.vector_store
```

### 新增测试

- `tests/rag/test_vector_store.py`
  - `test_load_incremental_first_call_loads_all`
  - `test_load_incremental_appends_new_chunks_syncs_embeddings`
  - `test_load_incremental_idempotent`
- `tests/rag/test_retriever.py`
  - `TestCacheReuse::test_retriever_reuses_cached_store`

### 验证结果

```bash
pytest tests/rag/test_vector_store.py tests/rag/test_retriever.py -v
# 18 passed

pytest tests/ -q --tb=no
# 1555 passed, 4 skipped, 1 xfailed, 4 xpassed

ruff check src/songyan/rag/vector_store.py src/songyan/rag/retriever.py \
  tests/rag/test_vector_store.py tests/rag/test_retriever.py
# All checks passed!
```
