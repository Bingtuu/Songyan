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

## 4. 失败根因（双层）

### Bug A：`run_project_pipeline` 没有跳过已有 accepted 章节

**代码位置**: [`src/songyan/workflows/phase2_graph.py:279`](file:///c:/Vibe%20Project/Songyan/src/songyan/workflows/phase2_graph.py#L279)

```python
for chapter_number in range(start, end + 1):
    # ... 直接调用 run_chapter_pipeline，不做任何存在性检查
```

`run_project_pipeline` 只是简单遍历 `range(start, end + 1)`，**完全没有检查 `chapter_heads` 表中是否已有 `accepted` 状态**。种子章节 Ch1（通过 `import_seed_chapter` 写入，status=`accepted`，version 1）被完全忽略，系统重新走了一遍完整 pipeline（日志中 `version_number=2` 证明了这一点）。

**合理行为**：运行前查询 `chapter_heads`，跳过已有 `accepted` 的章节，直接从未完成章节继续。

### Bug B：RAG 索引的超时异常未被捕获

**代码位置**: [`src/songyan/workflows/_helpers.py:518`](file:///c:/Vibe%20Project/Songyan/src/songyan/workflows/_helpers.py#L518) 和 [`_nodes.py:2173`](file:///c:/Vibe%20Project/Songyan/src/songyan/workflows/_nodes.py#L2173)

```python
# _helpers.py
except (RuntimeError, OSError, ConnectionError, ValueError, TypeError):
    logger.exception("rag.index_failed", ...)

# _nodes.py
except (RuntimeError, OSError) as exc:
    logger.warning("settlement_extractor_node.rag_index_failed", ...)
```

两处都只捕获了 `RuntimeError` 和 `OSError`，但 `asyncio.wait_for(timeout=30.0)` 超时抛出的是 **`asyncio.TimeoutError`** 或 **`asyncio.CancelledError`**，这两个异常**不在捕获列表中**，直接向上穿透，导致整个 `project_pipeline` 崩溃。

即使代码注释写了"非阻塞：失败不导致 settlement 回滚"，超时例外完全绕过了这个保护。

**底层超时位置**: [`src/songyan/rag/embedder.py:123`](file:///c:/Vibe%20Project/Songyan/src/songyan/rag/embedder.py#L123)

```python
return await asyncio.wait_for(
    loop.run_in_executor(None, self.embed, texts),
    timeout=30.0   # ← 首次模型冷加载不足
)
```

**日志证据**:

```
2026-06-22 22:35:55 [error    ] rag.index_failed               chapter_number=1 project_id=proj-d860902d
CancelledError
```

**核心结论**：`run-40ceb306` 的失败不是因为"Ch1 需要 RAG"本身有问题，而是因为 **pipeline 没有正确识别 Ch1 已经存在**（Bug A），把它当作新章重新生成，然后在新的 RAG 索引步骤因为冷启动超时而崩溃（Bug B）。

---

## 5. 修复方案

### Bug A 修复：`run_project_pipeline` 支持跳过已有 accepted 章节

**方案 A1（推荐）**：在 `run_project_pipeline` 启动前，查询 `chapter_heads` 表，获取当前项目所有 `status='accepted'` 的章节号列表。遍历章节范围时，如果 `chapter_number` 在该列表中，直接跳过。

```python
# 伪代码
accepted_chapters = await unit_of_work.chapter_heads.get_accepted_chapters(project_id)
for chapter_number in range(start, end + 1):
    if chapter_number in accepted_chapters:
        logger.info("skipping_already_accepted", chapter_number=chapter_number)
        continue
    # ... 正常 pipeline
```

**方案 A2**：在 CLI `run` 命令层支持 `--resume` 或自动检测，只运行未完成的章节。

### Bug B 修复：RAG 索引异常捕获补全 + 超时延长

| 子方案 | 操作 | 影响 |
|--------|------|------|
| **B1（必做）** | `_helpers.py` 和 `_nodes.py` 的 catch 块增加 `asyncio.TimeoutError` | 确保超时不会阻断 pipeline |
| **B2（推荐）** | `timeout=30.0` → `timeout=120.0`（或 180.0） | 覆盖模型首次冷加载 + 后续编码 |
| B3 | 运行前预加载 embedding 模型 | 消除冷启动，但增加启动时间 |
| B4 | 将 RAG 索引失败降级为 warning（已有设计意图，但异常捕获有漏洞） | 不牺牲质量，只完善异常处理 |

---

## 6. 下一步

1. **执行 Bug A 修复**：修改 `phase2_graph.py` `run_project_pipeline`，跳过已有 `accepted` 的章节。
2. **执行 Bug B 修复**：
   - `_helpers.py:518` catch 块增加 `asyncio.TimeoutError`
   - `_nodes.py:2173` catch 块增加 `asyncio.TimeoutError`
   - `embedder.py:123` `timeout=30.0` → `timeout=120.0`
3. **单测验证**：补充 `TimeoutError` 被正确捕获的测试用例。
4. **重新启动 Ch1-Ch150 full single-run**：使用 `proj-d860902d` 断点续跑（从 Ch2 开始），或新建项目重新验证。

---

## 7. 关联文档

- `tasks/121o-ch1-ch18-focused-rerun-validation.md` — 前置验证基线
- `src/songyan/rag/embedder.py` — 超时配置源码
