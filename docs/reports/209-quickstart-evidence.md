# Task 209 Quickstart Evidence

> **任务**: V11 Task 209 Quickstart 与用户文档闭环
> **范围**: help、doctor、init-db、create-project、run failure、report、export
> **结论**: Quickstart 文档链路已绑定命令证据；真实 LLM Ch1-3 成功验收仍路由至 Task 210/215。

## 环境

| 项 | 值 |
|----|----|
| 仓库 cwd | `c:/Vibe Project/Songyan` |
| 隔离 cwd | `%TEMP%/songyan-task209-quickstart` |
| 隔离 DB | `%TEMP%/songyan-task209-quickstart/quickstart.db` |
| 项目模板 | `xuanhuan` |
| project_id | `44e8054f0cef46b096b10bab858da2c9` |
| run_id | `run-0781e756` |
| 真实 LLM Ch1-3 | 未执行；Task 209 不消耗真实 API 预算，后续由 Task 210/215 做 release smoke |

## 命令证据

### 1. CLI help

```powershell
songyan --help
```

结果：

- exit code: 0
- 输出包含 `doctor`、`create-project`、`run`、`report`、`export`、`profile`、`metrics`、`index`、`mark`。

### 2. doctor 缺 key

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task209-quickstart/no-key.db"
$env:LLM_API_KEY = ""
$env:CHECKPOINTER_MODE = "memory"
songyan doctor --json
```

结果：

- exit code: 1
- `status`: `fail`
- `llm.key`: `fail`
- `resources.package`: `pass`
- 结论：缺 key 能结构化诊断并给出设置 `LLM_API_KEY` 的 hint。

### 3. doctor 初始化 DB

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task209-quickstart/quickstart.db"
$env:LLM_API_KEY = "task209_dummy_key"
$env:CHECKPOINTER_MODE = "memory"
songyan doctor --json --init-db
```

结果：

- exit code: 0
- `status`: `warn`
- `summary`: 7 pass, 1 warn, 0 fail
- `db.schema`: `pass`
- `resources.package`: `pass`
- warn 原因：隔离 cwd 中 `.env not found`。

### 4. 创建模板项目

```powershell
songyan create-project --template xuanhuan
```

结果：

- exit code: 0
- project_id: `44e8054f0cef46b096b10bab858da2c9`
- 模式: `webnovel_intense`
- 题材: `xuanhuan`
- 标题: `灵渊纪`
- 结论：非仓库 cwd 下模板建项可用。

### 5. Ch1-3 失败路径

```powershell
$env:LLM_API_KEY = ""
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 90 -- songyan run --project-id 44e8054f0cef46b096b10bab858da2c9 --chapters 1-3 --auto-confirm --skip-rag --gate-mode observe --on-failure abort
```

结果：

- wrapper: `WRAPPER_RESULT=PASS_NORMAL_EXIT`
- exit code: 0
- run_id: `run-0781e756`
- 成功章节: 0
- 失败章节: `[1]`
- 失败原因: `GoalPlanner LLM call failed: LLM API Key 未配置`
- 结论：失败被记录且可生成 report，但业务失败 exit code 仍为 0，必须路由到 Task 210/212。

### 6. 生成 report

```powershell
songyan report --run-id run-0781e756
```

结果：

- exit code: 0
- 输出: `logs/reports/report-run-0781e756.md`
- 报告显示 Ch1 失败、达标率 0.0%、失败原因包含缺 key。
- 结论：Markdown report 可解释失败；JSON + Markdown bundle 和脱敏日志索引仍是 Task 213。

### 7. export 无 accepted 章节

```powershell
songyan export --project-id 44e8054f0cef46b096b10bab858da2c9 --format md --output exports
```

结果：

- exit code: 1
- 错误: `项目 44e8054f0cef46b096b10bab858da2c9 没有可导出的 accepted 章节`
- 结论：错误清楚，Quickstart 必须说明只有 accepted 章节可导出。

### 8. list-projects

```powershell
songyan list-projects
```

结果：

- exit code: 0
- 输出包含 `44e8054f0cef46b096b10bab858da2c9`、`xuanhuan`、`webnovel_intense`、主角 `陆沉`。
- 结论：用户忘记 project_id 时可用该命令找回。

## 未执行项

| 项 | 原因 | 路由 |
|----|------|------|
| 真实 LLM Ch1-3 成功运行 | Task 209 是文档任务，不消耗真实 API 预算；当前只记录命令和失败路径 | Task 210/215 |
| wheel 安装后非仓库 cwd smoke | 当前仍是开发安装路径 | Task 215 |
| run bundle 脱敏输出 | 命令尚不存在 | Task 213 |
| backup/restore | 命令尚不存在 | Task 211 |
| profile validate/rollback | 命令尚不存在 | Task 214 |

## 收尾验证

| 命令 | 结果 |
|------|------|
| `git diff --check -- README.md docs/STATUS.md docs/INDEX.md tasks/V11-README.md` | pass，仅 Windows CRLF 提示 |
| `Select-String ... -Pattern '\s+$'` | 新增文档无行尾空白 |
| `python -m pytest tests/cli -q` | 35 passed |
| `python -m pytest tests/test_177_export_service.py tests/test_178_resource_loading.py tests/test_183_profile_cli.py tests/test_119_reporting_wrapper.py -q` | 40 passed |
| `ruff check src/ tests/` | pass |

## 文档映射

| 文档 | 绑定证据 |
|------|----------|
| `README.md` | 最短路径改为 `doctor --init-db -> create-project -> run Ch1-3 -> report -> export` |
| `docs/quickstart.md` | 详细 Quickstart、10 章教程、成本、日志、wrapper、限制 |
| `docs/troubleshooting.md` | 缺 key、DB、run 失败、report、export、Windows wrapper、脱敏分享 |
| `tasks/209-v11-quickstart-docs-DONE.md` | 本任务完成结论和后续路由 |

## 守护确认

Task 209 未修改 `src/`、prompt card、CED、T9、five-gate、segment audit 或 hard gate。
