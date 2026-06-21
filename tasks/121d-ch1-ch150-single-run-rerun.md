# Task 121d: Ch1-Ch150 Single-Run Rehearsal Rerun

> **日期**: 2026-06-21
> **类型**: V5.0 single-run 修复后验证 / V5.1 preflight
> **状态**: 待执行
> **前置**: Task 121c 已修复 rewrite fallback 后 settlement 被跳过的问题。

---

## 1. 任务边界

Task 121d 只做修复后的 Ch1-Ch150 single-run rehearsal 重跑，不做 Prompt 调优，不新增 workflow 节点，不调整 QG 阈值。

本任务用于验证 Task 121c 是否解除 Task 121b 暴露的 Ch5 settlement skip 阻断，并继续发现下一处真实长跑瓶颈。

---

## 2. 前置清理要求

重跑前必须完成：

- 确认无 `python` / `pytest` / `songyan` 残留进程。
- 清理 `.pytest_cache`、`.ruff_cache`、`__pycache__`、旧 `*.db-wal` / `*.db-shm` 等运行残留。
- 对 `songyan.db` 执行只读完整性检查，确认 `integrity_check` / `quick_check` 为 `ok`。
- 保留 Task 121b 的 `run-21ff158b`、JSONL、report 和数据库 partial 记录，作为历史证据。

---

## 3. 数据隔离策略

Task 121b 使用的 `proj-2375dbfc` 已包含 Ch1-Ch5 partial run，不再作为 Task 121d 的干净起点。

Task 121d 应使用新的 rehearsal 项目，或在执行前明确证明目标项目没有 `chapter_versions`、`chapter_heads`、`project_runs` 等历史章节状态。

---

## 4. 执行要求

正式执行时应记录：

- `project_id`
- `run_id`
- 章节范围 Ch1-Ch150
- wrapper stdout/stderr/meta 路径
- `logs/chapter_runs/<run_id>.jsonl`
- `logs/reports/report-<run_id>.md`

验收：

- 若 150 章通过：记录 150/150 成功、QG/settlement/summary 覆盖率、budget 和 ContextEmergency 指标。
- 若未通过：记录首个失败章节、失败节点、关键日志证据和下一步修复任务。

---

## 5. 当前清理记录

本文件创建时已完成一次重跑前清理：

- 未发现 `python` / `pytest` / `songyan` 残留进程。
- 已清理 pytest/ruff 缓存、Python `__pycache__` 和旧 WAL/SHM 文件。
- `songyan.db` 只读检查结果：`integrity_check=ok`，`quick_check=ok`。
- 未删除 Task 121b 证据日志或数据库 partial 记录。
