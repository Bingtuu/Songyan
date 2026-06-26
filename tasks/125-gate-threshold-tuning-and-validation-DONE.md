# Task 125: 候选硬门禁阈值调优与验证 — DONE

- **状态**: DONE
- **完成日期**: 2026-06-26
- **原始任务**: `tasks/125-gate-threshold-tuning-and-validation.md`
- **输入数据**: `run-a2bed648`（Ch1-Ch150 干净长跑）

---

## 目标摘要

基于 Task 124 对 `run-a2bed648` 的人工复核结论，将候选硬门禁从“对正常叙事累积过度敏感”调优为“对真实异常敏感”，使干净长跑上的 `any_gate` 误触发率降到可接受范围（目标 ≤5 章，理想 0 章），同时保留对真实异常（state mismatch 激增、health_score 骤降、连续审计点 P1 异常）的触发能力。

## 关键改动 / 交付物

1. **`src/songyan/models/gate_config.py`**
   - 新增阈值字段：`health_low_p1_min_absolute`、`health_low_p1_anomaly_factor`、`health_low_score_drop_threshold`、`health_low_streak_audit_window` 等。

2. **`src/songyan/workflows/_gates.py`**
   - `health_low_p1_halt` 改为 P1 异常检测：P1_count 同时超过绝对阈值与滚动中位数倍数才触发。
   - `health_low_absolute_score_halt` 改为相邻审计点 `overall_health_score` 相对跌幅检测。
   - `health_low_streak_halt` 改为基于审计点窗口（3 个审计点 ≈ 9 章）统计。

3. **`src/songyan/workflows/phase2_graph.py`**
   - 更新 gate 调用点，传入历史审计数据以支持滚动基线计算；保持无历史数据时向后兼容不触发。

4. **`scripts/analyze_124_gate_impact.py`**
   - 更新候选配置并重跑离线仿真。

5. **`tests/test_125_gate_thresholds.py`**（新增）
   - 覆盖 P1 异常检测、health_score 跌幅检测、审计点 streak 检测、旧行为向后兼容等 12 个单测。

6. **`docs/STATUS.md`**
   - 已更新 Task 125 完成状态。

## 验证证据

- **长跑验证**: `run-a2bed648`（Ch1-Ch150，150/150 全部成功）上调优后 `any_gate` 触发 **0 章**。
- **测试**: 全量 `pytest tests/` 通过，结果 `1828 passed, 1 xfailed, 2 warnings`（1 xfailed 为已知非阻断项）。
- **Lint**: `ruff check src/ tests/ scripts/analyze_124_gate_impact.py` 通过。
- **ContextEmergency**: 规则未调整，仍默认 `observe` 模式。

## 遗留 / 后续

- 本次调优以保证 `run-a2bed648` 零误伤为基线；跨项目泛化性需待后续更多长跑数据进一步验证。
