# Task 171p: Ch200 撞墙定点修复 —— state_mismatch 量具构念修正

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 D3 + §7 主线（`NNNp` 撞墙定点修复通道）
> **类型**: 定点修复（Task 171 D1 小窗口实跑反馈驱动）
> **优先级**: P0（挡住 D1 全量长跑）
> **依赖**: Task 171 小窗口实跑（run-ae6336b3，Ch3 halt）
> **状态**: ✅ **完成（演进型 field 构念修正；见 `171p-ch200-wall-fix-DONE.md`）**
> **负责人**: songyan-agent

---

## 立项依据（Task 171 小窗口实证）

Ch1-5 小窗口实跑在 **Ch3 被 `health_low_p1_halt: P1_count=11` 挡停**。诊断（`.tmp/diag_171p_mismatch.py` 读 continuity_reports）确认：**11 个 P1 全部是 `continuity_auditor._find_state_mismatches` 的假阳性**——它把**合理的角色发展**误判为"状态矛盾"：

- `emotional_state`：第1章"警觉、压抑的愤怒" → 第2章"震惊、决绝、嘲讽" —— 正常情绪演进。
- `knowledge`：第1章 → 第2章 → 第3章 **单调累积**（"确认A" → "确认A+B" → "确认A+B+C"）—— 角色**学到更多**被当成矛盾。

根因（`_scanners.py:_find_state_mismatches` L137-140）：**任意 field 在 2 章内 `prev != curr` 即判 mismatch**，未区分"本就该演进的 field"（emotional_state/knowledge）与"应稳定、变了才算矛盾的 field"。这与 Task 170 同类——**量具构念建错**，现在落在稳定性面上假阻塞长跑。

## 任务边界

**只修量具构念假阳性，不放宽任何冻结阈值**（health 阈值 7.0、P1 halt 语义均不动）。修正后 P1 只应包含真实矛盾（如"死亡→复活"、数值型硬冲突），不含正常演进/单调累积。

## 目标

1. **排除演进型 field**：`emotional_state`、`knowledge` 从 state-mismatch 检测排除（其变化是角色发展，非矛盾）。
2. **保留真实矛盾检测**：`physical_state`/`status`/`relationship_*` 等仍检测（这些字段"变了"更可能是真矛盾），窗口/语义不变。
3. **实证复验**：修正后在同一 DB（run-ae6336b3）重算 continuity，确认 Ch3 P1 从 11 降到合理值、health 不再假红线；小窗口 Ch1-5 可越过 Ch3。

## 验收标准
- `_find_state_mismatches` 排除演进型 field，有常量声明 + 注释说明构念依据。
- 单测：演进型 field 变化不计 mismatch；稳定型 field 真矛盾仍计。
- 复验：同 DB 重算 Ch3 continuity，P1 显著下降、health ≥ 7.0（或明确剩余为真矛盾）。
- `ruff`/pytest 通过；不放宽冻结阈值。

## 交付物
- `src/songyan/agents/continuity_auditor/_scanners.py` 修正 + 演进型 field 常量。
- `tests/test_171p_state_mismatch_construct.py`。
- 复验记录（写入本 spec 或 DONE）。
- `tasks/171p-ch200-wall-fix-DONE.md`。

## 明确不做
- 不放宽 health 7.0 / P1 halt 冻结口径；不改 gate 逻辑；不做 LLM 闭环；不在此扩大到非 state-mismatch 的其它 P1 源。
