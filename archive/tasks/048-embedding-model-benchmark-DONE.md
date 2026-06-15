# Task 048 — Embedding 模型选型基准测试 ✅

> **Phase**: 8b  
> **优先级**: P0  
> **完成日期**: 2026-06-03  
> **执行人**: Kimi Code CLI

---

## 完成情况

| 交付物 | 状态 | 位置 |
|--------|------|------|
| 基准测试脚本 | ✅ | `evals/embedding_benchmark.py` |
| 文本切分模块 | ✅ | `evals/chunking.py` |
| 查询集定义 | ✅ | `evals/queries.py` |
| 评估指标扩展 | ✅ | `evals/metrics.py` |
| MiniLM 基线实测 | ✅ | `evals/output/benchmark_minilm_v2.json` |
| text2vec 实测 | ✅ | `evals/output/benchmark_text2vec.json` |
| bge-large-zh 实测 | ✅ | `evals/output/benchmark_bge_large_zh.json` |
| 选型报告 | ✅ | `docs/review/embedding_benchmark_report.md` |
| 单元测试 | ✅ | `tests/evals/test_embedding_benchmark.py`（26 passed） |

---

## 三模型实测结果

| 模型 | Top-1 | Top-3 | Top-5 | MRR | 延迟 | 大小 | 环境 |
|------|-------|-------|-------|-----|------|------|------|
| **text2vec-base-chinese** | **90.0%** | **90.0%** | **100%** | **0.925** | **55ms** | **409MB** | ✅ 完美 |
| bge-large-zh-v1.5 | 80.0% | 90.0% | 90.0% | 0.850 | 127ms | 1.3GB | ✅ 可运行 |
| all-MiniLM-L6-v2 | 30.0% | 80.0% | 80.0% | 0.517 | 52ms | 80MB | ✅ 可运行 |
| BGE-M3 | — | — | — | — | — | 2.3GB | ❌ 内存不足 |

---

## 选型结论

**推荐 `shibing624/text2vec-base-chinese` 作为 Phase 8b 默认 Embedding 模型**。

理由：
1. 实测 Top-1 命中率 **90%**，远超 BGE-M3 的理论预期
2. 409MB 体积 / 55ms 延迟，普通 CPU 环境即可流畅运行
3. 对中文专有名词（"认知补丁"、"120Hz干扰器" 等）召回效果极佳
4. 零 API 成本，符合 V2.0 成本约束

**备选**: `BAAI/bge-large-zh-v1.5`（内存充裕的生产环境）

---

## 推荐配置（供 Task 049）

```python
DEFAULT_RAG_EMBEDDING_CONFIG = {
    "model_name": "shibing624/text2vec-base-chinese",
    "dimension": 768,
    "chunk_size": 500,
    "chunk_overlap": 100,
    "min_similarity": 0.3,
    "top_k": 5,
    "device": "cpu",
}
```

---

## 变更文件清单

- `evals/chunking.py` — 新增
- `evals/queries.py` — 新增
- `evals/embedding_benchmark.py` — 新增
- `evals/metrics.py` — 扩展
- `tests/evals/test_embedding_benchmark.py` — 新增
- `docs/review/embedding_benchmark_report.md` — 新增
- `docs/STATUS.md` — 更新

---

*交接状态: 已完成，可进入 Task 049*
