# Task 169a DONE: 自适应 halt 判定引擎与决策账本

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 Y（enforce 可生产化）
> **结论**: 完成。系统现在具备纯函数自适应 halt 判定引擎和 `adaptive_halt_decisions` SQLite decision ledger。

---

## 交付内容

- 新增模型：
  - `AdaptiveHaltPolicy`
  - `AdaptiveHaltDecision`
  - `AdaptiveHaltReason`
  - `AdaptiveHaltDecisionStatus`
  - `AdaptiveHaltReasonCode`
- 新增 SQLite 表：
  - `adaptive_halt_decisions`
- 新增 repository：
  - `AdaptiveHaltDecisionRepository.create(...)`
  - `get(...)`
  - `list_by_project(...)`
  - `list_by_chapter(...)`
- 新增纯判定函数：
  - `evaluate_adaptive_halt(report, policy)`

## 关键实现

- 判定函数只消费 `AdaptiveGateDataPlaneReport`。
- `missing` / `insufficient` 数据主导时只产出 `observe`。
- warmup 保护期内异常最多 `warn`。
- 默认需要多信号共振才进入 `halt_candidate`。
- observe mode 下不升级为 `halt`；enforce policy 下才可升级。
- decision ledger 持久化 reasons / evidence / policy version，便于复盘。

## 边界确认

- 不接入 phase2_graph。
- 不抛 `AutoHaltException`。
- 不写 run log。
- 不改 `_gates.py`。
- 不改 `GateConfig` 默认行为。
- 不启动真实长跑。

## 验证结果

```powershell
python -m pytest tests/test_169a_adaptive_halt_decision_engine.py -q
# 9 passed

python -m pytest tests/test_169a_adaptive_halt_decision_engine.py tests/db/test_migrations.py tests/db/test_schema.py -q
# 30 passed

python -m pytest tests/test_168a_adaptive_gate_signal_snapshot.py tests/test_168b_adaptive_gate_window_reporting.py tests/test_169a_adaptive_halt_decision_engine.py tests/test_130_gate_mode.py tests/test_139a_enforce_gate_audit.py tests/test_phase2_graph.py tests/test_105_streaming_validation.py -q
# 88 passed

python -m pytest tests/ -q
# 2392 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
# All checks passed
```

## 后续

进入 Task 169b：自适应 halt workflow 接入。169b 应把 169a 判定并行接入 phase2 后处理点，默认 observe，只记录 decision ledger；显式 enforce + adaptive halt enabled 时才允许 AutoHalt。
