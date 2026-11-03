# 205 · rejected 迁移与仓库过滤

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD 6.3；tech-m1 §3.4 / §5 步 1；W0 |
| 预估 | 一个切片 |

## 目标

五张 `plan_*` 表的 `approval_status` CHECK 允许 `rejected`；`PlanApprovalStatus` / `_APPROVAL` 同步；`list_pending_*` / Canon / 圣经均不展示 `rejected` 行。本切片不做 `canon edit` / `confirm` / `dismiss` CLI。

## 步骤

- [x] 测试先写：插入 `rejected` 后 Canon / Pending / `load_chapter_plan_bible` 均不可见；迁移空库与有数据库幂等
- [x] `_MIGRATIONS` 追加重建式迁移（五表 CHECK 含 `rejected`）；同步模型与仓库映射
- [x] 跑 tech-m1 第 7 节相关命令；开 PR，不合并

## 验收标准

- [x] 五表 CHECK 合法值为 `approved` \| `pending` \| `rejected`
- [x] `list_canon_*` 仍只含 `approved`；`list_pending_*` 排除 `rejected`
- [x] `rejected` 行不进 `load_chapter_plan_bible`（S8）
- [x] 迁移可重复跑；已有 `approved`/`pending` 行数据保留
- [x] 不改 workflows / settlement_extractor；不升包版本；不做步 2+

## 完成总结（DONE 时填写）

PR [#35](https://github.com/Bingtuu/Songyan/pull/35) squash 进 `main` 为 `1995181`。五表重建迁移 + 模型/仓库/`list_pending_*` 过滤落地。下一步：步 2 `canon edit`（`tasks/206`）。
