# 文学提质专项（Task 170c–170i）总览

> **立项依据**: Task 170b 判定 **blocker** —— 中段窗口 prose 文学质量不达标（voice 塌陷、节奏偏慢、真实文本缺陷），且机器文学诊断系统性失真。
> **性质**: Ch200 长跑（Task 171）的文学放行前置修复专项。
> **状态**: 🔴 **170h/170i/170j/170k/170l 路径 B 连续五步已完成并复评，均未达标，维持 blocker；Task 171 Ch200 长跑继续冻结。170l 同时修复 RuleAuditor 引号匹配 bug（中文弯引号 `"..."` 漏报），暴露 170h–170k `exposition_carrier=0` 失真。Task 170m 量具二次校准已完成：动态化关键词 + ground truth 闭环校准后，170l 原 exposition_carrier=72 降至 6（高置信），但 voice/exposition/窗口均值仍未达 Ch200 放行线，维持 blocker。Task 170n 方向评估已完成：推荐方向 C（目标降级）+ 同步准备方向 B（AI 腔后处理）作为长跑定点工具，最终方向待用户决策。**
> 量具阶段完成（170c ✅ / 170d ✅），提质阶段 170e（voice）✅ / 170f（pacing/exposition）✅ 完成，170g 出口验证完成（结论 blocker），170g Phase2 验证完成（结论仍 blocker），170h 路径 B 第一步验证完成（结论仍 blocker），170i 路径 B 第二步验证完成（结论仍 blocker），170j/170k/170l 路径 B 第三/四/五步验证完成（结论仍 blocker）。
> **最后整理**: 2026-07-10（170l 复评完成，结果未达 Ch200 放行线，进入决策点）

---

## 一句话目标

> **先校准"量具"（T9 去重 + LiteraryAuditor），再做生成侧提质（voice + pacing/exposition），最后用校准后的量具复评中段窗口——把 170b 的 blocker 转成 pass/observation，才放行 Ch200。 **Task 170m 已完成对 RuleAuditor exposition carrier 的二次校准：去硬编码、动态注入项目关键词、引入 ground truth 闭环，170l 原计数 72 校准为 6（高置信），但文学维度仍未达放行线。****

当前 170g 复评未达 pass 标准（voice 1.75、exposition 2.0、窗口均值 2.45，均低于 170g 自定 pass 线），因此专项状态更新为 **blocker**，Ch200 不放行。**170g Phase2 追加 5 项工艺补丁并复评后，仍未达标（voice 1.75、exposition 2.25、窗口均值 2.55）**，维持 blocker。**170h 路径 B 第一步结构性改写已完成并复评，仍未达标（voice 1.50、exposition 2.50、窗口均值 2.65）**，维持 blocker。**170i 路径 B 第二步已完成并复评，仍未达标（voice 2.00、exposition 2.25、窗口均值 2.55）**，维持 blocker。**170j/170k/170l 路径 B 第三/四/五步已完成并复评，均未达标**：170j（voice 2.25 / 窗口均值 2.60）、170k（voice 2.00 / 窗口均值 3.00）、170l（voice 2.00 / exposition 2.00 / 窗口均值 2.40，exposition_carrier 真实值 72 处）。**170l 同时修复 RuleAuditor 引号匹配 bug**（仅匹配 ASCII `"..."` 漏报中文弯引号 `"..."`，导致 170h–170k `exposition_carrier=0` 失真）。路径 B 轻量策略连续五步收益递减/劣化，当前进入决策点：需用户选择路径 B 升级 / AI 腔后处理 / 目标降级方向。

## 核心原则：量具优先

170b 暴露了一个关键陷阱：**机器诊断本身是失真的**——LiteraryAuditor 的 `character_autonomy` 给 6.5–8.5，人工/LLM voice 仅 1–2；T9 去重漏报了 Ch31 的明显重复。

如果先做提质、后校准量具，复评将不可信：
- 量具高估 → 真提质了也可能被假高分掩盖（**假通过**，带病进 Ch200）。
- 量具漏报 → 真提质了量具却抓不到改善（**假失败**，白做）。

因此本专项**先修量具（170c/170d），再做提质（170e/170f），最后用可信量具复评（170g）**。这样证据链闭合。

当前量具已可信（T9 0/0、机器/LLM 偏差 0/4），但提质未达 pass 线，所以**不是量具问题，而是生成侧深层卡点未解决**。170l 修复 RuleAuditor 引号匹配 bug 后，进一步证明此前 `exposition_carrier=0` 是量具漏报，真实 exposition 硬灌远高于预期。

## 170b 暴露的问题 → 专项方向映射

| 170b 发现 | 严重度 | 专项 Task | 类型 |
|-----------|:---:|:---:|------|
| T9 去重漏报近似/改写重复（Ch31 重复但 count=0） | 🔴 | **170c** | 量具 |
| LiteraryAuditor `character_autonomy` 高估、对对白同质不敏感 | 🔴 | **170d** | 量具 |
| voice 系统性塌陷（均值 1.8，对白全员同质冷静腔） | 🔴 | **170e** | 提质 |
| pacing 偏慢（单人解谜/日志堆叠）+ exposition 硬灌 | 🔴 | **170f** | 提质 |
| 提质是否有效、能否放行 Ch200 | — | **170g** | 出口 |

## Task 结构

| Task | 名称 | 类型 | 依赖 | 风险 | 文档 |
|------|------|:---:|:---:|:---:|------|
| 170c | T9 近似/改写重复检测 | 量具 | 170b | 低·独立 | ✅ `tasks/170c-t9-near-duplicate-detection-DONE.md` |
| 170d | LiteraryAuditor 校准 | 量具 | 170b | 低·独立 | ✅ `tasks/170d-literary-auditor-calibration-DONE.md` |
| 170e | voice 声纹区分提质 | 提质 | 170d | 中·碰生成链 | ✅ `tasks/170e-voice-differentiation-DONE.md` |
| 170f | pacing 节奏 + exposition 融合 | 提质 | 170d | 中·碰生成链 | ✅ `tasks/170f-pacing-exposition.md`（过程）、`tasks/170f-pacing-exposition-DONE.md`（DONE 报告）、`docs/reports/task-170f-stage2-reeval-report.md` |
| 170g | 提质复评出口 | 出口 | c+d+e+f | — | ✅ `tasks/170g-remediation-rerun-and-reeval-DONE.md`（改判 blocker）、`docs/reports/task-170g-remediation-reeval-report.md` |
| 170g Phase2 | 工艺补丁与小样本复评 | 出口补丁 | 170g | — | ✅ `tasks/170g-phase2-remediation-DONE.md`（结论仍 blocker）、`docs/reports/task-170g-phase2-remediation-reeval-report.md` |
| 170h | 路径 B 结构性改写：场景模板约束 + 非人实体戏份分配 + 声纹工程升级 | 提质 | 170g Phase2 | — | ✅ `tasks/170h-structural-rewrite-voice-exposition-DONE.md`、`docs/reports/task-170h-remediation-reeval-report.md` |
| 170i | 路径 B 第二步：主角认知冲突/误判代价 + 人类角色声纹锚定 | 提质 | 170h | — | ✅ `tasks/170i-protagonist-cognitive-conflict-voice-anchoring.md`、`tasks/170i-protagonist-cognitive-conflict-voice-anchoring-DONE.md`（结论仍 blocker）、`docs/reports/task-170i-remediation-reeval-report.md` |
| 170j | 路径 B 第三步：最小声纹锚定（minimal_voice_anchor） | 提质 | 170i | — | ✅ `tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md` |
| 170k | 路径 B 第四步：角色对抗性目标锚定（opposing_goal_anchor） | 提质 | 170j | — | ✅ `tasks/170k-opposing-goal-anchor.md`、`tasks/170k-opposing-goal-anchor-DONE.md`（结论仍 blocker）、`docs/reports/task-170k-opposing-goal-anchor-reeval-report.md` |
| 170l | 路径 B 第五步：声纹工程升级接口化（few_shot_voice_anchor + AI 腔禁用表） | 提质 | 170k | — | ✅ `tasks/170l-few-shot-voice-anchor.md`、`tasks/170l-few-shot-voice-anchor-DONE.md`（结论仍 blocker；同时修复 RuleAuditor 引号匹配 bug）、`docs/reports/task-170l-few-shot-voice-anchor-reeval-report.md` |
| 170m | 量具二次校准：RuleAuditor exposition carrier 动态化 + ground truth 闭环 | 量具 | 170l | 低·独立 | ✅ `tasks/170m-exposition-carrier-recalibration.md`、`tasks/170m-exposition-carrier-recalibration-DONE.md`、`docs/reports/task-170m-exposition-carrier-recalibration-report.md` |

## 依赖与执行顺序

```
170c（T9 去重）─────────┐
170d（Auditor 校准）──┬──┴──► 170e（voice）──┐
                     └─────► 170f（pacing/expo）─┴──► 170g（复评出口）──► 170g Phase2 ──► 170h ──► 170i ──► 170j ──► 170k ──► 170l
                                                                                          │
                                                                                          ▼
                                                                                  Task 171 Ch200（达标或明确降级后放行）
```

- **170c / 170d 先行且可并行**：都是量具修复，低风险、独立代码域（去重在 rule_auditor，校准在 literary_auditor 工艺卡）。
- **170e / 170f 依赖 170d**：需要校准后的可信量具才能判断提质是否有效；两者可部分并行（voice 在对白域，pacing/expo 在节奏与检测域）。
- **170g 依赖全部**：重跑中段窗口 + 用修复后量具复评，是本专项的终检。
- **170g 当前结论：blocker**，因此 **Task 171 Ch200 不放行**，需继续 170g Phase 2 工艺补丁并复评。
- **170g Phase2 已完成**：5 项工艺补丁落地，Ch29–Ch32 重跑并复评，结论 **仍未达标，维持 blocker**。
- **170h 已完成**：路径 B 第一步结构性改写落地，Ch29–Ch32 重跑并复评，结论 **仍未达标，维持 blocker**，进入 170i。
- **170i 已完成**：路径 B 第二步主角认知冲突/误判代价 + 人类角色声纹锚定落地，Ch29–Ch32 重跑并复评，结论 **仍未达标，维持 blocker**，进入 170j。
- **170j/170k/170l 已完成**：路径 B 第三/四/五步轻量策略迭代落地，Ch29–Ch32 重跑并复评，结论 **均未达标，维持 blocker**；170l 同时修复 RuleAuditor 引号匹配 bug，暴露 170h–170k `exposition_carrier=0` 失真。
- **170m 已完成**：对 RuleAuditor exposition carrier 进行二次校准（去硬编码、动态关键词、ground truth 闭环），170l 原计数 72 校准为 6（高置信），但 voice/exposition 仍未达放行线。

## 阶段发现的认知修正（写文档前查证得到，避免规划误区）

1. **T9 去重不是"只抓全等整段"**：`detect_duplicate_paragraphs` 已用 `difflib.SequenceMatcher`（阈值 0.9），但**只在单章内比、按单换行切段 + `min_chars=100` 过滤**。Ch31 漏报的根因需先复现（阈值过高？min_chars 滤掉？切分问题？）——170c 是**诊断 + 调参/扩展**，非从零加。
2. **声纹机制已存在且完整**：CreativeDirector 1.0.6 有"角色语言指纹"强制规则、Writer 1.2.0 有 `dialogue_style_cards` 注入 + `DialogueStyleCard` 结构化通路。voice 仍塌陷说明**现有机制失效或未触发**——170e 重点是**诊断为何失效**，非从零加声纹。
3. **RuleAuditor 无"连续独白/说明段落"代码检测**：认知动词黑名单只在 Writer 卡文字层，无对应检测——170f 的检测缺口真实存在。
4. **Writer manifest default=1.1.0 但最新卡是 1.2.0**：改 Writer 卡前必须先查线上实际加载版本，避免改错版本。
5. **170g 改判 blocker 的认知**：工程约束（`exposition_carrier`）使显性硬灌减少，但模型换壳为“建造者声音/残影独白/前代钥匙灌输/主角总结”，说明约束层级只到“形式”未到“信息生长方式”。必须补 CreativeDirector 正路径模板、RuleAuditor 深层检测、RevisionHandler 文学 patch 路径，才可能让 voice/exposition 真正提升。

## 专项边界（继承 V7 决策边界 2）

- **不做全自动 LLM 改写闭环**：提质以确定性工程修复 + 工艺卡约束 + 诊断告警 + 人工介入点为主。
- **170h 已维持 blocker，不放行 Ch200**：必须先完成 170i 并复评通过。
- 不放宽 T9/T10/T5/T6/T12 已冻结口径（170c 是补强 T9 检测能力，非放宽红线）。
- 不新增 LangGraph 节点、不新增 Agent。
- 量具与提质分离：量具修复（c/d）不改生成行为；提质（e/f）不改量具判定标准。

## 出口判定

本专项完成 = 170g 复评满足：
- voice / pacing / exposition 较 170b 基线**可测量地提升**（用校准后量具）；
- 机器/人工诊断偏差**收敛**（170d 校准生效）；
- T9 对近似重复**不再漏报**（170c 生效）；
- 综合达到 **pass 或 observation**（非 blocker）。

### 重新明确的 170g pass 标准

1. LLM rubric 中段窗口（Ch28–Ch40 任意连续 4 章）：
   - voice ≥ 3.0
   - exposition ≥ 3.0
   - pacing ≥ 3.0
   - 窗口 5 维均值 ≥ 3.0
2. 代码检测：
   - `exposition_carrier_count` ≤ 1（含新增深层模式）
   - T9 硬红线 0/0
3. 量具可信度：
   - 机器 literary_quality 与 LLM rubric 均值（×2）偏差 < 3 分
4. 无新退化：
   - continuity_health 不较 170f 同窗口恶化
   - 不引入新的 meta_tag / duplicate_para

未达标 → 保持 blocker，继续 Phase 2 工艺补丁；达标 → 方可把 170g 改为 observation/pass 并重新评估 Ch200 入口。

### 实际出口结论

**170l 当前结论：路径 B 第五步已完成并复评，仍未达标，维持 blocker，进入决策点。**

- 工程侧约束部分有效：`exposition_carrier` 约束 + RuleAuditor 代码检测使明显硬灌模式从 170f 的多处降至 1 处，170g Phase2 / 170h / 170i / 170j / 170k 窗口内保持 0 处（但 170l 修复引号匹配 bug 后发现此 0 为漏报）。
- T9 保持 0/0，量具可信：机器 literary_quality 与 LLM rubric 归一后无大偏差（0 / 3）。
- 170l 实测窗口（Ch30–Ch32）：voice 2.00、exposition 2.00、pacing 3.00、concept 3.00、ai_tone 2.00，窗口均值 2.40，未达 pass 线。
- exposition_carrier 真实值严重超标：Ch30=27、Ch31=24、Ch32=21，窗口合计 72 处；主要类型为 `info_delivery_dialogue`（34 处）、`direct_revelation_monologue`（11 处）、`repeated_revelation_beat`（7 处）、`expository_dialogue_chain`（7 处）、`unearned_revelation`（9 处）。
- 深层根因：`few_shot_voice_anchor` 让模型把“声纹示例”理解为“让角色更详细地解释设定”，`ai_tone_blocklist` 未能抵消模板化，叠加 `opposing_goal_anchor` 后形成“冷静对峙 + 完整说明”的同质化对白模板；高概念信息仍通过角色大段独白/说明直接投递，未真正经动作、失败、代价、认知冲突转化。
- **170l 同时修复 RuleAuditor 引号匹配 bug**：`_DIRECT_REVELATION_QUOTE_RE`、`_NON_CHARACTER_QUOTE_RE`、`_INFO_DELIVERY_DIALOGUE_RE`、`_FAQ_DIALOGUE_PATTERN`、`_REVELATION_BEAT_PATTERNS` 此前仅匹配 ASCII `"..."`，漏报中文弯引号 `"..."`；修复后暴露 170h–170k `exposition_carrier=0` 失真。该修复已同步到主仓库与 worktree，并新增弯引号覆盖单测。

**170l 路径 B 第五步未改判 observation，维持 blocker**。路径 B 轻量策略连续五步（170h→170i→170j→170k→170l）均未让 voice/exposition 同时达标，170l 反而造成 exposition 劣化与 carrier 暴增，**必须停止继续追加同层级细碎约束**。下一步需用户从以下方向决策：
1. **路径 B 升级**：更激进结构性改写（人类角色戏份/台词硬配额、非人实体单句信息上限、对白-动作交替硬节拍、认知冲突前置模板等），工程量较大，可能超出 V7 MVP 边界；
2. **AI 腔后处理**：在 RevisionHandler 中针对 `info_delivery_dialogue` / `direct_revelation_monologue` 做硬性拆分/改写，把说明性对白压缩或转化为动作/代价/冲突；
3. **目标降级**：诚实判定当前 deepseek-chat 在当前 prompt 工程深度下难以在 V7 内让 voice/exposition 同时 ≥3.0，将文学质量目标调整为“保持 pacing/concept/T9 不劣化”，先放行 Ch200 并在长跑中持续人工抽读修复。

必须在 Ch28–Ch40 等效窗口复评达到 pass 标准（voice ≥3.0、exposition ≥3.0、窗口均值 ≥3.0、exposition_carrier_count ≤1、T9 0/0、偏差 <3 分）或明确降级后，方可重新评估 Ch200 入口。

## 文档入口

- 立项依据：`tasks/170b-midwindow-literary-readability-assessment-DONE.md`、`docs/reports/task-170b-literary-readability-assessment-report.md`
- 170g 出口 DONE（改判 blocker）：`tasks/170g-remediation-rerun-and-reeval-DONE.md`
- 170g Phase2 DONE（仍 blocker）：`tasks/170g-phase2-remediation-DONE.md`
- 170g 复评报告：`docs/reports/task-170g-remediation-reeval-report.md`
- 170g Phase2 复评报告：`docs/reports/task-170g-phase2-remediation-reeval-report.md`
- 170h DONE（路径 B 第一步，仍 blocker）：`tasks/170h-structural-rewrite-voice-exposition-DONE.md`
- 170h 复评报告：`docs/reports/task-170h-remediation-reeval-report.md`
- 170i DONE（路径 B 第二步，仍 blocker）：`tasks/170i-protagonist-cognitive-conflict-voice-anchoring-DONE.md`
- 170i 复评报告：`docs/reports/task-170i-remediation-reeval-report.md`
- 170j DONE（路径 B 第三步，仍 blocker）：`tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md`
- 170k DONE（路径 B 第四步，仍 blocker）：`tasks/170k-opposing-goal-anchor-DONE.md`
- 170k 复评报告：`docs/reports/task-170k-opposing-goal-anchor-reeval-report.md`
- 170l DONE（路径 B 第五步，仍 blocker；修复 RuleAuditor 引号匹配 bug）：`tasks/170l-few-shot-voice-anchor-DONE.md`
- 170l 复评报告：`docs/reports/task-170l-few-shot-voice-anchor-reeval-report.md`
- V7 事实入口：`tasks/V7-README.md`
- 项目状态：`docs/STATUS.md`
- 改判与 Phase 2 计划：`docs/superpowers/plans/ghost-rider-nick-fury-adam-warlock.md`
