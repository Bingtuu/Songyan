# Songyan（松烟）— 多 Agent 中文小说写作系统

> **松烟入墨，字句成锋。**
>
> 面向长篇中文小说创作的多 Agent AI 生产系统，基于 LangGraph 多 Agent 协作架构。

## 项目状态

**Phase 3 — 编排层已完成（19/19 Task），共 617 个测试全部通过。** V1.0 核心闭环已跑通，准备进入 Phase 4 评测优化。

| Phase | 状态 | 内容 |
|-------|------|------|
| Phase 1 | ✅ 完成 | 模型、Schema、Repository、Genre/Mode 配置、CLI |
| Phase 2 | ✅ 完成 | 10 个 Agent + 5 个质量检测工具 |
| Phase 3 | ✅ 完成 | LangGraph 编排 + Craft Card Prompts + SummaryWriter |

---

## 1. 设计方式、逻辑和结构

### 1.1 核心设计哲学

V1.0 唯一要验证的假设：

> **"每生成一章，系统都知道它为什么这么写、哪里可能错、改了什么、状态发生了什么变化、下一章应该继承什么。"**

这不是一个"一键写小说"的工具，而是一个**可控生产、审查、修订、沉淀上下文**的工程闭环。质量不是 Writer 一个人的事，而是贯穿八层防线的共同结果：

```
LAYER 1: CreativeModeProfile（创作模式选择）
LAYER 2: CreativeDirector（创作意图与张力地图）
LAYER 3: Genre Profile（题材规则约束）
LAYER 4: 写作工艺层 Prompt（文学质量约束）
LAYER 5: Writer Agent（创作执行）
LAYER 6: Reviewer 双层审查（RuleAuditor + LLMAuditor）
LAYER 7: LiteraryAuditor（文学性诊断，不阻塞）
LAYER 8: 人工确认（最终门控）
```

### 1.2 系统架构

```
用户输入 (CLI)
    |
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Songyan V1.0 单章闭环                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              LangGraph Phase1State                    │   │
│  │  （只存 ID：project_id / version_id / report_id...）  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          |                                   │
│  GoalPlanner → CreativeDirector → ContextManager → Writer   │
│       |              |                  |            |       │
│       ▼              ▼                  ▼            ▼       │
│  ChapterGoal    CreativeBrief    ContextPackage  ChapterVersion
│                                                          |   │
│              ┌───────────────────────────────────────────┐   │
│              ▼                                           ▼   │
│       RuleAuditor（代码）                        LLMAuditor（语义）
│              |                                           |   │
│              └──────────────────┬────────────────────────┘   │
│                                 ▼                            │
│                          ReviewMerger                        │
│                     MergedReviewReport                       │
│                                 |                            │
│              ┌──────────────────┼──────────────────┐       │
│              ▼                  ▼                  ▼       │
│       LiteraryAuditor    RevisionHandler      HumanConfirm │
│       （诊断，不阻塞）   （patch，最多 2 轮）  accept/edit/reject/back
│                                 |                  |       │
│                                 └──────────────────┘       │
│                                                    |       │
│                                          SettlementExtractor│
│                                          + SummaryWriter    │
│                                                    |       │
│                                             SQLite（唯一事实源）
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 关键设计原则

- **Agent 代表"可替换能力"，不是"人"**：同一套底层，换不同配置，就能服务长篇网文、类型小说、严肃文学。
- **数据先行，指标说话**：每个功能必须有明确的评测指标，"设定硬错误数 = 0""AI 腔规则命中数 < 2"。
- **状态闭环**：每章完成后完成完整的状态结算——角色状态、设定快照、伏笔追踪、数值账本全部更新。
- **能删则删，晚点再加**：如果某个功能不是验证当前假设所必需的，就不做。

### 1.4 项目结构

```
songyan/
├── creative_modes/          # 创作模式配置（webnovel / literary / hybrid）
├── genres/                  # 题材配置（xuanhuan / urban / scifi）
├── prompts/                 # Agent Prompt 模板
├── src/songyan/
│   ├── cli/                 # CLI 命令（create-project / list-projects）
│   ├── db/                  # SQLite Schema + Repository + 连接管理
│   ├── models/              # Pydantic 数据模型（35+ 个）
│   ├── agents/              # Agent 实现（11 个 Agent）
│   │   ├── goal_planner.py
│   │   ├── creative_director.py
│   │   ├── context_manager.py
│   │   ├── writer.py
│   │   ├── rule_auditor.py
│   │   ├── llm_auditor.py
│   │   ├── literary_auditor.py
│   │   ├── revision_handler.py
│   │   ├── settlement_extractor.py
│   │   └── summary_writer.py      # 章节摘要生成
│   ├── utils/               # 质量检测工具（5 个纯代码工具）
│   │   ├── ai_tells.py
│   │   ├── fatigue_words.py
│   │   ├── hook_checker.py
│   │   ├── paragraph_rhythm.py
│   │   └── numerical_validator.py
│   ├── workflows/           # LangGraph 工作流编排
│   │   ├── phase1_graph.py  # 12 节点状态机 + 公共 API
│   │   ├── review_merger.py # Rule + LLM 合并
│   │   ├── _nodes.py        # 节点函数
│   │   └── _helpers.py      # 数据加载辅助
│   ├── prompts/             # PromptLoader + 工艺卡系统
│   ├── genres/              # Genre Profile 加载器
│   └── creative_modes/      # CreativeModeProfile 注册表
├── tests/                   # 测试（617 passed）
├── tasks/                   # Task 规格 + 交接报告（19 个 DONE）
└── docs/                    # 文档
```

---

## 2. Vibe Coding 实现方式和流程

本项目采用 **Vibe Coding** 工程化方法：每次只做一个小任务，先读后做，可验证再推进。

### 2.1 任务拆解原则

| 好的粒度 | 不好的粒度 |
|----------|------------|
| "实现 Pydantic models（含 CreativeModeProfile）" | "实现 Songyan V1.0" |
| "实现 SQLite schema（含 literary_observations）" | "搭好整个 multi-agent 系统" |
| "实现 CreativeDirector Agent" | "把设计文档全部落地" |

### 2.2 开发流程

```
1. 读取 CLAUDE.md（不可违背规则）
2. 读取 docs/STATUS.md（当前状态）
3. 读取 tasks/00x-xxx.md（当前 Task 规格）
4. 读取上游 tasks/00x-xxx-DONE.md（交接报告）
5. 用 5-8 行总结任务边界
6. 确认边界后开始写代码
7. 测试 → ruff → 更新 STATUS.md → 生成 DONE.md → git commit
```

### 2.3 编码规范

- 所有函数必须带类型标注（Python 3.11+ 语法）
- 所有 Pydantic 模型必须定义完整字段
- 数据访问集中在 repository.py，Agent 不直接拼 SQL
- Prompt 放在 prompts/ 目录，不在代码里写长字符串
- 不写无用抽象，不提前做插件化
- 单文件不超过 400 行，超过拆模块
- 错误处理用自定义异常，不用裸 except
- 异步优先：所有 IO 操作 async/await
- 日志用 structlog，不用 print

---

## 3. 技术设计

### 3.1 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| Python | 3.11+ | 异步优先 `async/await` |
| Pydantic | v2 | 所有数据模型，严格类型校验 |
| LangGraph | >=0.2 | 工作流编排（Phase 3 使用） |
| LangChain | >=0.3 | LLM 接口 |
| litellm | latest | 多模型统一接口 |
| SQLite | 内置 | V1.0 唯一长期事实源 |
| Click | latest | CLI 框架 |
| structlog | latest | 结构化日志 |
| tiktoken | latest | Token 计数 |
| pytest | +pytest-asyncio | 测试框架 |

### 3.2 数据事实源设计

**SQLite 是 V1.0 唯一的长期事实源。**

- LangGraph state 只存 ID，不存完整业务对象
- 每次生成/修订创建 chapter_versions 新记录，禁止覆盖
- 每个节点从 SQLite 加载数据，不从 state 取正文
- character_states 为快照表，永远 INSERT 新记录，禁止 UPDATE

### 3.3 版本管理

| 类型 | 说明 | 谁创建 |
|------|------|--------|
| `draft` | AI 初稿 | Writer |
| `revision` | AI 修订版 | RevisionHandler |
| `accepted` | 人工确认版 | HumanConfirm |
| `edited` | 人工编辑版 | HumanConfirm |

### 3.4 审查体系

- **RuleAuditor**（代码检测）：AI 腔、疲劳词、段落长度、首屏钩子、字数统计、数值公式（< 200ms）
- **LLMAuditor**（语义审查）：角色行为一致性、叙事节奏、对话区分度、信息倾倒、设定一致性（12 维度）
- **LiteraryAuditor**（文学性诊断）：人物工具化、概念空转、过度平滑、有价值裂隙（不阻塞流程）
- **ReviewMerger**（轻量合并）：Rule + LLM 结果合并为统一报告，加权评分
- **RevisionHandler**（patch 修订）：从 MergedReviewReport 提取 patchable issues，保护 valuable_fissure，最多 2 轮

### 3.5 状态结算

每章 accept 后必须执行 SettlementExtractor + SummaryWriter：
- 角色状态更新（old_value 必须与 DB 当前值一致）
- 新设定快照（source_quote 必须在正文中存在）
- 伏笔追踪（source_version_id 必须记录）
- 数值账本（closing_value 必须等于公式值）
- 结算完成后 **SummaryWriter** 生成结构化摘要（plot_summary / key_events / characters_appeared / emotional_tone）

---

## 4. 已实现内容

### Phase 1 — 基础设施（Task 001 ~ 007）

| Task | 内容 | 测试 |
|------|------|------|
| **Task 001** | 项目初始化（骨架、依赖、CLI 入口） | 3 passed |
| **Task 002** | Pydantic 数据模型（35 个模型） | 68 passed |
| **Task 003** | SQLite Schema（13 张表、WAL、FK） | 26 passed |
| **Task 004** | Repository 层（11 个 Repository） | 51 passed |
| **Task 005** | Genre Profile 系统（3 JSON + 加载器） | 36 passed |
| **Task 006** | CreativeModeProfile 系统（3 JSON + 注册表） | 38 passed |
| **Task 007** | CLI 创建项目（交互向导 + list-projects） | 6 passed |

### Phase 2 — Agent 能力层（Task 008 ~ 017）

| Task | 内容 | 测试 |
|------|------|------|
| **Task 008** | GoalPlanner Agent（LLM Client + 章节目标制定） | 32 passed |
| **Task 009** | CreativeDirector Agent（CreativeBrief + 张力地图） | 23 passed |
| **Task 010** | ContextManager Agent（上下文包组装 + Token 裁剪） | 36 passed |
| **Task 011** | Writer Agent（章节正文生成 + Scene 分割） | 37 passed |
| **Task 012** | RuleAuditor Agent（纯代码规则检测 + 综合评分） | 29 passed |
| **Task 013** | LLMAuditor Agent（LLM 语义审查 12 维度） | 33 passed |
| **Task 014** | LiteraryAuditor Agent（文学性诊断 7 类观察 + 4 维度评分） | 29 passed |
| **Task 015** | RevisionHandler Agent（issue-driven patch 修订） | 38 passed |
| **Task 016** | SettlementExtractor Agent（状态结算提取 + 代码验证） | 40 passed |
| **Task 017** | Quality Utils（AI 腔/疲劳词/钩子/段落节奏/数值验证） | 78 passed |

### Phase 3 — 编排层 + Prompt 工程（Task 018 ~ 019）

| Task | 内容 | 测试 |
|------|------|------|
| **Task 018** | Craft Card Prompts（YAML 工艺卡 + PromptLoader + 8 模块 Writer） | 18 passed |
| **Task 019** | LangGraph 编排 + SummaryWriter（12 节点状态机 + ReviewMerger + 摘要生成） | 22 passed |

**总计：617 个测试全部通过，ruff 0 errors。**

### 4.1 已交付的关键能力

- **配置即代码**：`genres/*.json` 和 `creative_modes/*.json` 是题材/模式规则的事实源，新增配置无需改代码
- **动态加载**：`load_genre_profile()` / `load_creative_mode_profile()` 带内存缓存，异常信息包含可用选项
- **交互式 CLI**：`songyan create-project` 8 步向导自动关联 genre_id + mode_id，保存到 SQLite
- **数据持久化**：Project / Character / Chapter / Review / Settlement 共 11 个 Repository 完整覆盖
- **版本链**：chapter_versions INSERT only，chapter_heads 指向当前和 accepted 版本
- **双层审查**：RuleAuditor（代码）+ LLMAuditor（语义）→ ReviewMerger 合并 → LiteraryAuditor（文学性诊断）
- **LangGraph 编排**：12 节点状态机，条件路由（revision 循环最多 2 轮，human_confirm 支持 accept/edit/reject/back）
- **Issue-driven 修订**：RevisionHandler 从 MergedReviewReport 提取 patchable issues，保护 valuable_fissure
- **状态闭环**：SettlementExtractor 执行 5 条验证规则后 INSERT 新快照，SummaryWriter 生成结构化摘要
- **工艺卡系统**：YAML 工艺卡（_manifest.yaml + vX.Y.Z.yaml），PromptLoader 单例支持标签过滤和版本切换

### 4.2 快速开始

```bash
# 安装
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 创建项目
songyan create-project

# 列出项目
songyan list-projects

# 运行测试
pytest tests/ -v
```

### 4.3 验证命令

```bash
pytest tests/ -v
# Expected: 617 passed

ruff check src/ tests/
# Expected: All checks passed
```

---

## 5. 下一阶段（Phase 4）

- **端到端集成测试**：验证单章完整流程（创建项目 → 生成章节 → 审查 → 修订 → 确认 → 结算 → 摘要）
- **评测集**：3 个种子项目（xuanhuan + webnovel），客观指标验收
- **验收指标**：设定硬错误数 = 0、AI 腔 < 2 处/章、审查漏检率 < 35%、状态结算准确率 > 90%

---

## 开发文档

- `CLAUDE.md` — 开发代理指令与不可违背规则（67 条）
- `system_prompt/development-tech-plan-v2.md` — V2 技术方案
- `system_prompt/ai-collaboration-guide.md` — 多 AI 协作规范
- `docs/INDEX.md` — 文档索引
- `docs/STATUS.md` — 项目状态看板

## 许可证

AGPL-3.0
