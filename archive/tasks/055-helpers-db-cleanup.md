# Task 055: _helpers.py 直接 DB 访问清理

> **Phase**: V3.0 Layer 0 — 修复稳定性底线
> **优先级**: P1
> **依赖**: 054
> **预计工作量**: 小（0.5~1 天）

---

## Goal

消除 `workflows/_helpers.py` 中绕过 Repository 层直接调用 `get_db()` 的代码，全部改为通过正式 Repository 接口访问数据。

## Context

`_helpers.py` 中的 `load_open_threads()` 和 `load_chapter_goal()` 直接执行 SQL，违反规则 53（Agent 不直接拿 DB connection）。这些辅助函数被 `context_manager_node` 和 `settlement_extractor_node` 调用，是 pipeline 中的高频路径。

## In Scope（必须完成）

- [ ] **`load_open_threads()` 重构**: 
  - 当前：直接 `SELECT ... FROM summaries WHERE ...`
  - 改为：通过 `SummaryRepository.list_recent()` 获取摘要，在调用方构建 `OpenThread` 列表
- [ ] **`load_chapter_goal()` 重构**:
  - 当前：直接 `SELECT ... FROM chapter_goals WHERE ...`
  - 改为：通过 `ChapterGoalRepository.get_by_chapter()`（已存在）获取
- [ ] **全量扫描**: 检查 `_helpers.py` 中是否还有其他直接 `get_db()` 调用，一并清理
- [ ] **回归测试**: 确保 `test_phase1_graph.py` 和 `test_context_manager.py` 通过

## Out of Scope（明确不做）

- 不新增 Repository 方法（只使用已有的）
- 不修改 `context_manager.py` 或 `phase1_graph.py` 的调用逻辑（只改数据来源）
- 不拆分 `_helpers.py`（属于 056）

## 接口契约

```python
# 删除以下直接 DB 访问函数，改为 Repository 调用
# - load_open_threads() 中的 async with get_db()
# - load_chapter_goal() 中的 async with get_db()
```

## 测试要求

### Layer 2: 模块测试
- [ ] `test_helpers_no_raw_db_access`: 验证 `_helpers.py` 中不再有 `get_db()` 导入或使用

### Layer 3: 集成测试
- [ ] `test_context_manager_node_with_open_threads`: 确认重构后 ContextManager 仍能正确加载 open_threads
- [ ] `test_settlement_node_goal_loaded`: 确认 SettlementExtractor 仍能正确加载 chapter_goal

## 验收标准

- [ ] `rg "get_db" src/songyan/workflows/_helpers.py` 返回空
- [ ] `pytest tests/ -k "phase1_graph or context_manager" -v` 全部通过
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/055-helpers-db-cleanup-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 4.1 P1-3
- `AGENTS.md` — 规则 53
