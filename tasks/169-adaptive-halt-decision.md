# Task 169: 自适应 halt 判定

> **Phase**: V7 阶段 Y（enforce 可生产化）
> **优先级**: P0（Task 168 后的直接后续；Task 170 前置）
> **状态**: ✅ 完成（169a / 169b 均已完成）
> **依赖**: Task 168 DONE（`AdaptiveGateDataPlaneReport` 数据面）
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 Y

---

## Goal

把 enforce 门禁从“绝对阈值 / 单点触发”升级为“基于趋势、样本充分性和多信号一致性的自适应判定”。169 不新增质量信号，只消费 Task 168 的 `AdaptiveGateDataPlaneReport`，输出可审计、可回放的 halt / observe 判定。

Task 169 的目标不是让系统更激进地停，而是让它**停得更准**：

- 正常波动不停。
- 孤立抖动不停。
- 样本不足不停。
- 真正持续退化才 halt。

## 背景

现有 `_gates.py` 已有 ContextEmergency / health_low 候选门禁，但它依赖临时输入：

- `previous_p1_counts`
- `recent_results`
- `min_health_score_so_far`
- 单章 `ContinuityReport`

这些输入在 phase2 运行时拼装，难以审计和复算。Task 168 已把这些分散信号沉淀为 SQLite 快照和窗口报告。Task 169 应基于该报告做纯判定，并把判定结果本身也持久化，避免 gate 行为只存在 JSONL run log。

## 拆分结论

Task 169 拆为两个子任务：

| Task | 名称 | 边界 |
|------|------|------|
| 169a | 自适应 halt 判定引擎与决策账本 | ✅ 已完成：纯函数判定 + Pydantic 模型 + SQLite decision ledger；不接入 workflow |
| 169b | workflow 接入与 observe/enforce 行为 | ✅ 已完成：在 phase2 运行后处理点接入 169a；默认 observe，可显式 enforce；不新增 workflow 节点 |

拆分原因：169a 必须先证明“同一份数据面 → 同一份判定”可复算；169b 才能把它接入现有 AutoHalt 行为。

## 总体边界

- 只能消费 `AdaptiveGateDataPlaneReport`，不重新散读 `continuity_reports`、run JSONL、schedule 表或其他底层表。
- SQLite 是长期事实源；判定结果必须可持久化。
- 不修改 Writer / RevisionHandler / SettlementExtractor。
- 不新增 workflow 节点。
- 不自动 rewrite。
- 不自动创建 re-plan proposal。
- 不放宽 T9/T10/T5/T6 既有冻结或校准口径。
- 不启动 Ch200；Ch200 属于 Task 171。
- 170 之前不冻结 T12。

## 判定输出语义

建议状态：

| 状态 | 含义 |
|------|------|
| `continue` | 样本充分，未见退化趋势 |
| `observe` | 样本不足或仅 observation 信号；只能记录，不可 halt |
| `warn` | 出现单信号轻度退化，但不足以 halt |
| `halt_candidate` | 满足自适应 halt 条件；observe 模式只记录 |
| `halt` | explicit enforce 模式下真正触发 AutoHalt |

建议 reason code：

| reason | 触发方向 |
|--------|----------|
| `health_p1_spike` | health 下降同时 P1/P2 异常抬升 |
| `orphan_acceleration` | orphan slope / delta 持续上升 |
| `quality_debt_streak` | degraded / convergence / qg_false 滑窗持续偏高 |
| `schedule_miss_spike` | Task 167 调度 missed / overdue 比例持续偏高 |
| `context_pressure_streak` | context emergency 或 budget/DB 压力持续偏高 |
| `cleanliness_regression` | T9 hard 信号回归；timeline 仍默认 observation |

## 自适应判定原则

169 应采用保守聚合策略：

- `missing` / `insufficient` 不可触发 halt。
- 单章尖峰默认只到 `warn`。
- `observation` 只能作为说明，不参与 hard halt。
- 至少一个窗口样本充分，且风险持续存在，才可进入 `halt_candidate`。
- 默认需要两个独立信号相互支持；单一 hard frozen redline 可作为例外，但必须带证据。
- 开局章节保留 warmup 保护。
- 小基数比率保护：分母太小时只能 `observe` 或 `warn`。

## 与现有 `_gates.py` 的关系

169 不应直接删除或重写旧 gate。建议策略：

1. 169a 先新增纯自适应判定函数。
2. 169b 在 phase2 后处理点并行调用新判定。
3. observe 模式下只写 decision ledger + run log gate observation。
4. enforce 模式下，只有显式打开 adaptive halt 后，`halt_candidate` 才升级为 `halt`。
5. Task 170 用小窗口验证后，再决定是否替换或降权旧绝对阈值门禁。

## 169a: 自适应 halt 判定引擎与决策账本

### Goal

新增纯判定引擎，输入 `AdaptiveGateDataPlaneReport`，输出 `AdaptiveHaltDecision`，并可持久化为 decision ledger。

### In Scope

- [x] 新增 Pydantic 模型：
  - `AdaptiveHaltPolicy`
  - `AdaptiveHaltDecision`
  - `AdaptiveHaltReason`
  - `AdaptiveHaltDecisionStatus`
  - `AdaptiveHaltReasonCode`
- [x] 新增 SQLite 表：
  - `adaptive_halt_decisions`
- [x] 新增 repository：
  - create / get / list_by_project / list_by_run
- [x] 新增纯判定函数：
  - `evaluate_adaptive_halt(report, policy) -> AdaptiveHaltDecision`
- [x] 判定函数只消费 `AdaptiveGateDataPlaneReport`。
- [x] 支持 observe/enforce action mode，但 169a 不触发 AutoHalt。

### Out of Scope

- 不接入 workflow。
- 不改 `_gates.py`。
- 不改 `GateConfig.for_mode(...)` 默认行为。
- 不写 `project_runs.status`。

## 169b: workflow 接入与 observe/enforce 行为

### Goal

把 169a 判定接入 phase2 多章运行后处理点，使每章或审计点可生成 adaptive halt decision。默认 observe，不误伤现有长跑。

### In Scope

- [x] 在 phase2 后处理点刷新 168 数据面并调用 169a。
- [x] 写入 `adaptive_halt_decisions`。
- [x] observe 模式：只记录，不 pause。
- [x] enforce 模式：只有显式启用 adaptive halt 且 decision=`halt` 时才触发 AutoHalt。
- [x] `ChapterRunLog.gate_reasons` 可记录 adaptive decision 摘要，但长期事实仍以 SQLite decision ledger 为准。
- [x] 不新增 workflow 节点；只在已有 phase2 控制流中接入。

### Out of Scope

- 不新增 LLM 调用。
- 不自动创建 ReplanProposal。
- 不自动修改正文。
- 不替换旧 gate；替换/降权留 Task 170 之后决策。
- 不启动 Ch200。

## 验收标准

Task 169 完成时必须满足：

- [x] 自适应 halt 判定是纯函数，可用合成 `AdaptiveGateDataPlaneReport` 单测覆盖。
- [x] 判定结果可持久化到 SQLite。
- [x] `missing` / `insufficient` / `observation` 不会触发 halt。
- [x] 良性波动不 halt。
- [x] 持续多信号退化能产出 `halt_candidate`。
- [x] observe/enforce 行为明确可测。
- [x] 不破坏现有 `_gates.py` 单测。
- [x] 生成 `tasks/169-adaptive-halt-decision-DONE.md`。

## 与后续任务关系

- **Task 170**：用小窗口验证 169 的误伤/漏拦行为，并标定 T12。
- **Task 171**：只有 168-170 稳定后才能启动 Ch200 长跑。

## 参考入口

- `tasks/168-adaptive-gate-data-plane-DONE.md`
- `tasks/168a-adaptive-gate-signal-snapshot-DONE.md`
- `tasks/168b-adaptive-gate-window-reporting-DONE.md`
- `src/songyan/evals/adaptive_gate.py`
- `src/songyan/workflows/_gates.py`
- `src/songyan/workflows/phase2_graph.py`
- `src/songyan/models/gate_config.py`
