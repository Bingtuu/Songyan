# 待修复项（2026-06-11 交接）

> **状态更新（2026-06-16）**: 以下 4 项已修复/确认，详见 `docs/memos/MEMO-001-vectorstore-reload.md`。
> 本文件保留为历史交接记录，不再作为活跃任务清单。

---

> 原说明：以下 4 项在 CR 修复中被 git checkout 回滚冲掉，需要重新应用。
> 所有修复逻辑已验证，只需用 Python 脚本重新写入。

---

## 1. vector_store.py — 添加 load_incremental()

**文件**: `src/songyan/rag/vector_store.py`
**来源**: Pass 8 PERF-01 (P1)
**原则**: 替换 `return` 前的 `async def load(self)` 结束时插入。

需要在 `load()` 方法之后添加：

```python
async def load_incremental(self) -> None:
    """PERF-01: Incremental load — only load chunks from new chapters."""
    if self._loaded_chapter == 0:
        await self.load()
        return
    new_chunks, new_embeddings = await self._repo.get_with_embeddings(self.project_id)
    existing_ids = {c.chunk_id for c in self._chunks}
    added = [(c, e) for c, e in zip(new_chunks, new_embeddings) if c.chunk_id not in existing_ids]
    if not added:
        return
    add_chunks, add_embs = zip(*added)
    self._chunks.extend(add_chunks)
    if self._embeddings is not None:
        import numpy as np
        self._embeddings = np.concatenate([self._embeddings, np.array(add_embs)], axis=0)
    self._loaded_chapter = max((c.chapter_number for c in self._chunks), default=0)
```

并给 `__init__` 增加：`self._loaded_chapter: int = 0`

## 2. retriever.py — 给 RAGRetriever 添加缓存

**文件**: `src/songyan/rag/retriever.py`
**来源**: Pass 8 PERF-01 (P1)
**原则**: 在 `retrieve_for_chapter()` 中缓存 VectorStore，避免全量重载。

```python
# class RAGRetriever 上方添加类变量:
_store_cache: dict = {}

# retrieve_for_chapter() 开头，在 try 块中替换:
# await self.vector_store.load()
# 为:
cache_key = self.vector_store.project_id
if cache_key in self._store_cache:
    cached = self._store_cache[cache_key]
    cached._chunks = self.vector_store._chunks
    cached._embeddings = self.vector_store._embeddings
    cached._loaded_chapter = getattr(self.vector_store, '_loaded_chapter', 0)
    await cached.load_incremental()
else:
    await self.vector_store.load()
    self._store_cache[cache_key] = self.vector_store
```

## 3. embedder.py — 添加 warm_up() + aembed() 超时

**文件**: `src/songyan/rag/embedder.py`
**来源**: Pass 8 PERF-02 (P2) + Pass 11 RES-06 (P2)

**aembed() 超时** (RES-06):
```python
# 修改 aembed 方法:
return await asyncio.wait_for(
    loop.run_in_executor(None, self.embed, texts),
    timeout=30.0
)
```

**warm_up() 类方法** (PERF-02):
```python
@classmethod
def warm_up(cls, model_name: str = "shibing624/text2vec-base-chinese",
            device: str = "cpu") -> "Embedder":
    """PERF-02: Preload Embedder model to avoid 5-20s lazy load delay."""
    emb = cls(model_name=model_name, device=device)
    emb._load_model()
    _ = emb.dimension
    return emb
```

## 4. test_eval_runner.py — 恢复原始文件，标记已知失败

**文件**: `tests/test_eval_runner.py`
**来源**: 原始文件第 328 行已有缩进问题 (非 CR 引入)

修复方式：`git checkout -- tests/test_eval_runner.py` 恢复原始版本。
然后修改第 328 行，将 `    @pytest.mark.xfail(...)` 的缩进改为与第 327 行 `@pytest.mark.asyncio` 一致（0 缩进）。

如果不行，直接在 `__init__.py` 或 conftest 中排除该测试：
```python
# pytest_ignore_collect_path = ["tests/test_eval_runner.py"]
```

## 回退记录

上述 4 项均在 git 中有 `**未提交**` 的修改版本（在回滚前），可以查看 git reflog 找回：
```bash
git reflog | grep -i 'commit'
```

所有修复都应使用 **Python 脚本**（而非 PowerShell）写入，避免编码污染：
```bash
py fix_remaining.py
```

---

## 已验证未回滚的修复（无需重新操作）

| 文件 | 修复项 | 验证状态 |
|------|--------|---------|
| `exceptions.py` | DatabaseError / ContextBuildError / SettlementError / PipelineError | ✅ 测试通过 |
| `connection.py` | PRAGMA quick_check + WAL/SHM 残留清理 | ✅ 测试通过 |
| `retry.py` | jitter (random.uniform 0.75-1.25) | ✅ 测试通过 |
| `migrations.py` | setting_snapshots (project_id, setting_key) 索引 | ✅ 测试通过 |
| `conftest.py` | mock_llm fixture | ✅ 测试通过 |
| `pyproject.toml` | jinja2 声明 + 版本约束 + addopts 去重 | ✅ 测试通过 |
| `.env.example` | DATABASE_URL 配置项 | ✅ 已写入 |
| `README.md` | 快速开始 + CLI + 恢复文档 | ✅ 已写入 |
| `docs/*` | STATUS/INDEX + 13 份审查报告 | ✅ 已写入 |


---

## 修复状态汇总（2026-06-16）

| # | 修复项 | 状态 | 备注 |
|---|--------|:----:|------|
| 1 | `vector_store.py` — `load_incremental()` | ✅ 已修复 | 同步追加 chunks 与 embeddings，见 MEMO-001 |
| 2 | `retriever.py` — `RAGRetriever` 缓存 | ✅ 已修复 | 缓存命中后 `self.vector_store` 指向缓存实例，见 MEMO-001 |
| 3 | `embedder.py` — `warm_up()` + `aembed()` 超时 | ✅ 已存在 | `warm_up()` 与 30s 超时已在当前代码中 |
| 4 | `test_eval_runner.py` — xfail 缩进 | ✅ 已正确 | 第 334 行缩进正确 |

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
