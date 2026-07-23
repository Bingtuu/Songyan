# Task 122c: E2E Validation Windows — DONE

- **状态**: DONE
- **完成日期**: 2026-06-26
- **前置任务**: Task 121q + 121r

## 目标摘要

完成 V5.1 三个压力拐点的端到端验证：Ch1-Ch20（早期低分容忍）、Ch40-Ch50（中段上下文压力）、Ch100-Ch110（后段高分保护）。验证目标从分段 Mock 测试推进到覆盖完整 Pipeline 的窗口级证据，确保不同章节区间的质量与上下文预算策略稳定。

## 关键改动/交付物

新增/补强三个集成测试文件：

- `tests/integration/test_ch1_20_e2e.py`
  - Ch1-Ch20 重度 Mock E2E 验证，28 秒完成。
- `tests/integration/test_ch41_50_validation.py`
  - 构造 Ch1-Ch40 历史后跑 Ch41-Ch50，Mock LLM；已补强 `ContextEmergency` / `AutoHalt` / `budget_used` 断言。
- `tests/integration/test_ch100_110_from_run_log.py`
  - 复用 Task 121q 实跑日志 `run-a2bed648`，对 Ch100-Ch110 做嵌入式证据校验。

## 验证证据

| 窗口 | 测试函数 | 结果 |
|------|----------|------|
| Ch1-Ch20 | `test_ch1_20_e2e_validation` | 20/20 成功，符合 ≥18/20 预期 |
| Ch40-Ch50 | `test_ch41_50_long_chain_validation` | 10/10 成功，`ContextEmergency = 0`，`AutoHalt = 0`，`max budget_used ≤ 1.0` |
| Ch100-Ch110 | `test_ch100_ch110_embedded_log_evidence` | 11/11 成功，QG 11/11，`ContextEmergency = 0`，`AutoHalt = 0`，`degraded_accept = 0`，`budget_used` 0.3866-0.4165，`overall_score` 0.7631-0.9341 |

- 源实跑记录：`logs/chapter_runs/run-a2bed648.jsonl`（Task 121q full single-run，Ch1-Ch150 150/150 成功）。
- 全量测试：`1828 passed, 1 xfailed, 2 warnings`。
- Lint：`ruff check src/ tests/` 已通过。
- 三个窗口合计 `ContextEmergency = 0`，`AutoHalt = 0`，`degraded_accept = 0`。

## 遗留/后续

无。本任务目标已全部达成，相关集成测试已纳入常规回归。
