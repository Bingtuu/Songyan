# Songyan 项目状态

> 短版状态板。长版历史状态已归档：`archive/v5/context-docs/STATUS-full-20260621.md`。

## 当前结论

| 项 | 状态 |
|----|------|
| 当前阶段 | **V5.2 进行中：Task 138h 已启动；目标是将 critical orphan 从 CreativeDirector 建议回收升级为 Writer 硬约束 + QG/RuleAuditor 可验证拦截，解决 `run-715f7d09` 暴露的 critical recall 执行闭环不稳定问题** |
| 最终验收 | **Task 120 V5.0 + Task 132 V5.1 Final Acceptance Package 已交付** |
| 风险口径 | P0/P1 风险为 0 |
| 最近全量测试 | `1979 passed, 1 xfailed`（2026-06-29，Task 138d-R2 环境/结构读数 snapshot allowlist 修复后） |
| 最近修复/验证 | Task 123 ContextEmergency / health_low 候选硬门禁（默认观测模式，16 个新单测）；Task 124 离线影响面分析；Task 125 阈值调优（P1 异常检测、health_score 跌幅、审计点 streak），新增 12 个单测；Task 126 enforce 小窗口实跑验证，Ch1–Ch19 零 gate 触发；**Task 127 重构 `health_low_score_halt` 为"历史新低 + P1 同步激增"复合条件，新增 8 个单测，pytest 1842 passed**；**Task 128 完成**：QG false 降级接受不终止 run、Ch1–Ch10 质量爬坡阈值、RevisionHandler readability 专精路径；pytest 1843 passed；**Task 129 条件完成**：enforce 模式 Ch1–Ch50 验证，`run-89d7a2d4` Ch1–Ch15 后因 quality_gate_fail_streak 暂停，暴露 Writer 结构退化、SettlementExtractor 角色/数值提取失败、orphaned settings 快速累积等底层缺陷；报告见 `docs/reports/task-129-enforce-validation-report.md`。**Task 130 已完成**：gate_mode 默认保持 `observe`，`songyan run` 暴露 `--gate-mode` CLI 参数，`songyan report` 新增 gate 触发汇总。**Task 131 已完成**：历史规划稿已归档至 `archive/tasks/`，索引文档已指向 `-DONE.md`。**Task 132 已完成**：V5.1 最终验收包已交付，V5.1 通过（条件完成项已明确转入 V5.2）。**Task 133/134/135 已完成**：Writer 多场景结构、SettlementExtractor 角色/数值提取、设定回收与 continuity health 治理；**Task 138f 已完成**：numerical_update evidence gate 已落地，无明确正文/source_quote 数字证据的 telemetry 候选会过滤并记录 diagnostic，真实 ledger 仍硬校验；**Task 138d-R2 retry4 已完成**：`run-bcee6ab6` Ch11/Ch12 settlement、summary、QG 全过，Ch12 continuity `health=3.0`、`orphaned=14`、`mismatches=0`；**Task 138g 已执行但未收口**：目标测试 `70 passed`、ruff 通过，`run-715f7d09` completed 但 Ch12 `health=3.0`、`orphaned=16`、critical orphan=4，证明问题不在 alias 而在 recall 执行闭环；**Task 138h 已启动**：critical orphan 强制回收闭环，文档见 `tasks/138h-critical-orphan-mandatory-recall-loop.md` |
| 当前 lint | `ruff check src/ tests/` 已通过；`scripts/` 目录包含一次性调试脚本，不参与 CI lint |
| Python | 3.11.9 |
| 事实入口 | `tasks/V5-README.md` |
| single-run rehearsal | Task 121b：`run-21ff158b`，Ch1-Ch4 成功，Ch5 阻断；Task 121d：`run-f749826e`，Ch1-Ch7 成功，Ch8 阻断；Task 121e 重跑：`run-0317a247`，Ch1-Ch17 成功，Ch18 阻断；Task 121f 聚焦验证：`run-058fb9de`，Ch1-Ch18 成功；Task 121g 完整重跑：`run-0fd1456e`，Ch1-Ch114 成功，Ch115 阻断；Task 121h 已完成工程修复；Task 121i `run-ce1767ff` Ch115 聚焦验证成功；Task 121j `run-b063b6f0` Ch1-Ch13 成功后因连续 ContextEmergency AutoHalt 暂停；Task 121l `run-08689f68` Ch1-Ch12 成功后因 Ch10-Ch12 连续 ContextEmergency 且含 QG false 按新策略暂停；Task 121o `run-4ff41095` Ch1-Ch18 全部成功 18/18，ContextEmergency 0 次，AutoHalt 0 次，已越过 Ch13 和 Ch18；Task 121p `run-2d7d96c2` 修复 Bug A/B 后重跑，Ch1-Ch3 成功，Ch4 因 0.82 阈值阻断；Task 121q `run-86b1170c` Ch1-Ch20 聚焦验证 20/20 全部成功；**Task 121q full single-run `run-a2bed648` Ch1-Ch150 全部成功 150/150，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙** |
| Task 121c | 已修复 rewrite fallback 后 `_skip_settlement=True` 错误阻断 settlement 的契约 |
| Task 121d | 已执行修复后重跑；已验证 Ch5 阻断解除，新增 Ch8 settlement_review 阻断 |
| Task 121e | 已修复并实跑验证 Ch8 settlement 伏笔校验阻断；Ch18 暴露新阻断 |
| Task 121f | 已修复 Ch18 CreativeDirector JSON parse failure 后的错误传播/章节状态判定契约，并通过 `run-058fb9de` Ch1-Ch18 聚焦验证 |
| Task 121g | 已完成新的干净 Ch1-Ch150 single-run：`run-0fd1456e` 最终 `partial`，Ch1-Ch114 成功，Ch115 因 quality gate human review 阻断 |
| Task 121h | 已完成 Ch115 quality gate / best-version rewrite 工程修复：rewrite 状态生命周期清理、版本化 new issues、低质量 rewrite / hard truncate 回滚到 safe best；全量 pytest/ruff 通过 |
| Task 121i | 已完成 Ch115 聚焦重跑：`run-ce1767ff`，Ch115 success / settlement / summary 均通过；Ch111-Ch115 质量窗口复核显示工程阻断解除但正文质量偏弱 |
| Task 121j | 已执行新 Ch1-Ch150 full single-run：`run-b063b6f0`，Ch1-Ch13 成功，Ch13 后因 Ch11-Ch13 连续 ContextEmergency 触发 AutoHalt，结果 partial |
| Task 121k | 已规划为 V5.1 Prompt / 正文质量清理，处理机械场景标题、元标记泄漏、短段落碎片化和说明文堆叠 |
| Task 121l | 已完成 AutoHalt 策略修复、单测和 Ch1-Ch18 聚焦实跑：`run-08689f68` 完成 Ch1-Ch12，失败 0；Ch10-Ch12 连续 ContextEmergency 且 Ch10 QG false，按新 `context_emergency_degraded_streak` 策略暂停，结果 partial |
| Task 121m | **已完成**：QG false 硬拦截 settlement + 元标记泄漏清理；`pytest` 1731 passed |
| Task 121n | **已完成**：Context Diet 2.0 预算增量 80→250 + human_marks 生命周期窗口 10→6；`pytest` 1731 passed |
| Task 121o | **已完成**：Ch1-Ch18 聚焦验证重跑 `run-4ff41095` **18/18 全部成功**，ContextEmergency 0 次，AutoHalt 0 次，已越过 Ch13 和 Ch18 |
| Task 121p | **已完成 Bug A/B 修复与重跑**：`run-40ceb306` 因 pipeline 未跳过已有 accepted 章节 + RAG 索引超时异常未捕获中断；Bug A/B 已修复；`run-2d7d96c2` 重跑 Ch1-Ch3 成功，**Ch4 因 0.82 阈值阻断** |
| Task 121q | **已完成**：`_SAFE_BEST_MIN_OVERALL_SCORE` 动态化（Ch1-Ch20→0.75, Ch21-Ch50→0.78, Ch51+→0.82）+ `degraded_accept` 降级回滚路径；pytest 1731 passed；ruff 通过；**Ch1-Ch20 聚焦验证 `run-86b1170c` 20/20 全部成功** |
| Task 121r | **已完成**：Writer 1.1.0（空行分隔场景、禁止 markdown/HTML/元标记、段落节奏约束）+ CreativeDirector 1.0.5（可执行约束、行动承载、避免设定清单退化）+ RuleAuditor 新增 markdown 场景标题与短段落比例检测；pytest 1764 passed；ruff 通过 |
| Task 122a | **已完成**：动态阈值 `_safe_best_min_score` 边界值测试 + `degraded_accept` 降级回滚路径测试；pytest 通过 |
| Task 122b | **已完成**：新增 12 个集成测试覆盖 degraded_accept 路由、safe best 保护、human_review_required gate、AutoHalt streak 逻辑；pytest 1784 passed；ruff 通过 |
| Task 122c | **已完成**：Ch1-Ch20 E2E 集成测试（28 秒重度 Mock）；Ch40-Ch50 / Ch100-Ch110 窗口待补充 |
| Task 122c | **已完成**：Ch1-Ch20 / Ch40-Ch50 / Ch100-Ch110 三个 E2E 窗口验证全部完成；`test_ch41_50_validation.py` 已补强 emergency/auto-halt 断言；`test_ch100_110_from_run_log.py` 已新增并复用 `run-a2bed648` 历史数据 |
| 重跑前清理 | **2026-06-23 已完成全量清理**：终止全部残留 Python 进程，删除数据库 28,440 行测试数据，清空所有业务表，清理日志文件，VACUUM 后 196 MB；环境完全干净 |
| 下一步规划 | **Task 138h-138j 已完成**：critical orphan 强制回收闭环建立。138i 措辞硬化无效，138j `recycle_hint` 显著有效（P1 5→2，health 3.0→3.9）。接受当前边界为阶段性成果。下一步进入 **Task 138k**（长窗口 rehearsal Ch1-Ch50/100），验证改进在更长章节窗口中的稳定性，并补全 Ch1-Ch150 single-run rehearsal 证据 |

测试说明：`1 xfailed` 为已知非阻断项；`0 xpassed`（已修复）；`0 failed`。数据库 `lifecycle_status` 列缺失与 RAG embedding 性能测试已修复，当前全量通过。

## 当前优先级

1. **Task 138k：长窗口 rehearsal Ch1-Ch50/100**：验证 138h-138j 改进在更长章节窗口中的稳定性。核心观察指标：critical orphan 趋势、health 趋势、settlement 通过率、QG 通过率。目标：连续 50 章 single-run 无 halt，health 维持在 ≥3.5。
2. **Task 137 收口判断**：基于 138k 的长窗口数据，判断 Task 137 是否满足"Ch10 起点聚焦验证"的收口条件（settlement 阻断解除、健康度 floor 通过、P1 orphan 可控）。
3. **后置默认化决策**：Writer 1.2.0 / `gate_mode="enforce"` 默认化仍后置，等 138k 长窗口数据验证后再决定。
4. **ContextEmergency / health_low 硬门禁预研**：作为 V5.2 方向后置，等 138k 数据出炉后评估是否需要引入。

## V5.1 交付摘要

- **Prompt 质量清理**：Task 121r 完成 Writer 1.1.0 + CreativeDirector 1.0.5 + RuleAuditor 格式检测。
- **测试矩阵**：Task 122a/122b/122c/122d 完成单元、集成、E2E、150 章压力四层测试。
- **候选硬门禁**：Task 123–130 完成实现、离线影响面分析、阈值调优、enforce 小窗口验证、score halt 重构、严格模式容错、gate_mode 默认决策；默认 `observe`，可显式启用 `enforce`。
- **文档一致性**：Task 131 完成历史规划稿归档，索引统一指向 `-DONE.md`。
- **V5.1 验收结论**：通过；条件完成项（Task 129 暴露的底层缺陷）已明确转入 V5.2。

## V5.0 交付摘要

- Context Diet 2.0 四组件已完成：TemporalCompressor、CharacterFocalDecay、SettingEvaporator、BudgetHardCeiling。
- Ch111-Ch150 分段验证完成：40/40 成功，QG/settlement/summary 均 40/40。
- Task 115-117 已关闭 DG-2 条件通过风险窗口。
- Task 118 已完成 ContinuityAuditor health_low P1/P2/P3 分级和 human marks 追踪。
- Task 119 已统一 `songyan report` 入口并加固 Windows wrapper。
- Task 120 给出 V5.0 最终通过结论。

## 遗留项

| 项 | 级别 | 处理 |
|----|------|------|
| 一次性 Ch1-Ch150 单命令证据 | P1 | **Task 121q full single-run `run-a2bed648` 已完成**：Ch1-Ch150 150/150 全部成功，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙 |
| Ch115 rewrite / best-version 劣化 | P1 | **Task 121h 已完成工程修复，Task 121i `run-ce1767ff` 已验证 Ch115 不再进入 human_review_required**；safe-best 回滚主路径未在本次触发，仍由单测覆盖 |
| 连续 ContextEmergency AutoHalt | P1 | **Task 121l 已完成策略修复；Task 121m 已完成 QG false 硬拦截；Task 121n 已完成预算调整；Task 121o 验证 Ch1-Ch18 0 次 emergency、0 次 AutoHalt。该风险已解除** |
| 0.82 阈值早期章节阻断 | P1 | **Task 121q 已完成**：0.82 已动态化，并引入 `degraded_accept` 降级回滚路径 |
| Prompt 质量瓶颈 | V5.1 | **Task 121r 已完成**：Writer 1.1.0 + CreativeDirector 1.0.5 + RuleAuditor 新增格式检测 |
| Pass 14-18 Code Review 缺口 | P1 | **已完成**：TS-01/TS-02/TS-03/TS-08 测试缺口已补齐；PR-05 元标记检测已补充；ST-03 目录迁移已修复；AG-04 显式拦截已补充；TS-10 测试卫生已清理 |
| health_low 硬门禁 | 预研 | **Task 123/124/125/126/127 已完成**：软复核 + 候选硬门禁实现 + 离线分析 + 阈值调优 + enforce 小窗口验证 + score halt 复合条件重构；`health_low_p1_halt`/`health_low_streak_halt` 在干净 run 中零误伤，`health_low_score_halt` 改为"历史新低 + P1 同步激增"复合条件；默认仍 `gate_mode="observe"`。`Task 129` 暴露的底层提取/设定回收缺陷由 Task 133/134/135 跟踪 |
| ContextEmergency 硬门禁 | 预研 | 保持合理降级，后置评估；当前 run 中未出现 context emergency |
| enforce 模式默认启用 | V5.2 | **被 Task 133/134/135 阻塞**：需先修复 Writer 多场景结构、SettlementExtractor 角色/数值提取、设定回收与 continuity health 缺陷，再完成跨项目 Ch1–Ch150 enforce 验证 |

## 文档入口

- 开发代理规则：`AGENTS.md`
- 文档索引：`docs/INDEX.md`
- V5 任务事实：`tasks/V5-README.md`
- V5.0 最终验收：`tasks/120-v5-final-acceptance-DONE.md`
- V5.1 规划：`tasks/121a-v50-goal-assessment-and-v51-plan.md`
- V5.1 Code Review 修复汇总：`docs/reports/pass14-final-fix-summary.md`
- Single-run rehearsal：`tasks/121b-ch1-ch150-single-run-rehearsal-DONE.md`
- Rewrite fallback settlement 修复：`tasks/121c-rewrite-fallback-settlement-contract-DONE.md`
- 修复后 single-run 重跑：`tasks/121d-ch1-ch150-single-run-rerun-DONE.md`
- Ch8 settlement 伏笔校验修复：`tasks/121e-ch8-settlement-foreshadowing-validation-fix-DONE.md`
- Ch18 CreativeDirector 错误传播修复：`tasks/121f-ch18-creative-director-error-contract-DONE.md`
- Ch1-Ch150 完整重跑 / Ch115 阻断：`tasks/121g-ch1-ch150-single-run-rerun-ch115-blocker-DONE.md`
- Ch115 工程修复：`tasks/121h-ch115-quality-gate-rewrite-state-review-DONE.md`
- Ch115 聚焦验证：`tasks/121i-ch115-focused-rerun-and-quality-window-DONE.md`
- Ch1-Ch150 修复后重跑：`tasks/121j-ch1-ch150-single-run-after-ch115-fix-DONE.md`
- Prompt 质量清理：`tasks/121k-prompt-quality-cleanup-plan-DONE.md`
- ContextEmergency AutoHalt review：`tasks/121l-context-emergency-autohalt-review-DONE.md`
- 候选硬门禁：`tasks/123-context-emergency-health-low-gate-proposal-DONE.md`
- 候选硬门禁阈值调优：`tasks/125-gate-threshold-tuning-and-validation-DONE.md`
- 候选硬门禁 enforce 小窗口验证：`tasks/126-small-window-enforce-validation-DONE.md`
- 重构 `health_low_score_halt`：`tasks/127-health-low-score-halt-refactor-DONE.md`
- 严格模式容错与开局期质量爬坡：`tasks/128-strict-mode-fault-tolerance-and-quality-ramp-DONE.md`
- enforce 模式 Ch1–Ch50 验证：`tasks/129-enforce-mode-ch1-ch50-validation-DONE.md`
- gate_mode 默认模式决策：`tasks/130-gate-mode-default-decision-DONE.md`
- 任务文档归档与状态一致性清理：`tasks/131-task-docs-archive-and-status-cleanup-DONE.md`
- V5.1 最终验收包：`tasks/132-v51-final-acceptance-package-DONE.md`
- Writer 多场景结构修复：`tasks/133-writer-multi-scene-structure-fix-DONE.md`
- SettlementExtractor 角色/数值提取修复：`tasks/134-settlement-character-numerical-extraction-fix-DONE.md`
- 设定回收与 continuity health 治理：`tasks/135-setting-recycling-and-continuity-health-governance-DONE.md`
- V5.2 Ch1-Ch20 采集窗口实跑验证：`tasks/136-v52-enforce-ch1-ch20-validation-DONE.md`
- 设定回收闭环与 tracking 刷新机制：`tasks/137-setting-recycling-closed-loop.md`
- 剩余 orphan 分类与证据表：`tasks/138a-remaining-orphan-classification.md`
- 基于分类结果确定最小动作：`tasks/138b-orphan-root-cause-decision.md`
- 剩余 orphan 最小修复：`tasks/138c-orphan-minimal-fix.md`
- 修复后 Ch10-Ch12 聚焦复跑验证：`tasks/138d-ch10-ch12-post-fix-rerun.md`
- 事实源同步与 Task 137 收尾判断：`tasks/138e-task137-fact-sync-and-closure.md`
- Settlement 数值结算证据门禁工程化修复：`tasks/138f-settlement-evidence-gated-numerical-extraction.md`
- V5 归档：`archive/v5/INDEX.md`
