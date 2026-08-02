# Songyan 文档索引

> 短版文档路由。默认只读当前入口；历史细节进入对应 `archive/` 索引。

## 默认必读

| 文件 | 用途 |
|------|------|
| `README.md` | 对外项目说明、快速开始和能力概览 |
| `AGENTS.md` | 开发代理短指令与不可违背规则 |
| `docs/STATUS.md` | 当前状态、下一步和归档状态 |
| `docs/quickstart.md` | 外部技术用户 Quickstart、10 章教程、成本和日志 |
| `docs/troubleshooting.md` | 故障排查入口和当前限制 |
| `tasks/V10-README.md` | V10 阶段总结入口 |
| `tasks/V11-README.md` | V11 正式阶段入口、开源门槛、Task 208-215 拆分 |
| `docs/reports/208-v11-readiness-audit.md` | Task 208 readiness audit 报告 |
| `docs/reports/209-quickstart-evidence.md` | Task 209 Quickstart 命令证据 |
| `docs/reports/210-doctor-preflight-evidence.md` | Task 210 doctor / preflight 命令证据 |
| `docs/reports/211-backup-restore-evidence.md` | Task 211 backup / restore 命令证据 |

## 当前开发入口

| 场景 | 文件 |
|------|------|
| V11 启动 | `tasks/V11-README.md` |
| V11 当前任务 | Task 212 失败恢复体验 |
| 外部用户 Quickstart | `docs/quickstart.md` |
| 故障排查 | `docs/troubleshooting.md` |
| V11 readiness audit | `docs/reports/208-v11-readiness-audit.md` |
| Quickstart 证据 | `docs/reports/209-quickstart-evidence.md` |
| doctor / preflight 证据 | `docs/reports/210-doctor-preflight-evidence.md` |
| backup / restore 证据 | `docs/reports/211-backup-restore-evidence.md` |
| 开源门槛 | `tasks/V11-README.md` 的“开源门槛与 V11 目标” |
| V11 规划备忘 | `tasks/V11-Plan.md` |
| V10 追溯 | `archive/v10/INDEX.md` |
| V10 closure report | `archive/v10/reports/207-v10-closure-report.md` |
| 架构手册 | `docs/architecture/04-vibe-coding-engineering.md` |
| 技术参考 | `docs/architecture/05-tech-reference.md` |
| 开发规范 | `AGENTS.md` |

## 归档入口

| 阶段 | 入口 |
|------|------|
| V10 | `archive/v10/INDEX.md` |
| V9 | `archive/v9/INDEX.md` |
| V8 | `archive/v8/INDEX.md` |
| V7 | `archive/v7/INDEX.md` |
| V6 | `archive/v6/INDEX.md` |
| V5 | `archive/v5/INDEX.md` |
| V4 | `archive/v4/INDEX.md` |
| V3 | `archive/v3/INDEX.md` |
| 早期任务 | `archive/tasks/` |
| 旧计划/规格 | `archive/superpowers/INDEX.md` |
| 历史分析文档 | `archive/docs/` |

## 当前目录约定

- `tasks/` 只保留活跃阶段入口、模板和当前/下一阶段计划。
- `archive/v10/tasks/` 保存 V10 Task 189-207 的任务书和 DONE 文档。
- `archive/v10/artifacts/` 保存 V10 JSON 样本、manifest 和 report artifact。
- `archive/v10/reports/` 保存 V10 Markdown 报告。
- `docs/reports/` 不再作为默认活跃报告目录；新报告若不是 README 直引，应优先进入任务归档或被 `.gitignore` 忽略。

## V11 当前路由

- 正式阶段事实入口：`tasks/V11-README.md`。
- 早期规划备忘：`tasks/V11-Plan.md`，不再作为正式执行入口。
- 当前状态：Task 208 readiness audit 已完成，审计报告见 `docs/reports/208-v11-readiness-audit.md`。
- Task 209 Quickstart 与用户文档闭环已完成，证据见 `docs/reports/209-quickstart-evidence.md`。
- Task 210 doctor / preflight 增强已完成，证据见 `docs/reports/210-doctor-preflight-evidence.md`。
- Task 211 backup / restore / schema ledger 已完成，证据见 `docs/reports/211-backup-restore-evidence.md`。
- 下一步：启动 Task 212 失败恢复体验，标准化常见失败分类、提示和恢复动作。
- 正式开源条件：必须满足 `tasks/V11-README.md` 的开源门槛；未满足时只能内部使用或发 preview。
