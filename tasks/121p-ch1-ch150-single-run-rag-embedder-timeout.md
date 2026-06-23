# Task 121p: Ch1-Ch150 Full Single-Run — RAG Embedder Timeout Blocker

> **日期**: 2026-06-22
> **类型**: V5.1 preflight / full single-run evidence
> **状态**: ❌ 中断（Ch1 完成后 RAG 索引超时）
> **run_id**: `run-40ceb306`
> **project_id**: `proj-d860902d`

---

## 1. 任务边界

基于 Task 121o（Ch1-Ch18 18/18 成功）的验证基线，启动新的干净项目执行 Ch1-Ch150 full single-run，获取 V5.0 single-run rehearsal 的最终证据。

---

## 2. 执行记录

| 项 | 值 |
|----|----|
| run_id | `run-40ceb306` |
| project_id | `proj-d860902d`（新建，深空锚点 / scifi / webnovel_intense） |
| 启动时间 | 2026-06-22 22:29:07 |
| 中断时间 | 2026-06-22 22:35:34 |
| wrapper 结果 | `WARN_BUSINESS_DONE_WITH_ERROR` |
| final_status | `partial` |
| 完成章节 | **仅 Ch1** |
| 失败阶段 | Ch1 结算后的 RAG 向量索引 |

---

## 3. Ch1 流程复盘

Ch1 的全流程实际已成功完成：

| 阶段 | 状态 | 关键指标 |
|------|------|----------|
| goal_planner | 完成 | event_count=3, word_count_target=3000 |
| creative_director | 完成 | forbidden_count=7, tension_count=3 |
| writer (v2) | 完成 | 3127字, scenes=2 |
| rule_auditor | 完成 | rhythm_score=3.97 |
| llm_auditor | 完成 | issues=10, overall_score=8.02 |
| review_merger (round 0) | 需修订 | overall=0.8421, has_major=True |
| revision_handler (v3) | 完成 | issues_fixed=8, preservation_ratio=1.0 |
| review_merger (round 1) | 需修订 | overall=0.9095, has_major=True |
| revision_handler (v4) | 完成 | issues_fixed=3, preservation_ratio=0.9953 |
| review_merger (round 2) | 需修订 | overall=0.9169, has_major=True |
| rewrite (v5) | 结构失败 | word_count=3659 → hard_truncate=3570, missing_ending_hook |
| human_gate | accept | rollback 到 best_version `rev-1-4-b822cca0` |
| settlement_extractor | 完成 | 5 新设定, 3 伏笔, 5 角色更新 |
| summary_writer | 完成 | summary_length=372 |
| **rag.index** | **失败** | **CancelledError（30s 超时）** |

---

## 4. 失败根因

RAG 向量索引阶段调用 `Embedder.aembed()` 时，sentence-transformers 模型首次冷加载耗时超过 30 秒，触发 `asyncio.wait_for` 超时，抛出 `CancelledError`，导致 pipeline 终止。

**代码位置**: [`src/songyan/rag/embedder.py:123`](file:///c:/Vibe%20Project/Songyan/src/songyan/rag/embedder.py#L123)

```python
return await asyncio.wait_for(
    loop.run_in_executor(None, self.embed, texts),
    timeout=30.0   # ← 首次模型加载不足
)
```

**日志证据**:

```
2026-06-22 22:35:55 [error    ] rag.index_failed               chapter_number=1 project_id=proj-d860902d
CancelledError
```

---

## 5. 修复方案

| 方案 | 操作 | 影响 |
|------|------|------|
| **A（推荐）** | `timeout=30.0` → `timeout=120.0`（或 180.0） | 覆盖模型首次冷加载 + 后续编码 |
| B | 运行前预加载 embedding 模型 | 消除冷启动，但增加启动时间 |
| C | 将 RAG 索引失败降级为 warning，不阻断 pipeline | 牺牲 RAG 检索质量，不推荐 |

---

## 6. 下一步

1. 执行方案 A：修改 `embedder.py` 超时配置。
2. 重新启动 Ch1-Ch150 full single-run（新建 run_id / 复用当前项目断点续跑）。
3. 验证 RAG 索引不再超时。

---

## 7. 关联文档

- `tasks/121o-ch1-ch18-focused-rerun-validation.md` — 前置验证基线
- `src/songyan/rag/embedder.py` — 超时配置源码
