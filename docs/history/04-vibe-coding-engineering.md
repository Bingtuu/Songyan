好的工程不是一次性写对的，而是在正确的约束下一步步走出来的。

# NovelForge — Vibe Coding 工程化开发手册

## Phase 1 单章闭环 MVP（完整 Prompt + 规范 + 任务拆解）

> **版本**: v1.0.0  
> **日期**: 2026-05-16  
> **用途**: 指导 AI 编程助手（Cursor / Claude Code / Copilot）按工程规范完成 Phase 1 开发  
> **核心原则**: 每次只做一个小任务，先读后做，可验证再推进

---

## 目录

- [1. 工程规范](#1-工程规范)
- [2. 项目管理框架](#2-项目管理框架)
- [3. 流程标准化](#3-流程标准化)
- [4. Phase 1 任务拆解（10 个 Task）](#4-phase-1-任务拆解10-个-task)
- [5. 所有 Prompt 汇总](#5-所有-prompt-汇总)
  - [5.1 Master System Prompt](#51-master-system-prompt)
  - [5.2 启动 Prompt](#52-启动-prompt)
  - [5.3 任务执行 Prompt](#53-任务执行-prompt)
  - [5.4 Writer Prompt](#54-writer-prompt)
  - [5.5 Reviewer Prompt](#55-reviewer-prompt)
  - [5.6 Planner Prompt](#56-planner-prompt)
  - [5.7 RevisionHandler Prompt](#57-revisionhandler-prompt)
  - [5.8 HumanConfirm Prompt](#58-humanconfirm-prompt)
- [6. 项目管理工具模板](#6-项目管理工具模板)
  - [6.1 STATUS.md](#61-statusmd)
  - [6.2 INDEX.md](#62-indexmd)
  - [6.3 ADR 模板](#63-adr-模板)
- [7. 交付检查清单](#7-交付检查清单)

---

## 1. 工程规范

### 1.1 技术栈（锁定）

| 组件 | 选型 | 说明 |
|------|------|------|
| Python | 3.11+ | 异步优先 `async/await` |
| Pydantic | v2 | 所有数据模型，严格类型校验 |
| LangGraph | >= 0.2 | 工作流编排 |
| LangChain | >= 0.3 | LLM 接口 |
| litellm | latest | 多模型统一接口 |
| SQLite | 内置 | Phase 1 唯一事实源 |
| Click | latest | CLI 框架 |
| structlog | latest | 结构化日志 |
| pytest | + pytest-asyncio | 测试框架 |

### 1.2 项目结构

```
novelforge/
├── pyproject.toml              # 项目配置
├── .env.example                # 环境变量模板
├── README.md                   # 项目说明
├── CLAUDE.md                   # 不可违背规则（约束清单）
├── docs/
│   ├── INDEX.md                # 文档索引
│   ├── STATUS.md               # 项目状态
│   ├── 00-product-vision.md    # 产品愿景
│   ├── 01-phase1-scope.md      # Phase 1 范围
│   ├── 02-data-models.md       # 数据模型
│   ├── 03-sqlite-schema.md     # 数据库 schema
│   ├── 04-agent-contracts.md   # Agent 输入输出契约
│   ├── 05-context-package.md   # 上下文包规范
│   ├── 06-review-and-revision.md  # 审查与修订
│   ├── 07-cli-commands.md      # CLI 命令
│   ├── 08-eval-plan.md         # 评测计划
│   └── decisions/              # 架构决策记录
│       └── ADR-001-sqlite-only.md
├── tasks/                      # 任务文件
│   ├── 001-init-project.md
│   ├── 002-data-models.md
│   ├── 003-sqlite-schema.md
│   ├── 004-repository-layer.md
│   ├── 005-create-project-cli.md
│   ├── 006-context-package.md
│   ├── 007-writer-agent.md
│   ├── 008-reviewer-agent.md
│   ├── 009-revision-handler.md
│   └── 010-langgraph-graph.md
├── src/
│   └── novelforge/
│       ├── __init__.py
│       ├── config.py           # 配置管理（Pydantic Settings）
│       ├── cli/
│       │   └── main.py         # CLI 入口
│       ├── db/
│       │   ├── schema.sql      # SQLite schema
│       │   ├── repository.py   # 数据访问层
│       │   └── connection.py   # 数据库连接
│       ├── models/
│       │   ├── __init__.py
│       │   ├── project.py      # ProjectSetting
│       │   ├── character.py    # Character, CharacterState
│       │   ├── chapter.py      # ChapterGoal, ChapterVersion, ChapterHead
│       │   ├── context.py      # ContextPackage
│       │   ├── review.py       # ReviewIssue, ReviewReport
│       │   └── revision.py     # Patch, RevisionOutput
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── planner.py      # Planner Agent
│       │   ├── writer.py       # Writer Agent
│       │   ├── reviewer.py     # Reviewer Agent
│       │   ├── context_manager.py  # ContextManager Agent
│       │   ├── revision_handler.py # RevisionHandler 节点
│       │   └── human_confirm.py    # HumanConfirm 节点
│       ├── workflows/
│       │   └── phase1_graph.py # LangGraph 定义
│       └── utils/
│           └── token_counter.py
├── prompts/                    # Prompt 文件
│   ├── writer.md
│   ├── reviewer.md
│   └── planner.md
├── tests/                      # 测试
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_repository.py
│   ├── test_context_package.py
│   ├── test_writer.py
│   ├── test_reviewer.py
│   ├── test_revision_handler.py
│   └── test_graph.py
└── evals/                      # 评测
    └── runner.py
```

### 1.3 编码规范

```
1. 所有函数必须带类型标注（Python 3.11+ 语法）
2. 所有 Pydantic 模型必须定义完整字段
3. 数据访问集中在 repository.py，Agent 不直接拼 SQL
4. Prompt 放在 prompts/ 目录，不在代码里写长字符串
5. 不写无用抽象，不提前做插件化
6. 不提前做多租户、复杂权限系统
7. 单文件不超过 400 行，超过拆模块
8. 错误处理用自定义异常，不用裸 except
9. 异步优先：所有 IO 操作 async/await
10. 日志用 structlog，不用 print
```

### 1.4 数据事实源规则（铁律）

**SQLite 是 Phase 1 唯一长期事实源。**

LangGraph checkpoint 只允许保存：

```python
# 这些是 state 里唯一允许存的业务相关字段
project_id: str
chapter_number: int
current_version_id: str | None      # 指向 chapter_versions
review_report_id: str | None        # 指向 review_reports
revision_round: int                 # 0, 1, 2
status: str                         # 状态机
```

**禁止**在 LangGraph state 中保存：
- 完整章节正文
- 完整上下文包
- 完整审查报告
- 完整角色档案

每个节点通过 ID 从 SQLite 加载业务对象。

### 1.5 版本管理规则

每次生成或修订都创建新的 `chapter_versions` 记录。**禁止覆盖。**

版本类型：

| 类型 | 说明 | 谁创建 |
|------|------|--------|
| `draft` | AI 初稿 | Writer |
| `revision` | AI 修订版 | RevisionHandler |
| `accepted` | 人工确认版 | HumanConfirm（用户 accept） |
| `edited` | 人工编辑版 | HumanConfirm（用户 edit） |

只有 `accepted` 或 `edited` 可以成为章节正式版本。

`chapter_heads` 表负责指向当前版本和 accepted 版本。

### 1.6 审查与修订规则

- Reviewer 输出必须是 `ReviewReport`，每个 critical/major issue 必须有 `evidence_quote`
- 没有证据的 issue 不能进入自动修订
- 修订由 **RevisionHandler** 完成，不由 Writer 完成
- 只处理 `fix_type = patch` 的 issue
- 最多自动修订 **2 轮**
- 修订后必须重新审查
- 修订引入新 critical/major → 停止自动修订，进入人工确认

---

## 2. 项目管理框架

### 2.1 开发顺序（严格）

```
001. Pydantic models
002. SQLite schema
003. Repository 层
004. CLI 创建项目
005. ContextPackage 组装
006. Writer 生成 draft
007. Reviewer 输出 ReviewReport
008. RevisionHandler patch 修订
009. Human accept + 版本保存
010. LangGraph 编排
```

**规则**：不要在单独模块没跑通前提前接入 LangGraph。

### 2.2 任务粒度标准

| 好的粒度 | 不好的粒度 |
|----------|------------|
| "实现 Pydantic models" | "实现 Phase 1" |
| "实现 SQLite schema" | "搭好整个 multi-agent 系统" |
| "实现 repository 的 CRUD" | "把设计文档全部落地" |
| "实现 create-project CLI" | "实现小说写作工具" |
| "实现 Writer prompt 和 mock adapter" | "完成 vibe coding" |

### 2.3 交付标准

每次开发完成后，必须说明：

1. **做了什么** —— 一句话描述
2. **改了哪些主要文件** —— 文件清单
3. **如何运行** —— 具体命令
4. **如何验证** —— 测试命令 + 期望结果
5. **还没做什么** —— 明确的边界

如果某一步发现设计不合理，先指出问题，再提出最小修改方案，不要直接扩大范围。

### 2.4 测试要求

每个核心模块至少有一个最小测试。

优先测试：
- 创建项目成功
- 保存章节版本成功
- 版本链可追踪
- ReviewReport 可解析
- patch 应用后生成新版本
- accepted 版本更新 chapter head
- ContextPackage 可重建

**规则**：如果修改了 schema，必须补测试。

---

## 3. 流程标准化

### 3.1 每轮工作流（标准节奏）

```
1. 更新 docs/STATUS.md（当前状态）
2. 写/读 tasks/00x-xxx.md（任务规格）
3. Prompt 里只引用 CLAUDE.md + docs/INDEX.md + 当前 task
4. Agent 执行 → 完成后运行测试
5. 更新 docs/STATUS.md（记录结果）
6. 下一个任务继续
```

### 3.2 "先读后做" 启动协议

每次启动新任务时，使用以下 prompt：

```
请先阅读：
1. CLAUDE.md（约束清单）
2. docs/INDEX.md（文档索引）
3. 当前任务文件（tasks/00x-xxx.md）

然后用 5-8 行总结你理解的任务边界。
确认边界后再开始修改代码。
不要读取完整架构文档，除非当前任务明确需要。
```

### 3.3 上下文包 Prompt 格式（标准模板）

每次给 coding agent 的 prompt 固定成这个结构：

```markdown
你现在只做一个小任务。

## Project Context
当前项目：NovelForge Phase 1 单章闭环 MVP。
遵守 `CLAUDE.md`。

## Read
- docs/INDEX.md
- docs/02-data-models.md
- tasks/002-data-models.md

## Task
实现 tasks/002-data-models.md 中规定的模型。

## Constraints
- 不实现任务外内容
- 不引入 Web/Postgres/Qdrant/Redis
- 不改未相关文件

## Done When
- 所有 model 可通过 Pydantic v2 validate
- 有最小单元测试
- 简要说明改动和验证方式
```

### 3.4 当前不做清单（明确排除）

除非用户明确要求，不要实现：

- React Web UI
- TUI（终端界面）
- Redis
- Celery / ARQ
- Qdrant
- PostgreSQL
- 多模型路由
- 模板市场
- 拆书分析
- 完整 Studio
- 10 个 Agent 架构
- 复杂 Supervisor 层级调度

### 3.5 ADR（架构决策记录）

重要决策必须写成 ADR，不藏在长文档里。

存放位置：`docs/decisions/ADR-NNN-title.md`

每个 ADR 包含：
- **Decision** —— 做了什么决定
- **Reason** —— 为什么做这个决定
- **Consequence** —— 后果和影响

---

## 4. Phase 1 任务拆解（10 个 Task）

### Task 001: 项目初始化

```markdown
# Task 001: 初始化项目结构

## Goal
创建项目骨架，配置 pyproject.toml、.env.example、目录结构。

## In Scope
- pyproject.toml（依赖：pydantic, langgraph, langchain, litellm, click, structlog, pytest-asyncio）
- .env.example（LLM_API_KEY, LLM_BASE_URL, LLM_MODEL）
- 完整目录结构（src/novelforge/ 下所有子目录和 __init__.py）
- CLAUDE.md（不可违背规则清单）
- docs/INDEX.md（文档索引框架）
- docs/STATUS.md（初始状态）

## Out of Scope
- 任何业务代码
- 数据库 schema
- CLI 命令

## Acceptance Criteria
- [ ] `pip install -e ".[dev]"` 成功
- [ ] 目录结构与规范一致
- [ ] `python -c "import novelforge"` 成功
- [ ] CLAUDE.md 包含所有约束规则
```

### Task 002: 数据模型

```markdown
# Task 002: 实现 Phase 1 数据模型

## Goal
实现所有 Phase 1 Pydantic models。

## Read
- docs/INDEX.md
- docs/02-data-models.md

## In Scope
- models/project.py: ProjectSetting
- models/character.py: Character, CharacterState
- models/chapter.py: ChapterGoal, ChapterVersion, ChapterHead
- models/context.py: ContextPackage, HardConstraint, SoftReference, CharacterStateSnapshot, ForeshadowingItem
- models/review.py: ReviewIssue, ReviewReport
- models/revision.py: Patch, RevisionOutput

## Out of Scope
- SQLite schema
- CLI
- LLM prompts
- LangGraph

## Acceptance Criteria
- [ ] 所有 model 有类型标注
- [ ] Pydantic v2 可正常 validate
- [ ] 有最小单元测试（test_models.py）
- [ ] ChapterVersion 版本链可通过 parent_version_id 追溯
```

### Task 003: SQLite Schema

```markdown
# Task 003: 实现 SQLite 数据库

## Goal
创建 SQLite schema 和数据库连接层。

## Read
- docs/INDEX.md
- docs/03-sqlite-schema.md

## In Scope
- db/schema.sql: 所有 CREATE TABLE 语句
- db/connection.py: 数据库连接管理
- db/migrations.py: schema 初始化

## Out of Scope
- Repository 层（下一 task）
- 业务逻辑

## Acceptance Criteria
- [ ] `sqlite3 novelforge.db < schema.sql` 成功
- [ ] 所有表创建无误
- [ ] 外键约束生效
- [ ] 连接管理可正常开关
```

### Task 004: Repository 层

```markdown
# Task 004: 实现 Repository 数据访问层

## Goal
实现所有 CRUD 操作。

## Read
- docs/INDEX.md
- docs/03-sqlite-schema.md

## In Scope
- db/repository.py:
  - ProjectRepository: create, get
  - CharacterRepository: create, get, list, update_state
  - ChapterVersionRepository: create, get, list_chain, get_head, update_head
  - ReviewReportRepository: create, get
  - ContextPackageRepository: save_snapshot, get_snapshot

## Out of Scope
- Agent 逻辑
- CLI

## Acceptance Criteria
- [ ] 所有 CRUD 有基本测试
- [ ] 版本链可通过 parent_version_id 追溯
- [ ] chapter_heads 可更新
- [ ] Agent 不直接拼 SQL，通过 repository 访问
```

### Task 005: CLI 创建项目

```markdown
# Task 005: 实现 create-project CLI

## Goal
实现新手创建向导 CLI。

## Read
- docs/INDEX.md
- docs/07-cli-commands.md

## In Scope
- cli/main.py: novelforge create-project 命令
- 7 步交互式向导（题材、灵感、主角、读者预期、禁忌、字数、书名）
- AI 实时建议（调用 LLM）
- 保存到 SQLite

## Out of Scope
- 其他 CLI 命令
- Writer/Reviewer

## Acceptance Criteria
- [ ] `novelforge create-project` 可交互运行
- [ ] 7 步向导完整
- [ ] 项目保存到 SQLite
- [ ] 可用 `novelforge list-projects` 查看
```

### Task 006: ContextPackage 组装

```markdown
# Task 006: 实现上下文包组装

## Goal
实现 ContextManager Agent 的上下文包组装逻辑。

## Read
- docs/INDEX.md
- docs/05-context-package.md

## In Scope
- agents/context_manager.py: assemble_context_package()
- 从 SQLite 加载：项目设定、角色状态、最近章节摘要、伏笔
- 分区组装：hard_constraints, soft_references, recent_plot, character_states, foreshadowing, chapter_goal
- token 估算和裁剪（默认 32K，上限 64K）
- context snapshot 保存到 generation_metadata

## Out of Scope
- Writer
- Reviewer

## Acceptance Criteria
- [ ] 上下文包正确分区
- [ ] 不出场角色不加载
- [ ] token 不超过 32K（默认）
- [ ] snapshot 可保存和重建
- [ ] 有测试验证组装逻辑
```

### Task 007: Writer Agent

```markdown
# Task 007: 实现 Writer Agent

## Goal
实现 Writer Agent 的初稿生成。

## Read
- docs/INDEX.md
- docs/04-agent-contracts.md
- prompts/writer.md

## In Scope
- agents/writer.py: write_draft()
- 按场景生成（不是一次性整章）
- 对话单独成段
- 章末有钩子
- 新设定标记 [[新设定:描述]]
- 输出 ChapterVersion (version_type="draft")

## Out of Scope
- 修订逻辑（RevisionHandler 负责）
- Reviewer

## Acceptance Criteria
- [ ] 可生成一章中文小说（至少 2000 字）
- [ ] 遵守上下文包硬约束
- [ ] 不引入未提及设定（或正确标记）
- [ ] 输出可解析为 ChapterVersion
- [ ] 有测试（可用 mock LLM）
```

### Task 008: Reviewer Agent

```markdown
# Task 008: 实现 Reviewer Agent

## Goal
实现结构化审查 Agent。

## Read
- docs/INDEX.md
- docs/06-review-and-revision.md
- prompts/reviewer.md

## In Scope
- agents/reviewer.py: review_chapter()
- 4 类检查：设定一致性、角色行为、时间线、质量
- 输出 ReviewReport（结构化 issue 列表）
- 每个 critical/major 必须有 evidence_quote
- 严重度分级：critical/major/minor/info

## Out of Scope
- 自动修订
- HumanConfirm

## Acceptance Criteria
- [ ] 可输出结构化 ReviewReport
- [ ] 每个 issue 有 evidence_quote
- [ ] critical/major 可被测试用例触发
- [ ] 无 evidence 的 issue 被过滤
- [ ] 有测试验证审查逻辑
```

### Task 009: RevisionHandler + HumanConfirm

```markdown
# Task 009: 实现修订和人工确认

## Goal
实现 RevisionHandler 节点和 HumanConfirm 节点。

## Read
- docs/INDEX.md
- docs/06-review-and-revision.md

## In Scope
- agents/revision_handler.py:
  - 筛选 patchable issues (critical/major + fix_type=patch)
  - 从后往前应用 patch
  - 创建 revision 版本
- agents/human_confirm.py:
  - CLI 交互：accept/edit/reject/back
  - 创建 accepted/edited 版本
  - 更新 chapter_heads

## Out of Scope
- LangGraph 编排（下一 task）

## Acceptance Criteria
- [ ] patch 只修改有 issue 的部分
- [ ] 保留未修改内容
- [ ] 最多 2 轮自动修订
- [ ] accept 创建 accepted 版本
- [ ] edit 创建 edited 版本
- [ ] chapter_heads 正确更新
```

### Task 010: LangGraph 编排

```markdown
# Task 010: LangGraph 工作流编排

## Goal
将所有节点串联成完整的 Phase 1 工作流。

## Read
- docs/INDEX.md

## In Scope
- workflows/phase1_graph.py:
  - 定义 Phase1State（只存 ID）
  - 6 个节点：planner, context_manager, writer, reviewer, revision_handler, human_confirm
  - 条件路由：pass→human_confirm, revise→revision_handler, human→human_confirm
  - revision_handler → reviewer（循环）
  - SQLite checkpoint

## Out of Scope
- Phase 2/3

## Acceptance Criteria
- [ ] 完整流程可运行：plan → assemble → write → review → confirm
- [ ] 有 issue 时进入 revision → review 循环
- [ ] 最多 2 轮修订
- [ ] 人工确认后保存 accepted 版本
- [ ] checkpoint 可恢复
- [ ] 有端到端测试
```

---

## 5. 所有 Prompt 汇总

### 5.1 Master System Prompt

```markdown
# NovelForge Development Guide

你是 NovelForge 项目的协作开发代理。NovelForge 是一个面向中文长篇小说写作的
multi-agent 工具，核心目标不是一次性生成文本，而是建立
"设定 → 上下文包 → 章节生成 → 结构化审查 → issue-driven 修订 → 人工确认 → 版本保存"
的可复现闭环。

## 当前阶段

当前只实现 Phase 1：单章闭环 MVP。

不要提前实现 Phase 2/3 的复杂能力，除非用户明确要求。

Phase 1 的目标是验证：
- 能否创建项目设定和角色卡
- 能否组装小说专用 Context Package
- 能否生成一章中文小说草稿
- 能否输出结构化 ReviewReport
- 能否基于 ReviewIssue 做局部 patch 修订
- 能否保存版本链并人工确认 accepted 版本

## 最高优先级原则

1. 每次只做一个可运行切片。
2. 先 CLI，后 Web。
3. 先 SQLite，后 PostgreSQL/Qdrant。
4. 先单章闭环，后连续章节。
5. 业务数据以 SQLite 为唯一事实源。
6. LangGraph checkpoint 只保存执行位置和 ID，不保存完整业务对象。
7. 所有 LLM 输出必须映射到 Pydantic schema。
8. 不允许让 Agent 输出自由格式文本后再靠字符串猜测解析。
9. 自动修订只允许 issue-driven patch，不允许默认整章重写。
10. 自动修订最多 2 轮，之后进入人工确认。

## 当前不做

除非用户明确要求，不要实现以下内容：
- React Web UI
- TUI
- Redis
- Celery / ARQ
- Qdrant
- PostgreSQL
- 多模型路由
- 模板市场
- 拆书分析
- 完整 Studio
- 10 个 Agent 架构
- 复杂 Supervisor 层级调度

## 推荐项目结构

novelforge/
  agents/
    planner.py
    writer.py
    reviewer.py
    context_manager.py
    revision_handler.py
  cli/
    main.py
  db/
    schema.sql
    repository.py
    migrations.py
  models/
    project.py
    character.py
    chapter.py
    context.py
    review.py
    revision.py
  workflows/
    phase1_graph.py
  prompts/
    writer.md
    reviewer.md
    revision.md
  evals/
    runner.py

## 核心数据模型

优先实现这些 Pydantic models：
- ProjectSetting
- Character
- CharacterState
- ChapterGoal
- ContextPackage
- ChapterVersion
- ReviewIssue
- ReviewReport
- Patch
- RevisionOutput

所有 Agent 输入输出必须使用这些模型。

## 数据事实源规则

SQLite 是 Phase 1 的唯一长期事实源。

必须保存：
- 项目设定
- 角色卡
- 角色状态
- 章节版本
- 审查报告
- 章节 HEAD
- 章节摘要
- 伏笔记录
- 生成元信息

LangGraph state 只允许保存：
- project_id
- chapter_number
- current_version_id
- review_report_id
- revision_round
- status

不要在 LangGraph state 中保存完整章节正文、完整上下文包或完整审查报告。

## 版本管理规则

每次生成或修订都创建新的 chapter_versions 记录。

版本类型：
- draft: AI 初稿
- revision: AI 修订版本
- accepted: 人工确认版本
- edited: 人工编辑版本

禁止覆盖旧版本。

只有 accepted 或 edited 可以成为章节正式版本。

chapter_heads 负责指向当前版本和 accepted 版本。

## Context Package 规则

Context Package 是小说写作上下文包，不是普通 RAG 检索结果。

必须分区：
- hard_constraints: 必须遵守的设定、角色状态、禁忌、本章义务
- soft_references: 可参考的世界观、风格、背景
- recent_plot: 前几章摘要、上一章结尾片段、开放剧情线
- character_states: 当前出场角色状态
- foreshadowing: 未回收、应回收、过期伏笔
- chapter_goal: 本章目标

默认 token budget 不超过 32K，除非用户明确调整。

每次生成时，需要把 context snapshot 写入 generation_metadata，用于复现。

## Writer 规则

Writer 只负责生成正文，不负责审查，不负责修改设定。

Writer 输入：
- ContextPackage
- ChapterGoal
- 可选风格规则

Writer 输出：
- 标题
- 正文
- 场景列表
- 字数
- 生成元信息

Writer 必须遵守：
- 不随意引入硬约束之外的新设定
- 如果确实需要新设定，用明确标记返回
- 章末需要有钩子
- 保持中文网文可读性
- 不输出审查意见

## Reviewer 规则

Reviewer 只负责审查，不直接修改正文。

Reviewer 输出必须是 ReviewReport。

每个 critical / major issue 必须包含：
- evidence_quote
- evidence_location
- issue_description
- expected
- actual
- suggested_fix
- fix_type
- confidence

没有证据片段的 issue 不能进入自动修订。

严重度定义：
- critical: 事实性错误或核心设定冲突，阻塞 accepted
- major: 明显影响阅读体验，建议修复
- minor: 小瑕疵，只记录
- info: 建议项，只记录

## Revision 规则

修订由 RevisionHandler 完成，不由 Writer 直接完成。

只处理 fix_type = patch 的 issue。

每个 patch 必须包含：
- issue_id
- original_text
- revised_text
- location

应用 patch 后必须创建新的 revision 版本。

修订后必须重新审查。

最多自动修订 2 轮。

如果修订引入新的 critical/major issue，停止自动修订，进入人工确认。

## CLI 优先命令

优先实现这些命令：
novelforge create-project
novelforge write-chapter --project <id> --chapter <n>
novelforge review --version <version_id>
novelforge revise --version <version_id>
novelforge accept --version <version_id>
novelforge show-version --version <version_id>
novelforge list-versions --project <id> --chapter <n>

## 开发顺序

严格按以下顺序推进：
1. Pydantic models
2. SQLite schema
3. Repository 层
4. CLI 创建项目
5. ContextPackage 组装
6. Writer 生成 draft
7. Reviewer 输出 ReviewReport
8. RevisionHandler patch 修订
9. Human accept
10. LangGraph 编排

不要在单独模块没跑通前提前接入 LangGraph。

## 测试要求

每个核心模块至少有一个最小测试。

优先测试：
- 创建项目成功
- 保存章节版本成功
- 版本链可追踪
- ReviewReport 可解析
- patch 应用后生成新版本
- accepted 版本更新 chapter head
- ContextPackage 可重建

如果修改了 schema，必须补测试。

## 编码风格

- 使用 Python 3.11+
- 使用 Pydantic v2
- 使用类型标注
- 数据访问集中在 repository 层
- Agent 不直接拼 SQL
- Prompt 放在 prompts/
- 不写无用抽象
- 不提前做插件化
- 不提前做多租户
- 不提前做复杂权限系统

## 交付标准

每次开发完成后，必须说明：
- 做了什么
- 改了哪些主要文件
- 如何运行
- 如何验证
- 还没做什么

如果某一步发现设计不合理，先指出问题，再提出最小修改方案，不要直接扩大范围。
```

### 5.2 启动 Prompt

```markdown
请先阅读：
1. CLAUDE.md（约束清单）
2. docs/INDEX.md（文档索引）
3. 当前任务文件（tasks/00x-xxx.md）

然后用 5-8 行总结你理解的任务边界。
确认边界后再开始修改代码。
不要读取完整架构文档，除非当前任务明确需要。
```

### 5.3 任务执行 Prompt（标准模板）

```markdown
你现在只做一个小任务。

## Project Context
当前项目：NovelForge Phase 1 单章闭环 MVP。
遵守 `CLAUDE.md`。

## Read
- docs/INDEX.md
- docs/02-data-models.md
- tasks/{TASK_FILE}.md

## Task
实现 tasks/{TASK_FILE}.md 中规定的内容。

## Constraints
- 不实现任务外内容
- 不引入 Web/Postgres/Qdrant/Redis
- 不改未相关文件

## Done When
- [ ] 测试通过
- [ ] 简要说明改动和验证方式
```

### 5.4 Writer Prompt

```markdown
你是中文网络小说作家。请根据以下信息创作第 {chapter_number} 章。

## 写作约束（必须遵守）
{hard_constraints}

## 本章目标
{chapter_goal}

## 出场角色状态
{character_states}

## 最近剧情
{recent_plot}

## 伏笔线索
{foreshadowing}

## 风格参考
{style_rules}

## 写作要求
1. 按场景生成，场景间用 ### 分隔
2. 对话单独成段，用引号包裹
3. 段落 3-5 行，战斗场景用短句增加节奏感
4. 不引入上面未提及的新设定（需要的话标记 [[新设定:描述]]）
5. 章末必须有钩子
6. 字数目标：{word_count_target} 字

## 输出格式
输出 JSON：
{
  "title": "章节标题",
  "content": "完整正文",
  "scenes": ["场景1内容", "场景2内容"],
  "word_count": 3000,
  "new_settings": ["新设定1", "新设定2"],
  "metadata": {"model": "xxx", "temperature": 0.7}
}
```

### 5.5 Reviewer Prompt

```markdown
你是资深中文网络文学编辑。请对以下章节进行严格审查。

## 审查标准

你必须输出结构化的 issue 列表。每个 issue 必须包含：
1. category：问题类别
2. severity：严重度（critical/major/minor/info）
3. evidence_quote：原文问题片段（必须引用原文！）
4. issue_description：具体问题
5. expected：应该是什么
6. actual：实际是什么
7. suggested_fix：修复建议
8. fix_type：修复类型（patch/rewrite_scene/confirm/register_setting）

## 严重度定义

- critical：事实性错误，读者会出戏
  - 已死角色再次出现
  - 违反已揭示的核心设定
  - 时间线明显矛盾
- major：质量或一致性问题，影响阅读体验
  - 角色行为与其性格明显冲突
  - 节奏严重失衡
  - 对话没有区分度
- minor：小瑕疵
  - 用词重复
  - 描写可以更生动
- info：建议
  - 可以增加伏笔
  - 这里可以加强钩子

## 铁律
- 没有 evidence_quote 的 issue 不要输出
- minor 和 info 不阻塞入库
- critical 必须修复

## 章节内容
{chapter_content}

## 上下文
### 硬约束
{hard_constraints}
### 角色状态
{character_states}
### 章节目标
{chapter_goal}

## 输出格式（JSON）
{
  "issues": [
    {
      "category": "world_consistency",
      "severity": "critical",
      "evidence_quote": "原文片段",
      "issue_description": "...",
      "expected": "...",
      "actual": "...",
      "suggested_fix": "...",
      "fix_type": "patch",
      "confidence": 0.95
    }
  ],
  "overall_score": 7.5,
  "summary": "总体评价"
}
```

### 5.6 Planner Prompt（章节目标 + 摘要）

```markdown
## 制定章节目标

你是小说规划师。根据以下信息，制定第 {chapter_number} 章的写作目标。

项目设定：
题材：{genre}
主角：{protagonist_name}（{protagonist_background}）
核心爽点：{core_hook}
基调：{tone}

最近剧情：
{recent_summaries}

输出要求：
- 本章必须发生的 1-3 个关键事件（具体可执行）
- 情感走向
- 章末钩子（有信息量，不能是"接下来会发生什么"）
- 字数目标（2000-5000）

输出 JSON：
{
  "target_events": ["事件1", "事件2"],
  "emotional_arc": "压抑→爆发",
  "hooks": ["悬念1"],
  "obligations": ["必须完成的事项"],
  "word_count_target": 3000
}

---

## 生成章节摘要

请为以下章节生成结构化摘要。

章节内容：
{chapter_content}

输出 JSON：
{
  "plot_summary": "200-500字情节梗概",
  "key_events": ["事件1", "事件2"],
  "characters_appeared": ["角色名"],
  "character_changes": {"角色名": "变化描述"},
  "settings_referenced": ["场景名"],
  "foreshadowing_planted": ["新伏笔"],
  "foreshadowing_resolved": ["回收的伏笔"],
  "emotional_tone": "情感基调",
  "pacing_score": 7.5
}
```

### 5.7 RevisionHandler Prompt

```markdown
你是修订助手。请修改以下章节内容，修复指定的问题。
只修改有问题的部分，其他内容保持不变。

## 原文
{original_content}

## 需要修复的问题
{issues}

## 规则
1. 每个问题只修改对应的那几句话
2. 不要改动没有问题的部分
3. 修改后全文保持流畅
4. 按位置从后往前应用 patch

## 输出格式（JSON）
{
  "patched_content": "完整的修改后全文",
  "patches": [
    {
      "issue_id": "issue-1",
      "original_text": "原文",
      "revised_text": "修改后",
      "location": "第3段第2句"
    }
  ]
}
```

### 5.8 HumanConfirm 交互设计

```markdown
HumanConfirm 是 CLI 交互节点，不是 LLM prompt。

交互流程：
1. 打印审查摘要
   📋 审查报告（N 个问题）
   [CRITICAL] world_consistency: ...
   [MAJOR] character_behavior: ...

2. 展示正文预览（前 1000 字 + ... + 后 500 字）

3. 提示选择：
   [a]ccept — 接受当前版本
   [e]dit   — 用编辑器修改
   [r]eject — 退回重写
   [b]ack   — 回退到历史版本

4. 处理：
   - accept → 创建 accepted 版本 → 更新 chapter_heads
   - edit   → 打开 $EDITOR → 创建 edited 版本 → 更新 chapter_heads
   - reject → 状态重置为 planning → revision_round = 0
   - back   → 列出历史版本 → 用户选择 → 回退

5. 最终状态：status = "summarizing"（触发 Planner 生成摘要）
```

---

## 6. 项目管理工具模板

### 6.1 STATUS.md

```markdown
# Project Status

## Done
- [x] 001: 项目初始化（pyproject.toml, 目录结构, CLAUDE.md）
- [x] 002: Pydantic 数据模型
- [ ] 003: SQLite schema
- [ ] 004: Repository 层
- [ ] 005: CLI 创建项目
- [ ] 006: ContextPackage 组装
- [ ] 007: Writer Agent
- [ ] 008: Reviewer Agent
- [ ] 009: RevisionHandler + HumanConfirm
- [ ] 010: LangGraph 编排

## Current
- 任务：003
- 状态：进行中
-  blocker：无

## Next
- 004: Repository 层

## Deferred
- Web UI
- Qdrant
- PostgreSQL
- Redis
- Phase 2/3

## Notes
- 2026-05-16: 002 完成，所有 model 测试通过
```

### 6.2 INDEX.md

```markdown
# NovelForge Docs Index

当前阶段：Phase 1 单章闭环 MVP。

如果任务涉及数据模型，读取：
- docs/02-data-models.md
- docs/03-sqlite-schema.md

如果任务涉及 Agent 输入输出，读取：
- docs/04-agent-contracts.md
- docs/05-context-package.md

如果任务涉及审查或修订，读取：
- docs/06-review-and-revision.md

如果任务涉及 CLI，读取：
- docs/07-cli-commands.md

不要默认读取完整架构文档。
```

### 6.3 ADR 模板

```markdown
# ADR-NNN: 标题

## 状态
- proposed / accepted / deprecated

## 决策
一句话描述做了什么决定。

## 原因
为什么做这个决定。列出考虑的替代方案和排除理由。

## 后果
这个决定带来什么影响（正面和负面）。

## 相关
- 关联的 task 编号
- 关联的文档
```

---

## 7. 交付检查清单

### Phase 1 交付前检查

- [ ] 10 个 Task 全部完成
- [ ] 每个 Task 有对应的测试
- [ ] 完整单章闭环可运行：create-project → write → review → accept
- [ ] 3 个题材各 1-3 章验证通过
- [ ] 结构化审查通过率 > 80%
- [ ] 人工返工率 < 30%
- [ ] Reviewer-人工金标一致率 > 70%
- [ ] 修订不引入新问题
- [ ] 版本链可追踪（draft → revision → accepted）
- [ ] checkpoint 可恢复
- [ ] docs/STATUS.md 更新为全部完成

### 代码质量检查

- [ ] 所有函数有类型标注
- [ ] 所有 Pydantic model 可 validate
- [ ] Agent 不直接拼 SQL
- [ ] LangGraph state 只存 ID
- [ ] Prompt 放在 prompts/ 目录
- [ ] 没有无用抽象
- [ ] 测试覆盖率 > 60%

---

> **文档说明**
>
> 本文档是 Phase 1 开发的**唯一入口**。开发时应遵循：
> 1. 先读 Master System Prompt（5.1）
> 2. 用启动 Prompt（5.2）确认边界
> 3. 用任务执行 Prompt（5.3）推进每个 Task
> 4. 更新 STATUS.md 记录进度
> 5. 重要决策写 ADR
>
> 不要直接引用 01-architecture-design.md 或 02-vibe-coding-prompts.md，
> 那些是设计背景资料。本文档才是开发的执行依据。
