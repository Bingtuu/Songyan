# 209 · W0 闭环与 today 文案（步 5）

| 项 | 内容 |
|---|---|
| 状态 | DOING |
| 关联 | PRD 6.3 / W0；tech-m1 §5 步 5 / §6；W0 |
| 预估 | 一个切片 |

## 目标

M1 步 5：一条端到端 CLI 测试锁定 `show` → `edit` → `confirm`/`dismiss` → `show` 再看见（entity+attribute）；更新 `today` 固定 `next`，不再暗示 confirm 不可用；同步故意更新 M0 锁文案测试。本切片不做 M2、不改 workflows / settlement_extractor、不升包版本、不声称 V1.0 完成。

## 步骤

- [x] 测试先写：`tests/cli/test_w0_e2e.py`（entity confirm + attribute dismiss 闭环）；更新 `tests/cli/test_workbench_commands.py` 锁新 `_NEXT`
- [x] 更新 `workbench.py` 的 `_NEXT` 产品文案
- [x] 轻量同步 STATUS / HANDOFF / INDEX / AGENTS / tasks README；跑 tech-m1 §7；开 PR，不合并、不 APPROVE

## 验收标准

- [x] 端到端：`canon show` → `edit` → `confirm`/`dismiss` → `show` 可见状态变化（至少 entity+attribute）
- [x] `today` / `today --json` 的 `next` 为新句，不再含「确认入典……不在本命令」
- [x] M0 `test_workbench_commands` 故意同步新锁文案（PR 说明写「故意更新 M0 锁文案」）
- [x] 不改 workflows / settlement_extractor；不升包版本（仍 `0.5.0`）；不做步 5 以外工作

## 完成总结（DONE 时填写）

（合入后填写 PR 与 tip SHA。）
