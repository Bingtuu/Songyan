# Songyan 项目状态板

> **当前阶段: V5.0 "Context Diet 2.0" — 智能遗忘架构**
> **更新日期**: 2026-06-16
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
| 状态 | **V5.0 Phase 3 — Task 105b 完成，DG-1 未通过** |
| V4.0 最终达标率 (Ch2-Ch50) | **81.6%** (Task 099) ✅ |
| Task 105b 实跑 | **Ch51-Ch100 全部成功，QG 通过率 58.0% (29/50)，DG-1 未通过** |
| 最近回归测试 | **1555 passed, 4 skipped, 1 xfailed, 4 xpassed** |
| Python | 3.11.9 |
| 下一 Task | **Task 110a: CharacterState 分层保真压缩** |

---

## V5.0 路线图

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
| 110a | **生产端保真压缩** — CharacterState 分层压缩 + 关键事实保留 | Ch80-Ch100 emergency 下降 ≥ 30%；关键事实不丢失 | 📝 |
| 110b | **结构与质量控制** — Setting key 规范化、Summary 模板化、HardConstraint 长度审计 | setting key 规范率 100%；summary 长度受控；hard_constraints 不膨胀 | 📝 |
| 110c | **加载与裁剪优化** — 智能过滤 + 分级 ContextEmergency + 可恢复性 | Ch80-Ch100 emergency 再降 ≥ 30%；保留 source_version_id | 📝 |
| 110d | **Ch80-Ch100 快速验证与调优** — 验证 110a-110c 效果并调参 | Ch80-Ch100 达标率 ≥ 80%；无连续 3 章失败 | 📝 |
| 111 | **Ch101-Ch150 流式验证 + 决策门 DG-2** | 达标率 ≥ 70%；budget_used ≤ 1.0；完成 150 章一次性生成 | 📝 |

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
- `tasks/105-ch51-ch100-streaming-validation-DONE.md` — 流式验证基础设施交付记录
- `tasks/105b-ch51-ch100-validation-restart-DONE.md` — Ch51-Ch100 验证重启交付记录
- `tasks/107-repair-convergence-guardrail-DONE.md` — 收敛护栏与 150 章阻断缺陷修复记录
- `tasks/108-character-lifecycle-auditor-DONE.md` — 角色退场机制记录
- `tasks/109-setting-dedup-and-foreshadowing-pressure-DONE.md` — 设定合并与伏笔监控记录
- `tasks/110a-character-state-tiered-compression.md` — CharacterState 分层保真压缩规划
- `tasks/110b-setting-summary-quality-control.md` — Setting/Summary/HardConstraint 质量控制规划
- `tasks/110c-loading-and-pruning-strategy.md` — 加载端智能过滤与分级裁剪规划
- `tasks/110d-ch80-ch100-validation-and-tuning.md` — Ch80-Ch100 快速验证与调优规划
- `logs/chapter_runs/run-33229919.jsonl` — Ch51-Ch59 实跑指标
