# Task 209: Quickstart 与用户文档闭环

> **阶段**: V11 开源可用化收尾
> **状态**: DONE
> **任务类型**: 文档闭环、命令证据、失败路由
> **输入**: Task 208 readiness audit
> **证据**: `docs/reports/209-quickstart-evidence.md`

## 目标

基于 Task 208 readiness audit，把 Songyan 面向外部技术用户的 README/docs 改成可执行、可验证、可复现的最短路径文档。覆盖 install -> env -> doctor -> create-project -> Ch1-3 run -> report -> export，并补充 10 章教程、成本说明、日志位置、失败入口和当前限制。

Task 209 只做文档、命令证据和路由校准，不修改 runtime、prompt、CED、T9、five-gate 或 hard gate。凡是需要 runtime 修复的缺口登记到 Task 210/212/215。

## 范围

- 更新 `README.md` 的 Quickstart 和常用命令。
- 新增 `docs/quickstart.md`，承载详细 Quickstart、Ch1-3、10 章教程、成本与日志说明。
- 新增 `docs/troubleshooting.md`，承载故障入口和后续任务路由。
- 新增 `docs/reports/209-quickstart-evidence.md`，记录实跑命令和结果。
- 更新 `docs/STATUS.md`、`docs/INDEX.md`、`tasks/V11-README.md`。

## 禁止项

- 不修改 `src/` runtime。
- 不修改 prompt card。
- 不修改 CED、T9、five-gate、segment audit 或 hard gate。
- 不实现 doctor/preflight、backup/restore、run bundle、profile validate 或 release checklist。
- 不提交隔离目录产生的 DB、日志、导出文件或 wrapper 输出。

## Task 208 输入缺口

| 缺口 | Task 209 处理 | 后续路由 |
|------|---------------|----------|
| README 写 Ch1-5，不符合 V11 Ch1-3 | 改为 Ch1-3 | 209 完成 |
| 缺 `doctor --init-db` | README 和 quickstart 明确加入 | 209 完成 |
| 缺 run_id/report 路径说明 | README 和 quickstart 明确加入 | 209 完成 |
| 缺 10 章教程 | `docs/quickstart.md` 增加 10 章教程 | 209 完成 |
| 缺成本和日志说明 | `docs/quickstart.md` 增加成本、日志、wrapper | 209 完成 |
| 缺故障入口 | `docs/troubleshooting.md` 增加故障路由 | 209 完成 |
| run 业务失败 exit code 0 | 文档记录限制，不修 runtime | 210/212 |
| 非法 checkpointer traceback | 文档记录限制，不修 runtime | 210 |
| backup/restore 缺失 | 文档记录限制 | 211 |
| run bundle 缺失 | 文档记录限制 | 213 |
| profile validate/rollback 缺失 | 文档记录限制 | 214 |
| wheel smoke/release docs 缺失 | 文档记录限制 | 215 |

## 文档结构

| 文件 | 用途 |
|------|------|
| `README.md` | 对外最短 Quickstart、常用命令和限制 |
| `docs/quickstart.md` | 详细安装、配置、自检、建项、Ch1-3、10 章、报告、导出、成本日志 |
| `docs/troubleshooting.md` | 故障排查入口、失败后下一步、脱敏分享建议 |
| `docs/reports/209-quickstart-evidence.md` | 本任务命令证据 |

## 完成条件

- [x] Task 209 任务书落盘。
- [x] README Quickstart 改为 V11 外部用户最短路径。
- [x] 详细 Quickstart / 10 章教程 / 成本日志 / 故障入口文档落盘。
- [x] 每条关键命令都有实跑证据、失败证据或后续任务路由。
- [x] `docs/STATUS.md`、`docs/INDEX.md`、`tasks/V11-README.md` 同步。
- [x] 未修改 runtime、prompt、CED、T9、five-gate 或 hard gate。
