# 文学提质专项（Task 170c–170g）总览

> **立项依据**: Task 170b 判定 **blocker** —— 中段窗口 prose 文学质量不达标（voice 塌陷、节奏偏慢、真实文本缺陷），且机器文学诊断系统性失真。
> **性质**: Ch200 长跑（Task 171）的文学放行前置修复专项。
> **状态**: ◻ 规划中（本总览 + 170c/d/e/f/g 五个任务文档已就绪，待执行）
> **最后整理**: 2026-07-06

---

## 一句话目标

> **先校准"量具"（T9 去重 + LiteraryAuditor），再做生成侧提质（voice + pacing/exposition），最后用校准后的量具复评中段窗口——把 170b 的 blocker 转成 pass/observation，才放行 Ch200。**

## 核心原则：量具优先

170b 暴露了一个关键陷阱：**机器诊断本身是失真的**——LiteraryAuditor 的 `character_autonomy` 给 6.5–8.5，人工/LLM voice 仅 1–2；T9 去重漏报了 Ch31 的明显重复。

如果先做提质、后校准量具，复评将不可信：
- 量具高估 → 真提质了也可能被假高分掩盖（**假通过**，带病进 Ch200）。
- 量具漏报 → 真提质了量具却抓不到改善（**假失败**，白做）。

因此本专项**先修量具（170c/170d），再做提质（170e/170f），最后用可信量具复评（170g）**。这样证据链闭合。

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
| 170c | T9 近似/改写重复检测 | 量具 | 170b | 低·独立 | `tasks/170c-t9-near-duplicate-detection.md` |
| 170d | LiteraryAuditor 校准 | 量具 | 170b | 低·独立 | `tasks/170d-literary-auditor-calibration.md` |
| 170e | voice 声纹区分提质 | 提质 | 170d | 中·碰生成链 | `tasks/170e-voice-differentiation.md` |
| 170f | pacing 节奏 + exposition 融合 | 提质 | 170d | 中·碰生成链 | `tasks/170f-pacing-exposition.md` |
| 170g | 提质复评出口 | 出口 | c+d+e+f | — | `tasks/170g-remediation-rerun-and-reeval.md` |

## 依赖与执行顺序

```
170c（T9 去重）─────────┐
170d（Auditor 校准）──┬──┴──► 170e（voice）──┐
                     └─────► 170f（pacing/expo）─┴──► 170g（复评出口）──► Task 171 Ch200
```

- **170c / 170d 先行且可并行**：都是量具修复，低风险、独立代码域（去重在 rule_auditor，校准在 literary_auditor 工艺卡）。
- **170e / 170f 依赖 170d**：需要校准后的可信量具才能判断提质是否有效；两者可部分并行（voice 在对白域，pacing/expo 在节奏与检测域）。
- **170g 依赖全部**：重跑中段窗口 + 用修复后量具复评，是本专项的终检。

## 阶段发现的认知修正（写文档前查证得到，避免规划误区）

1. **T9 去重不是"只抓全等整段"**：`detect_duplicate_paragraphs` 已用 `difflib.SequenceMatcher`（阈值 0.9），但**只在单章内比、按单换行切段 + `min_chars=100` 过滤**。Ch31 漏报的根因需先复现（阈值过高？min_chars 滤掉？切分问题？）——170c 是**诊断 + 调参/扩展**，非从零加。
2. **声纹机制已存在且完整**：CreativeDirector 1.0.6 有"角色语言指纹"强制规则、Writer 1.2.0 有 `dialogue_style_cards` 注入 + `DialogueStyleCard` 结构化通路。voice 仍塌陷说明**现有机制失效或未触发**——170e 重点是**诊断为何失效**，非从零加声纹。
3. **RuleAuditor 无"连续独白/说明段落"代码检测**：认知动词黑名单只在 Writer 卡文字层，无对应检测——170f 的检测缺口真实存在。
4. **Writer manifest default=1.1.0 但最新卡是 1.2.0**：改 Writer 卡前必须先查线上实际加载版本，避免改错版本。

## 专项边界（继承 V7 决策边界 2）

- **不做全自动 LLM 改写闭环**：提质以确定性工程修复 + 工艺卡约束 + 诊断告警为主。
- 不启动 Ch200（170g 只重跑中段窗口）。
- 不放宽 T9/T10/T5/T6/T12 已冻结口径（170c 是补强 T9 检测能力，非放宽红线）。
- 不新增 LangGraph 节点、不新增 Agent。
- 量具与提质分离：量具修复（c/d）不改生成行为；提质（e/f）不改量具判定标准。

## 出口判定

本专项完成 = 170g 复评满足：
- voice / pacing / exposition 较 170b 基线**可测量地提升**（用校准后量具）；
- 机器/人工诊断偏差**收敛**（170d 校准生效）；
- T9 对近似重复**不再漏报**（170c 生效）；
- 综合达到 **pass 或 observation**（非 blocker）。

达标 → 放行规划 **Task 171 Ch200**；未达标 → 记录残余债、按需再迭代或缩小 Ch200 目标。

## 文档入口

- 立项依据：`tasks/170b-midwindow-literary-readability-assessment-DONE.md`、`docs/reports/task-170b-literary-readability-assessment-report.md`
- V7 事实入口：`tasks/V7-README.md`
- 项目状态：`docs/STATUS.md`
