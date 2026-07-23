# Task 121n DONE: Context Diet 2.0 预算调整与 human_marks 生命周期优化

- **状态**: DONE
- **完成日期**: 2026-06-26
- **原任务文档**: `tasks/121n-context-diet-budget-and-human-marks-lifecycle.md`

## 目标摘要

调整 Context Diet 2.0 预算增长参数与 human_marks 生命周期清理窗口，降低中段（Ch8–Ch20）连续 ContextEmergency 触发频率，为 Ch1-Ch150 完整 single-run 提供稳定的上下文基线。

## 关键改动/交付物

- `src/songyan/agents/context_manager/_assemblers.py`
  - `BUDGET_INCREMENT_PER_CHAPTER`: `80` → `250`
  - `DEFAULT_BASE_BUDGET` 保持 `8000`
- `src/songyan/db/human_mark_repo.py`
  - `archive_stale` 默认窗口: `10` 章 → `6` 章
- 未改动 Context Diet 2.0 四组件架构、settlement 提取或 writer 生成逻辑。

## 验证证据

- `pytest tests/ -q`: **1731 passed**（任务完成时）
- `ruff check src/ tests/`: 通过
- 后续聚焦验证：Task 121o `run-4ff41095` Ch1-Ch18 **18/18 成功**，ContextEmergency 0 次，AutoHalt 0 次
- 后续窗口验证：Task 121q `run-86b1170c` Ch1-Ch20 **20/20 成功**
- 最终完整重跑：Task 121q `run-a2bed648` Ch1-Ch150 **150/150 全部成功**，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次

## 遗留/后续

- 无独立遗留项。
- 后续由 Task 121o / 121q 承接验证；最终 `run-a2bed648` 已覆盖 Ch1-Ch150 完整 single-run。
