# Task 168 DONE: 自适应门禁数据面

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 Y（enforce 可生产化）
> **结论**: 完成。系统现在具备统一的自适应门禁信号快照事实源，并能基于快照生成窗口级数据面报告。

---

## 拆分完成情况

| Task | 名称 | 结论 |
|------|------|------|
| 168a | 自适应门禁信号快照模型 | ✅ 完成：`archive/v7/tasks/168a-adaptive-gate-signal-snapshot-DONE.md` |
| 168b | 自适应门禁窗口聚合与报告出口 | ✅ 完成：`archive/v7/tasks/168b-adaptive-gate-window-reporting-DONE.md` |

## 交付能力

- `adaptive_gate_signal_snapshots` 成为 gate 输入信号的 SQLite 快照事实源。
- `AdaptiveGateSignalRepository` 支持 upsert / get / list_range / delete_range。
- `AdaptiveGateDataPlaneReport` 和 `AdaptiveGateSignalWindow` 提供 169 可消费的窗口读模型。
- `songyan metrics` 追加“自适应门禁数据面”段。
- 缺失/不足/观察类样本显式区分，不被误判为 fail。

## 能力边界

- 不改 `_gates.py`。
- 不改 `GateConfig`。
- 不生成 halt reason。
- 不修改 enforce / AutoHalt 行为。
- 不接入主 workflow。
- 不冻结 T12。
- 不启动 Ch200。

## 验证摘要

```powershell
python -m pytest tests/test_168a_adaptive_gate_signal_snapshot.py tests/test_168b_adaptive_gate_window_reporting.py -q
# 15 passed

python -m pytest tests/ -q
# 2383 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
# All checks passed
```

## 后续

进入 Task 169：自适应 halt 判定。169 应只消费 `AdaptiveGateDataPlaneReport`，把“正常波动不停、真退化才停”的策略落到判定层。
