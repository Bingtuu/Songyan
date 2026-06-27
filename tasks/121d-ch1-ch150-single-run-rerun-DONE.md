# Task 121d: Ch1-Ch150 Single-Run Rehearsal Rerun

> **日期**: 2026-06-21
> **类型**: V5.0 single-run 修复后验证 / V5.1 preflight
> **状态**: ✅ 完成（`partial`，Ch1-Ch7 成功，Ch8 新阻断）
> **前置**: Task 121c 已修复 rewrite fallback 后 settlement 被跳过的问题。

---

## 1. 任务边界

Task 121d 只做修复后的 Ch1-Ch150 single-run rehearsal 重跑，不做 Prompt 调优，不新增 workflow 节点，不调整 QG 阈值。

本任务用于验证 Task 121c 是否解除 Task 121b 暴露的 Ch5 settlement skip 阻断，并继续发现下一处真实长跑瓶颈。

---

## 2. 前置清理

- 未发现 `python` / `pytest` / `songyan` 残留进程。
- 已清理 pytest/ruff 缓存、Python `__pycache__` 和旧 WAL/SHM 文件。
- `songyan.db` 只读检查结果：`integrity_check=ok`，`quick_check=ok`。
- 保留 Task 121b 的 `run-21ff158b` 作为历史证据。

---

## 3. 执行结果

| 项 | 值 |
|----|----|
| project_id | `929dcc026aee480282c227dbd0522731` |
| run_id | `run-f749826e` |
| 章节范围 | Ch1-Ch150 |
| 实际完成 | Ch1-Ch7 成功，Ch8 失败 |
| JSONL | `logs/chapter_runs/run-f749826e.jsonl` |
| report | `logs/reports/report-run-f749826e.md` |

关键结论：

- Task 121b 暴露的 Ch5 settlement skip 阻断已解除。
- Ch1-Ch7 均成功，JSONL 中均为 `settlement_success=true`、`summary_success=true`、`skip_settlement=false`。
- Ch8 是新的首个失败点，失败节点为 `settlement_review`，原因为伏笔 `expected_resolution_chapter` 等于当前章节 8。
- 该问题由 Task 121e 修复并完成验证。

Ch8 关键日志：

```text
rewrite.struct_integrity_rollback_decision chapter_number=8
  rollback_source=active_best rollback_version_id=rev-8-3-2160c17c
  recovered_with_qg_pass=True skip_settlement=False

settlement_extractor_node.validation_failed_needs_review chapter_number=8
  validation_status=needs_human_review
  validation_errors=[
    "伏笔 ... 的预计回收章节 (8) 必须大于当前章节 (8)",
    ...
  ]

project_pipeline.end completed=[1, 2, 3, 4, 5, 6, 7] failed=[8] final_status=partial
```

---

## 4. 交付物

- 运行日志：`logs/chapter_runs/run-f749826e.jsonl`、`logs/reports/report-run-f749826e.md`
- 后续修复：Task 121e 已完成 Ch8 settlement 伏笔校验阻断修复。
