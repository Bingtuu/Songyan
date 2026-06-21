# Task 121a: V5.0 目标达成评估与 V5.1 下一步规划

> **类型**: 评估 / 决策备忘录  
> **日期**: 2026-06-21  
> **基准提交**: `016055c`  
> **结论**: V5.0 工程验收已达成；若严格要求“单命令一次性 Ch1-Ch150”，仍建议补一次 rehearsal 作为证据闭环。
> **执行更新**: Task 121b 已执行 rehearsal，`run-21ff158b` 在 Ch5 阻断，详见 `tasks/121b-ch1-ch150-single-run-rehearsal-DONE.md`。
> **修复更新**: Task 121c 已修复 rewrite fallback 后 settlement 被跳过的直接阻断，详见 `tasks/121c-rewrite-fallback-settlement-contract-DONE.md`。
> **编号更新**: Task 121 拆分为 121a/121b/121c/121d；本文为 121a 评估与规划，121d 负责修复后的 single-run 重跑。

---

## 1. 核心结论

### V5.0 是否达成目标

**达成，但需要区分两个口径。**

| 口径 | 判定 | 说明 |
|------|------|------|
| 工程验收口径 | ✅ 已达成 | Context Diet 2.0 四组件落地；Ch111-Ch150 40/40 成功；Task 115-120 关闭 P0/P1 风险；最终测试/lint 通过 |
| 单命令实跑口径 | ⚠️ 证据可补强 | 当前证据主要来自分段长跑、风险窗口复验和最终验收包；尚未看到一次从 Ch1 到 Ch150 的单一 uninterrupted run 作为最终证明 |

因此，V5.0 可以保持“通过验收”的结论；如果后续要对外宣称“一次性完成 150 章”，建议增加一次完整 rehearsal。

---

## 2. 证据表

| 证据 | 状态 | 说明 |
|------|------|------|
| Context Diet 2.0 四组件 | ✅ | TemporalCompressor、CharacterFocalDecay、SettingEvaporator、BudgetHardCeiling 已落地 |
| Ch111-Ch150 DG-2 | ✅ / ⚠️ | 40/40 成功，QG/settlement/summary 40/40；原 DG-2 条件通过风险已在 Task 115-117 关闭 |
| ContextEmergency 风险 | ✅ | Ch115/Ch120 复核为合理降级，Task 117 风险窗口复验未再触发 |
| Best-version 风险 | ✅ | Ch147/Ch148 复核通过，`quality_gate_router` 路由缺陷已修复 |
| ContinuityAuditor health_low | ✅ / P2 | 已有 P1/P2/P3 分级和 human marks 追踪；V5.0 维持软复核 |
| 报告与 wrapper | ✅ | `songyan report` 与加固 PowerShell wrapper 已交付 |
| P0/P1 风险 | ✅ | 当前为 0 |
| 最新全量回归 | ✅ | 当前为 `1718 passed, 2 xfailed, 15 warnings`；本文件初稿时为 `1718 passed, 1 xfailed, 1 xpassed, 14 warnings` |
| 最新 lint | ✅ | `ruff check src/ tests/` 通过 |

### 测试口径说明

最新清理后测试结果与 Task 120 完成时不同：

```text
1718 passed, 2 xfailed, 15 warnings
```

- `2 xfailed`: 已知非阻断项，包括 `test_concurrent_settlement_writes` 的 Windows SQLite 并发写入限制，以及 `test_audit_chain_mock_under_1s` 在冷启动/embedding model 加载条件下的性能 xfail。
- `0 skipped`: 之前 4 个同步测试 skip 已清理为正常通过。

---

## 3. V5.0 仍有的实际卡点

### 3.1 “一次性完成 150 章”证据链仍可补强

当前 V5.0 能力已经通过分段验证和窗口复验建立，但还没有单一 `run_id` 覆盖 Ch1-Ch150 的完整 rehearsal 证据。

**影响**：

- 不影响 V5.0 工程验收。
- 影响对外表达“单命令一次性完成 150 章”的严格性。

**当前状态**：

- Task 121b 已执行首次 rehearsal，`run-21ff158b` 在 Ch5 阻断。
- Task 121c 已修复直接阻断。
- Task 121d 负责重跑 Ch1-Ch150 single-run rehearsal，验证修复是否解除 Ch5 settlement skip。

### 3.2 Prompt 质量仍是主要体验瓶颈

V5.0 明确不做 Prompt 调优。历史记录显示以下问题仍更像 Prompt/质量策略问题，而不是 ContextEmergency 问题：

- DG-1 QG 通过率曾为 58.0%。
- 字数控制、钩子质量、叙事展开不足多次被标记为 V5.1 范围。
- `coherence_major` 和文本阅读体验虽被工程修复显著改善，但 Prompt 层仍是后续收益最大的位置。

### 3.3 health_low 已可追踪，但还不是硬门禁

Task 118 已建立 P1/P2/P3 分级和 `HumanMark.version_id/severity`，但没有让 health_low 阻断 accepted。

**当前判断**：

- 这对 V5.0 是合理取舍：避免误阻断长跑。
- 若要进入更严格质量阶段，可在 V5.1 对 P1 连续出现、state_mismatch、主线事实风险做 gate proposal。

### 3.4 ContextEmergency 不应优先硬门禁

Task 115/117 的证据显示，Ch115/Ch120 的 ContextEmergency 是合理降级，并且复验未再触发。

**当前判断**：

- `ContextEmergency` 是 BudgetHardCeiling 的保护机制，不应简单视为失败。
- 直接硬阻断所有 emergency 会降低 150 章跑通概率，并可能把合理降级误判为失败。

---

## 4. 下一步：ContextEmergency 硬门禁 vs Prompt 调优

### 推荐顺序

1. **先补一次 Ch1-Ch150 single-run rehearsal 证据**
2. **再做 Prompt 调优**
3. **最后做 ContextEmergency / health_low 硬门禁预研**

### 为什么不是先做 ContextEmergency 硬门禁

| 理由 | 说明 |
|------|------|
| 现有 emergency 风险已关闭 | Ch115/Ch120 复验通过，未形成当前 P1 |
| emergency 是保护机制 | 它用于避免超预算污染，不应简单当作失败 |
| 误阻断成本高 | 一次性 150 章更需要可恢复性，过早硬门禁会增加中断率 |
| health_low 数据刚完成治理 | 需要先观察 P1/P2/P3 与实际人工复核的相关性，再决定硬门禁 |

### 为什么 Prompt 调优优先级更高

| 理由 | 说明 |
|------|------|
| V5.0 多次明确留给 V5.1 | AGENTS.md P2-#51 和多个 Task 文档都将字数控制、钩子质量放到 V5.1 |
| 直接影响 QG 和阅读体验 | QG、字数、钩子、叙事展开都更靠近 Prompt 层 |
| 不破坏 P0 事实源契约 | 可在 Writer/CreativeDirector/SummaryWriter prompt 层迭代，不触碰 SQLite/state/settlement 边界 |
| 与 150 章目标互补 | Context Diet 解决“能跑长”，Prompt 调优解决“跑得好” |

---

## 5. 建议的 V5.1 任务拆分

### Task 121b: Ch1-Ch150 Single-Run Rehearsal 首轮

**目标**：验证一次性 150 章运行是否真实可达，并暴露首个明确失败点。

验收：

- 单一 run 覆盖 Ch1-Ch150。
- `success_rate == 100%` 或有明确失败点。
- 每章有 QG、settlement、summary、budget、health_low、ContextEmergency 指标。
- 输出 `songyan report --run-id <run_id>` 报告。

结果：

- `run-21ff158b` 在 Ch5 阻断。
- 结论不是“150 章已跑通”，而是“single-run rehearsal 已补测并暴露明确阻断点”。

### Task 121c: Rewrite Fallback Settlement Contract

**目标**：修复 Task 121b 暴露的 rewrite 回退后 settlement 被跳过问题。

结果：

- rewrite fallback 回退到可结算版本后不再透传 `_skip_settlement=True`。
- `_skip_settlement` 仅表示没有可安全结算正文。

### Task 121d: Ch1-Ch150 Single-Run Rehearsal 重跑

**目标**：在 Task 121c 后重跑 single-run rehearsal，验证 Ch5 settlement skip 阻断是否解除，并记录新的失败点或 150 章通过证据。

要求：

- 重跑前清理测试残留、进程残留和可安全清理的缓存/锁文件。
- 使用新的干净 rehearsal 项目或明确隔离的项目状态，避免复用 `proj-2375dbfc` 的 partial run 作为新证据。
- 保留 Task 121b 的 JSONL/report 作为历史证据，不删除数据库中的 partial 记录。
- 输出新的 `run_id`、JSONL、report 和 DONE 文档。

### Task 122: Prompt 调优一期

**目标**：提高 QG 稳定性和阅读体验，不改变事实源契约。

范围：

- Writer：字数控制、场景展开、结尾钩子。
- CreativeDirector：tension 与 forbidden_patterns 可执行性。
- SummaryWriter：摘要信息密度与下章钩子稳定性。

不做：

- 不新增 workflow 节点。
- 不放宽 QG 阈值。
- 不改 SettlementExtractor 事实验证规则。

### Task 123: ContextEmergency / health_low Gate Proposal

**目标**：把软信号升级为可解释的候选硬门禁，而不是直接阻断。

候选规则：

- 连续 N 章 P1 health_low。
- state_mismatch 且关联主线角色/设定。
- `budget_used_before_emergency > 1.0` 且 emergency 后仍 `budget_used > 1.0`。
- emergency 触发后缺失 settlement/summary 或导致 accepted 不一致。

---

## 6. 最终建议

**不要把 ContextEmergency 硬门禁作为下一步首要任务。**

V5.0 的目标已经在工程验收口径下完成；真正值得补的是“一次性 Ch1-Ch150 单命令 rehearsal”证据。完成这个 rehearsal 后，优先推进 Prompt 调优，因为它更直接对应当前剩余的质量瓶颈：QG、字数、钩子和叙事展开。

ContextEmergency / health_low 硬门禁应作为后续预研，基于 Task 118 的 severity 数据和 Task 115 的 emergency 可观测性做精细化 gate，而不是一刀切阻断。
