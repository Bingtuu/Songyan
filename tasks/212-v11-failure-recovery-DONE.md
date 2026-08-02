# Task 212 DONE - V11 失败恢复体验

> **完成时间**: 2026-08-02
> **结论**: Task 212 已完成。下一步进入 Task 213 run bundle 诊断包。

---

## 完成内容

### 1. 失败分类

新增统一恢复建议分类：

- `config_error`
- `database_error`
- `preflight_failed`
- `run_failed`
- `missing_artifact`
- `no_accepted_content`
- `asset_restore_error`

### 2. CLI 恢复建议

已接入：

- `songyan doctor` human 输出：配置失败时显示恢复建议。
- `songyan run` preflight fail：显示 preflight + 具体失败恢复建议。
- `songyan run` pipeline partial/failed：保留 `run_id`，提示 `songyan report --run-id <run_id>`。
- `songyan report` 缺 JSONL：exit 1，提示检查 `logs/chapter_runs` 和 run_id。
- `songyan export` 无 accepted：提示先生成 accepted 章节。
- `songyan backup` project 缺失：提示 `songyan list-projects`。
- `songyan restore` 坏 zip / 已存在 DB：提示重建 backup 或显式 `--force`。

### 3. 文档恢复手册

`docs/troubleshooting.md` 已按失败分类补齐：

- 配置失败。
- DB/schema 失败。
- run preflight 失败。
- run 已启动后失败。
- report 缺 artifact。
- export 无 accepted。
- backup/restore 资产问题。

---

## 代码与测试

主要改动：

- `src/songyan/services/recovery_service.py`
- `src/songyan/cli/main.py`
- `tests/cli/test_failure_recovery_commands.py`
- `tests/cli/test_doctor_command.py`
- `tests/cli/test_cli.py`
- `tests/cli/test_backup_restore_commands.py`
- `tests/test_119_reporting_wrapper.py`

命令证据见：

- `docs/reports/212-failure-recovery-evidence.md`

验证结果：

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/cli/test_failure_recovery_commands.py tests/cli/test_doctor_command.py tests/cli/test_cli.py tests/cli/test_backup_restore_commands.py -q` | 35 passed |
| `python -m pytest tests/test_119_reporting_wrapper.py tests/test_177_export_service.py tests/test_211_backup_restore.py -q` | 31 passed |
| `python -m pytest tests/cli -q` | 45 passed |
| `python -m pytest tests/ -q` | 3067 passed, 2 skipped, 1 xfailed, 7 warnings |
| `ruff check src/ tests/` | pass |

---

## 验收结论

| 验收项 | 结果 |
|--------|------|
| 至少 5 类失败有恢复提示 | PASS |
| 缺 key / config 问题有恢复命令 | PASS |
| DB/schema 问题有恢复命令 | PASS |
| run preflight fail 有恢复建议 | PASS |
| run pipeline failure 保留 run_id 并提示 report | PASS |
| report 缺 run log exit 1 并提示路径 | PASS |
| export 无 accepted 有恢复建议 | PASS |
| backup/restore 资产问题有恢复建议 | PASS |
| 不实现 run bundle / profile validate / release checklist | PASS |
| 不改 prompt / CED / T9 / hard gate | PASS |

---

## 后续路由

- Task 213：run bundle 与脱敏诊断包。
- Task 214：profile validate、危险项提示、rollback/history。
- Task 215：release checklist、wheel smoke、Windows 路径与发布前总验收。
