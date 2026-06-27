# Task 134: SettlementExtractor 角色状态与数值台账提取修复

> **类型**: 代码修复 / 事实源一致性  
> **日期**: 2026-06-27  
> **前置**: Task 111b（Settlement 与事实源一致性修复）、Task 129（enforce 模式 Ch1–Ch50 验证）  
> **目标**: 修复 enforce 模式下 `character_states` 和 `numerical_ledgers` 记录数为 0 的问题，确保 settlement extractor 能够正确建立角色状态快照和数值台账更新。

---

## 1. 背景与问题

`Task 129` enforce 模式验证（`run-89d7a2d4`）报告关键发现：

- `character_states`: 0
- `numerical_ledgers`: 0

这意味着 SettlementExtractor 未成功建立角色状态快照，也未更新数值台账。该问题直接违反 AGENTS.md 中的核心契约：

> “每章 accept 后必须执行 SettlementExtractor；character_states 快照表永远 INSERT，禁止 UPDATE。”
> “numerical_update.closing_value 必须等于公式值。”

在 observe 模式下，由于 `degraded_accept` 路径绕过了 settlement，该缺陷被掩盖；但在 enforce 模式下，它导致 settlement 失败并中断 run。

---

## 2. 根因假设（Brainstorming）

### 假设 A：SettlementExtractor 的 prompt 未正确要求输出角色状态 / 数值台账
Writer 1.1.0 变更后，settlement 输入格式或期望输出 schema 与 SettlementExtractor prompt 不一致。

### 假设 B：Parser 对角色状态 / 数值台账的提取失败但未报错
提取结果为空时，系统未抛出异常，而是静默跳过 INSERT。

### 假设 C：Schema 校验过滤了有效记录
Pydantic 模型变更导致合法的角色状态/数值更新被丢弃。

### 假设 D：QG false 降级接受导致 settlement 被跳过
Ch3/Ch11/Ch14/Ch15 因 QG 失败触发 `degraded_accept`，按设计跳过 settlement；但其他通过 QG 的章节（Ch1/Ch2/Ch4/Ch5 等）也记录为 0，说明提取本身存在问题。

---

## 3. 修复策略

1. **日志审计**：基于 `run-89d7a2d4` 的 JSONL 日志，定位 SettlementExtractor 的输入 prompt 和原始 LLM 输出，确认是否产生了角色状态/数值台账数据。
2. **Prompt 修复**：若 prompt 未明确要求，更新 SettlementExtractor 工艺卡，强制要求输出：
   - 每个出场角色的状态变化（state_key, old_value, new_value, source_quote）
   - 每个数值型设定的变化（ledger_key, opening_value, delta, closing_value, formula, source_quote）
3. **Parser 强化**：对空结果、schema mismatch、source_quote 不存在等情况显式报错，禁止静默跳过。
4. **空结果阻断**：若某章 accept 后 SettlementExtractor 返回空的 `character_states` 和 `numerical_ledgers`，但该章存在角色/数值线索，则进入 `settlement_review` 而非直接通过。
5. **回归测试**：新增单元测试和集成测试，覆盖角色状态提取、数值台账公式校验、空结果阻断。

---

## 4. 验收标准

- [ ] `pytest` 新增 8–12 个测试，覆盖 character_states / numerical_ledgers 提取与校验。
- [ ] enforce 模式 Ch1–Ch20 验证中，通过 QG 的章节 `character_states` + `numerical_ledgers` 记录数 > 0。
- [ ] `old_value` 与 DB 当前值一致率 ≥ 95%。
- [ ] `closing_value` 与公式计算值一致率 100%。
- [ ] 不破坏 observe 模式下 `run-a2bed648` 的 settlement 路径。
- [ ] `ruff check src/ tests/` 通过。
- [ ] 输出 `tasks/134-settlement-character-numerical-extraction-fix-DONE.md`。

---

## 5. 依赖关系

```
Task 111b Settlement 事实源一致性 ──┐
Task 129 enforce 验证 ──────────────┼──► Task 134 Settlement 提取修复
Task 130 模式决策 ──────────────────┘   （为 V5.2 enforce 默认启用提供证据）
```

---

## 6. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| Prompt 增强后 SettlementExtractor 输出过长 | 成本增加 / parser 不稳定 | 限制输出条目数，优先主角与数值线索 |
| 空结果阻断导致 observe 模式 150/150 失败 | 破坏基线 | 仅在 enforce 模式下启用阻断，observe 保持 warning |
| old_value 不一致率上升 | settlement_review 频繁触发 | 加强 source_quote 去噪与 DB 快照加载 |

---

## 7. 交付物

- `tasks/134-settlement-character-numerical-extraction-fix-DONE.md`
- SettlementExtractor / parser / schema 相关代码改动
- 新增测试文件
- enforce 模式 Ch1–Ch20 验证报告
