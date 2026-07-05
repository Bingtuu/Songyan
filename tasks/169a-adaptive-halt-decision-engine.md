# Task 169a: 自适应 halt 判定引擎与决策账本

> **Phase**: V7 阶段 Y（enforce 可生产化）
> **优先级**: P0
> **状态**: ✅ 完成
> **父任务**: `tasks/169-adaptive-halt-decision.md`
> **依赖**: Task 168 DONE

---

## Goal

实现一个纯判定引擎：输入 `AdaptiveGateDataPlaneReport`，输出 `AdaptiveHaltDecision`。169a 不接入 workflow，不触发 AutoHalt，只负责可复算、可审计的判定契约和决策账本。

## 背景

Task 168 已提供窗口级数据面，但它刻意不判断“是否 halt”。169a 是两者之间的判定层：

```text
AdaptiveGateDataPlaneReport -> AdaptiveHaltPolicy -> AdaptiveHaltDecision
```

这样可以先用合成窗口和历史 DB 复算验证判定逻辑，再由 169b 接入 phase2。

## In Scope

- [x] 新增模型：
  - `AdaptiveHaltPolicy`
  - `AdaptiveHaltDecision`
  - `AdaptiveHaltReason`
  - `AdaptiveHaltDecisionStatus`
  - `AdaptiveHaltReasonCode`
- [x] 新增 SQLite 表：
  - `adaptive_halt_decisions`
- [x] 新增 repository：
  - `AdaptiveHaltDecisionRepository.create(decision)`
  - `get(decision_id)`
  - `list_by_project(project_id, run_id=None)`
  - `list_by_chapter(project_id, chapter_number, run_id=None)`
- [x] 新增纯判定函数：
  - `evaluate_adaptive_halt(report, policy) -> AdaptiveHaltDecision`
- [x] 判定输出必须包含：
  - decision status
  - reason codes
  - evidence window
  - sample sufficiency summary
  - policy version
- [x] 缺失或不足样本必须产出 `observe`，不能 halt。

## Out of Scope

- 不接入 phase2_graph。
- 不抛 `AutoHaltException`。
- 不写 run log。
- 不改 `_gates.py`。
- 不改 `GateConfig` 默认行为。
- 不启动真实长跑。

## 模型建议

### `AdaptiveHaltPolicy`

建议字段：

| 字段 | 含义 |
|------|------|
| `policy_id` | 策略 ID，例如 `v7-adaptive-halt-mvp` |
| `mode` | `observe` / `enforce`；169a 只决定状态，不执行 halt |
| `warmup_chapters` | 开局保护章数 |
| `min_window_count` | 最少窗口数 |
| `min_present_ratio` | 各信号域最小 present 比例 |
| `require_multi_signal` | 是否需要多信号共振 |
| `health_drop_floor` | health 最低线或相对下滑辅助门槛 |
| `p1_spike_factor` | P1 中位数异常因子 |
| `orphan_slope_factor` | orphan slope 异常因子 |
| `quality_debt_ratio` | quality debt 滑窗比例门槛 |
| `schedule_missed_rate` | 调度 missed rate 门槛 |
| `context_pressure_ratio` | context emergency / budget pressure 门槛 |

默认策略必须保守：不因单个窗口或单信号轻微波动 halt。

### `AdaptiveHaltDecision`

建议字段：

| 字段 | 含义 |
|------|------|
| `decision_id` | 决策 ID |
| `project_id` / `run_id` | 作用范围 |
| `chapter_start` / `chapter_end` | 数据范围 |
| `evaluated_at_chapter` | 本次评估所在章 |
| `status` | continue / observe / warn / halt_candidate / halt |
| `reasons` | `AdaptiveHaltReason[]` |
| `evidence` | report 摘要、窗口索引、样本状态 |
| `policy_id` / `policy_version` | 策略追踪 |
| `created_at` | 生成时间 |

## 判定规则 MVP

169a 的 MVP 不追求复杂机器学习，只做可解释规则：

1. **样本不足保护**：窗口数不足、关键域 present 比例不足时，最多 `observe`。
2. **warmup 保护**：`chapter_end <= warmup_chapters` 时，最多 `warn`。
3. **单信号保护**：只有一个信号域异常时，最多 `warn`，除非触发冻结 hard redline。
4. **多信号共振**：两个及以上域同时异常，才允许 `halt_candidate`。
5. **mode 分离**：`halt_candidate` 在 observe mode 下不升级；enforce mode 才能变 `halt`。

建议首批信号域：

| 域 | MVP 判定 |
|----|----------|
| continuity | health 低位 + P1/P2 上升，或 orphan slope 持续上升 |
| quality | degraded / convergence / qg_false 窗口比例偏高 |
| schedule | missed rate / overdue rate 偏高 |
| context | context emergency rate 或 budget/db 压力持续偏高 |
| cleanliness | meta/duplicate hard count 回归；timeline 只 observation |

## 测试要求

目标测试建议：

```powershell
python -m pytest tests/test_169a_adaptive_halt_decision_engine.py -q
```

必要覆盖：

- [x] 空 report -> `observe`。
- [x] insufficient / missing 主导 -> `observe`。
- [x] warmup 期异常 -> 最多 `warn`。
- [x] 单信号尖峰 -> `warn`，不 halt。
- [x] continuity + quality 多信号持续退化 -> `halt_candidate`。
- [x] observe mode 下 `halt_candidate` 不升级为 `halt`。
- [x] enforce mode 下显式策略可升级为 `halt`。
- [x] decision ledger create/get/list 可 round-trip。
- [x] 不导入或调用 `_gates.py`。

## 验收标准

- [x] `evaluate_adaptive_halt(...)` 是纯函数。
- [x] 判定结果可持久化到 SQLite。
- [x] 决策证据足够复盘。
- [x] 缺失/不足/观察项不会误触 halt。
- [x] 生成 `tasks/169a-adaptive-halt-decision-engine-DONE.md`。

## 风险与约束

- 不要为了“自适应”引入不可解释模型；MVP 必须规则透明。
- 不要在 169a 中读取底层表，避免绕过 168 数据面。
- 不要直接复用旧 `_gates.py` 的单章输入，否则 168 数据面就失去意义。
