# Task 122a: Unit Test Matrix — Dynamic Thresholds & Degraded Accept

## 状态

DONE

## 完成日期

2026-06-26

## 目标摘要

为 Task 121q 落地的动态 safe-best 阈值和 `degraded_accept` 降级回滚路径补充单测覆盖，确保阈值边界与降级行为可回归、可验证。

## 关键改动/交付物

- `tests/test_safe_best_min_score.py`：新增 8 个测试，覆盖 `_safe_best_min_score` 三阶段阈值边界（Ch1-Ch20→0.75、Ch21-Ch50→0.78、Ch51+→0.82）。
- `tests/test_degraded_accept.py`：新增 12 个测试，覆盖：
  - `_score_card_is_degraded_acceptable` 阈值与硬约束判断；
  - `quality_gate_node` 在修复耗尽时正确路由到 `degraded_accept`；
  - `settlement_extractor_node` 对 `degraded_accept` 放行、对普通 QG false 拦截。
- 无生产代码改动；测试即交付物。

## 验证证据

- 专项测试：`python -m pytest tests/test_safe_best_min_score.py tests/test_degraded_accept.py -v` → **20 passed**
- 全量回归：`python -m pytest tests/ -q` → **1828 passed, 1 xfailed, 2 warnings**
- Lint：`ruff check src/ tests/` → **All checks passed**
- 该任务为单元测试任务，无 chapter run_id。

## 遗留/后续

- 无。动态阈值与降级路径已由 Task 121q 实现，Task 122a 完成单测覆盖；后续如阈值公式调整，需同步更新 `tests/test_safe_best_min_score.py` 边界值断言。
