# Task 179 DONE: CLI 体验修复

> 完成日期：2026-07-19  
> 阶段：V9.2 交付与发布  
> 对应任务书：`archive/v9/179-cli-experience-fixes.md`

## 结论

Task 179 已完成。`songyan run` 现在会在成功结束后输出稳定 `run_id: <id>` 行；未显式传入 `--mode-id` 时会从项目库读取 `projects.mode_id`，显式传入时仍可覆盖；README CLI 表已补齐 `songyan index` 并同步 `run` 关键参数。

## 变更范围

- `src/songyan/cli/main.py`
  - `--mode-id` 默认改为 `None`。
  - 新增 `_resolve_run_mode_id(project_id, explicit_mode_id)`。
  - 成功摘要输出 `run_id: <result.run_id>`。
- `tests/cli/test_cli.py`
  - 新增 Task 179 聚焦测试：run_id 输出、项目 mode fallback、显式 mode 覆盖、项目缺失错误、index help 注册。
- `tests/test_130_gate_mode.py`
  - gate-mode 成功路径显式传入 `--mode-id webnovel`，保持测试语义只聚焦 gate config。
- `README.md`
  - CLI 表补齐 `songyan index`。
  - `songyan run` 参数说明同步为“默认回读项目 mode，显式 `--mode-id` 覆盖”。

## 验收结果

| 项 | 结果 |
|---|---|
| Task 179 聚焦 CLI 测试 | `12 passed` |
| Ruff | `ruff check src/ tests/` → All checks passed |
| 默认全量 pytest | `2903 passed, 2 skipped, 1 xfailed, 7 warnings`，`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| Code review | `bits-code-guard` diff-only review → 0 P0/P1/P2 findings |

## 备注

- 本任务没有修复 `tests/cli/test_cli.py` 全文件中的 4 个既有 `create-project` 输出解析失败；该项仍归 Task 181。
- 本任务未跑真实 LLM 生成回归；修改范围是 CLI 包装行为，不触碰 workflow 生成、Agent 或状态结算路径。
