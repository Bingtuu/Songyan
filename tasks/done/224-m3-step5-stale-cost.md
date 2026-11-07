# 224 · M3 步5 stale_vs_canon + 费用可见

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD §4.2 / M3；tech-m3 §5 步 5 / B3 / B6；owner t104s992 开步 5 |
| 预估 | 一个切片 |

## 目标

M3 步 5：Canon 变更后自动标 `stale_vs_canon`；pick 默认拒 stale；list/报告 per-slot 费用字段可见；S4 可观测非 1 号 pick。

## 步骤

- [x] 测试先写：改 approved 属性后旧 variant `stale_vs_canon=1`；无 `--allow-stale` pick exit 2；有则放行；list 费用字段存在（可为 0）；不改 `content_stale`
- [x] 选定并锁定 **懒标记**（list / diff / pick / generate 前比对指纹标 `stale_vs_canon=1`；不自动清 0）；不改 M2 hard confirm 路径
- [x] 同步 STATUS / HANDOFF / INDEX / AGENTS / tasks README / tech-m3 进度；跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE

## 验收标准

- [x] 改 approved Canon 后，旧 variant 经 list/pick/diff/generate 前懒标记为 `stale_vs_canon=1`
- [x] pick 默认 exit 2；`--allow-stale` 才允许（仍不写 Canon / 不改 `content_stale`）
- [x] `variant list` JSON/text 含 per-slot `cost_cny_estimate`（字段存在；夹具可为 0）
- [x] 夹具可 `pick --slot 2`（S4）
- [x] 无步 6 / continue / review / branch / auto-pick；包仍 `0.5.0`

## 完成总结（DONE 时填写）

PR 待开；head 见 PR；base tip `main` `c38ee31`（#59）。未 merge / 未 APPROVE。包仍 `0.5.0`。下一刀（仅 owner/parent 授权后）：M3 步 6（闭环文案与文档同步）。
