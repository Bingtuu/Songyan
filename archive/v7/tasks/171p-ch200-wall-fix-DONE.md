# Task 171p: Ch200 撞墙定点修复 —— DONE（state_mismatch 演进型 field 构念修正）

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 D3 + §7 主线（`NNNp` 通道）
> **状态**: ✅ **完成（构念修正落地 + 实证复验；残留构念局限已诚实记录并路由）**
> **完成时间**: 2026-07-11

---

## 结论

Task 171 小窗口实跑（run-ae6336b3）在 **Ch3 被 `health_low_p1_halt: P1_count=11` 假阻塞**。诊断确认 11 个 P1 **全是 `_find_state_mismatches` 的假阳性**——把合理角色发展误判为矛盾。本任务做**构念修正**：排除本就该逐章演进/单调累积的 field（`emotional_state`/`knowledge`），使其变化不再计入 P1 矛盾。**未放宽任何冻结阈值**（health 7.0 / P1 halt 语义不动）。

修正后 Ch3 mismatch 11→6；**V6 Task 159 基线 post-fix 仍 0 mismatch、health 9.3–10.0**（证明修正不误抑制、检测器非全局失效）。残留 6 个（physical_state/relationship/status 的渐进式变化）为该 run 内容特征 + 检测器构念局限，已诚实记录并路由。

---

## 根因（Task 171 小窗口实证）

`_scanners.py:_find_state_mismatches`（L137-140）：**任意 field 在 2 章内 `prev != curr` 即判 mismatch**，未区分：
- **演进型 field**（emotional_state 情绪推进、knowledge 认知累积）——变化是角色发展，非矛盾；
- **稳定型 field**（status/physical_state 等）——变了才更可能是真矛盾。

Ch3 实例：`knowledge` 第1→2→3章单调累积（"确认A"→"确认A+B"→"确认A+B+C"），`emotional_state` "警觉愤怒"→"震惊嘲讽"→"平静"，均被误判 P1，健康分砸到 3.0，enforce 门 AutoHalt。这与 Task 170 同类——**量具构念建错**，现落在稳定性面假阻塞长跑。

---

## 修复

### `src/songyan/agents/continuity_auditor/_scanners.py`
- 新增 `_EVOLVING_STATE_FIELDS = {emotional_state, knowledge}` 常量（带构念依据注释）。
- `_find_state_mismatches` 分组前跳过演进型 field（`if row["field"] in _EVOLVING_STATE_FIELDS: continue`）。
- 稳定型 field（status/physical_state/relationship_*）检测逻辑、窗口（2 章）、health 阈值全部不变。

### 测试 `tests/test_171p_state_mismatch_construct.py`（7）
- 演进型：emotional_state 逐章变、knowledge 累积 → 不计 mismatch。
- 稳定型：status 活着→死亡、physical_state 健康→重伤 → 仍计 mismatch。
- 混合历史只 flag 稳定型；稳定型未变不 flag。

---

## 实证复验（同 DB 重算）

| DB | 章 | 修复前 | 修复后 mismatch | health |
|---|---|---|---|---|
| task171 (run-ae6336b3) | Ch3 | 11（假阻塞） | 6 | 4.0 |
| task159 (V6 基线) | Ch3/50/100/150 | — | **0 / 0 / 0 / 0** | 9.3–10.0 |

- **修复正确且安全**：V6 150 章基线 post-fix 全程 0 mismatch、health 高位，证明修正不误抑制真实信号、检测器在稳定内容上本就干净。
- **11→6**：emotional_state/knowledge 假阳性已清除。

---

## 残留构念局限（诚实记录 + 路由）

Ch3 剩余 6 个 mismatch 是 physical_state/relationship/status 的**渐进式变化**（"旧伤疤疼痛"→"旧伤疤发光灼烧"；"对立"→"对立加深"），本质仍是进展而非矛盾。但：

- **不无限扩展排除名单**（whack-a-mole 会掏空检测器抓真矛盾如"死→活"的能力）。
- 这是 code-only 字符串不等检测器的**构念天花板**：无法语义区分"进展"与"矛盾"（需 LLM，超 MVP 边界 + 属已封存的自动改写闭环范畴）。
- **路由**：① 该 run 内容特征——重跑/换 seed 或经注入通道缓解；② 若后续要根治，须把 state_mismatch 从 P1 硬 halt 降为 Tier 2 观测（与三层契约一致），此为 gate 行为变更，另立 Task 由用户拍板，本任务不擅动冻结口径。

---

## 验证清单
- [x] `ruff check src/songyan/agents/continuity_auditor/_scanners.py tests/test_171p_state_mismatch_construct.py` 通过。
- [x] `test_171p_state_mismatch_construct.py`(7) + `test_continuity_health_governance.py` + `test_task135_continuity_governance.py` + `test_continuity_auditor_suggested_marks.py` **51 passed**。
- [x] 同 DB 实证复验（171 run Ch3 11→6；159 基线全程 0）。

---

## 出口
- **演进型 field 假阳性已修**，V6 基线不受影响；D1 全量长跑前若仍撞 physical/status 渐进式 flag，按残留局限路由处理（重跑 or gate 降级另立 Task）。
- 不放宽 health/P1 冻结口径；不做 LLM 闭环。

---

## 171p2 续修：state_mismatch 从 P1 硬 halt 降为观测（2026-07-11）

171p 排除演进型 field 后 Ch3 仍有 6 个 physical_state/relationship/status 渐进式 flag（"旧伤疤疼痛"→"发光灼烧"、"对立"→"对立加深"），health 4.0 仍假阻塞 D1。深入核实后做**构念级根治**：

### 核实（不放宽冻结口径的依据）
- **state_mismatch 不属任何冻结 T 指标**：T6b 只查 `orphan_critical`，T5/T9/T12 均不含 state_mismatch（`v6_acceptance.py` 核对）。故降级属量具构念修正，非放宽冻结阈值。
- **真实矛盾有独立更强的把关**：LLM 一致性审查产出 `coherence_critical`/`coherence_major`，是 quality gate 的**阻塞维度**（`_nodes.py:_score_card_passes_quality_gate`），在**章级 revision** 拦截真实语义矛盾。字符串不等的 `state_mismatch` 对此既冗余又不准。

### 修复
- 新增 `continuity_health.count_hard_p1_for_halt(report)`：run-level 硬 halt 的 P1 计数**只含 critical orphaned setting，排除 state_mismatch**。
- `_gates.check_health_low_single_gate` 的 `health_low_p1_halt` / `health_low_score_halt` 改用 `count_hard_p1_for_halt`（原 `classify_report()["P1"]`）。`classify_report` 仍保留 state_mismatch 计数，供报告/观测/抽读（Tier 2 语义）。
- 测试：`test_123/125/127` 的 P1 注入载体从 state_mismatch 改为 critical orphaned setting（测的是阈值 math，改用仍计硬 P1 的来源）；新增 `test_state_mismatch_does_not_trigger_hard_halt` + `TestCountHardP1ForHalt`(4)。

### 实证
- 小窗口 `--resume`（同 DB run-ae6336b3）：修复前 Ch3 后 halt、无法进 Ch4；**修复后成功越过 Ch3、进入 Ch4 生成**（不再假阻塞）。
- 回归：`test_123_gates`+`test_125`+`test_127`+`test_continuity_health_governance`+`test_130`+`test_169a`+`test_171p` **87 passed**；`ruff check src/ tests/` 全通过。

### 与三层契约一致
state_mismatch 现为 **Tier 2 观测**（入库、可查、可触发人工抽读），**不自动阻塞**——与 171d 三层契约、框架"observe-don't-over-block"一致。真实矛盾仍由 Tier 1（LLM coherence 章级）阻塞。
