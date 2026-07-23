# Task 170b DONE: 中段窗口真实生成 + 文学性/可读性实读评估

> **完成时间**: 2026-07-06
> **阶段**: V7 阶段 Y→Z 之间的前置验证（Ch200 文学 gate）
> **结论**: **blocker —— 不直接进入 Ch200**。中段 prose 文学质量不达标（voice 系统性塌陷、节奏偏慢、存在真实文本缺陷），且机器文学诊断系统性失真。先做生成侧提质，再回 170b 复评。

---

## 做了什么

1. 用真实 DeepSeek API 生成中段窗口 **Ch1–Ch40，40/40 全部 accepted，无 AutoHalt**（隔离 DB `.tmp/task170b_ch1_ch40.db`，enforce + isolate，复用 157b 科幻大纲种子）。
2. 抽读窗口 **Ch28–Ch40（13 章）**：导出正文、取 LiteraryAuditor 4 维机器分、复算 T9 洁净度、拉 run_log；LLM 按 5 维 rubric 初评。
3. 助手**亲读核验** Ch28/Ch31/Ch33，交叉验证 LLM 初评。
4. 用户**通读全 13 章**，确认判断并追加"节奏偏慢"观察。
5. 助手基于三重依据代评终分，给出 blocker 判定与提质方向。

交付物：
- 生成脚本 `scripts/run_170b_midwindow_generation.py`
- 抽读评估脚本 `scripts/run_170b_readability_assessment.py`
- 评估报告 `archive/v7/reports/task-170b-literary-readability-assessment-report.md`
- 正文导出 `.tmp/task170b_prose_ch28_ch40.md`（177KB，供人工实读）

## 三个问题的答案

**Q1: 当前 prose 的文学水位在哪？**
5 维终评窗口均值 **2.32/5**。voice 1.8（塌陷）、exposition 2.1、pacing 2.4（用户确认慢）、ai_tone 2.2、concept 3.2（相对强项）。**概念落地是相对优势，voice 和节奏是最痛短板。**

**Q2: 机器诊断可不可信？**
**不可信——系统性失真。** 机器 `character_autonomy` 给 6.5–8.5 高分，但人工/LLM voice 维度仅 1–2 分；5/13 章偏差达 ⚠️ 阈值。机器高估了角色维度。**这是比 prose 差更底层的缺陷。**

**Q3: 够不够格进 Ch200？**
**不够，blocker。** 三条独立理由同时成立：voice 单维塌陷、机器诊断失真、Ch31 真实文本缺陷（段落重复 + 悬空残句）。

## 关键发现

1. **"X/X accept" 与文学质量脱钩得到实证**：本窗口 T9 硬红线全 0、continuity health 9.1–9.7、QG 全 True、无 degraded——**治理面完全健康，文学质量却不达标**。印证了 Task 170b 立项前提。
2. **机器 character_autonomy 系统性高估**：对"对白全员同质冷静腔"不敏感，需校准。
3. **T9 去重存在漏报洞**：Ch31 有明显段落重复（L633/641、L643/659）+ 悬空残句（L645），但 `duplicate_paragraph_count=0`——T9 只抓全等整段，漏近似/改写重复。**这是确定要修的检测器缺陷，与文学判定独立。**
4. **LLM 单章 rubric 评分偏糙**：对章间质量差异不够敏感（Ch33 有亮点却压到 2.0），不能当终判，需人工复核校准——印证"助手初筛 + 用户复核"分工的必要性。

## 提质方向（遵守 V7 边界 2：不做全自动 LLM 改写闭环）

| 方向 | 问题 | 手段 | 优先级 |
|------|------|------|:---:|
| D. T9 近似重复检测 | Ch31 重复但 T9=0 | 检测器从"全等整段"扩到"近似/改写重复"(n-gram/句级指纹) | 高（低风险独立） |
| A. voice 声纹区分 | 对白全员同质 | CreativeDirector/Writer 工艺卡加角色个体语气约束 | 高 |
| B. pacing 节奏 | 单人解谜/日志堆叠、场景切换少 | 控制单场景独白比例、鼓励场景切换；RuleAuditor 增连续独白检测 | 高 |
| C. exposition 融合 | 设定靠独白/日志硬灌 | 工艺卡强化"信息融进动作与对白" | 中 |
| E. LiteraryAuditor 校准 | character_autonomy 高估 | 校准评分标准使其对对白同质敏感 | 中 |

## 边界（本任务未越界）

- 不启动 Ch200（只跑到 Ch40）。
- 不改 Writer / RevisionHandler / CreativeDirector / SettlementExtractor（本任务是评估，提质另开任务）。
- 不做自动 LLM 改写闭环。
- 不改 accept 行为 / 不把文学分接入 QualityGate。
- 不放宽 T9/T10/T5/T6/T12 冻结口径。
- 隔离 DB，主库未受影响。

## 工程副产品（值得记的账）

- **脚本 DB 路径 footgun**：157b 系脚本默认 `DATABASE_URL` 回退到主库 `songyan.db`，`--init` 会误删主库（本次靠主库被占用锁保护未酿事故）。170b 两脚本已加固：进程内强制 `settings.database_url` 指向隔离 DB。建议后续同类脚本统一此做法。

## 与 Task 171 的关系

**170b = blocker → 暂缓 Task 171 Ch200。** 需先完成生成侧提质（优先 D + A/B），再回到 170b 复评；复评为 pass/observation 后方可规划 Ch200。
