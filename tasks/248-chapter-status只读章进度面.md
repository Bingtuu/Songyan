# 248 · chapter status（只读章进度面）

| 项 | 内容 |
|---|---|
| 状态 | TODO（tech-m4-followup 步 1；owner 已接受 B1–B8，2026-11-12） |
| 关联 | `docs/tech-m4-followup.md` §3 / B1 / B2；PRD §9.2 命令树；tech-m4 B10 分工句 |
| 预估 | 一个编码切片（TDD）+ tests/cli 套件 |

## 目标

落地 `songyan chapter status --project-id TEXT --chapter INT [--json]`：章级只读进度面（中薄面）。不承载 ContextEmergency（B2）；纯只读零写库，含不触发 `refresh_stale_vs_canon` 懒标定（status 是观察面不是结算面，stale 读当前值）。

## 字段面（B1 定稿）

| 分区 | 字段 | 来源 |
|---|---|---|
| 章态 | 六态之一（stale/settled/picked/variants_ready/drafting/empty） | 复用 `chapter_progress` 同优先级推导 |
| head 指针 | `current_version_id` / `accepted_version_id` / `content_stale` | `chapter_heads` |
| variant 槽列表 | 每槽 `slot_index / status / quality_flag / stale_vs_canon / cost_cny_estimate`（全状态，同 `variant list` 序） | `chapter_variants` |
| 本章费用 | 槽成本合计 + `llm_call_usage` 按章 SUM 对照 | 现有表 |
| 共审概况 | findings 按严重度计数（不重建全文报告） | `services/review_report.build_chapter_review` 只读路径 |

## 行为口径

- exit 码（B11 同形）：0 = 成功；2 = 章不在章宇宙（业务拒绝）；1 = 缺库 / 缺项目。
- 文本输出按分区；`--json` 同形；无槽显示「无槽」不报错。
- head 缺失（章只在 variants/versions 宇宙里）时指针分区显示空值说明，不炸。

## 步骤

- [ ] TDD：服务层 `load_chapter_status`（五态装配：empty/drafting/picked/settled/stale 各一断言；exit 2 分支在 CLI 层）
- [ ] CLI 挂 `chapter` 组；`--json` 字段完整性；tests/cli 套件
- [ ] 全量回归 + ruff；完工同步 STATUS/HANDOFF；归档

## 验收标准

- [ ] 五态装配断言全绿；章不在章宇宙 exit 2 文案明确
- [ ] 零写库（测试前后表行数快照一致）
- [ ] 全量 pytest 绿 + ruff 绿；不 bump 版本
- [ ] 完工同步 `docs/STATUS.md` / `docs/HANDOFF-mew.md`；归档 `tasks/done/`

## 完成总结

（待 DONE 时填写）
