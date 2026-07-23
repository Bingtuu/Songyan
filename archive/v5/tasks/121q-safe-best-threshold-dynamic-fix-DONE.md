# Task 121q: Safe-Best Threshold Dynamic Fix — DONE

**状态**: DONE  
**完成日期**: 2026-06-26  

## 目标摘要

将 `_SAFE_BEST_MIN_OVERALL_SCORE = 0.82` 的全局静态阈值改为章节阶段感知动态阈值，避免早期章节（Ch1-Ch20）因铺垫期天然得分偏低而在 rewrite 后无法回滚到 safe-best version。同时引入 `degraded_accept` 降级回滚路径，使低质量 rewrite 不必直接杀死章节。

## 关键改动/交付物

- `src/songyan/workflows/_nodes.py`
  - 新增 `_safe_best_min_score(chapter_number: int) -> float`：Ch1-Ch20 → 0.75，Ch21-Ch50 → 0.78，Ch51+ → 0.82。
  - 更新 `_is_safe_best_version` 与 `settlement_review_node` 回滚决策逻辑。
  - 新增 `degraded_accept` 路径：best_score < 动态阈值但 ≥ 0.70 时仍回滚并继续 settlement，标记 `quality_gate_passed=False`。
- 相关单元/集成测试覆盖动态阈值边界与降级回滚路由。

## 验证证据

- **全量测试**: `pytest` 1731 passed；后续回归 `1828 passed, 1 xfailed, 2 warnings`。
- **Lint**: `ruff check src/ tests/` 已通过。
- **聚焦实跑**: `run-86b1170c` Ch1-Ch20 **20/20 全部成功**，degraded_accept 0 次，失败 0 次。
- **完整单章重跑**: `run-a2bed648` Ch1-Ch150 **150/150 全部成功**，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙。
- **核心断言达成**: Ch4 类场景（overall_score ≈ 0.81）不再因 0.82 阈值而死亡。

## 遗留/后续

- 无。后续质量优化转入 Task 121r Prompt 清理与 Task 122 系列测试矩阵。
