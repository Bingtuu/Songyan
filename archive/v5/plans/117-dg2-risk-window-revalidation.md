# Task 117: DG-2 风险章节窗口复验

> **Phase**: V5.0 Phase 4 — DG-2 条件通过收口
> **优先级**: P1
> **依赖**: Task 115 完成；Task 116 完成
> **预计工作量**: 1 天

---

## Goal

在 Task 115 和 Task 116 完成后，针对 Ch115、Ch120、Ch147、Ch148 及必要相邻章节执行最小风险窗口复验，确认 DG-2 条件通过项已被解释、修复或收敛，且没有引入新的事实源、质量门或 budget 风险。

## Context

Task 114c 已证明 V5.0 可以完成 Ch111-Ch150 的连续长跑，但 DG-2 仍保留两个 P1 风险：

- Ch115、Ch120 触发 ContextEmergency。
- Ch147、Ch148 best-version 质量选择存在风险。

Task 117 不承担新的根因修复，而是作为收口复验任务，验证 Task 115/116 的修复在业务链路中有效。为了控制成本和变量，本 Task 默认执行最小窗口，不直接重跑 Ch111-Ch150。

## In Scope（必须完成）

- [ ] 确认 Task 115、116 的 DONE 文档和修复 commit 已完成。
- [ ] 选择复验窗口：默认 Ch115、Ch120、Ch147、Ch148；必要时扩展到 Ch114-Ch121、Ch146-Ch150。
- [ ] 使用 Windows 防卡协议执行长跑命令并保留 stdout/stderr。
- [ ] 生成复验报告，覆盖 QG、settlement、summary、budget、emergency、best-version。
- [ ] 检查 DB、JSONL 和报告三方一致性。
- [ ] 判断 DG-2 是否可从“条件通过”升级为“通过”，或保留条件通过但风险已解释。

## Out of Scope（明确不做）

- 不在复验期间临时修改代码。
- 不调整阈值或 Prompt。
- 不重跑 Ch111-Ch150 全量窗口，除非本任务发现系统性回归。
- 不新增质量治理策略，该事项归 Task 118。

## 实现方案

### 1. 复验窗口策略

按风险隔离原则分两组执行：

| 窗口 | 目标 | 默认章节 |
|------|------|----------|
| Emergency 窗口 | 验证 ContextEmergency 触发口径 | Ch115、Ch120 |
| Best-version 窗口 | 验证版本选择策略 | Ch147、Ch148 |

如单章复跑受到上游状态依赖影响，扩展为：

- Ch114-Ch121
- Ch146-Ch150

### 2. 复验指标

每章必须采集：

- success
- `budget_used`
- ContextEmergency
- revision/rewrite 次数
- QG 是否通过
- settlement 是否成功
- summary 是否成功
- accepted version 是否为 QG passed best
- accepted 是否指向 abandoned
- failure reason

### 3. 判定逻辑

| 情况 | 判定 |
|------|------|
| 4 个风险章全部成功，且 emergency/best 风险消除 | DG-2 可升级为通过 |
| 4 个风险章全部成功，emergency 属合理降级且已解释 | DG-2 保持条件通过但风险关闭 |
| 任一风险章 settlement/summary 失败 | 熔断，回到对应修复任务 |
| 任一章 `budget_used > 1.0` | 熔断，回到 Task 115 或 BudgetHardCeiling |
| 任一章 final head 指向非合格版本 | 熔断，回到 Task 116 |

## 接口契约

```bash
songyan run --project-id proj-e74ef1e4 --chapters 115-115 --mode-id webnovel_intense --auto-confirm
songyan run --project-id proj-e74ef1e4 --chapters 120-120 --mode-id webnovel_intense --auto-confirm
songyan run --project-id proj-e74ef1e4 --chapters 147-147 --mode-id webnovel_intense --auto-confirm
songyan run --project-id proj-e74ef1e4 --chapters 148-148 --mode-id webnovel_intense --auto-confirm
```

扩展窗口：

```bash
songyan run --project-id proj-e74ef1e4 --chapters 114-121 --mode-id webnovel_intense --auto-confirm
songyan run --project-id proj-e74ef1e4 --chapters 146-150 --mode-id webnovel_intense --auto-confirm
```

命令执行必须使用 PowerShell Job wrapper 和硬超时。

## 数据模型

不新增 DB 模型。复验报告可使用临时结构：

```python
class RiskWindowResult(BaseModel):
    chapter_number: int
    success: bool
    budget_used: float | None
    context_emergency: bool
    quality_gate_passed: bool
    settlement_success: bool
    summary_success: bool
    accepted_version_id: str | None
    best_version_valid: bool | None
    failure_reason: str | None = None
```

## 执行流程

1. **前置检查**
   - 确认 Task 115、116 已完成。
   - 运行相关聚焦测试和 `ruff check src/ tests/`。
   - 确认工作区无未解释代码改动。

2. **单章复验**
   - 分别执行 Ch115、Ch120、Ch147、Ch148。
   - 每章结束后立即检查 JSONL 和 DB。

3. **窗口复验**
   - 若单章通过但存在上下文依赖疑虑，执行扩展窗口。
   - 如单章已明确失败，不继续扩大窗口。

4. **报告生成**
   - 生成 DG-2 risk window report。
   - 对比 Task 114c 原报告指标。

5. **结论判定**
   - 明确 DG-2 状态：通过、条件通过但风险关闭、仍需修复。
   - 生成 `tasks/117-dg2-risk-window-revalidation-DONE.md`。

## 测试要求

### Layer 1: 前置测试

- [ ] Task 115 新增/更新测试通过。
- [ ] Task 116 新增/更新测试通过。
- [ ] `ruff check src/ tests/` 通过。

### Layer 2: 复验运行

- [ ] Ch115 复验成功。
- [ ] Ch120 复验成功。
- [ ] Ch147 复验成功。
- [ ] Ch148 复验成功。
- [ ] 必要扩展窗口成功。

### Layer 3: 一致性检查

- [ ] JSONL success 与 DB accepted 状态一致。
- [ ] accepted version 不指向 abandoned。
- [ ] accepted 后 settlement 和 summary 存在。
- [ ] 报告统计与 JSONL 一致。

## 验收标准（Acceptance Criteria）

| 指标 | 目标 |
|------|------|
| 风险章节完成率 | 4/4 成功 |
| QG 通过率 | 4/4 |
| settlement 成功 | 4/4 |
| summary 成功 | 4/4 |
| budget | 0 章 `budget_used > 1.0` |
| best-version | Ch147/Ch148 final version 均符合 Task 116 规则 |
| emergency | Ch115/Ch120 状态与 Task 115 结论一致 |
| 报告 | 生成复验报告并更新 V5 状态入口 |

## 风险与应对

| 风险 | 应对 |
|------|------|
| 单章复跑无法复现长跑上下文 | 扩展到相邻窗口，但不直接全量重跑 |
| 复验暴露新阻断 | 立即熔断，回到对应修复任务 |
| 成本失控 | 限定最大窗口 Ch114-Ch121 与 Ch146-Ch150 |

## 参考文档

- `archive/v5/plans/115-context-emergency-review.md`
- `archive/v5/plans/116-best-version-quality-selection-fix.md`
- `tasks/114-ch101-ch150-streaming-validation-DONE.md`
- `archive/v5/reports/report-task114c-dg2-ch111-ch150.md`
