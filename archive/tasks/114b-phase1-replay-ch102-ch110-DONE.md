# Task 114b: Phase 1 重跑 Ch102-Ch110 — 完成报告

> **Phase**: V5.0 Phase 4 — 150 章规模化验证
> **优先级**: P0
> **状态**: ⚠️ 熔断复核完成（Task 114b 未达出口条件；需进入 Task 114b2）
> **开始时间**: 2026-06-20
> **完成时间**: 2026-06-20

---

## 执行结果摘要

### ⚠️ Task 114a 修复验证（单元测试有效，实跑端到端未穿透）

**结论**：Task 114a 的 settlement 事实源契约修复在代码和回归测试层面有效，但 Task 114b 后两次实跑均因 QG 收敛失败提前 `_skip_settlement=True`，没有进入 `extract_settlement()`，因此不能作为端到端实跑通过证据。

| 修复项 | 验证结果 | 证据 |
|--------|---------|------|
| `old_value` 代码回填 | ⚠️ 待实跑穿透 | Ch103 回放在 settlement 前被 QG 阻断，无端到端验证日志 |
| `quote_filter` 角色名校验 | ⚠️ 待实跑穿透 | Ch103 回放未进入 quote_filter 实质验证 |
| `run_logger` 多维度判定 | ✅ 有效 | 日志显示 `settlement_success_calculated` 多维度检查 |
| 后处理触发条件收紧 | ✅ 有效 | 无旁路触发后处理 |

### ❌ QG 文学质量波动（非 Task 114a 范围）

**结论**：连续 2 章因 QG 文学质量分数过低导致 `settlement_success=false`，触发熔断条件。

| 章节 | Run ID | QG 失败原因 | settlement_success |
|------|--------|------------|-------------------|
| Ch103 | `run-385dc3e0` | `readability_score: 0.473` | `false` |
| Ch102 | `run-452c4f78` | `length_score: 0.440`（字数 2514，偏差 28%） | `false` |

**失败链路**：
```
LLM 生成内容质量波动
  → QG 维度分数低（< 0.5）
  → 修订耗尽（repair_exhausted=true，已修订 2 轮）
  → 触发 _convergence_failed=true 和 _skip_settlement=true
  → --auto-confirm 自动 accept 版本
  → settlement_extractor_node 检测到 _skip_settlement=true → 跳过 settlement
  → settlement_success=false，章节失败
```

**与原始失败的对比**：

| 章节 | 原始失败 (run-5105e24b) | 当前失败 |
|------|------------------------|----------|
| Ch102 | `quality_gate_passed=false` 但 `convergence_failed=false`, `settlement_success=true` | `quality_gate_passed=false` 且 `convergence_failed=true`, `settlement_success=false` |
| Ch103 | `quality_gate_passed=true` 但 `settlement_success=false`（old_value mismatch） | `quality_gate_passed=false` 且 `convergence_failed=true`, `settlement_success=false` |

**关键差异**：Task 113/111d 的收敛修复现在会在 QG 失败且修订耗尽时主动跳过 settlement，防止事实源污染。这是预期的保护机制，但也意味着文学质量波动会直接导致章节失败。

---

## 熔断条件分析

### ⚠️ 触发的熔断条件

**连续 Settlement 失败**：连续 2 章 `settlement_success=false`

### 根因分析

这 **不是** 系统性 settlement 阻断，也不是 Task 114a 修复的问题。根因是：

1. **LLM 生成质量波动**：Ch102 字数只有 2514（目标 3500，偏差 28%），Ch103 可读性分数只有 0.473
2. **收敛保护机制**：Task 107/113 的修复在修订耗尽且 QG 失败时主动跳过 settlement，防止事实源污染
3. **V5.0 限制**：根据 AGENTS.md P0 规则 #51，V5.0 阶段不做 Prompt 调优（字数控制、钩子质量属于 V5.1）

### 可修复性评估

| 修复方案 | 可行性 | 说明 |
|---------|--------|------|
| 调整 QG 阈值 | ❌ 违反 P0 规则 | V5.0 不做评分阈值调整 |
| 调整 Prompt 提高文学质量 | ❌ 违反 P0 规则 | V5.0 不做 Prompt 调优 |
| 调整 auto-confirm 策略 | ⚠️ 需评估 | 在 `_skip_settlement=true` 时不 accept 版本 |
| 接受部分章节失败，继续后续章节 | ❌ 暂不符合当前门禁 | Task 114a 尚缺端到端 settlement 实跑证据，不能直接进入 Task 114c |

---

## 验收标准评估

### Task 114a 修复验证（⚠️ 单元通过，实跑待补）

| 指标 | 目标 | 结果 |
|------|------|------|
| Ch103 无 `old_value mismatch` | ✅ 无 | ⚠️ 未进入 settlement，不能证明端到端通过 |
| Ch103 无 `quote_filter` 误杀 | ✅ 无 | ⚠️ 未进入 quote_filter 实质验证 |
| `run_logger` 多维度判定 | ✅ 生效 | ✅ 生效 |
| 后处理触发条件收紧 | ✅ 生效 | ✅ 生效 |

### Phase 1 完成率（❌ 未达目标）

| 指标 | 目标 | 结果 |
|------|------|------|
| Ch102-Ch110 完成率 | >= 80% | 0/2 已跑章节成功（0%） |
| QG 通过率 | >= 60% | 0/2（0%） |
| `budget_used` <= 1.0 | 每章 <= 1.0 | ✅ Ch102: 0.750, Ch103: 0.741 |
| 熔断触发 | 0 次 | ⚠️ 1 次（连续 settlement 失败） |
| 事实源污染 | 0 个 | ✅ 0 个 |

---

## 强制检查清单

### Ch103 回放（run-385dc3e0）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| JSONL `success` 字段状态正常 | ⚠️ | `success=false`（QG 失败导致） |
| `accepted_version_id` 无指向 abandoned | ✅ | 无事实源污染 |
| 每章 settlement + summary 已写入 | ❌ | `skip_settlement=true`，无 settlement |
| `budget_used` 趋势稳定 | ✅ | 0.741，无异常 |
| 无残留进程 | ✅ | 无残留 |
| 无熔断条件触发（事实源类） | ✅ | 无 old_value mismatch、无 quote_filter 误杀 |

### Phase 1 全量（run-452c4f78）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| JSONL `success` 字段状态正常 | ⚠️ | Ch102 `success=false`（QG 失败导致） |
| `accepted_version_id` 无指向 abandoned | ✅ | 无事实源污染 |
| 每章 settlement + summary 已写入 | ❌ | Ch102 `skip_settlement=true` |
| `budget_used` 趋势稳定 | ✅ | 0.750，无异常 |
| 无残留进程 | ✅ | 无残留 |
| 无熔断条件触发（事实源类） | ✅ | 无事实源类熔断 |

---

## 关键日志证据

### Ch103 回放（run-385dc3e0）

**未观察到 old_value mismatch，但不能视为端到端通过**：
```
# 日志中无 settlement.old_value_mismatch 或 settlement.validation_failed
# 但本次运行提前 _skip_settlement=True，未进入 extract_settlement()
# 因此不能证明 Task 114a 在真实 settlement 中端到端通过
```

**QG 失败导致 skip_settlement**：
```
2026-06-20 06:51:25 [warning] quality_gate.convergence_failed
  chapter_number=103
  failures=['readability_score:0.473']
  rollback_valid=True
2026-06-20 06:51:26 [info] settlement_extractor_node.skipping_settlement
  chapter_number=103
  version_id=v-103-5-2bd8f777
2026-06-20 06:51:27 [debug] run_logger.settlement_success_calculated
  chapter_number=103
  has_settlement_error=True
  has_settlement_id=False
  settlement_needs_review=True
  settlement_success=False
  skip_settlement=True
  success=False
```

### Ch102 全量重跑（run-452c4f78）

**未观察到 quote_filter 误杀，但不能视为端到端通过**：
```
# 日志中无 quote_filter.character_update_quote_filtered 或类似错误
# 但本次运行提前 _skip_settlement=True，未进入 quote_filter 实质验证
```

**QG 失败导致 skip_settlement**：
```
2026-06-20 06:58:54 [warning] quality_gate.convergence_failed
  chapter_number=102
  failures=['length_score:0.440']
  rollback_valid=True
2026-06-20 06:58:55 [info] settlement_extractor_node.skipping_settlement
  chapter_number=102
  version_id=v-102-5-b35fc126
2026-06-20 06:58:56 [debug] run_logger.settlement_success_calculated
  chapter_number=102
  has_settlement_error=True
  has_settlement_id=False
  settlement_needs_review=True
  settlement_success=False
  skip_settlement=True
  success=False
```

---

## 改动文件

无代码改动。Task 114b 是验证任务，不涉及代码修改。

---

## 已知限制与风险

### 已知限制

1. **V5.0 文学质量波动**：LLM 生成的内容质量存在波动，可能导致 QG 分数低于阈值
2. **收敛保护机制的副作用**：修订耗尽且 QG 失败时会跳过 settlement，防止事实源污染，但也导致章节失败
3. **V5.0 无法调优**：根据 AGENTS.md P0 规则 #51，V5.0 阶段不做 Prompt 调优和评分阈值调整

### 风险

1. **Task 114c 可能遇到同样问题**：Ch111-Ch150 也可能因 QG 文学质量波动导致章节失败
2. **完成率可能不达标**：如果文学质量波动频繁，Ch101-Ch150 完成率可能低于 95% 的目标

---

## 下一步建议

### 选项 1：进入 Task 114b2（推荐）

**理由**：
- Task 114b 未达出口条件，且没有穿透 settlement。
- 当前必须先处理 Ch102 length / Ch103 readability 在 settlement 前阻断的问题。
- 只有看到 Ch102/Ch103 短窗口 accept + settlement + summary 成功，才能进入 Task 114c。

**执行方案**：
1. 复核 Ch102 length 失败链路，避免 `length_score:0.440` 再次阻断。
2. 复核 Ch103 readability 失败链路，避免 `readability_score:0.473` 再次阻断。
3. 使用 Ch103 单章和 Ch102-Ch103 短窗口验证 settlement 端到端通过。
4. 验证通过后再启动 Task 114c Phase 2: Ch111-Ch130。

### 选项 2：先修复 auto-confirm 策略

**修改**：在 `_skip_settlement=true` 时，auto-confirm 不 accept 版本，而是直接标记为失败并继续下一章

**理由**：
- 避免 `accepted_version_id` 指向一个没有 settlement 的版本
- 可以更快地跑完所有章节，收集更多数据

**风险**：
- 需要修改代码，可能引入新的问题
- 违反"不在长跑中临时修改代码"的原则

### 选项 3：先解决 QG 文学质量问题（不推荐）

**理由**：
- 违反 AGENTS.md P0 规则 #51（V5.0 不做 Prompt 调优）
- 可能引入新的不稳定因素
- 延迟 V5.0 架构验证进度

---

## 参考文档

- `tasks/114a-settlement-fact-source-contract-fix-DONE.md` — Task 114a 修复完成文档
- `archive/v5/plans/114-ch101-ch150-streaming-validation.md` — Task 114 umbrella 历史规划稿
- `logs/chapter_runs/run-385dc3e0.jsonl` — Ch103 回放 JSONL
- `logs/chapter_runs/run-452c4f78.jsonl` — Ch102 全量重跑 JSONL
- `logs/task114/songyan-ch103-replay-20260620-064834.out.log` — Ch103 回放日志
- `logs/task114/songyan-phase1-102-110-20260620-065647.out.log` — Ch102 全量重跑日志
- `AGENTS.md` — P0 规则 #51：V5.0 不
