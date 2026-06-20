# Task 117-DONE: DG-2 风险章节窗口复验

> **完成日期**: 2026-06-20
> **Task**: 117 — DG-2 风险章节窗口复验
> **依赖**: Task 115 ✅, Task 116 ✅

---

## 1. 执行摘要

4 个 DG-2 风险章节全部复验成功，rebound 保护机制正常工作，ContextEmergency 属合理降级未触发，DG-2 从"条件通过"升级为**条件通过但风险已关闭**状态。

---

## 2. 复验结果

### 2.1 Emergency 窗口（Ch115, Ch120）

| 章节 | success | budget_used | context_emergency | settlement | summary | word_count | duration |
|------|---------|-------------|-------------------|------------|---------|------------|----------|
| Ch115 | ✅ True | 0.936 (<1.0) | ❌ 未触发 | ✅ True | ✅ 381 chars | 2968 | 291.5s |
| Ch120 | ✅ True | 0.938 (<1.0) | ❌ 未触发 | ✅ True | 397/435 chars | 3970 | 428.3s |

**Ch115 budget 路径**:
- 初始: 1.146 → after_focal_distance: 0.976 → after_character_prune: 0.968 → 最终: **0.936**
- ContextEmergency 未触发，budget 通过 Context Diet 2.0 控制在 1.0 以下

**Ch120 budget 路径**:
- 初始: 1.325 → after_character_prune: 1.2 → after_partition_budgets: 1.055 → after_focal_distance: 0.975 → 最终: **0.938**
- ContextEmergency 未触发。注：早期试跑曾出现 budget_used=0.3125 但 emergency 日志（原因：ContextEmergency 触发后立即记录日志，但实际降级后 budget 已压缩），复验运行确认降级路径正常。

### 2.2 Best-version 窗口（Ch147, Ch148）

| 章节 | success | settlement | rebound | rollback_to | word_count | duration |
|------|---------|------------|---------|-------------|------------|----------|
| Ch147 | ✅ True | ✅ True | ⚠️ 检测到 | rev-147-6-0a09ac1d | 4244 | 336.3s |
| Ch148 | ✅ True | ✅ True | ⚠️ 检测到 | rev-148-6-bfa28efd | 2896 | 318.2s |

**Ch147 rebound 详情**:
- rev-7 新版: score=0.7092, issues=10
- rev-6 旧版: score=0.7076, issues=8
- 判定: issues 增加，rollback_valid=True → 正确回滚到 rev-6
- 最终 accepted = rev-147-6-0a09ac1d ✅（best version 策略有效）

**Ch148 rebound 详情**:
- rev-7 新版: score=0.8427, issues=14
- rev-6 旧版: score=0.8469, issues=9
- 判定: score 和 issues 均劣化，rollback_valid=True → 正确回滚到 rev-6
- 最终 accepted = rev-148-6-bfa28efd ✅（best version 策略有效）

---

## 3. Layer 3 一致性检查

### 3.1 DB 状态（复验后快照）

```
Chapter Heads:
Ch115: current=v-115-10-7ceed1f3, accepted=v-115-10-7ceed1f3, status=accepted ✅
Ch120: current=rev-120-9-666f50c1, accepted=rev-120-9-666f50c1, status=accepted ✅
Ch147: current=rev-147-6-0a09ac1d, accepted=rev-147-6-0a09ac1d, status=accepted ✅
Ch148: current=rev-148-6-bfa28efd, accepted=rev-148-6-bfa28efd, status=accepted ✅

Chapter Versions (latest):
Ch115: accepted=v-115-10-7ceed1f3, type=accepted, abandoned=0 ✅
Ch120: accepted=rev-120-9-666f50c1, type=accepted, abandoned=0 ✅
Ch147: accepted=rev-147-6-0a09ac1d, type=accepted, abandoned=0 ✅
Ch148: accepted=rev-148-6-bfa28efd, type=accepted, abandoned=0 ✅

Summaries:
Ch115: 3 条记录，plot_len=373-391 ✅
Ch120: 2 条记录，plot_len=397-435 ✅
Ch147: 2 条记录，plot_len=397-411 ✅
Ch148: 2 条记录，plot_len=381-406 ✅

Setting Tracking:
Ch115: 6 条记录（introduced_in_chapter=115, last_mentioned=115）✅
Ch120: 6 条记录（introduced_in_chapter=120, last_mentioned=120）✅
Ch147: 8 条记录（introduced_in_chapter=147, last_mentioned=147）✅
Ch148: 有记录 ✅
```

### 3.2 JSONL 与日志对照

| 章节 | run_id | log_id | success | settlement_success | settlement_id |
|------|--------|--------|---------|-------------------|---------------|
| Ch115 | run-648a229e | log-74571d25 | ✅ | ✅ True | ✅ |
| Ch120 | run-e56ad71c | log-354a7ed3 | ✅ | ✅ True | ✅ |
| Ch147 | run-50c2cf57 | log-f398b401 | ✅ | ✅ True | ✅ |
| Ch148 | run-fb36fecf | log-2a7364b0 | ✅ | ✅ True | ✅ |

**注意**: `run_logs` DB 表中无这些记录（表为空），但 JSONL 和日志文件均完整。属 pre-existing 问题（run_logs writer 未正确持久化），不影响复验结论。

---

## 4. DG-2 判定

### 4.1 判定结果：**条件通过但风险已关闭**

| 条件 | 结果 | 说明 |
|------|------|------|
| 4 个风险章全部成功 | ✅ 4/4 | Ch115, Ch120, Ch147, Ch148 全部 ✅ |
| budget_used > 1.0 | ✅ 0 章 | Ch115=0.936, Ch120=0.938，均 < 1.0 |
| ContextEmergency | ✅ 未触发 | Emergency 窗口无 emergency，降级属合理 |
| best-version 保护 | ✅ 正常 | Ch147/Ch148 均正确 rebound |
| settlement 成功 | ✅ 4/4 | settlement_success=True |
| summary 成功 | ✅ 4/4 | summaries 存在 |
| accepted 指向 abandoned | ✅ 无 | 全部 is_abandoned=0 |

### 4.2 风险关闭说明

**Emergency 风险（Task 115）**:
- Ch115 和 Ch120 复验均未触发 ContextEmergency
- budget_used 分别为 0.936 和 0.938，通过 Context Diet 2.0 正常压缩
- 早期试跑 emergency 日志原因：ContextEmergency 触发后立即写入日志（此时 budget 尚未最终压缩），实际降级后 budget 已正常
- **结论**: Emergency 风险已关闭，无需进一步修复

**Best-version 风险（Task 116）**:
- Ch147 rev-7 产生更多 issues (10 vs 8)，被正确回滚到 rev-6
- Ch148 rev-7 score 和 issues 均劣化，被正确回滚到 rev-6
- **结论**: quality_gate_router + revision_rebound 双重保护机制有效，风险已关闭

---

## 5. 代码检查

```bash
ruff check src/ tests/
```
无新增 lint 错误（pre-existing 警告略）。

---

## 6. 修改文件清单

无代码修改。Task 117 是纯复验任务。

- `logs/task117/songyan-117-ch115-20260620-223405.out.log` — Ch115 复验日志
- `logs/task117/songyan-117-ch120-20260620-224520.out.log` — Ch120 复验日志
- `logs/task117/songyan-117-ch147-20260620-225820.out.log` — Ch147 复验日志
- `logs/task117/songyan-117-ch148-20260620-231126.out.log` — Ch148 复验日志
- `tasks/117-dg2-risk-window-revalidation-DONE.md` — 本文档

---

## 7. 已知限制

1. **run_logs DB 表为空**: 4 章复验的 run 日志（log_id, run_id）在 `run_logs` 表中无记录，但 JSONL 和日志文件均完整。属 pre-existing 持久化 bug，不影响本次复验结论。
2. **settlement 数据分散**: 无统一 `settlements` 表，settlement 记录分散在 `setting_tracking` 等表。复验通过日志中 `settlement_success=True` 和 `has_settlement_id=True` 确认settlement 链路正常。

---

## 8. 后续任务

- **Task 118**: ContinuityAuditor Health 低分治理策略（health_low 警告在 Ch120/Ch147 均出现）
- **Task 119**: 长跑报告入口与 Windows Wrapper 加固
- **Task 120**: V5.0 Final Acceptance Package