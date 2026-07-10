# V7 Task 总索引

> **阶段**: 篇章级质量修复 → 叙事自驱 → enforce 可生产化 → Ch300 渐进爬坡
> **当前口径**: **V7 阶段 W/X/Y 已通过，T9/T10/T12 已冻结；文学提质专项 170h（路径 B 第一步）已完成并复评，未达标并维持 blocker；170i（路径 B 第二步）已完成并复评，仍未达标并维持 blocker；170j/170k/170l（路径 B 第三/四/五步）已完成并复评，均未达标并维持 blocker；Task 171 Ch200 长跑继续冻结**。170g 及 170g Phase2 均判 blocker 未达标。**170h 已完成**：CreativeDirector 1.0.7 `scene_templates`、GoalPlanner 1.1.1 动作-失败-冲突信息承载、Writer 1.2.1 非人实体戏份配额/高概念推导链/声纹降级、RuleAuditor 结构性检测、RevisionHandler 1.1.1 voice/exposition 低分直连、LLMAuditor 1.0.3 新增 voice/exposition 维度、非角色声纹卡工程化，复评 voice 1.50 / exposition 2.50 / 窗口 5 维均值 2.65。**170i 已完成**：CreativeDirector 1.0.8 认知冲突-误判-代价模板、GoalPlanner 1.1.2 冲突-误判-代价-修正链、Writer 1.2.2 人类角色声纹锚定 + 认知冲突五节拍 + 主角连续内心独白限制、RuleAuditor 新增 protagonist_summary_tell / unconflicted_revelation / human_voice_homogeneity、RevisionHandler 1.1.2 认知冲突缺失 → 人类声纹同质化 → 主角总结容器优先级 patch；复评 **voice 2.00 / exposition 2.25 / 窗口 5 维均值 2.55**，仍未达 Ch200 放行标准；T9 0/0、exposition_carrier 0、机器/LLM 偏差 0/4。**170j/170k/170l 已完成**：170j minimal_voice_anchor（voice 2.25 / 窗口均值 2.60）、170k opposing_goal_anchor（voice 2.00 / 窗口均值 3.00）、170l few_shot_voice_anchor + ai_tone_blocklist（voice 2.00 / exposition 2.00 / 窗口均值 2.40，exposition_carrier 真实值 72 处）。**170l 同时修复 RuleAuditor 引号匹配 bug**（仅匹配 ASCII `"..."` 漏报中文弯引号 `"..."`），暴露 170h–170k `exposition_carrier=0` 失真。当前进入决策点，需用户选择路径 B 升级 / AI 腔后处理 / 目标降级方向。**Task 170m 量具二次校准已完成**：exposition_carrier 动态化 + ground truth 闭环校准后，170l 原 72 处降至 6 处（高置信），维持 blocker。**2026-07-10 追加 170i 量具补丁**：修复 `detect_human_voice_homogeneity` 恒为 0 假阴性（f-string 大括号转义、前后置说话人识别、短场景合并、空情绪词交集处理），新增 2 个单测并通过 ruff/pytest；该补丁修复量具本身，不改变 170i 未达标的结论。**2026-07-10 追加 170o/170p**：170o voice 量具二次归因校准（叙事归因 + 角色注册表 gating），暴露真正 blocker 在数据层——`characters` 表长期只 seed 主角（seeding gap）；170p 修复 seeding gap（新增 `NewCharacter` 模型 + 结算工艺卡 1.0.3 证据门禁 + `_apply` 幂等 INSERT），小窗口真实生成 `run-bcf3b8f1`（Ch1–Ch5）实证 `characters` 表 1→4、配角有状态快照，seeding gap 闭合；同批修复合并遗留的 2 个 broken 测试（`_build_non_character_voice_cards` / `_build_literary_issues` 按测试契约重建）。验证暴露 voice 量具仍因说话人归因召回率过低而假阴性，建议后续 170q 增强归因。当前维持 blocker，等待用户最终决策。
> **最后整理**: 2026-07-10（170o voice 量具归因校准 + 170p seeding gap 修复完成：`run-bcf3b8f1` 实证 characters 1→4；同批修复 2 个合并遗留 broken 测试；voice 量具仍需 170q 增强归因，维持 blocker）

本文是 V7 阶段任务文档的事实入口。V6 阶段事实入口见 `tasks/V6-README.md`；V5 见 `tasks/V5-README.md`；历史规划稿统一归档到 `archive/`，仅在追溯设计边界时查阅。V7 各任务最终状态以本文件和各 `*-DONE.md` 为准。

---

## 一句话目标

> **V7 让系统"自己把质量维持在高位"——先修复 V6 暴露的篇章级质量债（文本洁净、去重、概念落地），再闭合文学质量、伏笔调度、enforce 门禁三个开放环，最终渐进验证到 Ch300。170h 路径 B 第一步已完成并复评，未达标并维持 blocker；170i 路径 B 第二步已完成并复评，仍未达标并维持 blocker；170j/170k/170l 路径 B 第三/四/五步已完成并复评，均未达标并维持 blocker；Task 171 Ch200 入口继续冻结。170l 同时修复 RuleAuditor 引号匹配 bug（中文弯引号 `"..."` 漏报），暴露 170h–170k `exposition_carrier=0` 失真。当前进入决策点，需用户选择路径 B 升级 / AI 腔后处理 / 目标降级方向。**2026-07-10 追加 170i 量具补丁**：修复 `detect_human_voice_homogeneity` 恒为 0 假阴性（f-string 转义、前后置说话人、短场景合并、空情绪词交集），新增测试并通过 ruff/pytest；该补丁修复量具本身，不改变 170i 未达标结论。

四个决策边界（2026-07-04 确认，详见 `docs/v7-plan.md` §1.2）：
1. **质量修复优先**：先修 159 暴露的篇章级缺陷，再做长程爬坡。
2. **文学修复保守**：以确定性工程修复（清洗元标记、段落去重、概念预算）+ 诊断告警 + 人工介入点为主；**不做全自动 LLM 改写闭环**。
3. **渐进爬坡 Ch200→Ch300**：每级取真实证据再进下一级。
4. **不纳入题材泛化**：专注科幻单题材把质量做到 Ch300；genre 配置化划归可选/V8。

---

## 阶段验收判定（P/L/T/G/V）

V7 通过 = 同时满足以下五项（阈值沿用 v6-plan §1.4 的 T1-T8，V7 新增 T9-T12；T9/T10 已由阶段 W 用 Ch150 修复后基线冻结、T12 已由阶段 Y 的 Task 170 小窗口验证冻结，T11 待阶段 Z 长跑继续标定，继承 148z 纪律）：

| 维度 | 判据 |
|------|------|
| **P（洁净）** | 全程 accepted 正文零元标记泄漏、零整段落重复；跨章时间线矛盾作为 report-only 诊断（T9）；`songyan report` 可查文本洁净度指标 |
| **L（文学不衰减）** | Ch1-Ch300 全程无文学维度触 T3 红线；conceptual_grounding 不随长度单调下滑（T10：末段窗口均值 ≥ 首段基线 ×0.85） |
| **T（线索经济）** | ≥1 条主线伏笔跨度 ≥50 章并**主动调度**兑现（非事后审计）；弧级伏笔兑现率达标（T11）；plan→re-plan 闭环可审计可回滚 |
| **G（门禁可生产）** | enforce 门禁自适应化——用相对趋势/异常因子触发 halt，正常波动不误伤；Ch200+ 长跑中 AutoHalt 均对应真实退化（T12 已由 Task 170 小窗口冻结：良性 FP rate=0、真实退化拦截率 100%） |
| **V（验证）** | 取得 Ch200 → Ch300 渐进真实证据（新 run_id），每级满足上述红线；事实源质量不随长度衰减 |

---

## Task 状态

> 状态口径：`◻ 规划中`（有规划稿，未开工）/ `🔄 进行中` / `✅ 完成`（有 `*-DONE.md`）/ `⚠️ 条件完成`/ `⏳ 占位`（骨架占位，详细文档待前置数据出炉后写）。

### 阶段 W：篇章级质量修复（治 159 暴露的可读性/连贯性债）—— 首批重心

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 160 | 元标记泄漏根治（正则补全 + Writer/RevisionHandler 强制清洗 + ReviewMerger 阻塞） | ✅ 完成 | `tasks/160-meta-tag-leak-eradication-DONE.md` |
| 161 | 段落级去重（整段复制根治 + 重复长段落检测） | ✅ 完成 | `tasks/161-paragraph-dedup-DONE.md` |
| 162 | 跨章时间线一致性检测（倒计时/时间戳矛盾，先诊断） | ✅ 完成 | `tasks/162-cross-chapter-timeline-consistency-DONE.md` |
| 163 | 概念预算约束（治概念通胀） | ✅ 完成 | `tasks/163-concept-budget-constraint-DONE.md` |
| 164 | 文本洁净度度量入库 + `songyan report` 展示（T9 harness） | ✅ 完成 | `tasks/164-text-cleanliness-metrics-DONE.md` |
| 165 | 阶段 W 出口：Ch150 复跑验证 + T9/T10 标定冻结 | ✅ 完成 | `tasks/165-stage-w-ch150-rerun-and-threshold-freeze-DONE.md`；报告 `docs/reports/task-165-stage-w-exit-report.md` |
| 165p | 阶段 W 出口阻断项：T5/T6 harness 口径校准 + 165 报告复算 | ✅ 完成 | `tasks/165p-stage-w-harness-calibration-DONE.md` |

### 阶段 X：叙事自驱（骨架动态闭环 + 伏笔主动调度）

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 166 | plan→generate→re-plan 闭环总览 | ✅ 完成 | `tasks/166-plan-generate-replan-loop-DONE.md` |
| 166a | 弧后评估与 ReplanProposal 生成 | ✅ 完成 | `tasks/166a-arc-outcome-evaluation-and-replan-proposal-DONE.md` |
| 166b | 人工确认后的 re-plan 应用 | ✅ 完成 | `tasks/166b-approved-replan-application-DONE.md` |
| 167 | 长程伏笔主动兑现调度（拆 167a/b） | ✅ 完成 | `tasks/167-long-range-foreshadowing-active-scheduling-DONE.md` |
| 167a | 主动伏笔调度计划生成 | ✅ 完成 | `tasks/167a-foreshadowing-schedule-plan-DONE.md` |
| 167b | 调度计划注入与生命周期推进 | ✅ 完成 | `tasks/167b-schedule-injection-and-lifecycle-DONE.md` |

### 阶段 Y：enforce 门禁可生产化

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 168 | 自适应门禁数据面（拆 168a/b） | ✅ 完成 | `tasks/168-adaptive-gate-data-plane-DONE.md` |
| 168a | 自适应门禁信号快照模型 | ✅ 完成 | `tasks/168a-adaptive-gate-signal-snapshot-DONE.md` |
| 168b | 自适应门禁窗口聚合与报告出口 | ✅ 完成 | `tasks/168b-adaptive-gate-window-reporting-DONE.md` |
| 169 | 自适应 halt 判定（拆 169a/b） | ✅ 完成 | `tasks/169-adaptive-halt-decision-DONE.md` |
| 169a | 自适应 halt 判定引擎与决策账本 | ✅ 完成 | `tasks/169a-adaptive-halt-decision-engine-DONE.md` |
| 169b | 自适应 halt workflow 接入 | ✅ 完成 | `tasks/169b-adaptive-halt-workflow-integration-DONE.md` |
| 170 | enforce 小窗口验证 + T12 误报率标定 | ✅ 完成 | `tasks/170-enforce-small-window-validation-and-t12-calibration-DONE.md`；报告 `docs/reports/task-170-adaptive-gate-validation-report.md` |

### 文学提质专项（Task 170b 判定 blocker 后新增，Ch200 放行前置）

> **立项依据**: Task 170b 中段窗口（Ch28–Ch40）真实实读判定 **blocker**——"治理指标全达标 ≠ prose 好看"实证成立（voice 塌陷、节奏偏慢、真实文本缺陷），且机器文学诊断系统性高估、T9 近似重复漏报。
> **原则**: 量具优先——先校准量具（170c/170d），再做生成侧提质（170e/170f），最后用可信量具复评（170g），复评达到 pass 标准后才重新评估 Ch200 入口。总览 `tasks/170-literary-quality-remediation-README.md`。

| Task | 名称 | 类型 | 状态 | 事实文档 |
|------|------|:---:|:----:|----------|
| 170b | 中段窗口文学性/可读性实读评估 | 评估 | ✅ 完成（判定 blocker） | `tasks/170b-midwindow-literary-readability-assessment-DONE.md`；报告 `docs/reports/task-170b-literary-readability-assessment-report.md` |
| 170c | T9 近似/改写重复检测补强 | 量具 | ✅ 完成 | `tasks/170c-t9-near-duplicate-detection-DONE.md` |
| 170d | LiteraryAuditor 校准（character_autonomy 锚点） | 量具 | ✅ 完成 | `tasks/170d-literary-auditor-calibration-DONE.md`；回测 `docs/reports/task-170d-auditor-calibration-backtest.md` |
| 170e | voice 声纹区分提质 | 提质 | ✅ 完成 | `tasks/170e-voice-differentiation-DONE.md` |
| 170f | pacing 节奏 + exposition 融合 | 提质 | ✅ 完成（部分达标） | `tasks/170f-pacing-exposition.md`（过程文档）、`tasks/170f-pacing-exposition-DONE.md`（DONE 报告）、`docs/reports/task-170f-stage2-reeval-report.md` |
| 170g | 提质复评出口 | 出口 | ✅ 完成（改判 blocker，Phase2 仍未达标，不放行 Ch200） | `tasks/170g-remediation-rerun-and-reeval-DONE.md`、`tasks/170g-phase2-remediation-DONE.md`、`docs/reports/task-170g-remediation-reeval-report.md`、`docs/reports/task-170g-phase2-remediation-reeval-report.md` |
| 170h | 路径 B 结构性改写：场景模板约束 + 非人实体戏份分配 + 声纹工程升级 | 提质 | ✅ 完成（维持 blocker） | `tasks/170h-structural-rewrite-voice-exposition.md`（规划）、`tasks/170h-structural-rewrite-voice-exposition-DONE.md`（DONE）、`docs/reports/task-170h-remediation-reeval-report.md` |
| **170i** | **路径 B 第二步：主角认知冲突/误判代价 + 人类角色声纹锚定** | **提质** | **✅ 完成（维持 blocker）** | **`tasks/170i-protagonist-cognitive-conflict-voice-anchoring.md`**、**`tasks/170i-protagonist-cognitive-conflict-voice-anchoring-DONE.md`**、**`docs/reports/task-170i-remediation-reeval-report.md`** |
| **170i-patch** | **170i 量具补丁：修复 `detect_human_voice_homogeneity` 恒为 0 假阴性** | **量具** | **✅ 完成（2026-07-10）** | 补丁记录见 `tasks/170i-protagonist-cognitive-conflict-voice-anchoring-DONE.md` §量具补丁 |
| **170j** | **路径 B 第三步：最小声纹锚定（minimal_voice_anchor）** | **提质** | **✅ 完成（维持 blocker）** | **`tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md`** |
| **170k** | **路径 B 第四步：角色对抗性目标锚定（opposing_goal_anchor）** | **提质** | **✅ 完成（维持 blocker）** | **`tasks/170k-opposing-goal-anchor-DONE.md`**、**`docs/reports/task-170k-opposing-goal-anchor-reeval-report.md`** |
| **170l** | **路径 B 第五步：声纹工程升级接口化（few_shot_voice_anchor + AI 腔禁用表）** | **提质** | **✅ 完成（维持 blocker）** | **`tasks/170l-few-shot-voice-anchor.md`**、**`tasks/170l-few-shot-voice-anchor-DONE.md`**、**`docs/reports/task-170l-few-shot-voice-anchor-reeval-report.md`** |

| **170m** | **量具二次校准：RuleAuditor exposition carrier 动态化 + ground truth 闭环** | **量具** | **完成** | **`tasks/170m-exposition-carrier-recalibration.md`**、**`tasks/170m-exposition-carrier-recalibration-DONE.md`**、**`docs/reports/task-170m-exposition-carrier-recalibration-report.md`** |

| 170n | 文学提质下一阶段方向评估（路径 B 升级 / AI 腔后处理 / 目标降级） | 评估 | 170m | — | ✅ `tasks/170n-literary-next-step-assessment.md`、`tasks/170n-literary-next-step-assessment-DONE.md`、`docs/reports/task-170n-literary-next-step-assessment-report.md` |

| 170o | voice 量具归因校准：`detect_human_voice_homogeneity` 叙事归因 + 角色注册表 gating（暴露 seeding gap） | 量具 | 170m | — | ✅ `tasks/170o-voice-homogeneity-attribution-calibration-DONE.md` |

| 170p | seeding gap 修复：SettlementExtractor 新配角证据门禁入库（NewCharacter + 工艺卡 1.0.3） | 数据层 | 170o | — | ✅ `tasks/170p-settlement-new-character-seeding-DONE.md` |

### 阶段 Z：Ch300 渐进爬坡验证

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 171 | Ch200 长跑（V7 第一里程碑） | ◻ **规划中（入口冻结）** | 170h/170i/170j/170k/170l 路径 B 连续五步均已复评未达标，维持 blocker；170l 修复 RuleAuditor 引号匹配 bug 后暴露 exposition_carrier 真实值严重超标；需用户决策下一步方向（路径 B 升级 / AI 腔后处理 / 目标降级），达标或明确降级后方可重新评估入口 |
| 171p | Ch200 撞墙定点修复（占位，内容待实跑反馈） | ⏳ 占位 | 待 Ch200 实跑后确定 |
| 172 | Ch250 过渡验证 | ⏳ 占位 | 待 171 后写 |
| 172p | Ch250 撞墙定点修复（占位） | ⏳ 占位 | 待 Ch250 实跑后确定 |
| 173 | Ch300 终态验收 + V7 阶段验收报告 | ⏳ 占位 | 待 172 后写 |
| 173p | Ch300 撞墙定点修复（占位） | ⏳ 占位 | 待 Ch300 实跑后确定 |

---

## 依赖关系与执行纪律

```
W（篇章级质量修复 160-165p）─────────────► Z（171 Ch200 → 172 Ch250 → 173 Ch300）
X（叙事自驱 166-167）──────────┐              │每级带 171p/172p/173p 撞墙定点修复占位
Y（enforce 可生产化 168-170）──┴──────────────┘
```

- **阶段 W 先行**：是后续一切的地基——篇章级缺陷不修干净，爬坡只会把毛病放大。
- **阶段 W 出口已完成并冻结 T9/T10**：Task 165/165p 已确认阶段 W 通过，T9/T10 已冻结；后续 X/Y/Z 不得在长跑撞线后临时放宽冻结口径。
- **X 与 Y 可部分并行**：不同代码域（自驱在规划侧、门禁在 gate 侧）。
- **阶段 Y 出口已完成并冻结 T12**：Task 170 已用四类小窗口验证 168/169（良性 FP rate=0、真实退化 halt_candidate/halt=100%），T12 已冻结；后续 Z 不得在长跑撞线后临时放宽冻结口径。
- **Ch200 前新增文学放行门（Task 170b blocker）未闭合**：Task 170b 实读证明"治理达标 ≠ prose 好看"，Ch200 暂缓；文学提质专项 170c–170l 已完成，**170g 及 Phase2、170h、170i、170j、170k、170l 均判 blocker，不放行 Task 171**。**170i 路径 B 第二步已完成并复评，仍未达标；170j/170k/170l 路径 B 第三/四/五步已完成并复评，均未达标；170l 同时修复 RuleAuditor 引号匹配 bug（中文弯引号 `"..."` 漏报），暴露 170h–170k `exposition_carrier=0` 失真**。当前进入决策点，需用户选择路径 B 升级 / AI 腔后处理 / 目标降级方向。**Task 170m 量具二次校准已完成**：去硬编码、动态注入项目关键词、引入 ground truth 闭环后，170l 原 exposition_carrier=72 校准为 6（高置信），但 voice/exposition 仍未达放行线，维持 blocker。**2026-07-10 追加 170i 量具补丁**：修复 `detect_human_voice_homogeneity` 恒为 0 假阴性，不改变 170i 未达标结论。
- **Z 必须在 W+X+Y + 文学放行门落地后**：171/172/173 长跑是终检，每级出口未达标不进下一级；每级预留 `NNNp` 撞墙定点修复占位。当前 **Task 171 Ch200 继续冻结；170h/170i/170j/170k/170l 已完结，进入决策点**。
- **文档递进纪律**：166/166a/166b、167、168、169、170、170b/170c/170d 已落地并有 evidence；170e/170f 已完成并有 DONE 报告；后续 170g 与阶段 Z 详细 Task 文档继续按前置 evidence 递进补齐，避免文档超前返工。

---

## 编写策略与拆分依据（2026-07-04）

- **拆分粒度**：基于 V5/V6 测试历史 review——V6 全部 19 Task 拆 a/b/c、enforce 单项用 8 Task（123-130）——确认初稿 10 Task 低估爬坡难度，扩为 **17 Task**：161 拆成去重+时间线两个独立 Task、enforce 扩为 3 Task（数据面/判定/验证）、Ch200/250/300 每级带 `NNNp` 撞墙定点修复占位。
- **文档策略**：v7-plan 为全局骨架；阶段 W（160-165p）、阶段 X 的 166/167、阶段 Y 的 168/169/170 已落地详细文档；**170h/170i/170j/170k/170l DONE 已补齐**；后续 Z 仍保持方向性占位，待前置数据出炉后写。

---

## V7 明确不做（划界）

| 项 | 归属 |
|----|------|
| 全自动文学质量 LLM 改写闭环（不止诊断、能无人驱动改写并保证不劣化） | V7 只做小范围验证，不纳入主流程（除非验证充分） |
| 题材泛化（genre 配置化 + 非科幻验证） | 可选 / V8 |
| 多项目并发 / 分布式长跑 | 不做 |

---

## 文档入口

- V7 构想（方向性）：`docs/v7-vision.md`
- V7 阶段规划与 Task 160-173 路线图：`docs/v7-plan.md`
- V6 阶段事实入口（前置）：`tasks/V6-README.md`
- V6 阶段验收报告（篇章级质量债依据）：`docs/reports/task-159-v6-final-acceptance-report.md`
- V5 阶段事实入口：`tasks/V5-README.md`
- 项目状态：`docs/STATUS.md`
- 文档路由：`docs/INDEX.md`
