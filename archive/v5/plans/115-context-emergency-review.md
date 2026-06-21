# Task 115: ContextEmergency 触发复核与校准

> **Phase**: V5.0 Phase 4 — DG-2 条件通过收口
> **优先级**: P1
> **依赖**: Task 114c 完成；`archive/v5/reports/report-task114c-dg2-ch111-ch150.md`
> **预计工作量**: 1-2 天

---

## Goal

复核 Task 114c 中 Ch115、Ch120 触发 ContextEmergency 的原因，判断其属于合理降级、过早触发还是报告口径误判，并在不破坏 BudgetHardCeiling 的前提下完成校准。

## Context

Task 114c 已完成 Ch111-Ch150 分段流式验证，40/40 章节均完成 `accept + settlement + summary`，且没有 budget 超限、settlement validation failed 或 summary 缺失。

DG-2 仍为条件通过，唯一硬性未达标项是 ContextEmergency 次数不为 0。DG-2 报告显示：

| 章节 | budget_used | char_states | soft_refs | emergency | QG | settlement | summary |
|------|-------------|-------------|-----------|-----------|----|------------|---------|
| Ch115 | 0.268 | 1 | 0 | Y | Y | Y | Y |
| Ch120 | 0.311 | 1 | 0 | Y | Y | Y | Y |

两章最终结果成功，且 budget_used 很低，因此需要优先判断 emergency 是真实必要降级，还是 ContextPackage 裁剪、指标采集或报告判定的过早触发。

## In Scope（必须完成）

- [ ] 读取 Ch115、Ch120 的 JSONL、stdout/stderr、Context metrics 和 DB 状态。
- [ ] 定位 ContextEmergency 的触发路径、触发阈值和触发前后的 context 组成差异。
- [ ] 对比 Ch114-Ch121 相邻章节，确认是否只有 Ch115/Ch120 异常。
- [ ] 判断触发类型：
  - 合理降级：触发前确有 hard ceiling 风险。
  - 过早触发：触发时真实 budget 压力不足。
  - 报告误判：运行状态未触发 emergency，但指标记录为 Y。
- [ ] 如属过早触发，修复触发条件、指标采集或报告口径。
- [ ] 补充聚焦测试，覆盖低 budget 场景下 emergency 不应被误触发。
- [ ] 复跑 Ch115、Ch120 或最小相邻窗口，验证修复结果。

## Out of Scope（明确不做）

- 不放宽 `budget_used > 1.0` 硬门禁。
- 不修改 Writer/Reviewer 质量阈值。
- 不重跑 Ch111-Ch150 全窗口，除非 Task 117 要求。
- 不处理 Ch147/Ch148 best-version 风险，该事项归 Task 116。

## 实现方案

### 1. 现场复盘

- 从 `logs/chapter_runs/` 中定位包含 Ch115、Ch120 的有效 run 记录。
- 读取每章 `context_metrics`、`budget_used`、`context_emergency`、`char_states`、`soft_refs`、`revision`、`QG` 字段。
- 查询 DB 中对应 chapter head、accepted version、summary 和 settlement 状态，确认业务结果未污染。

### 2. 触发链路定位

重点检查以下模块：

- `src/songyan/agents/context_manager/`
- `src/songyan/workflows/_helpers.py`
- `src/songyan/workflows/_nodes.py`
- `src/songyan/evals/streaming_report.py`

需要明确：

- ContextEmergency 是在 context assembly 前、裁剪中还是报告生成阶段标记。
- 标记是否来自真实 hard ceiling 触发，还是来自空 context bucket、fallback context 或默认值。
- emergency 后是否导致角色、设定、伏笔信息过度裁剪。

### 3. 修复策略

按诊断结论选择最小修复：

| 诊断结论 | 修复方向 |
|----------|----------|
| 合理降级 | 不改代码，更新报告解释和 DONE 文档验收口径 |
| 过早触发 | 调整触发条件，使低 budget 且 context 稳定时不进入 emergency |
| 报告误判 | 修复 JSONL/report 字段映射，不改变运行逻辑 |
| 采集缺失 | 补齐 Context metrics，避免 `None` 或默认值误判 |

### 4. 回归验证

- 运行新增/更新的 context emergency 聚焦测试。
- 复跑 Ch115、Ch120。
- 如修复影响 context assembly 共享逻辑，补跑 Ch114-Ch121 最小窗口。

## 接口契约

```python
def is_context_emergency(metrics: dict[str, object]) -> bool:
    """根据真实 context metrics 判断是否触发 emergency."""
    ...
```

```bash
songyan run --project-id proj-e74ef1e4 --chapters 115-115 --mode-id webnovel_intense --auto-confirm
songyan run --project-id proj-e74ef1e4 --chapters 120-120 --mode-id webnovel_intense --auto-confirm
```

实际接口以现有源码为准。本 Task 优先复用现有函数，不强制新增公共 API。

## 数据模型

原则上不新增持久化模型。若现有 JSONL metrics 无法区分真实 emergency 与报告误判，可在 chapter run metrics 中补充字段：

```python
class ContextEmergencyMetrics(BaseModel):
    triggered: bool
    reason: str | None = None
    budget_used_before: float | None = None
    budget_used_after: float | None = None
    pruned_sections: list[str] = []
```

## 执行流程

1. **证据收集**
   - 定位 Ch115、Ch120 的 run id、JSONL 和日志。
   - 输出一份临时复核表，列出触发前后 metrics。

2. **根因分类**
   - 对比源码触发条件和报告统计逻辑。
   - 给出“合理降级 / 过早触发 / 报告误判 / 采集缺失”结论。

3. **最小修复**
   - 只修改与诊断结论直接相关的代码。
   - 补充测试，避免用阈值放宽掩盖问题。

4. **回放验证**
   - 复跑 Ch115、Ch120。
   - 必要时复跑 Ch114-Ch121。

5. **文档收口**
   - 生成 `tasks/115-context-emergency-review-DONE.md`。
   - 更新 `tasks/V5-README.md`、`docs/STATUS.md`、`README.md`、`docs/INDEX.md`。

## 测试要求

### Layer 1: 指标判定测试

- [ ] 低 `budget_used` 且 context sections 正常时，不触发 emergency。
- [ ] 超过 hard ceiling 或关键 section 缺失时，触发 emergency。
- [ ] `None`、空列表、缺失字段不会被错误当作 emergency。

### Layer 2: 报告测试

- [ ] DG-2 报告中 emergency 章节统计与 JSONL 一致。
- [ ] 合理降级能在报告中标明原因。

### Layer 3: 业务回放

- [ ] Ch115 单章回放完成 `accept + settlement + summary`。
- [ ] Ch120 单章回放完成 `accept + settlement + summary`。
- [ ] 如执行 Ch114-Ch121，全部章节无新增 P0/P1 阻断。

## 验收标准（Acceptance Criteria）

| 指标 | 目标 |
|------|------|
| Ch115/Ch120 触发原因 | 100% 可解释，有日志或指标证据 |
| DG-2 emergency 口径 | 与 JSONL/DB 证据一致 |
| budget 硬门禁 | 任意复跑章节 `budget_used <= 1.0` |
| 业务链路 | 复跑章节全部完成 `accept + settlement + summary` |
| 回归测试 | 聚焦测试通过；`ruff check src/ tests/` 通过 |
| 文档 | DONE、STATUS、README、INDEX、V5-README 同步 |

## 风险与应对

| 风险 | 应对 |
|------|------|
| 修复后 context 变大导致 budget 回升 | 保留 `budget_used > 1.0` 硬门禁，先做单章验证 |
| 把合理 emergency 错误消除 | 必须给出触发前后 metrics，不凭结果成功判定误触发 |
| 报告口径与运行口径继续分叉 | 报告测试必须直接读取 JSONL 样本断言 |

## 参考文档

- `tasks/114-ch101-ch150-streaming-validation-DONE.md`
- `archive/v5/reports/report-task114c-dg2-ch111-ch150.md`
- `tasks/V5-README.md`
- `docs/STATUS.md`
