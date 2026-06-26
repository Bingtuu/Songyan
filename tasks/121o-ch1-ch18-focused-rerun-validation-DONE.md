# Task 121o: Ch1-Ch18 聚焦验证重跑 — DONE

**状态**: DONE  
**完成日期**: 2026-06-26  
**原始任务**: `tasks/121o-ch1-ch18-focused-rerun-validation.md`

## 目标摘要

验证 Task 121m（QG false 硬拦截 + 元标记清理）与 Task 121n（Context Diet 2.0 预算调整 + human_marks 生命周期）的工程修复是否有效，确认系统能稳定越过 Ch13 和 Ch18 两个历史阻断点，为 Ch1-Ch150 full single-run 提供可信基线。

## 关键改动 / 交付物

- 复用 Task 121m 修复：QG false 版本禁止进入 settlement；Writer 后处理清理 `<!--` / `[[新设定` 等元标记。
- 复用 Task 121n 修复：Context Diet 2.0 token 预算增量 80→250；human_marks 生命周期窗口 10→6。
- 更新项目状态文档：`docs/STATUS.md`、`README.md`、`tasks/V5-README.md` 中记录 121o 验证结论。
- 本次任务本身为验证执行，未引入新的代码改动。

## 验证证据

| 项 | 值 |
|----|----|
| run_id | `run-4ff41095` |
| project_id | `d54de3c1d44842ff9dc6ceaa36f107c7` |
| 执行时间 | 2026-06-22 19:18 – 21:10（约 1h 53min）|
| 完成章节 | 18 / 18（Ch1–Ch18 全部 success）|
| 失败章节 | 0 |
| ContextEmergency 触发 | 0 次（121l 中 Ch10–Ch12 连续触发）|
| AutoHalt 触发 | 0 次 |
| QG false 次数 | 0；settlement 仅在 QG 通过版本执行 |
| 元标记泄漏 | 0 次（`<!--`、`[[新设定` 未出现）|
| pytest | 通过（121m/121n 验证时 1731 passed）|
| ruff | `ruff check src/ tests/` 通过 |

## 遗留 / 后续

- 已按结论分支进入下一步：启动 Ch1-Ch150 full single-run（后续由 Task 121q 完成）。
- 正文质量波动（Ch8/Ch13/Ch17 评分偏低、writer 字数超量）属于 Prompt / 正文质量范畴，归 Task 121k 处理，不影响本次工程修复验收。
