# V7 归档索引

> 本目录收纳 V7 阶段中已经完成、已取消或当前不再作为主开发入口的产物。当前事实入口以 `docs/STATUS.md`、`tasks/V8-README.md` 和各当前任务文档为准。V7 历史事实入口见 `tasks/V7-README.md`。

## 归档原则

- **当前主线不归档**：Task 171 Ch200 主线、171t/171u/171v/171w 仍保留在 `tasks/` 和 `docs/reports/`。
- **取消的任务归档**：Task 172（Ch250）因阶段战略调整取消，归档至此。
- **完成的 R&D 线归档**：171a/171a-1/171b/171c/171d 的 spec、DONE、报告、复算脚本和专用实验工具归档至此。
- **历史审计报告归档**：pass1-pass17 审计报告与相关日志归档至 `archive/v7/audit/`。
- **文学提质中间任务归档**：Task 170b–170o 的过程稿与 DONE 文档归档至 `archive/v7/tasks/`；入口只保留 `170-literary-quality-remediation-README.md`、`170-enforce-small-window-validation-and-t12-calibration-DONE.md`、`170c-t9-near-duplicate-detection-DONE.md`、`170d-literary-auditor-calibration-DONE.md`、`170p-settlement-new-character-seeding-DONE.md`。
- **规划文档归档**：`v7-vision.md`、`v7-plan.md` 归档至 `archive/v7/plans/`。
- **运行时代码不混入主流程**：171b/171c 的实验工具和对应测试随 R&D 证据归档，避免污染当前产品代码入口。
- **可追溯**：归档文件保留原文件名，便于从历史文档和报告中追溯。

## 目录

| 路径 | 内容 |
|---|---|
| `archive/v7/plans/` | V7 规划文档（v7-vision、v7-plan） |
| `archive/v7/tasks/` | 170b–170o 过程稿与 DONE；171a/171a-1/171b/171c/171d 的任务规格与 DONE 文档；已取消的 172 |
| `archive/v7/reports/` | 171a/171a-1/171b/171c/171d 的报告；task-170 系列文学提质中间报告 |
| `archive/v7/audit/` | pass1-pass17 V7 审计报告与 `_pytest-pass13.log` |
| `archive/v7/scripts/` | 171a-1/171b/171c/171d 的离线生成、标注、采样、A/B、标定脚本 |
| `archive/v7/tests/` | 171b/171c R&D 专用测试 |
| `archive/v7/src/songyan/utils/` | 171b/171c R&D 专用工具函数 |

## plans/

- `v7-vision.md` — V7 构想（方向性）：从叙事骨架到完整线索经济 + 单一体裁 Ch300 渐进验证
- `v7-plan.md` — V7 阶段规划：篇章级质量修复 + 叙事自驱 + enforce 可生产化 + Ch300 渐进爬坡 + Task 160-173 路线图

## 归档任务

| Task | 归档文档 |
|---|---|
| 171a 文学量具效度重建 | `archive/v7/tasks/171a-literary-metric-validity-rebuild.md`、`archive/v7/tasks/171a-literary-metric-validity-rebuild-DONE.md`、`archive/v7/reports/task-171a-metric-validity-report.md` |
| 171a-1 量具效度量化 | `archive/v7/tasks/171a-1-metric-validity-quantification.md`、`archive/v7/tasks/171a-1-metric-validity-quantification-DONE.md`、`archive/v7/reports/task-171a-1-metric-prf-report.md` |
| 171b 代表性样本集 | `archive/v7/tasks/171b-representative-sampling.md`、`archive/v7/tasks/171b-representative-sampling-DONE.md`、`archive/v7/reports/task-171b-representative-sampling-report.md` |
| 171c 杠杆组合验证 | `archive/v7/tasks/171c-improvement-levers.md`、`archive/v7/tasks/171c-improvement-levers-DONE.md`、`archive/v7/reports/task-171c-improvement-levers-report.md` |
| 171d 三层契约落地 | `archive/v7/tasks/171d-three-tier-contract.md`、`archive/v7/tasks/171d-three-tier-contract-DONE.md`、`archive/v7/reports/task-171d-three-tier-contract-report.md` |
| 170b–170o 文学提质专项 | 见下方「已归档的文学提质任务文档」 |
| 172 Ch250 过渡验证（已取消） | `archive/v7/tasks/172-ch250-transition-validation-archived.md` |

## 已归档的文学提质任务文档

Task 170 专项已结束（`docs/reports/v7-literary-framework-review.md`）。以下文档为历史记录，不再作为当前开发入口：

| 任务 | 归档文档 |
|---|---|
| 170 规划稿 | `archive/v7/tasks/170-enforce-small-window-validation-and-t12-calibration.md` |
| 170b 中段窗口文学性评估 | `archive/v7/tasks/170b-midwindow-literary-readability-assessment.md`、`archive/v7/tasks/170b-midwindow-literary-readability-assessment-DONE.md` |
| 170c T9 近似重复检测 | `archive/v7/tasks/170c-t9-near-duplicate-detection.md` |
| 170d LiteraryAuditor 校准 | `archive/v7/tasks/170d-literary-auditor-calibration.md` |
| 170e voice 声纹区分 | `archive/v7/tasks/170e-voice-differentiation-DONE.md` |
| 170f pacing/exposition | `archive/v7/tasks/170f-pacing-exposition.md`、`archive/v7/tasks/170f-pacing-exposition-DONE.md` |
| 170g 提质复评 | `archive/v7/tasks/170g-remediation-rerun-and-reeval.md`、`archive/v7/tasks/170g-remediation-rerun-and-reeval-DONE.md`、`archive/v7/tasks/170g-phase2-remediation-DONE.md` |
| 170h 路径 B 第一步 | `archive/v7/tasks/170h-structural-rewrite-voice-exposition.md`、`archive/v7/tasks/170h-structural-rewrite-voice-exposition-DONE.md` |
| 170i 主角认知冲突 | `archive/v7/tasks/170i-protagonist-cognitive-conflict-voice-anchoring.md`、`archive/v7/tasks/170i-protagonist-cognitive-conflict-voice-anchoring-DONE.md` |
| 170j 最小声纹锚定 | `archive/v7/tasks/170j-ai-tone-voice-feasibility-assessment.md`、`archive/v7/tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md` |
| 170k 对抗性目标锚定 | `archive/v7/tasks/170k-opposing-goal-anchor.md`、`archive/v7/tasks/170k-opposing-goal-anchor-DONE.md` |
| 170l 声纹工程升级 | `archive/v7/tasks/170l-few-shot-voice-anchor.md`、`archive/v7/tasks/170l-few-shot-voice-anchor-DONE.md` |
| 170m exposition carrier 校准 | `archive/v7/tasks/170m-exposition-carrier-recalibration.md`、`archive/v7/tasks/170m-exposition-carrier-recalibration-DONE.md` |
| 170n 文学提质方向评估 | `archive/v7/tasks/170n-literary-next-step-assessment.md`、`archive/v7/tasks/170n-literary-next-step-assessment-DONE.md` |
| 170o voice 归因校准 | `archive/v7/tasks/170o-voice-homogeneity-attribution-calibration-DONE.md` |

## 已归档的中间报告

| 报告 | 归档路径 |
|---|---|
| task-170-adaptive-gate-validation-report.md | `archive/v7/reports/task-170-adaptive-gate-validation-report.md` |
| task-170b-literary-readability-assessment-report.md | `archive/v7/reports/task-170b-literary-readability-assessment-report.md` |
| task-170d-auditor-calibration-backtest.md | `archive/v7/reports/task-170d-auditor-calibration-backtest.md` |
| task-170f-stage2-reeval-report.md | `archive/v7/reports/task-170f-stage2-reeval-report.md` |
| task-170g-remediation-reeval-report.md | `archive/v7/reports/task-170g-remediation-reeval-report.md` |
| task-170g-phase2-remediation-reeval-report.md | `archive/v7/reports/task-170g-phase2-remediation-reeval-report.md` |
| task-170h-remediation-reeval-report.md | `archive/v7/reports/task-170h-remediation-reeval-report.md` |
| task-170i-remediation-reeval-report.md | `archive/v7/reports/task-170i-remediation-reeval-report.md` |
| task-170j-minimal-voice-anchor-reeval-report.md | `archive/v7/reports/task-170j-minimal-voice-anchor-reeval-report.md` |
| task-170k-opposing-goal-anchor-reeval-report.md | `archive/v7/reports/task-170k-opposing-goal-anchor-reeval-report.md` |
| task-170l-few-shot-voice-anchor-reeval-report.md | `archive/v7/reports/task-170l-few-shot-voice-anchor-reeval-report.md` |
| task-170m-exposition-carrier-recalibration-report.md | `archive/v7/reports/task-170m-exposition-carrier-recalibration-report.md` |
| task-170n-literary-next-step-assessment-report.md | `archive/v7/reports/task-170n-literary-next-step-assessment-report.md` |

## 已归档的审计报告

见 `archive/v7/audit/`，包括 `pass1-compliance-report.md` 至 `pass17-agent-settlement-report.md` 及 `_pytest-pass13.log`。

## 当前仍在主入口的 V7 文件

| 路径 | 用途 |
|---|---|
| `tasks/170-literary-quality-remediation-README.md` | 文学提质专项总览（已结束，历史入口） |
| `tasks/170-enforce-small-window-validation-and-t12-calibration-DONE.md` | Task 170：enforce 小窗口验证 + T12 冻结 |
| `tasks/170c-t9-near-duplicate-detection-DONE.md` | Task 170c：T9 近似重复检测 |
| `tasks/170d-literary-auditor-calibration-DONE.md` | Task 170d：LiteraryAuditor 校准 |
| `tasks/170p-settlement-new-character-seeding-DONE.md` | Task 170p：新配角证据门禁入库 |
| `docs/reports/v7-literary-framework-review.md` | 当前文学质量框架与阶段验收标准，仍是活跃事实入口 |
| `docs/reports/task-171-ch200-long-run-report.md` | Task 171 Ch200 长跑报告 |
| `docs/reports/task-171-ch200-analysis-and-next-step-report.md` | Task 171 Ch200 分析与后续规划 |
| `docs/reports/task-171w-ch201-ch220-window-report.md` | 171w Ch201-Ch220 窗口报告 |
| `scripts/run_171_ch200.py` | Ch200 长跑 harness（历史脚本，V8 仍可复用） |
| `tasks/171-ch200-long-run.md` | Task 171 主线文档 |
| `tasks/171p-ch200-wall-fix*.md`、`tasks/171q-ch200-wall-fix-duplicate.md`、`tasks/171s-critical-setting-reference-refresh.md` | Ch200 撞墙修复事实 |
| `tasks/171t-ch200-d1-hard-clean.md` | D1 文本洁净量具补强 |
| `tasks/171u-ch200-d1-clean-application-and-report-refresh.md` | Ch200 清洁应用与报告事实源复算 |
| `tasks/171v-ch200-plus-literary-readability-guardrails.md` | Ch200+ 文学性与可读性护栏 |
| `tasks/171w-171v-hardening-and-ch201-ch220-rerun.md` | 171w hardening 与 Ch201-Ch220 重验 |
| `tasks/V7-README.md` | V7 历史任务总索引（已收尾） |
