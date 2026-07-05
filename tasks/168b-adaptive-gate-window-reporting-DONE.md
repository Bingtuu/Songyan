# Task 168b DONE: 自适应门禁窗口聚合与报告出口

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 Y（enforce 可生产化）
> **结论**: 完成。系统现在可以基于 `adaptive_gate_signal_snapshots` 生成窗口级自适应门禁数据面，并在 `songyan metrics` 中展示。

---

## 交付内容

- 新增窗口/报告模型：
  - `AdaptiveGateTrendPoint`
  - `AdaptiveGateSignalWindow`
  - `AdaptiveGateDataPlaneReport`
- 新增聚合函数：
  - `collect_adaptive_gate_windows(...)`
  - `build_adaptive_gate_data_plane_report(...)`
- 新增刷新入口：
  - `refresh_adaptive_gate_signal_snapshots(...)`
- 新增渲染函数：
  - `render_adaptive_gate_data_plane_section(...)`
- `render_stage_a_metrics(...)` 已追加“自适应门禁数据面”段。

## 关键实现

- 168b 聚合只依赖 `AdaptiveGateSignalRepository.list_range(...)` 读取快照。
- `refresh_adaptive_gate_signal_snapshots(...)` 可从现有 DB collectors / run log 刷新快照，不要求重新跑章节。
- 窗口聚合覆盖：
  - health min/median、P1/P2 median、orphan slope/delta、new critical mean；
  - degraded / convergence / qg_false window ratio；
  - literary / conceptual grounding 均值；
  - meta / duplicate / timeline observation 计数；
  - context emergency rate、budget max、DB max、scan max；
  - schedule hit rate、missed rate、overdue rate。
- `missing` / `insufficient` 不进入窗口硬计算；`observation` 可展示但不输出 pass/fail。

## 边界确认

- 不调用 `_gates.evaluate_all_gates`。
- 不生成 `gate_reasons`。
- 不修改 `GateConfig`。
- 不改变 enforce / AutoHalt 行为。
- 不接入主 workflow。
- 不做 T12 阈值冻结。
- 不启动 Ch200。

## 验证结果

```powershell
python -m pytest tests/test_168b_adaptive_gate_window_reporting.py -q
# 7 passed

python -m pytest tests/test_168a_adaptive_gate_signal_snapshot.py tests/test_168b_adaptive_gate_window_reporting.py -q
# 15 passed

python -m pytest tests/test_145_stage_a_metrics.py tests/test_146_quality_debt.py tests/test_147_literary_trend.py tests/test_148_foreshadowing_metrics.py tests/test_168a_adaptive_gate_signal_snapshot.py tests/test_168b_adaptive_gate_window_reporting.py tests/db/test_migrations.py tests/db/test_schema.py -q
# 67 passed

python -m pytest tests/test_162_timeline_consistency.py tests/test_164_text_cleanliness.py tests/test_165_stage_w_smoke.py tests/test_167a_foreshadowing_schedule.py tests/test_167b_schedule_injection.py tests/test_168a_adaptive_gate_signal_snapshot.py tests/test_168b_adaptive_gate_window_reporting.py -q
# 62 passed

python -m pytest tests/ -q
# 2383 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
# All checks passed
```

## 后续

进入 Task 169：自适应 halt 判定。169 应只消费 `AdaptiveGateDataPlaneReport`，不重新散读 `continuity_reports`、run JSONL 或 schedule 表。
