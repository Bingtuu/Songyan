# Task 181 DONE: CI 上线与测试清零

> 完成日期：2026-07-20
> 阶段：V9.2 交付与发布
> 对应任务书：`tasks/181-ci-and-test-cleanup.md`

## 结论

Task 181 已完成。GitHub Actions CI 已上线，覆盖 ruff、mypy、默认 pytest 与 CLI pytest；`tests/cli` 既有 4 个失败已清零；`mypy src/` 已清零；README 不再使用手写测试通过数 badge。

## 变更范围

- `.github/workflows/ci.yml`
  - `ruff check src/ tests/`
  - `mypy src/`
  - `python -m pytest tests/ -q`
  - `python -m pytest tests/cli -q`
- `tests/cli/test_cli.py`
  - 修复 create-project 输出解析，CLI 测试从 4 fail 变为全绿。
- Task 178 资源 loader 类型修复
  - Traversable API 改为 mypy 可识别的 `is_dir()` / `is_file()`。
  - `ProjectTemplateLoader` 对 zip-backed `outline.json` 使用 `as_file()`。
- 其他 mypy 收口
  - logging setup processor typing、continuity severity、LLM cost_source、lifecycle cleaner helper 返回类型。
- README / STATUS / V9-README / INDEX / AGENTS 同步。

## 验收结果

| 项 | 结果 |
|---|---|
| CLI 测试 | `35 passed` |
| mypy | `Success: no issues found in 172 source files` |
| Ruff | All checks passed |
| 默认全量 pytest | `2904 passed, 2 skipped, 1 xfailed, 7 warnings`，`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| Code review | `bits-code-guard` 分组 review 发现 1 个 P2；已修复并补回归测试 |

## 备注

- 本任务没有引入真实 LLM CI；CI 只跑本地/单元/CLI 口径。
- README badge 改为 GitHub Actions workflow badge，不再手写 passed 数。
