# Task 050 — RAGRetriever + ContextManager 集成 ✅

> **Phase**: 8b  
> **优先级**: P0  
> **完成日期**: 2026-06-03  
> **执行人**: Kimi Code CLI

---

## 完成情况

| 交付物 | 状态 | 位置 |
|--------|------|------|
| SoftReference 扩展 | ✅ | `src/songyan/models/context.py` — rag_retrieval 类型 |
| RAGRetriever | ✅ | `src/songyan/rag/retriever.py` (208 行) |
| RAG 工具函数 | ✅ | `src/songyan/rag/utils.py` (47 行) |
| ContextManager 改造 | ✅ | `src/songyan/agents/context_manager.py` — _build_rag_soft_references + rag_chunks 参数 |
| Writer Prompt 1.0.6 | ✅ | `prompts/cards/writer/1.0.6.yaml` |
| Writer Agent 改造 | ✅ | `src/songyan/agents/writer.py` — rag_results 变量构造 |
| 流水线集成 | ✅ | `src/songyan/workflows/_helpers.py` — 检索 + 注入 ContextPackage |
| CLI 开关 | ✅ | `src/songyan/cli/main.py` — `--rag-mode` / `--skip-rag` |
| 单元测试 | ✅ | 28 个新测试全部通过 |

---

## 测试统计

```
pytest tests/rag/test_utils.py tests/rag/test_retriever.py tests/test_context_manager_rag.py tests/test_writer_prompt_rag.py -v
28 passed in 0.52s
```

| 测试文件 | 用例数 | 说明 |
|----------|--------|------|
| `tests/rag/test_utils.py` | 10 | never/always/auto 启用判断、阈值计算（含边界） |
| `tests/rag/test_retriever.py` | 8 | query 构造（加权、元指令过滤、recent_plot）、Mock 检索、完整流程 |
| `tests/test_context_manager_rag.py` | 6 | RAG→SoftReference 转换、relevance_score 上限、ContextPackage 集成、优先级、排序 |
| `tests/test_writer_prompt_rag.py` | 4 | RAG 分区渲染、空列表省略、非 RAG ref 不渲染、文本截断 |

**回归测试**: `tests/test_context_manager.py` + `tests/creative_modes/` = 83 passed，零回归。

---

## 关键设计决策

| 决策 | 值 |
|------|-----|
| Prompt 版本 | 1.0.6（manifest default_version 更新） |
| RAG 结果传递 | SoftReference(type="rag_retrieval") → writer.py 提取为 rag_results |
| 检索位置 | `_helpers.py` async wrapper |
| Query 加权 | target_events 重复 + obligations 过滤元指令 + recent_plot 摘要 |
| RAG 优先级 | relevance_score = min(similarity + 0.3, 1.0) |
| 启用阈值 | auto 模式下 `max(10, min(50, estimated_chapters * 0.3))` |
| CLI 覆盖 | `SONGYAN_RAG_MODE` 环境变量 |

---

## 接口契约

```python
# RAG 启用判断
from songyan.rag.utils import should_enable_rag, compute_rag_threshold
should_enable_rag(current_chapter, project, rag_config)  # → bool
compute_rag_threshold(project)  # → int

# RAG 检索
from songyan.rag.retriever import RAGRetriever
retriever = RAGRetriever(embedder, vector_store, rag_config)
results = await retriever.retrieve_for_chapter(project_id, chapter_number, chapter_goal, recent_plot)

# CLI
songyan run --project-id xxx --chapters 1-10 --skip-rag
songyan run --project-id xxx --chapters 1-10 --rag-mode always
```

---

## Writer Prompt 1.0.6 新增分区

```yaml
{% if rag_results %}
## 历史相关段落（自动检索）
以下段落来自历史章节，经语义检索判定与当前写作内容相关。
**注意**：这些段落仅供参考，不要求必须引用。

{% for chunk in rag_results %}
- [第{{ chunk.chapter_number }}章 {{ chunk.metadata.chunk_type }}] {{ chunk.text[:200] }}...
{% endfor %}
{% endif %}
```

---

## 已知限制

1. **Writer Prompt 版本切换**: 目前通过 manifest default_version 统一切换，尚未支持按 creative mode 差异化版本
2. **关键词降级简化**: `_keyword_fallback` 使用简单字符串匹配，后续可优化为 TF-IDF
3. **chunk_type 传递**: writer.py 中 rag_results 的 chunk_type 目前固定为 "narrative"，后续可从 SoftReference metadata 传递

---

## 变更文件清单

### 新建文件
- `src/songyan/rag/retriever.py`
- `src/songyan/rag/utils.py`
- `prompts/cards/writer/1.0.6.yaml`
- `tests/rag/test_retriever.py`
- `tests/rag/test_utils.py`
- `tests/test_context_manager_rag.py`
- `tests/test_writer_prompt_rag.py`

### 修改文件
- `src/songyan/models/context.py`
- `src/songyan/agents/context_manager.py`
- `src/songyan/agents/writer.py`
- `src/songyan/workflows/_helpers.py`
- `prompts/cards/writer/_manifest.yaml`
- `src/songyan/cli/main.py`
- `docs/STATUS.md`

---

*交接状态: 已完成，可进入 Task 051 (A/B 测试)*
