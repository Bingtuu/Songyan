# Task 180 DONE: songyan doctor 环境自检

> 完成日期：2026-07-20  
> 阶段：V9.2 交付与发布  
> 对应任务书：`tasks/180-doctor-environment-check.md`

## 结论

Task 180 已完成。`songyan doctor` 已上线，默认执行无成本、本地只读环境自检；`--init-db` 才初始化/迁移 SQLite DB；`--check-llm` 才执行 LLM client 初始化探针；`--json` 输出机器可读结果。

## 变更范围

- `src/songyan/services/doctor_service.py`
  - 新增 `DoctorCheck` / `DoctorReport`。
  - 检查 `.env`、LLM key/config、SQLite URL/path/schema、checkpointer mode、package runtime resources。
  - schema 检查包含表名与关键迁移列/索引 drift，避免旧库缺列被误报 complete。
- `src/songyan/cli/main.py`
  - 新增 `songyan doctor [--json] [--check-llm] [--init-db]`。
  - 文本输出 PASS/WARN/FAIL；JSON 输出稳定结构；FAIL 时 exit code = 1。
- `tests/cli/test_doctor_command.py`
  - 新增 12 个聚焦测试，覆盖默认不触发 LLM、JSON 输出、DB/schema 诊断、资源检查与 drift 回归。

## 验收结果

| 项 | 结果 |
|---|---|
| Task 180 聚焦 doctor 测试 | `12 passed` |
| Ruff | `ruff check src/ tests/` → All checks passed |
| 默认全量 pytest | `2903 passed, 2 skipped, 1 xfailed, 7 warnings`，`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| Code review | `bits-code-guard` diff-only review 发现 1 个 P2；已修复并补回归测试 |

## 备注

- 默认 `songyan doctor` 不调用真实 LLM、不生成正文、不写业务库。
- `.env` 缺失为 WARN；缺 LLM key、非法 DB URL、资源缺失为 FAIL。
- `tests/cli/test_cli.py` 全文件既有 4 个 create-project 失败仍归 Task 181。
