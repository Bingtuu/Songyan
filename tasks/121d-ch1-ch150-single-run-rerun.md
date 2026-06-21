# Task 121d: Ch1-Ch150 Single-Run Rehearsal Rerun

> **日期**: 2026-06-21
> **类型**: V5.0 single-run 修复后验证 / V5.1 preflight
> **状态**: DONE / partial
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

---

## 6. 执行结果

Task 121d 已按边界执行，结果为 `partial`。

| 项 | 值 |
|----|----|
| project_id | `929dcc026aee480282c227dbd0522731` |
| run_id | `run-f749826e` |
| 章节范围 | Ch1-Ch150 |
| 实际完成 | Ch1-Ch7 成功，Ch8 失败 |
| wrapper stdout | `logs/task121d/songyan-task121d-ch1-ch150-rerun-20260621-105206.out.log` |
| wrapper stderr | `logs/task121d/songyan-task121d-ch1-ch150-rerun-20260621-105206.err.log` |
| wrapper meta | `logs/task121d/songyan-task121d-ch1-ch150-rerun-20260621-105206.meta.txt` |
| wrapper result | `logs/task121d/songyan-task121d-ch1-ch150-rerun-20260621-105206.result.txt` |
| JSONL | `logs/chapter_runs/run-f749826e.jsonl` |
| report | `logs/reports/report-run-f749826e.md` |

关键结论：

- Task 121b 暴露的 Ch5 settlement skip 阻断已解除。
- Ch1-Ch7 均成功，且 JSONL 中均为 `settlement_success=true`、`summary_success=true`、`skip_settlement=false`。
- Ch1 与 Ch8 均出现 `rewrite.struct_integrity_rollback_decision`，日志显示 `skip_settlement=False`，证明 Task 121c 的 rewrite fallback settlement contract 在重跑中生效。
- Ch8 是新的首个失败点，失败节点为 `settlement_review`，不是 rewrite fallback skip。

Ch8 关键日志：

```text
rewrite.struct_integrity_rollback_decision chapter_number=8
  rollback_source=active_best rollback_version_id=rev-8-3-2160c17c
  recovered_with_qg_pass=True skip_settlement=False

settlement_extractor_node.validation_failed_needs_review chapter_number=8
  validation_status=needs_human_review
  validation_errors=[
    "伏笔 ... 的预计回收章节 (8) 必须大于当前章节 (8)",
    "伏笔 ... 的预计回收章节 (8) 必须大于当前章节 (8)",
    "伏笔 ... 的预计回收章节 (8) 必须大于当前章节 (8)"
  ]

project_pipeline.end completed=[1, 2, 3, 4, 5, 6, 7] failed=[8] final_status=partial
```

---

## 7. 下一步

Task 121e 已创建并完成，专门处理 settlement extractor 对伏笔预计回收章节的校验/回填问题：

- 约束：不做 Prompt 调优，不降低 settlement 校验强度。
- 目标：当 LLM 输出的 `expected_resolution_chapter` 等于当前章节时，优先按数据库事实和章节上下文进行安全回填或转为当前章节内已回收事实，避免把可修复字段直接升级为人工 review 阻断。
- 验证：已完成聚焦测试；下一步重跑 Ch1-Ch150 single-run，确认 Ch8 是否解除阻断。
