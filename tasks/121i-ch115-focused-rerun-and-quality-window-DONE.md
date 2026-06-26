# Task 121i: Ch115 Focused Rerun and Quality Window Review — DONE

- 状态：**DONE**
- 完成日期：2026-06-26
- 原始任务：`tasks/121i-ch115-focused-rerun-and-quality-window.md`

## 目标摘要

验证 Task 121h 的工程修复是否真实解除 Ch115 阻断，并复核 Ch111-Ch115 质量窗口是否引入新的工程风险。聚焦重跑 Ch115，输出作为 Task 121j 前置证据。

## 关键交付物

- 重跑运行：`run-ce1767ff`（项目 `7950dbf3b70c468695e5bfe528d66acf`，仅重跑 Ch115）
- 最终版本：`v-115-6-8c013546`（accepted / current）
- 报告：`logs/reports/report-run-ce1767ff.md`
- JSONL：`logs/chapter_runs/run-ce1767ff.jsonl`

## 验证证据

**Ch115 结果**（`run-ce1767ff`）

- `success=true`, `error_stage=null`, `quality_gate_passed=true`
- `settlement_success=true`, `settlement_needs_human_review=false`, `summary_success=true`
- `skip_settlement=false`, `convergence_failed=false`
- `word_count=4165`, `overall_score=0.7286`, `budget_used=1.0`

**Wrapper**

```text
WRAPPER_RESULT=PASS_BUSINESS_COMPLETED_WRAPPER_TIMEOUT
completed=[115], failed=[], final_status=completed
```

**DB head**: `status=accepted`, `current_version_id=v-115-6-8c013546`, `accepted_version_id=v-115-6-8c013546`。

**版本选择**: 本次 accepted 版本 `v-115-6-8c013546`（overall 0.7286）；revision `rev-115-7` 因低于 best 被 abandon；旧高分 `rev-115-3`（0.8776）保留但未采用。safe-best 回滚主路径未触发。

**Ch111-Ch115 质量窗口**: Ch111/Ch114 QG false，Ch112/Ch113/Ch115 QG true；窗口 overall 均值 0.7377。

## 结论

- Task 121h 工程修复验证通过：Ch115 不再因 stale `_new_issues_introduced` 或 settlement human review 状态污染进入 `human_review_required`。
- 工程阻断已解除，Task 121j 可执行新的 Ch1-Ch150 full single-run。

## 遗留/后续

- Ch111-Ch115 正文质量仍偏弱：短段落比例过高、机械 `Scene` 标题仍存在、Ch111/Ch114 QG false。作为 Task 121k Prompt / 正文质量清理输入，不阻塞 Task 121j。
