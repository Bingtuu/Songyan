# V7 Task 总索引

> **阶段**: 篇章级质量修复 → 叙事自驱 → enforce 可生产化 → Ch300 渐进爬坡
> **当前口径**: **V7 阶段 W/X/Y 已通过，T9/T10/T12 已冻结；文学提质专项（Task 170）已结束——改判为"改契约 + 并行"框架（2026-07-10 用户拍板，见 `docs/reports/v7-literary-framework-review.md`）**。旧框架把文学质量（voice/exposition ≥3.0）设为 Ch200 硬前置门，经框架级复盘认定其有 5 个结构性错误（判决分辨率 > 量具精度、量具构念建错、用未证能力阻塞已证能力等），路径 B 五步 prompt 工程（170h–170l）在错误框架内必然递减/劣化，**已封存**。新框架把文学质量拆为三层契约：Tier 1 硬缺陷（T9，仍阻塞）+ Tier 2 趋势地板（observe 不阻塞）+ Tier 3 上限（并行 R&D）。**Task 171 Ch200 长跑已取得 `run-fb39245c` 200/200 accepted + D1 hard clean pass 证据**；171v Ch201-Ch220 小窗口已实跑但未通过出口（run `run-e27b763f` partial，19/20 accepted，failed=[207]），当前转 171v-hardening 后再重验，暂不进入 172。文学 R&D 171a/171a-1/171b/171c/171d 已完成并归档至 `archive/v7/`。阶段验收标准见 `docs/reports/v7-literary-framework-review.md` §8。170 系列 DONE 文档保留为历史事实，不再作为 Ch200 闸门。
> **最后整理**: 2026-07-12（Ch200 完成 200/200 accepted；171t/171u 完成 D1 hard clean pass；171v 小窗口 partial，需 hardening；171a–171d R&D 产物归档至 `archive/v7/`）

本文是 V7 阶段任务文档的事实入口。V6 阶段事实入口见 `tasks/V6-README.md`；V5 见 `tasks/V5-README.md`；历史规划稿统一归档到 `archive/`，仅在追溯设计边界时查阅。V7 各任务最终状态以本文件和各 `*-DONE.md` 为准。

---

## 一句话目标

> **V7 让系统"自己把质量维持在高位"——先修复 V6 暴露的篇章级质量债（文本洁净、去重、概念落地），再闭合文学质量、伏笔调度、enforce 门禁三个开放环，最终渐进验证到 Ch300。文学质量环（Task 170）经框架级复盘，从"voice/exposition ≥3.0 的 Ch200 硬前置门"改判为"三层契约 + 并行 R&D"（详见 `docs/reports/v7-literary-framework-review.md`）：Tier 1 硬缺陷仍阻塞、Tier 2 趋势地板转 observe 不阻塞、Tier 3 上限归并行 R&D。Task 171 Ch200 长跑已取得 200/200 accepted + D1 hard clean pass 证据；171v 小窗口已证明护栏进入 prompt，但尚未稳定改变正文输出，需 hardening 后重验。本阶段目标不再是"把 voice 拧到 3.0"，而是"建立可信、可证伪、体裁解耦、不阻塞规模化的文学质量框架，并取得 Ch200+ 真实证据"（阶段验收标准见框架文档 §8）。**

四个决策边界（2026-07-04 确认，详见 `docs/v7-plan.md` §1.2）：
1. **质量修复优先**：先修 159 暴露的篇章级缺陷，再做长程爬坡。
2. **文学修复保守**：以确定性工程修复（清洗元标记、段落去重、概念预算）+ 诊断告警 + 人工介入点为主；**不做全自动 LLM 改写闭环**。
3. **渐进爬坡 Ch200→Ch300**：每级取真实证据再进下一级。
4. **不纳入题材泛化（产品化）**：专注科幻单题材把质量做到 Ch300；genre 配置化 + 非科幻**产品化验证**划归可选/V8。**例外（2026-07-10）**：Task 171a/171b 为消除量具体裁窄化、验证量具效度，会用 ≥2 个体裁做**量具层的交叉验证与代表性采样**——这属于"证明量具体裁解耦"，不等于把非科幻纳入产品化爬坡目标，两者不冲突。

---

## 阶段验收判定（P/L/T/G/V）

V7 通过 = 同时满足以下五项（阈值沿用 v6-plan §1.4 的 T1-T8，V7 新增 T9-T12；T9/T10 已由阶段 W 用 Ch150 修复后基线冻结、T12 已由阶段 Y 的 Task 170 小窗口验证冻结，T11 待阶段 Z 长跑继续标定，继承 148z 纪律）：

| 维度 | 判据 |
|------|------|
| **P（洁净）** | 全程 accepted 正文零元标记泄漏、零整段落重复；跨章时间线矛盾作为 report-only 诊断（T9）；`songyan report` 可查文本洁净度指标 |
| **L（文学不衰减）** | 按三层契约（框架文档 §6.1）判定：**Tier 1** 文本洁净硬红线（并入 P/T9）；**Tier 2** pacing/concept/voice/exposition 作趋势地板（滚动窗口均值 ≥ 首段基线 ×0.85，复用 T10 模型，observe 不阻塞、跌破触发人工抽读）；**Tier 3** voice/exposition 绝对高分为并行 R&D 目标、非放行条件。**不再要求"文学维度触固定阈值即阻塞"**。 |
| **T（线索经济）** | ≥1 条主线伏笔跨度 ≥50 章并**主动调度**兑现（非事后审计）；弧级伏笔兑现率达标（T11）；plan→re-plan 闭环可审计可回滚 |
| **G（门禁可生产）** | enforce 门禁自适应化——用相对趋势/异常因子触发 halt，正常波动不误伤；Ch200+ 长跑中 AutoHalt 均对应真实退化（T12 已由 Task 170 小窗口冻结：良性 FP rate=0、真实退化拦截率 100%） |
| **V（验证）** | 取得 Ch200 → Ch300 渐进真实证据（新 run_id），每级满足 P/T/G 硬红线与 L 的 Tier 2 趋势地板；事实源质量不随长度衰减 |

> **文学维度口径变更（2026-07-10）**：L 维度原表述"全程无文学维度触 T3 红线"已按框架级复盘改判为三层契约——文学质量不再作 Ch200/Ch300 的硬阻塞门，改为 Tier 1 硬缺陷阻塞 + Tier 2 趋势观测 + Tier 3 并行 R&D。本阶段（含文学环）的完整 PASS 判据以 `docs/reports/v7-literary-framework-review.md` §8（A/B/C/D/E 五组）为准。

---

## Task 状态

> 状态口径：`◻ 规划中`（有规划稿，未开工）/ `🔄 进行中` / `✅ 完成`（有 `*-DONE.md`）/ `⚠️ 条件完成` / `⚠️ 条件未通过` / `⏳ 占位`（骨架占位，详细文档待前置数据出炉后写）。

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

### 文学提质专项（Task 170）—— 已结束，改判为"改契约 + 并行"框架

> **结束说明（2026-07-10）**: Task 170 系列（170b–170p）已全部完成并留档为历史事实，但其"voice/exposition ≥3.0 作为 Ch200 硬前置门"的**框架被推翻**。框架级复盘（`docs/reports/v7-literary-framework-review.md`）认定旧框架有 5 个结构性错误，路径 B 五步 prompt 工程（170h–170l）在错误框架内必然递减/劣化，**已封存**。文学质量改为三层契约 + 并行 R&D，收进 Task 171 体系（171a/171b/171c）。**下表 170b–170p 保留为历史记录，不再作为 Ch200 闸门；未完成的量具校准/提质工作转 171a/171c。**
> **原立项依据（保留）**: Task 170b 中段窗口（Ch28–Ch40）真实实读判定 blocker——"治理指标全达标 ≠ prose 好看"实证成立（voice 塌陷、节奏偏慢、真实文本缺陷），且机器文学诊断系统性高估、T9 近似重复漏报。这一实读观察仍成立；被推翻的是"用它作 Ch200 硬前置门 + 单窗口单体裁 prompt 迭代"的解决框架，而非观察本身。总览 `tasks/170-literary-quality-remediation-README.md`。

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
| **170m** | **量具二次校准：RuleAuditor exposition carrier 动态化 + ground truth 闭环** | **量具** | **✅ 完成** | **`tasks/170m-exposition-carrier-recalibration.md`**、**`tasks/170m-exposition-carrier-recalibration-DONE.md`**、**`docs/reports/task-170m-exposition-carrier-recalibration-report.md`** |
| 170n | 文学提质下一阶段方向评估（路径 B 升级 / AI 腔后处理 / 目标降级） | 评估 | ✅ 完成 | `tasks/170n-literary-next-step-assessment.md`、`tasks/170n-literary-next-step-assessment-DONE.md`、`docs/reports/task-170n-literary-next-step-assessment-report.md` |
| 170o | voice 量具归因校准：`detect_human_voice_homogeneity` 叙事归因 + 角色注册表 gating（暴露 seeding gap） | 量具 | ✅ 完成 | `tasks/170o-voice-homogeneity-attribution-calibration-DONE.md` |
| 170p | seeding gap 修复：SettlementExtractor 新配角证据门禁入库（NewCharacter + 工艺卡 1.0.3） | 数据层 | ✅ 完成 | `tasks/170p-settlement-new-character-seeding-DONE.md` |

### 阶段 Z：Ch300 渐进爬坡验证（含文学 R&D 并行线）

> **主线**（Ch200→250→300 长跑）与 **R&D 线**（171a→171b→171c 文学量具/样本/杠杆）并行。R&D 线是"文学结论"的前提，但**不阻塞主线**：Ch200 以已验证稳定性面放行、文学=观测。Ch200 完成后的当前收口链路为 **171t 量具补强 → 171u 清洁应用/报告复算 → 171v 文学护栏 → 171v-hardening + Ch201-Ch220 重验 → 172 Ch250**。阶段验收标准见 `docs/reports/v7-literary-framework-review.md` §8。

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 171 | Ch200 长跑（V7 第一里程碑，文学=观测已解冻） | ✅ **完成（Ch200 200/200 accepted；D1 hard clean pass）** | run `run-fb39245c` Ch1-Ch200 **200/200 accepted、gaps=[]、Halt=None**；171t/171u 已完成，当前 accepted head T9 meta/artifact=0、duplicate=0，T6b critical orphan peak=0；报告 `docs/reports/task-171-ch200-long-run-report.md`；分析 `docs/reports/task-171-ch200-analysis-and-next-step-report.md` |
| 171p | Ch200 撞墙定点修复（state_mismatch 构念修正） | ✅ **完成** | `tasks/171p-ch200-wall-fix-DONE.md`；排除演进型 field（emotional_state/knowledge），Ch3 假阳性 11→6，V6 159 基线 post-fix 全程 0、health 9.3–10（不误抑制） |
| 171q | Ch200 撞墙定点修复（分段修订 T9 重复——去重阈值口径对齐） | ✅ **完成** | `tasks/171q-ch200-wall-fix-duplicate.md`；min_chars 100→40 + 分级阈值 0.95/0.9，实证复验 accepted Ch2 T9 dup 8→0 |
| 171s | Ch200 撞墙定点修复（critical setting 同义提及刷新） | ✅ **完成** | `tasks/171s-critical-setting-reference-refresh.md`；增强 `_detect_setting_references` 复合中文设定召回，Ch160/161/162/164/165 实证刷新 `protagonist.genetic_identity.reaper_maker_consistency` |
| 171t | Ch200 D1 文本洁净量具补强 | ✅ **完成** | `tasks/171t-ch200-d1-hard-clean.md`；已扩展 T9 hard issue 检测：Markdown 标题、保护指令、斜杠拼接、纯省略号段、prompt/patch 指令、duplicate final sweep；目标 pytest 104/127 passed，`ruff check src/ tests/` 通过 |
| 171u | Ch200 D1 清洁应用与报告事实源复算 | ✅ **完成** | `tasks/171u-ch200-d1-clean-application-and-report-refresh.md`；20 个 clean accepted versions，T9 hard issue=0，T6b critical orphan peak=0，报告只取最新事实源 |
| 171v | Ch200+ 文学性与可读性护栏 | ⚠️ **条件未通过（小窗口 partial，需 hardening）** | `tasks/171v-ch200-plus-literary-readability-guardrails.md`；run `run-e27b763f` Ch201-Ch220 **19/20 accepted、failed=[207]、Halt=None**；T9=0，但角色主动性均值约 2.816、配角目标 4/4 次注入未落正文、概念密度仍偏高 |
| 171w | 171v-hardening：文学护栏硬化与 Ch201-Ch220 重验 | ◻ **规划中** | 待创建 spec；基于 171v 小窗口结论，重点修复 CreativeBrief/Revision metadata、配角目标必达约束、主动选择/概念预算 observe、Ch207 settlement 数值校验 |
| 171a | 文学量具效度重建（R0：构念重定义 + 体裁解耦通电 + voice 归因召回修复） | ✅ **完成 / 已归档** | `archive/v7/tasks/171a-literary-metric-validity-rebuild-DONE.md`、`archive/v7/reports/task-171a-metric-validity-report.md`；B2/B3 已由 171a-1 达标 |
| 171a-1 | 量具效度量化（≥2 体裁盲标 GT + voice/exposition P/R/F1，框架 §8 B2/B3） | ✅ **完成 / 已归档** | `archive/v7/tasks/171a-1-metric-validity-quantification-DONE.md`、`archive/v7/reports/task-171a-1-metric-prf-report.md`；scifi/wuxia voice F1=1.0、exposition F1=0.889/1.0 |
| 171b | 代表性样本集（R1：场景分层采样 + ≥2 体裁交叉 + 2×2 归因） | ✅ **完成 / 已归档** | `archive/v7/tasks/171b-representative-sampling-DONE.md`、`archive/v7/reports/task-171b-representative-sampling-report.md`；两体裁 9 章全 voice 适用，稀疏参照层正确剔除，170 低分归『量具无效』格 |
| 171c | 杠杆组合验证（R2：后处理/few-shot/解码参数/换模型/人工抽读，带退出判据） | ✅ **完成 / 已归档** | `archive/v7/tasks/171c-improvement-levers-DONE.md`、`archive/v7/reports/task-171c-improvement-levers-report.md`；确定性后处理证伪退出（Goodhart），温度死配置通电，换模型通道就绪待 live 资源 |
| 171d | 三层契约落地（框架 §8 A 组：A1 报告分层 + A3 Tier2 趋势地板/抽读 observe + A4 标定） | ✅ **完成 / 已归档** | `archive/v7/tasks/171d-three-tier-contract-DONE.md`、`archive/v7/reports/task-171d-three-tier-contract-report.md`；`detect_literary_spot_read` observe-only，465 章标定确认 rubric 1–10、地板 max(base×0.85, 3.0) |
| 172 | Ch250 过渡验证 | ⏳ 占位 | `tasks/172-ch250-transition-validation.md`；待 171w hardening + Ch201-Ch220 重验通过后启动 |
| 172p | Ch250 撞墙定点修复（占位） | ⏳ 占位 | 待 Ch250 实跑后确定 |
| 173 | Ch300 终态验收 + V7 阶段验收报告 | ⏳ 占位 | 待 172 后写 |
| 173p | Ch300 撞墙定点修复（占位） | ⏳ 占位 | 待 Ch300 实跑后确定 |

---

## 依赖关系与执行纪律

```
W（篇章级质量修复 160-165p）─────────────► Z（171 Ch200 → 171t/171u/171v → hardening/重验 → 172 Ch250 → 173 Ch300）
X（叙事自驱 166-167）──────────┐              │每级带撞墙定点修复与收口 task
Y（enforce 可生产化 168-170）──┴──────────────┘
```

- **阶段 W 先行**：是后续一切的地基——篇章级缺陷不修干净，爬坡只会把毛病放大。
- **阶段 W 出口已完成并冻结 T9/T10**：Task 165/165p 已确认阶段 W 通过，T9/T10 已冻结；后续 X/Y/Z 不得在长跑撞线后临时放宽冻结口径。
- **X 与 Y 可部分并行**：不同代码域（自驱在规划侧、门禁在 gate 侧）。
- **阶段 Y 出口已完成并冻结 T12**：Task 170 已用四类小窗口验证 168/169（良性 FP rate=0、真实退化 halt_candidate/halt=100%），T12 已冻结；后续 Z 不得在长跑撞线后临时放宽冻结口径。
- **文学放行门已改判为三层契约（Task 170 结束）**：Task 170b 实读观察"治理达标 ≠ prose 好看"仍成立，但"用它作 Ch200 硬前置门 + 单窗口单体裁 prompt 迭代"的框架经复盘被推翻（`docs/reports/v7-literary-framework-review.md`）。文学质量改为三层契约：**Tier 1 硬缺陷（T9）仍阻塞；Tier 2 趋势地板转 observe 不阻塞；Tier 3 上限归并行 R&D**。**Ch200 不再被文学 rubric 阻塞**，放行判据回到已验证稳定性面。文学量具/样本/杠杆的未完成工作转 171a/171b/171c 并行推进；路径 B（170h–170l）prompt 工程已封存。
- **Z 主线与 R&D 线并行**：171/172/173 长跑是终检，每级出口以**稳定性面**（T9/health/orphan/T12）判定、未达标不进下一级，每级预留撞墙定点修复或收口 task。**Task 171 Ch200 已完成且 D1 hard clean pass**；171v 小窗口已实跑但未通过出口，需 hardening + 重验后再进入 172。
- **文档递进纪律**：166/166a/166b、167、168、169、170、170b–170p 已落地并有 evidence；文学专项 Task 170 已结束并改判（框架文档 `docs/reports/v7-literary-framework-review.md`）。阶段 Z 的 171 主线、171t/171u/171v 收口与 172 占位 spec 保留在当前入口；171a/171a-1/171b/171c/171d R&D 产物已归档至 `archive/v7/`；173 与各后续撞墙修复继续保持方向性占位，待前置实跑数据出炉后补齐，避免文档超前返工。

---

## 编写策略与拆分依据（2026-07-04）

- **拆分粒度**：基于 V5/V6 测试历史 review——V6 全部 19 Task 拆 a/b/c、enforce 单项用 8 Task（123-130）——确认初稿 10 Task 低估爬坡难度，扩为 **17 Task**：161 拆成去重+时间线两个独立 Task、enforce 扩为 3 Task（数据面/判定/验证）、Ch200/250/300 每级带 `NNNp` 撞墙定点修复占位。
- **2026-07-12 拆分修正**：Ch200 20% 抽读证明 D1 hard clean 问题不只是 duplicate/stale report，而是 T9 artifact false negative；因此把原 171t/171u 拆为 **171t 量具补强、171u 清洁应用/报告复算、171v 文学护栏、172 Ch250 验证**。
- **文档策略**：v7-plan 为全局骨架；阶段 W（160-165p）、阶段 X 的 166/167、阶段 Y 的 168/169/170 已落地详细文档；**文学专项 170b–170p DONE 已补齐并结束**（改判见框架文档）；阶段 Z 的 171 主线、171t/171u/171v 收口 task 与 172 占位 spec 保持在当前入口；171a/b/c/d R&D 证据见 `archive/v7/INDEX.md`；173 与后续撞墙修复待前置数据出炉后写。

---

## V7 明确不做（划界）

| 项 | 归属 |
|----|------|
| 全自动文学质量 LLM 改写闭环（不止诊断、能无人驱动改写并保证不劣化） | V7 只做小范围验证，不纳入主流程（除非验证充分） |
| 题材泛化——**产品化**（genre 配置化 + 非科幻爬坡验证） | 可选 / V8。注：171a/171b 用 ≥2 体裁做**量具效度交叉验证**是例外，属"证明量具体裁解耦"，非产品化泛化。 |
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
- V7 归档：`archive/v7/INDEX.md`
