# Task 131: 任务文档归档与状态一致性清理

> **类型**: 工程清理 / 文档维护  
> **日期**: 2026-06-27  
> **前置**: Task 120–130 已完成  
> **状态**: ✅ 完成

---

## 1. 目标

消除 `tasks/` 目录中过时规划稿与 `-DONE.md` 交付证据并存的状态混乱，确保 `docs/INDEX.md`、`docs/STATUS.md`、`tasks/V5-README.md`、`README.md` 指向正确的最终事实文档。

---

## 2. 清理原则

- **最终事实优先**：凡是有 `-DONE.md` 的任务，以 `-DONE.md` 为唯一最终状态依据。
- **规划稿归档**：已完成任务的历史规划稿统一移入 `archive/tasks/`（部分 V5.0 收口任务规划稿已在 `archive/v5/plans/`），避免与活跃任务混淆。
- **索引只指向最终文档**：`docs/INDEX.md`、`docs/STATUS.md`、`tasks/V5-README.md` 中的任务链接优先指向 `-DONE.md`。
- **不做无根据的状态修改**：不凭空把规划稿改成 DONE，不删除尚未完成的活跃规划稿。

---

## 3. 已归档的历史规划稿

以下非 `-DONE.md` 规划稿已使用 `git mv` 移入 `archive/tasks/`，保留 Git 历史：

- `074-dialogue-quality-specialist.md`
- `075-checkpointer-abstraction.md`
- `076-writer-forced-truncation.md`
- `077a-layered-setting-library.md`
- `077b-budget-hard-enforcement.md`
- `077c-review-fixes.md`
- `078-foreshadowing-lifecycle.md`
- `079-revision-handler-restructuring.md`
- `080-character-appearance-window.md`
- `081-ch51-ch70-validation.md`
- `083-lifecycle-schema-scheduler.md`
- `084-setting-foreshadowing-lifecycle.md`
- `085-character-mark-lifecycle.md`
- `086-dynamic-budget.md`
- `087-phase-a-e2e-validation.md`
- `088-revision-word-limit.md`
- `089-writer-truncation-tighten.md`
- `090a-phase-b-ch1-ch20-e2e.md`
- `090b-rewrite-word-count-guardrail.md`
- `091-phase-b-ch21-ch50-e2e.md`
- `092-writer-scene-budget.md`
- `094-health-score-settlement-fixes.md`
- `095-scene-structure-protection.md`
- `096-ch2-ch50-regression.md`
- `098-context-pressure-gauge.md`
- `099-ch71-ch100-extension.md`
- `100a-revision-handler-floor-protection.md`
- `100b-quality-gate-and-edit-audit.md`
- `100c-context-pressure-optimization.md`
- `101-temporal-compressor.md`
- `102-character-focal-decay.md`
- `103-setting-evaporator.md`
- `104-budget-hard-ceiling.md`
- `105-ch51-ch100-streaming-validation.md`
- `106-unified-scoring-system.md`
- `110a-character-state-tiered-compression.md`
- `110b-setting-summary-quality-control.md`
- `110c-loading-and-pruning-strategy.md`
- `110d-ch80-ch100-validation-and-tuning.md`
- `110e-coherence-major-fix.md`
- `111a-workflow-decision-contract-fix.md`
- `111b-settlement-state-integrity-fix.md`
- `111c-context-prompt-consistency-fix.md`
- `111d-quality-gate-settlement-blockers-fix.md`
- `111e-task112-reporting-dg2-gate-fix.md`
- `111f-context-snapshot-prompt-metadata-fix.md`
- `111g-long-run-performance-containment.md`
- `112-preflight-blocker-fix.md`
- `113-ch101-convergence-settlement-blocker-fix.md`
- `121d-ch1-ch150-single-run-rerun.md`（同步新建 `-DONE.md` 交付证据）
- `122-v51-systematic-test-matrix.md`（子任务 122a–122d 已全部完成并各自有 `-DONE.md`）
- `126-small-window-enforce-validation.md`
- `128-strict-mode-fault-tolerance-and-quality-ramp.md`
- `129-enforce-mode-ch1-ch50-validation.md`
- `130-gate-mode-default-decision.md`

> 注：`121d` 原规划稿无对应 `-DONE.md`，本次按任务完成事实补全 `121d-ch1-ch150-single-run-rerun-DONE.md` 后再归档原规划稿。

---

## 4. 索引文档修正

- `docs/INDEX.md`
  - `121d` 链接由规划稿改为 `121d-ch1-ch150-single-run-rerun-DONE.md`。
  - 在“归档入口”段落明确 `archive/tasks/` 已存放历史任务规划稿，状态以 `-DONE.md` 为准。
- `tasks/V5-README.md`
  - “文档使用规则”段落新增“已归档的历史规划稿”类型，强调归档位置与状态口径。
  - `121d` 事实文档列改为 `-DONE.md`。
  - Task 131 状态更新为 ✅ 完成。
- `docs/STATUS.md`
  - 当前结论与优先级段落更新：Task 131 已完成，Task 132 执行中。
- `README.md`
  - 项目状态段落更新：Task 131 已完成，Task 132 执行中。

---

## 5. 验收标准

- [x] `tasks/` 根目录只保留：活跃未完成任务、已完成任务的 `-DONE.md`、Task 132 规划稿、V5.2 新规划稿（Task 133–135）。本任务 `-DONE.md` 作为最终交付证据，原规划稿已归档。
- [x] 历史规划稿已使用 `git mv` 移入 `archive/tasks/`。
- [x] `docs/INDEX.md` / `tasks/V5-README.md` / `docs/STATUS.md` / `README.md` 中的任务链接指向 `-DONE.md` 或活跃规划稿。
- [x] `121d` 补齐 `-DONE.md` 交付证据。

---

## 6. 回归验证

```text
python -m pytest tests/ -q
1864 passed, 2 skipped, 1 xfailed

ruff check src/ tests/
All checks passed!
```

本任务未修改代码，测试与 lint 结果与 Task 130 完成时一致。

---

## 7. 交付物

- `archive/v5/tasks/131-task-docs-archive-and-status-cleanup-DONE.md`
- `archive/v5/tasks/121d-ch1-ch150-single-run-rerun-DONE.md`
- 归档至 `archive/tasks/` 的历史规划稿列表（见第 3 节）
- 更新后的 `docs/INDEX.md`
- 更新后的 `tasks/V5-README.md`
- 更新后的 `docs/STATUS.md`
- 更新后的 `README.md`
