# Songyan（松烟）V1.0 开发技术方案（简短版）

> 基于 design_docs_v2 对齐版本。确认方向后扩充为完整实施文档。

---

## 1. 项目定位与验证目标

**Songyan** 是一个面向长篇中文小说创作的多 Agent AI 生产系统。V1.0 只验证一个核心假设：

> 每生成一章，系统都知道它为什么这么写、哪里可能错、改了什么、状态发生了什么变化、下一章应该继承什么。

**V1.0 范围**：单章闭环验证（生成 → 审查 → 修订 → 状态结算 → 人工确认），支持 3 种题材（玄幻/都市/科幻）和 3 种创作模式（网文/严肃文学/混合）。

---

## 2. 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| Python | 3.11+ | 异步优先 async/await |
| Pydantic | v2 | 所有数据模型，严格类型校验 |
| LangGraph | >=0.2 | 工作流编排 |
| LangChain | >=0.3 | LLM 接口 |
| litellm | latest | 多模型统一接口（OpenAI/DeepSeek/Anthropic） |
| SQLite | 内置 | V1.0 唯一长期事实源 |
| Click | latest | CLI 框架 |
| structlog | latest | 结构化日志 |
| tiktoken | latest | Token 计数 |
| pytest | +pytest-asyncio | 测试框架 |

**V1.0 不做**：Web UI、PostgreSQL/Qdrant/Redis、Celery、本地模型（vLLM/Ollama）、多租户、复杂权限。

---

## 3. 核心架构：八层质量防线

系统不是让 Writer 一个人写好，而是八层防线的共同结果：

```
Layer 1: CreativeModeProfile（创作模式选择）     — 网文 or 严肃文学
Layer 2: CreativeDirector（创作意图与张力地图）   — 写前定方向
Layer 3: Genre Profile（题材规则约束）            — 玄幻/都市/科幻各有规矩
Layer 4: 写作工艺层 Prompt（文学质量约束）        — 黄金开篇、ShowDon'tTell 等
Layer 5: Writer Agent（创作执行）                — AI 动笔
Layer 6: Reviewer 双层审查                        — RuleAuditor(代码) + LLMAuditor(语义)
Layer 7: LiteraryAuditor（文学性诊断）            — 防"流畅但平庸"
Layer 8: 人工确认（最终门控）                     — accept / edit / reject / back
```

**数据铁律**：SQLite 是唯一长期事实源。LangGraph state 只存 ID，不存完整业务对象。

---

## 4. Agent 分工与流程

### 4.1 9 个 Agent 一览

| Agent | 核心职责 | 不做什么 | 温度 |
|-------|----------|----------|------|
| **GoalPlanner** | 项目设定收集（8 步向导）、章节目标制定 | 不写正文、不做结算 | 0.7 |
| **CreativeDirector** | 写前生成本章创作意图 + 张力地图 + 禁忌清单 | 不直接写正文 | 0.7 |
| **ContextManager** | 加载 Genre/Mode Profile、按 Token 预算组装上下文包 | 不做生成、不做审查 | — |
| **Writer** | 按场景生成正文（受全部约束层约束） | 不做审查、不修改设定 | 0.7 |
| **RuleAuditor** | 代码层规则检测（AI 腔/疲劳词/段落/首屏/字数） | 不做语义判断 | — |
| **LLMAuditor** | LLM 语义审查（角色/节奏/对话/设定一致性） | 不做代码检测 | 0.3 |
| **LiteraryAuditor** | 文学性诊断（人物工具化/概念空转/裂隙） | 不阻塞流程、不修改正文 | 0.3 |
| **RevisionHandler** | 按 issue 局部 patch 修订（最多 2 轮） | 不整章重写 | 0.3 |
| **SettlementExtractor** | 状态结算提取 + 代码验证 + 更新 DB | 不写摘要 | 0.3 |

### 4.2 修正后的工作流顺序

```
GoalPlanner ──▶ CreativeDirector ──▶ ContextManager ──▶ Writer
                                                          |
                                                          ▼
                                                ┌──────────────────┐
                                                │   RuleAuditor    │  < 200ms，代码检测
                                                │   LLMAuditor     │  ~30s，语义审查
                                                └────────┬─────────┘
                                                         │
                                              MergedReviewReport
                                                         │
                                                         ▼
                                                LiteraryAuditor（不阻塞）
                                                         │
                              ┌──────────────────────────┼──────────────────────────┐
                              ▼                          ▼                          ▼
                        无 critical/major          RevisionHandler               HumanConfirm
                              |                    （局部 patch，最多 2 轮）      accept → Settlement
                              |                           |                    edit / reject / back
                              └───────────────────────────┘
```

### 4.3 关键输出物

- **ChapterGoal**：章节目标（事件、情感弧、钩子、字数）
- **CreativeBrief**：创作意图 + required_tensions + forbidden_patterns + allowed_fissures
- **ContextPackage**：分区上下文包（硬约束/角色状态/最近剧情/伏笔/软参考/题材规则/模式规则）
- **MergedReviewReport**：RuleAuditor + LLMAuditor 合并审查报告
- **LiteraryAuditResult**：文学性诊断（observations，不阻塞）
- **StateSettlement**：角色状态变更 / 新设定 / 伏笔操作 / 数值变更

---

## 5. 三大关键机制

### 5.1 CreativeModeProfile（创作模式系统）

同一套代码，不同配置，服务不同创作场景：

| 模式 | 核心差异 | 审查侧重 |
|------|----------|----------|
| **网文** | 节奏/爽点/钩子权重高，容忍一定套路 | narrative_pacing=1.2, cliche_risk=0.8 |
| **严肃文学** | 人物自治/概念落地/裂隙保留权重高 | character_autonomy=1.5, cliche_risk=1.5 |
| **混合** | 平衡两者 | 中间权重 |

新增模式只需一个 JSON 配置文件，无需改 Agent 代码。

### 5.2 双层审查（RuleAuditor + LLMAuditor）

| 维度 | 执行方 | 方式 | 耗时 |
|------|--------|------|------|
| AI 腔、疲劳词、段落节奏、首屏/章末钩子、字数、数值公式 | RuleAuditor | 代码规则（正则/统计） | < 200ms |
| 设定一致性、角色行为、叙事节奏、对话区分度、信息倾倒、ShowDon'tTell | LLMAuditor | LLM 语义理解 | ~30s |

合并为 `MergedReviewReport`，统一输出。RuleAuditor 大量 critical 时可跳过 LLMAuditor（快速失败）。

### 5.3 状态结算（SettlementExtractor）

每章 accept 后必须执行：
- 角色状态变更 → `character_states` **INSERT 新快照，永远不 UPDATE**
- 新设定登记 → `setting_snapshots`（带 `setting_key` 追踪演变）
- 伏笔操作 → `foreshadowings`（带 `source_version_id`）
- 数值变更 → `numerical_ledgers`（代码验证 `closing_value == opening + 增量 - 消耗`）
- 结算失败 → 标记 `needs_human_review`，不阻塞流程

---

## 6. 项目结构

```
songyan/
├── pyproject.toml, .env.example, README.md
├── CLAUDE.md                     # 不可违背规则清单
├── creative_modes/               # 创作模式配置（webnovel/literary/hybrid.json）
├── genres/                       # 题材配置（xuanhuan/urban/scifi.json）
├── prompts/                      # Agent Prompt 模板（不在代码里写长字符串）
│   ├── writer.md, craft_card.md
│   ├── creative_director.md, goal_planner.md
│   ├── rule_auditor.md, llm_auditor.md, literary_auditor.md
│   └── settlement_extractor.md
├── src/songyan/
│   ├── cli/main.py               # CLI 入口（Click）
│   ├── db/                       # SQLite schema + repository + connection
│   ├── models/                   # Pydantic v2 数据模型
│   ├── agents/                   # 9 个 Agent 实现
│   ├── workflows/phase1_graph.py # LangGraph 工作流编排
│   ├── utils/                    # 质量检测工具（AI腔/疲劳词/钩子/段落/Token）
│   └── creative_modes/registry.py # CreativeModeProfile 注册表
├── tests/                        # pytest + pytest-asyncio
└── evals/runner.py               # 评测集运行器
```

---

## 7. 开发阶段规划

### Phase 1：基础设施（Task 001-006）
- 项目初始化、Pydantic 模型、SQLite schema、Repository 层
- Genre Profile 加载器 + 3 个题材配置
- CreativeModeProfile 注册表 + 3 个模式配置

### Phase 2：写前管线（Task 007-011）
- CLI 创建项目（8 步向导，含模式选择）
- GoalPlanner（章节目标制定）
- CreativeDirector（创作意图+张力地图）
- ContextManager（Token 预算 + 上下文包组装）
- Writer Agent（按场景生成，四层 Prompt 注入）

### Phase 3：审查与修订（Task 012-015）
- RuleAuditor（代码检测，< 200ms）
- LLMAuditor（12 维度语义审查）
- LiteraryAuditor（文学性诊断，不阻塞）
- RevisionHandler（issue-driven patch，保护 valuable_fissure，最多 2 轮）

### Phase 4：结算与闭环（Task 016-019）
- SettlementExtractor（状态提取 + 代码验证 + INSERT 快照）
- HumanConfirm CLI（accept/edit/reject/back）
- LangGraph 工作流编排（修正后的顺序）
- 集成测试 + 评测集

---

## 8. V1.0 验收指标（客观可测量）

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| 设定硬错误数 | 0 | critical world_consistency = 0 |
| 人工大改比例 | < 30% | 需人工大幅修改的章节比例 |
| 审查漏检率 | < 20% | 人工发现但 AI 没发现的问题比例 |
| 修订后新问题数 | 0 | 第二轮审查新问题数 = 0 |
| AI 腔规则命中数 | < 2 处/章 | RuleAuditor 检测数 |
| 疲劳词命中数 | < 3 处/章 | RuleAuditor 检测数 |
| 首屏钩子达标率 | 100% | 前 300 字有吸引力事件 |
| 状态结算字段准确率 | > 90% | old_value 与 DB 一致率 |
| 概念空转段落数 | 0 | LiteraryAuditor 检测数 |

**移除指标**：overall_score > 6.5/10（太主观，容易自欺）。

---

## 9. 关键约束（不可违背）

1. **SQLite 唯一事实源**：LangGraph state 只存 ID，不存正文/报告/档案。
2. **版本不覆盖**：每次生成/修订都创建新的 `chapter_versions` 记录。
3. **character_states 快照表**：永远 INSERT 新记录，禁止 UPDATE。
4. **critical/major 必须有 evidence_quote**：无证据的 issue 不进入自动修订。
5. **自动修订最多 2 轮**：第 2 轮仍有问题 → 上报人工。
6. **LiteraryAuditor 不阻塞**：诊断只供参考，不阻塞入库。
7. **新增模式零代码**：CreativeModeProfile 新增模式只需 JSON 配置。

---

## 10. 待对齐问题

以下问题需要确认后写入完整版方案：

1. **LLM 选型**：默认使用 DeepSeek-chat？还是支持多模型切换（通过 litellm 环境变量）？
2. **评测集执行**：是否需要准备 3 个题材 × 2 种模式的人工种子章节？还是先用 mock 数据跑通流程？
3. **CLI 交互深度**：HumanConfirm 是简单的 y/n/e/r/b 选择，还是需要在 CLI 中嵌入文本编辑器（如调用系统默认编辑器）？
4. **Prompt 管理方式**：直接放在 `prompts/*.md` 文件中，还是用 Jinja2 模板引擎？
5. **上下文 Token 预算**：默认 32K 是否足够？是否需要支持 64K/128K 模型的动态预算？
6. **开发节奏**：是严格按 19 个 Task 顺序逐个完成，还是可以并行开发独立模块（如 RuleAuditor 的工具函数与 Writer 可并行）？

---

> **下一步**：确认以上方向后，本方案将扩充为包含每个 Task 的详细接口定义、数据库 schema、Prompt 模板、测试策略的完整实施文档。
