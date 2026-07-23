# Task 121l: ContextEmergency AutoHalt Review — DONE

- **状态**: DONE
- **完成日期**: 2026-06-26

## 目标摘要

复盘 Task 121j `run-b063b6f0` 中 Ch11-Ch13 连续触发 ContextEmergency 导致 AutoHalt 的问题，修复 AutoHalt 策略使其能区分“成功降级完成”与“真实上下文/质量失控”，为长距离 single-run 提供稳定的熔断控制。

## 关键改动 / 交付物

- **`src/songyan/workflows/phase2_graph.py`**
  - 新增 `_append_recent_result()`：成功与失败章节均进入最近 3 章熔断窗口。
  - 新增 `_has_context_emergency_degradation()`：显式区分成功降级与真实降级。
  - 新增 `_check_auto_halt_window()`：集中维护项目级熔断策略。
  - 成功路径透传 `settlement_success` / `summary_success`；失败路径透传 `budget_used` / `context_emergency`。
- **`tests/test_phase2_graph.py`**
  - `test_pipeline_continues_on_successful_context_emergency_streak`
  - `test_pipeline_halts_on_degraded_context_emergency_streak`
- **策略变更**
  - 连续 3 章 `context_emergency=true` 且全部 `success=true` / `quality_gate_passed=true` / `settlement_success=true` / `summary_success=true`：记录 warning 并继续运行。
  - 同一窗口内存在章节失败、QG false、settlement fail 或 summary fail：抛出 `AutoHaltException(reason="context_emergency_degraded_streak")`。
  - 原有连续 3 章 QG false 的 `quality_gate_fail_streak` 熔断逻辑保持不变。

## 验证证据

| 项 | 结果 |
|---|---|
| `pytest tests/test_phase2_graph.py -q` | 16 passed |
| `pytest tests/ -q` | 1725 passed, 1 xfailed, 1 xpassed, 14 warnings |
| `ruff check src/ tests/` | All checks passed |
| 聚焦实跑 run_id | `run-08689f68` |
| 聚焦项目 project_id | `0e131271e2f844998334d0d6398a5ad0` |
| 完成章节 | Ch1-Ch12，失败 0 章 |
| 暂停原因 | Ch10-Ch12 连续 ContextEmergency 且 Ch10 `quality_gate_passed=False`，按新策略正确触发 `context_emergency_degraded_streak` |

## 遗留 / 后续

- 本次聚焦实跑未越过 Ch13/Ch18，因中段质量链路进入 degraded emergency，需先处理正文长度/预算/动能不稳及 QG false 版本放行边界（后续由 Task 121m/121n/121o 承接）。
- Task 121o 已通过 `run-4ff41095` 实现 Ch1-Ch18 18/18 成功、0 次 ContextEmergency、0 次 AutoHalt。
- 最终 Task 121q `run-a2bed648` 完成 Ch1-Ch150 150/150 全部成功，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次。
