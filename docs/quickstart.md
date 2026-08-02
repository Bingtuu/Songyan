# Songyan Quickstart

> 面向外部技术用户。目标是在不阅读历史任务文档的情况下，完成安装、配置、自检、建项、Ch1-3 短窗口运行、报告查看和正文导出。

## 当前状态

Songyan 处于 V11 开源可用化收尾阶段。当前版本可以作为 preview 或内部可用版本验证，不应标记为正式开源可用版本。Task 208 已确认 Quickstart 骨架可用，Task 210 已补齐 doctor / run preflight 与失败 exit code，Task 211 已补齐 backup / restore / schema ledger，Task 212 已补齐常见失败分类和恢复建议；真实 Ch1-3 成功运行、wheel smoke、run bundle 和 profile validate 仍在 V11 后续任务中补齐。

## 环境要求

- Python >= 3.11。
- 一个兼容 OpenAI 接口的 LLM endpoint。默认配置使用 DeepSeek。
- 可写的本地目录，用于 SQLite DB、日志和导出文件。
- Windows 用户建议先使用 PowerShell，并在长跑时使用仓库脚本 `scripts/run_with_timeout.ps1`。如果当前目录不是仓库根目录，请用仓库绝对路径调用该脚本。

## 安装

开发安装：

```powershell
python -m pip install -e ".[dev]"
```

未来 release 包应支持 wheel 安装。wheel smoke 属于 Task 215 的验收项，当前 Quickstart 仍以开发安装为准。

确认 CLI 可用：

```powershell
songyan --help
```

期望能看到 `doctor`、`create-project`、`run`、`report`、`export` 等命令。

## 配置

复制配置模板：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，至少设置：

```dotenv
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
DATABASE_URL=sqlite:///songyan.db
CHECKPOINTER_MODE=sqlite
```

Windows 短窗口验证遇到 checkpoint 文件锁问题时，可以临时改为：

```dotenv
CHECKPOINTER_MODE=memory
```

成本预算可选：

```dotenv
SONGYAN_RUN_COST_BUDGET=10
```

`0` 表示不启用单次运行成本预算。预算相关失败会通过 `doctor` / preflight / report 输出恢复建议。

## 自检

第一次运行建议初始化或迁移 DB：

```powershell
songyan doctor --init-db
```

需要机器可读输出时：

```powershell
songyan doctor --json --init-db
```

`doctor` 当前会检查：

- `.env` 或环境变量配置。
- `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。
- SQLite `DATABASE_URL` 和 DB 父目录写权限。
- DB schema 完整性。
- `CHECKPOINTER_MODE`。
- `logs/` 路径可写性。
- `SONGYAN_RUN_COST_BUDGET` / `RUN_COST_BUDGET` 合法性。
- 体裁、模式、项目模板、prompt card、schema 等 package resources。

已知限制：

- 非法 `CHECKPOINTER_MODE`、非法预算、缺 key、DB/schema 等问题会输出结构化诊断。
- `--check-llm` 只做显式 LLM client 初始化探针，不默认发送生成请求。

## 创建项目

从模板创建玄幻项目：

```powershell
songyan create-project --template xuanhuan
```

输出中会出现：

```text
[OK] 项目已创建: <project_id>
```

后续命令都需要这个 `project_id`。如果忘记了，可以列出项目：

```powershell
songyan list-projects
```

常用模板包括 `scifi`、`xuanhuan`、`wuxia`、`urban`、`urban_fantasy`、`post_apocalyptic`、`mystery_noir`。

## Ch1-3 短窗口运行

使用自动确认模式生成前三章：

```powershell
songyan run --project-id <project_id> --chapters 1-3 --auto-confirm
```

Windows 下建议用硬超时 wrapper。该 wrapper 目前是仓库脚本，不是已安装的 `songyan` 子命令；如果当前目录不是仓库根目录，请改用仓库绝对路径。

```powershell
# 在仓库根目录下
powershell -File .\scripts\run_with_timeout.ps1 -TimeoutSec 3600 -- songyan run --project-id <project_id> --chapters 1-3 --auto-confirm

# 在任意 cwd 下
$songyanRepo = "C:\path\to\Songyan"
powershell -File "$songyanRepo\scripts\run_with_timeout.ps1" -TimeoutSec 3600 -- songyan run --project-id <project_id> --chapters 1-3 --auto-confirm
```

运行完成后记录输出里的：

```text
run_id: <run_id>
```

后续查看报告需要 `run_id`。

已知限制：

- `songyan run` 会先执行 preflight；缺少 `LLM_API_KEY`、非法配置、DB/schema 不可用或项目不存在时会在进入 pipeline 前 exit 1。
- 如果 pipeline 已启动后业务失败，命令会保留 `run_id` 并返回非 0 exit code。请用 `songyan report --run-id <run_id>` 查看失败原因。
- Task 209/210 未执行真实 LLM Ch1-3 成功验收，避免在文档与 preflight 任务中消耗 API 预算。正式开源前必须在 Task 215 补齐真实或明确替代的 smoke 证据。

## 生成报告

用 `run_id` 生成运行报告：

```powershell
songyan report --run-id <run_id>
```

默认输出：

```text
logs/reports/report-<run_id>.md
```

报告会包含章节成功率、失败章节、上下文预算、候选硬门禁、成本视图和失败原因。当前 `report` 只输出 Markdown；JSON + Markdown 诊断包和脱敏分享能力属于 Task 213。

## 导出正文

只有 accepted 章节能被导出。Ch1-3 accepted 后运行：

```powershell
songyan export --project-id <project_id> --chapters 1-3 --format md --output exports/
```

常用分组：

```powershell
songyan export --project-id <project_id> --by flat --format md --output exports/
songyan export --project-id <project_id> --by arc --format md --output exports/
songyan export --project-id <project_id> --by volume --format txt --output exports/
```

如果没有 accepted 章节，`export` 会失败并提示没有可导出的 accepted 章节。这不是数据丢失，而是说明项目还没有通过接收门槛的正文。

## 备份与恢复

`export` 只导出 accepted 正文，不保存可续跑状态。需要迁移或保护项目资产时，使用 `backup`：

```powershell
songyan backup --project-id <project_id> --output backups/
```

资产包是 zip，默认包含：

- `manifest.json`
- `db/songyan.db`
- `config/config.summary.json`
- `runs/project_runs.json`
- `logs/index.json`

默认不包含 `.env` 原文、API key 或日志正文。恢复到新 DB 路径：

```powershell
songyan restore --backup backups/songyan-backup-<project_id>-<timestamp>.zip --database-url sqlite:///restored.db
$env:DATABASE_URL = "sqlite:///restored.db"
songyan doctor --json
songyan list-projects
```

restore 默认拒绝覆盖已有 DB；确实需要覆盖时显式加 `--force`。

## 10 章教程

前三章通过后，可以扩展到 10 章：

```powershell
songyan run --project-id <project_id> --chapters 1-10 --auto-confirm --resume
```

建议策略：

1. 先跑 Ch1-3，确认 `report` 中成功率和失败原因。
2. 再跑 Ch4-10，不要直接长跑到 100 章。
3. 使用 `--resume` 复用最近未完成 run，避免重复已 accepted 章节。
4. 如果想让单章失败隔离并继续，使用默认 `--on-failure isolate`。
5. 如果希望首个失败立即停下，使用 `--on-failure abort`。

示例：

```powershell
songyan run --project-id <project_id> --chapters 4-10 --auto-confirm --resume --on-failure isolate
songyan report --run-id <run_id>
songyan export --project-id <project_id> --chapters 1-10 --format md --output exports/
```

## 成本、日志和恢复入口

成本预算：

```powershell
$env:SONGYAN_RUN_COST_BUDGET = "10"
songyan run --project-id <project_id> --chapters 1-3 --auto-confirm
```

主要日志位置：

| 路径 | 内容 |
|------|------|
| `logs/chapter_runs/<run_id>.jsonl` | 逐章运行结构化日志 |
| `logs/reports/report-<run_id>.md` | 人类可读运行报告 |
| `logs/app/` | 应用结构化日志 |
| `logs/wrapper/` | Windows timeout wrapper 输出；路径相对执行 wrapper 时的 cwd |
| `exports/` | 导出的 accepted 正文 |
| `backups/` | `songyan backup` 生成的项目资产包 |

常见恢复入口：

| 场景 | 当前动作 | 后续任务 |
|------|----------|----------|
| 缺 API key | 设置 `LLM_API_KEY` 后重新运行 `doctor --init-db`；run preflight 会在进入 pipeline 前阻断 | 212 已完成 |
| Ch1 生成失败 | 若输出了 `run_id`，先运行 `songyan report --run-id <run_id>` 看失败原因 | 212 已完成 |
| 中断或超时 | 使用 `--resume` 继续；长跑用 timeout wrapper | 212 已完成 |
| 无 accepted 可导出 | 先完成至少一章 accepted，再运行 `export` | 212 已完成 |
| 需要分享问题现场 | 当前只能分享 report 和必要日志片段；run bundle 待 Task 213 | 213 |
| 需要备份项目资产 | 使用 `songyan backup --project-id <project_id> --output backups/` | 211 已完成 |
| 需要恢复项目资产 | 使用 `songyan restore --backup <zip> --database-url sqlite:///restored.db` | 211 已完成 |

## 当前限制

- 还没有正式 release checklist 和 wheel smoke。
- run bundle 和脱敏诊断包属于 Task 213。
- profile validate、危险项提示和 rollback/history 属于 Task 214。
- 在 Task 209-215 全部完成前，项目只能标记为 preview 或内部可用，不应标记为正式开源可用版本。
