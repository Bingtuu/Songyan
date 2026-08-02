# Songyan Troubleshooting

> 当前文档是 V11 preview 阶段的故障入口。它记录现有可操作步骤，也明确哪些问题仍要进入 Task 210-215 修复。

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

| 现象 | 当前判断 | 先做什么 | 后续任务 |
|------|----------|----------|----------|
| `LLM API key is not configured` | 没有配置 `LLM_API_KEY` | 编辑 `.env` 或设置环境变量，再运行 `songyan doctor --init-db` | 210 |
| `database does not exist` | DB 尚未初始化 | 运行 `songyan doctor --init-db` | 210 |
| `Unsupported database_url` | 当前只支持 `sqlite:///...` | 修改 `DATABASE_URL=sqlite:///songyan.db` | 210 |
| 非法 `CHECKPOINTER_MODE` traceback | 当前配置加载阶段尚未被 doctor 捕获 | 改为 `sqlite` 或 `memory` | 210 |
| `songyan run` 输出失败但进程 exit code 为 0 | 已知 runtime 语义缺口 | 以 `run_id` 生成 report，按失败原因处理 | 210/212 |
| `report` 提示没有 JSONL | run log 不存在或 run_id 错误 | 检查 `logs/chapter_runs/` 和 run 输出 | 213 |
| `export` 提示没有 accepted 章节 | 项目还没有通过接收门槛的正文 | 先完成至少一章 accepted | 209 |
| 单章失败 | 可能是 LLM、成本、上下文、质量门或 settlement 问题 | `songyan report --run-id <run_id>` | 212 |
| 长跑卡住 | Windows 文件锁、网络或模型响应问题 | 用 timeout wrapper 包裹命令 | 212 |
| 需要迁移项目资产 | 当前无 backup/restore 命令 | 手动保护 DB、`.env`、关键 logs | 211 |
| 需要提交可复现问题 | 当前无 run bundle | 先提供 report、run_id、命令、必要日志片段，注意脱敏 | 213 |

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

如果 `songyan run` 输出了 `run_id`，先生成报告：

```powershell
songyan report --run-id <run_id>
```

再检查：

- 报告里的失败章节。
- 失败原因是否指向缺 key、endpoint、成本、上下文、质量门或 settlement。
- `logs/chapter_runs/<run_id>.jsonl` 是否存在。
- `logs/app/` 中是否有同一时间段的错误。

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

当前没有自动脱敏 run bundle。手动提交问题时建议提供：

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

自动 run bundle、脱敏规则和 issue 模板会在 Task 213/215 收口。
