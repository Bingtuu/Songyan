# Task 210 DONE - V11 doctor / preflight 增强

> **完成时间**: 2026-08-02
> **结论**: Task 210 已完成。下一步进入 Task 211 backup / restore / schema ledger。

---

## 完成内容

### 1. 配置加载收口

- `src/songyan/config.py` 增加安全加载路径，避免模块级 `settings` 在不可预期配置错误下直接阻断 CLI 导入。
- `CHECKPOINTER_MODE` 改为由 doctor/preflight 做运行时枚举诊断，非法值不再触发导入期 traceback。
- `SONGYAN_RUN_COST_BUDGET` / `RUN_COST_BUDGET` 非法值不再触发导入期 traceback，由 `runtime.budget` 报告。

### 2. doctor 增强

`songyan doctor` 新增或强化检查：

- `config.load`：配置加载状态。
- `logs.path`：当前 cwd 下日志目录是否存在、可写或可创建。
- `runtime.budget`：单 run 成本预算是否为非负数字。
- `runtime.checkpointer`：`sqlite` / `memory` 枚举检查和 hint。
- DB/schema 检查保留 `--init-db` 初始化和 schema drift 诊断。

### 3. run preflight

- `songyan run` 在进入 `run_project_pipeline` 前执行 strict preflight。
- preflight 覆盖 LLM key/config、DB/schema、runtime checkpointer、日志路径、成本预算、资源包和项目存在性。
- preflight fail 时输出 `Songyan run preflight`，exit code 1，不进入 pipeline。

### 4. run exit code

- pipeline 返回 `completed` 且无失败章节时 exit code 0。
- pipeline 返回 `partial` / `failed` 或存在 `chapters_failed` 时保留 `run_id` 输出并 exit code 1。
- `SONGYAN_FORCE_EXIT` 路径同步使用对应 exit code。

---

## 代码与测试

主要改动：

- `src/songyan/config.py`
- `src/songyan/services/doctor_service.py`
- `src/songyan/cli/main.py`
- `tests/cli/test_doctor_command.py`
- `tests/cli/test_cli.py`
- `tests/test_130_gate_mode.py`

命令证据见：

- `docs/reports/210-doctor-preflight-evidence.md`

验证结果：

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/cli -q` | 39 passed |
| `python -m pytest tests/test_119_reporting_wrapper.py tests/test_175_cost_tracking.py tests/test_phase2_graph.py -q` | 80 passed, 2 warnings |
| `python -m pytest tests/ -q` | 3063 passed, 2 skipped, 1 xfailed, 7 warnings |
| `ruff check src/ tests/` | pass |

---

## 验收结论

| 验收项 | 结果 |
|--------|------|
| 非法 `CHECKPOINTER_MODE` 不再 traceback | PASS |
| 非法预算不再 traceback | PASS |
| doctor 输出结构化 JSON 诊断 | PASS |
| doctor 覆盖日志路径与预算检查 | PASS |
| run 前缺 key 被 preflight 阻断 | PASS |
| run partial/failed 返回非 0 exit code | PASS |
| 不改 prompt / CED / T9 / hard gate | PASS |
| 不实现 Task 211-215 范围 | PASS |

---

## 后续路由

- Task 211：backup / restore / schema ledger。
- Task 212：失败恢复体验，标准化常见失败分类、提示和恢复动作。
- Task 213：run bundle 与脱敏诊断包。
- Task 214：profile validate、危险项提示、rollback/history。
- Task 215：release checklist、wheel smoke、Windows 路径与发布前总验收。
