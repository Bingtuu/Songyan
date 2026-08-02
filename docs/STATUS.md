# Songyan 项目状态

> 短状态板。这里仅保留当前判断、最新事实源和下一步；历史任务、报告和样本 artifact 统一看 `archive/`。

## 当前判断

| 项 | 结论 |
|----|------|
| 当前阶段 | V11 已启动；Task 213 run bundle 诊断包已完成，下一步进入 Task 214 配置安全与 profile validate |
| V10 长窗口 | sci-fi Ch200 baseline 已冻结；xuanhuan / wuxia / urban 均完成 Ch200，总验收 accepted=200、gap=0、failed=[]、five-gate PASS、segment audit PASS、T9=0 |
| V10 优秀度信号 | Task 196-203 已完成，严格保持 report-only，不接 Writer / CreativeDirector prompt，不进 CED 或 hard gate |
| V10 结构 spike | KG diff、FactTrack validity interval、Storyline Tree 均完成，三者 decision=`defer`，不接 runtime / prompt / CED / hard gate |
| 当前代码面 | V11 只做开源可用化收尾；Task 213 已提供可分享、可脱敏的 run bundle JSON + Markdown 诊断包 |

## 当前入口

| 文件 | 用途 |
|------|------|
| `README.md` | 对外开源入口 |
| `AGENTS.md` | 开发代理短规则 |
| `docs/INDEX.md` | 文档路由 |
| `tasks/V10-README.md` | V10 总结入口 |
| `archive/v10/INDEX.md` | V10 物理归档索引 |
| `archive/v10/reports/207-v10-closure-report.md` | V10 closure report |
| `tasks/V11-README.md` | V11 正式阶段入口 |
| `tasks/V11-Plan.md` | V11 早期规划备忘 |
| `tasks/208-v11-readiness-audit.md` | Task 208 任务书 |
| `tasks/208-v11-readiness-audit-DONE.md` | Task 208 DONE |
| `docs/reports/208-v11-readiness-audit.md` | V11 readiness audit 报告 |
| `docs/quickstart.md` | 外部技术用户 Quickstart |
| `docs/troubleshooting.md` | 故障排查入口 |
| `tasks/209-v11-quickstart-docs.md` | Task 209 任务书 |
| `tasks/209-v11-quickstart-docs-DONE.md` | Task 209 DONE |
| `docs/reports/209-quickstart-evidence.md` | Task 209 命令证据 |
| `tasks/210-v11-doctor-preflight.md` | Task 210 任务书 |
| `tasks/210-v11-doctor-preflight-DONE.md` | Task 210 DONE |
| `docs/reports/210-doctor-preflight-evidence.md` | Task 210 命令证据 |
| `tasks/211-v11-backup-restore-schema-ledger.md` | Task 211 任务书 |
| `tasks/211-v11-backup-restore-schema-ledger-DONE.md` | Task 211 DONE |
| `docs/reports/211-backup-restore-evidence.md` | Task 211 命令证据 |
| `tasks/212-v11-failure-recovery.md` | Task 212 任务书 |
| `tasks/212-v11-failure-recovery-DONE.md` | Task 212 DONE |
| `docs/reports/212-failure-recovery-evidence.md` | Task 212 命令证据 |
| `tasks/213-v11-run-bundle.md` | Task 213 任务书 |
| `tasks/213-v11-run-bundle-DONE.md` | Task 213 DONE |
| `docs/reports/213-run-bundle-evidence.md` | Task 213 命令证据 |

## 最新归档状态

- `tasks/` 保留活跃入口：`TEMPLATE.md`、`V10-README.md`、`V11-README.md`、`V11-Plan.md`；Task 208-213 任务书与 DONE 作为 V11 当前审计、文档闭环、preflight、资产生命周期、失败恢复和 run bundle 记录已落盘。
- V10 单项任务书与 DONE 文档已移至 `archive/v10/tasks/`。
- V10 JSON artifact 已移至 `archive/v10/artifacts/`。
- V10 Markdown 报告已移至 `archive/v10/reports/`。
- V5-V9 阶段 README 已移至各自 `archive/v*/` 目录。
- 历史调研、旧 code review 计划和旧 scoring 文档已移至 `archive/docs/`。

## 下一步

1. 启动 Task 214：配置安全与 profile validate，增加推荐范围、危险项提示、rollback/history 或等价机制。
2. 后续按证据推进 Task 215 release checklist。
3. 只做开源可用化收尾，不扩张生成能力；若要使用 V10 历史证据，优先读 `archive/v10/INDEX.md`。

## 守护项

- CED 仍只统计 consistency-only、merged/source、正文证据口径。
- T9 仍是硬红线，不接受解释性豁免。
- Task 197-206 的信号保持 report-only / spike，不作为自动 accept/reject 条件。
- 任何 runtime、prompt、harness 或质量 hard gate 改动，按 `AGENTS.md` 补对应测试和必要短窗口回归。
