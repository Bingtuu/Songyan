# V7 归档索引

> 本目录收纳 V7 阶段中已经完成、当前不再作为主开发入口的 R&D 产物。当前事实入口仍以 `docs/STATUS.md`、`tasks/V7-README.md` 和各当前任务文档为准。

## 归档原则

- **当前主线不归档**：Task 171 Ch200 主线、171t/171u/171v/172 仍保留在 `tasks/` 和 `docs/reports/`。
- **完成的 R&D 线归档**：171a/171a-1/171b/171c/171d 的 spec、DONE、报告、复算脚本和专用实验工具归档至此。
- **运行时代码不混入主流程**：171b/171c 的实验工具和对应测试随 R&D 证据归档，避免污染当前产品代码入口。
- **可追溯**：归档文件保留原文件名，便于从历史文档和报告中追溯。

## 目录

| 路径 | 内容 |
|---|---|
| `archive/v7/tasks/` | 171a/171a-1/171b/171c/171d 的任务规格与 DONE 文档 |
| `archive/v7/reports/` | 171a/171a-1/171b/171c/171d 的报告 |
| `archive/v7/scripts/` | 171a-1/171b/171c/171d 的离线生成、标注、采样、A/B、标定脚本 |
| `archive/v7/tests/` | 171b/171c R&D 专用测试 |
| `archive/v7/src/songyan/utils/` | 171b/171c R&D 专用工具函数 |

## 归档任务

| Task | 归档文档 |
|---|---|
| 171a 文学量具效度重建 | `archive/v7/tasks/171a-literary-metric-validity-rebuild.md`、`archive/v7/tasks/171a-literary-metric-validity-rebuild-DONE.md`、`archive/v7/reports/task-171a-metric-validity-report.md` |
| 171a-1 量具效度量化 | `archive/v7/tasks/171a-1-metric-validity-quantification.md`、`archive/v7/tasks/171a-1-metric-validity-quantification-DONE.md`、`archive/v7/reports/task-171a-1-metric-prf-report.md` |
| 171b 代表性样本集 | `archive/v7/tasks/171b-representative-sampling.md`、`archive/v7/tasks/171b-representative-sampling-DONE.md`、`archive/v7/reports/task-171b-representative-sampling-report.md` |
| 171c 杠杆组合验证 | `archive/v7/tasks/171c-improvement-levers.md`、`archive/v7/tasks/171c-improvement-levers-DONE.md`、`archive/v7/reports/task-171c-improvement-levers-report.md` |
| 171d 三层契约落地 | `archive/v7/tasks/171d-three-tier-contract.md`、`archive/v7/tasks/171d-three-tier-contract-DONE.md`、`archive/v7/reports/task-171d-three-tier-contract-report.md` |

## 当前仍在主入口的 V7 文件

| 路径 | 用途 |
|---|---|
| `docs/reports/v7-literary-framework-review.md` | 当前文学质量框架与阶段验收标准，仍是活跃事实入口 |
| `docs/reports/task-171-ch200-long-run-report.md` | Task 171 Ch200 长跑报告 |
| `docs/reports/task-171-ch200-analysis-and-next-step-report.md` | Task 171 Ch200 分析与后续规划 |
| `scripts/run_171_ch200.py` | Ch200/Ch250 渐进爬坡 harness |
| `tasks/171-ch200-long-run.md` | Task 171 主线文档 |
| `tasks/171p-ch200-wall-fix*.md`、`tasks/171q-ch200-wall-fix-duplicate.md`、`tasks/171s-critical-setting-reference-refresh.md` | Ch200 撞墙修复事实 |
| `tasks/171t-ch200-d1-hard-clean.md` | 下一步：D1 文本洁净量具补强 |
| `tasks/171u-ch200-d1-clean-application-and-report-refresh.md` | 后续：Ch200 清洁应用与报告事实源复算 |
| `tasks/171v-ch200-plus-literary-readability-guardrails.md` | 后续：Ch200+ 文学性与可读性护栏 |
| `tasks/172-ch250-transition-validation.md` | Ch250 过渡验证占位 |
