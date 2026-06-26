# Task 121j: Ch1-Ch150 Single-Run After Ch115 Fix

> **日期**: 2026-06-22
> **类型**: V5.1 preflight / full single-run evidence
> **状态**: DONE / partial
> **前置**: Task 121i 已验证 Ch115 聚焦运行通过 settlement 和 summary。

---

## 1. 任务边界

本任务目标是在 Task 121h/121i 修复与聚焦验证通过后，重新执行一次干净的 Ch1-Ch150 full single-run，取得单一 `run_id` 的连续证据链。

本任务聚焦：

- 使用新的干净项目或明确隔离状态执行 Ch1-Ch150。
- 输出完整 JSONL、wrapper stdout/stderr/result、`songyan report` 报告。
- 判断是否达成 150/150。
- 若未达成，记录首个真实阻断点，不包装 partial 结果。

不做：

- 不在 full run 中途人工介入。
- 不复用 `run-0fd1456e` partial 结果。
- 不在本任务中改 Prompt 或 workflow。
- 不把分段成功证据当作 single-run 完成证据。

---

## 2. 前置清理

执行前必须记录：

- 无残留 `python` / `pytest` / `songyan` 长跑进程。
- SQLite integrity check 为 `ok`。
- 旧 WAL/SHM 已清理或确认安全。
- `__pycache__`、可安全缓存已清理。
- 历史日志已归档或不会覆盖。

---

## 3. 运行要求

| 项 | 要求 |
|----|------|
| run_id | 必须新生成 |
| project_id | 必须新建或明确隔离 |
| 章节范围 | Ch1-Ch150 |
| mode | `webnovel_intense` |
| genre | `scifi` |
| wrapper timeout | 建议不低于 86400 秒 |
| 自动确认 | 允许，但不得绕过 human review 阻断 |

---

## 4. 观测指标

每章必须记录：

- `success`
- `error_stage`
- `quality_gate_passed`
- `convergence_failed`
- `skip_settlement`
- `settlement_success`
- `summary_success`
- `word_count`
- `score_card`
- `budget_used`
- `context_emergency`
- `continuity_health_score`

额外关注：

- 是否再次经过 Ch115。
- 是否出现新的首个阻断章节。
- QG false 是否集中出现在某个窗口。
- rewrite / hard truncate 是否再次覆盖高分 best。

---

## 5. 验收标准

### 完成口径

若满足以下条件，Task 121j 可判定为 single-run 证据达成：

- 单一 `run_id` 覆盖 Ch1-Ch150。
- 150/150 `success=true`。
- 每章均有 accepted/current 版本。
- 每章均完成 settlement 和 summary。
- wrapper result 为成功口径。
- 生成完整 `songyan report`。

### 未完成口径

若运行中断或 partial：

- 不得声称 Ch1-Ch150 已完成。
- 必须记录 completed / failed / first_failed_chapter。
- 必须定位首个真实阻断阶段。
- 必须输出下一步任务建议。

---

## 6. 后续

- 若 150/150 完成，更新 `docs/STATUS.md`、`tasks/V5-README.md`、`README.md`、`docs/INDEX.md`，并关闭 single-run P1 遗留项。
- 若出现新的工程阻断，创建下一个 Task 121 子任务聚焦修复。
- 若工程链路通过但质量问题明显，进入 Task 121k 或 V5.1 Prompt 调优。

---

## 7. 完成记录

Task 121j 已执行，结论为 **partial，未达成 Ch1-Ch150 single-run 完成证据**。

本次有效推进：

- 使用新建干净项目执行，未复用 `run-0fd1456e` 或 `run-ce1767ff`。
- 新 `run_id` 覆盖 Ch1-Ch13，Ch1-Ch13 均 success / settlement / summary / QG 通过。
- 已越过历史 Ch5 和 Ch8 阻断点。
- 未到达 Ch18 或 Ch115。
- 首个新阻断为 Ch13 后 `AutoHaltException`：Ch11-Ch13 连续 3 章触发 `ContextEmergency`。

运行配置：

| 项 | 值 |
|----|----|
| project_id | `fe44a161b8f94111800b6b0273046f32` |
| run_id | `run-b063b6f0` |
| task tag | `task121j` / `ch1-ch150-after-ch115-fix` |
| mode | `webnovel_intense` |
| genre | `scifi` |
| 章节范围 | Ch1-Ch150 |
| wrapper timeout | `86400` 秒 |

证据路径：

- JSONL: `logs/chapter_runs/run-b063b6f0.jsonl`
- wrapper stdout: `logs/task121j/songyan-task121j-ch1-ch150-after-ch115-fix-20260622-113801.out.log`
- wrapper stderr: `logs/task121j/songyan-task121j-ch1-ch150-after-ch115-fix-20260622-113801.err.log`
- wrapper meta: `logs/task121j/songyan-task121j-ch1-ch150-after-ch115-fix-20260622-113801.meta.txt`
- report: `logs/reports/report-run-b063b6f0.md`

说明：CLI 在 Ch13 后抛出 `AutoHaltException`，但进程未自然退出，wrapper 未写出 `.result.txt`。确认业务状态已为 `paused` 且不会继续推进后，手动停止残留进程。该操作不改变业务结论。

关键错误：

```text
songyan.exceptions.AutoHaltException: 连续 3 章触发 ContextEmergency（Ch11-Ch13）
```

DB 状态：

```text
project_runs.status = paused
current_chapter = 13
completed_chapters = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
failed_chapters = []

chapter_heads: count=13, max_chapter=13
accepted chapter_heads: 13
```

JSONL 汇总：

| 指标 | 值 |
|------|----|
| logged chapters | 13 |
| success | 13 |
| failed | 0 |
| settlement_fail | 0 |
| summary_fail | 0 |
| qg_false | 0 |
| context_emergency | 4 |
| ContextEmergency chapters | `[8, 11, 12, 13]` |
| avg overall | 0.8037 |
| min overall | 0.6861 |

最近章节窗口：

| Ch | Success | QG | Settlement | Summary | Word Count | Overall | ContextEmergency |
|----|---------|----|------------|---------|------------|---------|------------------|
| 9 | true | true | true | true | 3834 | 0.6882 | false |
| 10 | true | true | true | true | 3827 | 0.8076 | false |
| 11 | true | true | true | true | 3252 | 0.8700 | true |
| 12 | true | true | true | true | 2927 | 0.8433 | true |
| 13 | true | true | true | true | 3220 | 0.8714 | true |

结论：

- Task 121j 未达成 Ch1-Ch150 150/150 single-run 证据。
- Ch5 / Ch8 历史阻断点已在新 full-run 中越过。
- 新首个阻断为 ContextEmergency 自动熔断，不是 quality gate、settlement、summary 或 human review。
- 后续应创建 Task 121l，聚焦连续 ContextEmergency / AutoHalt 策略与 Context Diet 触发阈值，而不是继续修改 Ch115 quality gate。
