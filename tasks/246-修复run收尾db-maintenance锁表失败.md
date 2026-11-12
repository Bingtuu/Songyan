# 246 · 修复 run 收尾 db-maintenance 锁表失败

| 项 | 内容 |
|---|---|
| 状态 | TODO |
| 关联 | `src/songyan/workflows/phase2_graph.py:_run_db_maintenance`（:266；触发点 :991 / :1157）；真实模型冒烟 step 1a（2026-11-11，`.tmp/smoke-m4-20261111/notes.md` 已知告警节） |
| 预估 | 一个调查切片 + 一个修复切片（TDD） |

## 目标

消除 `run` 章节成功后收尾维护步骤在 Windows + memory checkpointer 下的 `database table is locked`，让 DB 维护（遥测采样 + WAL 截断 + optimize，收尾或含 VACUUM）实际执行而不是静默跳过。

## 背景（冒烟实证，2026-11-11）

- 项目 A `run --chapters 1 --auto-confirm`：章节本身成功（exit 0，3297 字），收尾报 `project_pipeline.db_maintenance_failed: database table is locked (final=True)`。
- 非阻塞（异常只告警不中断 run），但维护静默失败 = `RunDbMetricsRepository` 遥测行之外的物理维护（`PRAGMA wal_checkpoint(TRUNCATE)` / `PRAGMA optimize`，收尾超阈时 `VACUUM`）未执行，长跑项目 WAL 会持续累积。
- **疑向（待实证，勿直接当结论）**：`_run_db_maintenance` 用 `get_db()` 独立短连接执行 `wal_checkpoint(TRUNCATE)`——TRUNCATE 要求无其他连接持有 WAL。run 主链路 / memory checkpointer 若仍持有同库连接（尤其读事务），Windows 下 SQLite 文件锁行为比 POSIX 严格，容易撞锁。

## 步骤

- [ ] 本地复现：Windows + `CHECKPOINTER_MODE=memory` + 隔离 `DATABASE_URL` 跑单章 run，抓锁发生时序（哪个连接持有锁、维护语句是哪条）
- [ ] 定位：确认失败点是 `wal_checkpoint(TRUNCATE)`、`optimize` 还是 `VACUUM`；确认锁持有方（主连接池 / checkpointer）
- [ ] 修复（选最小改动，候选方向）：维护前显式关闭 / 提交 checkpointer 写侧；维护与写路径串行化；连接加 `busy_timeout`；或改 checkpoint 模式（PASSIVE）。修通用时序问题优先于平台特判
- [ ] TDD：锁场景回归（模拟并发持有连接时维护不炸 / 等待成功）
- [ ] Windows 实测：单章 run 收尾无 `db_maintenance_failed`，且遥测日志确认维护实际执行

## 验收标准

- [ ] Windows + memory checkpointer 下 `run` 收尾无 `db_maintenance_failed`
- [ ] 维护步骤实际生效（日志 / `run_db_metrics` 行 / WAL 截断证据）
- [ ] 非 Windows 行为不变，或差异有明确说明
- [ ] 全量 pytest 绿 + ruff 绿；不 bump 版本
- [ ] 完工同步 `docs/STATUS.md` / `docs/HANDOFF-mew.md`；归档 `tasks/done/`

## 完成总结

（待 DONE 时填写）
