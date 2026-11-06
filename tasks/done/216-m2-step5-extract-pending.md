# 216 · M2 步5 抽取→pending（source=extract）+ S8

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD §7.3 / 导入 M2；tech-m2 §5 步 5 / B4–B6 / §3.1 item 6–7 / §4.4；S8 |
| 预估 | 一个切片 |

## 目标

M2 步 5：`plan_attributes.source` CHECK 扩 `'extract'`；SettlementExtractor / import 经 `apply_settlement` 将抽取映射为 `plan_*` 的 `pending`（属性 `source=extract`）；confirm 前不进 `list_canon_*` / 圣经（S8）；confirm 后可见且 source 保持 `extract`；旧结算表保留为 `untrusted_until_confirmed` 对照；`apply_settlement` 不得把 `plan_*` 写成 `approved`。不做步 6 / variant / continue；包仍 `0.5.0`。

## 步骤

- [x] 测试先写：迁移接受 extract；pending extract 不在 canon / 圣经；confirm 后可见且 source=extract；apply_settlement 入队 pending 且不 approve；结算读径带 untrusted 标记
- [x] 窄迁移 + `PlanFactSource` / `_SOURCE` / `list_canon_attributes`
- [x] `enqueue_extract_proposals` + `apply_settlement` 调用；结算 repo 标注 `untrusted_until_confirmed`
- [x] 跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE；不 bump 版本

## 验收标准

- [x] `source` CHECK / Literal 含 `plan`\|`human`\|`extract`
- [x] 抽取入队后 `approval_status=pending`、`source=extract`；confirm 前不在 `list_canon_*`；S8=0 泄漏
- [x] confirm 后进 canon，source 仍为 `extract`
- [x] `apply_settlement` 不写 `plan_*` 的 `approved`
- [x] 旧结算表仍在；读径可标 `untrusted_until_confirmed`
- [x] 无步 6 / variant / continue；包仍 `0.5.0`

## 完成总结（DONE 时填写）

PR [#52](https://github.com/Bingtuu/Songyan/pull/52) squash 进 `main` 为 `2fa8209`（CI 修复 head 曾为 `8004edb`）。抽取 / import 经 `apply_settlement` 入队 `plan_*` pending（`source=extract`）；confirm 前不进 canon / 圣经（S8）；结算表保留 untrusted 对照。未做步 6 / variant / continue；包仍 `0.5.0`。下一刀：M2 步 6（闭环文案与文档同步）。
