# Task 165: 阶段 W 出口 — Ch1-Ch150 复跑验证 + T9/T10 标定冻结

> **Phase**: V7 阶段 W（篇章级质量修复）出口
> **优先级**: P0（阶段 W 出口 = 修复效果验收 + T9/T10 冻结；X/Y/Z 的前置闸门）
> **依赖**: Task 160（元标记）、161（去重）、162（时间线）、163（概念预算）、164（洁净度度量 + T9 harness）全部合入
> **预计工作量**: 大（Ch1-Ch150 复跑 >15h；拆 165a 复跑 + 修复效果对比 / 165b T9/T10 标定冻结 + 阶段 W 出口报告）
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 W + §2 P/L 判据

---

## Goal

在合入 160-164 修复后的管线上**复跑 Ch1-Ch150**，验证 `run-bba292da` 暴露的篇章级质量债被治理——**52 章元标记泄漏清零、19 章整段重复清零、时间线矛盾收敛、conceptual_grounding 止跌**；并用该 run 作为 **Ch150 修复后基线**，**标定并冻结 T9（文本洁净度红线）/ T10（文学不衰减）** 为 V7 正式口径（继承 148z"先实测再冻结、不撞线放宽"纪律）。这是阶段 W 出口，也是 X/Y/Z 一切工作的地基基线。

## Context

设计核实（2026-07-04，创建前对主干代码核对）：

- **复跑基线对照**：`run-bba292da`（V6 Ch1-Ch150，150/150 accept，但 52 章元标记 / 19 章重复 / conceptual_grounding 7.12→6.02）。阶段 W 要在**修复后管线**上取得**同等稳定 + 显著更洁净**的 150 章证据——完成率不劣于、且三类篇章级缺陷清零/收敛。
- **判据 harness 复用 164**：T9 走 Task 164 的 `check_t9`；T10 走 Task 147 的文学趋势查询（`detect_literary_trend` + conceptual_grounding 末段/首段窗口比）。**165 不重写判据，只在 150 章规模调用 + 与 `run-bba292da` 逐项对比 + 冻结阈值**。
- **T9/T10 是 V7 阶段 W 出口唯一待冻结阈值**：v7-plan §4 明确 T9-T12 待标定冻结。其中 **T9/T10 在阶段 W 出口冻结**（本 Task），T11/T12 留 X/Y 阶段。冻结须基于本次 150 章修复后实测分布：
  - **T9**：元标记=0 / 整段重复=0 是结构性红线；**时间线矛盾**因 162 是诊断项、可能有误报，本 Task 须用实测决定"矛盾纳入硬零"还是"仅报告不计红线"，并冻结 `check_t9` 的 `include_timeline_in_redline` 口径。
  - **T10**：conceptual_grounding（及各文学维度）末段 W=5 窗口均值 ≥ 首段基线 ×0.85。**0.85 系数须用修复后实测校准**——若修复后仍达不到 0.85，按纪律记录并调整（不为凑过放宽，也不凭空定过严），冻结为 V7 正式口径。
- **纯验证 + 度量标定边界**：本 Task **不改治理/生成/门禁代码**；T9/T10 冻结只标定判据阈值常量/口径并更新标定文档。若 150 章暴露真退化（如某类元标记仍泄漏、重复未清零）→ 判为"修复不彻底"，回 160-162 补修（新开 `16Xp` 修复 Task），阶段 W 出口标"条件不通过"+ 阻断项，不在 165 里改治理逻辑。

**为什么这是阶段 W 出口**：160-162 修检测与清洗、163 治概念、164 建度量与判据——165 是**在真实 150 章长跑上验证四者协同生效 + 冻结验收口径**。X/Y/Z 都以"篇章级洁净的 Ch150 基线"为前提，故 165 未达标不进 X/Y/Z（继承 V6 阶段出口纪律）。

### 2026-07-05 执行结果与 165p 交接

- 真实复跑 `run-11fc7c96` 已完成：Ch1-Ch150 150/150 accepted，`failed=[]`，无 AutoHalt。
- P 洁净通过：元标记 52→0、重复长段落 19→0；时间线诊断 3 章（[21, 37, 142]）按候选口径 report-only。
- L 文学通过：conceptual_grounding 首段 W=5 6.80，末段 W=5 6.06，阈值 5.78（×0.85）。
- 初次报告中阶段 W 出口条件不通过：`不回退` 项中 T5 扫描耗时旧口径 fail、T6c 小基数归因口径 fail。
- 该阻断项已由 `tasks/165p-stage-w-harness-calibration-DONE.md` 解决。复算后阶段 W 通过，T9/T10 已冻结，最终结论见 `tasks/165-stage-w-ch150-rerun-and-threshold-freeze-DONE.md`。

## Cross-Task Coordination（阶段 W 统一口径）

- **判据/曲线复用**：T9 走 164 `check_t9`；T10 走 147 文学趋势；洁净度曲线走 164 `render_text_cleanliness_section`。165 只在 150 章规模跑 + 对比 + 冻结，**不新增判据函数、不 fork**。
- **逐项对比口径**：与 `run-bba292da` 对比"更洁净且不劣"= 完成率不低于、元标记/重复清零、时间线矛盾收敛、conceptual_grounding 末段不再单调跌破 T10、其余 V6 红线（T3/T4/T5/T6）不回退。
- **T9/T10 冻结写入**：冻结结论写入 `docs/v7-plan.md` §4（更新 T9/T10 行）+ 新建/追加 V7 标定报告（对齐 `docs/reports/v6-stageA-threshold-calibration.md` 风格）；阶段 W 出口报告的 P/L 项引用冻结值。
- **纯验证边界**：不改治理/门禁/生成/检测代码；仅标定 T9/T10 阈值常量 + 对应单测。真退化 → 新开 `16Xp` 修复 Task，阶段 W 结论标"条件通过/不通过"。

### 阶段 W 出口报告结构（权威定义）

报告 `docs/reports/task-165-stage-w-exit-report.md` 必须逐条给出：

| 项 | 判据（可判定） | 证据来源 | 结论 |
|----|----------------|----------|------|
| **P 洁净** | 150 章 accepted 正文元标记=0 + 整段重复=0 + 时间线矛盾（按冻结口径） | 164 `check_t9` / 洁净度曲线 | pass/fail |
| **L 文学** | conceptual_grounding 末段 W=5 均值 ≥ 首段基线 ×T10系数；全程无 T3 红线 | 147 趋势 / `detect_literary_trend` | pass/fail |
| **修复对比** | vs `run-bba292da`：52→0 元标记、19→0 重复、grounding 止跌 | 逐项对比表 | pass/fail |
| **不回退** | T3/T4/T5/T6 等 V6 红线不因修复回退 | `evaluate_v6_acceptance` | pass/fail |

- 每项附**实测值 + 阈值 + 与 `run-bba292da` 对比**，引用具体新 run_id / harness 三态，使不在场者可独立复核。
- 报告须**单列「T9/T10 阈值标定与冻结」专节**：给出 150 章修复后洁净度全样本、conceptual_grounding 首/末段窗口均值、T9 矛盾口径决定、T10 系数冻结决定与理由。
- 末尾给**总结论**：P/L 达标 + T9/T10 已冻结 → 阶段 W 通过、可进 X/Y；任一 fail → 条件通过/不通过 + 阻断项 + 后续 `16Xp` 修复 Task。

## In Scope（必须完成）

### 165a — Ch1-Ch150 复跑 + 修复效果对比
- [ ] 隔离副本 DB（带大纲项目）单命令无人值守跑 Ch1-Ch150，enforce + isolate（与 158/159 同口径）；洁净度 + 五类度量逐章入库。可复用 `scripts/run_159_ch1_ch150.py` 骨架改造为 165 复跑脚本。
- [ ] 取得新 run_id（非 `run-bba292da`）的 150 章证据；记录完成率、AutoHalt、degraded、failed。
- [ ] **修复效果逐项对比**：元标记泄漏章数（目标 52→0）、整段重复章数（目标 19→0）、时间线矛盾数（收敛）、conceptual_grounding 首/末段窗口均值（止跌）。
- [ ] **采集 T9/T10 全样本**：150 章逐章洁净度三类计数 + 各文学维度逐章分，完整落盘供 165b 冻结使用。
- [ ] 若某类缺陷未清零/未收敛：记录确切章 + 形态，判"修复不彻底→回 160-162 补修（新开 16Xp）、阶段 W 条件不通过"，不改治理。

### 165b — T9/T10 标定冻结 + 阶段 W 出口报告
- [ ] `check_t9(1,150)` 出三态；147 文学趋势出 conceptual_grounding 首/末段窗口均值 + 全维度趋势。
- [ ] **T9 冻结**：用 150 章实测决定"时间线矛盾"是否纳入硬零（`include_timeline_in_redline`），冻结 T9 正式口径（元标记=0 / 重复=0 为硬红线）。
- [ ] **T10 冻结**：用修复后 conceptual_grounding 首/末段实测校准 ×0.85 系数——达标则冻结 0.85；不达标则按纪律记录 + 调整为实测可达且有意义的正向约束（不为凑过放宽），冻结为 V7 正式口径。
- [ ] 冻结结论写入 `docs/v7-plan.md` §4（T9/T10 行）+ V7 标定报告；阶段 W 出口报告 P/L 项引用冻结值。
- [ ] 若冻结需改 `check_t9`/T10 判据的默认参数/口径：属**度量标定**非治理，允许改该纯函数 + 对应单测（`tests/test_164_*.py` 等），不得触碰生成/门禁/检测逻辑。
- [ ] 按 **Cross-Task Coordination「阶段 W 出口报告结构」** 逐条核对 P/L/修复对比/不回退，每项给实测值/阈值/基线对比/证据引用/pass-fail。
- [ ] 产出 `docs/reports/task-165-stage-w-exit-report.md`（含逐章/检查点表 + 洁净度曲线 + 文学趋势 + T9/T10 冻结专节 + 修复对比表 + 总结论）。
- [ ] 更新 V7 事实文档：`tasks/V7-README.md`（165 状态 + 阶段 W 出口结论 + **T9/T10 已冻结**）、`docs/STATUS.md`、`docs/INDEX.md`（如需）。

## Out of Scope（明确不做）

- 不改任何**治理/门禁/生成/检测代码**（纯验证；修复不彻底另开 `16Xp`）。**例外**：T9/T10 冻结若需调整 `check_t9`/T10 判据的阈值常量/口径，允许改该纯度量函数 + 对应单测。
- 除 **T9/T10**（阶段 W 出口冻结）外，不冻结 T11/T12（留 X/Y 阶段）。
- 不做 X/Y/Z 的任何工作（自驱/门禁/爬坡）——165 是它们的前置闸门。
- 不承诺 Ch200+（那是阶段 Z）。
- 不新增 LLM 判据。

## 测试要求

> **测试哲学**：165 的判据可信度由 164 的 `check_t9` 单测 + 147 趋势单测背书（150 章只是更大样本，不改判据）。165 **不新增判据单测**；Layer 2 仅对复跑脚本 + 阶段 W 出口报告汇总渲染做冒烟。真正的验收是 Layer 3 的 150 章实跑 + 报告核对。

### Layer 2: 复跑脚本 + 出口报告汇总渲染冒烟
- [ ] 复跑脚本章范围/度量入库/report 路径解析：3-5 章 Mock 跑通（不跑真 LLM）。
- [ ] **P/L/修复对比/不回退汇总渲染**：喂合成洁净度 + 文学趋势 + `run-bba292da` 对比数据，验证四项表格能生成 pass/fail 行、总结论正确（全 pass + T9/T10 冻结→通过；含 fail→条件不通过 + 列阻断项 + 后续 16Xp）。
- [ ] T9/T10 冻结逻辑：合成"元标记残留/重复残留""grounding 达标/不达标"样本，验证冻结决定分支正确。

### Layer 3: Ch1-Ch150 复跑（阶段 W 出口）
- [ ] 修复后管线单命令跑完 Ch1-Ch150（150/150 或明确 AutoHalt 根因），取得新 run_id。
- [ ] 修复效果：元标记 52→0、重复 19→0、时间线矛盾收敛、conceptual_grounding 止跌（末段 ≥ 首段 ×T10系数）。
- [ ] `check_t9(1,150)` pass；T10 pass；V6 红线（T3/T4/T5/T6）不回退。
- [ ] **T9/T10 冻结完成**：150 章全样本标定 + 冻结决定写入 v7-plan §4 + V7 标定报告。
- [ ] P/L/修复对比/不回退逐条 pass，产出阶段 W 出口报告并给总结论。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_165_*.py -v` 全过（复跑脚本 + 出口报告汇总 + 冻结逻辑冒烟）；若改 T9/T10 纯函数则对应单测同步全过；`ruff check` 通过；全量 pytest 不回归。
- [ ] 修复后管线取得 Ch1-Ch150 连续证据（新 run_id，非 `run-bba292da`），完成率不劣于基线。
- [ ] 修复效果达标：元标记 52→0、整段重复 19→0、时间线矛盾收敛、conceptual_grounding 末段 ≥ 首段 ×T10系数（或如实标 L 条件不通过 + 16Xp）。
- [ ] **T9/T10 已冻结**：150 章洁净度全样本 + conceptual_grounding 首/末段实测 + 冻结决定，写入 `docs/v7-plan.md` §4 与 V7 标定报告；150 章在冻结口径下不破线（或如实标条件不通过 + 后续 Task）。
- [ ] **阶段 W 出口报告逐条核对 P/L/修复对比/不回退并给总结论**，每项有实测值/阈值/基线/证据引用，不在场者可复核；含独立「T9/T10 阈值标定与冻结」专节。
- [ ] 不违反不可违背规则：除 T9/T10 纯度量标定外纯验证、不改治理/门禁/生成/检测；缺陷另开 16Xp；阶段 W 结论如实标"通过/条件通过/不通过"。
- [ ] 生成 `tasks/165-stage-w-ch150-rerun-and-threshold-freeze-DONE.md` + `docs/reports/task-165-stage-w-exit-report.md`。
- [ ] 更新 `tasks/V7-README.md`（165 状态 + **阶段 W 出口结论 + T9/T10 已冻结**）与 `docs/STATUS.md`。

## 参考文档

- `docs/v7-plan.md` §2 P/L 判据、§3 阶段 W（Task 165 行 + 阶段 W 出口）、§4 T9/T10
- 复跑脚本骨架：`scripts/run_159_ch1_ch150.py`（隔离 DB + 逐章度量 + 报告拼装）
- T9 harness：Task 164 `tasks/164-text-cleanliness-metrics-DONE.md`、`check_t9` / `render_text_cleanliness_section`
- T10 / 文学趋势：Task 147 `tasks/147-literary-quality-trend-DONE.md`、`src/songyan/evals/db_metrics.py`（`detect_literary_trend` / `collect_literary_scores`）
- 修复上游：Task 160/161/162/163 DONE 文档
- 复跑基线对照：`run-bba292da`（`docs/reports/task-159-v6-final-acceptance-report.md`）
- 冻结纪律先例：`tasks/148z-stage-a-threshold-calibration-DONE.md`、`docs/reports/v6-stageA-threshold-calibration.md`
