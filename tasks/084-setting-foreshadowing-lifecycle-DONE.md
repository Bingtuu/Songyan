# Task 084 交接报告：setting_snapshots + foreshadowings repository 生命周期策略

> **完成日期**: 2026-06-07
> **状态**: ✅ 已完成
> **对应 Commit**: 待填充

---

## 交付物清单

| # | 交付物 | 路径 | 状态 |
|---|--------|------|:----:|
| 1 | SettingSnapshotRepository 生命周期策略 | `src/songyan/db/settlement_repo.py` | ✅ |
| 2 | ForeshadowingRepository 生命周期策略 | `src/songyan/db/settlement_repo.py` | ✅ |
| 3 | 查询过滤（lifecycle_status='active'） | `src/songyan/db/settlement_repo.py` | ✅ |
| 4 | 单元测试 | `tests/db/test_setting_foreshadowing_lifecycle.py` | ✅ |
| 5 | 交接报告 | 本文件 | ✅ |

---

## 实现摘要

### SettingSnapshotRepository

| 方法 | 功能 | 条件 |
|------|------|------|
| `list_by_project()` | 只返回 `lifecycle_status='active'` | SQL WHERE 过滤 |
| `archive_stale()` | active → dormant | 10 章未提及（JOIN setting_tracking）且非 critical |
| `archive_very_stale()` | dormant → archived | 20 章未提及 |

**is_critical 例外**：通过 JOIN `human_marks` 表（priority>=8 + mark_type='setting'）排除。

### ForeshadowingRepository

| 方法 | 功能 | 条件 |
|------|------|------|
| `list_active()` | 只返回 `lifecycle_status='active'` + `status IN ('planted', 'due')` | 双重过滤 |
| `archive_overdue()` | active → dormant | overdue > 5 章，排除 resolved |
| `archive_very_overdue()` | dormant → archived | overdue > 15 章，排除 resolved |
| `archive_resolved()` | resolved → archived | 无论生命周期状态 |

---

## 关键设计决策

1. **双重状态系统**：
   - `status`：业务语义（planted/due/overdue/resolved）
   - `lifecycle_status`：生命周期（active/dormant/archived）
   - `list_active()` 同时过滤两者，确保 resolved 记录不进入上下文

2. **setting_snapshots 的"未提及"判断**：
   - 通过 JOIN `setting_tracking` 表的 `last_mentioned_chapter` 字段
   - 不修改 setting_snapshots 表结构，复用现有追踪数据

3. **向后兼容**：
   - 现有数据默认 `lifecycle_status='active'`，查询行为不变
   - `archive_overdue` 默认 window=5（可覆盖原有行为）

---

## 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_list_active_filters_lifecycle_status` | foreshadowings 查询叠加 lifecycle_status 过滤 |
| `test_archive_overdue` | 5 章 overdue → dormant |
| `test_archive_overdue_does_not_touch_resolved` | resolved 不被 archive_overdue 归档 |
| `test_archive_very_overdue` | 15 章 overdue → archived |
| `test_archive_resolved` | resolved → archived |
| `test_list_by_project_filters_lifecycle_status` | setting_snapshots 查询过滤 |
| `test_archive_stale` | 10 章未提及 → dormant |
| `test_archive_stale_does_not_touch_critical` | priority>=8 的 human_mark 保护 setting |
| `test_archive_stale_boundary` | 边界：10 章不归档，11 章归档 |

**测试结果**: 9 passed

---

## 回归验证

- `tests/ -k "foreshadow or setting"`: 95 passed（含原有 Task 078 测试全部通过）
- `tests/db/test_lifecycle_scheduler.py`: 13 passed, 4 skipped
- 无新增失败

---

## 验收标准核对

- [x] `pytest tests/db/test_setting_foreshadowing_lifecycle.py -v` 全部通过
- [x] 不违反不可违背规则（数据访问集中在 repository.py）
- [x] 生成了 `tasks/084-setting-foreshadowing-lifecycle-DONE.md`

---

## 已知限制

1. `setting_snapshots` 的 `chapter_number` 在 `list_by_project()` 中仍使用 ordinal 估算（i+1），非精确章节号
2. `is_critical` 判断仅基于 `human_marks.priority>=8`，未复用 `_is_setting_critical()` 的动态逻辑（需要 chapter_goal，repository 层无法获取）
3. `character_states` 和 `human_marks` 生命周期策略 — Task 085

---

## 参考

- `docs/v4.0-tech-plan.md` — 第 4.1 节
- `tasks/083-lifecycle-schema-scheduler-DONE.md` — 上游依赖
- `tasks/085-character-mark-lifecycle.md` — 下游依赖
