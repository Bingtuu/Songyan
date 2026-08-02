# Task 213 Run Bundle Evidence

> **任务**: V11 Task 213 run bundle 诊断包
> **范围**: `songyan bundle-run`、JSON + Markdown bundle、日志索引、脱敏
> **结论**: run bundle 已可由一条 CLI 命令生成，缺 run log 时输出 Task 212 恢复建议，成功路径默认不包含 `.env`、API key、日志正文或书稿正文。

## Bundle 格式

```text
songyan-run-bundle-<run_id>-<timestamp>.zip
├── bundle.json
├── bundle.md
└── logs/index.json
```

`bundle.json` 包含：

- `run`
- `project`
- `chapters`
- `cost`
- `quality_signals`
- `artifacts`
- `logs`
- `redaction`
- `warnings`

## 命令证据

### 1. 缺 run log

```powershell
songyan bundle-run --run-id missing-run --output bundles
```

结果：

- exit code: 1
- 输出 `run log not found: logs/chapter_runs/missing-run.jsonl`
- 输出 `[missing_artifact]`
- 输出恢复命令：`Get-ChildItem logs/chapter_runs`、`songyan report --run-id missing-run`

### 2. 成功生成 bundle

证据环境：

- 临时 cwd：`C:\Users\Admin\AppData\Local\Temp\songyan-task213-evidence`
- `DATABASE_URL=sqlite:///C:/Users/Admin/AppData/Local/Temp/songyan-task213-evidence/bundle.db`
- `CHECKPOINTER_MODE=memory`
- run log：`logs/chapter_runs/run-task213.jsonl`

命令：

```powershell
songyan bundle-run --run-id run-task213 --output bundles
```

结果：

- exit code: 0
- 输出 `诊断包已生成`
- 输出 `files: bundle.json, bundle.md, logs/index.json`
- 生成 `bundles/songyan-run-bundle-run-task213-20260802T122703Z.zip`

### 3. 包结构和脱敏检查

命令：

```powershell
Expand-Archive -Path bundles/songyan-run-bundle-run-task213-20260802T122703Z.zip -DestinationPath inspect
Get-ChildItem -Recurse inspect
Select-String -Path "inspect\*" -Pattern 'task213_dummy_key','C:\\secret','C:/secret' -SimpleMatch
```

结果：

- zip 内包含：
  - `bundle.json`
  - `bundle.md`
  - `logs/index.json`
- 搜索敏感串结果：`NO_SECRET_HITS`
- 未包含 `.env`、API key、日志正文或书稿正文。

## 自动化测试证据

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/test_213_run_bundle.py tests/cli/test_run_bundle_commands.py -q` | 6 passed |
| `python -m pytest tests/cli -q` | 48 passed |
| `python -m pytest tests/test_119_reporting_wrapper.py tests/test_175_cost_tracking.py tests/test_211_backup_restore.py tests/test_213_run_bundle.py -q` | 71 passed |
| `python -m pytest tests/ -q` | 3070 passed, 2 skipped, 1 xfailed, 7 warnings |
| `ruff check src/ tests/` | pass |

测试覆盖：

- bundle zip 包含 `bundle.json`、`bundle.md`、`logs/index.json`。
- bundle 包含 run、project、章节状态、成本、quality signals 和日志索引。
- 缺 run log 时抛出可恢复错误。
- `--project-id` 与 run log 不一致时失败。
- 脱敏测试证明 API key / secret / 绝对路径不进入 bundle。
- CLI `bundle-run --help`、成功路径、缺 run log 恢复建议。

## 边界确认

| 能力 | 结论 |
|------|------|
| report | bundle 引用 report 路径，不替代 report 生成逻辑 |
| backup | bundle 不保存可恢复 DB，不替代 backup |
| export | bundle 不导出正文，不替代 export |
| run bundle | 仅诊断包，不改变生成、修订、accept 或质量门 |

## 后续路由

| 缺口 | 路由 |
|------|------|
| profile validate、危险项提示、rollback/history | Task 214 |
| wheel smoke、release checklist、CONTRIBUTING、issue templates | Task 215 |

## 守护确认

Task 213 未修改 prompt card、Writer / CreativeDirector / Auditor 生成逻辑、CED、T9、five-gate、segment audit 或质量 hard gate。
