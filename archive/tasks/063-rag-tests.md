# Task 063: RAG 模块测试补充

> **Phase**: V3.x Layer 3 — 系统化质量守卫
> **优先级**: P2
> **依赖**: 无
> **预计工作量**: 中（1~2 天）

---

## Goal

为 V2.x 新增的 RAG 模块补充独立测试，覆盖 chunker、embedder、retriever、vector_store、utils 五个文件。

## Context

RAG 模块（Task 048~050）是 V2.x 最后阶段快速上线的能力，当前 5 个文件零独立测试。虽然 Layer 2 的 30 章运行会间接验证 RAG，但缺乏单元测试意味着后续任何修改都可能引入回退。

## In Scope（必须完成）

| 文件 | 新增测试数 | 测试内容 |
|------|-----------|---------|
| `rag/chunker.py` | >=3 | 中文句子边界、特殊标点拆分、空输入、短章节单 chunk |
| `rag/embedder.py` | >=2 | 正常嵌入、空文本处理、batch shape |
| `rag/retriever.py` | >=3 | 单命中、多命中聚合、空结果、章节去重 |
| `rag/vector_store.py` | >=2 | 写入/查询往返、重复写入幂等、空存储 |
| `rag/utils.py` | >=1 | 辅助函数边界值 |

## Out of Scope（明确不做）

- 不做真实 Embedding 模型加载测试（用 Mock）
- 不做大规模性能测试
- 不做 RAG 与 Writer 的集成测试（已在 Task 050 完成）

## 验收标准

- [ ] RAG 模块新增测试 >=11 个
- [ ] `pytest tests/rag/ -v` 全部通过
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/059-rag-tests-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 7.1 测试补充
