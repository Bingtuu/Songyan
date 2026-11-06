# 221 · M3 步2 variant generate

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD §4.2 / M3；tech-m3 §5 步 2 / B2/B6/S8；owner t104s953 开步 2 |
| 预估 | 一个切片 |

## 目标

M3 步 2：`variant generate` 写 N 条 `ChapterVersion` + `chapter_variants`；只读 Canon；不 auto-pick；per-slot cost；预算耗尽 → 退出码 3。

## 步骤

- [x] 测试先写：N=2 两行 `generated`；`plan_*` 前后一致；S8 pending 零泄漏；预算耗尽 exit 3；无 pick
- [x] 服务编排 + CLI `variant generate`；mock 模型
- [x] 同步 STATUS / HANDOFF / INDEX / AGENTS / tasks README；跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE

## 验收标准

- [x] 默认 `--n 2`；新槽均为 `generated`；无自动 `picked`
- [x] 只读 approved Canon；pending 不进指纹/圣经路径
- [x] 每槽 INSERT version + variant；`cost_cny_estimate` 字段有值
- [x] 预算耗尽保留已写槽；退出码 3
- [x] 不写 `plan_*`；不调用 canon confirm；不 UPDATE 已有 picked 正文
- [x] 无步 3+；无 continue/review/branch；包仍 `0.5.0`

## 完成总结（DONE 时填写）

PR 见本切片开出的 PR；未 merge / 未 APPROVE。包仍 `0.5.0`。下一刀（仅 owner/parent 授权后）：M3 步 3 `variant list`/`diff` 增强。
