# V5.0 Task 总索引

> **阶段**: Context Diet 2.0 — 智能遗忘架构
> **当前口径**: **V5.0 完成** — Task 115-120 全部收口，P0/P1 风险为 0；Task 121a-121f 已统一划分，Task 121f 已修复 Ch18 CreativeDirector JSON parse failure 状态污染阻断
> **最后整理**: 2026-06-21

本文是 V5 阶段任务文档的事实入口。历史规划稿保留用于追溯设计边界；最终状态以本文件和各 `*-DONE.md` 为准。

---

## 总结论

V5.0 已完成从 Context Diet 2.0 核心组件到 150 章验证的全部主线和收口工作。

- **Context Diet 2.0 四组件已落地**：TemporalCompressor、CharacterFocalDecay、SettingEvaporator、BudgetHardCeiling。
- **Ch51-Ch100 流式验证基础设施已完成**；DG-1 因 QG 通过率 58.0% 未通过，后续通过 Task 106-110e 收敛。
- **Task 111a-111g、112、113、114a、114b2** 修复了工作流、事实源、报告、QG、settlement 和长跑性能阻断项。
- **Task 114c** 分段完成 Ch111-Ch150：40/40 成功，QG/settlement/summary 均 40/40。
- **Task 115-120 完成 V5.0 收口**：DG-2 条件通过风险关闭（P1→✅）、ContinuityAuditor health_low 分级策略落地（软复核）、报告入口统一、wrapper 加固。
- **V5.0 最终结论：P0/P1 风险为 0，全量回归 1722 passed，lint 通过。**
- **Task 121a 已完成规划判断**：V5.0 工程验收通过，但严格 single-run 证据需补强。
- **Task 121b 已补测 single-run rehearsal**：`run-21ff158b` 从 Ch1 开始，Ch1-Ch4 成功，Ch5 阻断，未达成 Ch1-Ch150 single-run。
- **Task 121c 已修复直接阻断**：rewrite fallback 回退到可结算版本后不再错误透传 `_skip_settlement=True`。
- **Task 121d 已执行重跑**：`run-f749826e` 使用新干净项目，Ch1-Ch7 成功，Ch8 `settlement_review` 阻断；Task 121c 修复已验证，Ch5 阻断解除。
- **Task 121e 已修复 Ch8 直接阻断**：同章 `expected_resolve_chapter` 自动回填到下一章，早于当前章节仍保持硬校验。
- **Task 121e 重跑验证**：`run-0317a247` Ch1-Ch17 成功，Ch18 新阻断；Ch8 已验证解除，ContextEmergency 次数为 0。
- **Task 121f 已修复 Ch18 直接阻断**：终态完成后，前置 CreativeDirector JSON parse failure 残留 error 不再污染章节成功判定。

---

## 文档使用规则

| 类型 | 用途 | 状态口径 |
|------|------|----------|
| `tasks/V5-README.md` | V5 总索引和当前事实入口 | 最高优先级 |
| `*-DONE.md` | 单任务交付证据 | 最终状态依据 |
| 无 `DONE` 的规划稿 | 任务边界、设计背景 | 不作为最终状态依据 |
| `114b` 熔断记录 | 失败/复核证据 | 已被 114b2 覆盖 |
| `114` umbrella | 114a/114b/114b2/114c 分段执行边界 | 以 114c DONE 为最终结果 |

---

## V5 任务状态

| Task | 名称 | 最终状态 | 事实文档 |
|------|------|:--------:|----------|
| 101 | TemporalCompressor | ✅ 完成 | `101-temporal-compressor-DONE.md` |
| 102 | CharacterFocalDecay | ✅ 完成 | `102-character-focal-decay-DONE.md` |
| 103 | SettingEvaporator | ✅ 完成 | `103-setting-evaporator-DONE.md` |
| 104 | BudgetHardCeiling | ✅ 完成 | `104-budget-hard-ceiling-DONE.md` |
| 105 | Ch51-Ch100 流式验证基础设施 | ✅ 完成 | `105-ch51-ch100-streaming-validation-DONE.md` |
| 105b | Ch51-Ch100 验证重启 | ✅ 完成，DG-1 未通过 | `105b-ch51-ch100-validation-restart-DONE.md` |
| 106 | Unified Scoring System | ✅ 完成 | `106-unified-scoring-system-DONE.md` |
| 107 | 收敛护栏与 150-blockers 修复 | ✅ 完成 | `107-repair-convergence-guardrail-DONE.md` |
| 108 | CharacterLifecycleAuditor | ✅ 完成 | `108-character-lifecycle-auditor-DONE.md` |
| 109 | SettingDeduplication + ForeshadowingPressure | ✅ 完成 | `109-setting-dedup-and-foreshadowing-pressure-DONE.md` |
| 110a | CharacterState 分层保真压缩 | ✅ 完成，效果有限 | `110a-character-state-tiered-compression-DONE.md` |
| 110b | Setting/Summary/HardConstraint 质量控制 | ✅ 完成 | `110b-setting-summary-quality-control-DONE.md` |
| 110c | 加载与裁剪优化 | ✅ 完成 | `110c-loading-and-pruning-strategy-DONE.md` |
| 110d | Ch80-Ch100 快速验证与调优 | ✅ 完成，调参无正收益 | `110d-ch80-ch100-validation-and-tuning-DONE.md` |
| 110e | coherence_major 根因修复 | ✅ 完成 | `110e-coherence-major-fix-DONE.md` |
| 111a | 工作流决策契约修复 | ✅ 完成 | `111a-workflow-decision-contract-fix-DONE.md` |
| 111b | Settlement 与事实源一致性修复 | ✅ 完成 | `111b-settlement-state-integrity-fix-DONE.md` |
| 111c | Context 与 Prompt 一致性修复 | ✅ 完成 | `111c-context-prompt-consistency-fix-DONE.md` |
| 111d | QualityGate 与 Settlement 阻断项修复 | ✅ 完成 | `111d-quality-gate-settlement-blockers-fix-DONE.md` |
| 111e | Task 112 报告与 DG-2 Gate 修复 | ✅ 完成 | `111e-task112-reporting-dg2-gate-fix-DONE.md` |
| 111f | Context Snapshot、Prompt 与 Metadata 修复 | ✅ 完成 | `111f-context-snapshot-prompt-metadata-fix-DONE.md` |
| 111g | 长跑性能缺陷收敛 | ✅ 完成 | `111g-long-run-performance-containment-DONE.md` |
| 112 | Task 114 前置阻断修复 | ✅ 完成 | `112-preflight-blocker-fix-DONE.md` |
| 113 | Ch101 收敛回滚与 Settlement 阻断修复 | ✅ 完成 | `113-ch101-convergence-settlement-blocker-fix-DONE.md` |
| 114a | Settlement 事实源契约修复 | ✅ 完成 | `114a-settlement-fact-source-contract-fix-DONE.md` |
| 114b | Phase 1 重跑 Ch102-Ch110 | ⚠️ 熔断复核完成，未达出口 | `114b-phase1-replay-ch102-ch110-DONE.md` |
| 114b2 | QG 收敛阻断处理 + settlement 验证窗口 | ✅ 完成 | `114b2-qg-convergence-settlement-window-DONE.md` |
| 114c | Ch111-Ch150 分段流式验证 + DG-2 | ⚠️ 条件通过，风险已关闭 | `114-ch101-ch150-streaming-validation-DONE.md` |
| 115 | ContextEmergency 触发复核与校准 | ✅ 完成 | `115-context-emergency-review-DONE.md` |
| 116 | Best-Version 质量选择策略复核与修复 | ✅ 完成 | `116-best-version-quality-selection-fix-DONE.md` |
| 117 | DG-2 风险章节窗口复验 | ✅ 完成 | `117-dg2-risk-window-revalidation-DONE.md` |
| 118 | ContinuityAuditor Health 低分治理策略 | ✅ 完成 | `118-continuity-health-governance-DONE.md` |
| 119 | 长跑报告入口与 Windows Wrapper 加固 | ✅ 完成 | `119-reporting-wrapper-hardening-DONE.md` |
| 120 | V5.0 Final Acceptance Package | ✅ 完成 | `120-v5-final-acceptance-DONE.md` |
| 121a | V5.0 目标评估与 V5.1 下一步规划 | ✅ 完成 | `121a-v50-goal-assessment-and-v51-plan.md` |
| 121b | Ch1-Ch150 Single-Run Rehearsal | ❌ 未通过，Ch5 阻断 | `121b-ch1-ch150-single-run-rehearsal-DONE.md` |
| 121c | Rewrite Fallback Settlement Contract | ✅ 完成 | `121c-rewrite-fallback-settlement-contract-DONE.md` |
| 121d | Ch1-Ch150 Single-Run Rehearsal Rerun | ❌ 未通过，Ch8 新阻断 | `121d-ch1-ch150-single-run-rerun.md` |
| 121e | Ch8 Settlement Foreshadowing Validation Fix | ✅ 完成，重跑到 Ch18 新阻断 | `121e-ch8-settlement-foreshadowing-validation-fix-DONE.md` |
| 121f | Ch18 CreativeDirector Error Contract | ✅ 完成 | `121f-ch18-creative-director-error-contract-DONE.md` |

---

## 关键验证口径

| 验证项 | 结果 |
|--------|------|
| Ch51-Ch100 真实重启验证 | 50/50 成功，QG 29/50，DG-1 未通过 |
| Ch80-Ch96 coherence_major 修复验证 | 17/17 成功，QG 17/17，coherence_major 0/17 |
| Ch101 修复回放 | `run-90e08243` 恢复 accepted + settlement + summary |
| Ch102/Ch103 settlement 验证窗口 | `run-af3ba939` 完成 accept + settlement + summary |
| Ch111-Ch150 DG-2 | 40/40 成功，QG/settlement/summary 40/40，条件通过；Task 115-117 已关闭风险 |
| Ch1-Ch150 single-run rehearsal | `run-21ff158b`：Ch1-Ch4 成功，Ch5 阻断；`run-f749826e`：Ch1-Ch7 成功，Ch8 阻断；`run-0317a247`：Ch1-Ch17 成功，Ch18 CreativeDirector JSON parse failure 新阻断 |
| 最近全量回归 | `1722 passed, 2 xfailed, 14 warnings` |
| 当前全量 ruff | `ruff check src/ tests/` 已通过 |

测试口径说明：`2 xfailed` 为已知非阻断项（Windows SQLite 并发写入限制、冷启动 embedding model 性能 xfail）。

---

## 遗留项（已关闭或 V5.1 范围）

| 风险 | 严重级别 | 状态 |
|------|----------|------|
| Ch115/Ch120 ContextEmergency 触发原因 | ~~P1~~ | **Task 115 已关闭**：诊断为合理降级（`budget_used` 触发时 1.0007），新增可观测性字段 |
| Ch147/Ch148 best-version 质量选择策略 | ~~P1~~ | **Task 116 已关闭**：`quality_gate_router` 路由缺陷修复，QG 通过后不再错误触发 rewrite |
| ContinuityAuditor health 低分只写 human marks、不阻断 accept | ~~P2~~ | **Task 118 已关闭**：软复核策略（health_low 追踪但不断路），V5.1 可扩展为硬门禁 |
| 一次性 Ch1-Ch150 单命令证据 | P1 | **Task 121e 重跑已越过 Ch8；Task 121f 已修复 Ch18 CreativeDirector JSON parse failure 状态污染阻断**，需重跑 single-run |

---

## V5.0 收口任务完成记录

Task 115-120 用于 V5.0 条件通过后的收口，不改变 Task 114c 已完成的事实口径。

| Task | 优先级 | 目标 | 状态 |
|------|--------|------|------|
| 115 | P1 | 复核 Ch115/Ch120 ContextEmergency，判断合理降级、过早触发或报告误判 | ✅ 完成（合理降级 + `budget_used_before_emergency` 字段） |
| 116 | P1 | 修复 Ch147/Ch148 best-version 质量选择风险，防止低分 fallback 覆盖高分 QG best | ✅ 完成（`quality_gate_router` 路由修复） |
| 117 | P1 | 复跑 DG-2 风险章节窗口，验证 115/116 修复结果 | ✅ 完成（4/4 成功，DG-2 条件通过但风险关闭） |
| 118 | P2 | 明确 ContinuityAuditor health_low 的记录、软复核或阻断策略 | ✅ 完成（health_low P1/P2/P3 分级，软复核） |
| 119 | P2 | 统一长跑报告入口并加固 Windows wrapper 退出判定 | ✅ 完成（songyan report CLI，6 种 WRAPPER_RESULT 结果码） |
| 120 | P2 | 汇总 V5.0 最终验收包，给出最终通过/条件通过/不通过结论 | ✅ 完成 |

---

## 清理结论

- Task 113 已补齐 DONE 文档，避免 `STATUS/INDEX` 指向规划稿却声称完成。
- `114b` 明确标记为失败/熔断复核记录，不再作为 Task 114 成功依据。
- `114b2` 是 Ch102/Ch103 settlement 端到端恢复依据。
- `114c DONE` 是 Ch111-Ch150 与 DG-2 的最终依据。
- Task 114、114b、115-120 的历史规划稿已移入 `archive/v5/plans/`，旧 `run_task117.ps1` 已移入 `archive/v5/scripts/`。
- 后续新增 V5 文档应优先更新本索引，再更新 `docs/STATUS.md`、`README.md`、`docs/INDEX.md`。
