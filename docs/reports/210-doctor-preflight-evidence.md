# Task 210 Doctor / Preflight Evidence

> **任务**: V11 Task 210 doctor / preflight 增强
> **范围**: config load、doctor JSON、DB/schema、resources、logs、budget、run preflight、run exit code
> **结论**: 非法配置不再导致 CLI 导入期 traceback；doctor / run preflight 能结构化报告环境问题；`songyan run` 在 preflight 或业务失败时返回非 0 exit code。

## 环境

| 项 | 值 |
|----|----|
| 仓库 cwd | `c:/Vibe Project/Songyan` |
| 隔离 cwd | `C:/Users/Admin/AppData/Local/Temp/songyan-task210-evidence` |
| 隔离 DB | `C:/Users/Admin/AppData/Local/Temp/songyan-task210-evidence/preflight.db` |
| 模板 | `xuanhuan` |
| project_id | `cbcaf8a7673b40bdb1aec215461be215` |
| 真实 LLM 生成 | 未执行；Task 210 只验证 preflight 和失败语义，不消耗真实生成预算 |

## 命令证据

### 1. 非法 CHECKPOINTER_MODE

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task210-evidence/invalid-checkpointer.db"
$env:LLM_API_KEY = "task210_dummy_key"
$env:CHECKPOINTER_MODE = "invalid"
$env:SONGYAN_RUN_COST_BUDGET = "0"
songyan doctor --json
```

结果：

- exit code: 1
- `status`: `fail`
- `config.load`: `pass`
- `runtime.checkpointer`: `fail`
- `db.url`: 使用调用方提供的隔离 DB URL
- stdout / stderr 未出现 `Traceback`

结论：非法 `CHECKPOINTER_MODE` 不再阻断 CLI 导入，转为结构化诊断。

### 2. 非法成本预算

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task210-evidence/invalid-budget.db"
$env:LLM_API_KEY = "task210_dummy_key"
$env:CHECKPOINTER_MODE = "memory"
$env:SONGYAN_RUN_COST_BUDGET = "not-a-number"
songyan doctor --json
```

结果：

- exit code: 1
- `status`: `fail`
- `runtime.budget`: `fail`
- `db.url`: 使用调用方提供的隔离 DB URL
- stdout / stderr 未出现 `Traceback`

结论：非法预算值由 `doctor` 报告，不再造成导入期异常。

### 3. 隔离目录 doctor 初始化 DB

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task210-evidence/preflight.db"
$env:LLM_API_KEY = "task210_dummy_key"
$env:CHECKPOINTER_MODE = "memory"
$env:SONGYAN_RUN_COST_BUDGET = "0"
songyan doctor --json --init-db
```

结果：

- exit code: 0
- `status`: `warn`
- summary: 10 pass, 1 warn, 0 fail
- `config.load`: `pass`
- `db.schema`: `pass`
- `logs.path`: `pass`
- `runtime.budget`: `pass`
- warn 原因：隔离 cwd 中 `.env not found`

结论：doctor 覆盖配置加载、DB/schema、日志路径、预算和资源包检查。

### 4. 创建模板项目

```powershell
songyan create-project --template xuanhuan
```

结果：

- exit code: 0
- project_id: `cbcaf8a7673b40bdb1aec215461be215`
- 模式: `webnovel_intense`
- 题材: `xuanhuan`
- 标题: `灵渊纪`

### 5. run 缺 key preflight

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task210-evidence/preflight.db"
$env:LLM_API_KEY = ""
$env:CHECKPOINTER_MODE = "memory"
$env:SONGYAN_RUN_COST_BUDGET = "0"
songyan run --project-id cbcaf8a7673b40bdb1aec215461be215 --chapters 1-1 --auto-confirm --skip-rag --gate-mode observe --on-failure abort
```

结果：

- exit code: 1
- 输出 `Songyan run preflight`
- `llm.key`: `fail`
- 未输出 `run_id`
- 未进入生成 pipeline

结论：缺 key 在 run 前被阻断，避免“业务失败但进程 exit 0”的误导路径。

## 自动化测试证据

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/cli -q` | 39 passed |
| `python -m pytest tests/test_119_reporting_wrapper.py tests/test_175_cost_tracking.py tests/test_phase2_graph.py -q` | 80 passed, 2 warnings |
| `python -m pytest tests/ -q` | 3063 passed, 2 skipped, 1 xfailed, 7 warnings |
| `ruff check src/ tests/` | pass |

新增测试覆盖：

- 子进程环境下非法 `CHECKPOINTER_MODE` 不 traceback，`doctor --json` 返回结构化 fail。
- 非法 `SONGYAN_RUN_COST_BUDGET` 返回 `runtime.budget` fail。
- `songyan run` preflight fail 时不解析 mode、不进入 pipeline。
- pipeline mock 返回 `partial` 时 CLI 保留 `run_id`，exit code 为 1。
- pipeline mock 返回 `completed` 时 CLI 保持 exit code 0。

## 后续路由

| 缺口 | 路由 |
|------|------|
| backup/restore | Task 211 |
| 失败恢复分类、retry/resume/isolate 体验完善 | Task 212 |
| run bundle、脱敏诊断包 | Task 213 |
| profile validate、危险项提示、rollback/history | Task 214 |
| wheel smoke、release checklist、CONTRIBUTING、issue templates | Task 215 |

## 守护确认

Task 210 未修改 prompt card、Writer / CreativeDirector / Auditor 生成逻辑、CED、T9、five-gate、segment audit 或质量 hard gate。
