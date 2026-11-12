# 246 · 修复 run 收尾 db-maintenance 锁表失败

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-12；根因修复 + 最终实测 PASS 后归档；代码 @ `8c26105` 之后的独立提交） |
| 关联 | `src/songyan/db/connection.py:get_db`（根因点）；`src/songyan/workflows/phase2_graph.py:_run_db_maintenance`（暴露点；触发点 :991 / :1157）；真实模型冒烟 step 1a（2026-11-11，`.tmp/smoke-m4-20261111/notes.md` 已知告警节） |
| 预估 | 一个调查切片 + 一个修复切片（TDD）——实际：调查 4 轮实验 + 根因修复 + 防御层 |

## 目标

消除 `run` 章节成功后收尾维护步骤在 Windows + memory checkpointer 下的 `database table is locked`，让 DB 维护（遥测采样 + WAL 截断 + optimize）实际执行而不是静默跳过。

## 根因（2026-11-12 实锤，实验链）

**`get_db()` 的 `PRAGMA quick_check` 从不消费结果**，是 `database table is locked` 的元凶：

1. **分步插桩**（真实 run，`.tmp/smoke-246-debug/`）：异常发生在 `step=wal_checkpoint`；PASSIVE 同样抛——排除「TRUNCATE 需独占截断」假设。既有 `run_db_metrics` 行时间戳与告警同刻 → 遥测 INSERT 成功，肇事语句在 checkpoint/optimize 之中。
2. **sync 探针**（失败同一进程同一瞬间）：sync `sqlite3` 连接 `wal_checkpoint(TRUNCATE)` 成功 `[(0,0,0)]`——排除 DB 文件 / 进程级 WAL 锁死，问题锁定在 aiosqlite 连接自身状态。
3. **最小复现**：完全按 `get_db()` 的 pragma 序列（aiosqlite `execute` 只 prepare 不 step）后跑 `wal_checkpoint` → 稳定复现 `OperationalError: database table is locked`。
4. **单变量二分**：只发 `PRAGMA quick_check` 必炸；去掉即正常。机制：quick_check 在 prepare 期启动完整性扫描并持锁，语句未 step 完结/close，同连接后续 `wal_checkpoint`（需 schema 独占）吃 SQLITE_LOCKED。

**损害面**：不只 run 收尾维护——任何 `get_db()` 连接上的 `wal_checkpoint` 都会炸（只是全库只有 `_run_db_maintenance` 跑 checkpoint，所以只有它暴露）。且 RES-03 的完整性检查语义从未真正完成。

## 修复（TDD）

- **根因修复**：`get_db()` 的 quick_check 改为 fetch 全部结果 + close 游标；非 ok 行记 `db.integrity_check_failed`（带问题样本）。RED：`tests/db/test_connection.py::TestQuickCheckCheckpointRegression`（get_db 连接可跑 wal_checkpoint；quick_check 真执行返回 ok）→ GREEN。
- **防御层（`_run_db_maintenance`，保留）**：分步独立容错（单步失败不跳过其余）；checkpoint 结果行必须 fetch——busy≠0 记 `db_checkpoint_busy`（原代码从不 fetch，busy 被静默吞掉，是独立缺陷）；TRUNCATE 失败 / busy → 回退 `wal_checkpoint(PASSIVE)`（真实并发读者场景 busy 行 (1,3,3) 本地实证可达）。RED：`TestTruncateCheckpointFallback` 3 测 → GREEN。
- 诊断 sync 探针已完成使命，未保留进代码。

## 步骤

- [x] 本地复现 + 定位：4 轮实验链实锤（插桩 → sync 探针 → 最小复现 → 单变量二分）。
- [x] TDD 根因修复：`get_db` quick_check 消费结果；回归 2 测。
- [x] TDD 防御层：分步容错 + busy 行落日志 + PASSIVE 回退；回归 3 测。
- [x] 最终实测（`.tmp/smoke-246-final/`）：修复后 Windows 真实单章 run **0 条** `db_maintenance_failed`（修复前 3/3 必现），`db_telemetry_sampled` 正常、WAL 截断为 0 字节、费用 ¥0.4203。

## 验收标准

- [x] Windows + memory checkpointer 下 `run` 收尾无 `db_maintenance_failed`——实测 0 条（此前 3/3 复现）。
- [x] 维护步骤实际生效——遥测行落库 + `db_telemetry_sampled` 日志 + WAL 截断 0 字节。
- [x] 非 Windows 行为不变——修的是通用语义（未消费语句不该悬挂），无平台特判。
- [x] 全量 pytest 绿（3623 passed / 2 skipped / 1 xpassed）+ ruff 绿；不 bump 版本。
- [x] 完工同步 `docs/STATUS.md` / `docs/HANDOFF-mew.md`；归档 `tasks/done/`。

## 完成总结

**状态**：DONE（2026-11-12）。

**做了什么**：四轮实验（分步插桩 → 同进程 sync 探针对照 → 按 get_db pragma 序列最小复现 → 单变量二分）实锤根因——`get_db()` 的 `PRAGMA quick_check` 发出后从不消费结果，prepare 期启动的完整性扫描持锁悬挂，使同连接后续 `wal_checkpoint` 抛 SQLITE_LOCKED「database table is locked」。修复：quick_check 结果取尽 + 游标关闭（顺带让 RES-03 检查真正完成）；另加防御层（维护分步容错、checkpoint busy 行落日志——原代码从不 fetch 结果行、busy 被静默吞掉、TRUNCATE 失败回退 PASSIVE）。

**测试**：TDD 两批 RED→GREEN（connection 回归 2 测 + 维护回退 3 测）；全量 3623 passed / 2 skipped / 1 xpassed（原 xfail 转 pass，非本任务引入的失败）+ ruff 绿。

**真实模型复验**：`.tmp/smoke-246-final/` 单章 run 收尾 `db_maintenance_failed` 0 条（修复前 3/3 必现），遥测落库、WAL 截断 0 字节，费用 ¥0.4203。

**遗留**：无本案遗留。另注：246 调查期间两次 debug run 因 Git Bash `$PWD` 路径形态把库写到了 `C:\c\Vibe Project\...`（已注意，最终验收用 Windows 绝对路径）；既有 flake（doctor 子进程 / canon promise 并发）与本任务无关。
