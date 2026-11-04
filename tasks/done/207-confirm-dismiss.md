# 207 · confirm + dismiss 入典主表面

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD 6.3；tech-m1 §3.4 / §4.2 / §5 步 3；W0 |
| 预估 | 一个切片 |

## 目标

人可通过 `songyan canon confirm` / `dismiss` 改变计划行持久 `approval_status`（至少 entity + attribute）：confirm → `approved` 且 Canon / 圣经可见；dismiss → `rejected` 且不在 list_canon_* / pending / 圣经。若保留 CLI `accept`，零 DB 写，仅提醒去 confirm。本切片不做 check / today 文案。

## 步骤

- [x] 测试先写：entity/attribute confirm → approved + canon/bible；dismiss → rejected 排除；accept（若有）不改库；rejected 后再 edit → pending；缺库/缺项目/坏 id exit 1
- [x] 实现 `canon confirm` / `dismiss`（+ 可选非持久 `accept`）；注册不破坏 M0 / 步 2
- [x] 跑相关 ruff / mypy / pytest；开 PR，不合并、不 APPROVE

## 验收标准

- [x] `confirm` 后 `approval_status=approved`，输出含「已入典」；出现在 `list_canon_*`；章窗口规则下可进 `load_chapter_plan_bible`
- [x] `dismiss` 后 `approval_status=rejected`；不在 `list_canon_*` / pending / 圣经（S8）；行仍可读
- [x] 若有 `accept`：零 DB 写；提醒尚未入典、请 confirm
- [x] rejected 后同 id `edit` 覆盖为 pending，需再 confirm
- [x] 缺库 / 缺项目 / 坏 id exit 1；缺库不建空库
- [x] 不改 workflows / settlement_extractor；不升包版本；不做步 4+

## 完成总结（DONE 时填写）

PR [#38](https://github.com/Bingtuu/Songyan/pull/38) squash 进 `main` 为 `7c7ec43`。`canon confirm` / `dismiss`（+ 非持久 `accept`）支持 entity + attribute；未做 check / today 文案。下一刀（仅 owner/parent 授权后）：步 4 `check`。
