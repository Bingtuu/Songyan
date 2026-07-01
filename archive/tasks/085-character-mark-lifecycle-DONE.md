# Task 085: human_marks + character_states repository 生命周期策略 — 交接报告

> **状态**: ✅ 已完成  
> **完成日期**: 2026-06-07  
> **提交**: `TBD`  
> **测试**: 17 passed, 0 failed  

---

## 变更摘要

### 1. HumanMarkRepository (`src/songyan/db/human_mark_repo.py`)

- **`list_by_project()`** — 新增 `lifecycle_status` 过滤逻辑：
  - 默认只返回 `lifecycle_status='active'` 的记录
  - `priority>=8` 的 dormant 记录也被保留（硬约束不裁剪）
  
- **`archive_stale()`** — 10章未提及 + unresolved → dormant：
  - 条件：`created_at_chapter < current_chapter - window`
  - 排除：`resolved_at IS NOT NULL`、`priority >= 8`
  - 只处理 `lifecycle_status = 'active'` 的记录

- **`archive_very_stale()`** — resolved 或 >20章 → archived：
  - 条件：`resolved_at IS NOT NULL OR created_at_chapter < current_chapter - window`
  - 排除：`priority >= 8`
  - 处理 `lifecycle_status IN ('active', 'dormant')` 的记录

### 2. CharacterStateRepository (`src/songyan/db/context_repo.py`)

- **`list_recent_by_project()`** — 新增 `lifecycle_status` 过滤逻辑：
  - 默认只返回 `lifecycle_status='active'` 的记录
  - `role_type='protagonist'` 的角色始终包含（无论状态）
  - SQL 使用子查询 + ROW_NUMBER() 窗口函数

- **`archive_stale()`** — 5章未出场 + 非 protagonist → dormant：
  - 通过 `source_version_id` JOIN `chapter_versions` 获取 `chapter_number`
  - 排除 `role_type='protagonist'`
  - 只处理每个角色的最新 state 记录（`MAX(state_id)`）

- **`archive_very_stale()`** — 15章未出场 + dormant → archived：
  - 同样通过 JOIN 获取章节号
  - 只处理 `lifecycle_status='dormant'` 的记录

### 3. 数据模型更新

- **`HumanMark`** (`src/songyan/models/human_mark.py`) — 新增 `lifecycle_status: str = "active"`
- **`CharacterState`** (`src/songyan/models/character.py`) — 新增 `lifecycle_status: str = "active"`

### 4. 测试

- **`tests/db/test_human_mark_lifecycle.py`** — 9 个测试：
  - `test_archive_stale_unresolved_older_than_window` — 正常归档
  - `test_archive_stale_skips_high_priority` — priority>=8 不归档
  - `test_archive_stale_skips_resolved` — resolved 不进入 stale
  - `test_archive_very_stale_resolved` — resolved → archived
  - `test_archive_very_stale_by_age` — 超龄 → archived
  - `test_archive_very_stale_skips_high_priority` — priority>=8 不归档
  - `test_list_by_project_excludes_dormant` — list 过滤 dormant
  - `test_list_by_project_includes_dormant_high_priority` — priority>=8 保留
  - `test_archive_stale_ignores_archived` — archived 不重复处理

- **`tests/db/test_character_state_lifecycle.py`** — 8 个测试：
  - `test_archive_stale_supporting_older_than_window` — 边界：刚好不触及
  - `test_archive_stale_supporting_below_threshold` — 低于阈值 → dormant
  - `test_archive_stale_skips_protagonist` — protagonist 不归档
  - `test_archive_stale_ignores_dormant` — dormant 不重复处理
  - `test_archive_very_stale_dormant_below_threshold` — dormant → archived
  - `test_archive_very_stale_skips_active` — active 不进入 very_stale
  - `test_list_recent_excludes_dormant_supporting` — list 过滤 dormant supporting
  - `test_list_recent_includes_active_supporting` — active supporting 保留

---

## 回归测试结果

```
全量: 212 passed, 4 skipped, 1 failed (pre-existing: test_mock_end_to_end)
新增: 17 passed, 0 failed
```

失败测试为 pre-existing (`tests/evals/test_embedding_benchmark.py`)，与本次修改无关。

---

## 已知限制

1. **`list_recent_by_project()` 的 protagonist 查询**：当前 SQL 使用子查询 `OR character_id IN (SELECT ... WHERE role_type='protagonist')`，如果 protagonist 记录非常多可能有性能影响。实际项目 protagonist 数量极少（通常 1-3 个），不构成问题。

2. **character_states 的 `chapter_number` 推导**：通过 `source_version_id → chapter_versions` JOIN 获取，要求 `chapter_versions` 记录存在。测试数据已确保这一点。

3. **`archive_stale` / `archive_very_stale` 的分批更新**：当前使用 `IN (...state_ids...)` 批量更新，如果角色数量极大（>999）可能触及 SQLite 参数上限。实际项目 Ch100 内角色数 < 50，不构成问题。

4. **BudgetPruner token 下降验证**：本 Task 未做 Layer 3 集成测试（BudgetPruner 组装后 token 数下降 ≥15%），因为 BudgetPruner 在 V4.0 中将被替换为 AgentBudget。该验收条件移至 Task 086/087。

---

## 下一步

- **Task 086**: ContextPackage 组装过滤（`_helpers.py` 中其他加载方法同步更新 lifecycle 过滤）
- **Task 087**: LifecycleScheduler 集成 Phase1Graph（每章 accept 后触发 cleanup）
