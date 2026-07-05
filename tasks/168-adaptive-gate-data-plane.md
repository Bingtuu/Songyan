# Task 168: 自适应门禁数据面

> **Phase**: V7 阶段 Y（enforce 可生产化）
> **优先级**: P0（Task 167 后的直接后续；Task 169/170 前置）
> **状态**: ✅ 完成（168a / 168b 均已完成）
> **依赖**: Task 165/165p DONE（T9/T10 冻结）；Task 166/167 DONE（re-plan + 主动调度生命周期）
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 Y

---

## Goal

把当前分散在 run log、continuity reports、literary observations、text cleanliness、quality debt、T5 telemetry 和 Task 167 schedule lifecycle 中的信号，沉淀为 **gate 可读、可复算、可审计** 的数据面。

Task 168 不负责“是否 halt”。它只回答：

1. 当前窗口有哪些可用于自适应门禁的信号？
2. 哪些信号是充分样本，哪些只是 observation？
3. 哪些趋势、滑窗、命中率和异常因子可以供 Task 169 判定使用？

## 背景

V5/V6 已经有多个门禁和度量组件：

- `_gates.py` 已支持 ContextEmergency / health_low 候选门禁，部分逻辑依赖滚动中位数和 P1 异常因子。
- Task 145-148 已建立 orphan/T7、质量债、文学趋势、弧级伏笔兑现率等长期度量。
- Task 164/165p 已冻结 T9/T10，并校准 T5/T6 harness 误伤口径。
- Task 167 已新增 `ForeshadowingSchedulePlan` / `ForeshadowingScheduleItem`，并在 accept 后推进 `injected/satisfied/missed` 生命周期。

目前缺口是：这些信号还没有统一的数据契约。Task 169 如果直接从各表和 JSONL 临时拼读，就会把“采样充分性”“趋势计算”“异常因子”和“halt 判定”耦在一起，容易复现 V6/V5 enforce 误伤问题。

## 拆分结论

Task 168 拆为两个子任务：

| Task | 名称 | 边界 |
|------|------|------|
| 168a | 自适应门禁信号快照模型 | ✅ 已完成：定义 gate signal snapshot 的 Pydantic 模型、SQLite 表和 repository；只做单章/审计点事实快照 |
| 168b | 自适应门禁窗口聚合与报告出口 | ✅ 已完成：基于 168a 快照做滑窗聚合、趋势/命中率计算和 `songyan metrics` 展示；不产出 halt 决策 |

这样拆分的原因是：168a 是事实源和数据契约，必须稳定、可回放；168b 是派生读模型和报告层，可独立调整窗口口径。169 再消费 168b 的窗口聚合结果做自适应 halt 判定。

## 总体边界

- SQLite 是唯一长期事实源；run JSONL 只能作为导入/刷新来源，不作为 169 的直接长期依赖。
- LangGraph state 不新增大对象；最多保留 ID 或已有运行字段。
- 不修改 Writer / RevisionHandler / SettlementExtractor 的职责。
- 不新增 workflow 节点。
- 不改变现有 gate 触发逻辑。
- 不放宽 T9/T10/T5/T6 已冻结或已校准口径。
- 不启动 Ch200 长跑；Ch200 属于 Task 171。
- 缺失数据必须标为 `missing` / `insufficient` / `observation`，不能当作 fail。

## 数据面范围

Task 168 统一以下信号，但不重新定义业务判据：

| 信号域 | 来源 | 168 数据面字段方向 |
|--------|------|-------------------|
| continuity / orphan | `continuity_reports`、Task 145 collector | `health_score`、P1/P2/P3、orphan total/critical/recurring/other、forgotten count、样本充分性 |
| 新 critical 速率 | `setting_tracking`、Task 145 T7 | 每章新增 critical、滑窗均值、相对基线变化 |
| 质量债 | `ChapterRunLog` / `run_quality_debt`、Task 146 | degraded / convergence_failed / qg_false 的累计与滑窗比例 |
| 文学趋势 | `literary_observations`、Task 147 | 四维度分数、W=5 滑窗均值、T10 conceptual grounding 观测输入 |
| 文本洁净度 | `text_cleanliness_metrics`、Task 164 | meta tag、duplicate paragraph、timeline diagnostic 计数 |
| DB / context 压力 | `run_db_metrics`、run log context metrics、Task 165p | DB size、scan latency、context emergency、budget ratio |
| 线索/伏笔调度 | `foreshadowing_schedule_items`、`foreshadowings`、Task 167 | active/injected/satisfied/missed/cancelled 数、hit rate、missed rate、overdue rate |
| re-plan 背书 | `planning_constraints`、Task 166 | active constraint 数、来自 proposal 的约束覆盖情况 |

## 168a: 自适应门禁信号快照模型

### Goal

新增最小可用的 `AdaptiveGateSignalSnapshot` 数据契约，把单章或审计点级别的 gate 输入统一持久化。

### In Scope

- [x] 新增 Pydantic 模型：
  - `AdaptiveGateSignalSnapshot`
  - `AdaptiveGateSignalSourceStatus`
  - `AdaptiveGateContinuitySignals`
  - `AdaptiveGateQualitySignals`
  - `AdaptiveGateNarrativeSignals`
  - `AdaptiveGateContextSignals`
- [x] 新增 SQLite 表：
  - `adaptive_gate_signal_snapshots`
- [x] 新增 repository：
  - upsert snapshot
  - get by `(project_id, run_id, chapter_number)`
  - list by project / run / chapter range
  - delete range（供复算）
- [x] 保留来源状态：
  - `present`
  - `missing`
  - `insufficient`
  - `observation`
- [x] 单章快照必须可从已有表/JSONL 输入构建；缺失来源不报错。

### Out of Scope

- 不计算滑窗趋势。
- 不渲染报告。
- 不产出 gate reason。
- 不修改 `_gates.py`。
- 不接入 phase2 主 workflow。

## 168b: 自适应门禁窗口聚合与报告出口

### Goal

基于 168a 的 snapshots 计算窗口级输入面，给 Task 169 提供稳定的趋势、滑窗和异常因子来源。

### In Scope

- [x] 新增窗口聚合模型：
  - `AdaptiveGateSignalWindow`
  - `AdaptiveGateDataPlaneReport`
- [x] 实现 collector / refresher：
  - `refresh_adaptive_gate_signal_snapshots(project_id, start, end, run_id=None)`
  - `collect_adaptive_gate_windows(project_id, start, end, run_id=None, window=5)`
- [x] 计算但不判定：
  - health rolling min / rolling median
  - P1/P2 rolling median
  - orphan slope / recent delta
  - degraded / convergence / qg_false window ratio
  - context emergency rate / budget pressure
  - schedule hit rate / missed rate / overdue rate
  - T9/T10 observation 汇总
- [x] 在 `songyan metrics` 中追加“自适应门禁数据面”段。
- [x] 提供离线脚本或 CLI 路径，便于对历史 DB / run_id 复算。

### Out of Scope

- 不触发 halt。
- 不生成 AutoHalt reason。
- 不改变 `GateConfig` 默认值。
- 不修改 enforce 模式行为。
- 不自动创建 re-plan proposal。

## 验收标准

Task 168 完成时必须满足：

- [x] gate 输入信号有统一 SQLite 快照事实源。
- [x] 缺失/不足样本不会被误判为失败。
- [x] 167 的 `injected/satisfied/missed` 生命周期能进入数据面。
- [x] T9/T10/T5/T6 现有口径保持不变。
- [x] `songyan metrics` 能展示 168 数据面，且明确标注“只供 169 判定使用”。
- [x] 目标测试和相关回归通过。
- [x] 生成 `tasks/168-adaptive-gate-data-plane-DONE.md`。

## 与后续任务关系

- **Task 169** 消费 168b 的窗口聚合结果，实现自适应 halt 判定。
- **Task 170** 用小窗口验证良性波动/真实退化两类场景，并标定 T12 误报率。
- **Task 171** 只有在 168-170 稳定后才能启动 Ch200 长跑。

## 参考入口

- `tasks/145-orphan-and-critical-rate-metrics-DONE.md`
- `tasks/146-quality-debt-ledger-DONE.md`
- `tasks/147-literary-quality-trend-DONE.md`
- `tasks/148-arc-foreshadowing-fulfillment-DONE.md`
- `tasks/165p-stage-w-harness-calibration-DONE.md`
- `tasks/167-long-range-foreshadowing-active-scheduling-DONE.md`
- `src/songyan/evals/db_metrics.py`
- `src/songyan/evals/v6_acceptance.py`
- `src/songyan/workflows/_gates.py`
- `src/songyan/workflows/_run_logger.py`
