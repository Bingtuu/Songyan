# Songyan 项目状态板

> 每次 AI 接手任务前必须先读此文件。
> 每次任务完成后必须更新此文件。

---

## 当前阶段

Phase 2 — Agent 能力层（Task 017 完成）

## 已完成

- [x] design_docs_v2 文档体系建立
- [x] system_prompt/development-tech-plan-v2.md — V2 技术方案
- [x] CLAUDE.md — 开发代理指令与不可违背规则（67 条）
- [x] docs/STATUS.md — 项目状态板
- [x] docs/INDEX.md — 文档索引（三层分类）
- [x] system_prompt/ai-collaboration-guide.md — 多 AI 协作规范
- [x] system_prompt/context-management-guide.md — 上下文管理方案
- [x] system_prompt/tdd-guide.md — TDD 测试驱动方案
- [x] .env.example — 环境变量模板
- [x] pyproject.toml — 项目配置（含 pydantic, langgraph, litellm 等依赖）
- [x] .gitignore — 忽略规则
- [x] src/songyan/ 完整目录结构 + __init__.py + config.py + cli/main.py
- [x] tests/test_init.py — Task 001 验收测试
- [x] tasks/TEMPLATE.md — Task 规格模板
- [x] tasks/001-init-project.md — Task 001 规格
- [x] README.md — 项目说明骨架

## 进行中

- [x] Task 001: 项目初始化（骨架已搭，pip install 验证通过）
- [x] Task 002: Pydantic 数据模型（35 个模型，68 个测试全部通过）
- [x] Task 003: SQLite Schema（13 张表，26 个测试全部通过）
- [x] Task 004: Repository 层（11 个 Repository，51 个 DB 测试全部通过）
- [x] Task 005: Genre Profile 系统（3 个 JSON 配置 + 加载器 + 36 个测试全部通过）
- [x] Task 006: CreativeModeProfile 系统（3 个 JSON 配置 + 注册表 + 38 个测试全部通过）
- [x] Task 007: CLI 创建项目（create-project 交互向导 + list-projects + 6 个 CLI 测试全部通过）

## 待开始

- [ ] Task 008: GoalPlanner Agent
- [ ] Task 008: GoalPlanner Agent
- [ ] Task 009: CreativeDirector Agent
- [ ] Task 010: ContextPackage 组装
- [ ] Task 011: Writer Agent
- [x] Task 017: Quality Utils（5 个检测工具 + 77 测试全部通过）
- [ ] Task 018: Craft Card Prompts
- [ ] Task 008: GoalPlanner Agent
- [ ] Task 009: CreativeDirector Agent
- [ ] Task 010: ContextManager
- [ ] Task 011: Writer Agent
- [ ] Task 012: RuleAuditor Agent
- [ ] Task 013: LLMAuditor Agent
- [ ] Task 014: LiteraryAuditor Agent
- [ ] Task 015: RevisionHandler
- [ ] Task 016: SettlementExtractor
- [ ] Task 019: LangGraph 编排 + SummaryWriter
- [ ] 集成测试 + 评测集

## 阻塞项

- 无

## 最近变更

- 2026-05-24: Task 017 Quality Utils 完成（AI 腔/疲劳词/钩子/段落节奏/数值验证 5 个检测工具、_helpers 辅助模块、77 个 utils 测试全部通过、ruff 0 errors、总测试 279 passed）
- 2026-05-24: Task 007 CLI 创建项目完成（create-project 8 步交互向导、list-projects、动态加载 mode/genre、project_id 生成、SQLite 持久化、6 个 CLI 测试全部通过）
- 2026-05-24: Task 006 CreativeModeProfile 系统完成（webnovel 完整配置 + literary/hybrid 基础配置、load_creative_mode_profile / list_creative_mode_profiles / CreativeModeProfileLoader、内存缓存、38 个测试全部通过）
- 2026-05-24: Task 005 Genre Profile 系统完成（xuanhuan 完整配置 + urban/scifi 基础配置、load_genre_profile / list_genre_profiles / GenreProfileLoader、内存缓存、36 个测试全部通过）
- 2026-05-24: Task 004 Repository 层完成（核心/审查/结算 11 个 Repository、JSON 序列化、版本链、快照 INSERT only、51 个 DB 测试全部通过）
- 2026-05-24: Task 003 SQLite Schema 完成（13 张表、aiosqlite 异步连接、WAL 模式、26 个测试全部通过）
- 2026-05-24: Task 002 Pydantic 数据模型完成（35 个模型、68 个测试全部通过）
- 2026-05-24: 完整工程规范体系建立（CLAUDE.md + TDD + 上下文管理 + 协作规范 + Task 001 骨架）
- 2026-05-24: 项目目录整理（design_docs_v2/ → docs/architecture/，design_docs/ → docs/history/，project_review_docs/ → docs/review/）
