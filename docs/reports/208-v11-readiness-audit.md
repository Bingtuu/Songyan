# Task 208 V11 Readiness Audit Report

> **日期**: 2026-08-01
> **范围**: README、CLI、doctor、create-project、run、report、export、profile、安装、配置、发布纪律
> **结论**: 可以进入 Task 209，但不能标记为正式开源可用版本
> **边界**: 本报告只做审计和任务拆分，未修改 runtime、prompt、CED、T9、five-gate 或 hard gate。

## 执行摘要

Songyan 当前已有外部技术用户路径的基础骨架：

- `songyan` console script 可调用，CLI 主命令存在。
- `doctor` 支持 JSON 输出、缺 key 检查、SQLite URL 检查、DB schema 初始化、资源枚举和 checkpointer 模式检查。
- `create-project --template xuanhuan` 能在非仓库 cwd 下创建项目。
- `report` 能从失败 run 的 JSONL 生成 Markdown 报告。
- `export` 能明确拒绝无 accepted 章节的项目。
- `profile show/diff/upsert` 已存在，并有测试覆盖。
- CI 已覆盖 ruff、mypy、默认 pytest 和 CLI pytest。

但开源门槛尚未达标：

- README 写出了最短路径，但没有绑定“外部环境 Ch1-3 成功运行”的证据，也没有 dry-run smoke。
- 缺 key 时 `run` 会记录失败，但最终进程 exit code 为 0，容易误导自动化脚本和用户。
- `doctor` 对非法 `CHECKPOINTER_MODE` 的体验是导入期 traceback，而不是结构化 doctor 报告。
- backup/restore、run bundle、profile validate/rollback 均未实现。
- 发布侧缺 CHANGELOG、CONTRIBUTING、issue templates、release checklist、wheel smoke。
- 当前 editable 安装元数据版本为 `0.1.0`，而 `pyproject.toml` 为 `2.0.0`，发布版本纪律需要收敛。

## 审计环境

| 项 | 结果 |
|----|------|
| OS | Windows |
| 仓库 cwd | `c:/Vibe Project/Songyan` |
| 隔离 cwd | `%TEMP%/songyan-task208-audit` |
| CLI 调用方式 | `python -c "from songyan.cli.main import cli; cli()" ...` 与本机 `songyan --help` |
| 隔离 DB | `%TEMP%/songyan-task208-audit/quickstart.db` |
| LLM key | 使用空值或 dummy 值做诊断，不发起真实生成成功验收 |

## 文档审计

| 文档 | 状态 | 证据 | 缺口 |
|------|------|------|------|
| `README.md` | partial | 已说明项目定位、安装、配置、doctor、create-project、run、export、常用命令 | Quickstart 直接写 Ch1-5，V11 要求是 Ch1-3；缺 cost、run_id、report、失败恢复、无真实外部环境成功证据 |
| `docs/STATUS.md` | pass | 指向 V11 readiness audit，边界清楚 | Task 208 完成后需更新状态 |
| `docs/INDEX.md` | pass | V11 正式入口指向 `tasks/V11-README.md` | Task 208 完成后应增加审计报告路由 |
| `tasks/V11-README.md` | pass | 已定义开源门槛、Task 208-215、审计先行 | Task 状态需要按本次审计更新 |
| `tasks/V11-Plan.md` | pass | 已降级为早期备忘 | 无 |

## CLI 能力盘点

实际 CLI 主命令：

| 命令 | 状态 | 说明 |
|------|------|------|
| `doctor` | partial | 支持 `--json`、`--check-llm`、`--init-db` |
| `create-project` | partial | 支持交互创建和 `--template` |
| `list-projects` | pass | 可列出项目 |
| `run` | partial | 支持 `--chapters`、`--auto-confirm`、`--resume`、`--run-id`、`--on-failure`、`--gate-mode` |
| `report` | partial | 从 JSONL 生成 Markdown 报告 |
| `export` | partial | 导出 accepted 正文，空 accepted 时明确失败 |
| `profile show/diff/upsert` | partial | 可查看、比较、写入 profile override |
| `metrics` | internal | 面向内部长期度量，非 Quickstart 必需 |
| `index` | internal | RAG 索引工具，非 Quickstart 必需 |
| `mark` | internal | 人工标记工具，非 Quickstart 必需 |

缺失命令：

| 缺口 | 影响 | 后续任务 |
|------|------|----------|
| `backup` / `restore` | 长期项目资产不可迁移、不可恢复 | 211 |
| `report --bundle` 或 `bundle-run` | 缺可分享、可脱敏诊断包 | 213 |
| `profile validate` | 配置危险值无法集中校验 | 214 |
| profile rollback/history | 外部用户调参后无法安全回退 | 214 |
| release/checklist smoke | 开源发布不可复验 | 215 |

## 最短路径实跑结果

### 1. doctor 缺 key

命令在非仓库 cwd 下运行，`DATABASE_URL` 指向隔离 DB，`LLM_API_KEY` 为空。

| 项 | 结果 |
|----|------|
| exit code | 1 |
| 总状态 | fail |
| 关键证据 | `llm.key` fail，提示设置 `LLM_API_KEY` 或 `.env` |
| 其他证据 | `resources.package` pass，7 genres、4 modes、7 templates |
| 判断 | 缺 key 可诊断，资源枚举在非仓库 cwd 下成立 |

### 2. doctor 初始化 DB

命令在非仓库 cwd 下运行，使用 dummy key，`--init-db` 初始化隔离 DB。

| 项 | 结果 |
|----|------|
| exit code | 0 |
| 总状态 | warn |
| pass | 7 |
| warn | 1 |
| warn 原因 | `.env not found` |
| 判断 | DB schema 初始化与资源检查可用；但环境变量已足够时 `.env` 缺失仍为 warn，需在 Task 210 判断是否合理 |

### 3. create-project

命令：`create-project --template xuanhuan`。

| 项 | 结果 |
|----|------|
| exit code | 0 |
| project_id | `1d73e07936404c1ab1bf9829a7f86a3c` |
| 模式 | `webnovel_intense` |
| 题材 | `xuanhuan` |
| 标题 | `灵渊纪` |
| 判断 | 模板建项在非仓库 cwd 成立 |
| 体验问题 | 输出混入大量 repository 日志；无 `--quiet` 或 onboarding 摘要 |

### 4. run Ch1-3 缺 key失败

命令使用隔离 DB、空 key、`--chapters 1-3 --auto-confirm --skip-rag --gate-mode observe --on-failure abort`，并用 90 秒 wrapper 包裹。

| 项 | 结果 |
|----|------|
| wrapper 结果 | `WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| 进程 exit code | 0 |
| run_id | `run-ab257f3e` |
| 成功章节 | 0 |
| 失败章节 | `[1]` |
| 失败原因 | `GoalPlanner LLM call failed: LLM API Key 未配置` |
| 判断 | 失败被记录，但 exit code 0 会误导用户和 CI；Ch1-3 实际只到 Ch1 失败 |
| 额外噪声 | LiteLLM 输出 botocore warning；DB maintenance 出现 `database table is locked` warning |

### 5. report

命令：`report --run-id run-ab257f3e`。

| 项 | 结果 |
|----|------|
| exit code | 0 |
| 输出 | `logs/reports/report-run-ab257f3e.md` |
| 报告内容 | Ch1 失败、达标率 0.0%、DG-1 未通过、失败原因含缺 key |
| 判断 | report 对失败 run 有解释力 |
| 缺口 | 只有 Markdown，没有诊断 bundle JSON、日志索引、脱敏策略 |

### 6. export

命令：`export --project-id 1d73e07936404c1ab1bf9829a7f86a3c --format md --output exports`。

| 项 | 结果 |
|----|------|
| exit code | 1 |
| 错误 | `项目 ... 没有可导出的 accepted 章节` |
| 判断 | 错误清楚；但外部 Quickstart 需要在 Ch1-3 accepted 后再验 export |

## 错误体验审计

| 场景 | 当前表现 | 状态 | 后续任务 |
|------|----------|------|----------|
| 缺 `LLM_API_KEY` in doctor | JSON fail，有 hint | pass | 210 保持 |
| 缺 `LLM_API_KEY` in run | run 失败写日志，但 exit code 0 | partial | 210/212 |
| 非 SQLite `DATABASE_URL` | doctor JSON fail，有 hint | pass | 210 保持 |
| 非法 `CHECKPOINTER_MODE` | 导入期 pydantic traceback | missing | 210 |
| DB 不存在 | doctor warn，建议 `--init-db` | pass | 210 保持 |
| 缺 run log | report 警告但 exit code 0 | partial | 212/213 |
| 无 accepted 章节 export | exit code 1，错误清楚 | pass | 209 文档化 |
| 非法模板 | exit code 1，列 available；但混入 seed/template 噪声 | partial | 209/210 |

## 安装与发布审计

| 项 | 当前状态 | 判断 |
|----|----------|------|
| `pyproject.toml` | 有 `songyan = "songyan.cli.main:cli"`，版本 `2.0.0` | partial |
| 本机 editable 安装 | `pip show songyan` 显示版本 `0.1.0`，editable path 指向本仓库 | partial |
| console script | `songyan --help` 可运行 | pass |
| package data | `songyan` 包含 yaml/json/md/sql，`evals` 包含 seeds | pass |
| 非仓库 cwd 资源 | doctor pass，create-project pass | partial |
| wheel build smoke | 未执行，CI 未覆盖 | missing |
| CHANGELOG | 根目录未发现 | missing |
| CONTRIBUTING | 根目录未发现 | missing |
| issue templates | `.github` 仅有 workflow | missing |
| release checklist | 未发现 | missing |
| License | `LICENSE` 存在，AGPL-3.0 | pass |
| CI | ruff、mypy、默认 pytest、CLI pytest | partial |

## 开源门槛矩阵

| 开源门槛 | 状态 | 证据 | 下一步 |
|----------|------|------|--------|
| 用户不读历史任务也能理解项目定位 | partial | README 和 V11 README 有定位；README 仍引用 V10 任务入口作为验证详情 | Task 209 重写 Quickstart 与外部用户 docs |
| 新环境能完成最短闭环 | partial | 非仓库 cwd 下 doctor 和 create-project 可用；run 因缺 key失败且 exit 0；export 无 accepted 失败 | Task 209/210 提供真实 Ch1-3 证据或 dry-run smoke |
| 发布物不依赖仓库工作目录 | partial | 源码 PYTHONPATH 非仓库 cwd 验证通过；wheel 未验 | Task 215 增加 wheel + 非仓库 cwd smoke |
| 本地环境问题可诊断 | partial | doctor 覆盖 key、DB、schema、resources；非法 checkpointer traceback；预算/日志路径未覆盖 | Task 210 |
| 失败后知道怎么恢复 | missing | run/report 能显示失败，但无标准恢复分类，run 失败 exit 0 | Task 212 |
| 长期项目资产可保护 | missing | 无 backup/restore 命令 | Task 211 |
| 问题可复现、可脱敏分享 | missing | report 仅 Markdown，无 bundle JSON、日志索引、脱敏 | Task 213 |
| 配置不容易误伤系统 | partial | profile show/diff/upsert 存在；无 validate/rollback/history/危险范围提示 | Task 214 |
| 开源发布物可信 | partial | License/CI/console script 存在；缺 changelog、contributing、issue templates、release checklist、wheel smoke；版本元数据不一致 | Task 215 |
| 既有质量边界不退化 | pass | Task 208 未改 runtime/prompt/hard gate；聚焦测试通过 | 全阶段守护 |

## Task 209-215 校准

| Task | 校准后优先级 | 范围调整 | 输入证据 | 验收证据 |
|------|--------------|----------|----------|----------|
| 209 Quickstart 与用户文档闭环 | P0 | 先把 README Quickstart 改为 `doctor --init-db -> create-project -> Ch1-3 -> report -> export`；明确真实 LLM key 和成本前提；补失败时下一步 | 本报告文档审计、非仓库 cwd 实跑 | README/docs 命令逐条可执行；至少一份 Ch1-3 成功或 dry-run 替代证据 |
| 210 doctor / preflight 增强 | P0 | 覆盖非法 settings 导入、日志路径、预算、run 前 preflight、LLM endpoint probe 分级；处理 run 失败 exit code | doctor 与 run 错误样本 | JSON + human 输出；缺 key/非法 checkpointer/不可写路径/预算等测试 |
| 211 backup / restore / schema ledger | P1 | 实现资产包或等价 backup/restore；schema ledger 区分 export 和 backup | 缺命令审计 | backup 后 restore 到新路径并通过 doctor/export |
| 212 失败恢复体验 | P1 | 标准化至少 5 类失败：缺 key、LLM endpoint、成本熔断、schema drift、质量门/settlement 失败；明确 resume/isolate/retry | run/report 失败样本 | 故障注入演练或自动化测试 |
| 213 run bundle 诊断包 | P1 | 在 report 基础上增加 JSON + Markdown bundle、日志索引和脱敏 | report 缺口 | bundle 不含 API key、敏感 env、绝对路径默认脱敏 |
| 214 配置安全与 profile validate | P2 | 在现有 show/diff/upsert 上增加 validate、推荐范围、危险项、rollback/history 或等价机制 | profile 审计 | profile validate 测试覆盖危险值 |
| 215 Release checklist 与总验收 | P2 | 补 CHANGELOG、CONTRIBUTING、issue templates、release checklist、wheel smoke、版本一致性 | 发布审计 | wheel + 非仓库 cwd + Windows smoke；CI/release checklist 通过 |

## 是否进入 Task 209

可以进入 Task 209。

理由：Task 208 已冻结外部用户路径的真实缺口，且 Quickstart 文档是后续 doctor、backup、bundle、release 的共同入口。Task 209 不应试图一次补齐所有工具，应先把“外部用户最短路径”写成可执行命令链，并把无法通过的点明确路由给 Task 210-215。

限制：在 Task 209-215 完成前，Songyan 只能视为内部可用或 preview，不能标记为正式开源可用版本。

## 审计验证

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/cli -q` | 35 passed |
| `python -m pytest tests/test_177_export_service.py tests/test_178_resource_loading.py tests/test_183_profile_cli.py tests/test_119_reporting_wrapper.py -q` | 40 passed |
| `songyan --help` | exit 0 |
| `doctor --json` 缺 key | exit 1，结构化 fail |
| `doctor --json --init-db` dummy key | exit 0，schema complete |
| `create-project --template xuanhuan` | exit 0 |
| `run --chapters 1-3` 空 key | exit 0，但业务失败 |
| `report --run-id run-ab257f3e` | exit 0 |
| `export` 无 accepted | exit 1 |

## 守护声明

本任务没有修改 `src/`、`tests/`、prompt card、CED、T9、five-gate、segment audit 或核心生成链路。所有 runtime 缺口均登记为后续任务输入。
