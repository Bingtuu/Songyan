# Songyan Troubleshooting

> 当前文档是 V11 preview 阶段的故障入口。它记录现有可操作步骤，也明确哪些问题仍要进入 Task 214-215 修复。

## 先跑 doctor

遇到安装、配置、DB 或资源问题时，先运行：

```powershell
songyan doctor --json --init-db
```

如果不想初始化或迁移 DB：

```powershell
songyan doctor --json
```

需要检查 LLM client 初始化时：

```powershell
songyan doctor --json --check-llm
```

`--check-llm` 当前只做显式 client 初始化探针，不默认发起生成请求。

## 常见问题路由

| 分类 | 现象 | 先做什么 | 状态 |
|------|------|----------|------|
| `config_error` | 缺 `LLM_API_KEY`、非法 `CHECKPOINTER_MODE`、非法预算或 LLM 配置 | 修正 `.env` / 环境变量，再运行 `songyan doctor --json --init-db` | 212 已完成 |
| `database_error` | DB 不存在、schema 缺失、非法 `DATABASE_URL` | 设置 `DATABASE_URL=sqlite:///songyan.db`，运行 `songyan doctor --json --init-db` | 212 已完成 |
| `preflight_failed` | `songyan run` 输出 `Songyan run preflight` | 按 FAIL 项修正配置、DB、资源或 project_id | 212 已完成 |
| `run_failed` | `songyan run` 输出 `run_id` 后 exit code 非 0 | 运行 `songyan report --run-id <run_id>` | 212 已完成 |
| `missing_artifact` | `report` 找不到 JSONL / run log | 检查 `logs/chapter_runs/` 和 run 输出中的 run_id | 212 已完成 |
| `no_accepted_content` | `export` 提示没有 accepted 章节 | 先生成并 accepted 至少一章，再运行 `export` | 212 已完成 |
| `asset_restore_error` | backup project 不存在、restore 坏包、restore 目标 DB 已存在 | `songyan list-projects`、重新 backup，或确认后用 `restore --force` | 212 已完成 |
| 提交可复现问题 | 使用自动脱敏 run bundle | `songyan bundle-run --run-id <run_id> --output bundles/` | 213 已完成 |

CLI 的 human 输出会在常见失败后追加 `恢复建议:` 段，包含上述分类和可执行命令。`--json` 输出保持机器可读，恢复说明看对应 check 的 `hint` 和本文档。

## 缺 key 的最小验证

```powershell
$env:LLM_API_KEY = ""
songyan doctor --json
```

期望结果：

- `status` 为 `fail`。
- `llm.key` 为 `fail`。
- 输出包含设置 `LLM_API_KEY` 的 hint。

## DB 初始化验证

```powershell
$env:DATABASE_URL = "sqlite:///songyan.db"
songyan doctor --json --init-db
```

期望结果：

- `db.url` 为 `pass`。
- `db.path` 为 `pass`。
- `db.schema` 为 `pass` 或可解释的 `warn`。

## 运行失败后的最短处理

`songyan run` 会先执行 preflight。若输出 `Songyan run preflight`，说明 pipeline 尚未启动，请先修正配置、DB/schema、预算、资源或 project_id。

如果 `songyan run` 输出了 `run_id`，说明 pipeline 已启动；即使命令 exit code 非 0，也可以先生成报告：

```powershell
songyan report --run-id <run_id>
```

再检查：

- 报告里的失败章节。
- 失败原因是否指向缺 key、endpoint、成本、上下文、质量门或 settlement。
- `logs/chapter_runs/<run_id>.jsonl` 是否存在。
- `logs/app/` 中是否有同一时间段的错误。

若 `songyan report --run-id <run_id>` 输出 `missing_artifact`，说明 run log 不存在或 run_id 写错。先运行：

```powershell
Get-ChildItem logs/chapter_runs
```

再用实际存在的 `<run_id>.jsonl` 文件名重试。

如果是中断或超时，尝试：

```powershell
songyan run --project-id <project_id> --chapters 1-3 --auto-confirm --resume
```

如果希望失败章隔离并继续：

```powershell
songyan run --project-id <project_id> --chapters 1-10 --auto-confirm --on-failure isolate
```

如果希望首个失败立即停下：

```powershell
songyan run --project-id <project_id> --chapters 1-10 --auto-confirm --on-failure abort
```

## 备份与恢复

需要保护或迁移项目资产时：

```powershell
songyan backup --project-id <project_id> --output backups/
```

该命令生成 zip 资产包，包含 SQLite 快照、schema ledger、项目配置摘要、运行摘要和关键日志索引。默认不包含 `.env` 原文、API key 或日志正文。

恢复到新 DB 路径：

```powershell
songyan restore --backup backups/songyan-backup-<project_id>-<timestamp>.zip --database-url sqlite:///restored.db
$env:DATABASE_URL = "sqlite:///restored.db"
songyan doctor --json
songyan list-projects
```

restore 默认拒绝覆盖已有 DB；确实要覆盖时加 `--force`。

`songyan export` 只导出 accepted 正文，不保存可续跑状态；不要把 export 当作项目备份。

## Windows timeout wrapper

长跑或测试卡住时，可以用仓库脚本包一层硬超时。该 wrapper 目前不是已安装的 `songyan` 子命令；如果当前目录不是仓库根目录，请用仓库绝对路径调用。

```powershell
# 在仓库根目录下
powershell -File .\scripts\run_with_timeout.ps1 -TimeoutSec 3600 -- songyan run --project-id <project_id> --chapters 1-3 --auto-confirm

# 在任意 cwd 下
$songyanRepo = "C:\path\to\Songyan"
powershell -File "$songyanRepo\scripts\run_with_timeout.ps1" -TimeoutSec 3600 -- songyan run --project-id <project_id> --chapters 1-3 --auto-confirm
```

wrapper 输出会写入执行 wrapper 时 cwd 下的：

```text
logs/wrapper/
```

## 分享问题时需要的信息

需要提交可复现问题时，优先生成自动脱敏 run bundle：

```powershell
songyan bundle-run --run-id <run_id> --output bundles/
```

bundle zip 包含 `bundle.json`、`bundle.md` 和 `logs/index.json`。默认不包含 `.env`、API key、日志正文或书稿正文。

手动补充问题时建议提供：

- 使用的命令。
- `project_id` 和 `run_id`。
- `songyan doctor --json` 的输出，移除 API key 或敏感路径。
- `logs/reports/report-<run_id>.md`。
- 必要的 `logs/chapter_runs/<run_id>.jsonl` 片段。
- Python 版本、OS、Songyan commit 或版本。

不要提交：

- `.env`。
- API key。
- 完整私密书稿。
- 未脱敏的绝对路径或私密本地目录。

Issue 模板会在 Task 215 收口。
