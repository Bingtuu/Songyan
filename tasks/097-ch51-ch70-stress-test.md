# Task 097: Ch51-Ch70 压力测试（修复后）

> **Phase**: V4.0 Phase B — 压力测试
> **优先级**: P0
> **依赖**: Task 096（Ch2-Ch50 回归通过）
> **预计工作量**: 中（2-3 天）

---

## Goal

使用 Task 092-094 的修复，对 Ch51-Ch70（决策门 1 区间）进行压力测试，验证长程稳定性。

---

## Context

### 当前基线（Task 091）

| 指标 | Ch51-Ch70 |
|------|-----------|
| 字数达标率 | 60.0% |
| 平均字数比 | 1.127 |
| 最大字数比 | 1.676 |
| 平均 health_score | 2.0 |
| 平均 token_budget | 0.996 |
| 最大 token_budget | 1.104 |
| 截断率 | 10.0% |

### 为什么 Ch51-Ch70 是关键区间

- 这是 V3.x 验证中发现的"蜜月期结束"拐点
- 生命周期管理在此区间首次展现效果（归档窗口进入 20 章）
- 090b 的 rewrite 机制在此区间频繁触发
- **本 Task 验证修复后，此区间的稳定性是否显著改善**

### 修复后预期

| 指标 | 目标 |
|------|------|
| 字数达标率 | 60.0% → **> 70%** |
| 平均字数比 | 1.127 → **~1.05** |
| 最大字数比 | 1.676 → **< 1.4** |
| health_score | 2.0 → **≥ 3.0** |
| token_budget | 0.996 → **< 1.1** |
| 0 失败 | 保持 |

---

## In Scope（必须完成）

### 1. 端到端验证 Ch51-Ch70

复用 Task 096 的 runner：

```bash
python scripts/task_095_runner.py --start 51 --end 70
# 或使用断点续跑：从 Ch50 的 DB 继续
python scripts/task_095_runner.py --resume --start 51 --end 70
```

配置：
- 种子：`evals/seeds/scifi_webnovel.json`
- 输出目录：`evals/output/task_097_scifi_webnovel/`
- 续跑起点：`evals/output/task_096_scifi_webnovel/test.db`（Ch50 状态）

### 2. 核心指标

与 Task 096 保持一致，特别关注：
- **长程稳定性**：Ch60、Ch65、Ch70 三个节点的指标是否平稳
- **生命周期曲线**：active settings / foreshadowings 是否继续稳定在 90±10
- **revision 反弹**：revision_rebound_detected 触发频率
- **settlement 失败率**：是否 < 2%

### 3. 决策门 1 评估输入

Task 096 的结果将直接决定：
- **如果达标**：进入 Task 097（Ch71-Ch100 扩展验证），证明 100 章可行性
- **如果不达标**：回退到 Task 092/093/094 继续优化

---

## Out of Scope（明确不做）

- Ch71+ 验证（Task 097）
- 代码修改
- 手动质量审查

---

## 验收标准（Acceptance Criteria）

- [ ] Ch51-Ch70 端到端跑通，**0 失败**
- [ ] 字数达标率 **> 70%**（目标）或 **> 60%**（最低可接受）
- [ ] budget_used 平均 **< 1.2**
- [ ] budget_used 最大 **< 1.4**
- [ ] health_score 平均 **≥ 3.0**
- [ ] token_budget 平均 **< 1.2**
- [ ] token_budget 最大 **< 1.4**
- [ ] 单场景章节 **< 2 章**
- [ ] 生成压力测试报告 `evals/output/task_097_scifi_webnovel/report.md`
- [ ] 生成了 `tasks/097-ch51-ch70-stress-test-DONE.md`

---

## 失败处理策略

| 情况 | 处理 |
|------|------|
| 达标率 ≥ 70% + health ≥ 3.0 | **通过**，进入 Task 097 |
| 达标率 60%-70% 或 health 2.5-3.0 | 有条件通过，记录限制，进入 Task 097（优化目标写入 Task 098 改进计划） |
| 达标率 < 60% 或 health < 2.5 | **暂停**，回退到 092/093/094 继续优化 |

---

## 参考

- `scripts/task_091_resilient_runner.py`
- `evals/output/task_091_scifi_webnovel/report.md` — 基线报告
- `tasks/096-ch2-ch50-regression.md`
