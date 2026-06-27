# Task 091: Phase B Ch21-Ch50 端到端验证

> **Phase**: V4.0 Phase B — Agent 约束硬化
> **优先级**: P0
> **依赖**: Task 090a + 090b（Ch1-Ch20 验证通过且达标率 ≥ 65%）
> **预计工作量**: 中~高（3~5 天）

---

## Goal

长程验证 Phase B 效果：Ch21-Ch50 跑通，字数达标率 > 65%，平均 budget_used < 1.4，最大值 < 1.6，连续性健康分平均 ≥ 3.0。

## Context

本 Task 是 Phase B 的收官验证，也是**决策门 1** 的核心输入（结合复用 Task 081 脚本跑 Ch51-Ch70）。数据将决定 Phase C 是否启动。

**Task 087 遗留项闭环**：Task 087 因环境限制未能完成 Ch1-Ch20 端到端生命周期效果验证（context 数据量下降 ≥ 20%）。本 Task 在长程运行中通过 `_collect_lifecycle_stats` 收集 `setting_snapshots` / `foreshadowings` / `human_marks` / `character_states` 的 `active` / `dormant` / `archived` 分布：
- **Ch1-Ch20**：对比 V3.x 基线（已有数据），验证 LifecycleScheduler 实际效果
- **Ch21-Ch50**：观察 active→dormant→archived 迁移趋势是否持续，不要求与 V3.x 对比（V3.x 无此段基线数据）

## In Scope（必须完成）

- [ ] **Ch21-Ch50 端到端跑通**
- [ ] **字数达标率**：> 65%（±20%）
- [ ] **budget_used**：
  - Ch21-Ch50 平均值 < 1.4
  - Ch21-Ch50 最大值 < 1.6
- [ ] **连续性健康分**：平均 ≥ 3.0
- [ ] **V3.x 基线对比**：budget_used、字数、health_score 趋势
- [ ] **生命周期效果验证**：
  - 每章 accept 后触发 `_collect_lifecycle_stats`，记录 4 张表的 active/dormant/archived 数量
  - **Ch1-Ch20**：对比 V3.x 基线，验证 context 数据量下降 ≥ 20%
  - **Ch21-Ch50**：验证 active 占比持续下降、dormant/archived 累积增长趋势正常
  - 输出 `lifecycle_trend.json`：逐章迁移趋势
- [ ] **决策门 1 数据准备**：复用 Task 081 验证脚本快速跑 Ch51-Ch70（约 1 天），汇总 Ch21-Ch70 全段数据

## Out of Scope（明确不做）

- 任何业务逻辑代码修改（runner 的 stats 收集/断点续跑配置除外）
- Ch71+ 验证（Task 096/097）
- Phase C 架构工作

## 验收标准（Acceptance Criteria）

- [ ] Ch21-Ch50 端到端跑通
- [ ] 字数达标率 > 65%
- [ ] budget_used 平均 < 1.4，最大 < 1.6
- [ ] 连续性健康分平均 ≥ 3.0
- [ ] Ch51-Ch70 快速验证完成（用于决策门 1）
- [ ] 生命周期数据量下降 ≥ 20%（Ch1-Ch20 对比 V3.x 基线）
- [ ] Ch21-Ch50 active 占比呈下降趋势（不要求与 V3.x 对比）
- [ ] 生成了 `tasks/091-phase-b-ch21-ch50-e2e-DONE.md`

## 失败处理策略

| 场景 | 处理方式 |
|------|---------|
| 单章失败（非连续性错误）| runner 断点续跑，记录错误后继续下一章 |
| 连续 3 章失败 | 暂停，分析根因，修复后 resume |
| 达标率 < 65% | 暂停，回退到 090b 继续优化，不启动 091 报告 |
| budget_used 最大 > 1.6 | 标记为风险项，上报决策门 1 但不阻塞 |

## 参考

- `docs/v4.0-tech-plan.md` — 第 7.2 节、决策门 1
- `tasks/081-ch51-ch70-validation-DONE.md` — Ch51-Ch70 验证脚本复用
