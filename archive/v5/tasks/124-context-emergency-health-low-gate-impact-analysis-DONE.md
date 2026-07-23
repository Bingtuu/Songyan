# Task 124 DONE：候选硬门禁离线影响面分析

- **状态**: DONE
- **完成日期**: 2026-06-26
- **Run ID**: `run-a2bed648`

## 目标摘要

基于 V5.0 最终干净长跑 `run-a2bed648` 的历史数据，对 Task 123 实现的 ContextEmergency / health_low 候选硬门禁做离线仿真，量化各类 gate 在真实章节中的触发次数、分布与潜在误伤率，为是否开启 enforce 模式提供数据依据。分析不发起新实跑，仅复用生产判断函数与已有日志/数据库记录。

## 关键改动 / 交付物

- `scripts/analyze_124_gate_impact.py`：离线门禁影响面分析脚本，复用 `src/songyan/workflows/_gates.py` 的判断函数。
- `archive/v5/reports/124-gate-impact-analysis-run-a2bed648.md`：自动生成的影响面报告（Task 124 完成时的原始版本）。
- `tests/test_124_gate_impact.py`：16 个单元测试，覆盖数据加载、Analyzer 规则仿真、报告渲染与端到端 CLI。

## 分析结果（Task 124 完成时）

- **分析范围**: `run-a2bed648` 的 Ch31–Ch150，共 120 章（Ch1–Ch30 无 JSONL/DB 记录）。
- **触发统计**:
  - `health_low_p1_halt`: 40 次
  - `health_low_absolute_score_halt`: 40 次
  - `health_low_streak_halt`: 118 次
  - `context_emergency_budget_ratio_halt`: 0 次
  - `context_emergency_failure_halt`: 0 次
  - `any_gate` 并集: 118 次（首次触发 Ch33）
- **根因**: 所有 P1 均来自 `critical` 类型的 `orphaned_settings`（正常叙事累积）；`overall_health_score` 在 Ch>30 后被硬下限保护在 2.0，导致固定阈值 `< 3.0` 必然误伤。
- **结论**: 原始候选阈值对干净长跑过于敏感，直接开启 enforce 会大面积阻断。该结论直接驱动 Task 125 阈值调优。

## 验证证据

- 全量 pytest：`1816 passed, 1 xfailed, 2 warnings`。
- ruff check：`ruff check src/ tests/ scripts/analyze_124_gate_impact.py` 通过。
- 报告由 `scripts/analyze_124_gate_impact.py` 自动生成，规则复用生产代码 `_gates.py`。

## 遗留 / 后续

- 本分析仅覆盖 `run-a2bed648`；后续新 run 可定期复用本脚本复盘，形成 gate 阈值调整闭环。
- enforce 模式的最终开启决策需结合更多 run 样本与人工复核（已由 Task 125 处理阈值调优）。
