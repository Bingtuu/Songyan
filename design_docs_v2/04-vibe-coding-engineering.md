好的工程不是一次性写对的，而是在正确的约束下一步步走出来的。
制墨的工序不能乱：取烟、和胶、捣练、成锭。每步到位，墨才能用。

# Songyan（松烟）— Vibe Coding 工程化开发手册

## V1.0 单章闭环 MVP（完整 Prompt + 规范 + 任务拆解）

> **版本**: V2.0.0
> **日期**: 2026-05-24
> **用途**: 指导 AI 编程助手（Cursor / Claude Code / Copilot）按工程规范完成 V1.0 开发
> **核心原则**: 每次只做一个小任务，先读后做，可验证再推进
> **变更**: 基于 v2 review——Planner 拆分、Reviewer 双层化、CreativeDirector/LiteraryAuditor 新增、CreativeModeProfile 引入

---

## 目录

- [1. 工程规范](#1-工程规范)
- [2. 项目管理框架](#2-项目管理框架)
- [3. 流程标准化](#3-流程标准化)
- [4. V1.0 任务拆解（16 个 Task）](#4-v10-任务拆解16-个-task)
- [5. 所有 Prompt 汇总](#5-所有-prompt-汇总)
- [6. 项目管理工具模板](#6-项目管理工具模板)
- [7. 交付检查清单](#7-交付检查清单)

---

## 1. 工程规范

### 1.1 技术栈（锁定）

| 组件 | 选型 | 说明 |
|------|------|------|
| Python | 3.11+ | 异步优先 `async/await` |
| Pydantic | v2 | 所有数据模型，严格类型校验 |
| LangGraph | >=0.2 | 工作流编排 |
| LangChain | >=0.3 | LLM 接口 |
| litellm | latest | 多模型统一接口 |
| SQLite | 内置 | V1.0 唯一事实源 |
| Click | latest | CLI 框架 |
| structlog | latest | 结构化日志 |
| tiktoken | latest | Token 计数 |
| pytest | + pytest-asyncio | 测试框架 |

### 1.2 项目结构

```
songyan/
├── pyproject.toml                          # 项目配置
├── .env.example                            # 环境变量模板
├── README.md                               # 项目说明
├── CLAUDE.md                               # 不可违背规则（约束清单）
├── creative_modes/                         # ⭐ 创作模式配置
│   ├── webnovel.json
│   ├── literary.json
│   └── hybrid.json
├── genres/                                 # 题材配置文件
│   ├── xuanhuan.json
│   ├── urban.json
│   └── scifi.json
├── docs/
│   ├── INDEX.md                            # 文档索引
│   ├── STATUS.md                           # 项目状态
│   ├── 00-product-vision.md                # 产品愿景
│   ├── 01-phase1-scope.md                  # V1.0 范围
│   ├── 02-data-models.md                   # 数据模型
│   ├── 03-sqlite-schema.md                 # 数据库 schema
│   ├── 04-agent-contracts.md               # Agent 输入输出契约
│   ├── 05-context-package.md               # 上下文包规范
│   ├── 06-review-and-revision.md           # 审查与修订
│   ├── 07-cli-commands.md                  # CLI 命令
│   ├── 08-eval-plan.md                     # 评测计划
│   └── decisions/                          # 架构决策记录
│       ├── ADR-001-sqlite-only.md
│       ├── ADR-002-genre-profile-json.md
│       ├── ADR-003-issue-driven-patch.md
│       ├── ADR-004-state-settlement.md
│       ├── ADR-005-planner-split.md        # ⭐ 新增
│       ├── ADR-006-reviewer-dual-layer.md  # ⭐ 新增
│       ├── ADR-007-creative-mode-profile.md # ⭐ 新增
│       ├── ADR-008-creative-director.md    # ⭐ 新增
│       └── ADR-009-literary-auditor.md     # ⭐ 新增
├── tasks/                                  # 任务文件
│   ├── 001-init-project.md
│   ├── 002-data-models.md
│   ├── 003-sqlite-schema.md
│   ├── 004-repository-layer.md
│   ├── 005-genre-profiles.md
│   ├── 006-creative-mode-profiles.md       # ⭐ 新增
│   ├── 007-create-project-cli.md
│   ├── 008-goal-planner.md                 # ⭐ 拆分
│   ├── 009-creative-director.md            # ⭐ 新增
│   ├── 010-context-package.md
│   ├── 011-writer-agent.md
│   ├── 012-rule-auditor.md                 # ⭐ 新增
│   ├── 013-llm-auditor.md                  # ⭐ 新增
│   ├── 014-literary-auditor.md             # ⭐ 新增
│   ├── 015-revision-handler.md
│   ├── 016-settlement-extractor.md         # ⭐ 拆分
│   ├── 017-quality-utils.md                # ⭐ 更新范围
│   ├── 018-craft-card-prompts.md
│   └── 019-langgraph-graph.md              # ⭐ 修正流程顺序
├── src/
│   └── songyan/
│       ├── __init__.py
│       ├── config.py                       # 配置管理（Pydantic Settings）
│       ├── cli/
│       │   └── main.py                     # CLI 入口
│       ├── db/
│       │   ├── schema.sql                  # SQLite schema
│       │   ├── repository.py               # 数据访问层
│       │   └── connection.py               # 数据库连接
│       ├── models/
│       │   ├── __init__.py
│       │   ├── project.py                  # ProjectSetting（含 mode_id）
│       │   ├── character.py                # Character, CharacterState
│       │   ├── chapter.py                  # ChapterGoal, ChapterVersion, ChapterHead
│       │   ├── context.py                  # ContextPackage（含 CreativeBrief）
│       │   ├── review.py                   # RuleAuditResult, LLMAuditResult, MergedReviewReport ⭐ 更新
│       │   ├── revision.py                 # Patch, RevisionOutput
│       │   ├── settlement.py               # StateSettlement ⭐
│       │   ├── genre.py                    # GenreProfile
│       │   ├── creative_mode.py            # ⭐ CreativeModeProfile, CreativeBrief, Tension
│       │   └── literary.py                 # ⭐ LiteraryObservation, LiteraryAuditResult
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── goal_planner.py             # ⭐ 拆分自 planner
│       │   ├── creative_director.py        # ⭐ 新增
│       │   ├── context_manager.py
│       │   ├── writer.py
│       │   ├── rule_auditor.py             # ⭐ 新增
│       │   ├── llm_auditor.py              # ⭐ 新增
│       │   ├── literary_auditor.py         # ⭐ 新增
│       │   ├── revision_handler.py
│       │   └── settlement_extractor.py     # ⭐ 拆分自 planner
│       ├── workflows/
│       │   └── phase1_graph.py             # ⭐ 修正流程顺序
│       ├── utils/                          # 质量检测工具
│       │   ├── ai_tells.py                 # AI 腔检测
│       │   ├── fatigue_words.py            # 疲劳词检测
│       │   ├── hook_checker.py             # 首屏/章末钩子检测
│       │   ├── paragraph_rhythm.py         # 段落节奏分析
│       │   └── token_counter.py            # Token 计数
│       └── creative_modes/                 # ⭐ 新增目录
│           ├── __init__.py
│           └── registry.py                 # CreativeModeProfile 注册表
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_repository.py
│   ├── test_context_package.py
│   ├── test_writer.py
│   ├── test_goal_planner.py                # ⭐
│   ├── test_creative_director.py           # ⭐
│   ├── test_rule_auditor.py                # ⭐
│   ├── test_llm_auditor.py                 # ⭐
│   ├── test_literary_auditor.py            # ⭐
│   ├── test_revision_handler.py
│   ├── test_settlement_extractor.py        # ⭐
│   ├── test_graph.py
│   └── test_genre_profile.py
└── evals/
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

**SQLite 是 V1.0 唯一长期事实源。**

LangGraph checkpoint 只允许保存：

```python
# state 里唯一允许存的业务相关字段
project_id: str
chapter_number: int
mode_id: str                              # 创作模式 ID ⭐ 新增
current_version_id: str | None            # 指向 chapter_versions
review_report_id: str | None              # 指向 review_reports
creative_brief_id: str | None             # 指向 creative_briefs ⭐ 新增
literary_observation_id: str | None       # 指向 literary_observations ⭐ 新增
revision_round: int                       # 0, 1, 2
status: str                               # 状态机
```

**禁止**在 LangGraph state 中保存：
- 完整章节正文
- 完整上下文包（ContextPackage）
- 完整审查报告（MergedReviewReport）
- 完整角色档案
- Genre Profile 内容
- CreativeModeProfile 内容 ⭐
- CreativeBrief 内容 ⭐
- Prompt 文本

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

- **双层审查**：RuleAuditor（代码检测） → LLMAuditor（语义审查） → MergedReviewReport ⭐
- RuleAuditor 输出 `RuleAuditResult`：AI 腔/疲劳词/段落/首屏/字数（代码执行）
- LLMAuditor 输出 `LLMAuditResult`：角色/节奏/对话/设定（LLM 调用）
- 每个 critical/major issue 必须有 `evidence_quote`
- `style_ai_tells` 和 `style_fatigue_words` 由 RuleAuditor 检测（代码，不是 LLM）⭐
- 没有证据的 issue 不能进入自动修订
- 修订由 **RevisionHandler** 完成，不由 Writer 完成
- 只处理 `fix_type = patch` 的 issue
- **保护 valuable_fissure**：LiteraryAuditor 标记的裂隙不进入自动修订 ⭐
- 最多自动修订 **2 轮**
- 修订后必须重新双层审查
- 修订引入新 critical/major → 停止自动修订，进入人工确认

### 1.7 状态结算规则（铁律）⭐

- 每章 **accept 后** 必须执行 SettlementExtractor
- `character_update.old_value` 必须与 DB 当前值一致
- `new_setting.source_quote` 必须在正文中存在
- `new_setting.setting_key` 必须唯一（用于追踪设定演变）⭐
- `numerical_update.closing_value` 必须等于公式值
- **character_states 为快照表，永远 INSERT 新记录，不 UPDATE 旧记录** ⭐
- **foreshadowings 增加 source_version_id 字段** ⭐
- 结算失败标记 `needs_human_review`，不阻塞流程
- 结算完成后才生成 ChapterSummary

### 1.8 Genre Profile 规则（铁律）

- 每个项目必须关联一个 Genre Profile（通过 genre_id）
- Writer Prompt 中注入 `genre.writer_rules`
- RuleAuditor 中注入 `genre.fatigue_words` ⭐（原 Reviewer 改为 RuleAuditor）
- LLMAuditor 中注入 `genre.reviewer_focus` ⭐（原 Reviewer 改为 LLMAuditor）
- 玄幻项目（genre_id="xuanhuan"）启用 `genre_numerical` 审查维度
- Genre Profile 从 `genres/` 目录加载，不是写死在代码里

### 1.9 CreativeModeProfile 规则（铁律）⭐ 新增

- 每个项目必须关联一个 CreativeModeProfile（通过 mode_id）
- V1.0 默认 `mode_id="webnovel"`
- CreativeModeProfile 决定：启用的 Agent、审查维度权重、修订策略、容错阈值
- 新增创作模式只需注册配置 JSON，无需修改 Agent 代码
- CreativeBrief 由 CreativeDirector 生成，入 Writer Prompt
- LiteraryAuditor 的诊断不阻塞入库

---

## 2. 项目管理框架

### 2.1 开发顺序（严格）

```
001. Pydantic models（含 CreativeModeProfile, CreativeBrief, RuleAuditResult, LLMAuditResult, LiteraryObservation）⭐
002. SQLite schema（含 creative_briefs, literary_observations 表）⭐
003. Repository 层（含 creative_briefs, literary_observations CRUD）⭐
004. Genre Profile 加载器 + 配置文件
005. CreativeModeProfile 注册表 + 配置文件 ⭐ 新增
006. CLI 创建项目（增加 mode 选择）⭐
007. GoalPlanner（拆分自 Planner）⭐
008. CreativeDirector ⭐ 新增
009. ContextPackage 组装（含 Token 预算 + CreativeBrief 注入）⭐
010. Writer Agent（含 CreativeBrief 注入）⭐
011. RuleAuditor（代码检测工具：AI 腔/疲劳词/段落/钩子/字数）⭐ 新增
012. LLMAuditor（LLM 语义审查：角色/节奏/对话/设定）⭐ 新增
013. LiteraryAuditor（文学性诊断）⭐ 新增
014. RevisionHandler patch 修订（保护 valuable_fissure）⭐
015. SettlementExtractor 状态结算（从 Planner 拆分）⭐
016. Quality Utils（AI 腔/疲劳词/首屏钩子/段落节奏检测）
017. Craft Card Prompts 加载
018. Human accept + 版本保存
019. LangGraph 编排（修正流程顺序）⭐
```

**规则**：不要在单独模块没跑通前提前接入 LangGraph。

### 2.2 任务粒度标准

| 好的粒度 | 不好的粒度 |
|----------|------------|
| "实现 Pydantic models（含 CreativeModeProfile）" | "实现 Songyan V1.0" |
| "实现 SQLite schema（含 literary_observations）" | "搭好整个 multi-agent 系统" |
| "实现 CreativeDirector Agent" | "把设计文档全部落地" |
| "实现 RuleAuditor 代码检测模块" | "完成 vibe coding" |

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
- 创建项目成功（含 mode 选择）
- Genre Profile 正确加载
- CreativeModeProfile 正确注册 ⭐
- CreativeBrief 可生成并解析 ⭐
- RuleAuditor 代码检测正确（AI 腔/疲劳词/段落）
- LLMAuditor ReviewReport 可解析（含 evidence_quote）
- LiteraryAuditor 输出 LiteraryObservation（不阻塞）⭐
- MergedReviewReport 正确合并 Rule + LLM 结果 ⭐
- 保存章节版本成功
- 版本链可追踪
- patch 应用后生成新版本
- SettlementExtractor 验证通过（old_value 匹配）
- character_states 为 INSERT 新记录 ⭐
- accepted 版本更新 chapter head
- ContextPackage 可重建（含 Token 估算 + CreativeBrief）

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

```markdown
你现在只做一个小任务。

## Project Context
当前项目：Songyan V1.0 单章闭环 MVP。
遵守 `CLAUDE.md`。

## Read
- docs/INDEX.md
- docs/02-data-models.md
- tasks/{TASK_FILE}.md

## Task
实现 tasks/{TASK_FILE}.md 中规定的内容。

## Constraints
- 不实现任务外内容
- 不引入 Web/Postgres/Qdrant/Redis/Celery
- 不改未相关文件
- 遵循 CreativeModeProfile 规则（如果当前 task 涉及）
- 遵循 Genre Profile 规则（如果当前 task 涉及）

## Done When
- [ ] 测试通过
- [ ] 简要说明改动和验证方式
```

### 3.4 当前不做清单（明确排除）

除非用户明确要求，不要实现：

- React Web UI / TUI
- Redis / Celery / ARQ / Qdrant / PostgreSQL
- 多模型路由
- 模板市场
- 拆书分析
- 完整 Studio
- 风格迁移（文学风格控制属于 V2.0+）
- 角色心理模型（V2.0+）
- 读者情绪模拟（V2.0+）
- PolyphonyPlanner（V1.5+）
- CharacterAutonomyAuditor（V2.0+）
- ForeshadowingManager（V1.5+）
- LongFormContinuityAuditor（V2.0+）
- MacroNarrativePlanner（V2.0+）

### 3.5 ADR（架构决策记录）

重要决策必须写成 ADR，不藏在长文档里。

存放位置：`docs/decisions/ADR-NNN-title.md`

每个 ADR 包含：
- **Decision** —— 做了什么决定
- **Reason** —— 为什么做这个决定
- **Consequence** —— 后果和影响

**已有 ADR**：
- ADR-001: SQLite 作为 V1.0 唯一事实源
- ADR-002: Genre Profile JSON 配置（而非硬编码）
- ADR-003: Issue-Driven Patch（而非整章重写）
- ADR-004: StateSettlement 结构化结算（而非仅摘要）
- ADR-005: **Planner 拆分为 GoalPlanner + SettlementExtractor** ⭐ 新增
- ADR-006: **Reviewer 双层化为 RuleAuditor + LLMAuditor** ⭐ 新增
- ADR-007: **CreativeModeProfile 创作模式系统** ⭐ 新增
- ADR-008: **CreativeDirector 创作导演 Agent** ⭐ 新增
- ADR-009: **LiteraryAuditor 文学性诊断 Agent** ⭐ 新增

---

## 4. V1.0 任务拆解（19 个 Task）

### Task 001: 项目初始化

```markdown
# Task 001: 初始化项目结构

## Goal
创建项目骨架，配置 pyproject.toml、.env.example、目录结构。

## In Scope
- pyproject.toml（依赖：pydantic, langgraph, langchain, litellm, click, structlog, pytest-asyncio, tiktoken）
- .env.example（LLM_API_KEY, LLM_BASE_URL, LLM_MODEL）
- 完整目录结构（src/songyan/ 下所有子目录和 __init__.py）
- CLAUDE.md（不可违背规则清单，含 CreativeModeProfile + SettlementExtractor 规则）
- docs/INDEX.md（文档索引框架）
- docs/STATUS.md（初始状态）
- genres/ 目录（空）
- creative_modes/ 目录（空）⭐

## Out of Scope
- 任何业务代码
- 数据库 schema
- CLI 命令
- Genre Profile 配置文件（Task 005）
- CreativeModeProfile 配置文件（Task 006）

## Acceptance Criteria
- [ ] `pip install -e ".[dev]"` 成功
- [ ] 目录结构与规范一致（含 creative_modes/）
- [ ] `python -c "import songyan"` 成功
- [ ] CLAUDE.md 包含所有约束规则（含 CreativeModeProfile + SettlementExtractor）
```

### Task 002: 数据模型

```markdown
# Task 002: 实现 V1.0 数据模型

## Goal
实现所有 V1.0 Pydantic models。

## Read
- docs/INDEX.md
- docs/02-data-models.md

## In Scope
- models/project.py: ProjectSetting（含 genre_id + mode_id）⭐
- models/character.py: Character, CharacterState
- models/chapter.py: ChapterGoal（含 chapter_type）, ChapterVersion（含 context_snapshot + creative_brief_id）⭐, ChapterHead
- models/context.py: ContextPackage（含 creative_brief, genre_rules, mode_rules）⭐, HardConstraint, SoftReference, CharacterStateSnapshot（含 importance_score）, RecentPlot, ForeshadowingItem, ModeRules ⭐
- models/review.py: ReviewIssue（ReviewCategory 12 维 LLM）⭐, RuleAuditResult ⭐, LLMAuditResult ⭐, MergedReviewReport ⭐
- models/revision.py: Patch, RevisionOutput
- models/settlement.py: StateSettlement, CharacterUpdate, NewSetting（含 setting_key）⭐, ForeshadowingUpdate（含 source_version_id）⭐, NumericalUpdate, Increment, Decrement
- models/genre.py: GenreProfile
- models/creative_mode.py: CreativeModeProfile, CreativeBrief, Tension ⭐ 新增
- models/literary.py: LiteraryObservation, LiteraryAuditResult ⭐ 新增

## Out of Scope
- SQLite schema
- CLI
- LLM prompts
- LangGraph

## Acceptance Criteria
- [ ] 所有 model 有类型标注
- [ ] Pydantic v2 可正常 validate
- [ ] StateSettlement 的验证逻辑正确（old_value 检查、setting_key 唯一性）⭐
- [ ] CreativeModeProfile 可从 dict 加载
- [ ] CreativeBrief 包含 required_tensions + forbidden_patterns
- [ ] LiteraryObservation 的 observation_type 枚举正确
- [ ] 有最小单元测试（test_models.py）
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
  - 新增 creative_briefs 表 ⭐
  - 新增 literary_observations 表 ⭐
  - chapter_versions 增加 UNIQUE(project_id, chapter_number, version_number) ⭐
  - review_reports 增加 audit_type 字段 ⭐
  - review_reports 增加 rule_audit_result + llm_audit_result 字段 ⭐
  - character_states 明确为快照表（注释说明永远 INSERT）⭐
  - setting_snapshots 增加 setting_key 字段 ⭐
  - foreshadowings 增加 source_version_id 字段 ⭐
- db/connection.py: 数据库连接管理
- db/migrations.py: schema 初始化

## Out of Scope
- Repository 层（下一 task）
- 业务逻辑

## Acceptance Criteria
- [ ] `sqlite3 songyan.db < schema.sql` 成功
- [ ] 所有表创建无误（含 creative_briefs, literary_observations）
- [ ] 唯一约束生效（chapter_versions）
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
  - CharacterRepository: create, get, list, update_state（INSERT 新快照）⭐
  - ChapterVersionRepository: create, get, list_chain, get_head, update_head
  - ReviewReportRepository: create, get（含 rule_audit_result + llm_audit_result）⭐
  - LiteraryObservationRepository: create, get ⭐ 新增
  - CreativeBriefRepository: create, get ⭐ 新增
  - ContextPackageRepository: save_snapshot, get_snapshot
  - ForeshadowingRepository: create, update_status, list_active
  - SettingSnapshotRepository: create, list_by_project（含 setting_key 追踪）⭐
  - NumericalLedgerRepository: create, get_latest

## Out of Scope
- Agent 逻辑
- CLI

## Acceptance Criteria
- [ ] 所有 CRUD 有基本测试
- [ ] 版本链可通过 parent_version_id 追溯
- [ ] chapter_heads 可更新
- [ ] character_states 为 INSERT 操作 ⭐
- [ ] CreativeBriefRepository 可创建和查询 ⭐
- [ ] LiteraryObservationRepository 可创建和查询 ⭐
- [ ] Agent 不直接拼 SQL，通过 repository 访问
```

### Task 005: Genre Profile 系统

```markdown
# Task 005: 实现 Genre Profile 加载器 + 配置文件

## Goal
实现 Genre Profile 的加载和管理。

## Read
- docs/INDEX.md
- genres/ 目录

## In Scope
- genres/xuanhuan.json: 玄幻题材配置
- genres/urban.json: 都市题材配置
- genres/scifi.json: 科幻题材配置
- songyan/genres/__init__.py
- songyan/genres/loader.py: load_genre_profile(genre_id) -> GenreProfile

## Genre Profile 内容要求
每个 JSON 必须包含：
- id, name, chapter_types, fatigue_words, satisfaction_types
- has_numerical_system, has_power_scaling
- pacing_rule, writer_rules, reviewer_focus, active_audit_dimensions（从 ReviewCategory 枚举选）⭐, taboos

## Out of Scope
- Writer/Reviewer 中的注入逻辑（后续 task）

## Acceptance Criteria
- [ ] 三个 JSON 配置文件有效
- [ ] active_audit_dimensions 使用枚举值（不是数字）⭐
- [ ] load_genre_profile("xuanhuan") 返回正确的 GenreProfile
- [ ] load_genre_profile("urban") 返回正确的 GenreProfile
- [ ] 无效的 genre_id 抛出明确异常
- [ ] 有测试验证加载逻辑
```

### Task 006: CreativeModeProfile 系统 ⭐ 新增

```markdown
# Task 006: 实现 CreativeModeProfile 注册表 + 配置文件

## Goal
实现创作模式配置系统。

## Read
- docs/INDEX.md
- creative_modes/ 目录

## In Scope
- creative_modes/webnovel.json: 网文模式配置
- creative_modes/literary.json: 严肃文学模式配置
- creative_modes/hybrid.json: 混合模式配置
- songyan/creative_modes/__init__.py
- songyan/creative_modes/registry.py: CreativeModeRegistry ⭐

## CreativeModeProfile 内容要求
每个 JSON 必须包含：
- id, name, enabled_agents（各阶段启用的 Agent 列表）
- audit_weights（各维度权重）
- active_audit_dimensions（启用的审查维度列表）
- revision_policy（修订策略）
- tolerance（容错阈值：max_ai_tells, max_fatigue_words, max_cliche_risk）
- success_metrics（成功指标定义）

## Out of Scope
- Writer/Reviewer 中的注入逻辑
- CreativeDirector/LiteraryAuditor（后续 task）

## Acceptance Criteria
- [ ] 三个 JSON 配置文件有效
- [ ] CreativeModeRegistry.register() / .get() / .list_modes() 正常工作
- [ ] webnovel 模式启用 goal_planner + creative_director + writer + rule_auditor + llm_auditor + literary_auditor
- [ ] literary 模式启用额外的 polyphony_planner
- [ ] 新增模式只需注册 JSON，无需改代码
- [ ] 有测试验证注册和加载逻辑
```

### Task 007: CLI 创建项目

```markdown
# Task 007: 实现 create-project CLI

## Goal
实现新手创建向导 CLI。

## Read
- docs/INDEX.md
- docs/07-cli-commands.md

## In Scope
- cli/main.py: songyan create-project 命令
- 8 步交互式向导（创作模式选择 + 题材从列表选择）⭐
  - 第 1 步：创作模式选择（webnovel / literary / hybrid）⭐
  - 第 2-8 步：原有步骤后移
- AI 实时建议（调用 LLM）
- 保存到 SQLite（genre_id 关联 GenreProfile，mode_id 关联 CreativeModeProfile）⭐

## Out of Scope
- 其他 CLI 命令
- Writer/Reviewer

## Acceptance Criteria
- [ ] `songyan create-project` 可交互运行
- [ ] 8 步向导完整（含创作模式选择）⭐
- [ ] 创作模式选择从 CreativeModeRegistry 加载 ⭐
- [ ] 题材选择从 GenreProfile 列表加载
- [ ] 项目保存到 SQLite（含 genre_id + mode_id）⭐
- [ ] 可用 `songyan list-projects` 查看
```

### Task 008: GoalPlanner Agent ⭐ 拆分

```markdown
# Task 008: 实现 GoalPlanner Agent（拆分自 Planner）

## Goal
实现章节目标制定 Agent。

## Read
- docs/INDEX.md
- docs/04-agent-contracts.md
- prompts/goal_planner.md ⭐

## In Scope
- agents/goal_planner.py: define_chapter_goal()
  - 输入：项目设定 + Genre Profile + CreativeModeProfile + 最近剧情 ⭐
  - 输出：ChapterGoal（JSON）
  - 包含：target_events, emotional_arc, hooks, obligations, word_count_target, chapter_type
  - 遵守 CreativeModeProfile 的约束 ⭐

## Out of Scope
- 状态结算（SettlementExtractor 负责）
- 摘要生成
- ContextManager
- Writer

## Acceptance Criteria
- [ ] 可输出结构化 ChapterGoal
- [ ] 遵守 Genre Profile 的 pacing_rule
- [ ] 遵守 CreativeModeProfile 的约束 ⭐
- [ ] target_events 具体可执行
- [ ] hooks 有信息量
- [ ] 有测试（可用 mock LLM）
```

### Task 009: CreativeDirector Agent ⭐ 新增

```markdown
# Task 009: 实现 CreativeDirector Agent

## Goal
实现创作导演 Agent——写前生成创作意图+张力地图。

## Read
- docs/INDEX.md
- docs/04-agent-contracts.md
- prompts/creative_director.md

## In Scope
- agents/creative_director.py: generate_creative_brief()
  - 输入：ChapterGoal + Genre Profile + 角色状态 + 最近剧情 + CreativeModeProfile
  - 输出：CreativeBrief（结构化 JSON）
  - 包含：creative_intent, required_tensions, forbidden_patterns, allowed_fissures, style_constraints, reader_contract
  - 温度 0.7

## Out of Scope
- 不写正文
- 不做审查

## Acceptance Criteria
- [ ] 可输出结构化 CreativeBrief
- [ ] CreativeBrief 包含 required_tensions（1-3 个）
- [ ] CreativeBrief 包含 forbidden_patterns（至少 3 个）
- [ ] forbidden_patterns 具体（不是"不要写得不好"）
- [ ] 输出 JSON，不自由格式
- [ ] 有测试（可用 mock LLM）
```

### Task 010: ContextPackage 组装

```markdown
# Task 010: 实现上下文包组装（含 Token 预算管理 + CreativeBrief 注入）

## Goal
实现 ContextManager Agent 的上下文包组装逻辑。

## Read
- docs/INDEX.md
- docs/05-context-package.md

## In Scope
- agents/context_manager.py: assemble_context_package()
  - 从 SQLite 加载：项目设定、角色状态、最近章节摘要、伏笔
  - 加载 Genre Profile 并注入
  - 加载 CreativeModeProfile 并注入 ⭐
  - 加载 CreativeBrief 并注入 ⭐
  - 分区组装：hard_constraints, soft_references, recent_plot, character_states, foreshadowing, chapter_goal, genre_rules, mode_rules, creative_brief ⭐
  - **Token 估算和预算管理**（默认 32K，上限 64K）
  - 出场角色检测（只加载出场角色）
  - 预算超出时的裁剪策略（软参考 → CreativeBrief → 最近剧情 → 角色详细度）⭐
  - context snapshot 保存到 generation_metadata

## ContextBudget 实现
```python
@dataclass
class ContextBudget:
    total_budget: int = 32_000
    generation_reserve: int = 8_000
    available: int = 24_000
    creative_brief_max: int = 1_500      # ⭐ 新增
    # 各分区预算...
```

## Out of Scope
- Writer
- Reviewer

## Acceptance Criteria
- [ ] 上下文包正确分区（含 creative_brief + mode_rules）⭐
- [ ] Token 估算准确（使用 tiktoken）
- [ ] 不出场角色不加载
- [ ] Token 不超过 32K（默认）
- [ ] 超预算时按优先级裁剪（CreativeBrief 在软参考之后裁剪）⭐
- [ ] snapshot 可保存和重建
- [ ] 有测试验证组装逻辑和预算管理
```

### Task 011: Writer Agent

```markdown
# Task 011: 实现 Writer Agent（含 CreativeBrief 注入）

## Goal
实现 Writer Agent 的初稿生成。

## Read
- docs/INDEX.md
- docs/04-agent-contracts.md
- prompts/writer.md
- prompts/craft_card.md
- prompts/creative_director.md（参考 CreativeBrief 格式）⭐

## In Scope
- agents/writer.py: write_draft()
  - 加载 craft_card.md 作为工艺层注入
  - 加载 CreativeBrief 作为创作意图层注入 ⭐
  - 按场景生成（不是一次性整章）
  - 对话单独成段
  - 章末有钩子
  - 新设定标记 [[新设定:描述]]
  - 输出 ChapterVersion (version_type="draft")
  - generation_metadata 包含 context_snapshot + creative_brief ⭐

## Prompt 组装逻辑
```python
def build_writer_prompt(context: ContextPackage, goal: ChapterGoal) -> str:
    sections = [
        build_constraint_section(context),          # 约束层（动态）
        load_craft_card(),                           # 工艺层（固定）
        build_genre_section(context.genre_rules),    # 题材层（GenreProfile）
        build_creative_brief_section(context.creative_brief),  # 创作意图层 ⭐
    ]
    return "\n\n---\n\n".join(sections)
```

## Out of Scope
- 修订逻辑（RevisionHandler 负责）
- Reviewer

## Acceptance Criteria
- [ ] 可生成一章中文小说（至少 2000 字）
- [ ] 遵守上下文包硬约束
- [ ] 遵守 CreativeBrief 的 forbidden_patterns ⭐
- [ ] 实现 CreativeBrief 的 required_tensions ⭐
- [ ] 不引入未提及设定（或正确标记）
- [ ] 输出可解析为 ChapterVersion
- [ ] Craft Card 内容正确注入 Prompt
- [ ] Genre Profile 规则正确注入
- [ ] CreativeBrief 正确注入 Prompt ⭐
- [ ] 有测试（可用 mock LLM）
```

### Task 012: RuleAuditor Agent ⭐ 新增

```markdown
# Task 012: 实现 RuleAuditor 代码检测 Agent

## Goal
实现代码层规则检测 Agent。

## Read
- docs/INDEX.md
- docs/06-review-and-revision.md
- prompts/rule_auditor.md ⭐

## In Scope
- agents/rule_auditor.py: audit_rules()
  - AI 腔检测（正则匹配，调用 utils/ai_tells.py）
  - 疲劳词检测（字符串匹配，调用 utils/fatigue_words.py）
  - 段落节奏分析（统计，调用 utils/paragraph_rhythm.py）
  - 首屏钩子检查（规则，调用 utils/hook_checker.py）
  - 章末钩子检查（规则，调用 utils/hook_checker.py）
  - 字数统计
  - 数值公式验证（玄幻，调用 utils/numerical_validator.py）⭐
  - 输出 RuleAuditResult（结构化 JSON）
  - **不调用 LLM，全部代码执行**

## Out of Scope
- LLM 语义审查（LLMAuditor 负责）
- 文学性诊断（LiteraryAuditor 负责）

## Acceptance Criteria
- [ ] AI 腔检测识别 "不禁猛然意识到" 等模式（< 50ms）
- [ ] 疲劳词检测统计 "冷笑" 出现次数（< 20ms）
- [ ] 首屏钩子检测正确判断前 300 字（< 10ms）
- [ ] 段落节奏分析正确（< 30ms）
- [ ] 字数统计准确
- [ ] 数值公式验证正确（玄幻）⭐
- [ ] **所有检测总耗时 < 200ms**
- [ ] 有测试验证各种检测场景
```

### Task 013: LLMAuditor Agent ⭐ 新增

```markdown
# Task 013: 实现 LLMAuditor 语义审查 Agent

## Goal
实现 LLM 语义审查 Agent。

## Read
- docs/INDEX.md
- docs/06-review-and-revision.md
- prompts/llm_auditor.md ⭐

## In Scope
- agents/llm_auditor.py: audit_semantics()
  - 12 维度语义审查（world_consistency, character_behavior, timeline, new_setting_unregistered, narrative_pacing, narrative_hook, info_dump, dialogue_distinctness, dialogue_subtext, description_sensory, show_dont_tell, genre_numerical）
  - 输出 LLMAuditResult（结构化 issue 列表）
  - 每个 critical/major 必须有 evidence_quote
  - 严重度分级：critical/major/minor/info
  - 输出文学性评分：cliche_risk_score, character_autonomy_score, conceptual_idling_score ⭐

## Out of Scope
- 代码检测（RuleAuditor 负责）
- 文学性诊断（LiteraryAuditor 负责）
- 自动修订

## Acceptance Criteria
- [ ] 可输出结构化 LLMAuditResult（12 维度）
- [ ] 每个 issue 有 evidence_quote
- [ ] critical/major 可被测试用例触发
- [ ] 无 evidence 的 issue 被过滤
- [ ] 输出文学性评分（供 LiteraryAuditor 参考）⭐
- [ ] 有测试验证审查逻辑
```

### Task 014: LiteraryAuditor Agent ⭐ 新增

```markdown
# Task 014: 实现 LiteraryAuditor 文学性诊断 Agent

## Goal
实现文学性诊断 Agent。

## Read
- docs/INDEX.md
- prompts/literary_auditor.md ⭐

## In Scope
- agents/literary_auditor.py: diagnose_literary_quality()
  - 人物工具化检测（character_tooling）
  - 概念空转检测（conceptual_idling）
  - 过度平滑诊断（excessive_smoothing）
  - 有价值裂隙标记（valuable_fissure）— 不是缺陷，建议保留
  - 套路化风险评估（cliche_risk）
  - 复调不足检测（polyphony_weakness）
  - 作者侵入检测（authorial_intrusion）
  - 输出 LiteraryAuditResult（结构化 observations 列表）
  - **诊断不阻塞入库**

## Out of Scope
- 不修改正文
- 不输出 fix
- 不阻塞流程

## Acceptance Criteria
- [ ] 可输出结构化 LiteraryAuditResult
- [ ] observations 包含 observation_type + description
- [ ] valuable_fissure 标记为 preserve: true
- [ ] 诊断不阻塞（无论结果如何，流程继续）
- [ ] 有测试验证诊断逻辑
```

### Task 015: RevisionHandler

```markdown
# Task 015: 实现修订 Handler

## Goal
实现 RevisionHandler 节点。

## Read
- docs/INDEX.md
- docs/06-review-and-revision.md

## In Scope
- agents/revision_handler.py:
  - 筛选 patchable issues (critical/major + fix_type=patch)
  - **排除 LiteraryAuditor 标记的 valuable_fissure** ⭐
  - 从后往前应用 patch
  - 创建 revision 版本

## Out of Scope
- LangGraph 编排
- HumanConfirm

## Acceptance Criteria
- [ ] patch 只修改有 issue 的部分
- [ ] 保留未修改内容
- [ ] 保护 valuable_fissure（不修改 LiteraryAuditor 标记的元素）⭐
- [ ] 最多 2 轮自动修订
- [ ] 从后往前应用 patch
- [ ] 有测试
```

### Task 016: SettlementExtractor ⭐ 拆分

```markdown
# Task 016: 实现 SettlementExtractor 状态结算

## Goal
实现章节完成后的结构化状态结算。

## Read
- docs/INDEX.md
- models/settlement.py

## In Scope
- agents/settlement_extractor.py: extract_settlement()
  - 从 accepted 章节正文中提取状态变更
  - 输出 StateSettlement（结构化 JSON）
  - 代码层验证：
    - character_update.old_value == DB 当前值
    - new_setting.source_quote 在正文中存在
    - new_setting.setting_key 唯一 ⭐
    - numerical_update.closing_value == 公式值
  - 验证通过后 INSERT 新快照（不 UPDATE）⭐
  - 验证失败标记 needs_human_review

## Out of Scope
- 摘要生成（后续 task）
- LangGraph 编排

## Acceptance Criteria
- [ ] 可从正文中提取 character_updates
- [ ] old_value 验证逻辑正确
- [ ] source_quote 存在性验证正确
- [ ] setting_key 唯一性验证正确 ⭐
- [ ] numerical closing_value 公式验证正确
- [ ] 验证通过后 INSERT 新记录（不 UPDATE）⭐
- [ ] 验证失败标记 needs_human_review 不阻塞
- [ ] 有测试（含验证失败场景）
```

### Task 017: Quality Utils

```markdown
# Task 017: 实现质量检测工具模块

## Goal
实现 AI 腔检测、疲劳词检测、钩子检测、段落节奏分析工具。

## Read
- docs/INDEX.md
- genres/*.json（疲劳词表来源）

## In Scope
- utils/ai_tells.py:
  - AI_TELL_PATTERNS: 正则模式列表
  - detect_ai_tells(text: str) -> list[AiTellMatch]
  - AiTellMatch: pattern, matched_text, location
  
- utils/fatigue_words.py:
  - detect_fatigue_words(text: str, fatigue_words: list[str]) -> list[FatigueWordMatch]
  - FatigueWordMatch: word, count, locations
  
- utils/hook_checker.py:
  - check_opening_hook(text: str) -> bool
  - check_ending_hook(text: str) -> bool
  
- utils/paragraph_rhythm.py:
  - analyze_paragraph_rhythm(text: str) -> RhythmScore

- utils/numerical_validator.py: ⭐ 新增
  - validate_numerical_formulas(text: str, context: NumericalContext) -> list[str]
  - 验证 closing_value == opening + sum(increments) - sum(decrements)

## Out of Scope
- RuleAuditor 中的调用（已在 Task 012 中）
- Writer 中的预防

## Acceptance Criteria
- [ ] AI 腔检测能识别 "不禁猛然意识到" 等模式（< 50ms）
- [ ] 疲劳词检测能统计 "冷笑" 出现次数（< 20ms）
- [ ] 首屏钩子检测正确判断前 300 字（< 10ms）
- [ ] 段落节奏分析正确（< 30ms）
- [ ] 数值公式验证正确 ⭐
- [ ] **所有检测总耗时 < 200ms**
- [ ] 有测试验证各种检测场景
```

### Task 018: Craft Card Prompts

```markdown
# Task 018: 实现写作工艺层 Prompt 加载

## Goal
实现工艺层 Prompt 的加载和注入。

## Read
- docs/INDEX.md
- prompts/craft_card.md

## In Scope
- prompts/craft_card.md: 完整工艺层模板（黄金开篇、段落节奏、对话工艺、ShowDon'tTell、信息释放、感官沉浸、章末钩子、新设定标记）
- utils/prompt_loader.py: load_craft_card() -> str
- Writer Agent 中的集成（调用 load_craft_card 注入 Prompt）

## Out of Scope
- Writer 生成逻辑（已在 Task 011 中）

## Acceptance Criteria
- [ ] craft_card.md 内容完整（8 个工艺模块）
- [ ] load_craft_card() 正确返回文件内容
- [ ] Writer Prompt 中正确注入工艺层
- [ ] 工艺层内容不对性能造成负面影响（通过测试验证）
```

### Task 019: LangGraph 编排 ⭐ 修正流程顺序

```markdown
# Task 019: LangGraph 工作流编排（修正后的流程顺序）

## Goal
将所有节点串联成完整的 V1.0 工作流。

## Read
- docs/INDEX.md

## In Scope
- workflows/phase1_graph.py:
  - 定义 Phase1State（含 mode_id, creative_brief_id, literary_observation_id）⭐
  - 节点（修正后的顺序）：
    1. goal_planner（目标制定）⭐
    2. creative_director（创作意图）⭐
    3. context_manager（上下文组装）
    4. writer（写作）
    5. rule_auditor（代码检测）⭐
    6. llm_auditor（语义审查）⭐
    7. review_merger（合并报告）⭐
    8. literary_auditor（文学诊断）⭐
    9. revision_router（条件路由）
    10. revision_handler（patch 修订）
    11. human_confirm（人工确认）
    12. settlement_extractor（状态结算）⭐
  - 条件路由：pass → literary_auditor → human_confirm, revise → revision_handler
  - revision_handler → rule_auditor（循环，最多 2 轮）⭐
  - human_confirm → settlement（accept）/ goal_planner（reject）⭐
  - settlement → done
  - SQLite checkpoint

## 修正后的状态机
```
idle -> goal_planning -> creative_direction -> context_assembly -> writing
  -> rule_auditing -> llm_auditing -> review_merging -> literary_auditing
  -> [revision -> rule_auditing -> llm_auditing] (最多 2 轮)
  -> human_confirm

human_confirm:
  accept -> settlement -> done
  reject -> goal_planning
  back -> writing
  edit -> (编辑器) -> accept -> settlement -> done
```

## Out of Scope
- V1.5/V2.0 功能

## Acceptance Criteria
- [ ] 完整流程可运行：goal_plan → creative_direct → assemble → write → rule_audit → llm_audit → merge → literary_audit → settle → confirm
- [ ] 流程顺序正确（CreativeDirector 在 ContextManager 之前）⭐
- [ ] 有 issue 时进入 revision → rule_audit 循环（最多 2 轮）⭐
- [ ] accept 后执行 settlement（状态结算）⭐
- [ ] settlement 验证失败后进入 human_confirm ⭐
- [ ] reject 退回 goal_planner（不是 planner）⭐
- [ ] checkpoint 可恢复
- [ ] 有端到端测试
```

---

## 5. 所有 Prompt 汇总

### 5.1 Master System Prompt

```markdown
# Songyan Development Guide

你是 Songyan 项目的协作开发代理。Songyan 是一个面向中文长篇小说写作的
multi-agent 系统，核心目标不是一次性生成文本，而是建立
"设定 → 创作模式选择 → 章节目标制定 → 创作意图生成 → 上下文包 → 章节生成 → 双层审查 → 文学性诊断 → issue-driven修订 → 状态结算 → 人工确认 → 版本保存"
的可复现闭环。

## 当前阶段

当前只实现 V1.0：单章闭环 MVP。

不要提前实现 V1.5/V2.0 的复杂能力，除非用户明确要求。

V1.0 的目标是验证：
- 能否创建项目设定和角色卡（含创作模式选择）
- 能否加载 Genre Profile 并注入 Prompt
- 能否加载 CreativeModeProfile 并决定工作流 ⭐
- 能否生成 CreativeBrief（创作意图+张力地图）⭐
- 能否组装小说专用 Context Package（含 Token 预算 + CreativeBrief）
- 能否生成一章中文小说草稿（受工艺层 + CreativeBrief 约束）
- 能否输出 RuleAuditResult（代码检测，AI腔/疲劳词/段落）⭐
- 能否输出 LLMAuditResult（语义审查，12维度）⭐
- 能否合并为 MergedReviewReport ⭐
- 能否输出 LiteraryAuditResult（文学性诊断）⭐
- 能否基于 ReviewIssue 做局部 patch 修订（保护 valuable_fissure）⭐
- 能否执行 SettlementExtractor 并验证 ⭐
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
9. **双层审查：RuleAuditor（代码快）+ LLMAuditor（语义准）** ⭐
10. LiteraryAuditor 诊断不阻塞入库。⭐
11. 自动修订只允许 issue-driven patch，不允许默认整章重写。
12. 自动修订最多 2 轮，之后进入人工确认。
13. 每章 accept 后必须执行 SettlementExtractor，代码层验证后 INSERT 新快照。⭐
14. 每个项目关联 Genre Profile + CreativeModeProfile。⭐
15. CreativeBrief 由 CreativeDirector 生成，入 Writer Prompt。⭐
16. **Agent 代表"可替换能力"，不是"人"**。⭐

## 当前不做

除非用户明确要求，不要实现：
- React Web UI / TUI
- Redis / Celery / ARQ / Qdrant / PostgreSQL
- 多模型路由
- 模板市场
- 拆书分析
- 完整 Studio
- 风格迁移（V2.0+）
- 角色心理模型（V2.0+）
- 读者情绪模拟（V2.0+）
- PolyphonyPlanner（V1.5+）
- CharacterAutonomyAuditor（V2.0+）
- ForeshadowingManager（V1.5+）
- LongFormContinuityAuditor（V2.0+）
- MacroNarrativePlanner（V2.0+）

## 推荐项目结构

songyan/
  agents/
    goal_planner.py              # ⭐ 拆分
    creative_director.py         # ⭐ 新增
    context_manager.py
    writer.py
    rule_auditor.py              # ⭐ 新增
    llm_auditor.py               # ⭐ 新增
    literary_auditor.py          # ⭐ 新增
    revision_handler.py
    settlement_extractor.py      # ⭐ 拆分
  cli/
    main.py
  db/
    schema.sql
    repository.py
    connection.py
  models/
    project.py
    character.py
    chapter.py
    context.py
    review.py                    # ⭐ 更新
    revision.py
    settlement.py
    genre.py
    creative_mode.py             # ⭐ 新增
    literary.py                  # ⭐ 新增
  workflows/
    phase1_graph.py              # ⭐ 更新
  prompts/
    writer.md
    craft_card.md
    creative_director.md         # ⭐ 新增
    goal_planner.md              # ⭐ 拆分
    rule_auditor.md              # ⭐ 新增
    llm_auditor.md               # ⭐ 新增
    literary_auditor.md          # ⭐ 新增
    settlement_extractor.md      # ⭐ 拆分
  creative_modes/                # ⭐ 新增
    webnovel.json
    literary.json
    hybrid.json
  genres/
    xuanhuan.json
    urban.json
    scifi.json
  utils/
    ai_tells.py
    fatigue_words.py
    hook_checker.py
    paragraph_rhythm.py
    numerical_validator.py       # ⭐ 新增
    token_counter.py
  evals/
    runner.py

## 核心数据模型

优先实现这些 Pydantic models：
- ProjectSetting（含 genre_id + mode_id）
- ChapterGoal（含 chapter_type）
- CreativeBrief（含 required_tensions + forbidden_patterns） ⭐
- ContextPackage（含 creative_brief + mode_rules） ⭐
- RuleAuditResult（含 ai_tell_matches + fatigue_word_matches） ⭐
- LLMAuditResult（含 issues + dimension_scores + cliche_risk_score） ⭐
- LiteraryAuditResult（含 observations + valuable_fissure） ⭐
- MergedReviewReport（合并 Rule + LLM） ⭐
- StateSettlement（含 character_updates + new_settings + setting_key） ⭐
- ChapterVersion（含 creative_brief_id + literary_observation_id） ⭐
```

---

## 6. 项目管理工具模板

### 6.1 Task 文件模板

```markdown
# Task NNN: 任务标题

## Goal
一句话描述目标。

## Read
- docs/INDEX.md
- docs/XX-relevant-doc.md
- tasks/{DEPENDENCY}.md（依赖的 task）

## In Scope
- 具体实现内容
- 新增/修改的文件

## Out of Scope
- 明确排除的内容

## Acceptance Criteria
- [ ] 可验证的完成标准 1
- [ ] 可验证的完成标准 2
- [ ] 测试通过

## Dependencies
- Task XXX（必须在之前完成）
```

### 6.2 STATUS.md 更新模板

```markdown
# Songyan 项目状态

## 当前任务
Task NNN: 任务标题

## 已完成
- Task 001: 项目初始化 ✅
- Task 002: 数据模型 ✅
- ...

## 进行中
- Task NNN: 任务标题（进行中）

## 阻塞
- 无

## 已知问题
- 问题描述 → 解决方案
```

---

## 7. 交付检查清单

### V1.0 交付前必须完成

- [ ] 所有 19 个 Task 完成
- [ ] 所有测试通过（pytest -v）
- [ ] 双层审查可运行（RuleAuditor + LLMAuditor → MergedReviewReport）⭐
- [ ] LiteraryAuditor 诊断不阻塞 ⭐
- [ ] CreativeDirector 生成 CreativeBrief ⭐
- [ ] SettlementExtractor 验证通过（old_value 匹配，INSERT 不 UPDATE）⭐
- [ ] 完整流程可运行：goal_plan → creative_direct → assemble → write → rule_audit → llm_audit → merge → literary_audit → settle → confirm ⭐
- [ ] 3 个题材配置文件有效（xuanhuan/urban/scifi）
- [ ] 3 个创作模式配置文件有效（webnovel/literary/hybrid）⭐
- [ ] CLI 创建项目可交互运行（8 步向导）
- [ ] 评测指标可收集：
  - [ ] 设定硬错误数
  - [ ] 人工大改比例
  - [ ] 审查漏检率
  - [ ] 修订后新问题数
  - [ ] AI 腔规则命中数
  - [ ] 疲劳词命中数
  - [ ] 首屏/章末钩子达标率
  - [ ] 状态结算字段准确率
  - [ ] 概念空转段落数 ⭐
  - [ ] 人物语言区分度 ⭐
- [ ] 文档更新：
  - [ ] README.md
  - [ ] CLAUDE.md
  - [ ] docs/INDEX.md

### 代码质量检查

- [ ] 所有函数带类型标注
- [ ] 所有 Pydantic 模型定义完整
- [ ] 无裸 except
- [ ] 单文件不超过 400 行
- [ ] Prompt 放在 prompts/ 目录
- [ ] 无 print，全部用 structlog
- [ ] 测试覆盖率 > 60%
