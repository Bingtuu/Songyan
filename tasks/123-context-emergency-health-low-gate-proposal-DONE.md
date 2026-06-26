# Task 123 DONE: ContextEmergency / health_low 候选硬门禁提案

- **状态**: DONE
- **完成日期**: 2026-06-26
- **任务文档**: `tasks/123-context-emergency-health-low-gate-proposal.md`

## 目标摘要

将 `health_low` 与 `ContextEmergency` 两个软复核信号升级为可配置、可解释、可观测的候选硬门禁，默认观测模式，复用现有 AutoHalt 状态机，避免误伤 V5.0 已验证的 150 章长跑能力。

## 关键改动 / 交付物

- 新增 `src/songyan/models/gate_config.py`：`GateConfig` 配置模型，支持 `gate_mode=observe/enforce` 及各规则开关。
- 新增 `src/songyan/workflows/_gates.py`：纯逻辑门禁判断函数（health_low 单章、health_low streak、ContextEmergency 单章、统一评估）。
- 扩展 `src/songyan/workflows/phase2_graph.py`：`_check_auto_halt_window` 新增 health_low streak reason；`_run_single_chapter` 接入单章即时判断。
- 扩展 `src/songyan/models/run_log.py` 与 `src/songyan/workflows/_run_logger.py`：`ChapterRunLog` 记录 `continuity_health_severity`、`gate_triggered`、`gate_reasons`、`gate_mode`。
- 扩展 `src/songyan/models/context.py` 与 DB 层：`ContextSnapshot` 增加 `context_emergency_level`。
- 新增 `tests/test_123_gates.py`：16 个单元测试覆盖 GateConfig、health_low 单章/连续、ContextEmergency 单章、`_check_auto_halt_window` streak 集成。

## 验证证据

- `python -m pytest tests/test_123_gates.py -q`：**16 passed**（当前重测通过）。
- 最近全量回归：`1828 passed, 1 xfailed, 2 warnings`，零回归（来源：`docs/STATUS.md`）。
- `ruff check src/ tests/`：已通过（来源：`docs/STATUS.md`）。
- 实跑数据：V5.0 最终 full single-run `run-a2bed648` Ch1-Ch150 全部成功，ContextEmergency 0 次、AutoHalt 0 次，未触发任何新门禁。

## 遗留 / 后续

- 规则默认观测模式，不自动 pause run；是否开启门禁模式由后续 Task 124/125 基于 `run-a2bed648` 离线影响面分析与阈值调优结果决定。
- 可选增强：`human_gate_node` 展示 continuity warnings、CLI 一键切换模式、基于历史 run 的触发章节分析，留待后续任务评估。
