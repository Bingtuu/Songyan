# Task 114c DONE: Ch111-Ch150 分段流式验证 + DG-2

> **Phase**: V5.0 Phase 4 — 150 章规模化验证
> **状态**: ⚠ 条件通过
> **完成日期**: 2026-06-20
> **项目**: `proj-e74ef1e4`
> **模式**: `webnovel_intense`

---

## 结论

Task 114c 已按分段方式完成 Ch111-Ch150 验证，没有一次性运行完整 40 章。最新有效指标口径下，Ch111-Ch150 共 40 章全部完成 `accept + settlement + summary`，未出现 accepted 指向 abandoned、settlement validation failed、summary 缺失或 `source_version_id` 缺失污染。

DG-2 报告结果为 **条件通过**：运行完成率、QG 通过率、budget、settlement、summary 均达标；但 Ch115、Ch120 触发过 ContextEmergency，未满足目标 0 次，需要后续复核触发分区与质量影响。

报告文件：

```text
logs/reports/report-task114c-dg2-ch111-ch150.md
```

---

## 本次修复

### 1. 单 scene 分段修订

Ch120 暴露单 scene 章节回退到整章 patch 时更容易引发截断或结构风险。本次调整 `run_segmented_revision()`：

- 没有 issue 时才返回 `segmented=False`。
- 只有 1 个 scene 但存在 issue 时，仍按 scene-scoped patch 执行。
- 保留原有内容保留率守卫，避免整章重写式漂移。

### 2. rewrite 结构失败回滚

Phase 2/3 中多次出现 rewrite 结构失败或修订反弹。本次补强 `rewrite_node()`：

- 优先回滚到 QG 合格 best version。
- 若没有 best，则回滚到 rewrite 前的 active version。
- 结构失败 rewrite 不再留在 chapter head。

### 3. best-version rollback 状态清理

`review_merger_node()` 在修订反弹并回滚 best version 时，清空上一轮残留的：

- `_new_issues_introduced`
- `_quality_gate_failures`
- `_convergence_failed`
- `_skip_settlement`
- `_settlement_needs_human_review`

避免已回滚到合格版本后仍携带旧失败状态跳过 settlement。

### 4. human gate QG 结果保持

`human_gate_node()` 在前序节点已经判定 `_quality_gate_passed=True` 时，不再因后续状态残留重新置 false，保证 QG 合格 best rollback 可以继续进入 settlement。

### 5. Settlement foreshadowing 容错

Ch136 暴露 LLM 漏填 `ForeshadowingUpdate.source_version_id` 会触发 settlement validation failed。本次调整 SettlementExtractor：

- 对缺失 `source_version_id` 的伏笔更新，用 accepted `version_id` 回填。
- 将 LLM 用 `0` / `""` 表示未知的 `expected_resolve_chapter` 规范化为 `None`，避免误触发章节硬校验。

---

## 分段执行记录

| 范围 | 最新有效 Run ID | 章节 |
|------|-----------------|------|
| Phase 2 分段 | `run-21f48aae` | Ch111-Ch112 |
| Phase 2 单章补跑 | `run-b9f15045` | Ch113 |
| Phase 2 分段 | `run-42aecdd6` | Ch114-Ch115 |
| Phase 2 分段 | `run-f5566785` | Ch116-Ch119 |
| Phase 2 单章补跑 | `run-6e1fdace` | Ch120 |
| Phase 2 分段 | `run-62dffc44` | Ch121-Ch125 |
| Phase 2 单章补跑 | `run-dd53f186` | Ch126 |
| Phase 2 收口 | `run-142431c2` | Ch127-Ch130 |
| Phase 3 单章补跑 | `run-0f55c70b` | Ch131 |
| Phase 3 分段 | `run-83dba423` | Ch132-Ch135 |
| Phase 3 单章补跑 | `run-2c1a2c97` | Ch136 |
| Phase 3 收口 | `run-8e14bcf1` | Ch137-Ch150 |

最终 Ch137-Ch150 收口日志：

```text
logs/task114/songyan-114c-phase3-ch137-150-postfix-20260620-174232.out.log
logs/task114/songyan-114c-phase3-ch137-150-postfix-20260620-174232.err.log
logs/chapter_runs/run-8e14bcf1.jsonl
```

该段业务日志显示：

```text
project_pipeline.end completed=[137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150] failed=[] final_status=completed run_id=run-8e14bcf1
运行完成: 14/14 章成功
```

外层 wrapper 在业务完成后仍显示 running，已按 Windows 防卡协议复核完整完成日志、确认无残留 `python/pytest/songyan` 进程后停止；该情况记录为外层进程退出异常，不影响业务结果判定。

---

## DG-2 指标

| 指标 | 结果 |
|------|------|
| 章节范围 | Ch111-Ch150 |
| 总章节数 | 40 |
| 成功章节 | 40/40 |
| QG 通过率 | 40/40 |
| settlement 成功 | 40/40 |
| summary 成功 | 40/40 |
| `convergence_failed` | 0 |
| `skip_settlement` | 0 |
| `llm_audit_critical` | 0 |
| 平均 `budget_used` | 0.784 |
| 最大 `budget_used` | 0.930 |
| `budget_used > 1.0` | 0 |
| ContextEmergency | 2 次：Ch115、Ch120 |
| 平均 revision 轮数 | 1.8 |

DB 一致性复核：

| 检查项 | 结果 |
|--------|------|
| Ch111-Ch150 `chapter_heads` 行数 | 40 |
| accepted 指向 abandoned | 0 |
| accepted 后缺 summary | 0 |
| Ch111-Ch150 新伏笔缺 `source_version_id` | 0 |

---

## 验证命令

### 聚焦测试

```bash
python -m pytest tests/test_settlement_extractor.py tests/test_079_segmented_revision.py tests/test_107_convergence_guardrail.py tests/test_108_core_nodes.py -q
```

结果：

```text
100 passed, 1 xfailed
WRAPPER_RESULT=PASS_NORMAL_EXIT
```

### Task 114c 报告

报告由 `songyan.evals.streaming_report.generate_report()` 基于 Ch111-Ch150 最新 JSONL 记录生成：

```text
logs/reports/report-task114c-dg2-ch111-ch150.md
```

报告结论：

```text
DG-2 条件通过项需复核: ContextEmergency 次数 == 0。
```

---

## 已知限制

1. **ContextEmergency 未达目标 0 次**：Ch115、Ch120 触发 emergency，但当章最终 QG、settlement、summary 均成功，且 `budget_used` 分别为 0.268、0.311。需要后续复核是合理降级还是过早触发。
2. **质量选择仍有 P1 风险**：Ch147、Ch148 曾出现 rewrite fallback 接受低于早先 best score 的版本；最终 JSONL 仍为 QG 通过且无 P0 状态污染，但后续应检查 best-version 选择策略是否过度偏向 rewrite 结果。
3. **ContinuityAuditor health 低分仍持续出现**：多个章节记录 `continuity.health_low`，当前只写 human marks，不阻断 accept；这属于 V5.1 质量/一致性复核范围。
4. **报告入口文档漂移**：任务文档仍提到 `scripts/generate_streaming_report.py`，实际报告实现位于 `src/songyan/evals/streaming_report.py`。

---

## 变更文件

- `src/songyan/agents/revision_handler/_segmented_revision.py`
- `src/songyan/agents/settlement_extractor/__init__.py`
- `src/songyan/workflows/_nodes.py`
- `tests/test_079_segmented_revision.py`
- `tests/test_107_convergence_guardrail.py`
- `tests/test_108_core_nodes.py`
- `tests/test_settlement_extractor.py`
- `logs/reports/report-task114c-dg2-ch111-ch150.md`
- `tasks/114-ch101-ch150-streaming-validation-DONE.md`
- `docs/STATUS.md`
- `README.md`
- `docs/INDEX.md`

---

## 下一步

建议进入 Task 115：复核 Ch115/Ch120 ContextEmergency 触发原因，并处理 Ch147/Ch148 best-version 质量选择风险。当前无需拆 P0 修复任务，因 Task 114c 没有发现长期事实源污染、settlement 半提交或 accepted 指向 abandoned。
