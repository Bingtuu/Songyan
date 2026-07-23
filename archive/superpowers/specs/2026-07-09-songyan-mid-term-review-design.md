# Songyan 中期评估报告设计文档

> 设计日期: 2026-07-09
> 目标受众: 工程团队与产品/业务决策者兼顾的通用评估
> 报告结构: 主报告 + 4 份专题附录

---

## 1. 项目背景

Songyan（松烟）是一个面向长篇中文小说的多 Agent 协作写作系统，当前处于 **V7 / 170j** 阶段。项目已完成 V5（150 章工程验收）、V6（叙事骨架 + 度量 + 长跑底盘，Ch1–Ch150 150/150 accept）、V7 阶段 W/X/Y（篇章级修复、叙事自驱、自适应门禁）。当前核心阻塞是文学提质专项：中段窗口（Ch28–Ch40）LLM rubric voice 2.00 / exposition 2.25 / 5 维均值 2.55，未达 Ch200 放行标准（voice ≥3.0 / exposition ≥3.0 / 均值 ≥3.0），Task 171 Ch200 长跑入口冻结。

## 2. 报告目标

回答四个核心问题：

1. **架构可行性**: 当前架构能否支撑 200 章以上稳定生成并保证文学性/可读性/质量过关？
2. **文学性卡点**: 当前文学性卡点的根因是什么？背后是什么缺陷？最佳解决路径是什么？
3. **其他缺陷**: 项目还有哪些未解决的缺陷和风险？
4. **前景定位**: 如何定位 Songyan 的长期前景？

## 3. 报告结构（方案 B）

### 3.1 主报告

**文件**: `docs/mid-term-review-report.md`

| 章节 | 字数目标 | 内容 |
|------|---------|------|
| 执行摘要 | 400–600 | 四问的直接答案、核心结论、关键风险 |
| 评估范围与方法 | 300–500 | 证据来源、评估维度、可信度说明 |
| 核心结论 | 800–1200 | 对四问的展开回答 |
| 关键指标总览 | 600–800 | V5/V6/V7 指标、170h/170i 复评、Ch200 入口差距 |
| 总体判断与建议 | 600–1000 | 前景定位、优先级、决策建议 |

### 3.2 专题附录

**目录**: `docs/mid-term-review/`

| 文件 | 核心问题 | 主要内容 |
|------|---------|----------|
| `01-architecture-assessment.md` | 架构能否支撑 200 章+ | Context Diet 2.0、叙事骨架、事实源治理、门禁系统、工程 blockers |
| `02-literary-blocker-analysis.md` | 文学性卡点根因与路径 | 170b–170i 复盘、AI 腔/声纹扁平/认知冲突模板化、解决路径评估 |
| `03-other-defects-and-risks.md` | 其他缺陷与风险 | 量具可信度、测试覆盖、工程债、LLM 依赖、Ch250/Ch300 不确定性 |
| `04-outlook-and-recommendations.md` | 前景定位与建议 | 研究项目/工程产品/垂直工具定位、ROI、决策树、下一步 |

## 4. 研究方法

### 4.1 内部证据

- **项目文档**: `docs/STATUS.md`, `tasks/V7-README.md`, `docs/v7-plan.md`, `archive/v7/tasks/170-literary-quality-remediation-README.md`, 各 Task DONE 文件与复评报告
- **代码审查**: `src/songyan/agents/`（Writer / CreativeDirector / GoalPlanner / RuleAuditor / LLMAuditor / RevisionHandler / LiteraryAuditor）, `src/songyan/workflows/`, `src/songyan/evals/`, `prompts/cards/`
- **运行数据**: `run-bba292da`（V6）、`run-83a004b3`（170i）、170h/170i 复评报告中的量化指标
- **测试与验证**: 分模块 pytest 结果、`ruff check`、测试策略

### 4.2 外部研究

- LLM 长篇叙事生成的前沿实践与限制
- AI 腔（AI tell / AI tone）的成因与缓解方法
- 角色声纹工程（voice differentiation / dialogue style cards）在 LLM 中的应用
- 长篇生成中的上下文管理、RAG、摘要、状态结算最佳实践
- 当前主流模型（DeepSeek / Kimi / Claude / GPT-4）在长篇中文小说生成上的能力边界

### 4.3 分析框架

- **P/L/T/G/V 五维评估**: 文本洁净（P）、文学不衰减（L）、线索经济（T）、门禁可生产（G）、验证（V）
- **量具优先**: 任何文学性判断必须同时看机器指标、代码检测、LLM rubric、人工/LLM 抽读
- **收益递减分析**: 当前路径 B 已连续两次（170h/170i）未达标，需评估继续同层级约束的收益与更激进方案的成本

## 5. 各专题核心论点与证据需求

### 5.1 01-architecture-assessment.md

- **论点 1**: Context Diet 2.0 在工程上已证明可支撑 150 章，但 200–300 章的上下文压缩边际效益会递减。
- **论点 2**: 叙事骨架（StoryOutline / ArcPlan / PlotThread）解决了"为什么写"的问题，但未直接解决"怎么写得好看"。
- **论点 3**: 事实源治理（settlement evidence、character states snapshots、setting tracking）是项目的核心护城河，已相对成熟。
- **论点 4**: 自适应门禁（168/169/170）已冻结 T12，但文学质量门仍依赖 LLM rubric，存在主观性和模型能力边界。
- **证据需求**: V6 run-bba292da 数据、Context Diet 压力测试、DB 大小增长曲线、adaptive gate 验证报告。

### 5.2 02-literary-blocker-analysis.md

- **论点 1**: 当前文学性卡点不是量具问题（T9 0/0、偏差 0/4），而是生成侧深层问题。
- **论点 2**: 根本缺陷是 **LLM 倾向用结构化、说明性、对称化的模板化语言处理高概念信息**，而工程约束只能改变"形式载体"，难以改变"信息生长方式"。
- **论点 3**: 人类角色声纹扁平是因为当前声纹卡是"静态标签"（口头禅、句式偏好）而非"动态行为模式"（在冲突/压力/误判下的差异化反应）。
- **论点 4**: 认知冲突模板被模型写成"结构化心理描写"，而非具有个人历史的独特对白。
- **解决路径评估**:
  - 路径 A: 继续追加同层级工艺约束（收益递减，预计无法单独达标）
  - 路径 B1: 激进声纹工程（逐角色少样本示例、固定台词槽、禁忌词、句式配额）
  - 路径 B2: AI 腔后处理/句式扰动（去模板化 rewrite、反 AI 腔 prompt）
  - 路径 C: 接受当前 LLM 能力边界，降级目标或转向辅助工具
- **证据需求**: 170b–170i 全部复评报告、代表性章节文本样本、RuleAuditor 检测结果、LLMAuditor rubric 数据。

### 5.3 03-other-defects-and-risks.md

- **缺陷 1**: 量具仍部分依赖 LLM 主观评分，机器指标（literary_quality / character_autonomy）与人工判断存在偏差。
- **缺陷 2**: 测试覆盖偏重工程流程，对文学质量的验证依赖昂贵的真实 LLM 调用，难以规模化。
- **缺陷 3**: 对 DeepSeek / 特定模型能力的强依赖，模型升级或切换可能破坏现有 prompt 工程。
- **缺陷 4**: Ch250/Ch300 的验证尚未开始，存在未知的长程退化风险（概念通胀复发、伏笔调度失效、上下文压缩失真）。
- **缺陷 5**: 全自动 LLM 改写闭环未建立，文学修复仍需大量人工介入。
- **证据需求**: 测试矩阵、pytest 覆盖、模型调用成本估算、T11 伏笔兑现数据。

### 5.4 04-outlook-and-recommendations.md

- **定位选项**:
  - A. 继续攻坚，目标 Ch300（高投入、高风险、高研究价值）
  - B. 转向"长篇初稿生成器 + 人工精修"工具（降低文学质量目标，提升可用性）
  - C. 冻结 Ch200+，聚焦当前 150 章能力的产品化（风险最低）
  - D. 作为研究平台，输出方法论和开源组件（不追求商业闭环）
- **建议**: 基于证据给出明确推荐，并附决策树（如果 170j 复评仍不达标，应如何决策）。

## 6. 交付物清单

- [ ] `docs/mid-term-review-report.md`（主报告）
- [ ] `docs/mid-term-review/01-architecture-assessment.md`
- [ ] `docs/mid-term-review/02-literary-blocker-analysis.md`
- [ ] `docs/mid-term-review/03-other-defects-and-risks.md`
- [ ] `docs/mid-term-review/04-outlook-and-recommendations.md`

## 7. 质量门控

- 每份文档必须标注证据来源（文档路径、run_id、代码位置、外部 URL）
- 所有量化判断必须引用项目实际数据
- 文学性分析必须同时引用机器指标、代码检测、LLM rubric、文本样本
- 前景建议必须明确说明前提假设和风险

---

*本设计文档经用户批准后，将用于指导中期评估报告的撰写。*
