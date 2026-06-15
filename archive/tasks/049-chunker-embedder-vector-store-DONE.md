# Task 049 — Chunker + Embedder + VectorStore 实现 ✅

> **Phase**: 8b  
> **优先级**: P0  
> **完成日期**: 2026-06-03  
> **执行人**: Kimi Code CLI

---

## 完成情况

| 交付物 | 状态 | 位置 |
|--------|------|------|
| RAG 数据模型 | ✅ | `src/songyan/models/rag.py` |
| CreativeModeProfile 扩展 | ✅ | `src/songyan/models/creative_mode.py` |
| Chunker | ✅ | `src/songyan/rag/chunker.py` (191 行) |
| Embedder | ✅ | `src/songyan/rag/embedder.py` (104 行) |
| VectorStore | ✅ | `src/songyan/rag/vector_store.py` (148 行) |
| DB Schema | ✅ | `src/songyan/db/schema.sql` — chapter_chunks 表 |
| DB Migration | ✅ | `src/songyan/db/migrations.py` — `_migrate_chapter_chunks()` |
| ChunkRepository | ✅ | `src/songyan/db/chunk_repo.py` (196 行) |
| Settlement 集成 | ✅ | `src/songyan/workflows/_nodes.py` + `_helpers.py` |
| CLI index 命令 | ✅ | `src/songyan/cli/commands/index.py` + `main.py` |
| 创作模式配置 | ✅ | 4 个 `creative_modes/*.json` 添加 rag_config |
| 依赖更新 | ✅ | `pyproject.toml` — sentence-transformers + numpy |
| 单元测试 | ✅ | 25 个测试全部通过 |

---

## 关键设计决策

| 参数 | 值 | 理由 |
|------|-----|------|
| 默认 Embedding 模型 | `shibing624/text2vec-base-chinese` | Task 048 实测 Top-1 90% |
| 维度 | 768 | text2vec 实际输出维度 |
| chunk_size | 500 | Task 048 验证 |
| chunk_overlap | 100 | Task 048 验证 |
| 向量存储 | SQLite + numpy 内存数组 | 与现有架构兼容 |
| 懒加载 | 是 | ≤30 章项目零成本 |
| 单例复用 | 是 | 避免重复加载模型 |

---

## 测试统计

```
pytest tests/rag/ tests/db/test_chunk_repo.py tests/test_settlement_indexing.py -v
25 passed in 3.05s
```

| 测试文件 | 用例数 | 说明 |
|----------|--------|------|
| `tests/rag/test_chunker.py` | 8 | 短章节、重叠、场景边界、句子保护、metadata |
| `tests/rag/test_embedder.py` | 6 | Mock 维度、批量、单例、异步非阻塞、一致性 |
| `tests/rag/test_vector_store.py` | 6 | 添加搜索、章节去重、最低门槛、空搜索、持久化、删除 |
| `tests/db/test_chunk_repo.py` | 3 | 批量插入、按章删除、按项目删除 |
| `tests/test_settlement_indexing.py` | 2 | indexing 成功入库、enabled=never 跳过 |

---

## 接口契约

```python
# Chunker
chunker = Chunker(chunk_size=500, chunk_overlap=100)
chunks = chunker.chunk_chapter(content, project_id, chapter_number, version_id,
                               known_characters=None, known_settings=None)

# Embedder
embedder = Embedder(model_name="shibing624/text2vec-base-chinese")
embeddings = await embedder.aembed([c.text for c in chunks])  # (N, 768)

# VectorStore
store = VectorStore(project_id, ChunkRepository())
await store.load()                           # 从 SQLite 加载
await store.add_chunks(chunks, embeddings)   # 写入 SQLite + 内存
results = await store.search(query_emb, top_k=5, min_similarity=0.3)

# CLI
songyan index --project-id xxx --chapters 1-10
songyan index --project-id xxx --rebuild
```

---

## 已知限制

1. **metadata 提取基础版**: characters_mentioned / setting_keys_mentioned 使用简单字符串匹配，后续可引入 LLM 辅助提取
2. **chunk_type 简化**: 仅实现了 dialogue / narrative 二分，description/action 检测待完善
3. **BGE-M3 未支持**: 环境限制（PyTorch 2.0 CPU），但模型名称可配置，用户可自行切换

---

## 变更文件清单

### 新增文件
- `src/songyan/models/rag.py`
- `src/songyan/rag/__init__.py`
- `src/songyan/rag/chunker.py`
- `src/songyan/rag/embedder.py`
- `src/songyan/rag/vector_store.py`
- `src/songyan/db/chunk_repo.py`
- `src/songyan/cli/commands/index.py`
- `tests/rag/test_chunker.py`
- `tests/rag/test_embedder.py`
- `tests/rag/test_vector_store.py`
- `tests/db/test_chunk_repo.py`
- `tests/test_settlement_indexing.py`

### 修改文件
- `src/songyan/models/__init__.py`
- `src/songyan/models/creative_mode.py`
- `src/songyan/db/schema.sql`
- `src/songyan/db/migrations.py`
- `src/songyan/db/__init__.py`
- `src/songyan/workflows/_helpers.py`
- `src/songyan/workflows/_nodes.py`
- `src/songyan/cli/main.py`
- `pyproject.toml`
- `creative_modes/webnovel.json`
- `creative_modes/literary.json`
- `creative_modes/hybrid.json`
- `creative_modes/webnovel_intense.json`
- `docs/STATUS.md`

---

*交接状态: 已完成，可进入 Task 050 (RAGRetriever + ContextManager 集成)*
