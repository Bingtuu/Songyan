# Songyan 文档索引

> 短版文档路由。长版索引已归档：`archive/v5/context-docs/INDEX-full-20260621.md`。

## 默认必读

| 文件 | 用途 |
|------|------|
| `AGENTS.md` | 开发代理短指令与不可违背规则 |
| `docs/STATUS.md` | 当前状态、测试口径、下一步 |
| `tasks/V9-README.md` | **V9 任务事实入口（已开工）**：生产化地基 + urban 第三体裁 Ch100，Task 173-188 扁平编号；**V9.1 全部完成**（173/174/175/176 ✅），**V9.2 Task 177/178/179/180 已完成**，下一步 181 CI 上线与测试清零 |
| `tasks/V8-README.md` | **V8 历史任务事实入口（已收尾，含 V8.5）**：多体裁可插拔质量 + 章数爬坡；含 Task 编号治理规则；任务文档与报告归档 `archive/v8/` |
| `tasks/V7-README.md` | **V7 历史任务事实入口（已收尾）**：sci-fi 单一体裁 Ch200 达成 |
| `tasks/V6-README.md` | V6 历史任务事实入口：叙事骨架 MVP + 度量 + 长跑底盘，Task 141-159 |
| `tasks/V5-README.md` | V5.0 历史任务事实入口 |

## V8 历史产物（已收尾，保留入口）

V8 已全量闭环（P/C/Q/S/V 五维全绿 + V8.5 遗留清零）。任务文档与报告统一归档至 `archive/v8/`（完整清单见 `archive/v8/INDEX.md`）；`tasks/V8-README.md` 保留为历史事实总索引。

| 文件 | 用途 |
|------|------|
| `tasks/V8-README.md` | V8 任务总索引、阶段验收标准、依赖关系、Task 编号治理规则（历史事实入口） |
| `archive/v8/INDEX.md` | V8 归档索引：全部任务文档与报告的归档清单 |
| `archive/v8/tasks/172-project-template-plugin-DONE.md` | Task 172：项目模板化与体裁可插拔 |
| `archive/v8/tasks/172a-v8-genre-runtime-profiles.md` | Task 172a：体裁运行时画像（GenreRuntimeProfile） |
| `archive/v8/tasks/172d-cross-genre-literary-guardrails-DONE.md` | Task 172d：文学护栏跨体裁化 |
| `archive/v8/tasks/172b-xuanhuan-ch100-climb.md` | Task 172b：xuanhuan Ch100 爬坡（含冻结终判口径，V9 中篇爬坡参照） |
| `archive/v8/tasks/172c-wuxia-ch100-clean-rerun-DONE.md` | Task 172c：wuxia Ch100 clean rerun 完成报告（100/100 五门 PASS） |
| `archive/v8/tasks/172j-budget-pruner-max-shadowing-fix.md` | Task 172j：BudgetPruner max_* 修复（V9 调参前置） |
| `archive/v8/tasks/172k-c-dimension-evidence-closure.md` | Task 172k：C 判据证据补完 xuanhuan end10 / urban end15 / wuxia end20 |
| `archive/v8/reports/172b-xuanhuan-ch100-climb.md` | xuanhuan Ch100 验收报告 |
| `archive/v8/reports/172c-wuxia-ch100-climb.md` | wuxia Ch100 验收报告 |
| `archive/v8/reports/172a.7-genre-short-window-validation.md` | 多体裁短窗口验证报告 |
| `docs/reports/v8-literature-and-landscape-review.md` | V8 长调研报告（GenreRuntimeProfile 设计依据，保留活跃入口） |

## V9 当前任务（已开工）

| 文件 | 用途 |
|------|------|
| `tasks/V9-README.md` | V9 总索引、A/B/C 验收判据、依赖关系与执行纪律 |
| `tasks/175-cost-tracking-and-budget-circuit-breaker.md` | Task 175 任务书：成本追踪与预算熔断（✅ 完成：阶段 A-D 全闭环，实跑验收通过） |
| `tasks/175-cost-tracking-and-budget-circuit-breaker-DONE.md` | Task 175 完成报告：成本遥测 + DB 权威熔断 + report 成本视图，含阶段 D 实跑证据 |
| `tasks/176-windows-anti-hang-wrapper.md` | Task 176 任务书：Windows 防卡 wrapper（✅ 完成） |
| `tasks/176-windows-anti-hang-wrapper-DONE.md` | Task 176 完成报告：通用超时 wrapper + 进程树清理 + 自检矩阵 |
| `tasks/177-export-book-manuscript.md` | Task 177 任务书：`songyan export` 正文导出（✅ 完成） |
| `tasks/177-export-book-manuscript-DONE.md` | Task 177 完成报告：accepted head 正文导出 + flat/arc/volume Markdown/txt + Ch100 实库验收 |
| `tasks/178-wheel-packaging-resource-loading.md` | Task 178 任务书：wheel 打包与资源加载修复（✅ 完成） |
| `tasks/178-wheel-packaging-resource-loading-DONE.md` | Task 178 完成报告：运行资源入包 + importlib.resources + wheel 非仓库 cwd 验收 |
| `tasks/179-cli-experience-fixes.md` | Task 179 任务书：CLI 三坑修复（✅ 完成） |
| `tasks/179-cli-experience-fixes-DONE.md` | Task 179 完成报告：run_id 输出 + 项目 mode fallback + README index 表项 |
| `tasks/180-doctor-environment-check.md` | Task 180 任务书：`songyan doctor` 环境自检（✅ 完成） |
| `tasks/180-doctor-environment-check-DONE.md` | Task 180 完成报告：本地只读环境自检 + JSON 输出 + schema drift 检测 |
| `tasks/173-interpreter-exit-hang-fix.md` | Task 173 任务书：解释器退出挂死修复 |
| `tasks/173-interpreter-exit-hang-fix-DONE.md` | Task 173 完成报告：LLM client 生命周期关闭 + force-exit 兜底 |
| `tasks/174-logging-system-foundation.md` | Task 174 任务书：日志体系落地 |
| `tasks/174-logging-system-foundation-DONE.md` | Task 174 完成报告：应用日志落盘 + 关联字段约定 |

## V7 历史产物（保留入口）

| 文件 | 用途 |
|------|------|
| `docs/reports/v7-literary-framework-review.md` | 文学质量框架级复盘 + V7 阶段验收标准 |
| `archive/v7/reports/task-171-ch200-long-run-report.md` | Task 171 Ch200 长跑报告 |
| `archive/v7/reports/task-171-ch200-analysis-and-next-step-report.md` | Task 171 Ch200 分析与 V7→V8 过渡 |
| `archive/v7/reports/task-171w-ch201-ch220-window-report.md` | 171w Ch201-Ch220 窗口报告 |
| `docs/reports/task-165-stage-w-exit-report.md` | V7 阶段 W 出口报告 |
| `docs/reports/task-165-v7-threshold-calibration.md` | V7 阈值标定 |
| `archive/v7/tasks/171-ch200-long-run.md` | Task 171 Ch200 长跑 |
| `archive/v7/tasks/171p-ch200-wall-fix-DONE.md` | 171p state_mismatch 构念修正 |
| `archive/v7/tasks/171p-ch200-wall-fix.md` | 171p 规划稿 |
| `archive/v7/tasks/171q-ch200-wall-fix-duplicate.md` | 171q T9 重复阈值对齐 |
| `archive/v7/tasks/171s-critical-setting-reference-refresh.md` | 171s critical setting 同义刷新 |
| `archive/v7/tasks/171t-ch200-d1-hard-clean.md` | 171t D1 文本洁净量具补强 |
| `archive/v7/tasks/171u-ch200-d1-clean-application-and-report-refresh.md` | 171u Ch200 清洁应用与报告复算 |
| `archive/v7/tasks/171v-ch200-plus-literary-readability-guardrails.md` | 171v Ch200+ 文学护栏 |
| `archive/v7/tasks/171w-171v-hardening-and-ch201-ch220-rerun.md` | 171w hardening 与 Ch201-Ch220 重验 |
| `archive/v7/tasks/170-literary-quality-remediation-README.md` | 文学提质专项总览（已结束） |
| `archive/v7/tasks/170-enforce-small-window-validation-and-t12-calibration-DONE.md` | Task 170：enforce 小窗口验证 + T12 冻结 |
| `archive/v7/tasks/170c-t9-near-duplicate-detection-DONE.md` | Task 170c：T9 近似重复检测 |
| `archive/v7/tasks/170d-literary-auditor-calibration-DONE.md` | Task 170d：LiteraryAuditor 校准 |
| `archive/v7/tasks/170p-settlement-new-character-seeding-DONE.md` | Task 170p：新配角证据门禁入库 |

## V6 历史产物

| 文件 | 用途 |
|------|------|
| `tasks/V6-README.md` | V6 任务总索引 |
| `archive/v6/reports/task-157-ch1-ch50-integration-validation-report.md` | Task 157 Ch1-Ch50 集成验证 |
| `archive/v6/reports/task-158-ch1-ch100-long-run-validation-report.md` | Task 158 Ch1-Ch100 长跑验证 |
| `archive/v6/reports/task-158r-kill-resume-drill-report.md` | Task 158r kill-resume 演练 |
| `archive/v6/reports/task-159-v6-final-acceptance-report.md` | V6 最终验收报告 |
| `archive/v6/reports/v6-stageA-threshold-calibration.md` | V6 阶段 A 阈值标定 |

## V5 历史产物

| 文件 | 用途 |
|------|------|
| `tasks/V5-README.md` | V5.0 任务总索引 |
| `archive/v5/INDEX.md` | V5 归档索引 |
| `archive/v5/reports/` | Task 124/129/136-139d 等 V5.2 阶段报告 |
| `archive/v5/plans/` | V5 历史规划稿 |
| `archive/v5/context-docs/` | AGENTS/STATUS/INDEX 长版快照 |

## 长期规划

| 文件 | 用途 |
|------|------|
| `docs/300-chapter-gap-analysis.md` | 300 章卡点与解决路径的代码级分析 |
| `archive/v6/plans/v6-plan.md` | V6 阶段规划 |
| `archive/v7/plans/v7-vision.md` | V7 构想 |
| `archive/v7/plans/v7-plan.md` | V7 阶段规划 |
| `docs/reports/v7-literary-framework-review.md` | V7 文学质量框架级复盘 |

## V7 代码审查与架构审计

已归档至 `archive/v7/audit/`，入口见 `archive/v7/INDEX.md`。

## 按场景查阅

| 场景 | 文件 |
|------|------|
| V9 任务入口（已开工） | `tasks/V9-README.md` |
| V9 长跑可靠性 DONE | `tasks/173-interpreter-exit-hang-fix-DONE.md`、`tasks/174-logging-system-foundation-DONE.md`、`tasks/175-cost-tracking-and-budget-circuit-breaker-DONE.md`、`tasks/176-windows-anti-hang-wrapper-DONE.md` |
| V9 交付发布 DONE | `tasks/177-export-book-manuscript-DONE.md`、`tasks/178-wheel-packaging-resource-loading-DONE.md`、`tasks/179-cli-experience-fixes-DONE.md`、`tasks/180-doctor-environment-check-DONE.md` |
| V8 历史任务入口（已收尾） | `tasks/V8-README.md` |
| 当前项目状态 | `docs/STATUS.md` |
| V8 归档索引（任务文档与报告） | `archive/v8/INDEX.md` |
| V9 中篇爬坡冻结口径参照 | `archive/v8/tasks/172b-xuanhuan-ch100-climb.md` |
| V7 历史任务入口 | `tasks/V7-README.md` |
| V6 历史任务入口 | `tasks/V6-README.md` |
| V5 历史任务入口 | `tasks/V5-README.md` |
| 开发规范 | `AGENTS.md` |
| 300 章卡点分析 | `docs/300-chapter-gap-analysis.md` |
| 架构手册 | `docs/architecture/04-vibe-coding-engineering.md` |
| 技术参考 | `docs/architecture/05-tech-reference.md` |
| Code Review | `docs/code-review-plan.md` |
| Prompt 工艺卡 | `src/songyan/prompts/cards/` |

## 归档入口

归档内容默认不读，仅在追溯历史决策时查阅。

- `archive/v3/INDEX.md` — V3.x 历史结论
- `archive/v4/INDEX.md` — V4.x 历史结论
- `archive/v5/INDEX.md` — V5 归档索引
- `archive/v6/INDEX.md` — V6 归档索引
- `archive/v7/INDEX.md` — V7 历史产物归档
- `archive/v8/INDEX.md` — V8 历史产物归档（任务文档 + 报告）
- `archive/tasks/` — 历史任务规划稿与交接报告
