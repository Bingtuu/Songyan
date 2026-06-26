# Task 123: ContextEmergency / health_low 候选硬门禁提案

> **日期**: 2026-06-26
> **类型**: V5.1 预研 / 候选硬门禁设计
> **状态**: **✅ DONE**
> **前置**: Task 115（ContextEmergency 复核）、Task 118（ContinuityAuditor health_low 分级与 human marks 追踪）、Task 122d（150 章压力测试）已完成
> **实现文件**:
> - `src/songyan/models/gate_config.py`
> - `src/songyan/workflows/_gates.py`
> - `src/songyan/workflows/phase2_graph.py`
> - `src/songyan/models/run_log.py`
> - `src/songyan/workflows/_run_logger.py`
> - `src/songyan/models/context.py`
> - `src/songyan/db/schema.sql`
> - `src/songyan/db/migrations.py`
> - `src/songyan/db/repository.py`
> - `tests/test_123_gates.py`
> **关联文档**: `tasks/121a-v50-goal-assessment-and-v51-plan.md`、`tasks/115-context-emergency-review-DONE.md`、`tasks/118-continuity-health-governance-DONE.md`

---

## 1. 目标

把当前两个**软复核信号**升级为**可配置、可解释、可观测的候选硬门禁**，同时保持 V5.0 已验证的 150 章长跑能力不被误伤。

具体目标：

1. 为 `health_low` 设计一套基于 severity（P1/P2/P3）和连续 streak 的候选硬门禁规则。
2. 为 `ContextEmergency` 设计一套基于超预算程度和降级后果的候选硬门禁规则，与现有 AutoHalt 的 `context_emergency_degraded_streak` 互补。
3. 提供**观测模式**（只记录、不阻断）和**门禁模式**（触发即 pause run）两种运行方式，默认观测模式。
4. 输出一份可落地的任务文档、单测方案和风险评估，为后续是否开启硬门禁提供数据依据。

---

## 2. 现状与调研结论

### 2.1 `health_low` 现状

- **检测位置**: `src/songyan/agents/continuity_auditor/__init__.py`
- **调用点**: `src/songyan/workflows/phase2_graph.py` 的 `_run_single_chapter()`，每 3 章调用一次（`chapter_number % 3 == 0`）。
- **输出**: `ContinuityReport`，包含 `overall_health_score`、`orphaned_settings`、`state_mismatches`、`forgotten_items`、`overdue_foreshadowings`。
- **HumanMark 写入**: `write_constraints()` 把问题写入 `human_marks` 表，字段含 `severity`（P1/P2/P3）和 `version_id`。
- **当前影响**: **软信号**。只会写入 human marks 和记录 `ChapterRunLog.continuity_health_score`，**不阻断 accept / settlement / summary**。
- **P1 来源**: `state_mismatches`、critical orphaned settings、`priority == 9` 的角色矛盾。

### 2.2 `ContextEmergency` 现状

- **触发条件**: `ContextPackage.budget_used > 1.0`，由 `BudgetPruner._context_emergency()` 触发。
- **可观测字段**: `context_emergency`、`context_emergency_level`（固定 3）、`budget_used_before_emergency`。
- **当前影响**:
  - 单章内：清空软分区、只保留最高优先级角色，保证生成仍可继续。
  - 批量层：`_check_auto_halt_window()` 已实现 `context_emergency_degraded_streak`——连续 3 章 emergency 且伴随 `success=False` / `quality_gate_passed=False` / `settlement_success=False` / `summary_success=False` 时 pause run。
- **数据通道**: `ChapterRunLog`、`chapter_versions.generation_metadata.context_snapshot`、`context_snapshots` 均有记录。

### 2.3 AutoHalt 现状

- **位置**: `src/songyan/workflows/phase2_graph.py:145`
- **当前 reason**:
  - `quality_gate_fail_streak`: 连续 3 章 QG 失败。
  - `context_emergency_degraded_streak`: 连续 3 章 ContextEmergency 且伴随降级。
- **状态**: 触发后 `ProjectRunState.status = "paused"`，抛出 `AutoHaltException`。
- **数据窗口**: `recent_results` 最近 3 章，含 `success`、`quality_gate_passed`、`context_emergency`、`settlement_success`、`summary_success`。

### 2.4 关键设计判断

- **最自然的接入点是 Phase2 编排层**，复用 AutoHalt 的状态机（`paused` + `AutoHaltException`）。
- 如果规则是 **streak-based**（连续 N 章异常），直接扩展 `_check_auto_halt_window` 最轻量。
- 如果规则是 **单章即时熔断**（如任一 P1 即暂停），应在 `_run_single_chapter` 的 ContinuityAuditor 调用后新增判断，而不是混入 streak checker。
- 两种规则都应支持配置开关和观测模式，避免 V5.0 已验证的长跑被误阻断。

---

## 3. 候选硬门禁规则

### 3.1 health_low 候选规则

#### 规则 A：P1 零容忍（单章即时）

- **条件**: 当前章 ContinuityAuditor 产生任意 P1（`state_mismatch` 或 critical orphaned setting）。
- **动作**: pause run，进入人工复核。
- **理由**: P1 通常意味着角色状态矛盾或核心设定冲突，继续生成会污染事实源。
- **风险**: 长跑中可能因偶发的扫描误判导致频繁暂停，需要配合 severity 校准。

#### 规则 B：连续 health_low streak（批量趋势）

- **条件**: 最近 3 章（或每 3 章审计点）`overall_health_score < threshold`，且其中 P1 ≥ 1 或 P2 ≥ 2。
- **动作**: pause run。
- **理由**: 捕捉持续退化趋势，避免单章偶发噪音。
- **可配置参数**:
  - `health_low_threshold`: 默认 `7.0`（与现有 `continuity_health_threshold` 一致）。
  - `health_low_p1_limit`: 默认 `1`（任意 P1 触发）。
  - `health_low_p2_limit`: 默认 `2`（连续 2 个 P2 触发）。

#### 规则 C：绝对低分（单章即时）

- **条件**: `overall_health_score < 3.0`。
- **动作**: pause run。
- **理由**: 即使 P1 计数为 0，极低分也说明连续性已严重劣化。

### 3.2 ContextEmergency 候选规则

#### 规则 D：超预算硬门禁（单章即时）

- **条件**: `context_emergency == True` 且 `budget_used_before_emergency > 1.3`（即硬断言核裁 `HARD_ENFORCE_THRESHOLD` 仍无法压回预算）。
- **动作**: pause run。
- **理由**: 当前 `ContextEmergency` 只表示 budget_used > 1.0，而 `budget_used_before_emergency > 1.3` 代表超预算程度更严重，继续生成的上下文已被大幅裁剪，质量风险高。
- **可配置参数**:
  - `emergency_budget_ratio_threshold`: 默认 `1.3`。

#### 规则 E：emergency 导致关键阶段失败（单章即时）

- **条件**: `context_emergency == True` 且（`settlement_success=False` 或 `summary_success=False`）。
- **动作**: pause run。
- **理由**: emergency 已经实际造成了事实源或摘要缺失，需要人工介入。
- **注意**: 当前 `context_emergency_degraded_streak` 是 streak-based 版本，规则 E 是其单章即时版本。

#### 规则 F：连续 emergency streak（已存在，可扩展）

- **条件**: 连续 3 章 `context_emergency=True` 且伴随降级。
- **动作**: pause run。
- **现状**: 已在 `_check_auto_halt_window` 中实现，本任务可保持或调整阈值。

---

## 4. 不做范围

以下事项**不属于** Task 123，避免与 V5.0 已收口的事实源契约冲突：

1. **不修改 SQLite 事实源契约**: 不改 `SettlementExtractor` 校验规则、不新增业务表、不改 `ChapterVersion` / `ChapterHead` 状态语义。
2. **不放宽 QualityGate 阈值**: 硬门禁是对 QG 的补充，不是替代。
3. **不做 Prompt 调优**: 因 ContextEmergency 或 health_low 暴露的质量问题，由 V5.1 Prompt 专项处理，本任务只负责 gate 机制。
4. **不新增 LangGraph 节点**: 接入点限制在 `phase2_graph.py` 的编排层，不在 Phase1 单章图内新增节点。
5. **不默认开启硬门禁**: 默认运行观测模式，所有规则以告警/记录方式输出，不直接 pause run，除非显式配置。
6. **不做 150 章实跑验收**: 本任务只需 Mock 单测和集成测试验证；实跑验证留到 Task 123 完成后由后续任务执行。

---

## 5. 验收标准

### 5.1 必选项（Must Have）

- [x] 新建 `tasks/123-context-emergency-health-low-gate-proposal.md` 并明确目标、规则、验收标准和不做范围。
- [x] 实现一个可配置的 **GateConfig**，支持以下开关：
  - `health_low_gate_enabled`: bool，默认 `False`。
  - `health_low_p1_halt`: bool，默认 `False`。
  - `health_low_streak_halt`: bool，默认 `False`。
  - `context_emergency_single_halt`: bool，默认 `False`。
  - `context_emergency_streak_halt`: bool，默认 `True`（保持现有行为）。
- [x] 在 `_check_auto_halt_window` 中新增基于 `health_low` 的 streak reason（规则 B），并补充到 `recent_results` 数据窗口。
- [x] 在 `_run_single_chapter` 的 ContinuityAuditor 调用后，新增基于 P1 / 绝对低分的单章即时判断（规则 A/C），默认不触发，仅记录观测日志。
- [x] 在 `_run_single_chapter` 中，新增基于 `budget_used_before_emergency` 的单章 ContextEmergency 硬门禁（规则 D），默认不触发。
- [x] 所有新 reason 统一使用 `AutoHaltException`，`reason` 字段新增：
  - `health_low_p1_halt`
  - `health_low_streak_halt`
  - `context_emergency_budget_ratio_halt`
- [x] `ChapterRunLog` 扩展字段记录触发 gate 的详细指标（`continuity_health_severity`、`gate_triggered`、`gate_reasons`、`gate_mode`）。
- [x] 单测覆盖：
  - health_low P1 单章触发/不触发。
  - health_low 连续 streak 触发/不触发。
  - ContextEmergency `budget_used_before_emergency > 1.3` 触发/不触发。
  - 配置开关关闭时，只记录不阻断。
- [x] 新增 `tests/test_123_gates.py` 16 个测试全部通过。
- [x] `ruff check src/ tests/` 通过；全量 pytest `1800 passed, 1 xfailed, 2 warnings`，零回归。

### 5.2 可选项（Nice to Have）

- [ ] 在 `human_gate_node` 的 interrupt payload 中增加 `continuity_warnings` 列表，让人工复核时可见 health_low 详情。
- [ ] 提供一个 CLI 命令或配置脚本，方便在观测模式和门禁模式之间切换。
- [ ] 基于 `run-a2bed648` 历史数据做离线影响面分析：若当时开启各规则，会 pause 在哪些章节。

---

## 6. 交付物

1. `tasks/123-context-emergency-health-low-gate-proposal.md`（本文档）。
2. 代码改动（已完成）：
   - `src/songyan/models/gate_config.py`：新增 `GateConfig` 配置模型。
   - `src/songyan/workflows/_gates.py`：新增纯逻辑门禁判断函数。
   - `src/songyan/workflows/phase2_graph.py`：扩展 `_check_auto_halt_window`、`_append_recent_result`、`_run_single_chapter`。
   - `src/songyan/models/run_log.py`：扩展 `ChapterRunLog` 字段（`continuity_health_severity`、`gate_triggered`、`gate_reasons`、`gate_mode`）。
   - `src/songyan/workflows/_run_logger.py`：透传 gate 字段。
   - `src/songyan/workflows/_nodes.py`：`_save_context_snapshot` 写入 `context_emergency_level`。
   - `src/songyan/models/context.py`：`ContextSnapshot` 增加 `context_emergency_level`。
   - `src/songyan/db/schema.sql`、`src/songyan/db/migrations.py`、`src/songyan/db/repository.py`：补齐 `context_snapshots` 可观测性字段。
3. 单测：`tests/test_123_gates.py`（16 个测试覆盖 GateConfig、health_low 单章/连续、ContextEmergency 单章、`_check_auto_halt_window` streak 集成）。
4. 影响面分析报告（可选，基于 `run-a2bed648` 数据）—— 未执行。

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| P1 误判导致长跑频繁暂停 | 150 章实跑成功率下降 | 默认观测模式；P1 规则可单独开关；连续 streak 优先于单章即时 |
| `budget_used_before_emergency` 缺失稳定数据 | 规则 D 无法可靠触发 | 先补齐 `context_snapshots` 表字段和 Repository 写入；本任务先以 `budget_used` 和 `_budget_was_enforced` 组合兜底 |
| 与现有 AutoHalt 混淆 | 维护成本增加 | 新 reason 独立命名，统一走 `AutoHaltException`，文档明确区分 streak / single-chapter 语义 |
| 人工复核成本上升 | 每次 pause 都需要人工判断 | human_gate_node 展示详细指标；后续可基于 severity 数据自动建议 accept/reject |

---

## 8. 建议的启动顺序

1. **Step 1**: 补齐可观测性——确保 `ChapterRunLog` 已稳定记录 `continuity_health_score`、`health_low_severity`（P1/P2/P3 计数）、`budget_used_before_emergency`。
2. **Step 2**: 实现配置模型与观测模式——所有规则先以 warning 方式输出，不阻断。
3. **Step 3**: 实现 streak-based health_low gate（规则 B），扩展 `_check_auto_halt_window`。
4. **Step 4**: 实现单章即时 health_low gate（规则 A/C）和 ContextEmergency budget ratio gate（规则 D），默认关闭。
5. **Step 5**: 单测、集成测试、全量回归、ruff。
6. **Step 6**（可选）: 基于 `run-a2bed648` 做离线影响面分析，决定是否调整默认阈值。

---

## 9. 相关代码入口

- `src/songyan/agents/continuity_auditor/__init__.py`
- `src/songyan/agents/continuity_auditor/_constraints.py`
- `src/songyan/agents/continuity_auditor/continuity_health.py`
- `src/songyan/agents/context_manager/__init__.py`（BudgetPruner / `_context_emergency`）
- `src/songyan/workflows/phase2_graph.py`（`_run_single_chapter`、`_check_auto_halt_window`、`_append_recent_result`）
- `src/songyan/models/project_run.py`
- `src/songyan/models/run_log.py`
- `src/songyan/exceptions.py`（`AutoHaltException`）

---

**一句话总结**：Task 123 的目标是把 `health_low` 和 `ContextEmergency` 从“可观测软信号”升级为“可配置候选硬门禁”，默认观测模式，复用 AutoHalt 状态机，先通过单测和配置开关验证机制正确性，再决定是否在生产长跑中开启。
