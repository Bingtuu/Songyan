# Task 121i: Ch115 Focused Rerun and Quality Window Review

> **日期**: 2026-06-22
> **类型**: V5.1 preflight / focused verification
> **状态**: DONE
> **前置**: Task 121h 完成 Ch115 quality gate / best-version rewrite 契约修复。

---

## 1. 任务边界

本任务只验证 Task 121h 的修复是否真实解除 Ch115 阻断，并复核 Ch111-Ch115 质量窗口是否出现新的工程风险。

本任务聚焦：

- 使用隔离项目或明确隔离状态聚焦重跑 Ch115。
- 验证 Ch115 不再因 stale `_new_issues_introduced` 或低质量 rewrite 覆盖 best 而进入 `human_review_required`。
- 复核 Ch111-Ch115 的质量趋势、版本选择和 settlement/summary 完整性。
- 输出可作为 Task 121j full single-run 前置证据的报告。

不做：

- 不修改 Prompt。
- 不调整 QualityGate 阈值。
- 不执行 Ch1-Ch150 full single-run；该步骤归 Task 121j。
- 不把聚焦验证结果包装为 Ch1-Ch150 完成证据。

---

## 2. 输入与前置条件

| 项 | 要求 |
|----|------|
| Task 121h | 已完成，测试通过 |
| 数据库 | 可使用新隔离项目，或明确记录复用状态与清理方式 |
| 目标章节 | Ch115，必要时包含 Ch111-Ch115 窗口 |
| 事实源 | SQLite `songyan.db` |
| 历史参考 | `run-0fd1456e`、`logs/chapter_runs/run-0fd1456e.jsonl` |

---

## 3. 验证重点

### 3.1 Ch115 阻断解除

必须确认：

- `success=true`
- `error_stage=null`
- `settlement_success=true`
- `summary_success=true`
- `skip_settlement=false`
- `settlement_needs_human_review=false`
- 未因 stale `_new_issues_introduced` 进入 `human_review_required`

### 3.2 best-version 保护生效

必须确认：

- 如果存在高分 best version，低质量 rewrite / hard truncate 产物不会覆盖 best。
- 如果最终 accepted/current 版本不是 rewrite 产物，需要记录 rollback 决策和原因。
- 如果最终版本仍是 rewrite 产物，需要证明它不低于 best 的质量门阈值和分数差阈值。

### 3.3 Ch111-Ch115 质量窗口

复核指标：

- `overall_score`
- `readability`
- `momentum`
- `length`
- `quality_gate_passed`
- `convergence_failed`
- `word_count`
- 短段落比例、机械场景标题、元标记泄漏

预期结论：

- Task 121i 只判断工程修复是否有效。
- 文本风格和 Prompt 问题若仍存在，记录为 Task 121k 输入。

---

## 4. 建议执行顺序

1. 清理可安全清理的缓存、旧 WAL/SHM 和残留进程。
2. 运行 Ch115 聚焦验证。
3. 生成或提取 run log、JSONL、wrapper result。
4. 查询 Ch115 `chapter_heads`、`chapter_versions`、`review_reports`，确认最终版本和 best 版本关系。
5. 抽查 Ch111-Ch115 accepted/current 正文质量。
6. 汇总验证结论。

---

## 5. 验收标准

本任务完成需满足：

- Ch115 聚焦验证通过 settlement 和 summary。
- Ch115 版本选择证据完整，能说明 best-version 保护是否生效。
- Ch111-Ch115 质量窗口有指标摘要和缺陷归类。
- 输出新的 `run_id`、JSONL、wrapper 日志、报告路径。
- 若 Ch115 仍失败，必须明确失败是工程状态问题、真实当前版本 quality issue，还是 Prompt/文本质量问题。

---

## 6. 后续

- 若 Ch115 聚焦验证通过，进入 Task 121j 执行新的 Ch1-Ch150 full single-run。
- 若 Ch115 因工程状态问题继续失败，回到 Task 121h 修复。
- 若 Ch115 因真实文本质量问题失败，进入 Task 121k 或单独 Prompt/质量策略任务。

---

## 7. 完成记录

Task 121i 已完成。聚焦验证复用 Task 121g 项目 `7950dbf3b70c468695e5bfe528d66acf`，保留 Ch1-Ch114 的真实上下文，仅重跑 Ch115。

运行入口：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_songyan_chapter.ps1 `
  -ProjectId '7950dbf3b70c468695e5bfe528d66acf' `
  -Chapters '115-115' `
  -ModeId 'webnovel_intense' `
  -Tag 'ch115-focused' `
  -TaskName 'task121i' `
  -TimeoutSec 1800 `
  -BusinessDoneGraceSec 60
```

证据路径：

- Wrapper result: `logs/task121i/songyan-task121i-ch115-focused-20260622-111159.result.txt`
- Wrapper output: `logs/task121i/songyan-task121i-ch115-focused-20260622-111159.output.txt`
- Run JSONL: `logs/chapter_runs/run-ce1767ff.jsonl`
- Streaming report: `logs/reports/report-run-ce1767ff.md`

Wrapper 结果：

```text
WRAPPER_RESULT=PASS_BUSINESS_COMPLETED_WRAPPER_TIMEOUT
DETAIL=pipeline_end_found=true timeout=1800s business_done_timeout=True
BUSINESS_DONE_DETECTED=06/22/2026 11:18:48
PROCESS_KILLED_AFTER_BUSINESS_DONE
```

说明：业务已检测到 `project_pipeline.end`，最终 `completed=[115]`、`failed=[]`、`final_status=completed`。wrapper 在业务完成后的 grace 期终止仍未退出的进程，属于 pass 类型。

Ch115 JSONL 结果：

| 字段 | 结果 |
|------|------|
| `run_id` | `run-ce1767ff` |
| `success` | `true` |
| `error_stage` | `null` |
| `settlement_success` | `true` |
| `settlement_needs_human_review` | `false` |
| `summary_success` | `true` |
| `quality_gate_passed` | `true` |
| `convergence_failed` | `false` |
| `skip_settlement` | `false` |
| `word_count` | 4165 |
| `overall_score` | 0.7286 |
| `readability` | 0.7105 |
| `momentum` | 0.5 |
| `length` | 0.64 |
| `budget` | 1.0 |

DB head 结果：

```text
Ch115 chapter_heads.status = accepted
current_version_id = v-115-6-8c013546
accepted_version_id = v-115-6-8c013546
```

版本选择证据：

| Version | Type | Word Count | Overall | Abandoned | 说明 |
|---------|------|------------|---------|-----------|------|
| `v-115-1-e194192e` | draft | 3288 | 0.8422 | false | Task 121g 初稿 |
| `rev-115-2-b814b851` | revision | 3224 | 0.8468 | false | Task 121g revision |
| `rev-115-3-9e494dd5` | revision | 3493 | 0.8776 | false | Task 121g 高分版本 |
| `v-115-4-f6287310` | draft | 6062 | n/a | true | Task 121g rewrite 超长产物 |
| `cv-fc9d4049` | draft | 4200 | 0.7335 | false | Task 121g hard truncate 后失败版本 |
| `v-115-6-8c013546` | accepted | 4165 | 0.7286 | false | Task 121i 聚焦重跑最终 accepted |
| `rev-115-7-97a5395d` | revision | 4165 | 0.7284 | true | Task 121i revision，因低于 best 被 abandon |

Task 121i 未复现 Task 121g 的 `human_review_required` 阻断。日志关键事件：

- `human_gate.decision ... decision=accept ... quality_gate_passed=True ... settlement_needs_human_review=False ... skip_settlement=False`
- `settlement_extractor_node.contract_snapshot ... quality_gate_passed=True ... settlement_needs_human_review=False ... skip_settlement=False`
- `settlement.validation_passed`
- `settlement_extractor_node.settlement_applied`
- `summary_writer.generated`
- `project_pipeline.end ... completed=[115] ... failed=[] ... final_status=completed`

结论：

- Task 121h 的工程修复通过聚焦实跑验证：Ch115 不再因 stale `_new_issues_introduced` 或 settlement human review 状态污染阻断。
- 本次没有触发 121h 的 safe-best rewrite 回滚主路径；原因是本次聚焦重跑没有进入 rewrite，且当前运行内 best 本身 `overall=0.7286`，不满足 `overall >= 0.82` 的 safe-best 条件。
- 旧的 `rev-115-3` 高分版本仍保留在 DB 中，但本次聚焦验证选择重新生成并接受 `v-115-6-8c013546`。这证明工程阻断已解除，但不证明当前 Ch115 文本质量优于历史高分版本。

Ch111-Ch115 质量窗口：

| Ch | Run | Success | QG | Convergence | Word Count | Overall | Readability | Momentum | Length | Budget |
|----|-----|---------|----|-------------|------------|---------|-------------|----------|--------|--------|
| 111 | `run-0fd1456e` | true | false | true | 2758 | 0.6545 | 0.6900 | 0.2 | 0.58 | 1.0 |
| 112 | `run-0fd1456e` | true | true | false | 4200 | 0.7375 | 0.7700 | 0.5 | 0.60 | 1.0 |
| 113 | `run-0fd1456e` | true | true | false | 4079 | 0.8558 | 0.9440 | 0.8 | 0.72 | 0.9683 |
| 114 | `run-0fd1456e` | true | false | true | 4193 | 0.7119 | 0.4840 | 0.8 | 0.60 | 0.8586 |
| 115 | `run-ce1767ff` | true | true | false | 4165 | 0.7286 | 0.7105 | 0.5 | 0.64 | 1.0 |

Window average overall: `0.7377`。

正文质量抽查：

| Ch | 当前版本 | 段落数 | 短段落比例 | `### Scene` 标题 | HTML 标记 |
|----|----------|--------|------------|------------------|-----------|
| 111 | `rev-111-3-f9ebc7d4` | 63 | 0.556 | 1 | 0 |
| 112 | `rev-112-3-b361bab8` | 155 | 0.684 | 3 | 0 |
| 113 | `rev-113-3-ffa15439` | 129 | 0.651 | 2 | 0 |
| 114 | `rev-114-3-de330497` | 145 | 0.669 | 1 | 0 |
| 115 | `v-115-6-8c013546` | 133 | 0.639 | 1 | 0 |

质量结论：

- 工程阻断已解除，Task 121j 可以执行新的 Ch1-Ch150 full single-run。
- Ch111-Ch115 的文本质量仍偏弱，尤其短段落比例持续过高、机械 `Scene` 标题仍存在，Ch111/Ch114 的 QG false 也显示中后段质量不稳。
- 这些问题不应阻塞 Task 121j 的工程证据重跑，但必须作为 Task 121k 的 Prompt / 正文质量清理输入。
