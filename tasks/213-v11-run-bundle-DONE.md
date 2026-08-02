# Task 213 DONE - V11 run bundle 诊断包

> **完成时间**: 2026-08-02
> **结论**: Task 213 已完成。下一步进入 Task 214 配置安全与 profile validate。

---

## 完成内容

### 1. CLI 命令

新增：

```powershell
songyan bundle-run --run-id <run_id> --output bundles/
```

可选：

```powershell
songyan bundle-run --run-id <run_id> --project-id <project_id> --output bundles/
```

### 2. Bundle 产物

zip 结构：

```text
songyan-run-bundle-<run_id>-<timestamp>.zip
├── bundle.json
├── bundle.md
└── logs/index.json
```

### 3. 内容覆盖

`bundle.json` 包含：

- run 元信息。
- project 摘要。
- 章节状态和失败分类。
- 成本聚合。
- report / run log 路径索引。
- quality gate / candidate gate / context emergency / health / overdue / run quality debt 摘要。
- CED / T9 / five-gate 的外部信号说明。
- 脱敏声明和 warnings。

### 4. 脱敏与边界

默认不包含：

- `.env` 原文。
- API key / token / authorization header。
- 敏感 env。
- 绝对路径。
- 日志正文。
- 书稿正文。

bundle 只做诊断与复现辅助，不替代：

- `report`
- `backup`
- `export`

---

## 代码与测试

主要改动：

- `src/songyan/services/run_bundle_service.py`
- `src/songyan/cli/main.py`
- `tests/test_213_run_bundle.py`
- `tests/cli/test_run_bundle_commands.py`

命令证据见：

- `docs/reports/213-run-bundle-evidence.md`

验证结果：

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/test_213_run_bundle.py tests/cli/test_run_bundle_commands.py -q` | 6 passed |
| `python -m pytest tests/cli -q` | 48 passed |
| `python -m pytest tests/test_119_reporting_wrapper.py tests/test_175_cost_tracking.py tests/test_211_backup_restore.py tests/test_213_run_bundle.py -q` | 71 passed |
| `python -m pytest tests/ -q` | 3070 passed, 2 skipped, 1 xfailed, 7 warnings |
| `ruff check src/ tests/` | pass |

---

## 验收结论

| 验收项 | 结果 |
|--------|------|
| 一条命令生成 JSON + Markdown bundle | PASS |
| bundle 包含 run 元信息、章节状态、成本、日志索引和失败分类 | PASS |
| 缺 run log 时 exit 1 并提示 Task 212 恢复路径 | PASS |
| 脱敏测试覆盖 API key、敏感串、绝对路径 | PASS |
| 不包含 `.env`、日志正文或书稿正文 | PASS |
| 不改变 report / backup / export 边界 | PASS |
| 不实现 profile validate / release checklist | PASS |
| 不改 prompt / CED / T9 / hard gate | PASS |

---

## 后续路由

- Task 214：配置安全与 profile validate，覆盖推荐范围、危险项提示、rollback/history 或等价机制。
- Task 215：release checklist、wheel smoke、Windows 路径与发布前总验收。
