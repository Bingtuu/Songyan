# V11 Task 总索引

> **阶段**: 开源可用化收尾
> **定位**: V11 是正式开源前最后一个工程阶段，目标是把已有能力交付给外部技术用户，而不是继续扩张生成能力。
> **当前口径**: V10 已全量闭环并归档；V11 从 Task 208 启动。`tasks/V11-Plan.md` 是早期备忘，本文是 V11 正式阶段入口。
> **状态**: 已启动；Task 208 readiness audit、Task 209 Quickstart 文档闭环、Task 210 doctor / preflight 增强已完成，下一步进入 Task 211 backup / restore / schema ledger。

---

## 设计评审结论

`tasks/V11-Plan.md` 的总体方向是合理的：它把 V11 明确限定为开源前收口，面向懂命令行、能配置 LLM API key 的外部技术用户，并且排除了 Web/UI、账号、后台服务和新一轮质量研究。这条边界必须保留。

需要收紧的地方有三点：

1. **先审计再开发**：不能直接从 Quickstart 或 doctor 增强开写。首任务必须从外部用户最短路径做 readiness audit，冻结当前缺口和任务拆分。
2. **文档必须绑定可执行命令**：README / docs 不能只写“应该可以”，每条 Quickstart 路径必须有本地命令或自动化证据。
3. **工具增强必须服务交付路径**：backup/restore、run bundle、profile validate 等都是外部可用化工具，不是新的生成能力或质量研究入口。

结论：V11 可以开始，但必须按“小批量、证据先行、不开新能力口子”的方式推进。

---

## 一句话目标

> 让一个懂命令行、会配置 API key 的外部技术用户，不读 V5-V10 历史任务文档，也能按 README/docs 完成安装、doctor 自检、项目创建、短窗口生成、失败恢复、报告理解、备份恢复和书稿导出。

---

## 开源门槛与 V11 目标

V11 完成后，Songyan 应达到“负责任开源给外部技术用户”的条件。这里的开源门槛不是普通商业产品门槛，而是技术用户可以独立安装、运行、诊断、恢复和提交可复现问题的最低条件。

| 开源门槛 | V11 对应目标 | 主要任务 |
|----------|--------------|----------|
| 用户不读历史任务也能理解项目定位 | README 和 docs 聚焦项目能力、快速开始、常用命令、当前限制 | 208、209 |
| 新环境能完成最短闭环 | `doctor -> create-project -> run Ch1-3 -> export` 有文档和实跑证据 | 208、209、210 |
| 发布物不依赖仓库工作目录 | wheel / 非仓库 cwd / Windows 路径下资源枚举、项目创建、短窗口生成、导出通过 | 209、215 |
| 本地环境问题可诊断 | API key、LLM endpoint、DB schema、资源、写权限、预算、日志路径都有明确检查和下一步建议 | 210 |
| 失败后知道怎么恢复 | 至少 5 类常见失败有分类、提示、恢复命令或诊断路径 | 212 |
| 长期项目资产可保护 | DB、配置、运行摘要和关键日志索引可 backup/restore 或形成等价资产包 | 211 |
| 问题可复现、可脱敏分享 | run bundle 输出 JSON + Markdown，包含章节状态、成本、质量门、日志索引，并过滤敏感信息 | 213 |
| 配置不容易误伤系统 | profile validate、推荐范围、危险项提示、rollback/history 或等价安全机制可用 | 214 |
| 开源发布物可信 | 版本号、CHANGELOG、Release checklist、License、贡献指南、issue 模板、最小复现指南齐备 | 215 |
| 既有质量边界不退化 | V9/V10 守护项仍成立：SQLite 事实源、CED 口径、T9 纪律、五门口径、report-only 边界不破 | 全阶段 |

不满足以上门槛时，可以继续内部使用或发 preview，但不应标记为正式开源可用版本。

---

## 硬边界

- 不扩张核心生成能力。
- 不新增核心 Agent / Workflow 节点。
- 不做 Web UI、桌面端、账号系统、云同步、后台任务队列、多人协作或模板市场。
- 不启动新一轮体裁研究、质量研究或 prompt 提质主线。
- 不把 Task 197-206 的 report-only / spike 信号接入 prompt、CED 或 hard gate。
- CED 仍只统计 consistency-only、merged/source、正文证据口径。
- T9 仍是硬红线，不接受解释性豁免。
- SQLite 仍是唯一长期事实源。

---

## 用户路径

V11 只服务以下外部技术用户路径：

1. 安装项目或 wheel。
2. 配置 `.env` / LLM endpoint / API key。
3. 运行 `songyan doctor`，知道本地环境是否可用。
4. 从模板创建项目。
5. 运行 Ch1-3 短窗口生成。
6. 查看 run/report/cost/log。
7. 遇到常见失败时按提示恢复。
8. 备份项目资产，必要时恢复。
9. 导出 accepted 正文。
10. 按 release docs 判断当前版本是否可用。

---

## 验收矩阵

| 组 | 验收目标 | 通过标准 |
|----|----------|----------|
| A | 安装与 Quickstart | README/docs 可从空环境走到 `doctor -> create-project -> run Ch1-3 -> export` |
| B | 非仓库 cwd / wheel | wheel 安装后资源枚举、项目创建、短窗口生成、导出通过 |
| C | doctor 与错误提示 | 缺 key、DB/schema、资源、写权限、LLM 配置等问题有明确状态和下一步 |
| D | 项目资产 | backup/restore 或等价资产包可保存 DB、配置、关键日志索引和运行摘要 |
| E | 失败恢复 | 至少 5 类常见失败有恢复路径和测试或演练证据 |
| F | run bundle | 一条命令输出可分享的 JSON + Markdown 诊断包，并完成脱敏 |
| G | 配置安全 | profile diff/validate/rollback 或等价能力能约束危险参数 |
| H | 发布纪律 | 版本号、CHANGELOG、release checklist、CI/wheel smoke、最小复现指南齐备 |
| I | 既有守护项 | 不破坏 scifi 回归、五门口径、CED 口径、T9 纪律和 SQLite 事实源 |

---

## Task 拆解

| Task | 名称 | 状态 | 目标 | 依赖 |
|------|------|:----:|------|------|
| 208 | V11 readiness audit | DONE | 从外部技术用户视角只读审计 README、CLI、doctor、create-project、run、export、report 路径，产出缺口清单和后续任务拆分 | V10 closure |
| 209 | Quickstart 与用户文档闭环 | DONE | 把 README/docs 改成可执行最短路径，覆盖 Ch1-3、10 章教程、成本、日志、导出和故障入口 | 208 |
| 210 | doctor / preflight 增强 | DONE | 强化本地环境、资源、schema、LLM、写权限、预算和日志检查，输出机器可读 JSON 与人类可读建议 | 208/209 |
| 211 | backup / restore / schema ledger | 待定 | 建立项目资产生命周期：备份、恢复、schema 版本/迁移状态校验，明确 export 与 backup 边界 | 208 |
| 212 | 失败恢复体验 | 待定 | 标准化常见失败分类、提示和恢复动作，覆盖 retry/resume/isolate/提额/诊断包路径 | 208/210 |
| 213 | run bundle 诊断包 | 待定 | 输出 run 元信息、章节状态、成本、五门/T9/CED/overdue/health、日志索引和脱敏报告 | 208/210 |
| 214 | 配置安全与 profile validate | 待定 | 增加推荐范围、危险项提示、validate、rollback/history 或等价安全机制 | 208/210 |
| 215 | Release checklist 与开源前总验收 | 待定 | wheel、非仓库 cwd、Windows、CI、CHANGELOG、license/contributing/issue templates、最小复现指南总验收 | 209-214 |

---

## Task 208 审计结论

Task 208 已完成。任务书见 `tasks/208-v11-readiness-audit.md`，DONE 见 `tasks/208-v11-readiness-audit-DONE.md`，审计报告见 `docs/reports/208-v11-readiness-audit.md`。

结论：

- 可以进入 Task 209。
- 当前仍不能标记为正式开源可用版本，只能视为内部可用或 preview。
- 已有基础：CLI 主入口、doctor、模板建项、report、export、profile、资源枚举和 CI。
- 主要缺口：Quickstart 成功证据不足、run 失败 exit code 语义不清、非法配置 traceback、backup/restore 缺失、run bundle 缺失、profile validate/rollback 缺失、release checklist 和 wheel smoke 缺失。

Task 209 应优先把外部用户最短路径写成可执行命令链，并把无法通过的点明确路由给 Task 210-215。

---

## Task 209 文档闭环结论

Task 209 已完成。任务书见 `tasks/209-v11-quickstart-docs.md`，DONE 见 `tasks/209-v11-quickstart-docs-DONE.md`，命令证据见 `docs/reports/209-quickstart-evidence.md`。

交付：

- `README.md` 的 Quickstart 已改为 `doctor --init-db -> create-project -> run Ch1-3 -> report -> export`。
- `docs/quickstart.md` 增加详细 Quickstart、10 章教程、成本预算、日志位置、Windows wrapper 和当前限制。
- `docs/troubleshooting.md` 增加缺 key、DB、run 失败、report、export、Windows wrapper、脱敏分享等故障入口。
- Task 209 在隔离目录复跑了 help、doctor、init-db、create-project、失败 run、report、export 和 list-projects。

Task 209 留给后续实现的 runtime 缺口中，非法 `CHECKPOINTER_MODE` traceback 与 `run` 业务失败 exit code 语义已由 Task 210 收口。

仍需后续实现：

- Task 211：backup/restore。
- Task 212：失败恢复分类、提示和 retry/resume/isolate 体验。
- Task 213：run bundle 与脱敏诊断包。
- Task 214：profile validate、危险项提示、rollback/history。
- Task 215：真实 Ch1-3 release smoke、wheel smoke、CHANGELOG、CONTRIBUTING、issue templates、release checklist。

---

## Task 210 doctor / preflight 结论

Task 210 已完成。任务书见 `tasks/210-v11-doctor-preflight.md`，DONE 见 `tasks/210-v11-doctor-preflight-DONE.md`，命令证据见 `docs/reports/210-doctor-preflight-evidence.md`。

交付：

- 非法 `CHECKPOINTER_MODE` 不再导致 CLI 导入期 traceback，改由 `runtime.checkpointer` 结构化诊断。
- 非法 `SONGYAN_RUN_COST_BUDGET` / `RUN_COST_BUDGET` 不再导致导入期 traceback，改由 `runtime.budget` 结构化诊断。
- `songyan doctor` 增加 `config.load`、`logs.path`、`runtime.budget` 等检查。
- `songyan run` 增加 strict preflight，覆盖 LLM key/config、DB/schema、资源、日志路径、预算、runtime checkpointer 和项目存在性。
- `songyan run` 在 preflight fail 时 exit 1，不进入 pipeline；pipeline 返回 `partial` / `failed` 或存在失败章节时保留 `run_id` 并 exit 1。

仍需后续实现：

- Task 211：项目资产 backup/restore 或等价资产包。
- Task 212：常见失败分类、恢复命令和演练证据。
- Task 213：run bundle 与脱敏诊断包。
- Task 214：profile validate、危险项提示、rollback/history。
- Task 215：真实 Ch1-3 release smoke、wheel smoke、发布文档和总验收。

---

## 文档入口策略

- `README.md` 面向外部用户，只保留项目定位、快速开始、常用命令和当前状态。
- `docs/STATUS.md` 保持短状态板。
- `docs/INDEX.md` 保持短路由。
- `tasks/V11-README.md` 是 V11 阶段事实入口。
- `tasks/V11-Plan.md` 作为早期规划备忘保留，不再作为正式执行入口。
- 历史任务和报告默认只通过 `archive/` 查证。

---

## 风险与对策

| 风险 | 对策 |
|------|------|
| V11 膨胀成产品化大改 | 只面向外部技术用户；不做 UI/账号/后台 |
| 继续新增质量研究 | 禁止新增核心质量研究主线；质量能力留在 V10 归档 |
| 文档仍依赖历史任务 | README/docs 只写用户路径；历史任务只作审计材料 |
| backup/restore 影响事实源 | 先做只读审计和 schema ledger，再实现可写恢复 |
| run bundle 泄露敏感信息 | 必须有脱敏测试，API key、绝对路径、敏感 env 不进包 |
| 配置能力误用 | profile validate、推荐范围、危险项提示、rollback/history |
| 发布只在本机成立 | wheel + 非仓库 cwd + Windows 路径作为硬验收 |

---

## 与 V9/V10 的关系

- V9 解决生产化地基。
- V10 解决多体裁长窗口和优秀度观察层。
- V11 解决外部技术用户能否负责任地使用项目。

V11 是开源前收口，不是新产品线。
