# Task 178 DONE: wheel 打包与资源加载修复

> 完成日期：2026-07-19  
> 阶段：V9.2 交付与发布  
> 对应任务书：`archive/v9/178-wheel-packaging-resource-loading.md`

## 结论

Task 178 已完成。Songyan 运行资源已从仓库根目录迁入包内并纳入 wheel，默认 loader 改为 `importlib.resources` 解析；外部目录注入口保留。wheel 安装后，在非仓库 cwd 已跑通资源枚举、`create-project --template scifi` 和 scifi Ch1-3 真实生成。

执行中额外发现并修复：`songyan/db/schema.sql` 也是 wheel 运行资源。首次 wheel `create-project` 验收因缺少该 SQL 失败，已把 `**/*.sql` 加入 `songyan` package-data，并补入 Task 178 资源测试。

## 变更范围

- 资源迁移：
  - `prompts/cards/` → `src/songyan/prompts/cards/`
  - `prompts/literary_plugins/` → `src/songyan/prompts/literary_plugins/`
  - `genres/*.json` → `src/songyan/genres/data/*.json`
  - `creative_modes/*.json` → `src/songyan/creative_modes/data/*.json`
  - `project_templates/*` → `src/songyan/project_templates/data/`
  - `evals/seeds/` 保持原位，作为 `evals` 包资源打包。
- `pyproject.toml` package-data：
  - `songyan = ["**/*.yaml", "**/*.json", "**/*.md", "**/*.sql"]`
  - `evals = ["seeds/**/*.json", "seeds/**/*.md"]`
- Loader 接线：
  - `PromptLoader`、`plugin_loader`、`genres.loader`、`creative_modes.registry`、`ProjectTemplateLoader`、`evals.runner.resolve_seed_resource()`。
- 脚本收口：
  - 170j/k/l 实验脚本改为 `TemporaryDirectory()` 临时 mode 目录。
  - `inject_172d_genre_lexicons.py` / `audit_172a1_genre_tokens.py` 改读写包内 data 路径。
- 死代码清理：
  - 删除 `goal_planner.py` 与 `creative_director/__init__.py` 中未使用的 `PROMPT_PATH`。

## 验收结果

| 项 | 结果 |
|---|---|
| Task 178 资源测试 | `6 passed` |
| 资源相关测试组 | `137 passed, 1 warning` |
| 全量 pytest | `2903 passed, 2 skipped, 1 xfailed, 7 warnings`，`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| Ruff | `ruff check src/ tests/` → All checks passed |
| wheel 构建 | `pip wheel --no-deps . -w .tmp\178_wheelhouse` → `songyan-2.0.0-py3-none-any.whl` |
| wheel 资源枚举 | 非仓库 cwd + venv site-packages：7 genre、4 mode、12 template id、prompt cards、literary plugins、`evals/seeds`、`schema.sql` 全部可读 |
| wheel create-project | `songyan create-project --template scifi` 成功，project `0202ebd879304d52891bd09fb207b934` |
| wheel Ch1-3 | `songyan run --project-id 0202ebd879304d52891bd09fb207b934 --chapters 1-3 --auto-confirm` → 3/3 成功，run `run-1d5fbe93` |
| scifi end10 回归 | 10/10 accepted，status `completed`，failed `[]`，budget 峰值 0.9693，总成本约 ¥0.8744，`WRAPPER_RESULT=PASS_NORMAL_EXIT` |

## 备注

- scifi end10 本次 `t9_issue_count=1`，按诊断残留记录；不得写成 T9=0。
- wheel 验收使用 unpacked wheel 为目标，不承诺 zipimport。
- 非仓库 cwd 真实生成时，仓库 `.env` 不会自动加载；验收命令通过进程环境注入必要 LLM 配置，未打印密钥。
