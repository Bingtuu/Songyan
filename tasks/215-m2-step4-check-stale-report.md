# 215 · M2 步4 check 报告 stale 范围

| 项 | 内容 |
|---|---|
| 状态 | DOING |
| 关联 | PRD §6.5 / W4；tech-m2 §5 步 4 / §3.1 item 3 / §4.1 / §6 |
| 预估 | 一个切片 |

## 目标

M2 步 4：`songyan check` 在 `chapter_heads.content_stale=1` 时报告受影响 / stale 章范围（human + `--json`）。check 仍只读：不写 `content_stale`、plan 行、`chapter_versions`。不做步 5+（extract→pending / 文档对齐）。

## 步骤

- [x] 测试先写：`tests/cli/test_check_stale_report.py` — 标脏后 check 点名范围；check 前后 `content_stale` 与 plan 审批行 / version 正文不变
- [x] `cli/commands/check.py` 最小实现：读取 stale 章集合并写入 human/JSON 输出
- [x] 跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE；不 bump 版本

## 验收标准

- [x] 硬确认标脏后，`check` 点名 stale / 受影响章范围（JSON：`content_stale_chapters` / `chapter_content_stale`；human：`## 正文过期标记`）
- [x] check 本身不改 `content_stale`、plan 审批行、`chapter_versions`
- [x] 退出码沿用既有约定（0 / 1 / 2）
- [x] 无步 5 extract source；包仍 `0.5.0`

## 完成总结（DONE 时填写）

（合并后由 docs-align 归档；本 PR 仅实现步 4。）
