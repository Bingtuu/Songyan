# Task 122d DONE — Stress Test: Long Sequence Stability

- **状态**: DONE
- **完成日期**: 2026-06-26
- **任务文档**: [122d-stress-test-long-sequence-stability.md](122d-stress-test-long-sequence-stability.md)

## 目标摘要

在不调用 LLM（Mock 模式）的前提下，验证 150 章长序列中上下文预算、human_marks 蒸发、AutoHalt 熔断以及 accepted 章节跳过等关键机制的稳定性，确保 Context Diet 2.0 与状态机在长序列下无异常跳变或误熔断。

## 关键交付物

- 新增压力测试文件：`tests/integration/test_122d_long_sequence_stability.py`
- 覆盖 5 个核心场景：
  1. `test_context_budget_150_chapters` — 150 章 budget_used 平滑增长、异常跳变检测
  2. `test_human_marks_decay_6_chapters` — 低 priority human_marks 在 6 章窗口后蒸发
  3. `test_auto_halt_false_positive` — 连续 ContextEmergency 但 QG pass 时不误熔断
  4. `test_auto_halt_true_positive` — 连续 ContextEmergency + QG fail 时正确 AutoHalt
  5. `test_accepted_chapter_skip` — pipeline 遇到 accepted 章节直接跳过，不重复生成/审计
- 无新增业务代码或配置变更，压力测试聚焦 pipeline 路由与状态机契约。

## 验证证据

- **122d 专属测试**：5/5 全部通过（Mock 模式，< 60 秒）
- **全量回归**：`pytest tests/ -q` 结果 `1784 passed, 1 xfailed, 2 warnings`
- **Lint**：`ruff check src/ tests/` 通过
- **实跑证据**：Task 121q 一次性完整实跑 `run-a2bed648`，Ch1-Ch150 150/150 全部成功，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙

## 遗留/后续

- 无工程遗留。长序列稳定性已由 Mock 压力测试 + `run-a2bed648` 实跑双重验证。
- 后续如调整 Context Diet 阈值或 AutoHalt 策略，应保持本测试用例同步更新。
