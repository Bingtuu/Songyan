# 228 · promise 销账 evidence 落库 + 事务化

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | tech-m2 §4.1 / B3；tech-m1 注记（evidence 留痕推迟项，现已到期）；来源 = 全量评审发现（M1 R2/M3 均命中） |
| 预估 | 一个切片 |

## 背景

226 之后 `foreshadowings.status='resolved'` 的唯一写径是 `canon confirm promise`（人确认销账）。但人给的 `--evidence` 目前只被 echo，不落库——审计链上「谁、凭哪条证据销的账」没有持久记录；且 `_confirm_promise` 是 check-then-act：状态预检在一条连接，`update_status` 在另一条连接，并发/重入下守卫可被越过。tech-m1 已声明 evidence 落库是推迟项，现到期。

## 目标

1. `foreshadowings` 增加 `resolved_evidence TEXT` 列（写-only 审计，不改任何读口径/门）。
2. `canon confirm promise` 把 evidence 持久化到该列。
3. 状态守卫 + 写入收进同一事务（单连接），消除 check-then-act。

## 步骤

- [x] 建任务 + HANDOFF 指向
- [ ] RED：三个失败测试（evidence 落库 / 并发守卫 / 旧库迁移补列）
- [ ] GREEN：迁移 + schema.sql + `update_status(resolved_evidence=)` + `_confirm_promise` 单事务
- [ ] 全量验证 + 只读 review
- [ ] 完成总结 + 归档 + 提交

## 验收标准

- [ ] confirm promise 后行上 `resolved_evidence` = 人给的 evidence（测试锁死）。
- [ ] 旧库（无该列）跑迁移补列，既有行保持 NULL。
- [ ] 并发双 confirm 同一伏笔：恰好一个成功（测试锁死）。
- [ ] 不改 `canon show --kind promise` 等任何读/展示口径；不改 open 集口径。
- [ ] `pytest tests/` 全绿（允许既有 flaky `test_llm_http_timeout`）；ruff / mypy 过。

## 完成总结（DONE 时填写）

**状态**：DONE（2026-11-07）。

**做了什么**：`foreshadowings` 加 `resolved_evidence TEXT` 列（schema.sql + `_migrate_foreshadowings_resolved_evidence`，注册于 _MIGRATIONS 末尾，幂等只增）；repo 新增 `settle_resolved`——原子 UPDATE 自带开放集守卫（`lifecycle_status='active' AND status IN open 集`），rowcount==1 才成交；`_confirm_promise` 改为预检 fast-fail + 事务内原子守卫，evidence 随写入落库。review 两条 Low 已同切片修复：守卫失败错误消息重读当前状态（不再引用过期预检值）；`update_status` docstring 声明 resolved 写径为 `settle_resolved`。STATUS 已同步。

**验收**：三个新测试（evidence 落库 / 并发双销账恰一成交 / 旧库迁移补列）先红后绿；相关回归 `test_canon_confirm_promise + test_workbench_promise_readonly + test_review_settlement_repository` 28 passed；ruff / mypy（198 文件）全绿。读口径与 open 集零变化（写-only 审计列）。

**遗留**：无。
