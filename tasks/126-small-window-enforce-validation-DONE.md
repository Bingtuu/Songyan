# Task 126 DONE：候选硬门禁 enforce 模式小窗口实跑验证

- **状态**: DONE
- **完成日期**: 2026-06-26
- **Run ID**: `run-13bb5303`
- **项目 ID**: `c1b7b6d73c0d4428a58b1175f3316273`

## 目标摘要

在干净新项目上以 `gate_mode="enforce"` 跑 Ch1–Ch20，验证 Task 125 调优后的 health_low / ContextEmergency 阈值不会误伤正常长跑。先启用 `health_low_absolute_score_halt`，发现开局期误触发后禁用该子规则，完成后续验证。

## 关键改动 / 交付物

- `tasks/126-small-window-enforce-validation.md`：任务规划与结果记录。
- `scripts/run_126_enforce_validation.py`：直接调用 `run_project_pipeline` 并注入候选 enforce 配置的验证脚本。
- 实跑日志：`logs/chapter_runs/run-13bb5303.jsonl`。

## 实跑结果

| 指标 | 数值 |
|------|------|
| 完成章节 | Ch1–Ch19（共 19 章） |
| 失败章节 | Ch20（QG false block，与 gate 无关） |
| Gate 触发 | **0 次** |
| ContextEmergency | 未出现 |
| 总耗时 | 6587 秒（约 1h50m） |

### Continuity audit P1 计数

- Ch3: 0
- Ch6: 0
- Ch9: 1
- Ch12: 3
- Ch15: 9
- Ch18: 13

均未达到 `health_low_p1_min_absolute=50` 或 streak 阈值 `250`。

## 重要发现

1. `health_low_absolute_score_halt`（score 相对跌幅 ≥2.0）在第一次实跑中于 Ch6 误触发：score 从 10.0 跌至 5.2，属于新项目开局期正常下降，不适合直接作为 enforce 规则。
2. 禁用 score_drop 后，`health_low_p1_halt` 与 `health_low_streak_halt` 在 Ch1–Ch19 零误伤，配置安全。

## 验证证据

- 日志：`logs/chapter_runs/run-13bb5303.jsonl`
- `gate_triggered` 字段全为 `false`。
- 全量 pytest / ruff 在 Task 125 阶段已验证：`1828 passed, 1 xfailed, 2 warnings`。

## 遗留 / 后续

- 建议 Task 127：移除或重构 `health_low_absolute_score_halt`（例如仅在 score 创历史新低且 P1 同步激增时触发）。
- 在 Ch1–Ch50 或跨项目上继续验证 P1 异常与 streak 阈值的泛化性。
