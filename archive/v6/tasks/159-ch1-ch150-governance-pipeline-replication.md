# Task 159: Ch1-Ch150 治理管线复现 + V6 阶段验收

> **Phase**: V6 阶段 D（长窗口验证）
> **优先级**: P0（V6 阶段验收出口——逐条核对 §1.3 N/D/S/R/V + 冻结遗留的 T5 阈值，产出 V6 验收报告）
> **依赖**: Task 157（harness + Ch50）、Task 158（Ch100 + T5 首测）、Task 158r（kill→resume 命令级证据）均达标
> **预计工作量**: 大（Ch1-Ch150 长跑 >15h；拆 159a 复现长跑 + 逐项基线对比 + 159b V6 验收报告 N/D/S/R/V + T5 阈值复核冻结）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 D + §1.3

---

## Goal

在 V5.2 + 骨架 + 末端治理 + 长跑底盘的**真实合入管线**上复现 V5.1 的 150 章里程碑（替代旧 `run-a2bed648`），并**逐项与旧基线对比**：orphan 斜率不高于 138n、P1 critical orphan=0、文学趋势无 T3 红线、质量债无 T4 红线、≥1 条主线线索全程 T1 可追溯。**同时完成 T5 阈值复核与冻结**——T5 是阶段 A 出口标定（148z）遗留的唯一未冻结阈值，Task 158 首测扫描耗时破线，159 须基于 150 章实测数据诊断破线根因、确定并冻结 T5 正式口径。最终产出 **V6 验收报告**，逐条核对 §1.3 的 **N/D/S/R/V** 五项判定，给出 V6 阶段是否通过的结论。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- **复现目标基线**：`run-a2bed648`（V5.1 Ch1-Ch150 干净 single-run，150/150 accept、ContextEmergency=0、AutoHalt=0、degraded=0、failed=0，见 `docs/STATUS.md`）。V6 要在**新管线**（含骨架 141-144 + 度量 145-148 + 治理 149-152 + 底盘 153-156）上取得**不劣于**该基线的 150 章证据，且新增可度量的主线对象。
- **验收判据 harness（Task 157 交付、158 已在 Ch100 验证规模）**：`evaluate_v6_acceptance(project_id, 1, 150, ...)` 一次性出 T1-T8 三态。**159 不重写判据，只在 150 章规模调用 + 逐项与 138n/a2bed648 对比**。
- **五类曲线 + 主报告**：`render_stage_a_metrics(project_id, 1, 150)`（`songyan metrics --chapters 1-150`）。orphan/T7/质量债/文学/弧级兑现 + T5 遥测段全在其中。
- **§1.3 N/D/S/R/V 判定项**（v6-plan L26-31）：
  - **N（骨架）**：项目携带大纲/弧；GoalPlanner 输入含弧上下文（`context_snapshots` 可验证 `derived_from_arc`）；Ch1-Ch50 ≥1 条主线线索完成 T1 跃迁。
  - **D（度量）**：五类长期指标入库且 `songyan metrics` 可查。
  - **S（源头收敛）**：满足 T6（orphan 斜率下降 + T6c 归因）。
  - **R（可靠）**：单命令无人值守 Ch1-Ch100 + kill→resume 续完（**Task 158 已证 Ch100 无人值守；kill→resume 由 Task 158r 补齐真实命令级证据 `run-82bd2e07`**），159 引用其证据，不重复 kill 演练，除非 150 章链路有别。
  - **V（验证）**：V5.2+骨架管线上 Ch1-Ch150 连续运行证据（非旧 a2bed648），全程满足 T3/T4/T5 红线。
- **阈值冻结现状**：T3/T6a/T6b/T8 已冻结（148z）；T4 已在 157 首判 50 章满窗通过。**T5 尚未冻结**——Task 158（`run-10d7961b`）首次实测：Ch100 DB 尺寸 84.78MB 未破线，但连续性扫描耗时在 Ch50/Ch70 达 1.93×/1.76× 基线而破线（前 10 样本均值 89.1ms）。按 148z 纪律"破线不临时放宽阈值，先记录再调整后冻结"，**T5 的复核与冻结是 Task 159 的强制交付项**（详见 In Scope 159b「T5 阈值复核与冻结」）。159 是**其余全阈值 + 新冻结的 T5 同时在 150 章成立**的终检。
- **历史对照 DB**：`.tmp/task138n_ch1_ch30_rerun.db`（orphan 斜率基线）、`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`（T7 基线）；a2bed648 run log。

**为什么这是收官**：157 证 50 章 + harness、158 证 100 章 + 可靠性、158r 补齐 kill→resume 命令级证据。**T5 在 158 首测破线、尚未冻结**，因此 159 除了把窗口拉到 150 章、与历史基线正面对比、把 §1.3 五项判定写成可复核的验收报告外，还必须**完成 T5 阈值复核并冻结**——这是 V6 "阶段验收"的定义（v6-plan L148），也是阶段 A 出口标定（148z）遗留的最后一个未冻结阈值。

## Cross-Task Coordination（阶段 D 统一口径）

- **判据/曲线全部复用**：T1-T8 走 157 的 `evaluate_v6_acceptance`；五类曲线走 `render_stage_a_metrics`。159 只在 150 章规模跑一遍 + 做基线对比 + 写 N/D/S/R/V 核对，**不新增判据函数、不 fork**。
- **R 项引用而非重跑**：§1.3-R 的 kill→resume 已由 **Task 158r** 取得真实命令级证据（`run-82bd2e07`，in-flight kill@Ch3 → 同命令 `--resume` 续完 Ch1-Ch5，报告 `archive/v6/reports/task-158r-kill-resume-drill-report.md`）；159 的 R 判定**引用 158/158r 报告**。仅当 150 章链路与 100 章有实质差异（如项目大纲/弧规划显著不同、新增主线线索导致 checkpoint 模式变化）才补一次 150 章内的 resume 演练；DONE 说明是否补及判断依据。
- **T5 复核口径**：T5 是**唯一未冻结**的 V6 阈值。159 必须基于 150 章实测数据复核并冻结 T5，作为阶段 A 出口标定（148z）的补完。复核范围与冻结判定见 In Scope 159b「T5 阈值复核与冻结」；复核结论写入 v6-plan §1.4 与 148z 标定报告，V6 验收报告的 V 项引用其冻结值。
- **逐项对比口径**：与 a2bed648 对比"不劣于"= 完成率不低于、orphan 斜率不高于 138n、P1=0、无 T3/T4/T5 红线、且**额外**具备 a2bed648 没有的可追溯主线线索（T1）与五类度量（D）。V6 不是"数字更漂亮"，而是"同等稳定 + 可度量可治理"。
- **纯验证边界**：不改任何治理/门禁/harness 代码；T5 复核只**标定阈值常量/基线窗口口径**并更新标定文档，不改治理逻辑。若 150 章暴露真退化 → 新开修复 Task（如 159p），V6 验收结论标"条件通过/不通过"并列明阻断项，不在 159 里改治理。

### V6 验收报告结构（权威定义）

报告 `archive/v6/reports/task-159-v6-final-acceptance-report.md` 必须逐条给出：

| 项 | 判据（可判定） | 证据来源 | 结论 |
|----|----------------|----------|------|
| **N 骨架** | 大纲/弧携带 + GoalPlanner 弧上下文（`context_snapshots.derived_from_arc`）+ Ch1-Ch50 ≥1 主线 T1 跃迁 | NarrativeRepository / context_snapshots / `check_t1` | pass/fail |
| **D 度量** | 五类指标入库且 `songyan metrics 1-150` 可查、无断档 | `render_stage_a_metrics` 输出 | pass/fail |
| **S 收敛** | T6a 斜率 ≤138n×0.5 + T6b P1=0 + T6c 归因成立 | `evaluate_v6_acceptance` T6* | pass/fail |
| **R 可靠** | 单命令无人值守 Ch100（Task 158）+ kill→resume 命令级证据（Task 158r `run-82bd2e07`） | Task 158 / 158r 报告 | pass/fail |
| **V 验证** | 新管线 Ch1-Ch150 连续证据 + 全程 T3/T4 不破 + **T5 按 159 复核后的冻结阈值不破** | 本 Task 长跑 + `evaluate_v6_acceptance` | pass/fail |

- 每项附**实测值 + 阈值 + 与基线对比**，并引用具体 run_id / 报告路径 / harness 三态输出，使不在场者能独立复核真假。
- 报告须**单列「T5 阈值复核与冻结」专节**（见 In Scope 159b），给出：150 章 DB 尺寸/扫描耗时全样本、旧口径（前 10 样本均值 ×1.5）复算结果、破线归因、新基线窗口/系数的冻结决定与理由。V 项的 T5 结论必须引用该专节的冻结阈值，而非 158 的临时口径。
- 末尾给**总结论**：五项全 pass（且 T5 已冻结）→ V6 通过；任一 fail → 条件通过/不通过 + 阻断项 + 后续 Task。

## In Scope（必须完成）

### 159a — Ch1-Ch150 复现长跑 + 逐项基线对比
- [ ] 隔离副本 DB（带大纲项目）单命令无人值守跑 Ch1-Ch150，enforce 门禁；metrics 逐章追加 `.tmp/task159_ch1_ch150_metrics.jsonl`。on_failure/预算选型与 158 一致或说明差异。
- [ ] 取得新 run_id（**非** a2bed648）的 150 章证据；记录完成率、AutoHalt、degraded、failed。
- [ ] 逐项与基线对比：orphan 斜率 vs 138n、P1 critical orphan（=0）、T7 速率 vs 138k、文学趋势（无 T3）、质量债（无 T4）。
- [ ] **采集 T5 全样本**：150 章每 10 章一个 `run_db_metrics` 样本（DB 尺寸 / WAL 尺寸 / `scan_latency_ms`），完整落盘供 159b 复核使用（158 只有 ~10 个样本，是破线口径失真的直接原因之一）。
- [ ] 若中途触红线/AutoHalt：记录确切章 + 根因，判"真退化→新开修复 Task、V6 条件不通过"或"波动→记录"，不改治理。

### 159b — V6 验收报告 N/D/S/R/V + T5 冻结
- [ ] `evaluate_v6_acceptance(1,150)` 出全 T1-T8 三态；`songyan metrics 1-150` 出五类曲线。
- [ ] **T5 阈值复核与冻结**（阶段 A 出口标定的补完，必须完成）：
  - [ ] **尺寸红线**：确认 150 章 DB 尺寸远低于 300MB（158 Ch100=84.78MB），复核 300MB 是否仍是合理红线；给出 150 章实测峰值。
  - [ ] **扫描耗时红线复核**：用 150 章全样本复算现口径 `check_t5_latency_redline`（前 10 样本均值 ×1.5）。**诊断 158 破线根因**——现口径的"前 10 样本"基线窗口在 100 章仅 ~10 样本时几乎覆盖全程、与被比较样本重叠，叠加 `find_orphaned` 单点计时的文件系统抖动，导致 Ch50/Ch70 假破线。
  - [ ] **给出冻结决定**：在"扩大/滑动基线窗口""改用中位数或分位数抗抖动""调整 1.5× 系数""对单点耗时做多次采样取稳健值"等口径中选定一种或组合，并说明理由；冻结为 V6 正式 T5 口径。**遵守 148z 纪律：基于实测数据调整后冻结，不为凑过而临时放宽**。
  - [ ] 若复核后 150 章在新口径下仍破线且判为真退化 → V6 的 V 项标"条件不通过"+ 新开修复/优化 Task，不强行冻结。
  - [ ] 冻结结论写入 `archive/v6/reports/v6-stageA-threshold-calibration.md`（补 T5 段）与 `docs/v6-plan.md` §1.4（更新 T5 行 + L54 附注），并在 159 验收报告单列「T5 阈值复核与冻结」专节。
  - [ ] 若冻结需改动 `check_t5_latency_redline` 的默认参数/基线口径：这属于**度量标定**而非治理逻辑，允许在 159 内改动该纯函数 + 补/改对应单测（`tests/test_158_t5_freeze.py` 等），但不得触碰生成/门禁/harness 判据。
- [ ] 按 **Cross-Task Coordination「V6 验收报告结构」** 逐条核对 N/D/S/R/V，每项给实测值/阈值/基线对比/证据引用/pass-fail；V 项 T5 引用冻结后的阈值。
- [ ] 产出 `archive/v6/reports/task-159-v6-final-acceptance-report.md`（V6 阶段验收报告），含逐章/检查点（Ch1/Ch50/Ch100/Ch150）表 + 五类曲线 + harness 三态 + **T5 阈值复核与冻结专节** + N/D/S/R/V 核对表 + 与 a2bed648 逐项对比 + 总结论。
- [ ] 更新 V6 事实文档：`tasks/V6-README.md`（159 状态 + 阶段 D 出口 + V6 验收结论 + **T5 已冻结**）、`docs/STATUS.md`、`docs/INDEX.md`（如需）。

## Out of Scope（明确不做）

- 不改任何**治理/门禁/生成/阶段 C 代码或 157 harness 判据**（纯验证；缺陷另开 Task）。**例外**：T5 阈值复核若需调整 `check_t5_latency_redline` 的基线窗口/系数等**纯度量标定参数**，允许改动该纯函数 + 对应单测（见 159b），这不属于治理逻辑。
- 不重复 158/158r 已完成的 kill→resume 演练（除非 150 章链路与 100 章相比存在显著不同的弧规划/大纲结构或 checkpoint 模式差异）。
- 除 **T5**（唯一遗留未冻结阈值，159 强制冻结）外，不冻结/不改动其它阈值（T3/T4/T6a/T6b/T8 已在 148z/157 冻结）。
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
- [ ] `evaluate_v6_acceptance(1,150)`：T2 完成、T6（S）、T3/T4（V）不破、T1（N）可追溯；**T5 按 159 复核冻结后的口径不破**。
- [ ] **T5 阈值复核与冻结完成**：150 章全样本复算 + 158 破线根因诊断 + 新口径冻结决定，写入标定报告与 v6-plan §1.4。
- [ ] 逐项与 a2bed648/138n/138k 对比"不劣于"成立。
- [ ] N/D/S/R/V 五项逐条 pass，产出 V6 验收报告并给总结论。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_159_*.py -v` 全过（复现脚本 + 验收汇总渲染 + 基线对比冒烟）；若改动 T5 纯函数则 `tests/test_158_t5_freeze.py` 同步更新且全过；`ruff check` 通过；全量 pytest 不回归。
- [ ] 新管线取得 Ch1-Ch150 连续证据（新 run_id，非 a2bed648），完成率不劣于基线。
- [ ] 逐项对比成立：orphan 斜率 ≤138n×0.5、P1=0、无 T3/T4 红线、≥1 条主线线索全程 T1 可追溯。
- [ ] **T5 已冻结**：给出 150 章 DB 尺寸峰值 + 扫描耗时全样本 + 158 破线根因 + 新口径冻结决定，结论写入 `archive/v6/reports/v6-stageA-threshold-calibration.md` 与 `docs/v6-plan.md` §1.4；150 章在冻结口径下不破线（或如破线则如实标 V 条件不通过 + 后续 Task）。
- [ ] **V6 验收报告逐条核对 §1.3 N/D/S/R/V 五项并给总结论**，每项有实测值/阈值/基线/证据引用，不在场者可复核；含独立「T5 阈值复核与冻结」专节。
- [ ] 不违反不可违背规则：除 T5 纯度量标定外纯验证、不改治理/阶段 C/harness 判据；缺陷另开 Task；V6 结论如实标"通过/条件通过/不通过"。
- [ ] 生成 `archive/v6/tasks/159-ch1-ch150-governance-pipeline-replication-DONE.md` + `archive/v6/reports/task-159-v6-final-acceptance-report.md`。
- [ ] 更新 `tasks/V6-README.md`（159 状态 + **阶段 D 出口 = V6 阶段验收结论 + T5 已冻结**）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.3 N/D/S/R/V、§1.4 T1-T8（T5 行 L43 + 附注 L54）、§3 阶段 D（Task 159 行 + 阶段 D 出口 = V6 验收）
- Task 157（harness）：`archive/v6/tasks/157-ch1-ch50-integration-validation-DONE.md`；Task 158（Ch100 + T5 首测）：`archive/v6/tasks/158-ch1-ch100-long-run-validation-DONE.md`
- kill→resume 命令级证据（R 项引用）：`archive/v6/reports/task-158r-kill-resume-drill-report.md`、`scripts/run_158r_kill_resume_drill.py`
- T5 阈值复核依据：`archive/v6/reports/v6-stageA-threshold-calibration.md`（待补 T5 段）、`archive/v6/reports/task-158-ch1-ch100-long-run-validation-report.md`（158 T5 首测数据）、`src/songyan/evals/db_maintenance_metrics.py`（`check_t5_size_redline` / `check_t5_latency_redline` 现口径）、`tests/test_158_t5_freeze.py`（T5 判定单测）
- 阈值冻结：`archive/v6/tasks/148z-stage-a-threshold-calibration-DONE.md`、`archive/v6/reports/v6-stageA-threshold-calibration.md`
- 复现基线：`run-a2bed648`（`docs/STATUS.md`）、`.tmp/task138n_ch1_ch30_rerun.db`、`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
- V5 里程碑对照：`archive/v5/tasks/121q-safe-best-threshold-dynamic-fix-DONE.md`
