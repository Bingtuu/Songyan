# Task 211 DONE - V11 backup / restore / schema ledger

> **完成时间**: 2026-08-02
> **结论**: Task 211 已完成。下一步进入 Task 212 失败恢复体验。

---

## 完成内容

### 1. backup 命令

新增：

```powershell
songyan backup --project-id <project_id> --output backups/
```

能力：

- 使用 SQLite backup API 生成一致性 DB 快照。
- 输出 zip 资产包。
- 写入 `manifest.json`、`config/config.summary.json`、`runs/project_runs.json`、`logs/index.json`。
- 默认不包含 `.env` 原文、API key 或日志正文。

### 2. restore 命令

新增：

```powershell
songyan restore --backup <backup.zip> --database-url sqlite:///restored.db
```

能力：

- 从资产包恢复 SQLite DB 到新路径。
- 默认拒绝覆盖已有 DB。
- `--force` 显式允许覆盖。
- restore 前校验 manifest 格式、DB hash 和 schema。
- restore 后输出 `doctor --json`、`list-projects` 下一步命令。

### 3. schema ledger / manifest

资产包 manifest 包含：

- backup 格式版本。
- 创建时间。
- project summary。
- DB 快照大小与 sha256。
- schema status、schema version、missing tables、quick_check。
- resource summary。
- run summary。
- key log index summary。
- sensitive data exclusion statement。

### 4. export / backup 边界

文档已明确：

- `songyan export` 只导出 accepted 正文，不保存可恢复状态。
- `songyan backup` 保存可恢复 / 可迁移项目资产。

---

## 代码与测试

主要改动：

- `src/songyan/services/backup_service.py`
- `src/songyan/cli/main.py`
- `tests/test_211_backup_restore.py`
- `tests/cli/test_backup_restore_commands.py`

命令证据见：

- `docs/reports/211-backup-restore-evidence.md`

验证结果：

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/test_211_backup_restore.py -q` | 4 passed |
| `python -m pytest tests/cli/test_backup_restore_commands.py -q` | 5 passed |
| `python -m pytest tests/cli -q` | 44 passed |
| `python -m pytest tests/test_177_export_service.py tests/test_178_resource_loading.py tests/test_211_backup_restore.py -q` | 25 passed |
| `python -m pytest tests/ -q` | 3067 passed, 2 skipped, 1 xfailed, 7 warnings |
| `ruff check src/ tests/` | pass |

---

## 验收结论

| 验收项 | 结果 |
|--------|------|
| `songyan backup` 生成 zip 资产包 | PASS |
| zip 包含 DB 快照、manifest、配置摘要、运行摘要、日志索引 | PASS |
| manifest 包含 schema ledger / sha256 / project summary | PASS |
| 资产包默认不包含 `.env` 或 API key | PASS |
| `songyan restore` 可恢复到新 DB | PASS |
| restore 后 `doctor --json` schema pass | PASS |
| restore 后 `list-projects` 能看到原项目 | PASS |
| restore 默认拒绝覆盖已有 DB | PASS |
| `--force` 可显式覆盖 | PASS |
| export / backup 边界已文档化 | PASS |
| 不改 prompt / CED / T9 / hard gate | PASS |
| 不实现 Task 212-215 范围 | PASS |

---

## 后续路由

- Task 212：失败恢复体验，标准化常见失败分类、提示和恢复动作。
- Task 213：run bundle 与脱敏诊断包。
- Task 214：profile validate、危险项提示、rollback/history。
- Task 215：release checklist、wheel smoke、Windows 路径与发布前总验收。
