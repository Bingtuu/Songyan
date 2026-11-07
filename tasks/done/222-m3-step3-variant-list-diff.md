# 222 · M3 步3 variant list / diff

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD §4.2 / M3；tech-m3 §5 步 3 / §4.1 / §4.3；owner t104s965 开步 3 |
| 预估 | 一个切片 |

## 目标

M3 步 3：增强 `variant list`（槽字段 + fingerprint 短显 + JSON）；新增只读 `variant diff`（unified；缺槽 exit 2）。

## 步骤

- [x] 测试先写：同章两稿可 list/diff；缺槽 exit 2；非法参数 exit 1；list/diff 不写 plan_*
- [x] 服务 + CLI：`list` 表面字段；`diff` unified；`get_by_slot`
- [x] 同步 STATUS / HANDOFF / INDEX / AGENTS / tasks README；跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE

## 验收标准

- [x] `variant list` 暴露 slot_index / status / stale_vs_canon / fingerprint / cost / content_ref / score
- [x] `variant diff --a/--b` 输出 unified；JSON 表面含 diff 文本
- [x] 缺槽 → 退出码 2；非法章号 → 退出码 1
- [x] 只读：不写 `plan_*` / Canon；无 pick/abandon；无 continue/review/branch
- [x] 包仍 `0.5.0`

## 完成总结（DONE 时填写）

PR [#58](https://github.com/Bingtuu/Songyan/pull/58)；head `6026419`；base tip `main` `135fcfb`（#57）。未 merge / 未 APPROVE。包仍 `0.5.0`。下一刀（仅 owner/parent 授权后）：M3 步 4 `variant pick` / `abandon`。
