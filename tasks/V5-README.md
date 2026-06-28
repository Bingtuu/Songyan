# V5.0 Task 总索引

> **阶段**: Context Diet 2.0 — 智能遗忘架构
> **当前口径**: **V5.2 进行中：Task 138d-R2 retry3 已执行；Ch11 通过 settlement/summary/QG，Ch12 因新的环境读数类 numerical_update 停在 settlement_review，尚未生成 Ch12 continuity，仍无法验证 orphan 是否低于 baseline 16** — V5.1 已收口，P0/P1 风险为 0；Task 121 系列已完成 Ch1-Ch150 full single-run 最终证据、Prompt 质量清理、测试矩阵与硬门禁预研；Task 122a/122b/122c/122d 完成动态阈值、Pipeline 集成测试、E2E 验证窗口与 150 章长序列压力测试；Task 123/124/125/126/127/128 完成 ContextEmergency / health_low 候选硬门禁提案、离线影响面分析、阈值调优、enforce 小窗口实跑验证、score halt 复合条件重构、严格模式容错/开局期质量爬坡；**Task 129 条件完成**：enforce 模式 Ch1–Ch50 验证 `run-89d7a2d4` 在 Ch15 因 quality_gate_fail_streak 暂停，暴露 Writer 结构退化、SettlementExtractor 角色/数值提取失败、orphaned settings 快速累积等底层缺陷；**Task 130 已完成**：gate_mode 默认保持 `observe`，`songyan run` 暴露 `--gate-mode` CLI 参数，`songyan report` 新增 gate 触发汇总。**Task 131 已完成**：历史规划稿已归档至 `archive/tasks/`，索引文档已指向 `-DONE.md`。**Task 132 已完成**：V5.1 最终验收包已交付，V5.1 通过（条件完成项转入 V5.2）。**Task 133/134/135 已完成**：Writer 多场景结构、SettlementExtractor 角色/数值提取、设定回收与 continuity health 治理。**Task 136 已完成 Ch1–Ch20 采集窗口实跑**：多场景 100%、旧口径 Settlement 100%、Health floor 通过，但 orphan 增长速率未减半，整体验收未通过。Task 137 保持活跃；Task 138f 已完成 numerical_update evidence gate；`run-0a48030b` 证明 Ch11 阻断解除，但 Ch12 暴露 `period/decay/depth/distance` 等有正文读数证据却未命中 telemetry/evidence gate 的新分类缺口。全量 `pytest tests/ -q` -> `1973 passed, 1 xfailed`；`ruff check src/ tests/` 通过。
> **最后整理**: 2026-06-28

本文是 V5 阶段任务文档的事实入口。历史规划稿已统一归档到 `archive/tasks/`（部分 V5.0 收口任务在 `archive/v5/plans/`），仅在追溯设计边界时查阅；最终状态以本文件和各 `*-DONE.md` 为准。

---

## 总结论

V5.0 已完成从 Context Diet 2.0 核心组件到 150 章验证的全部主线和收口工作。

- **Context Diet 2.0 四组件已落地**：TemporalCompressor、CharacterFocalDecay、SettingEvaporator、BudgetHardCeiling。
- **Ch51-Ch100 流式验证基础设施已完成**；DG-1 因 QG 通过率 58.0% 未通过，后续通过 Task 106-110e 收敛。
- **Task 111a-111g、112、113、114a、114b2** 修复了工作流、事实源、报告、QG、settlement 和长跑性能阻断项。
- **Task 114c** 分段完成 Ch111-Ch150：40/40 成功，QG/settlement/summary 均 40/40。
- **Task 115-120 完成 V5.0 收口**：DG-2 条件通过风险关闭（P1→✅）、ContinuityAuditor health_low 分级策略落地（软复核）、报告入口统一、wrapper 加固。
- **V5.0 最终结论：P0/P1 风险为 0，全量回归 1725 passed，lint 通过。**
- **Task 121a 已完成规划判断**：V5.0 工程验收通过，但严格 single-run 证据需补强。
- **Task 121b 已补测 single-run rehearsal**：`run-21ff158b` 从 Ch1 开始，Ch1-Ch4 成功，Ch5 阻断，未达成 Ch1-Ch150 single-run。
- **Task 121c 已修复直接阻断**：rewrite fallback 回退到可结算版本后不再错误透传 `_skip_settlement=True`。
- **Task 121d 已执行重跑**：`run-f749826e` 使用新干净项目，Ch1-Ch7 成功，Ch8 `settlement_review` 阻断；Task 121c 修复已验证，Ch5 阻断解除。
- **Task 121e 已修复 Ch8 直接阻断**：同章 `expected_resolve_chapter` 自动回填到下一章，早于当前章节仍保持硬校验。
- **Task 121e 重跑验证**：`run-0317a247` Ch1-Ch17 成功，Ch18 新阻断；Ch8 已验证解除，ContextEmergency 次数为 0。
- **Task 121f 已修复并验证 Ch18 直接阻断**：终态完成后，前置 CreativeDirector JSON parse failure 残留 error 不再污染章节成功判定；`run-058fb9de` Ch1-Ch18 成功，`failed=[]`。
- **Task 121g 已完成完整 single-run 重跑**：`run-0fd1456e` Ch1-Ch114 成功，Ch115 因 quality gate human review 阻断，最终 `partial`；真实瓶颈已从 Ch18 推进到 Ch115。
- **Task 121h 已完成工程修复**：rewrite 状态生命周期清理、版本化 new issues、低质量 rewrite / hard truncate 回滚到 safe best；全量 `pytest` / `ruff` 通过。
- **Task 121i 已完成聚焦验证**：`run-ce1767ff` 复用 Task 121g 项目重跑 Ch115，success / settlement / summary 均通过；Ch111-Ch115 质量窗口偏弱，输入 Task 121k。
- **Task 121j 已执行 full single-run 重跑**：`run-b063b6f0` 使用新干净项目，Ch1-Ch13 全部 success / settlement / summary / QG 通过，但 Ch13 后因 Ch11-Ch13 连续 ContextEmergency 触发 AutoHalt，最终 partial。
- **Task 121l 已完成策略修复和聚焦实跑**：`run-08689f68` 使用新 clean project，Ch1-Ch12 全部 success，失败 0；Ch10-Ch12 连续 ContextEmergency 且 Ch10 QG false，按新 `context_emergency_degraded_streak` 策略暂停，结果 partial。
- **Task 121m/121n/121o 已规划**：121m 负责 QG false 硬拦截 settlement + 元标记泄漏清理；121n 负责 Context Diet 2.0 预算增量调整（80→250）+ human_marks 生命周期窗口缩短（10→6）；121o 负责 121m/121n 完成后执行 Ch1-Ch18 聚焦验证重跑。
- **Task 121k 已拆分后置质量任务**：单独处理 Prompt / 正文质量清理。
- **Task 121m 已完成**：QG false 硬拦截 settlement + 元标记泄漏清理。
- **Task 121n 已完成**：Context Diet 2.0 预算增量 80→250 + human_marks 生命周期窗口 10→6。
- **Task 121o 已完成**：Ch1-Ch18 聚焦验证重跑，18/18 成功，ContextEmergency 0 次，AutoHalt 0 次。
- **Task 121p 已完成**：修复 pipeline 未跳过已有 accepted 章节 + RAG 索引超时异常未捕获两个 Bug；`_SAFE_BEST_MIN_OVERALL_SCORE` 动态化（Ch1-Ch20→0.75, Ch21-Ch50→0.78, Ch51+→0.82）+ `degraded_accept` 降级回滚路径。
- **Task 121q 已完成**：`run-a2bed648` Ch1-Ch150 full single-run 150/150 全部成功，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙。
- **Task 121r 已完成**：Writer 1.1.0 + CreativeDirector 1.0.5 + RuleAuditor 新增 markdown 场景标题与短段落比例检测；pytest 1764 passed。
- **Task 122a 已完成**：`_safe_best_min_score` 边界值测试 + `degraded_accept` 降级回滚路径测试。
- **Task 122b 已完成**：新增 12 个集成测试覆盖 degraded_accept 路由、safe best 保护、human_review_required gate、AutoHalt streak 逻辑；pytest 1784 passed。
- **Task 122c 已完成**：Ch1-Ch20 / Ch40-Ch50 / Ch100-Ch110 三个 E2E 窗口验证完成；Ch40-Ch50 测试补强 emergency/auto-halt 断言；Ch100-Ch110 基于 `run-a2bed648` 历史数据新增离线验证测试。

- **Task 122d 已完成**：新增 `tests/integration/test_122d_long_sequence_stability.py`，覆盖 150 章上下文预算趋势、human_marks 6 章蒸发、AutoHalt 真/假阳性、accepted 章节跳过 5 个压力场景；pytest 1784 passed；ruff 通过。
- **Task 123 已完成**：ContextEmergency / health_low 候选硬门禁实现（默认观测模式），新增 `GateConfig`、`_gates.py`、`tests/test_123_gates.py` 16 个单测。
- **Task 124 已完成**：基于 `run-a2bed648` 的候选硬门禁离线影响面分析，原始阈值触发 118/120 章；交付分析脚本、报告与 16 个单测。
- **Task 125 已完成**：候选硬门禁阈值调优，引入 P1 异常检测、health_score 相对跌幅、审计点 streak 窗口；`run-a2bed648` 上 `any_gate` 触发 0 章；新增 `tests/test_125_gate_thresholds.py` 12 个单测；全量 pytest 1828 passed。
- **Task 126 已完成**：候选硬门禁 enforce 模式 Ch1–Ch20 小窗口实跑验证；发现 `health_low_absolute_score_halt` 在新项目开局期误触发，禁用后 Ch1–Ch19 零 gate 触发，Ch20 因既有 QG false block 失败；交付 `scripts/run_126_enforce_validation.py`。
- **Task 127 已完成**：候选硬门禁 score halt 条件重构，将绝对分单条件改为“P1 异常 & (相对跌幅 | streak 窗口)”复合条件；Ch1–Ch19 enforce 小窗口零 gate 触发；pytest 1842 passed。
- **Task 128 已完成**：严格模式容错与开局期质量爬坡； settlement 对 QG false 降级为 `degraded_accept`（Ch1–Ch10）以绕过开局期 QG 过严导致的阻断，同时用 `degraded_accept` 元标记支持后续复盘；新增 RevisionHandler readability 专项修复路径；全量 pytest 1856 passed，ruff 通过。
- **Task 129 条件完成**：enforce 模式 Ch1–Ch50 验证 `run-89d7a2d4` Ch1–Ch15 后因 quality_gate_fail_streak 暂停；报告见 `docs/reports/task-129-enforce-validation-report.md`；暴露的底层缺陷由 Task 133/134/135 跟踪。
- **Task 130 已完成**：基于 124–129 证据决定 `gate_mode` 默认保持 `observe`，`songyan run` 暴露 `--gate-mode {observe|enforce}` CLI 参数，`songyan report` 新增候选硬门禁触发汇总。
- **Task 131 已完成**：历史规划稿已归档至 `archive/tasks/`，索引文档已指向 `-DONE.md`。
- **Task 132 已完成**：V5.1 最终验收包已交付，V5.1 通过（条件完成项转入 V5.2）。
- **Task 133 已完成**：Writer 多场景结构输出修复（V5.2）。
- **Task 134 已完成**：SettlementExtractor 角色状态与数值台账提取修复（V5.2）。
- **Task 135 已完成**：设定回收与 continuity health 治理（V5.2）。
- **Task 136 已完成 Ch1–Ch20 采集窗口实跑验证**：验证期间临时启用 Writer 1.2.0 并恢复运行前 manifest default_version；基于 enforce profile 但关闭 health_low halt；多场景 100%、旧口径 Settlement 100%、Health floor 通过，但 orphan 增长未减半；报告见 `docs/reports/task-136-v52-enforce-ch1-ch20-validation-report.md`。
- **Task 138d-R2 retry3 已执行**：Task 137 保持活跃，不创建 `137-DONE`。`run-4fd48756` 曾完成 Ch10-Ch12，Ch12 continuity `health=3.0`、`orphaned=16`；Task 138f 已解除 `consciousness_upload_progress` 无证据数值阻断。最新 `run-0a48030b` 使用 `.tmp/task138d_r2_retry3_ch10_focus_20260628_231943.db`，Ch11 accepted 且 settlement/summary/QG 全过；Ch12 QG 通过但 settlement_review 失败，错误集中在有正文读数证据但未命中 telemetry/evidence gate 的环境读数属性（`period`/`decay`/`depth`/`distance`）。下一步先做最小分类修复，再重新副本 DB 复跑。文档见 `tasks/138d-ch10-ch12-post-fix-rerun.md`。
---

## 文档使用规则

| 类型 | 用途 | 状态口径 |
|------|------|----------|
| `tasks/V5-README.md` | V5 总索引和当前事实入口 | 最高优先级 |
| `*-DONE.md` | 单任务交付证据 | 最终状态依据 |
| 已归档的历史规划稿 | 已完成任务的设计边界追溯 | 已移入 `archive/tasks/` 或 `archive/v5/plans/`，不作为最终状态依据 |
| 无 `DONE` 的活跃规划稿 | 尚未完成的任务边界 | 不作为最终状态依据 |
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
| 121d | Ch1-Ch150 Single-Run Rehearsal Rerun | ❌ 未通过，Ch8 新阻断 | `121d-ch1-ch150-single-run-rerun-DONE.md` |
| 121e | Ch8 Settlement Foreshadowing Validation Fix | ✅ 完成，重跑到 Ch18 新阻断 | `121e-ch8-settlement-foreshadowing-validation-fix-DONE.md` |
| 121f | Ch18 CreativeDirector Error Contract | ✅ 完成，Ch1-Ch18 聚焦验证通过 | `121f-ch18-creative-director-error-contract-DONE.md` |
| 121g | Ch1-Ch150 Single-Run Rerun and Ch115 Blocker | ❌ 未通过，Ch1-Ch114 成功，Ch115 新阻断 | `121g-ch1-ch150-single-run-rerun-ch115-blocker-DONE.md` |
| 121h | Ch115 Quality Gate / Best-Version Rewrite Contract Fix | ✅ 完成 | `121h-ch115-quality-gate-rewrite-state-review-DONE.md` |
| 121i | Ch115 Focused Rerun and Quality Window Review | ✅ 完成，`run-ce1767ff` | `121i-ch115-focused-rerun-and-quality-window-DONE.md` |
| 121j | Ch1-Ch150 Single-Run After Ch115 Fix | ❌ 未通过，Ch1-Ch13 成功，Ch13 后 AutoHalt | `121j-ch1-ch150-single-run-after-ch115-fix-DONE.md` |
| 121k | Prompt Quality Cleanup Plan | ✅ 完成，规划由 Task 121r 落地 | `121k-prompt-quality-cleanup-plan-DONE.md` |
| 121l | ContextEmergency AutoHalt Review | ✅ 策略修复完成，聚焦实跑 partial | `121l-context-emergency-autohalt-review-DONE.md` |
| 121m | QG False 硬拦截 + 元标记泄漏清理 | ✅ 完成 | `121m-qg-false-block-and-meta-tag-cleanup-DONE.md` |
| 121n | Context Diet 预算与 human_marks 生命周期调整 | ✅ 完成 | `121n-context-diet-budget-and-human-marks-lifecycle-DONE.md` |
| 121o | Ch1-Ch18 聚焦验证重跑 | ✅ 完成，`run-4ff41095` 18/18 | `121o-ch1-ch18-focused-rerun-validation-DONE.md` |
| 121p | Bug A/B 修复与 RAG embedder 超时 | ✅ 完成 | `121p-ch1-ch150-single-run-rag-embedder-timeout-DONE.md` |
| 121q | Safe-Best 动态阈值 + Ch1-Ch150 full single-run | ✅ 完成，`run-a2bed648` 150/150 | `121q-safe-best-threshold-dynamic-fix-DONE.md` |
| 121r | Prompt 质量清理 | ✅ 完成，pytest 1764 passed | `121r-prompt-quality-cleanup-execution-DONE.md` |
| 122a | 动态阈值与降级回滚单测 | ✅ 完成 | `122a-unit-test-matrix-dynamic-thresholds-DONE.md` |
| 122b | Pipeline 集成测试矩阵 | ✅ 完成，pytest 1784 passed | `122b-integration-test-pipeline-scenarios-DONE.md` |
| 122c | E2E 验证窗口补全 | ✅ 完成 | `122c-e2e-validation-windows-DONE.md` |
| 122d | 150 章长序列压力测试 | ✅ 完成，pytest 1784 passed | `122d-stress-test-long-sequence-stability-DONE.md` |
| 123 | ContextEmergency / health_low 候选硬门禁提案 | ✅ 完成 | `123-context-emergency-health-low-gate-proposal-DONE.md` |
| 124 | 候选硬门禁离线影响面分析 | ✅ 完成，原始阈值触发 118/120 章 | `124-context-emergency-health-low-gate-impact-analysis-DONE.md` |
| 125 | 候选硬门禁阈值调优与验证 | ✅ 完成，`run-a2bed648` any_gate 0 章 | `125-gate-threshold-tuning-and-validation-DONE.md` |
| 126 | 候选硬门禁 enforce 小窗口实跑验证 | ✅ 完成，Ch1–Ch19 零 gate 触发 | `126-small-window-enforce-validation-DONE.md` |
| 127 | health_low score halt 复合规则重构 | ✅ 完成 | `127-health-low-score-halt-refactor-DONE.md` |
| 128 | 严格模式容错与开局期质量爬坡 | ✅ 完成 | `128-strict-mode-fault-tolerance-and-quality-ramp-DONE.md` |
| 129 | Enforce 模式 Ch1–Ch50 验证 | ⚠️ 条件完成（Ch1–Ch15 后 AutoHalt） | `129-enforce-mode-ch1-ch50-validation-DONE.md` |
| 130 | gate_mode 默认决策 | ✅ 完成 | `130-gate-mode-default-decision-DONE.md` |
| 131 | Task docs archive & status cleanup | ✅ 完成 | `131-task-docs-archive-and-status-cleanup-DONE.md` |
| 132 | V5.1 final acceptance package | ✅ 完成 | `132-v51-final-acceptance-package-DONE.md` |
| 133 | Writer 多场景结构输出修复 | ✅ 完成 | `133-writer-multi-scene-structure-fix-DONE.md` |
| 134 | SettlementExtractor 角色状态与数值台账提取修复 | ✅ 完成 | `134-settlement-character-numerical-extraction-fix-DONE.md` |
| 135 | 设定回收与 continuity health 治理 | ✅ 完成 | `135-setting-recycling-and-continuity-health-governance-DONE.md` |
| 136 | V5.2 Ch1–Ch20 采集窗口跨项目验证 | ⚠️ 已完成，验收未通过（orphan 未减半） | `136-v52-enforce-ch1-ch20-validation-DONE.md` |
| 137 | 设定回收闭环与 tracking 刷新机制 | ⚠️ 保持活跃；后续由 138a-138f 承接收口 | `137-setting-recycling-closed-loop.md` |
| 138a | 剩余 orphan 分类与证据表 | ✅ 完成 | `138a-remaining-orphan-classification.md` |
| 138b | 基于分类结果确定最小动作 | ✅ 完成 | `138b-orphan-root-cause-decision.md` |
| 138c | 剩余 orphan 最小修复 | ✅ 完成 | `138c-orphan-minimal-fix.md` |
| 138d | 修复后 Ch10-Ch12 聚焦复跑验证 | ✅ 完成 | `138d-ch10-ch12-post-fix-rerun.md` |
| 138e | 事实源同步与 Task 137 收尾判断 | ✅ 完成，Task 137 不归档 | `138e-task137-fact-sync-and-closure.md` |
| 138d-R2 | 第二轮 Ch10-Ch12 聚焦复跑验证 | ⚠️ 未完成；`run-0a48030b` Ch11 通过，Ch12 因 `period`/`decay`/`depth`/`distance` 有证据环境读数未命中 snapshot 分类停在 settlement_review | `138d-ch10-ch12-post-fix-rerun.md` |
| 138f | Settlement 数值结算证据门禁工程化修复 | ✅ 完成 | `138f-settlement-evidence-gated-numerical-extraction.md` |

---

## 关键验证口径

| 验证项 | 结果 |
|--------|------|
| Ch51-Ch100 真实重启验证 | 50/50 成功，QG 29/50，DG-1 未通过 |
| Ch80-Ch96 coherence_major 修复验证 | 17/17 成功，QG 17/17，coherence_major 0/17 |
| Ch101 修复回放 | `run-90e08243` 恢复 accepted + settlement + summary |
| Ch102/Ch103 settlement 验证窗口 | `run-af3ba939` 完成 accept + settlement + summary |
| Ch111-Ch150 DG-2 | 40/40 成功，QG/settlement/summary 40/40，条件通过；Task 115-117 已关闭风险 |
| Ch1-Ch150 single-run rehearsal | `run-21ff158b`：Ch1-Ch4 成功，Ch5 阻断；`run-f749826e`：Ch1-Ch7 成功，Ch8 阻断；`run-0317a247`：Ch1-Ch17 成功，Ch18 CreativeDirector JSON parse failure 新阻断；`run-058fb9de`：Ch1-Ch18 聚焦验证成功；`run-0fd1456e`：Ch1-Ch114 成功，Ch115 quality gate human review 阻断；`run-ce1767ff`：Ch115 聚焦验证成功；`run-b063b6f0`：Ch1-Ch13 成功，连续 ContextEmergency AutoHalt 暂停；`run-08689f68`：Task 121l 聚焦验证 Ch1-Ch12 成功，Ch10-Ch12 degraded emergency AutoHalt 暂停 |
| Ch1-Ch150 full single-run | **Task 121q `run-a2bed648`：150/150 全部成功**，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙 |
| Task 122c E2E 窗口验证 | Ch1-Ch20（`test_ch1_20_e2e.py`，20/20）；Ch40-Ch50（`test_ch41_50_validation.py`，10/10，emergency 0，auto-halt 0）；Ch100-Ch110（`test_ch100_110_from_run_log.py`，11/11，复用 `run-a2bed648`） |
| Task 122d 150 章压力测试 | `tests/integration/test_122d_long_sequence_stability.py`（5/5），覆盖 150 章 budget 趋势、human_marks 蒸发、AutoHalt 真/假阳性、accepted 章节跳过 |
| Ch115 质量复盘 | `rev-115-3` 已达 `overall=0.8776` 且字数健康，但后续 rewrite 输出 7771 字并经 hard truncate 后降至 `overall=0.7335`；Task 121h 已修状态生命周期与 best-version 保护，Task 121i 已验证 Ch115 不再 human_review_required |
| 最近全量回归 | `1864 passed, 2 skipped, 1 xfailed` |
| 当前全量 ruff | `ruff check src/ tests/ scripts/analyze_124_gate_impact.py` 已通过 |
| 候选硬门禁离线验证 | Task 124：`run-a2bed648` 原始候选阈值触发 118/120 章 |
| 候选硬门禁阈值调优 | Task 125：`run-a2bed648` 调优后 `any_gate` 触发 0 章 |
| enforce 模式 Ch1–Ch50 验证 | Task 129：`run-89d7a2d4` Ch1–Ch15 成功，Ch15 后因 quality_gate_fail_streak 暂停；报告见 `docs/reports/task-129-enforce-validation-report.md` |

测试口径说明：`1 xfailed` 为已知非阻断项，`0 xpassed`；2 warnings 均为既有 pytest/依赖警告。

---

## 遗留项（已关闭或 V5.1 范围）

| 风险 | 严重级别 | 状态 |
|------|----------|------|
| Ch115/Ch120 ContextEmergency 触发原因 | ~~P1~~ | **Task 115 已关闭**：诊断为合理降级（`budget_used` 触发时 1.0007），新增可观测性字段 |
| Ch147/Ch148 best-version 质量选择策略 | ~~P1~~ | **Task 116 已关闭**：`quality_gate_router` 路由缺陷修复，QG 通过后不再错误触发 rewrite |
| ContinuityAuditor health 低分只写 human marks、不阻断 accept | ~~P2~~ | **Task 118/123/124/125/126/127 已关闭**：health_low 软复核 + 候选硬门禁实现 + 离线影响面分析 + 阈值调优 + enforce 小窗口验证 + score halt 复合条件重构；`run-a2bed648` 与 Ch1–Ch19 小窗口上 `any_gate` 触发 0 章，默认仍 `gate_mode="observe"`。**Task 129 条件完成**，暴露的底层缺陷由 Task 133/134/135 跟踪 |
| 一次性 Ch1-Ch150 单命令证据 | ~~P1~~ | **Task 121q `run-a2bed648` 已完成**：Ch1-Ch150 150/150 全部成功，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙 |
| enforce 模式默认启用 | V5.2 | **被 Task 133/134/135 阻塞**：需先修复 Writer 多场景结构、SettlementExtractor 角色/数值提取、设定回收与 continuity health 缺陷，再完成跨项目 Ch1–Ch150 enforce 验证 |
| 连续 ContextEmergency AutoHalt | ~~P1~~ | **已解除**：Task 121l 策略修复 + Task 121m QG false 硬拦截 + Task 121n 预算调整；Task 121o `run-4ff41095` 验证 Ch1-Ch18 0 次 emergency、0 次 AutoHalt |
| Ch115 rewrite / best-version 劣化 | P1 | **Task 121h 已完成工程修复，Task 121i `run-ce1767ff` 已验证 Ch115 聚焦重跑成功**；safe-best 回滚主路径由单测覆盖，本次实跑未触发 rewrite |
| QG false 版本进入 settlement | ~~P1~~ | **Task 121m 已完成**：settlement_extractor_node 入口增加 QG false 硬拦截 |
| 开局期 QG false 在 enforce 模式下阻断后续章节 | ~~P1~~ | **Task 128 已完成**：Ch1–Ch10 QG false 触发 `degraded_accept` 标记但不阻断 settlement，RevisionHandler readability 专项修复增强开局期正文质量；明确标注为“流程绕过”而非“质量修复” |
| 元标记泄漏（`<!-- 新设定 -->`） | ~~P1~~ | **Task 121m 已完成**：清理 writer prompt 中的 HTML 注释指令，后处理强制过滤 |
| 正文纯净度与段落节奏 | V5.1 | Task 121k 处理：机械场景标题、短段落碎片化、说明文堆叠 |

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
- Task 121g 已补齐 DONE 文档，明确 `run-0fd1456e` 不能作为 Ch1-Ch150 完成证据，但可作为 Ch115 首个真实阻断证据。
- Task 121h-121r 已全部完成；Task 122a-122d 测试矩阵已完成；Task 123-130 候选硬门禁预研、严格模式容错与 gate_mode 默认决策已完成，`run-a2bed648` 与 Ch1–Ch19 小窗口上 `any_gate` 触发 0 章；pytest `1864 passed, 2 skipped, 1 xfailed`。
- **Task 129 条件完成**：enforce 模式 Ch1–Ch50 验证 `run-89d7a2d4` 在 Ch15 因 quality gate streak 暂停，暴露 Writer 多场景结构退化、SettlementExtractor 角色/数值提取失败、orphaned settings 快速累积等缺陷，由 Task 133/134/135 跟踪修复。
- **Task 130 已完成**：gate_mode 默认保持 `observe`，`songyan run` 暴露 `--gate-mode` CLI 参数，`songyan report` 新增 gate 触发汇总。
- **Task 131 已完成**：历史规划稿已归档至 `archive/tasks/`，索引文档已指向 `-DONE.md`。
- **Task 133/134/135 已完成代码与测试**：V5.2 底层缺陷修复已落地；Task 138f 完成后最新全量 pytest `1973 passed, 1 xfailed`。
- **Task 136 已完成 Ch1–Ch20 采集窗口实跑验证**：验证期间临时启用 Writer 1.2.0 并恢复运行前 manifest default_version；基于 enforce profile 但关闭 health_low halt；多场景 100%、旧口径 Settlement 100%、Health floor 通过，但 orphan 增长速率未减半（Ch12-Ch15 高于 Ch9-Ch12），整体验收未通过；报告见 `docs/reports/task-136-v52-enforce-ch1-ch20-validation-report.md`。
- **Task 138d-R2 retry3 已执行**：Task 137 保持活跃，不创建 `137-DONE`。`run-0a48030b` 使用新副本 DB 复跑 Ch10-Ch12，Ch11 accepted 且 settlement/summary/QG 全过；Ch12 QG 通过但 settlement_review 失败，尚未生成 continuity，无法比较 orphan baseline 16。最新阻断是有正文读数证据但未命中 telemetry/evidence gate 的环境读数属性，下一步先做最小分类修复。文档见 `tasks/138d-ch10-ch12-post-fix-rerun.md`。
- 后续新增 V5 文档应优先更新本索引，再更新 `docs/STATUS.md`、`README.md`、`docs/INDEX.md`。
