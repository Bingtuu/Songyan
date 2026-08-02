# Task 211 Backup / Restore Evidence

> **任务**: V11 Task 211 backup / restore / schema ledger
> **范围**: backup、restore、schema ledger、项目配置摘要、运行摘要、日志索引、export / backup 边界
> **结论**: `songyan backup` / `songyan restore` 已可执行；资产包包含 SQLite 快照、manifest、schema ledger、配置摘要、运行摘要和日志索引；restore 可恢复到新 DB 并通过 doctor / list-projects 验证。

## 环境

| 项 | 值 |
|----|----|
| 仓库 cwd | `c:/Vibe Project/Songyan` |
| 隔离 cwd | `C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence` |
| source DB | `C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence/source.db` |
| restored DB | `C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence/restored.db` |
| 模板 | `xuanhuan` |
| project_id | `d5d618ee694343d9a62b0dc04ac9ba1c` |
| 真实 LLM 生成 | 未执行；Task 211 只验证资产生命周期，不消耗真实生成预算 |

## 命令证据

### 1. 初始化 source DB

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence/source.db"
$env:LLM_API_KEY = "task211_dummy_key"
$env:CHECKPOINTER_MODE = "memory"
$env:SONGYAN_RUN_COST_BUDGET = "0"
songyan doctor --json --init-db
```

结果：

- exit code: 0
- `status`: `pass`
- summary: 11 pass, 0 warn, 0 fail
- `db.schema`: `pass`
- `resources.package`: `pass`

### 2. 创建模板项目

```powershell
songyan create-project --template xuanhuan
```

结果：

- exit code: 0
- project_id: `d5d618ee694343d9a62b0dc04ac9ba1c`
- 模式: `webnovel_intense`
- 题材: `xuanhuan`
- 标题: `灵渊纪`

### 3. 生成 backup 资产包

```powershell
songyan backup --project-id d5d618ee694343d9a62b0dc04ac9ba1c --output backups
```

结果：

- exit code: 0
- 输出: `backups/songyan-backup-d5d618ee694343d9a62b0dc04ac9ba1c-20260802T053649Z.zip`
- `schema`: `pass`
- `runs`: 0
- 输出明确 `.env/api_key/log_content not included`

### 4. 检查 zip 结构

```powershell
$zip = (Get-ChildItem backups/*.zip | Select-Object -First 1).FullName
[System.IO.Compression.ZipFile]::OpenRead($zip).Entries | Select-Object -ExpandProperty FullName
```

结果：

```text
db/songyan.db
manifest.json
config/config.summary.json
runs/project_runs.json
logs/index.json
```

### 5. restore 到新 DB

```powershell
songyan restore --backup <zip> --database-url sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence/restored.db
```

结果：

- exit code: 0
- restored DB: `C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence/restored.db`
- project_id: `d5d618ee694343d9a62b0dc04ac9ba1c`
- schema: `pass (version=41)`
- 输出下一步命令：`doctor --json`、`list-projects`

### 6. restore 后 doctor

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence/restored.db"
songyan doctor --json
```

结果：

- exit code: 0
- `status`: `warn`
- summary: 10 pass, 1 warn, 0 fail
- `db.schema`: `pass`
- warn 原因：隔离 cwd 中 `.env not found`

### 7. restore 后 list-projects

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence/restored.db"
songyan list-projects
```

结果：

- exit code: 0
- 输出包含 `d5d618ee694343d9a62b0dc04ac9ba1c`
- 标题: `灵渊纪`
- 题材: `xuanhuan`
- 模式: `webnovel_intense`
- 主角: `陆沉`

### 8. restore 覆盖保护

```powershell
songyan restore --backup <zip> --database-url sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence/restored.db
```

结果：

- exit code: 1
- 错误: `target database already exists`
- 结论：默认拒绝覆盖已有 DB。

显式 `--force`：

```powershell
songyan restore --backup <zip> --database-url sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task211-evidence/restored.db --force
```

结果：

- exit code: 0
- schema: `pass`

### 9. manifest 敏感项声明

抽查 `manifest.json`：

```json
{
  "format": "songyan_project_backup",
  "format_version": 1,
  "project_id": "d5d618ee694343d9a62b0dc04ac9ba1c",
  "schema_status": "pass",
  "api_key_included": false,
  "env_file_included": false
}
```

结论：资产包默认不包含 `.env` 原文和 API key。

## 自动化测试证据

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/test_211_backup_restore.py -q` | 4 passed |
| `python -m pytest tests/cli/test_backup_restore_commands.py -q` | 5 passed |
| `python -m pytest tests/cli -q` | 44 passed |
| `python -m pytest tests/test_177_export_service.py tests/test_178_resource_loading.py tests/test_211_backup_restore.py -q` | 25 passed |
| `python -m pytest tests/ -q` | 3067 passed, 2 skipped, 1 xfailed, 7 warnings |
| `ruff check src/ tests/` | pass |

新增测试覆盖：

- 资产包包含 `manifest.json`、DB 快照、config summary、run summary、logs index。
- 资产包默认不包含 `.env` / API key / log content。
- restore 到新 DB 后可查询原 project。
- restore 默认拒绝覆盖已有 DB。
- `--force` 可显式覆盖。
- 坏 zip 文件返回可读错误。
- 缺 project_id 时 backup 失败。

## export 与 backup 边界

- `songyan export`：只导出 accepted 正文，面向书稿交付，不保存可续跑状态。
- `songyan backup`：保存可恢复 / 可迁移的项目资产，包含 SQLite 事实库快照、schema ledger、项目摘要、运行摘要和日志索引。

## 后续路由

| 缺口 | 路由 |
|------|------|
| 失败恢复分类、retry/resume/isolate 体验完善 | Task 212 |
| run bundle、脱敏诊断包 | Task 213 |
| profile validate、危险项提示、rollback/history | Task 214 |
| wheel smoke、release checklist、CONTRIBUTING、issue templates | Task 215 |

## 守护确认

Task 211 未修改 prompt card、Writer / CreativeDirector / Auditor 生成逻辑、CED、T9、five-gate、segment audit 或质量 hard gate。
