# 269 · pending 分组过目与伏笔 horizon/归档

| 项 | 内容 |
|---|---|
| 状态 | TODO |
| 关联 | task 259（`canon pending` / `confirm batch`）；task 226（回收只进提案）；`foreshadowing_horizon_floor`（xuanhuan/wuxia=48，urban 默认 0）；dogfood pending 91、overdue 23 |
| 预估 | 两个编码切片（TDD） |

## 目标

人仍必须过目才能入典或销承诺，但过目成本要从「91 条全盘或一条条点」降下来；被放弃的模板伏笔不能继续以 overdue + 紧迫分打进后续上下文。

## 共同约束（266–269 批次）

- 先写测试再写实现。新测试放 `tests/<area>/test_<行为>.py`，禁止新增 `test_task###_*.py`。
- 退出码与既有 CLI 同族（非法/不存在引用 exit 2；非 TTY 缺确认 exit 2 同 B4/259）。
- `canon confirm batch --yes` 保持显式捷径，**不进入** `chapter continue` / `chapter accept` 的默认环。
- 结算声称回收只进提案、不直写 resolved（task 226），本批次不动。
- 全量 pytest + ruff 绿才交验收。STATUS/HANDOFF 由 Mew 勾完验收后同步。

## 步骤

- [ ] 切片 1：给 `canon pending` 加分组/过滤（至少 `--chapter`，建议再加来源或实体）。列出按章或按来源分节。`canon confirm` / `canon dismiss` 支持同一组过滤（例如「本章提案」），摘要后交互 y/N；`--yes` 跳过；**非 TTY 无 `--yes` exit 2**。空集 exit 0 并明示。部分失败 exit 1、已处理的保留。`confirm batch --yes` 仍是「全部 pending」的显式捷径，行为与 259 兼容，不改 W2 默认环。
- [ ] 切片 2：抬高 urban 的 `foreshadowing_horizon_floor`。建议先取 **8**（短篇都市灵异；只抬高不缩短；scifi/默认 0 不受影响）。机制已在结算写入时夹紧 `expected_resolve`（见 `_nodes.py` 与 `GenreRuntimeProfile`），改档案值并补测即可。
- [ ] 切片 2 续：补承诺归档写径（表上已有 `foreshadowings.lifecycle_status`：active/dormant/archived，但无对应 CLI）。例如 `canon dismiss promise --foreshadowing-id`（或 `canon archive promise`）：把放弃的承诺标 archived，幂等；归档后不再进入开放承诺集、`today` 的 overdue、上下文紧迫加分。这不是 `confirm promise`（那个仍是人确认回收为 resolved）。
- [ ] LLM 给出的 `expected_resolve_chapter` 在人确认到期日前只当建议：`today` / `canon show --kind promise` 可显示「建议到期」，但 **overdue 计数和「2 章内到期 +2 紧迫」只作用于已确认到期日的承诺**。未确认的不得把 +1/+2 种下即打成逾期硬信号。确认到期日的命令要单独、显式（不要和入典 batch 绑在一起）。

## 验收标准

- [ ] 能按章列出并确认/驳回一组 pending；非 TTY 无 `--yes` 零写入 exit 2；全部 batch 路径未变成 continue/accept 默认步骤。
- [ ] urban 新种伏笔的 expected_resolve 至少是 planted+8；夹具能证明 +1/+2 会被抬高。
- [ ] 归档后的承诺不出现在开放集与上下文紧迫列表；`confirm promise` 对已归档行拒绝。
- [ ] 未确认到期日的承诺不计入 overdue、不加 +2 紧迫；确认后才按到期日计算。
- [ ] 结算回收仍只进提案。全量 pytest + ruff 绿；不 bump 版本。

## Mew 验收时额外会做的事（不必写进实现 PR）

用夹具回归「urban 种下 → 266 清场 / 267 不占槽 / 268 无种子创建」。如需实模型抽检（都市灵异写 1–2 章看是否再漏模板），会先报预算再跑，不默认重放 8 章。

## 完成总结（DONE 时填写）
