# Task 169b DONE: 自适应 halt workflow 接入

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 Y（enforce 可生产化）
> **结论**: 完成。phase2 现在可在章节后处理点并行生成 adaptive halt decision ledger；默认关闭，不改变现有运行行为。

---

## 交付内容

- `GateConfig` 新增显式 adaptive halt 配置：
  - `adaptive_halt_enabled`
  - `adaptive_halt_action_mode`
  - `adaptive_halt_policy_id`
  - `adaptive_halt_window`
  - `adaptive_halt_warmup_chapters`
- phase2 新增 `_evaluate_adaptive_halt_for_run(...)` helper：
  - 刷新 168 快照。
  - 构建 `AdaptiveGateDataPlaneReport`。
  - 调用 `evaluate_adaptive_halt(...)`。
  - 写入 `adaptive_halt_decisions`。
- phase2 成功/失败章节后处理路径接入 helper。
- 默认 `adaptive_halt_enabled=False`，不会调用 helper。

## 行为边界

- 默认配置不改变现有 run 行为。
- observe 模式下 `halt_candidate` 只记录，不暂停。
- explicit enforce + decision=`halt` 时才抛 `AutoHaltException(reason="adaptive_halt_decision")`。
- decision ledger 写失败只告警，不影响 accepted/current head。
- 不新增 LangGraph node。
- 不改 Writer / RevisionHandler / SettlementExtractor。
- 不替换旧 `_gates.py`。
- 不冻结 T12。
- 不启动 Ch200。

## 验证结果

```powershell
python -m pytest tests/test_169b_adaptive_halt_workflow_integration.py -q
# 5 passed

python -m pytest tests/test_169a_adaptive_halt_decision_engine.py tests/test_169b_adaptive_halt_workflow_integration.py tests/db/test_migrations.py tests/db/test_schema.py -q
# 35 passed

python -m pytest tests/test_168a_adaptive_gate_signal_snapshot.py tests/test_168b_adaptive_gate_window_reporting.py tests/test_169a_adaptive_halt_decision_engine.py tests/test_169b_adaptive_halt_workflow_integration.py tests/test_130_gate_mode.py tests/test_139a_enforce_gate_audit.py tests/test_phase2_graph.py tests/test_105_streaming_validation.py -q
# 93 passed

python -m pytest tests/ -q
# 2397 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
# All checks passed
```

## 后续

进入 Task 170：enforce 小窗口验证 + T12 误报率标定。Task 170 应验证 169 的良性波动不误伤、真实退化能拦截，并给出是否降权旧绝对阈值 gate 的证据。
