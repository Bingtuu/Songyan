# 217 · M2 步6 闭环文案与文档同步

| 项 | 内容 |
|---|---|
| 状态 | DOING |
| 关联 | tech-m2 §5 步 6；STATUS / HANDOFF / today next |
| 预估 | 一个切片 |

## 目标

M2 步 6：更新 `today` 固定 `next`（提示 confirm/入典、承诺债、硬确认；仍声明生成不在本命令）；同步 STATUS / HANDOFF / INDEX / AGENTS / tasks 与 main 上步 5（#52 / `2fa8209`）。不声称 V1.0 完成；不 bump `0.5.0`；不开 M2 代码验收 / variant / continue。

## 步骤

- [x] 更新 `workbench.py` `_NEXT` + `tests/cli/test_workbench_commands.py`
- [x] 同步 STATUS / HANDOFF / INDEX / AGENTS / tasks；归档 216；新建 217
- [x] 跑 ruff + workbench/today 相关 pytest；开 PR，不合并、不 APPROVE；不 bump 版本

## 验收标准

- [x] `_NEXT` 含 confirm/入典、承诺（销账）、`--hard`/`--mark-stale`，且声明生成不在本命令
- [x] 文档记步 5 已在 `main`（#52 → `2fa8209`）；本 PR = 步 6；合入后 tip 含步 1–6，下一刀 = M2 代码验收（仅授权后）
- [x] 无 V1.0 完成声称；包仍 `0.5.0`；无验收编码 / variant / continue

## 完成总结（DONE 时填写）

PR [#53](https://github.com/Bingtuu/Songyan/pull/53)（head `ad2c83d`；基 tip `2fa8209`）。`today` `_NEXT` 更新为提示 confirm/入典、承诺销账与 `--hard`/`--mark-stale`；文档对齐步 5 已合入并指向步 6。归档 216。未 merge / 未 APPROVE；包仍 `0.5.0`；未开 M2 代码验收 / variant / continue。合入后 tip 含步 1–6；下一刀 = M2 代码验收（仅 owner/parent 授权后）。
