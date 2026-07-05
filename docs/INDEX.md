# Songyan 文档索引

> 短版文档路由。长版索引已归档：`archive/v5/context-docs/INDEX-full-20260621.md`。

## 默认必读

| 文件 | 用途 |
|------|------|
| `AGENTS.md` | 开发代理短指令与不可违背规则 |
| `docs/STATUS.md` | 当前状态、测试口径、下一步 |
| `tasks/V7-README.md` | **V7 任务事实入口（当前阶段）**：篇章级质量修复 → 叙事自驱 → enforce 可生产化 → Ch300 渐进爬坡，Task 160-173 |
| `tasks/160-meta-tag-leak-eradication-DONE.md` | Task 160：元标记泄漏根治（Writer/RevisionHandler 默认清洗 + ReviewMerger 阻塞） |
| `tasks/161-paragraph-dedup-DONE.md` | Task 161：段落级去重（分段修订拼接去重 + 重复长段落诊断） |
| `tasks/162-cross-chapter-timeline-consistency-DONE.md` | Task 162：跨章时间线一致性诊断（确定性时间信号 + metrics 诊断段） |
| `tasks/163-concept-budget-constraint-DONE.md` | Task 163：概念预算约束（概念台账 + CreativeDirector 规划侧约束 + metrics 诊断段） |
| `tasks/164-text-cleanliness-metrics-DONE.md` | Task 164：文本洁净度度量入库 + metrics 展示 + T9 harness |
| `tasks/165-stage-w-ch150-rerun-and-threshold-freeze-DONE.md` | Task 165：阶段 W 出口 Ch1-Ch150 复跑验证 + T9/T10 冻结（已完成） |
| `tasks/165p-stage-w-harness-calibration-DONE.md` | Task 165p：阶段 W 出口阻断项，T5/T6 harness 口径校准（已完成） |
| `docs/reports/task-165-stage-w-exit-report.md` | Task 165：阶段 W 出口报告（150/150 accepted，P/L/不回退均通过） |
| `tasks/V6-README.md` | V6 任务事实入口（前置阶段）：叙事骨架 MVP + 度量 + 长跑底盘，Task 141-159 |
| `tasks/V5-README.md` | V5.0 任务事实入口 |
| `tasks/121a-v50-goal-assessment-and-v51-plan.md` | Task 121a：V5.0 目标评估与 V5.1 规划 |
| `tasks/121b-ch1-ch150-single-run-rehearsal-DONE.md` | Ch1-Ch150 single-run rehearsal 结果 |
| `tasks/121c-rewrite-fallback-settlement-contract-DONE.md` | rewrite fallback 后 settlement 契约修复 |
| `tasks/121d-ch1-ch150-single-run-rerun-DONE.md` | Task 121d：修复后 single-run 重跑结果 |
| `tasks/121e-ch8-settlement-foreshadowing-validation-fix-DONE.md` | Task 121e：Ch8 settlement 伏笔校验修复 |
| `tasks/121f-ch18-creative-director-error-contract-DONE.md` | Task 121f：Ch18 CreativeDirector 错误传播修复 |
| `tasks/121g-ch1-ch150-single-run-rerun-ch115-blocker-DONE.md` | Task 121g：Ch1-Ch150 完整重跑与 Ch115 新阻断定位 |
| `tasks/121h-ch115-quality-gate-rewrite-state-review-DONE.md` | Task 121h：Ch115 quality gate / best-version rewrite 工程修复 |
| `tasks/121i-ch115-focused-rerun-and-quality-window-DONE.md` | Task 121i：Ch115 聚焦重跑与质量窗口复核 |
| `tasks/121j-ch1-ch150-single-run-after-ch115-fix-DONE.md` | Task 121j：Ch115 修复后 Ch1-Ch150 full single-run |
| `tasks/121k-prompt-quality-cleanup-plan-DONE.md` | Task 121k：Prompt / 正文质量清理 |
| `tasks/121l-context-emergency-autohalt-review-DONE.md` | Task 121l：连续 ContextEmergency AutoHalt review |
| `tasks/121m-qg-false-block-and-meta-tag-cleanup-DONE.md` | Task 121m：QG false 硬拦截与元标记泄漏清理 |
| `tasks/121n-context-diet-budget-and-human-marks-lifecycle-DONE.md` | Task 121n：Context Diet 2.0 预算调整与 human_marks 生命周期优化 |
| `tasks/121o-ch1-ch18-focused-rerun-validation-DONE.md` | Task 121o：Ch1-Ch18 聚焦验证重跑 |
| `tasks/121p-ch1-ch150-single-run-rag-embedder-timeout-DONE.md` | Task 121p：Ch1-Ch150 full single-run RAG embedder 超时阻断 |
| `tasks/121q-safe-best-threshold-dynamic-fix-DONE.md` | Task 121q：Safe-Best 阈值动态化修复；**full single-run `run-a2bed648` Ch1-Ch150 150/150** |
| `tasks/121r-prompt-quality-cleanup-execution-DONE.md` | Task 121r：Prompt / 正文质量清理执行 |
| `tasks/122a-unit-test-matrix-dynamic-thresholds-DONE.md` | Task 122a：单元测试矩阵——动态阈值与降级回滚 |
| `tasks/122b-integration-test-pipeline-scenarios-DONE.md` | Task 122b：集成测试——Pipeline 关键场景 |
| `tasks/122c-e2e-validation-windows-DONE.md` | Task 122c：端到端验证窗口 |
| `tasks/122d-stress-test-long-sequence-stability-DONE.md` | Task 122d：压力测试——150 章长序列稳定性 |
| `tasks/123-context-emergency-health-low-gate-proposal-DONE.md` | Task 123：ContextEmergency / health_low 候选硬门禁提案 |
| `tasks/124-context-emergency-health-low-gate-impact-analysis-DONE.md` | Task 124：候选硬门禁离线影响面分析 |
| `tasks/125-gate-threshold-tuning-and-validation-DONE.md` | Task 125：候选硬门禁阈值调优与验证 |
| `tasks/126-small-window-enforce-validation-DONE.md` | Task 126：候选硬门禁 enforce 模式小窗口实跑验证 |
| `tasks/127-health-low-score-halt-refactor-DONE.md` | Task 127：重构 `health_low_score_halt` 复合条件 |
| `tasks/128-strict-mode-fault-tolerance-and-quality-ramp-DONE.md` | Task 128：严格模式容错与开局期质量爬坡 |
| `tasks/129-enforce-mode-ch1-ch50-validation-DONE.md` | Task 129：enforce 模式 Ch1–Ch50 验证 |
| `tasks/130-gate-mode-default-decision-DONE.md` | Task 130：gate_mode 默认模式决策 |
| `tasks/131-task-docs-archive-and-status-cleanup-DONE.md` | Task 131：任务文档归档与状态一致性清理 |
| `tasks/132-v51-final-acceptance-package-DONE.md` | Task 132：V5.1 最终验收包 |
| `tasks/133-writer-multi-scene-structure-fix-DONE.md` | Task 133：Writer 多场景结构修复（V5.2） |
| `tasks/134-settlement-character-numerical-extraction-fix-DONE.md` | Task 134：SettlementExtractor 角色/数值提取修复（V5.2） |
| `tasks/135-setting-recycling-and-continuity-health-governance-DONE.md` | Task 135：设定回收与 continuity health 治理（V5.2） |
| `tasks/136-v52-enforce-ch1-ch20-validation-DONE.md` | Task 136：V5.2 Ch1–Ch20 采集窗口跨项目实跑验证（已完成；后续 138n/138o 长窗口验证已证明 orphan 问题收敛） |
| `tasks/137-setting-recycling-closed-loop.md` | Task 137：设定回收闭环与 tracking 刷新机制（V5.2，已关闭；工作由 138a-138f 承接完成，138e 明确不归档） |
| `tasks/138a-remaining-orphan-classification-DONE.md` | Task 138a：剩余 orphan 分类与证据表（`run-4fd48756` 的 16 个 orphan） |
| `tasks/138b-orphan-root-cause-decision-DONE.md` | Task 138b：基于分类结果确定最小动作 |
| `tasks/138c-orphan-minimal-fix-DONE.md` | Task 138c：剩余 orphan 最小修复 |
| `tasks/138d-ch10-ch12-post-fix-rerun-DONE.md` | Task 138d/138d-R2：修复后 Ch10-Ch12 聚焦复跑验证（R2 最新 `run-bcee6ab6` completed，Ch12 continuity `orphaned=14`） |
| `tasks/138e-task137-fact-sync-and-closure-DONE.md` | Task 138e：事实源同步与 Task 137 收尾判断（已完成；Task 137 不归档） |
| `tasks/138f-settlement-evidence-gated-numerical-extraction-DONE.md` | Task 138f：Settlement 数值结算证据门禁工程化修复（已完成） |
| `tasks/138g-critical-orphan-root-cause-review.md` | Task 138g：critical orphan 根因复核与最小收口（已关闭；根因分析与修复由 138m/138n/138o 完成） |
| `tasks/138h-critical-orphan-mandatory-recall-loop-DONE.md` | Task 138h：critical orphan 强制回收闭环（已完成；子项 A+B 已落地） |
| `tasks/138i-writer-prompt-mandatory-reference-tone-hardening-DONE.md` | Task 138i：Writer prompt 措辞硬化（已完成但效果有限） |
| `tasks/138j-writer-mandatory-reference-recycle-hints-DONE.md` | Task 138j：Writer 回收提示（已完成；P1 5→2，health 3.0→3.9） |
| `tasks/138k-long-window-rehearsal-ch1-ch50.md` | Task 138k：长窗口 rehearsal Ch1-Ch50/100（已完成 Ch1-Ch30；暴露 Ch21+ health 下滑） |
| `tasks/138m-critical-orphan-root-cause-and-v52-boundary.md` | Task 138m：Ch21-Ch30 critical orphan 根因分析与 V5.2 边界决策（已完成；报告见 `docs/reports/task-138m-critical-orphan-root-cause-report.md`） |
| `tasks/138n-qg-mandatory-reference-revision-loop-DONE.md` | Task 138n：QG 阻断式 critical orphan revision + mandatory_reference 上限调优（已完成；Ch30 health 8.5 / P1=0） |
| `docs/reports/task-138n-ch1-ch30-rerun-report.md` | Task 138n：Ch1-Ch30 重跑验证报告 |
| `tasks/138o-ch31-ch50-long-window-validation-DONE.md` | Task 138o：Ch31-Ch50 长窗口延续验证（已完成；Ch50 health 8.8 / P1=0） |
| `docs/reports/task-138o-ch31-ch50-long-window-validation-report.md` | Task 138o：Ch31-Ch50 长窗口延续验证报告 |
| `tasks/138p-character-id-alias-in-cloned-projects-DONE.md` | Task 138p：克隆/延续项目角色 ID alias 断裂修复（已完成；新增 `tests/test_task138p_character_id_alias.py`） |
| `tasks/139a-v52-enforce-gate-config-final-audit.md` | Task 139a：V5.2 enforce 门禁配置最终审计（已完成；Ch1-Ch50 离线模拟零 gate 触发） |
| `docs/reports/task-139a-enforce-gate-config-audit.md` | Task 139a：enforce 门禁配置审计报告 |
| `tasks/139b-v52-enforce-ch1-ch50-validation.md` | Task 139b：V5.2 enforce 模式 Ch1-Ch50 复跑验证（已完成；`run-813a9ed7` 50/50 accept，无 AutoHalt） |
| `tasks/139e-v52-rewrite-mandatory-reference-fix.md` | Task 139e：rewrite_node 丢失 mandatory reference 修复（已完成） |
| `tasks/139f-v52-revision-router-mandatory-reference-bypass-fix.md` | Task 139f：revision_router 回滚 bypass mandatory reference 修复（已完成） |
| `docs/reports/task-139b-enforce-ch1-ch50-validation-report.md` | Task 139b：首次 enforce 实跑验证报告（Ch1-Ch21） |
| `docs/reports/task-139b-enforce-ch1-ch50-validation-report.md` | Task 139b：第一次重跑 enforce 实跑验证报告（Ch1-Ch24） |
| `docs/reports/task-139b-enforce-ch1-ch50-validation-report.md` | Task 139b：第二次重跑 enforce 实跑验证报告（Ch1-Ch50，通过） |
| `tasks/139c-v52-enforce-ch51-ch150-validation.md` | Task 139c：V5.2 enforce 模式 Ch51-Ch150 长窗口验证（已完成；`run-c68a1384` + `run-7b45c17d` + `run-df933dbf` 合计 100/100 accept） |
| `tasks/139d-v52-default-enforce-switch-and-final-acceptance.md` | Task 139d：V5.2 默认 gate_mode 切换为 enforce 与最终验收包交付（已完成；CLI 默认 `enforce`，验收包已交付） |
| `docs/reports/task-139d-v52-final-acceptance-package.md` | Task 139d：V5.2 最终验收包（已验收；Ch1-Ch150 150/150 accept） |
| `tasks/139g-v52-settlement-llm-timeout-fix.md` | Task 139g：V5.2 settlement LLM 超时修复（已完成） |
| `tasks/139h-v52-ch80-revision-word-count-blowup-fix.md` | Task 139h：V5.2 Ch80 revision 字数膨胀修复（已完成；`run-7b45c17d` Ch80 accept，生成 `v-80-12-e017e643`） |
| `tasks/140-v52-legacy-task-cleanup-DONE.md` | Task 140：V5.2 遗留任务状态清理（已完成） |
| `archive/v5/138m-analysis/` | Task 138m 根因分析中间数据与脚本（已归档） |
| `docs/reports/task-137-v52-enforce-ch1-ch20-rerun-report.md` | Task 137：Ch1–Ch20 采集窗口复跑报告（`run-06ae5101` partial） |
| `docs/reports/task-137-ch10-focus-validation-report.md` | Task 138d/138e/138d-R2/138g：Ch10 起点聚焦验证报告（最新 `run-715f7d09` completed，Ch12 `health=3.0`、`orphaned=16`） |

## 长期规划（300 章目标）

| 文件 | 用途 |
|------|------|
| `tasks/V7-README.md` | **V7 任务事实入口（当前阶段）**：Task 160-173 状态、P/L/T/G/V 阶段验收判定、依赖关系与执行纪律 |
| `tasks/V6-README.md` | V6 任务事实入口（前置）：Task 141-159 状态、阶段验收判定、依赖关系与执行纪律 |
| `docs/300-chapter-gap-analysis.md` | 300 章卡点与解决路径（含根因：缺自顶向下叙事架构）的代码级分析（V6/V7 论证基础） |
| `docs/v6-plan.md` | V6 阶段规划：叙事骨架 MVP + 长篇质量度量 + 可靠长跑底盘 + Task 141-159 路线图 |
| `docs/v7-vision.md` | V7 构想（方向性）：从叙事骨架到完整线索经济 + 满 Ch300 渐进验证 |
| `docs/v7-plan.md` | V7 阶段规划：篇章级质量修复 + 叙事自驱 + enforce 可生产化 + Ch300 渐进爬坡 + Task 160-173 路线图 |

## 按场景查阅

| 场景 | 文件 |
|------|------|
| V5.0 最终是否通过 | `archive/tasks/120-v5-final-acceptance-DONE.md` |
| 报告入口 / wrapper | `archive/tasks/119-reporting-wrapper-hardening-DONE.md` |
| health_low 治理 | `archive/tasks/118-continuity-health-governance-DONE.md` |
| DG-2 风险窗口复验 | `archive/tasks/117-dg2-risk-window-revalidation-DONE.md` |
| Ch111-Ch150 验证 | `archive/tasks/114-ch101-ch150-streaming-validation-DONE.md` |
| Ch102/Ch103 settlement 验证窗口 | `archive/tasks/114b2-qg-convergence-settlement-window-DONE.md` |
| Ch1-Ch150 single-run rehearsal | `tasks/121b-ch1-ch150-single-run-rehearsal-DONE.md` |
| Ch5 settlement skip 修复 | `tasks/121c-rewrite-fallback-settlement-contract-DONE.md` |
| 修复后 single-run 重跑 / Ch8 新阻断 | `tasks/121d-ch1-ch150-single-run-rerun-DONE.md` |
| Ch8 settlement 伏笔校验修复 | `tasks/121e-ch8-settlement-foreshadowing-validation-fix-DONE.md` |
| Ch18 CreativeDirector 错误传播修复 | `tasks/121f-ch18-creative-director-error-contract-DONE.md` |
| Ch1-Ch150 完整重跑 / Ch115 阻断 | `tasks/121g-ch1-ch150-single-run-rerun-ch115-blocker-DONE.md` |
| Ch115 工程修复 | `tasks/121h-ch115-quality-gate-rewrite-state-review-DONE.md` |
| Ch115 聚焦验证 | `tasks/121i-ch115-focused-rerun-and-quality-window-DONE.md` |
| Ch1-Ch150 修复后 full single-run | `tasks/121j-ch1-ch150-single-run-after-ch115-fix-DONE.md` |
| Ch1-Ch150 RAG embedder 超时阻断 | `tasks/121p-ch1-ch150-single-run-rag-embedder-timeout-DONE.md` |
| Ch1-Ch150 full single-run 最终证据 | `tasks/121q-safe-best-threshold-dynamic-fix-DONE.md` |
| Safe-Best 阈值动态化 | `tasks/121q-safe-best-threshold-dynamic-fix-DONE.md` |
| Prompt / 正文质量清理 | `tasks/121k-prompt-quality-cleanup-plan-DONE.md` |
| Prompt 质量清理执行 | `tasks/121r-prompt-quality-cleanup-execution-DONE.md` |
| 单元测试矩阵 | `tasks/122a-unit-test-matrix-dynamic-thresholds-DONE.md` |
| 集成测试场景 | `tasks/122b-integration-test-pipeline-scenarios-DONE.md` |
| 端到端验证窗口 | `tasks/122c-e2e-validation-windows-DONE.md` |
| 压力测试长序列 | `tasks/122d-stress-test-long-sequence-stability-DONE.md` |
| ContextEmergency AutoHalt review | `tasks/121l-context-emergency-autohalt-review-DONE.md` |
| QG false 拦截与元标记清理 | `tasks/121m-qg-false-block-and-meta-tag-cleanup-DONE.md` |
| Context Diet 预算与 human marks 生命周期 | `tasks/121n-context-diet-budget-and-human-marks-lifecycle-DONE.md` |
| Ch1-Ch18 聚焦验证 | `tasks/121o-ch1-ch18-focused-rerun-validation-DONE.md` |
| ContextEmergency / health_low 候选硬门禁 | `tasks/123-context-emergency-health-low-gate-proposal-DONE.md` |
| 候选硬门禁影响面分析 | `tasks/124-context-emergency-health-low-gate-impact-analysis-DONE.md` |
| 候选硬门禁阈值调优 | `tasks/125-gate-threshold-tuning-and-validation-DONE.md` |
| 候选硬门禁 enforce 小窗口验证 | `tasks/126-small-window-enforce-validation-DONE.md` |
| health_low score halt 重构 | `tasks/127-health-low-score-halt-refactor-DONE.md` |
| 严格模式容错与开局期质量爬坡 | `tasks/128-strict-mode-fault-tolerance-and-quality-ramp-DONE.md` |
| enforce 模式 Ch1–Ch50 验证 | `tasks/129-enforce-mode-ch1-ch50-validation-DONE.md` |
| gate_mode 默认模式决策 | `tasks/130-gate-mode-default-decision-DONE.md` |
| 任务文档归档与状态清理 | `tasks/131-task-docs-archive-and-status-cleanup-DONE.md` |
| V5.1 最终验收包 | `tasks/132-v51-final-acceptance-package-DONE.md` |
| Writer 多场景结构修复（V5.2） | `tasks/133-writer-multi-scene-structure-fix-DONE.md` |
| SettlementExtractor 角色/数值提取修复（V5.2） | `tasks/134-settlement-character-numerical-extraction-fix-DONE.md` |
| 设定回收与 continuity health 治理（V5.2） | `tasks/135-setting-recycling-and-continuity-health-governance-DONE.md` |
| V5.2 Ch1–Ch20 采集窗口实跑验证 | `tasks/136-v52-enforce-ch1-ch20-validation-DONE.md` |
| 设定回收闭环与 tracking 刷新机制（V5.2，已关闭） | `tasks/137-setting-recycling-closed-loop.md` |
| 剩余 orphan 分类与证据表 | `tasks/138a-remaining-orphan-classification-DONE.md` |
| 基于分类结果确定最小动作 | `tasks/138b-orphan-root-cause-decision-DONE.md` |
| 剩余 orphan 最小修复 | `tasks/138c-orphan-minimal-fix-DONE.md` |
| 修复后 Ch10-Ch12 聚焦复跑验证 | `tasks/138d-ch10-ch12-post-fix-rerun-DONE.md`（R2 最新 `run-bcee6ab6`） |
| 事实源同步与 Task 137 收尾判断（已完成；Task 137 不归档） | `tasks/138e-task137-fact-sync-and-closure-DONE.md` |
| Settlement 数值结算证据门禁工程化修复（已完成） | `tasks/138f-settlement-evidence-gated-numerical-extraction-DONE.md` |
| critical orphan 根因复核与最小收口（已关闭） | `tasks/138g-critical-orphan-root-cause-review.md` |
| Task 138m critical orphan 根因分析决策报告 | `docs/reports/task-138m-critical-orphan-root-cause-report.md` |
| critical orphan 强制回收闭环（已完成；子项 A+B 已落地） | `tasks/138h-critical-orphan-mandatory-recall-loop-DONE.md` |
| settlement 数值遥测误报修复（已完成） | `tasks/138l-settlement-telemetry-false-positive-fix-DONE.md` |
| V5.1 Code Review 总规划（已归档） | `archive/v5/reports/pass14-to-pass18-v51-review-roadmap.md` |
| V5.1 Code Review 修复汇总（已归档） | `archive/v5/reports/pass14-final-fix-summary.md` |
| 架构手册 | `docs/architecture/04-vibe-coding-engineering.md` |
| 技术参考 | `docs/architecture/05-tech-reference.md` |
| Code Review | `docs/code-review-plan.md` |
| Prompt 工艺卡 | `prompts/cards/` |

## 归档入口

归档内容默认不读，仅在追溯历史决策时查阅。

- `archive/v5/INDEX.md` — V5 归档索引
- `archive/v5/context-docs/` — AGENTS / STATUS / INDEX 长版快照
- `archive/v5/plans/` — V5.0 已完成任务的历史规划稿
- `archive/v4/INDEX.md` — V4.x 历史结论
- `archive/v3/INDEX.md` — V3.x 历史结论
- `archive/tasks/` — 历史任务规划稿与交接报告（V5.0/V5.1 已完成任务的历史规划稿已归档至此，状态以各任务 `-DONE.md` 为准）
