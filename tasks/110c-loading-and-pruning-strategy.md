# Task 110c: 加载端智能过滤与分级裁剪

> **Phase**: V5.0 Phase 4 准备 — 加载与裁剪优化
> **优先级**: P0
> **依赖**: Task 110b 完成
> **预计工作量**: 2-3 天

---

## Goal

在信息进入 ContextPackage 时做更智能的过滤，并在超预算时分级压缩，避免 ContextEmergency 直接清空所有软信息。

---

## Context

### 当前问题

1. **加载端过滤不足**：非当前 arc 角色仍被加载（只是降级），低相关设定仍进入候选池。
2. **ContextEmergency 过于粗暴**：一旦触发，只保留主角 + 最近 1 章摘要，Writer 失去伏笔、设定、配角等关键信息。
3. **没有分区预算**：某个分区（如 character_states）膨胀会挤压其他分区。

---

## In Scope

- [ ] **加载端按相关性过滤**
  - `soft_references` 只保留与 `chapter_goal.target_events` 关键词相关的 setting
  - `character_states` 非当前 arc 角色直接 skip（不只是降级为 compact）
  - `foreshadowings` 只保留 due/overdue + 当前章相关 + 最近 planted 的 N 个

- [ ] **动态硬上限（章节阶段相关）**
  - Ch80+：`MAX_SETTING_INPUT` 从 10 降到 6
  - Ch80+：`MAX_FORESHADOWING` 从 8 降到 5
  - Ch80+：`MAX_CHARACTER_STATES` 从 4 降到 3
  - 根据 `context_pressure` 动态调整

- [ ] **分级 ContextEmergency**
  - Level 1（budget_used 1.0–1.2）：保留主角 + top2 配角；soft_references top 5；foreshadowing due/overdue；arc/volume 摘要截断 50%
  - Level 2（1.2–1.5）：只保留主角；soft_references top 3；foreshadowing overdue；清空 open_threads/permanent_scenes
  - Level 3（>1.5）：当前核裁模式

- [ ] **分区预算制**
  - character_states: 30%、recent_plot: 20%、soft_references: 15%、foreshadowing: 10%、其他: 25%
  - 各分区先内部压缩，跨分区裁剪作为最后手段

- [ ] **保留可恢复性**
  - 压缩后的信息保留 `source_version_id`
  - emergency 模式下仍保留 top 3 soft_references、overdue foreshadowings、priority=10 marks

## Out of Scope

- 不新增 Agent/Workflow 节点
- 不修改 Writer Prompt
- 不删除 P0 硬约束（chapter_goal, creative_brief, genre_rules, mode_rules）

---

## 验收标准

| 指标 | 目标 |
|------|------|
| ContextEmergency 次数 | Ch80-Ch100 较 105b 下降 ≥ 50% |
| Level 3 emergency 次数 | ≤ 5/50 |
| 加载前初始 token | Ch90+ 较 105b 下降 ≥ 25% |
| 全量回归测试 | 无新增失败 |
| 关键信息可恢复性 | 压缩后仍保留 source_version_id |

---

## 技术要点

- 修改 `context_manager/__init__.py` 中 `assemble_context_package`
- 修改 `BudgetPruner` 增加分区预算逻辑
- 修改 `_context_emergency` 为分级模式
- 修改 `_build_character_snapshots` 增加 arc 过滤

---

## 风险

- **过滤过度导致 coherence 下降**：非当前 arc 但重要的角色被 skip。缓解：protagonist/antagonist 永远不过滤。
- **分级 emergency 仍触发 Level 3**：如果生产端未控制好，Level 3 仍会发生。缓解：与 Task 110a/110b 配合。
- **分区预算僵化**：某些章节需要更多角色状态。缓解：分区比例按章节类型微调。
