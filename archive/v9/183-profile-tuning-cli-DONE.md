# Task 183 DONE: Profile 调参 CLI

> 完成日期：2026-07-20
> 阶段：V9.3 爬坡工具链
> 对应任务书：`archive/v9/183-profile-tuning-cli.md`

## 结论

Task 183 已完成。`songyan profile show/diff/upsert --genre <g>` 已上线，能够展示 registry / DB override / effective 三列视图，并通过 DB override 完成调参而不改代码。`upsert` 遵循 172i/172j 语义：写入“代码默认模型 + 用户显式字段”的伪稀疏全量 JSON，避免把 registry 调优值误写成 DB 显式覆盖。

## 变更范围

- `src/songyan/services/profile_service.py`
  - Profile 三列视图、override diff、伪稀疏 upsert、reset、嵌套字段校验。
  - `show/diff` 只读 DB，不调用 `init_schema()`，不会创建缺失 DB。
- `src/songyan/cli/main.py`
  - 新增 `profile` 命令组。
  - 新增 `show` / `diff` / `upsert` 子命令。
- `tests/test_183_profile_cli.py`
  - 7 个聚焦测试覆盖只读 show、upsert 写入语义、nested replacement、reset 和错误输入。

## 验收结果

| 项 | 结果 |
|---|---|
| `songyan profile show` | 可展示 registry / DB override / effective |
| `songyan profile diff` | 可展示 DB override 导致的生效差异 |
| `songyan profile upsert` | 可写入 DB override；不会写 effective 全量 profile |
| `--reset` | 可清空 DB override 意图，effective 回到 registry |
| 聚焦测试 | `7 passed` |
| CLI 测试 | `35 passed` |
| 全量默认 pytest | `2921 passed, 2 skipped, 1 xfailed, 7 warnings`；`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| mypy | `Success: no issues found in 175 source files` |
| Ruff | All checks passed |
| Code review | 1 个 P2，已修复并补测 |

## 备注

- 未改变 `load_profile()` 语义，也未修改 `genre_runtime_profiles` schema。
- 未知体裁 upsert 被拒绝；当前 `load_profile()` 对未知体裁回退 scifi baseline，DB override 不能可靠生效。
- 嵌套子模型仍按 172i 语义整体替换；CLI 输出会标注 nested replacement。
