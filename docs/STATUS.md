# Songyan 项目状态

> 短状态板。这里仅保留当前判断、最新事实源和下一步；历史任务、报告和样本 artifact 统一看 `archive/`。

## 当前判断

| 项 | 结论 |
|----|------|
| 当前阶段 | V10 已全量闭环，下一步进入 V11 开源可用化收尾 |
| V10 长窗口 | sci-fi Ch200 baseline 已冻结；xuanhuan / wuxia / urban 均完成 Ch200，总验收 accepted=200、gap=0、failed=[]、five-gate PASS、segment audit PASS、T9=0 |
| V10 优秀度信号 | Task 196-203 已完成，严格保持 report-only，不接 Writer / CreativeDirector prompt，不进 CED 或 hard gate |
| V10 结构 spike | KG diff、FactTrack validity interval、Storyline Tree 均完成，三者 decision=`defer`，不接 runtime / prompt / CED / hard gate |
| 当前代码面 | V11 之前不扩张生成能力，优先整理安装、配置、doctor、项目创建、导出和发布纪律 |

## 当前入口

| 文件 | 用途 |
|------|------|
| `README.md` | 对外开源入口 |
| `AGENTS.md` | 开发代理短规则 |
| `docs/INDEX.md` | 文档路由 |
| `tasks/V10-README.md` | V10 总结入口 |
| `archive/v10/INDEX.md` | V10 物理归档索引 |
| `archive/v10/reports/207-v10-closure-report.md` | V10 closure report |
| `tasks/V11-Plan.md` | V11 开源可用化预登记 |

## 最新归档状态

- `tasks/` 仅保留活跃入口：`TEMPLATE.md`、`V10-README.md`、`V11-Plan.md`。
- V10 单项任务书与 DONE 文档已移至 `archive/v10/tasks/`。
- V10 JSON artifact 已移至 `archive/v10/artifacts/`。
- V10 Markdown 报告已移至 `archive/v10/reports/`。
- V5-V9 阶段 README 已移至各自 `archive/v*/` 目录。
- 历史调研、旧 code review 计划和旧 scoring 文档已移至 `archive/docs/`。

## 下一步

1. 启动 Task 208：V11 readiness audit，从外部技术用户视角审计安装、配置、doctor、项目创建、运行、导出和报告路径。
2. 只做开源可用化收尾，不扩张生成能力。
3. 若要使用 V10 历史证据，优先读 `archive/v10/INDEX.md`，不要重新扫全量历史目录。

## 守护项

- CED 仍只统计 consistency-only、merged/source、正文证据口径。
- T9 仍是硬红线，不接受解释性豁免。
- Task 197-206 的信号保持 report-only / spike，不作为自动 accept/reject 条件。
- 任何 runtime、prompt、harness 或质量 hard gate 改动，按 `AGENTS.md` 补对应测试和必要短窗口回归。
