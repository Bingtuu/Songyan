# Songyan 项目状态板

> **当前阶段: V5.0 "Context Diet 2.0" — 智能遗忘架构**
> **更新日期**: 2026-06-21
>
> V4.x 历史归档见 `archive/v4/INDEX.md`

---

## V5.0 愿景

> **"不是所有信息都值得记住。通过智能遗忘与分层压缩，支撑 150+ 章稳定生成。"**

| 维度 | V4.0 | V5.0 |
|------|------|------|
| 目标 | Ch1~Ch50 稳定（Context-on-Demand 优化） | **Ch1~Ch150 全自动** |
| 策略 | BudgetPruner 裁剪、四信号系统、Accept 守卫 | **TemporalCompressor + CharacterFocalDecay + SettingEvaporator + BudgetHardCeiling** |
| 核心问题 | 上下文持续增长，预组装大包触及天花板 | **信息密度控制：记住什么、遗忘什么、怎么压缩** |
| 代码哲学 | 按需、自律、可归档 | **智能遗忘、分层压缩、活跃信息池控制** |

---

## V5.0 核心决策

**Context-on-Demand（检索架构） → Context Diet 2.0（信息节食）**

```
V4.0: ContextManager 预组装大包 → BudgetPruner 裁剪 → 仍持续增长
V5.0: TemporalCompressor 分层摘要 + CharacterFocalDecay 角色衰减
       + SettingEvaporator 设定蒸发 + BudgetHardCeiling 硬天花板
       → 信息密度 O(log n) → 支撑 150+ 章
```

**关键变更**:

| 组件 | V4.0 | V5.0 |
|------|------|------|
| 历史信息加载 | 平铺最近 N 章摘要 | **金字塔分层**（最近详细 + 弧摘要 + 卷摘要） |
| 角色档案 | 出场即加载完整档案 | **按未出场章数衰减**（完整→精简→符号→不加载） |
| 设定/伏笔 | 时间阈值归档 | **语义相关性蒸发**（resolve_confidence + embedding 合并） |
| 预算控制 | fullness_factor 0.5 | **fullness_factor 0.7 + ContextEmergency** |
| 验证方式 | 每 Task 人工写报告 | **流式自动收集 + 一键生成报告** |

---

## 当前状态

| 指标 | 数值 |
|------|------|
| 状态 | **V5.0 完成** — Task 120 Final Acceptance Package：P0/P1 风险为 0；全量回归 1718 passed；lint 全通过；文档一致性已验证 |
| Task 119 已完成 | 报告入口：songyan report CLI + 模块入口；wrapper 加固：6 种 WRAPPER_RESULT 结果码；日志路径规范化 |
| Task 120 已完成 | V5.0 Final Acceptance Package：P0/P1 风险为 0；全量回归 1718 passed；lint 全通过；V5-README.md 已同步更新 |
| Task 117 已完成 | Ch115/Ch120/Ch147/Ch148 4/4 成功，rebound 保护正常，Emergency 属合理降级未触发 |
| 最近回归测试 | **1718 passed, 1 xfailed, 1 xpassed, 14 warnings** (`pytest tests/ -q`，xfail/xpass 均为已知非阻断项) |
| 当前 lint | **`ruff check src/ tests/` 已通过** |
| Python | 3.11.9 |
| 当前 Task | **V5.0 完成** — Task 120 Final Acceptance Package 已交付；Task 121 已产出 V5.0 评估与 V5.1 下一步规划 |
| 下一步建议 | **V5.0 交付完成。建议先补 Ch1-Ch150 single-run rehearsal 证据，再做 Prompt 调优；ContextEmergency/health_low 硬门禁后置预研** |

> 测试口径说明：`1 xfailed` 为 Windows SQLite 并发写入限制；`1 xpassed` 为性能测试预热/冷启动差异，均为已知非阻断项。

---

## V5.0 路线图

> 状态事实入口见 `tasks/V5-README.md`。本表只保留当前 V5 主线进度，规划稿不再作为完成状态依据。

### Phase 1 — Context Diet 2.0 核心组件（Week 1-3）

| Task | 内容 | 验收条件 | 状态 |
|------|------|---------|:----:|
| 101 | **TemporalCompressor** — 时间分层压缩 | `previous_summaries` token < 平铺 60%；Ch51 达标 ≥ 75% | ✅ |
| 102 | **CharacterFocalDecay** — 角色焦点衰减 | Ch55 `character_states` token < Ch50 的 70%；衰减覆盖率 100% | ✅ |
| 103 | **SettingEvaporator** — 设定蒸发器 | Ch60 active settings < Ch50 的 70%；蒸发误判 < 5% | ✅ |
| 104 | **BudgetHardCeiling** — 预算硬天花板 | `fullness_factor` 0.7；ContextEmergency 触发正确；Emergency 后 token < budget | ✅ |

### Phase 2 — 流式验证（Week 4）

| Task | 内容 | 验收条件 | 状态 |
|------|------|---------|:----:|
| 105 | **Ch51-Ch100 流式验证基础设施 + 决策门 DG-1** | JSONL 指标、自动熔断、一键报告 | ✅ |
| 105b | **Ch51-Ch100 验证重启** | 在 Task 106-109 修复后重新跑 Ch51-Ch100；50/50 成功，QG 通过率 58.0%，DG-1 未通过 | ✅ |
| Task 106 | **Unified Scoring System** — 统一评分体系 | 5 维评分结构 + ScoreAggregator + 工作流适配；全量回归通过 | ✅ |
| Task 107 | **Repair Convergence Guardrail + Fix 150-Blockers** — 修订/重写收敛护栏与 150 章阻断缺陷修复 | rewrite 结构完整性校验；QG 耗尽回滚 best_version + 跳过 settlement；skip_settlement 成功路径；rewrite best 基准更新；literary-scorecard 决策合并；length 阈值校准；废弃版本过滤；max_revision_rounds 透传；1524 passed | ✅ |

### Phase 3 — 活跃信息池控制（Week 5-6）

| Task | 内容 | 验收条件 | 状态 |
|------|------|---------|:----:|
| 108 | **角色退场机制** — CharacterLifecycleAuditor | 非核心角色 30 章未出场 → dormant；活跃角色 ≤ 10 | ✅ |
| 109 | **设定合并 + 伏笔监控** — SettingDeduplication + ForeshadowingPressure | 相似设定合并率 ≥ 90%；未闭合伏笔比例 ≤ 60% | ✅ |

### Phase 4 — 150 章规模化验证（Week 7-10）

| Task | 内容 | 验收条件 | 状态 |
|------|------|---------|:----:|
| 110a | **生产端保真压缩** — CharacterState 分层压缩 + 关键事实保留 | Ch80-Ch100 验证：压缩生效，但 emergency 未显著下降（81.0% vs 82.0% 基线）；关键事实保留 | ✅ |
| 110b | **结构与质量控制** — Setting key 规范化、Summary 模板化、HardConstraint 长度审计 | setting key 规范率 100%；summary 长度受控；hard_constraints 不膨胀 | ✅ |
| 110c | **加载与裁剪优化** — 智能过滤 + 分级 ContextEmergency + 可恢复性 | Ch80-Ch100 emergency 再降 ≥ 30%；保留 source_version_id | ✅ |
| 110d | **Ch80-Ch100 快速验证与调优** — 验证 110a-110c 效果并调参 | ContextEmergency 0%；参数调优已验证并回滚；QG 58.8% 未达 80% 目标 | ✅ |
| 110e | **coherence_major 根因修复** — ScoreAggregator 阈值校准 + LLMAuditor 审查上下文增强 | Ch80-Ch96 QG 100% (17/17)；coherence_major 0/17；文本阅读体验验证通过 | ✅ |
| 111a | **工作流决策契约修复** — ReviewMerger/ScoreAggregator/Literary/Revision 路由一致性 | merged critical/major 不被覆盖；Literary 不阻塞；rewrite_scene 不自动 patch；无证据 issue 不修订；全量回归 1628 passed | ✅ |
| 111b | **Settlement 与事实源一致性修复** — accept/settlement/summary/state 边界 | validation failed 不落库；accepted 与 settlement 无半提交；summary_id 指向真实记录；state 不存完整 ContextPackage；全量回归 1632 passed | ✅ |
| 111c | **Context 与 Prompt 一致性修复** — hard ceiling、hard constraints、Craft Card、human instruction | Emergency 后 budget ≤ 1.0；硬约束不裁剪；Prompt 权重和 human instruction 字段一致；全量回归 1635 passed | ✅ |
| 111d | **QualityGate 与 Settlement 阻断项修复** — budget QG、new issues、summary fallback | budget_used 使用 `_context_metrics`；new issues 不 accepted+missing settlement；accepted 后 summary 100% | ✅ |
| 111e | **Task 112 报告与 DG-2 Gate 完整性修复** | report 不因 `budget_used=None` 崩溃；DG-2 覆盖逐章 budget、settlement、summary、failure reason | ✅ |
| 111f | **Context Snapshot、Prompt 与 Metadata 一致性修复** | Writer/Auditor 复用上下文快照；human instruction/brief 动态字段不丢；metadata 可回放 | ✅ |
| 111g | **长跑性能缺陷收敛** | 减少重复 context assembly；限制 settlement prompt 事实源；收敛 O(N²) 热点 | ✅ |
| 112 | **Task 114 前置阻断修复** | 修复 budget QG 硬门禁与 Settlement setting_key 规范化；恢复 Ch97 accepted + settlement + summary 基线 | ✅ |
| 113 | **Ch101 收敛回滚与 Settlement 阻断修复** | 修复 rebound 后 best version/head 选择；恢复 Ch101 accepted + settlement + summary 基线；全量回归通过 | ✅ |
| 114a | **Settlement 事实源契约修复** | 修复 Ch103 暴露的 `old_value` mismatch、`quote_filter` 内部 ID 误杀引用、run logger/post-processing 残留风险 | ✅ |
| 114b | **Phase 1 重跑 Ch102-Ch110** | Ch103/Ch102 回放因 QG 收敛失败触发 `_skip_settlement=True`，未进入 settlement；未达 Phase 1 出口条件 | ⚠️ |
| 114b2 | **QG 收敛阻断处理 + settlement 端到端验证窗口** | 已修复 QG 收敛阻断和 rewrite 结构失败路由；Ch102/Ch103 `run-af3ba939` 完成 accept+settlement+summary | ✅ |
| 114c | **Ch111-Ch150 分段流式验证 + DG-2** | Ch111-Ch150 40/40 成功；QG/settlement/summary 40/40；DG-2 因 Ch115/Ch120 ContextEmergency 为条件通过 | ⚠️ 条件通过 |

### Phase 4 收口任务 — DG-2 条件通过后续任务（Task 115-120，已完成）

| Task | 内容 | 验收条件 | 状态 |
|------|------|---------|:----:|
| 115 | **ContextEmergency 触发复核与校准** | Ch115/Ch120 触发原因 100% 可解释；新增 `budget_used_before_emergency` 字段；全量回归通过 | ✅ 完成 |
| 116 | **Best-Version 质量选择策略复核与修复** | Ch147/Ch148 best version 符合 QG passed best 规则；低分 rewrite fallback 不覆盖高分 best；`quality_gate_router` 路由缺陷已修复 | ✅ 完成 |
| 117 | **DG-2 风险章节窗口复验** | Ch115/Ch120/Ch147/Ch148 4/4 成功；报告与 JSONL/DB 一致；DG-2 风险已关闭 | ✅ 完成 |
| 118 | **ContinuityAuditor Health 低分治理策略** | health_low 可统计、可追踪、可分级；human marks 关联 project/chapter/version | ✅ 完成 |
| 119 | **长跑报告入口与 Windows Wrapper 加固** | 报告入口统一；songyan report CLI；wrapper 正常/超时/业务完成异常均有明确结果码 | ✅ 完成 |
| 120 | **V5.0 Final Acceptance Package** | Task 115-120 全部收口；P0/P1 风险为 0；全量回归 1718 passed；lint 通过 | ✅ 完成 |

---

## 当前遗留风险

| 风险 | 级别 | 处理建议 |
|------|------|----------|
| Ch115/Ch120 ContextEmergency | ~~P1~~ | **Task 115 已关闭**：诊断为合理降级（`budget_used` 触发时 1.0007），新增可观测性字段 |
| Ch147/Ch148 best-version 质量选择 | ~~P1~~ | **Task 116 已关闭**：`quality_gate_router` 路由缺陷修复，QG 通过后不再错误触发 rewrite |
| DG-2 风险窗口复验 | ~~P1~~ | **Task 117 已关闭**：Ch115/Ch120 Emergency 未触发，Ch147/Ch148 rebound 正确，DG-2 条件通过但风险已关闭 |
| ContinuityAuditor health 低分 | ~~P2~~ | **Task 118 已关闭**：P1/P2/P3 分级 + human marks 追踪；V5.1 可扩展硬门禁 |
| 报告入口与 Windows wrapper 漂移 | ~~P2~~ | **Task 119 已关闭**：统一 `songyan report` 入口并加固 wrapper 退出判定 |
| 一次性 Ch1-Ch150 单命令证据 | P2 | **Task 121 建议补强**：V5.0 工程验收已达成，如需严格宣称 single-run，应补 rehearsal |

---

## V4.x 关键结论（归档）

> 详细归档见 `archive/v4/INDEX.md`

1. **预组装上下文包可被优化到 Ch50 级别**
   - BudgetPruner + 四信号系统 + 下限保护 = 81.6% 达标率
   - 不是"必须废弃"，而是"需要更聪明地控制加载什么"

2. **token budget 不是瓶颈**
   - 平均 budget_used = 1.073，问题不在检索架构
   - ContextService 按需检索暂缓

3. **真正的瓶颈是信息密度**
   - 角色档案、设定、伏笔的累积无法仅靠裁剪解决
   - 必须主动"遗忘"低价值信息

4. **V4.0 → V5.0 转向**
   - 原 Phase C（ContextService）归档
   - 新方向：Context Diet 2.0（智能遗忘 + 分层压缩）

---

## 参考

- `archive/v4/INDEX.md` — V4.x 完整归档索引
- `docs/INDEX.md` — 文档索引
- `AGENTS.md` — 开发代理指令与不可违背规则
- `tasks/V5-README.md` — V5.0 任务总索引与当前事实入口
- `tasks/105-ch51-ch100-streaming-validation-DONE.md` — 流式验证基础设施交付记录
- `tasks/105b-ch51-ch100-validation-restart-DONE.md` — Ch51-Ch100 验证重启交付记录
- `tasks/107-repair-convergence-guardrail-DONE.md` — 收敛护栏与 150 章阻断缺陷修复记录
- `tasks/108-character-lifecycle-auditor-DONE.md` — 角色退场机制记录
- `tasks/109-setting-dedup-and-foreshadowing-pressure-DONE.md` — 设定合并与伏笔监控记录
- `tasks/110a-character-state-tiered-compression-DONE.md` — CharacterState 分层保真压缩交付记录
- `tasks/110b-setting-summary-quality-control-DONE.md` — Setting/Summary/HardConstraint 质量控制交付记录
- `tasks/110c-loading-and-pruning-strategy-DONE.md` — 加载端智能过滤与分级 ContextEmergency 交付记录
- `tasks/110d-ch80-ch100-validation-and-tuning-DONE.md` — Ch80-Ch100 快速验证与调优记录
- `tasks/110e-coherence-major-fix-DONE.md` — coherence_major 根因修复交付记录
- `tasks/111a-workflow-decision-contract-fix-DONE.md` — 工作流决策契约修复交付记录
- `tasks/111b-settlement-state-integrity-fix-DONE.md` — Settlement 与事实源一致性修复交付记录
- `tasks/111c-context-prompt-consistency-fix-DONE.md` — Context 与 Prompt 一致性修复交付记录
- `tasks/111d-quality-gate-settlement-blockers-fix-DONE.md` — QualityGate 与 Settlement 阻断项修复交付记录
- `tasks/111e-task112-reporting-dg2-gate-fix-DONE.md` — Task 112 报告与 DG-2 Gate 完整性修复交付记录
- `tasks/111f-context-snapshot-prompt-metadata-fix-DONE.md` — Context Snapshot、Prompt 与 Metadata 一致性修复交付记录
- `tasks/111g-long-run-performance-containment-DONE.md` — 长跑性能缺陷收敛交付记录
- `tasks/112-preflight-blocker-fix-DONE.md` — Task 114 前置阻断修复交付记录
- `tasks/113-ch101-convergence-settlement-blocker-fix-DONE.md` — Ch101 收敛回滚与 Settlement 阻断修复记录
- `tasks/114a-settlement-fact-source-contract-fix-DONE.md` — Task 114a Settlement 事实源契约修复交付记录
- `tasks/114b-phase1-replay-ch102-ch110-DONE.md` — Task 114b Phase 1 熔断复核记录
- `tasks/114b2-qg-convergence-settlement-window-DONE.md` — Task 114b2 QG 收敛阻断与 settlement 端到端验证记录
- `archive/v5/plans/114-ch101-ch150-streaming-validation.md` — Task 114 umbrella 历史规划稿：114a Settlement 修复、114b Phase 1 重跑、114b2 验证窗口、114c DG-2 长跑
- `tasks/114-ch101-ch150-streaming-validation-DONE.md` — Task 114c Ch111-Ch150 分段流式验证与 DG-2 条件通过记录
- `tasks/115-context-emergency-review-DONE.md` — Task 115 ContextEmergency 触发复核与校准交付记录
- `tasks/116-best-version-quality-selection-fix-DONE.md` — Task 116 best-version 质量选择策略复核与修复交付记录
- `tasks/117-dg2-risk-window-revalidation-DONE.md` — Task 117 DG-2 风险章节窗口复验交付记录
- `tasks/118-continuity-health-governance-DONE.md` — Task 118 ContinuityAuditor health_low 治理策略交付记录
- `tasks/119-reporting-wrapper-hardening-DONE.md` — Task 119 长跑报告入口与 Windows wrapper 加固交付记录
- `tasks/120-v5-final-acceptance-DONE.md` — V5.0 Final Acceptance Package
- `tasks/121-v50-goal-assessment-and-v51-plan.md` — V5.0 目标达成评估与 V5.1 下一步规划
- `logs/chapter_runs/run-33229919.jsonl` — Ch51-Ch59 实跑指标





















