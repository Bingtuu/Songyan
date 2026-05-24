# Vibe Coding 准备 V1
## system prompt框架

```
# NovelForge Development Guide

你是 NovelForge 项目的协作开发代理。NovelForge 是一个面向中文长篇小说写作的 multi-agent 工具，核心目标不是一次性生成文本，而是建立“设定 → 上下文包 → 章节生成 → 结构化审查 → issue-driven 修订 → 人工确认 → 版本保存”的可复现闭环。

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
```

```
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
这些属于 Phase 2/3。
```

```
-- **推荐项目结构**
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

```

### 核心数据模型
优先实现这些 Pydantic models：
* ProjectSetting
* Character
* CharacterState
* ChapterGoal
* ContextPackage
* ChapterVersion
* ReviewIssue
* ReviewReport
* Patch
* RevisionOutput

所有 Agent 输入输出必须使用这些模型。

### 数据事实源规则
SQLite 是 Phase 1 的唯一长期事实源。

必须保存：

* 项目设定
* 角色卡
* 角色状态
* 章节版本
* 审查报告
* 章节 HEAD
* 章节摘要
* 伏笔记录
* 生成元信息

LangGraph state 只允许保存：

* project_id
* chapter_number
* current_version_id
* review_report_id
* revision_round
* status
  
不要在 LangGraph state 中保存完整章节正文、完整上下文包或完整审查报告。

### 版本管理规则
每次生成或修订都创建新的 `chapter_versions` 记录。

版本类型：

* `draft`: AI 初稿
* `revision`: AI 修订版本
* `accepted`: 人工确认版本
* `edited`: 人工编辑版本
* 
禁止覆盖旧版本。

只有 `accepted` 或 `edited` 可以成为章节正式版本。

chapter_heads 负责指向当前版本和 accepted 版本。

### Context Package 规则
Context Package 是小说写作上下文包，不是普通 RAG 检索结果。

必须分区：

* hard_constraints: 必须遵守的设定、角色状态、禁忌、本章义务
* soft_references: 可参考的世界观、风格、背景
* recent_plot: 前几章摘要、上一章结尾片段、开放剧情线
* character_states: 当前出场角色状态
* foreshadowing: 未回收、应回收、过期伏笔
* chapter_goal: 本章目标
  
默认 token budget 不超过 32K，除非用户明确调整。

每次生成时，需要把 context snapshot 写入 generation_metadata，用于复现。

### Writer 规则
Writer 只负责生成正文，不负责审查，不负责修改设定。

Writer 输入：

* ContextPackage
* ChapterGoal
* 可选风格规则
  
Writer 输出：

* 标题
* 正文
* 场景列表
* 字数
* 生成元信息

Writer 必须遵守：

* 不随意引入硬约束之外的新设定
* 如果确实需要新设定，用明确标记返回
* 章末需要有钩子
* 保持中文网文可读性
* 不输出审查意见

### Reviewer 规则
Reviewer 只负责审查，不直接修改正文。

Reviewer 输出必须是 ReviewReport。

每个 critical / major issue 必须包含：

* evidence_quote
* evidence_location
* issue_description
* expected
* actual
* suggested_fix
* fix_type
* confidence 

没有证据片段的 issue 不能进入自动修订。

严重度定义：

* critical: 事实性错误或核心设定冲突，阻塞 accepted
* major: 明显影响阅读体验，建议修复
* minor: 小瑕疵，只记录
* info: 建议项，只记录

Revision 规则
修订由 RevisionHandler 完成，不由 Writer 直接完成。

只处理 fix_type = patch 的 issue。

每个 patch 必须包含：

* issue_id
* original_text
* revised_text
* location

应用 patch 后必须创建新的 revision 版本。

修订后必须重新审查。

最多自动修订 2 轮。

如果修订引入新的 critical/major issue，停止自动修订，进入人工确认。

CLI 优先命令
优先实现这些命令：
```
novelforge create-project
novelforge write-chapter --project <id> --chapter <n>
novelforge review --version <version_id>
novelforge revise --version <version_id>
novelforge accept --version <version_id>
novelforge show-version --version <version_id>
novelforge list-versions --project <id> --chapter <n>
```
### 开发顺序
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

### 测试要求
每个核心模块至少有一个最小测试。

优先测试：

* 创建项目成功
* 保存章节版本成功
* 版本链可追踪
* ReviewReport 可解析
* patch 应用后生成新版本
* accepted 版本更新 chapter head
* ContextPackage 可重建

如果修改了 schema，必须补测试。

### 编码风格
* 使用 Python 3.11+
* 使用 Pydantic v2
* 使用类型标注
* 数据访问集中在 repository 层
* Agent 不直接拼 SQL
* Prompt 放在 prompts/
* 不写无用抽象
* 不提前做插件化
* 不提前做多租户
* 不提前做复杂权限系统

### 交付标准
每次开发完成后，必须说明：

* 做了什么
* 改了哪些主要文件
* 如何运行
* 如何验证
* 还没做什么

如果某一步发现设计不合理，先指出问题，再提出最小修改方案，不要直接扩大范围。

## 上下问管理
### 1. 把长文档拆成短文档
建议把 01-architecture-design.md 拆成这样：
```
docs/
  00-product-vision.md
  01-phase1-scope.md
  02-data-models.md
  03-sqlite-schema.md
  04-agent-contracts.md
  05-context-package.md
  06-review-and-revision.md
  07-cli-commands.md
  08-eval-plan.md
  decisions/
    ADR-001-phase1-sqlite.md
    ADR-002-langgraph-state-only-ids.md
```
每个文件控制在 100-250 行以内。
这样你每次只让工具读取相关文件，而不是整份大设计。

### 2. 写一个短版项目索引
创建 docs/INDEX.md，专门告诉 agent “要做什么看哪个文件”。

示例：
```
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
以后你可以在 prompt 里只写：
请先阅读 CLAUDE.md 和 docs/INDEX.md，再根据当前任务读取必要文档。

### 3. 做一份“不可违背规则”短文档
长设计里真正每次都需要的不是全部内容，而是约束规则。放到 CLAUDE.md 或 AGENTS.md 里。

重点只保留：

* 当前只做 Phase 1
* SQLite 是唯一事实源
* LangGraph state 只存 ID
* 所有 LLM 输出必须是 Pydantic schema
* Writer 不审查
* Reviewer 不改正文
* RevisionHandler 只做 patch
* 自动修订最多 2 轮
  
不提前做 Web/Qdrant/Postgres/Redis
这份文件建议不超过 200 行。

### 4. 每个任务单独写 Task Spec
不要直接说“实现数据模型”。给 agent 一个小任务文件，比如：
```
tasks/
  001-init-project.md
  002-data-models.md
  003-sqlite-schema.md
  004-repository-layer.md
  005-create-project-cli.md
```
每个任务文件包含：
```
# Task 002: Implement Phase 1 Data Models

## Goal
实现 Phase 1 需要的 Pydantic models。

## Read First
- CLAUDE.md
- docs/02-data-models.md

## In Scope
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

## Out of Scope
- SQLite schema
- CLI
- LangGraph
- LLM prompts

## Acceptance Criteria
- 所有 model 有类型标注
- Pydantic v2 可正常 validate
- 有最小单元测试
```
然后每次 prompt：

请执行 tasks/002-data-models.md。只读取任务里列出的文档。完成后运行相关测试。

### 5. 使用“上下文包 prompt”格式
每次给 coding agent 的 prompt 固定成这个结构：
```
你现在只做一个小任务。

## Project Context
当前项目：NovelForge Phase 1 单章闭环 MVP。
遵守 `CLAUDE.md`。

## Read
- docs/INDEX.md
- docs/02-data-models.md
- tasks/002-data-models.md

## Task
实现 tasks/002-data-models.md。

## Constraints
- 不实现任务外内容
- 不引入 Web/Postgres/Qdrant/Redis
- 不改未相关文件

## Done When
- 测试通过
- 简要说明改动和验证方式
```
这个比贴整份设计文档稳定得多。

### 6. 为每个模块维护“当前状态”
建一个 docs/STATUS.md：
```
# Project Status

## Done
- Project initialized
- Basic Pydantic models implemented

## Current
- Implementing SQLite schema

## Next
- Repository layer
- create-project CLI

## Deferred
- Web UI
- Qdrant
- PostgreSQL
- LangGraph

```

这样新一轮 agent 不需要重新理解所有历史。

### 7. 重要决策写 ADR，不要藏在长文档里
比如：
```
# ADR-002: LangGraph State Stores Only IDs

## Decision
LangGraph state only stores identifiers and execution status.

## Reason
SQLite is the business source of truth. Checkpoint is only for execution recovery.

## Consequence
Nodes must load full business objects from repository by ID.
```
### 8. 给 agent 明确“先读后做”
推荐启动 prompt：
```
请先阅读：
1. CLAUDE.md
2. docs/INDEX.md
3. 当前任务文件

然后用 5-8 行总结你理解的任务边界。
确认边界后再开始修改代码。
不要读取完整架构文档，除非当前任务明确需要。
```
这能减少 agent 自己脑补和乱扩展。

### 9. 控制每次任务粒度
好的任务粒度：

* “实现 Pydantic models”
* “实现 SQLite schema”
* “实现 repository 的 project/chapter version CRUD”
* “实现 create-project CLI”
* “实现 Writer prompt 和 mock LLM adapter”
* “实现 ReviewReport 解析与保存”

不好的任务粒度：

* “实现 Phase 1”
* “搭好整个 multi-agent 系统”
* “把设计文档全部落地”
* “实现小说写作工具”

### 10. 我的推荐工作流
每一轮都这样：

* 更新 docs/STATUS.md
* 写一个 tasks/00x-xxx.md
* prompt 里只引用 CLAUDE.md、docs/INDEX.md、当前 task
* agent 完成后运行测试
* 把结果写回 docs/STATUS.md
* 下一个任务继续

这样上下文不会爆，而且开发节奏会很稳。

最关键的一点：设计文档是背景资料，不是每次开发的输入。每次开发的输入应该是一个小任务文件 + 2-3 个相关规范文件。