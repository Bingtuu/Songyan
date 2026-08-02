# Task 212 Failure Recovery Evidence

> **任务**: V11 Task 212 失败恢复体验
> **范围**: doctor、run preflight、run failed、report、export、backup、restore
> **结论**: 常见失败已按分类输出恢复建议；至少 5 类失败有 CLI 输出或测试证据；`report` 缺 run log 不再安静成功。

## 失败分类

| 分类 | 覆盖场景 |
|------|----------|
| `config_error` | 缺 LLM key、非法配置 |
| `database_error` | DB/schema 问题 |
| `preflight_failed` | `songyan run` 进入 pipeline 前失败 |
| `run_failed` | pipeline 已启动后章节失败 |
| `missing_artifact` | report 缺 JSONL / run_id 错误 |
| `no_accepted_content` | export 没有 accepted 章节 |
| `asset_restore_error` | backup/restore 资产问题 |

## 命令证据

### 1. doctor 缺 key

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task212-evidence/recovery.db"
$env:CHECKPOINTER_MODE = "memory"
$env:SONGYAN_RUN_COST_BUDGET = "0"
$env:LLM_API_KEY = ""
songyan doctor
```

结果：

- exit code: 1
- `llm.key`: fail
- 输出 `[config_error]`
- 输出恢复命令：`Copy-Item .env.example .env`、`songyan doctor --json --init-db`

### 2. run preflight 缺 key

```powershell
songyan run --project-id 4409f34196e34960b40916dc2dd96884 --chapters 1-1 --auto-confirm --skip-rag --gate-mode observe
```

结果：

- exit code: 1
- 输出 `Songyan run preflight`
- 输出 `[preflight_failed]`
- 输出 `[config_error]`
- 输出恢复命令：`songyan doctor --json --init-db`、`songyan list-projects`
- 未进入 pipeline，未输出 `run_id`

### 3. report 缺 run log

```powershell
songyan report --run-id missing-run
```

结果：

- exit code: 1
- 输出 `错误: 未找到运行日志 logs/chapter_runs/missing-run.jsonl`
- 输出 `[missing_artifact]`
- 输出恢复命令：`Get-ChildItem logs/chapter_runs`、`songyan report --run-id missing-run`

### 4. export 无 accepted 章节

```powershell
songyan export --project-id 4409f34196e34960b40916dc2dd96884 --chapters 1-3 --format md --output exports
```

结果：

- exit code: 1
- 输出 `没有可导出的 accepted 章节`
- 输出 `[no_accepted_content]`
- 输出恢复命令：`songyan run --project-id ... --chapters 1-3 --auto-confirm`

### 5. backup 缺 project

```powershell
songyan backup --project-id missing --output backups
```

结果：

- exit code: 1
- 输出 `project not found`
- 输出 `[asset_restore_error]`
- 输出恢复命令：`songyan list-projects`

### 6. restore 坏 zip

```powershell
Set-Content -Path bad.zip -Value 'not a zip'
songyan restore --backup bad.zip --database-url sqlite:///restored.db
```

结果：

- exit code: 1
- 输出 `backup package is not a valid zip file`
- 输出 `[asset_restore_error]`
- 输出恢复命令：`songyan backup --project-id <project_id> --output backups/`

## 自动化测试证据

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/cli/test_failure_recovery_commands.py tests/cli/test_doctor_command.py tests/cli/test_cli.py tests/cli/test_backup_restore_commands.py -q` | 35 passed |
| `python -m pytest tests/test_119_reporting_wrapper.py tests/test_177_export_service.py tests/test_211_backup_restore.py -q` | 31 passed |
| `python -m pytest tests/cli -q` | 45 passed |
| `python -m pytest tests/ -q` | 3067 passed, 2 skipped, 1 xfailed, 7 warnings |
| `ruff check src/ tests/` | pass |

新增测试覆盖：

- `doctor` 缺 key 输出 `[config_error]`。
- `run` preflight fail 输出 `[preflight_failed]` 与 `[config_error]`。
- pipeline mock 返回 `partial` 时输出 `[run_failed]` 和 `songyan report --run-id <run_id>`。
- `report` 缺 JSONL 时 exit 1 并输出 `[missing_artifact]`。
- `export` 无 accepted 章节输出 `[no_accepted_content]`。
- `backup` missing project 输出 `[asset_restore_error]`。
- `restore` 已存在 DB / 坏 zip 输出 `[asset_restore_error]`。

## 后续路由

| 缺口 | 路由 |
|------|------|
| run bundle、脱敏诊断包 | Task 213 |
| profile validate、危险项提示、rollback/history | Task 214 |
| wheel smoke、release checklist、CONTRIBUTING、issue templates | Task 215 |

## 守护确认

Task 212 未修改 prompt card、Writer / CreativeDirector / Auditor 生成逻辑、CED、T9、five-gate、segment audit 或质量 hard gate。
