# Task 169b: 自适应 halt workflow 接入

> **Phase**: V7 阶段 Y（enforce 可生产化）
> **优先级**: P0
> **状态**: ✅ 完成
> **父任务**: `tasks/169-adaptive-halt-decision.md`
> **依赖**: Task 169a（decision engine + ledger）

---

## Goal

把 169a 的自适应 halt 判定接入 phase2 多章运行控制流，使系统能够在每章后基于 `AdaptiveGateDataPlaneReport` 生成可审计判定。默认 observe，只记录不暂停；显式 enforce + adaptive halt enabled 时才允许 AutoHalt。

## 背景

现有 phase2 已有几类暂停路径：

- `quality_gate_fail_streak`
- health_low gate / streak gate
- ContextEmergency 相关 gate
- run 级异常 / 人工节点

169b 不能直接替换这些逻辑。它应作为并行的新判定路径，先在 observe 模式沉淀证据，再由 Task 170 小窗口验证是否具备替换/降权旧绝对阈值的条件。

## In Scope

- [x] 在 phase2 章节后处理点刷新 168 快照：
  - `refresh_adaptive_gate_signal_snapshots(project_id, start, current_chapter, run_id=...)`
- [x] 构建数据面报告：
  - `build_adaptive_gate_data_plane_report(...)`
- [x] 调用 169a：
  - `evaluate_adaptive_halt(report, policy)`
- [x] 持久化 decision：
  - `AdaptiveHaltDecisionRepository.create(...)`
- [x] observe 模式：
  - 记录 decision，不暂停 run。
  - 可把 summary 写入 run log `gate_reasons` 或独立字段，但 SQLite ledger 是事实源。
- [x] enforce 模式：
  - 只有显式启用 adaptive halt 且 decision=`halt` 时才抛 `AutoHaltException`。
- [x] 保留现有 `_gates.py` 行为。

## Out of Scope

- 不新增 workflow 节点。
- 不改 Writer / RevisionHandler / SettlementExtractor。
- 不自动创建 ReplanProposal。
- 不自动 rewrite。
- 不删除旧 gate。
- 不冻结 T12。
- 不启动 Ch200。

## 接入位置建议

接入应放在 phase2 单章完成后的后处理阶段，满足：

1. 当前章已有 run log / settlement / summary 结果。
2. 168 快照可读取当前章相关信号。
3. decision ledger 写入失败不污染 accepted/current head。
4. enforce 时暂停发生在章节完成之后，而不是正文生成中途。

建议作为已有 phase2 控制流的 helper，而不是新 LangGraph node：

```python
decision = await evaluate_adaptive_halt_for_run(
    project_id=project_id,
    run_id=run_id,
    chapter_number=chapter_number,
    chapter_start=chapter_range_start,
    policy=policy,
)
```

## 配置建议

不要直接修改现有 `GateConfig.for_mode("enforce")` 的默认启用行为。建议新增显式配置：

| 配置 | 默认 | 说明 |
|------|------|------|
| `adaptive_halt_enabled` | `False` | 是否启用自适应 halt 判定 |
| `adaptive_halt_action_mode` | `observe` | observe 只记录；enforce 可暂停 |
| `adaptive_halt_policy_id` | `v7-adaptive-halt-mvp` | 策略版本 |
| `adaptive_halt_window` | `5` | 168b 窗口大小 |
| `adaptive_halt_warmup_chapters` | `10` | 开局保护 |

如果不扩展 `GateConfig`，也可新建 `AdaptiveHaltPolicy` 并由 phase2 helper 显式传入。关键是默认不改变现有 enforce 行为。

## 行为矩阵

| gate_mode | adaptive_halt_enabled | decision | 行为 |
|----------|------------------------|----------|------|
| observe | False | any | 不调用 169b |
| observe | True | continue/warn/halt_candidate | 写 ledger，不暂停 |
| enforce | False | any | 保持旧 gate 行为 |
| enforce | True | halt_candidate | 可升级为 halt 并暂停 |
| enforce | True | observe/warn | 写 ledger，不暂停 |

## 测试要求

目标测试建议：

```powershell
python -m pytest tests/test_169b_adaptive_halt_workflow_integration.py -q
```

必要覆盖：

- [x] observe 模式下 `halt_candidate` 不抛 AutoHalt。
- [x] enforce + explicit enable 下 `halt` 抛 AutoHalt。
- [x] adaptive disabled 时不调用 169a。
- [x] decision ledger 写入失败只告警，不影响章节 accepted 后处理。
- [x] 现有 `_gates.py` 测试不回退。
- [x] run log 可记录 adaptive summary，但 SQLite ledger 仍为事实源。
- [x] 不新增 LangGraph node。

## 验收标准

- [x] phase2 能生成 adaptive halt decision ledger。
- [x] 默认配置不改变现有运行行为。
- [x] 显式 enable 后可在 enforce 模式触发 AutoHalt。
- [x] observe/enforce 行为均有测试。
- [x] 不破坏既有 gate / AutoHalt / resume 测试。
- [x] 生成 `tasks/169b-adaptive-halt-workflow-integration-DONE.md`。

## 与 Task 170 的交接

169b 完成后，Task 170 才能做小窗口验证：

- 良性波动样本：必须不 halt。
- 真退化样本：必须能 halt 或至少 halt_candidate。
- 对比旧 gate：记录误伤/漏拦。
- 冻结 T12 误报率口径。
