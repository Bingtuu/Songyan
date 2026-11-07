# 223 · M3 步4 variant pick / abandon

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD §4.2 / M3；tech-m3 §5 步 4 / B4 / B5；owner t104s981 开步 4 |
| 预估 | 一个切片 |

## 目标

M3 步 4：`variant pick` / `variant abandon`（+ JSON）。pick 只移动工作正文指针；abandon 软删；不写 `plan_*`；不覆盖 picked 正文。

## 步骤

- [x] 测试先写：pick 前后 approved 不变；同章仅一 picked；abandon 后仍可读 content；再 generate 不 UPDATE 已 pick 的 version 行；stale 默认拒 / `--allow-stale` 放行；abandon picked 拒
- [x] 服务 + repo 事务 + CLI `pick` / `abandon`
- [x] 同步 STATUS / HANDOFF / INDEX / AGENTS / tasks README；跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE

## 验收标准

- [x] `pick` 改 `ChapterHead.current_version_id`；原 picked → archived；新行 → picked
- [x] `pick` 前后 `plan_*` approved 快照不变；不自动 confirm / 不标 `content_stale`
- [x] `stale_vs_canon=1` 默认 exit 2；`--allow-stale` 才允许
- [x] `abandon` → status=`abandoned`；正文仍可读；abandon 当前 picked → exit 2
- [x] 再 `generate` 不 UPDATE 已 pick 的 `content_ref` 正文
- [x] 夹具含 `pick --slot 2`（S4 可观测）
- [x] 无步 5/6；无 continue/review/branch；包仍 `0.5.0`

## 完成总结（DONE 时填写）

PR [#59](https://github.com/Bingtuu/Songyan/pull/59)；head `d9de192`；base tip `main` `0b47410`（#58）。未 merge / 未 APPROVE。包仍 `0.5.0`。下一刀（仅 owner/parent 授权后）：M3 步 5（stale 自动标脏 + 费用可见）。
