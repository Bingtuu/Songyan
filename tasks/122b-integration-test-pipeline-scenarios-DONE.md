# Task 122b: Integration Test — Pipeline Scenarios

- 状态：DONE
- 完成日期：2026-06-26

## 目标摘要

为 V5.1 单章 pipeline 在关键质量场景下的行为建立集成测试覆盖，重点验证动态阈值、`degraded_accept` 降级路径、safe-best 保护、human_review_required gate 以及 AutoHalt streak 逻辑，确保修复不引入路由断裂。

## 关键改动/交付物

- 新增集成测试文件：`tests/test_122b_pipeline_scenarios.py`
  - `TestQualityGateDegradedAcceptRouter`（2 个测试）：QG false + best score ≥ 0.70 时标记 `_degraded_accept=True` 并路由到 `human_confirm`；`quality_gate_router` 正确返回 `"pass"`。
  - `TestSafeBestPreserveOnRewrite`（3 个测试）：高于/低于动态阈值、coherence_critical 时不视为 safe best。
  - `TestHumanReviewRequiredGate`（2 个测试）：无 best 或 best score < 0.70 时正确标记 `_settlement_needs_human_review=True` 并跳过 settlement。
  - `TestAutoHaltWindow`（5 个测试）：连续 3 章 ContextEmergency + QG fail、连续 3 章 QG fail 触发 `AutoHaltException`；纯 emergency、混合 streak、窗口不足时不触发。
- 测试使用 AsyncMock/MagicMock 注入预设 score_card，不调用真实 LLM API。

## 验证证据

- 任务专属测试：`pytest tests/test_122b_pipeline_scenarios.py -v` → **12/12 passed**。
- 全量回归：Task 122b 关闭时 pytest 为 **1784 passed**，`ruff check src/ tests/` 全部通过。
- 当前基线（STATUS.md）：`1828 passed, 1 xfailed, 2 warnings`；ruff 已通过。

## 遗留/后续

无。本任务测试覆盖已并入 V5.1 测试基线，后续随全量回归持续执行。
