# Task 159: Ch1-Ch150 治理管线复现 + V6 阶段验收

> **Phase**: V6 阶段 D（长窗口验证）
> **优先级**: P0（V6 阶段验收出口——逐条核对 §1.3 N/D/S/R/V，产出 V6 验收报告）
> **依赖**: Task 157（harness + Ch50）、Task 158（Ch100 + kill→resume + T5 冻结）均达标
> **预计工作量**: 大（Ch1-Ch150 长跑 >15h；拆 159a 复现长跑 + 逐项基线对比 + 159b V6 验收报告 N/D/S/R/V）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 D + §1.3

---

## Goal

在 V5.2 + 骨架 + 末端治理 + 长跑底盘的**真实合入管线**上复现 V5.1 的 150 章里程碑（替代旧 `run-a2bed648`），并**逐项与旧基线对比**：orphan 斜率不高于 138n、P1 critical orphan=0、文学趋势无 T3 红线、质量债无 T4 红线、≥1 条主线线索全程 T1 可追溯。最终产出 **V6 验收报告**，逐条核对 §1.3 的 **N/D/S/R/V** 五项判定，给出 V6 阶段是否通过的结论。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- **复现目标基线**：`run-a2bed648`（V5.1 Ch1-Ch150 干净 single-run，150/150 accept、ContextEmergency=0、AutoHalt=0、degraded=0、failed=0，见 `docs/STATUS.md`）。V6 要在**新管线**（含骨架 141-144 + 度量 145-148 + 治理 149-152 + 底盘 153-156）上取得**不劣于**该基线的 150 章证据，且新增可度量的主线对象。
- **验收判据 harness（Task 157 交付、158 已在 Ch100 验证规模）**：`evaluate_v6_acceptance(project_id, 1, 150, ...)` 一次性出 T1-T8 三态。**159 不重写判据，只在 150 章规模调用 + 逐项与 138n/a2bed648 对比**。
- **五类曲线 + 主报告**：`render_stage_a_metrics(project_id, 1, 150)`（`songyan metrics --chapters 1-150`）。orphan/T7/质量债/文学/弧级兑现 + T5 遥测段全在其中。
- **§1.3 N/D/S/R/V 判定项**（v6-plan L26-31）：
  - **N（骨架）**：项目携带大纲/弧；GoalPlanner 输入含弧上下文（`context_snapshots` 可验证 `derived_from_arc`）；Ch1-Ch50 ≥1 条主线线索完成 T1 跃迁。
  - **D（度量）**：五类长期指标入库且 `songyan metrics` 可查。
  - **S（源头收敛）**：满足 T6（orphan 斜率下降 + T6c 归因）。
  - **R（可靠）**：单命令无人值守 Ch1-Ch100 + kill→resume 续完（**Task 158 已证**，159 引用其证据，不重复 kill 演练，除非 150 章链路有别）。
  - **V（验证）**：V5.2+骨架管线上 Ch1-Ch150 连续运行证据（非旧 a2bed648），全程满足 T3/T4/T5 红线。
- **阈值全部已冻结**：T3/T6a/T6b/T8（148z）、T4（157 首判 50 章满窗）、T5（158 Ch100 冻结）。159 是**全阈值同时在 150 章成立**的终检。
- **历史对照 DB**：`.tmp/task138n_ch1_ch30_rerun.db`（orphan 斜率基线）、`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`（T7 基线）；a2bed648 run log。

**为什么这是收官**：157 证 50 章 + harness、158 证 100 章 + 可靠性 + T5。159 把窗口拉到 150 章、与历史基线正面对比、并把 §1.3 五项判定写成一份可被不在场者复核的验收报告——这是 V6 "阶段验收"的定义（v6-plan L148）。

## Cross-Task Coordination（阶段 D 统一口径）

- **判据/曲线全部复用**：T1-T8 走 157 的 `evaluate_v6_acceptance`；五类曲线走 `render_stage_a_metrics`。159 只在 150 章规模跑一遍 + 做基线对比 + 写 N/D/S/R/V 核对，**不新增判据函数、不 fork**。
- **R 项引用而非重跑**：§1.3-R 的 kill→resume 已由 Task 158 在 Ch100 实证；159 的 R 判定**引用 158 报告**。仅当 150 章链路与 100 章有实质差异（如项目大纲/弧规划显著不同、新增主线线索导致 checkpoint 模式变化）才补一次 150 章内的 resume 演练；DONE 说明是否补及判断依据。
- **逐项对比口径**：与 a2bed648 对比"不劣于"= 完成率不低于、orphan 斜率不高于 138n、P1=0、无 T3/T4/T5 红线、且**额外**具备 a2bed648 没有的可追溯主线线索（T1）与五类度量（D）。V6 不是"数字更漂亮"，而是"同等稳定 + 可度量可治理"。
- **纯验证边界**：不改任何代码；若 150 章暴露真退化 → 新开修复 Task（如 159p），V6 验收结论标"条件通过/不通过"并列明阻断项，不在 159 里改治理。

### V6 验收报告结构（权威定义）

报告 `docs/reports/task-159-v6-final-acceptance-report.md` 必须逐条给出：

| 项 | 判据（可判定） | 证据来源 | 结论 |
|----|----------------|----------|------|
| **N 骨架** | 大纲/弧携带 + GoalPlanner 弧上下文（`context_snapshots.derived_from_arc`）+ Ch1-Ch50 ≥1 主线 T1 跃迁 | NarrativeRepository / context_snapshots / `check_t1` | pass/fail |
| **D 度量** | 五类指标入库且 `songyan metrics 1-150` 可查、无断档 | `render_stage_a_metrics` 输出 | pass/fail |
| **S 收敛** | T6a 斜率 ≤138n×0.5 + T6b P1=0 + T6c 归因成立 | `evaluate_v6_acceptance` T6* | pass/fail |
| **R 可靠** | 单命令无人值守 Ch100 + kill→resume（引用 Task 158） | Task 158 报告 | pass/fail |
| **V 验证** | 新管线 Ch1-Ch150 连续证据 + 全程 T3/T4/T5 不破 | 本 Task 长跑 + `evaluate_v6_acceptance` | pass/fail |

- 每项附**实测值 + 阈值 + 与基线对比**，并引用具体 run_id / 报告路径 / harness 三态输出，使不在场者能独立复核真假。
- 末尾给**总结论**：五项全 pass → V6 通过；任一 fail → 条件通过/不通过 + 阻断项 + 后续 Task。

## In Scope（必须完成）

### 159a — Ch1-Ch150 复现长跑 + 逐项基线对比
- [ ] 隔离副本 DB（带大纲项目）单命令无人值守跑 Ch1-Ch150，enforce 门禁；metrics 逐章追加 `.tmp/task159_ch1_ch150_metrics.jsonl`。on_failure/预算选型与 158 一致或说明差异。
- [ ] 取得新 run_id（**非** a2bed648）的 150 章证据；记录完成率、AutoHalt、degraded、failed。
- [ ] 逐项与基线对比：orphan 斜率 vs 138n、P1 critical orphan（=0）、T7 速率 vs 138k、文学趋势（无 T3）、质量债（无 T4）、T5（承接 158 冻结阈值，150 章不超）。
- [ ] 若中途触红线/AutoHalt：记录确切章 + 根因，判"真退化→新开修复 Task、V6 条件不通过"或"波动→记录"，不改治理。

### 159b — V6 验收报告 N/D/S/R/V
- [ ] `evaluate_v6_acceptance(1,150)` 出全 T1-T8 三态；`songyan metrics 1-150` 出五类曲线。
- [ ] 按 **Cross-Task Coordination「V6 验收报告结构」** 逐条核对 N/D/S/R/V，每项给实测值/阈值/基线对比/证据引用/pass-fail。
- [ ] 产出 `docs/reports/task-159-v6-final-acceptance-report.md`（V6 阶段验收报告），含逐章/检查点（Ch1/Ch50/Ch100/Ch150）表 + 五类曲线 + harness 三态 + N/D/S/R/V 核对表 + 与 a2bed648 逐项对比 + 总结论。
- [ ] 更新 V6 事实文档：`tasks/V6-README.md`（159 状态 + 阶段 D 出口 + V6 验收结论）、`docs/STATUS.md`、`docs/INDEX.md`（如需）。

## Out of Scope（明确不做）

- 不改任何治理/门禁/阶段 C 代码或 157 harness（纯验证；缺陷另开 Task）。
- 不重复 158 已完成的 kill→resume 演练（除非 150 章链路与 100 章相比存在显著不同的弧规划/大纲结构或 checkpoint 模式差异）。
- 不冻结新阈值（全部已在 148z/157/158 冻结）。
- 不承诺 Ch300 或 200+（那是 V7）。
- 不新增 LLM 判据。

## 测试要求

> **测试哲学**：159 的判据可信度完全由 Task 157 的 Layer 2 harness 单测背书（150 章只是更大样本，不改判据）。因此 159 **不新增判据单测**；Layer 2 仅对本 Task 新增的一次性复现脚本 + N/D/S/R/V 汇总渲染做冒烟，确保脚本与报告拼装不出错。真正的验收是 Layer 3 的 150 章实跑 + 报告核对。

### Layer 2: 复现脚本 + 验收汇总渲染冒烟（临时 SQLite，Mock/短程）
- [ ] 复现脚本章范围/metrics jsonl/report 路径解析：3-5 章 Mock 跑通，断言 jsonl 与 run_id 记录正确（不跑真 LLM）。
- [ ] **N/D/S/R/V 汇总渲染**：喂合成的 `V6AcceptanceResult` + 基线对比数据，验证报告表格五项都能生成 pass/fail 行、总结论正确（五项全 pass→通过；含 fail→条件不通过 + 列阻断项）。复用 157 的 `render_v6_acceptance_section`，只测 159 的汇总拼装。
- [ ] 基线对比逻辑：合成 orphan 斜率略高/略低于 138n、P1=0/>0，验证"不劣于基线"判定正确。

### Layer 3: Ch1-Ch150 复现长跑（V6 阶段验收出口）
- [ ] 新管线单命令跑完 Ch1-Ch150（150/150 或明确 AutoHalt 根因），取得新 run_id 证据。
- [ ] `evaluate_v6_acceptance(1,150)`：T2 完成、T6（S）、T3/T4/T5（V）不破、T1（N）可追溯。
- [ ] 逐项与 a2bed648/138n/138k 对比"不劣于"成立。
- [ ] N/D/S/R/V 五项逐条 pass，产出 V6 验收报告并给总结论。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_159_*.py -v` 全过（复现脚本 + 验收汇总渲染 + 基线对比冒烟）；`ruff check` 通过；全量 pytest 不回归。
- [ ] 新管线取得 Ch1-Ch150 连续证据（新 run_id，非 a2bed648），完成率不劣于基线。
- [ ] 逐项对比成立：orphan 斜率 ≤138n×0.5、P1=0、无 T3/T4/T5 红线、≥1 条主线线索全程 T1 可追溯。
- [ ] **V6 验收报告逐条核对 §1.3 N/D/S/R/V 五项并给总结论**，每项有实测值/阈值/基线/证据引用，不在场者可复核。
- [ ] 不违反不可违背规则：纯验证、不改治理/阶段 C/harness；缺陷另开 Task；V6 结论如实标"通过/条件通过/不通过"。
- [ ] 生成 `tasks/159-ch1-ch150-governance-pipeline-replication-DONE.md` + `docs/reports/task-159-v6-final-acceptance-report.md`。
- [ ] 更新 `tasks/V6-README.md`（159 状态 + **阶段 D 出口 = V6 阶段验收结论**）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.3 N/D/S/R/V、§1.4 T1-T8、§3 阶段 D（Task 159 行 + 阶段 D 出口 = V6 验收）
- Task 157（harness）：`tasks/157-ch1-ch50-integration-validation.md`；Task 158（Ch100 + R + T5）：`tasks/158-ch1-ch100-long-run-validation.md`
- 阈值冻结：`tasks/148z-stage-a-threshold-calibration-DONE.md`、`docs/reports/v6-stageA-threshold-calibration.md`
- 复现基线：`run-a2bed648`（`docs/STATUS.md`）、`.tmp/task138n_ch1_ch30_rerun.db`、`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
- V5 里程碑对照：`tasks/121q-safe-best-threshold-dynamic-fix-DONE.md`
