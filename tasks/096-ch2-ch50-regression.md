# Task 096: Ch2-Ch50 回归验证（修复后）

> **Phase**: V4.0 Phase B — 回归验证
> **优先级**: P0
> **依赖**: Task 092 + Task 093 + Task 094（所有修复已完成）
> **预计工作量**: 中（2-3 天）

---

## Goal

使用 Task 092-094 的修复，对 Ch2-Ch50 进行端到端回归验证，确认修复效果。

---

## Context

### 当前基线（Task 091）

| 指标 | Ch2-Ch20 | Ch21-Ch50 |
|------|----------|-----------|
| 字数达标率 | 63.2% | 33.3% |
| 平均字数比 | 1.040 | 1.203 |
| 最大字数比 | 1.232 | 1.768 |
| 平均 health_score | 3.33 | 1.2 |
| 平均 token_budget | 1.122 | 1.144 |
| 最大 token_budget | 1.291 | 1.246 |

### 修复后预期（Task 092-094）

| 指标 | 目标改善 |
|------|---------|
| 字数达标率 | 33.3% → **> 75%** |
| 平均字数比 | 1.203 → **~1.08** |
| 最大字数比 | 1.768 → **< 1.4** |
| health_score | 1.2 → **≥ 3.5** |
| token_budget | 不变（预期 **~1.1**） |
| 单场景章节 | **< 3 章** |
| Rewrite 触发率 | **< 20%** |

---

## In Scope（必须完成）

### 1. 端到端验证 Ch2-Ch50

复用 `scripts/task_091_resilient_runner.py`（或创建 `task_095_runner.py`）：

```bash
python scripts/task_095_runner.py --start 2 --end 50
```

配置：
- 种子：`evals/seeds/scifi_webnovel.json`
- 输出目录：`evals/output/task_096_scifi_webnovel/`
- 模式：webnovel
- 模型：deepseek/deepseek-chat

### 2. 核心指标收集

每章收集（与 Task 091 保持一致）：
- word_count / target_word_count（预算使用比）
- token_budget_used
- revision_count / revision_triggered
- health_score / orphaned_count / overdue_count
- scenes_count（新增）
- rewrite_reason（新增）
- budget_compliance（新增）

### 3. 对比报告

与 Task 091 基线对比：

| 指标 | 091 基线 | 096 修复后 | 改善幅度 |
|------|---------|-----------|---------|
| 字数达标率 | 49.3% | ? | +?% |
| 平均字数比 | 1.136 | ? | -? |
| 最大字数比 | 1.768 | ? | -? |
| health_score | 2.0 | ? | +? |
| token_budget | 1.073 | ? | ~? |
| 单场景章节 | N/A | ? | N/A |
| Rewrite 触发率 | ~30% | ? | -?% |

---

## Out of Scope（明确不做）

- Ch51+ 验证（Task 097）
- 代码修改
- 手动审查章节质量

---

## 验收标准（Acceptance Criteria）

- [ ] Ch2-Ch50 端到端跑通，**0 失败**
- [ ] 字数达标率 **> 75%**（目标）或 **> 65%**（最低可接受）
- [ ] budget_used 平均 **< 1.3**
- [ ] budget_used 最大 **< 1.5**
- [ ] health_score 平均 **≥ 3.5**（目标）或 **≥ 3.0**（最低可接受）
- [ ] token_budget 平均 **< 1.3**
- [ ] token_budget 最大 **< 1.5**
- [ ] 单场景章节 **< 3 章**
- [ ] 生成对比报告 `evals/output/task_096_scifi_webnovel/report.md`
- [ ] 生成了 `tasks/096-ch2-ch50-regression-DONE.md`

---

## 失败处理策略

| 情况 | 处理 |
|------|------|
| 达标率 ≥ 75% | 通过，进入 Task 097 |
| 达标率 65%-75% | 记录问题，进入 Task 097（带已知限制） |
| 达标率 < 65% | 暂停，回退到 092/093/094 继续优化 |

---

## 参考

- `scripts/task_091_resilient_runner.py` — Runner 模板
- `evals/output/task_091_scifi_webnovel/report.md` — 基线报告
- `tasks/092-writer-scene-budget.md`
- `tasks/094-health-score-settlement-fixes.md`
- `tasks/095-scene-structure-protection.md`
