# Songyan 中期评估报告撰写计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于项目内部证据和外部领域研究，撰写一份完整的中期评估报告（主报告 + 4 份专题附录），回答架构可行性、文学性卡点、其他缺陷、前景定位四个核心问题。

**Architecture:** 采用"主报告 + 专题附录"结构，主报告提供执行摘要和核心结论，专题附录承载技术分析和证据细节；所有判断必须引用项目实际数据或外部权威来源。

**Tech Stack:** Markdown、项目内部文档/代码/运行数据、WebSearch / FetchURL 外部调研、Pydantic 模型（用于指标数据校验，可选）。

---

## 文件结构

### 新建文件

- `docs/mid-term-review-report.md` — 主报告（执行摘要 + 核心结论 + 关键指标 + 总体判断）
- `docs/mid-term-review/01-architecture-assessment.md` — 架构可行性评估
- `docs/mid-term-review/02-literary-blocker-analysis.md` — 文学性卡点根因与路径
- `docs/mid-term-review/03-other-defects-and-risks.md` — 其他缺陷与风险
- `docs/mid-term-review/04-outlook-and-recommendations.md` — 前景定位与建议

### 可能修改的文件

- `docs/INDEX.md` — 添加中期评估报告入口
- `docs/STATUS.md` — 如果报告结论需要更新当前状态描述（本次可能只读）

---

## Task 1: 收集和整理内部证据

**Files:**
- Read: `docs/STATUS.md`
- Read: `tasks/V7-README.md`
- Read: `docs/v7-plan.md`
- Read: `archive/v7/tasks/170-literary-quality-remediation-README.md`
- Read: `archive/v7/tasks/170i-protagonist-cognitive-conflict-voice-anchoring-DONE.md`
- Read: `archive/v7/reports/task-170i-remediation-reeval-report.md`
- Read: `archive/v7/reports/task-170h-remediation-reeval-report.md`
- Read: `archive/v7/tasks/170h-structural-rewrite-voice-exposition-DONE.md`
- Read: `tasks/159-v6-final-acceptance-DONE.md` 或 `archive/v6/reports/task-159-v6-final-acceptance-report.md`
- Read: `docs/300-chapter-gap-analysis.md`

- [ ] **Step 1: 提取关键指标表格**

  从上述文档中提取以下数据并整理成表格：
  - V6 长跑结果：`run-bba292da` 150/150 accept、health ≥8.2、orphan 斜率 0.0897
  - 170h 复评：voice 1.50 / exposition 2.50 / 窗口均值 2.65
  - 170i 复评：voice 2.00 / exposition 2.25 / 窗口均值 2.55
  - Ch200 入口标准：voice ≥3.0 / exposition ≥3.0 / pacing ≥3.0 / 均值 ≥3.0、exposition_carrier_count ≤1、T9 0/0、偏差 <3
  - 170i 工程侧正面指标：T9 0/0、exposition_carrier 0、机器/LLM 偏差 0/4

- [ ] **Step 2: 提取关键文本样本**

  从 `archive/v7/reports/task-170i-remediation-reeval-report.md` 或运行数据中提取 2–3 个代表性文本片段，用于说明：
  - AI 腔模板化
  - 人类角色声纹扁平
  - 认知冲突被写成结构化心理描写

- [ ] **Step 3: 验证指标来源**

  检查每个指标是否能在文档中找到明确出处；对找不到出处的指标标记为"待确认"，必要时搜索相关 Task 文件。

---

## Task 2: 进行外部调研

**Files:**
- Create: `docs/mid-term-review/_external-research-notes.md`（临时笔记，完成后可删除或归档）

- [ ] **Step 1: 搜索 LLM 长篇叙事生成的能力边界**

  使用 WebSearch 搜索：
  - "LLM long-form fiction writing coherence 200 chapters"
  - "AI tone AI tell detection creative writing"
  - "large language model character voice consistency long narrative"
  - "LLM 长篇小说生成 200章 一致性"

- [ ] **Step 2: 搜索角色声纹工程方法**

  使用 WebSearch 搜索：
  - "dialogue style cards few-shot character voice LLM"
  - "character voice differentiation prompt engineering"
  - "LLM narrative voice embedding style transfer"

- [ ] **Step 3: 搜索 AI 腔缓解和后处理方法**

  使用 WebSearch 搜索：
  - "reduce AI tone in LLM generated prose"
  - "LLM writing de-templating rewrite techniques"
  - "anti-AI-tell prompt engineering fiction"

- [ ] **Step 4: 整理外部调研笔记**

  将搜索结果按主题整理到 `_external-research-notes.md`，每个来源标注 URL、核心结论、对 Songyan 的适用性评估。

---

## Task 3: 撰写 01-architecture-assessment.md

**Files:**
- Create: `docs/mid-term-review/01-architecture-assessment.md`

- [ ] **Step 1: 撰写"150 章已经证明什么"**

  内容要点：
  - Context Diet 2.0 四组件的有效性
  - 叙事骨架（StoryOutline / ArcPlan / PlotThread）解决目标派生问题
  - 事实源治理（settlement evidence、character states snapshots）的成熟度
  - 自适应门禁冻结 T12

- [ ] **Step 2: 撰写"200 章+ 的新挑战"**

  内容要点：
  - 上下文压缩的边际效益递减
  - 伏笔跨度 ≥50 章的主动调度尚未在长跑中验证
  - 文学质量门的主观性和模型能力边界
  - DB 大小和扫描耗时增长（T5）

- [ ] **Step 3: 给出架构可行性判断**

  明确结论：当前架构在"工程稳定性"和"事实源治理"上可以继续扩展，但"文学性"不是仅靠架构扩展能解决的问题。

---

## Task 4: 撰写 02-literary-blocker-analysis.md

**Files:**
- Create: `docs/mid-term-review/02-literary-blocker-analysis.md`

- [ ] **Step 1: 复盘 170b–170i**

  按时间线整理：
  - 170b 判定 blocker 的依据
  - 170c/170d 量具校准
  - 170e/170f/170g 生成侧提质
  - 170g Phase2 / 170h / 170i 路径 B 连续未达标

- [ ] **Step 2: 分析根因**

  核心论点：
  - 工程约束只能改变"信息载体形式"，难以改变 LLM 的"信息生长方式"
  - 当前声纹卡是静态标签，不是动态行为模式
  - 认知冲突模板被模型结构化执行，失去个人历史感

- [ ] **Step 3: 评估解决路径**

  对每条路径给出评估：
  - 路径 A（继续同层级约束）：收益递减，不建议单独依赖
  - 路径 B1（激进声纹工程）：包括逐角色少样本示例、固定台词槽、禁忌词、句式配额；有潜力但工程量大
  - 路径 B2（AI 腔后处理/句式扰动）：包括去模板化 rewrite、反 AI 腔 prompt；可能短期见效但治标不治本
  - 路径 C（接受 LLM 能力边界）：降级目标或转向辅助工具

- [ ] **Step 4: 给出推荐路径**

  明确推荐：建议采用 **B1 + B2 组合试点**，设定 2–3 轮小样本验证窗口，若仍不达标则升级到路径 C。

---

## Task 5: 撰写 03-other-defects-and-risks.md

**Files:**
- Create: `docs/mid-term-review/03-other-defects-and-risks.md`

- [ ] **Step 1: 量具与验证风险**

  内容要点：
  - LLM rubric 的主观性
  - 机器 literary_quality / character_autonomy 与人工判断的偏差
  - 文学质量验证依赖昂贵的真实 LLM 调用，难以规模化

- [ ] **Step 2: 工程与测试风险**

  内容要点：
  - 对 DeepSeek / 特定模型的强依赖
  - 测试覆盖偏重工程流程，对文学质量覆盖不足
  - Windows pytest 长耗时问题

- [ ] **Step 3: 长程未知风险**

  内容要点：
  - Ch250/Ch300 未验证
  - 概念通胀可能复发
  - 伏笔调度在长窗口中的失效风险
  - 上下文压缩失真导致角色/设定遗忘

- [ ] **Step 4: 组织与流程风险**

  内容要点：
  - 全自动 LLM 改写闭环未建立
  - 文学修复仍依赖人工介入
  - 任务链长，状态同步成本高

---

## Task 6: 撰写 04-outlook-and-recommendations.md

**Files:**
- Create: `docs/mid-term-review/04-outlook-and-recommendations.md`

- [ ] **Step 1: 定义四种前景定位**

  - A. 继续攻坚 Ch300（研究导向，高投入高风险）
  - B. 转向"长篇初稿生成器 + 人工精修"工具（降低文学目标，提升可用性）
  - C. 冻结 Ch200+，聚焦 150 章能力产品化（风险最低）
  - D. 作为研究平台，输出方法论和开源组件

- [ ] **Step 2: 给出明确推荐**

  推荐方向（待证据支撑后确定，初稿倾向 B 或 C，取决于 170j 结果）。

- [ ] **Step 3: 制定决策树**

  决策节点：
  - 170j 复评是否达标？
  - Ch200 长跑是否 150/200 accept 且文学指标 ≥3.0？
  - Ch250/Ch300 每级是否达标？

- [ ] **Step 4: 给出下一步行动建议**

  短期（1–2 周）：170j 方案验证
  中期（1–2 月）：Ch200 入口重新评估
  长期（3–6 月）：根据 Ch200 结果决定方向

---

## Task 7: 撰写主报告 mid-term-review-report.md

**Files:**
- Create: `docs/mid-term-review-report.md`

- [ ] **Step 1: 撰写执行摘要**

  用 400–600 字直接回答四问，给出核心结论。

- [ ] **Step 2: 撰写评估范围与方法**

  说明证据来源、评估维度和可信度限制。

- [ ] **Step 3: 撰写核心结论**

  对四个问题分别展开，每部分引用专题附录。

- [ ] **Step 4: 撰写关键指标总览**

  用表格呈现 V5/V6/V7 指标、170h/170i 复评数据、Ch200 入口差距。

- [ ] **Step 5: 撰写总体判断与建议**

  总结前景定位、优先级和下一步行动。

---

## Task 8: 交叉验证和一致性检查

**Files:**
- Read: `docs/mid-term-review-report.md`
- Read: `docs/mid-term-review/01-architecture-assessment.md`
- Read: `docs/mid-term-review/02-literary-blocker-analysis.md`
- Read: `docs/mid-term-review/03-other-defects-and-risks.md`
- Read: `docs/mid-term-review/04-outlook-and-recommendations.md`

- [ ] **Step 1: 检查内部一致性**

  确保主报告结论与专题附录一致，没有矛盾。

- [ ] **Step 2: 检查证据引用**

  确保每个量化判断都有来源，每个外部结论都有 URL。

- [ ] **Step 3: 检查术语统一**

  确保"AI 腔"、"声纹扁平"、"认知冲突"、"路径 B/C" 等术语在各文档中定义一致。

- [ ] **Step 4: 运行 ruff 检查（仅涉及 Python 时）**

  本次报告为 Markdown，不涉及 Python 代码；但如有辅助脚本，运行 `ruff check src/ tests/`。

---

## Task 9: 更新文档索引

**Files:**
- Modify: `docs/INDEX.md`

- [ ] **Step 1: 在 INDEX.md 中添加中期评估报告入口**

  在"默认必读"或"按场景查阅"部分添加：
  - `docs/mid-term-review-report.md` — 中期评估报告（执行摘要）
  - `docs/mid-term-review/` — 中期评估专题附录

---

## Self-Review

- **Spec coverage:** 设计文档中的 5 份交付物、4 个核心问题、研究方法和质量门控都有对应任务。
- **Placeholder scan:** 无 TBD/TODO；推荐路径为"待证据支撑后确定"是合理的开放性结论，不是占位符。
- **Type consistency:** 不涉及代码类型；文件路径和术语在各任务中一致。
