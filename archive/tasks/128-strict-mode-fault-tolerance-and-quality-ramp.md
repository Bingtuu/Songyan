# Task 128: 严格模式容错与开局期质量爬坡

> **类型**: 工程修复 / 流程重构  
> **日期**: 2026-06-26  
> **前置**: Task 127（score halt 重构）  
> **目标**: 解决 enforce 模式下因单章 QG false 导致整 run 终止的问题，为新项目开局期建立"质量爬坡"容错机制，使 Ch1–Ch150 baseline 重跑和后续 enforce 验证能够稳定进行。

---

## 1. 背景与问题

Task 128 原计划进行 enforce 模式 Ch1–Ch50 实跑验证，但实跑发现：

- Ch1 成功，gate 未触发。
- **Ch2 因 QG false 被 settlement 硬拦截，导致整 run 终止**。
- Ch2 `overall_score=0.6386`，`readability=0.3185`，`ai_tell_count=2`，`fatigue_word_count=7`。
- 经过两轮 revision，readability 未提升，说明 RevisionHandler 未能修复开局期 readability 问题。

根因不是 gate 阈值，而是：**pipeline 缺乏严格模式下的容错降级路径，且新项目开局期生成质量与统一 QG 标准不匹配**。

---

## 2. 目标

1. 让 QG false 不再导致整 run 终止，而是降级接受（`degraded_accept`）并继续。
2. 为 Ch1–Ch10 引入质量爬坡机制，使用更宽松的 QG 阈值。
3. 增强 RevisionHandler 对 readability / AI 腔 / 段落节奏的修复能力。
4. 在修复后重新跑通 Ch1–Ch150 baseline，确认没有状态污染。

---

## 3. 子任务

### 3.1 128a: 流程契约修复 — QG false 不终止 run

**问题**：Task 121m 的 QG false 硬拦截 settlement 导致章节 success=false，配合 `on_failure="abort"` 直接终止整 run。

**改动**：
- 在 `settlement_extractor` 或 `phase2_graph` 中，当 `quality_gate_passed=false` 时：
  - 跳过 settlement（不更新长期状态）。
  - 将章节标记为 `degraded_accept`。
  - 章节 `success=true`，但 `quality_gate_passed=false`。
  - run 继续下一章。
- 在 `chapter_run_log` 中新增字段：`degraded_accept=true`。

**验收**：
- Ch2 QG false 时，run 不终止，继续 Ch3。
- 长期状态（character_states、settings、foreshadowings）未被污染。

### 3.2 128b: 质量爬坡阈值 — Ch1–Ch10 宽松 QG

**问题**：统一 QG 标准对约束真空的新项目开局期不公平。

**改动**：
- 在 `ProjectSetting` 或 mode profile 中增加 `quality_ramp_chapters` 配置（默认 10）。
- Ch1–`quality_ramp_chapters` 使用宽松 threshold：
  - `readability` threshold 从 0.5 降至 0.3
  - `overall_score` threshold 从 0.7 降至 0.55
- Ch11+ 恢复严格 threshold。
- 在 score_card / quality_gate 判断逻辑中按章节号选择 threshold。

**验收**：
- Ch1–Ch10 在相同生成质量下 QG 通过率显著提升。
- Ch11+ 仍使用严格标准。

### 3.3 128c: RevisionHandler readability 修复增强

**问题**：Ch2 两轮 revision 后 readability 未变化，说明 revision prompt 没有针对 readability 指标。

**改动**：
- 当 `readability_ok=false` 时，调用专门的 readability revision 路径。
- 针对 `ai_tell_count`、`fatigue_word_count`、`paragraph_rhythm_score` 给出具体修改指令。
- 优先修复 AI 腔和段落节奏，再处理其他维度。

**验收**：
- 新增单元测试：模拟 readability 低的章节，revision 后 readability 提升。
- Ch2 实跑中 revision 能有效修复 readability 问题。

### 3.4 128d: Ch1–Ch150 baseline 重跑验证

**问题**：修复流程契约和质量爬坡后，需要确认长链稳定性。

**改动**：
- 使用默认配置（observe，无 enforce）重新跑 Ch1–Ch150。
- 记录 `degraded_accept` 章节数、ContextEmergency 次数、AutoHalt 次数。
- 检查是否有状态污染或连续性断裂。

**验收**：
- Ch1–Ch150 全部成功或明确降级接受。
- `degraded_accept` 章节集中在 Ch1–Ch10。
- ContextEmergency / AutoHalt 次数在可接受范围。

---

## 4. 验收标准

### 4.1 代码变更
- [ ] 128a: QG false 流程契约修复。
- [ ] 128b: 质量爬坡阈值机制。
- [ ] 128c: RevisionHandler readability 修复增强。
- [ ] 新增/更新相关单元测试和集成测试。

### 4.2 实跑验证
- [ ] 128d: Ch1–Ch150 baseline 重跑完成。
- [ ] `degraded_accept` 章节主要分布在 Ch1–Ch10。
- [ ] 无状态污染、无连续性断裂。

### 4.3 测试与 lint
- [ ] 全量 pytest 通过。
- [ ] `ruff check src/ tests/` 通过。

---

## 5. 依赖关系

```
Task 127 score halt 重构 ──┐
                           ├──► Task 128 严格模式容错与质量爬坡 ──┬──► Task 129 enforce 模式 Ch1–Ch50 验证
                           │                                       │
                           └── 发现 QG false 阻断 run 问题 ──────────┘
```

---

## 6. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| degraded_accept 导致状态污染 | 连续性断裂 | 跳过 settlement，不写入长期状态 |
| 质量爬坡阈值过宽 | 低质量章节被接受 | Ch11+ 恢复严格阈值；degraded_accept 章节限制在开局期 |
| RevisionHandler 增强引入新 bug |  revision 循环异常 | 新增单元测试覆盖 |
| Ch1–Ch150 重跑再次失败 | V5.1 阻塞 | 分析失败原因，必要时继续调整阈值或 prompt |

---

## 7. 交付物

- `archive/v5/tasks/128-strict-mode-fault-tolerance-and-quality-ramp-DONE.md`
- 代码改动：`src/songyan/workflows/phase2_graph.py`、settlement 相关模块、quality gate 相关模块、revision handler
- 新增/更新测试
- Ch1–Ch150 baseline 重跑日志与报告
- 全量 pytest / ruff 通过记录
