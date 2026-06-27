# Task 084: setting_snapshots + foreshadowings repository 生命周期策略

> **Phase**: V4.0 Phase A — 数据生命周期 + 动态预算
> **优先级**: P0
> **依赖**: Task 083（Schema + Scheduler 框架就绪）
> **预计工作量**: 中（2 天）

---

## Goal

实现 `setting_snapshots` 和 `foreshadowings` 两张表的生命周期策略，让 BudgetPruner 自动过滤 dormant/archived 数据，预期 setting_snapshots 减少 ~40%、foreshadowings 减少 ~30%。

## Context

V3.x 中 setting_snapshots 按 `chapter_number` 全量加载（Ch70=129 条），foreshadowings 按 `status='active'` 全量加载（Ch70=62 条）。本 Task 在 Task 083 提供的 `status` 字段和 Scheduler 框架上，填充这两张表的具体策略逻辑。

| 表 | active → dormant | dormant → archived | 例外 |
|----|-----------------|-------------------|------|
| setting_snapshots | 最近 10 章内未提及 | 20 章未提及 | `is_critical=True` 永不休眠 |
| foreshadowings | overdue 超过 5 章 | resolved 或 overdue > 15 章 | — |

## In Scope（必须完成）

- [ ] **setting_snapshots repository 层**：
  - `archive_stale_settings(project_id, current_chapter, window=10)`：10 章未提及 → dormant
  - `archive_very_stale_settings(project_id, current_chapter, window=20)`：20 章未提及 → archived
  - `is_critical=True` 的记录永不改变状态
  - 所有查询方法新增 `status='active'` 过滤条件
- [ ] **foreshadowings repository 层**：
  - `archive_overdue_foreshadowings(project_id, current_chapter, overdue_window=5)`：overdue > 5 章 → dormant
  - `archive_resolved_foreshadowings(project_id)`：status='resolved' → archived
  - `archive_very_overdue(project_id, current_chapter, window=15)`：overdue > 15 章 → archived
  - 所有查询方法新增 `status='active'` 过滤
- [ ] **BudgetPruner 适配**：`hard_constraints` 分区中 human_marks 只加载 active，setting_snapshots 只加载 active
- [ ] **单元测试**：
  - 模拟 Ch1-Ch30 数据，验证各阶段状态迁移正确
  - `is_critical` 例外生效
  - BudgetPruner 过滤后 token 数下降

## Out of Scope（明确不做）

- human_marks / character_states 的策略（Task 085）
- LifecycleScheduler 框架本身（Task 083）
- 动态预算公式（Task 086）
- 任何 Agent / Prompt / Workflow 修改

## 接口契约

```python
# src/songyan/db/repository.py（新增方法）

class SettingSnapshotRepository:
    async def archive_stale(
        self, project_id: str, current_chapter: int, window: int = 10
    ) -> int:
        """将 N 章未提及的 setting_snapshots 标记为 dormant。返回影响行数。"""
        ...
    
    async def archive_very_stale(
        self, project_id: str, current_chapter: int, window: int = 20
    ) -> int:
        """将 M 章未提及的 dormant 记录标记为 archived。"""
        ...
    
    async def get_active_for_project(
        self, project_id: str, chapter_number: int
    ) -> list[SettingSnapshot]:
        """只返回 status='active' 的记录（替换原全量查询）。"""
        ...

class ForeshadowingRepository:
    async def archive_overdue(
        self, project_id: str, current_chapter: int, window: int = 5
    ) -> int:
        """将 overdue > N 章的 foreshadowings 标记为 dormant。"""
        ...
    
    async def archive_resolved(self, project_id: str) -> int:
        """将所有 resolved 标记为 archived。"""
        ...
    
    async def get_active_for_project(
        self, project_id: str, chapter_number: int
    ) -> list[ForeshadowingItem]:
        """只返回 status='active' 的记录。"""
        ...
```

## 数据模型

无需新增 Pydantic 模型。复用现有 `SettingSnapshot` 和 `ForeshadowingItem`，通过 `status` 字段过滤。

## 测试要求

### Layer 2: 模块测试
- [ ] 正向：模拟 30 章数据，验证 10 章/20 章窗口正确触发状态迁移
- [ ] 边界：第 10 章刚好触及 → dormant；第 9 章 → 仍为 active
- [ ] 例外：`is_critical=True` 记录状态不变
- [ ] 查询过滤：`get_active_for_project()` 不返回 dormant/archived

### Layer 3: 集成测试
- [ ] BudgetPruner 组装 ContextPackage 时，setting_snapshots token 数下降 ≥ 20%

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/db/test_setting_lifecycle.py -v` 全部通过
- [ ] `pytest tests/db/test_foreshadowing_lifecycle.py -v` 全部通过
- [ ] BudgetPruner 过滤后 setting_snapshots 数量下降 ≥ 20%（Ch30 模拟数据）
- [ ] 不违反不可违背规则（数据访问集中在 repository.py）
- [ ] 生成了 `tasks/084-setting-foreshadowing-lifecycle-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 4.1 节
- `tasks/083-lifecycle-schema-scheduler.md` — 上游依赖
