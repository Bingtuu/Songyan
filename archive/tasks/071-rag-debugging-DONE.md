# Task 071: RAG 独立调试 — DONE

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-05
> **实际工作量**: ~2 小时

---

## 根因分析

058b 运行日志显示 RAG 在 Ch30 触发但 `vector_store.total_chunks=0`，检索结果为空。

**Root Cause（双重问题）:**

1. **primary**: `human_gate_node` 的 `accept` 路径只更新了 `ChapterHead`，**未更新 `ChapterVersion.version_type`**。`settlement_extractor_node` 检查 `version.version_type in ("accepted", "edited")` 失败，导致 `_index_accepted_chapter` **从未被调用**。

2. **secondary**: `_index_accepted_chapter` 中 `SettingTrackingRepository.list_by_project()` 返回 `list[dict]`，但代码试图访问 `.setting_key`（对象属性访问），导致 `AttributeError`。该异常被 `except Exception` 吞掉，日志中仅显示 `rag.index_failed`，没有详细错误信息。

---

## 修复内容

### Fix 1: 触发 RAG 索引条件

| 文件 | 修改 |
|------|------|
| `src/songyan/db/repository.py` | `ChapterVersionRepository` 新增 `accept_version(version_id)` 方法 |
| `src/songyan/workflows/_nodes.py` | `human_gate_node` accept 路径调用 `accept_version()`，使 `version_type="accepted"` |

### Fix 2: dict 访问兼容性

| 文件 | 修改 |
|------|------|
| `src/songyan/workflows/_helpers.py` | `known_settings = [s.setting_key ...]` → `[s.get("setting_key") ...]` |

### Enhancement: 诊断日志

| 文件 | 新增日志 |
|------|----------|
| `src/songyan/workflows/_helpers.py` | `rag.chunked`, `rag.embedded`, `rag.indexed`（含 embedding_shape） |
| `src/songyan/rag/vector_store.py` | `vector_store.add_start`（chunk_count/embedding_shape）、`vector_store.add_done`、`vector_store.loaded`（含 embedding_shape） |

---

## 测试覆盖

| 测试文件 | 数量 | 说明 |
|----------|------|------|
| `tests/rag/test_rag_indexing.py` | 5 passed | **新增**：accept_version、index→retrieve 往返、embedding shape 一致性、空内容、retrieve_for_chapter |
| `tests/rag/` 全量 | 43 passed | 原有 38 + 新增 5 |
| `tests/` 全量 | **1166 passed** | 零失败 |

集成测试中的 `version_type` 断言已同步更新：accept 后 revision 版本的 `version_type` 从 `"revision"` → `"accepted"`。

---

## 验证结果

从测试日志可见 RAG 索引现已正常工作：

```
rag.chunked    chapter_number=2 chunk_count=1 project_id=...
rag.embedded   chapter_number=2 embedding_shape=(1, 768) project_id=...
rag.indexed    chapter_number=2 chunk_count=1 embedding_shape=(1, 768) project_id=...
```

---

## 与 Task 071 原始验收标准的差异

| 原始标准 | 实际完成 | 说明 |
|----------|----------|------|
| 定位 root cause | ✅ | 双重根因：version_type 未更新 + dict 属性访问错误 |
| 修复写入路径 | ✅ | accept_version + dict.get 修复 |
| 增加诊断日志 | ✅ | vector_store 和 _index_accepted_chapter 均增加 |
| 写入→加载→检索往返测试 | ✅ | 5 个新增集成测试 |
| `pytest tests/rag/` 通过 | ✅ | 43 passed |
| 更新 STATUS.md | ✅ | 测试数 1161→1166，071 标记完成 |
| 生成 DONE 文件 | ✅ | 本文件 |

---

## 参考

- `src/songyan/workflows/_nodes.py` — `human_gate_node` accept 路径修复
- `src/songyan/workflows/_helpers.py` — `_index_accepted_chapter` 诊断日志 + dict 访问修复
- `src/songyan/db/repository.py` — `accept_version()` 方法
- `tests/rag/test_rag_indexing.py` — 端到端索引与检索测试
