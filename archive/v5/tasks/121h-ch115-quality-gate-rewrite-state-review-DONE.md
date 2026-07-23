# Task 121h: Ch115 Quality Gate / Best-Version Rewrite Contract Fix — DONE

- **状态**：DONE
- **完成日期**：2026-06-26

## 目标摘要

复盘 Task 121g `run-0fd1456e` 中 Ch115 的 quality gate / rewrite 状态生命周期问题：rewrite 与 hard truncate 后，旧 revision 的 `_new_issues_introduced` 与 quality gate 状态可能污染最终版本判断，且高分 best version 可能被低质量 rewrite 覆盖。本任务修复状态归属与 safe-best 回滚契约，为后续 Ch115 聚焦验证提供工程闭环。

## 关键改动/交付物

- `src/songyan/workflows/_nodes.py`
  - 新增 `_new_issues_version_id` 与 `_new_issues_for_current_version`，让 new issues 只归属当前版本，过滤跨版本 stale state。
  - `rewrite_node` 生成 rewrite / hard truncate 版本后，统一清理旧 `_new_issues_introduced`、`_quality_gate_failures`、`_settlement_needs_human_review`、`_convergence_failed`、`_skip_settlement`、`_score_card`。
  - `review_merger_node` 增加 safe-best 保护：active best 满足 overall≥0.82、length_ok、budget_ok、无 critical，且 rewrite/hard-truncate 分数低于 best 超过 0.08 时，自动 abandon 当前版本并回滚到 best。
  - `revision_handler_node` 为 new issues 写入 `version_id` 归属。
  - `quality_gate_node` 只消费当前版本的 new issues。
- `src/songyan/workflows/phase1_graph.py`：`Phase1State` 增加 `_new_issues_version_id` 字段。
- 测试：
  - `tests/test_107_convergence_guardrail.py::test_qg_ignores_stale_versioned_new_issues`
  - `tests/test_108_core_nodes.py::test_low_quality_rewrite_rolls_back_to_safe_best`

## 验证证据

- 分析基础：`run-0fd1456e`（Task 121g），Ch1-Ch114 成功，Ch115 因 quality gate human review 阻断。
- Ch115 复盘结论：rewrite/hard-truncate 后版本劣化与状态污染共同导致阻断；`rev-115-3` 已产生 overall=0.8776 的安全 best 候选。
- 聚焦测试：
  - `pytest tests/test_108_core_nodes.py tests/test_rewrite_node.py tests/test_107_convergence_guardrail.py tests/test_phase1_graph.py -q`：84 passed。
  - `ruff check src/songyan/workflows/_nodes.py src/songyan/workflows/phase1_graph.py tests/test_108_core_nodes.py tests/test_rewrite_node.py tests/test_107_convergence_guardrail.py tests/test_phase1_graph.py`：通过。
- 全量测试（任务完成时）：`pytest tests/ -q`：1724 passed，1 xfailed，1 xpassed，14 warnings；`ruff check src/ tests/`：通过。
- 后续验证：Task 121i `run-ce1767ff` 已确认 Ch115 success / settlement / summary 均通过，不再进入 `human_review_required`。

## 遗留/后续

- 不处理 Prompt 层叙事质量或全局 threshold 调优（归 Task 121k / 121q 等后续任务）。
- safe-best 回滚主路径未在 Ch115 实跑中触发，由单元测试覆盖；后续 full single-run 继续观测。
