# Task 071: RAG 独立调试

> **Phase**: V3.1 — 质量跃迁
> **优先级**: P2
> **依赖**: 无
> **预计工作量**: 小（~4 小时）

---

## Goal

解决 RAG 检索器在 30 章运行中 `vector_store.total_chunks=0` 的零检索问题，确保 RAG 在触发阈值后真正能返回相关 chunks。

## Context

058b 运行日志显示：
- RAG 在 Ch30 触发（符合 `threshold=estimated_chapters*0.3=10` 的预期）
- 但 `vector_store.total_chunks=0`，检索结果为空
- 降级到关键词匹配后，仍无有效结果

根因假设：
1. **Chunk 写入失败**：`Chunker.chunk_chapter()` 产出 chunks，但 `VectorStore.add_chunks()` 未成功写入 SQLite
2. **向量未持久化**：`Embedder.embed()` 产出的 embeddings 未正确序列化存入 BLOB
3. **加载失败**：`VectorStore.load()` 从 SQLite 读取时返回空
4. **索引未建立**：Chunks 写入了但没有 embeddings，导致 `search()` 时 `_embeddings` 为空数组

## In Scope（必须完成）

- [ ] 检查 `VectorStore.add_chunks()` 的写入路径：是否调用了 `chunk_repo.bulk_insert()`
- [ ] 检查 `chunk_repo.bulk_insert()` 的实现：embeddings 是否正确序列化为 BLOB
- [ ] 检查 `VectorStore.load()` 的读取路径：从 SQLite 加载后 `_chunks` 和 `_embeddings` 是否非空
- [ ] 检查 `chunk_repo.get_with_embeddings()` 的实现：查询 SQL 是否正确
- [ ] 在 `VectorStore.add_chunks()` 和 `load()` 中增加诊断日志（chunk 数、embedding shape）
- [ ] 修复发现的 root cause
- [ ] 补充集成测试：写入 → 加载 → 检索的完整往返

## Out of Scope（明确不做）

- 不更换向量数据库（保持 SQLite + numpy）
- 不做 Embedding 模型切换
- 不做 RAG 与 Writer 的集成测试（已在 Task 050 完成）
- 不做大规模性能测试

## 诊断检查清单

```python
# 在 vector_store.py 中增加诊断

async def add_chunks(...) -> None:
    logger.info(
        "vector_store.add_start",
        chunk_count=len(chunks),
        embedding_shape=embeddings.shape,
    )
    ...
    logger.info(
        "vector_store.add_done",
        total_chunks=self.total_chunks,
    )

async def load(self) -> None:
    chunks, embeddings = await self._repo.get_with_embeddings(self.project_id)
    logger.info(
        "vector_store.load_result",
        chunk_count=len(chunks),
        embedding_shape=embeddings.shape if embeddings is not None else None,
    )
```

## 测试要求

- [ ] 写入 5 个 chunks + embeddings → load 后 chunk 数 = 5
- [ ] 写入后 search 返回非空结果
- [ ] load 后 embedding shape = (N, D)，与写入时一致
- [ ] 空 VectorStore 的 search 返回 `[]` 不抛异常

## 验收标准

- [ ] `pytest tests/rag/test_vector_store.py -v` 全部通过 + 新增诊断测试通过
- [ ] RAG 在模拟 30 章场景下能返回非空检索结果
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/071-rag-debugging-DONE.md`

## 参考文档

- `src/songyan/rag/vector_store.py` — VectorStore
- `src/songyan/rag/retriever.py` — RAGRetriever
- `src/songyan/db/chunk_repo.py` — ChunkRepository
- `tests/rag/test_vector_store.py` — 现有测试
