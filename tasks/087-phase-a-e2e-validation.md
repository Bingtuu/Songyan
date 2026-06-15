# Task 087: Phase A 端到端验证 + 决策门 0

> **Phase**: V4.0 Phase A — 数据生命周期 + 动态预算
> **优先级**: P0
> **依赖**: Task 083, 084, 085, 086（Phase A 全部代码完成）
> **预计工作量**: 中（3 天）

---

## Goal

验证 Phase A 全部改动（生命周期管理 + 动态预算 + 规则分组）的端到端效果：Ch1-Ch20 跑通、全量回归通过、context 数据量下降 ≥ 20%。触发决策门 0。

## Context

Phase A 是 V4.0 的核心 Quick Wins。如果生命周期管理 + 动态预算效果不显著，后续 Phase B/C 需要调整预期。本 Task 是 Phase A 的收官验证。

**前置条件**：`evals/` 验证脚本需同步更新以支持 `dynamic_budget` 和 `lifecycle_status` 参数。

## In Scope（必须完成）

- [ ] **evals 脚本同步更新**：
  - `evals/` 目录下的 runner 支持读取 `dynamic_budget` 和 `lifecycle_status` 配置
  - 验证脚本可输出 `active_count` / `dormant_count` / `archived_count` 统计
- [ ] **Ch1-Ch20 端到端验证**：
  - 使用真实 LLM（DeepSeek）或 Mock 模式跑通 Ch1-Ch20
  - 收集 metrics：budget_used、final_tokens、字数、生命周期状态分布
- [ ] **全量回归测试**：`pytest -x -q` 通过（失败数 < 5）
- [ ] **数据量对比**：与 V3.x 基线对比，context 数据量（setting_snapshots + foreshadowings + human_marks + character_states）下降 ≥ 20%
- [ ] **决策门 0 判断**：
  - 通过：失败数 < 5，数据量下降 ≥ 20% → 继续推进 Phase B
  - 未通过：暂停，分析根因

## Out of Scope（明确不做）

- Ch21+ 的验证（Task 090a/091）
- 字数约束硬化（Task 088/089）
- 任何 Phase B/C/D 的工作

## 验收标准（Acceptance Criteria）

- [ ] `evals/` 验证脚本已更新支持新参数
- [ ] `pytest -x -q` 通过（失败数 < 5）
- [ ] Ch1-Ch20 端到端跑通（无论真实 LLM 或 Mock）
- [ ] context 数据量下降 ≥ 20%（对比 V3.x 同章节基线）
- [ ] 决策门 0 结论记录到 `docs/STATUS.md`
- [ ] 生成了 `tasks/087-phase-a-e2e-validation-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 7.1 节
- `tasks/083-lifecycle-schema-scheduler.md`
- `tasks/084-setting-foreshadowing-lifecycle.md`
- `tasks/085-character-mark-lifecycle.md`
- `tasks/086-dynamic-budget.md`
