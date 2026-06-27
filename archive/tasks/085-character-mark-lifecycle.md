# Task 085: human_marks + character_states repository 生命周期策略

> **Phase**: V4.0 Phase A — 数据生命周期 + 动态预算
> **优先级**: P0
> **依赖**: Task 083（Schema + Scheduler 框架就绪）
> **预计工作量**: 中（2 天）

---

## Goal

实现 `human_marks` 和 `character_states` 两张表的生命周期策略，让 protagonist 永不过期、priority≥8 的标记保留，预期 human_marks 减少 ~50%、character_states 非 arc 角色精简。

## Context

V3.x 中 human_marks 按时间窗口过滤（`chapter_window=3`）后仍持续增长（Ch70=100+），character_states 按 arc 窗口过滤后非 arc 角色仍有冗余。本 Task 在 Task 083 的框架上填充这两张表的具体策略。

| 表 | active → dormant | dormant → archived | 例外 |
|----|-----------------|-------------------|------|
| human_marks | 最近 10 章未提及且 unresolved | 已 resolved 或 > 20 章未提及 | `priority >= 8` 保留 |
| character_states | 最近 5 章未出场 | 15 章未出场 | protagonist 永不过期 |

## In Scope（必须完成）

- [ ] **human_marks repository 层**：
  - `archive_stale_marks(project_id, current_chapter, window=10)`：10 章未提及 + unresolved → dormant
  - `archive_resolved_marks(project_id, window=20)`：resolved 或 > 20 章 → archived
  - `priority >= 8` 的记录永不改变状态
  - ContextManager 中 human_marks 加载只取 active
- [ ] **character_states repository 层**：
  - `archive_stale_characters(project_id, current_chapter, window=5)`：5 章未出场 → dormant
  - `archive_very_stale_characters(project_id, current_chapter, window=15)`：15 章未出场 → archived
  - `importance='protagonist'` 永不过期
  - ContextManager 中 character_states 加载只取 active（protagonist 始终包含）
- [ ] **单元测试**：
  - 状态迁移正确
  - protagonist/priority≥8 例外生效
  - BudgetPruner 过滤后 token 数下降

## Out of Scope（明确不做）

- setting_snapshots / foreshadowings 策略（Task 084）
- LifecycleScheduler 框架（Task 083）
- 动态预算（Task 086）
- arc 窗口过滤逻辑（Task 080 已实现，本 Task 只增加 status 过滤）

## 接口契约

```python
# src/songyan/db/repository.py（新增方法）

class HumanMarkRepository:
    async def archive_stale(
        self, project_id: str, current_chapter: int, window: int = 10
    ) -> int:
        """10 章未提及 + unresolved → dormant。priority>=8 除外。"""
        ...
    
    async def archive_resolved(
        self, project_id: str, current_chapter: int, window: int = 20
    ) -> int:
        """resolved 或 >20 章 → archived。"""
        ...
    
    async def get_active_for_project(
        self, project_id: str, chapter_number: int
    ) -> list[HumanMark]:
        """只返回 active（含 priority>=8 的 dormant，它们被保留）。"""
        ...

class CharacterStateRepository:
    async def archive_stale(
        self, project_id: str, current_chapter: int, window: int = 5
    ) -> int:
        """5 章未出场 → dormant。protagonist 除外。"""
        ...
    
    async def archive_very_stale(
        self, project_id: str, current_chapter: int, window: int = 15
    ) -> int:
        """15 章未出场 → archived。"""
        ...
    
    async def get_active_for_project(
        self, project_id: str, chapter_number: int
    ) -> list[CharacterState]:
        """返回 active + protagonist（无论状态）。"""
        ...
```

## 测试要求

### Layer 2: 模块测试
- [ ] 正向：模拟数据验证 5 章/10 章/15 章/20 章窗口
- [ ] 例外：protagonist 状态不变；priority=8 的 mark 状态不变
- [ ] 边界：第 5 章刚好触及 → dormant；第 4 章 → active

### Layer 3: 集成测试
- [ ] BudgetPruner 组装后 character_states token 数下降 ≥ 15%

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/db/test_mark_lifecycle.py -v` 全部通过
- [ ] `pytest tests/db/test_character_lifecycle.py -v` 全部通过
- [ ] BudgetPruner 过滤后 human_marks 数量下降 ≥ 30%（Ch30 模拟数据）
- [ ] 生成了 `tasks/085-character-mark-lifecycle-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 4.1 节
- `tasks/080-character-appearance-window.md` — arc 窗口逻辑（只增加 status 过滤）
