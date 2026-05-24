# Songyan 项目状态板

> 每次 AI 接手任务前必须先读此文件。
> 每次任务完成后必须更新此文件。

---

## 当前阶段

Phase 2 — Agent 能力层（Task 010 完成）

## 已完成

### Phase 1 — 基础设施
- [x] Task 001: 项目初始化（骨架、pip install、CLAUDE.md、docs/INDEX.md、STATUS.md）
- [x] Task 002: Pydantic 数据模型（35 个模型、68 个测试）
- [x] Task 003: SQLite Schema（13 张表、aiosqlite 异步连接、WAL 模式、26 个测试）
- [x] Task 004: Repository 层（11 个 Repository、JSON 序列化、版本链、51 个测试）
- [x] Task 005: Genre Profile 系统（xuanhuan/urban/scifi、加载器、36 个测试）
- [x] Task 006: CreativeModeProfile 系统（webnovel/literary/hybrid、注册表、38 个测试）
- [x] Task 007: CLI 创建项目（create-project 8 步向导、list-projects、6 个测试）

### Phase 2 — Agent 能力层
- [x] Task 017: Quality Utils（AI 腔/疲劳词/钩子/段落节奏/数值验证、77 个测试）
- [x] Task 008: GoalPlanner Agent（LLM Client + 章节目标制定、32 个测试）
- [x] Task 009: CreativeDirector Agent（CreativeBrief 生成 + 张力地图 + 禁忌清单、23 个测试）
- [x] Task 010: ContextManager Agent（上下文包组装 + Token 预算裁剪、36 个测试）
- [x] Task 011: Writer Agent（章节正文生成 + Scene 分割 + 版本保存、37 个测试）
- [x] Task 012: RuleAuditor Agent（纯代码规则检测 + Quality Utils 复用 + 综合评分、29 个测试）
- [x] Task 013: LLMAuditor Agent（LLM 语义审查 12 维度 + JSON 解析 + 综合评分、33 个测试）

## 待开始


- [ ] Task 012: RuleAuditor Agent
- [ ] Task 013: LLMAuditor Agent
- [ ] Task 014: LiteraryAuditor Agent
- [ ] Task 015: RevisionHandler
- [ ] Task 016: SettlementExtractor
- [ ] Task 018: Craft Card Prompts
- [ ] Task 019: LangGraph 编排 + SummaryWriter
- [ ] 集成测试 + 评测集

## 阻塞项

- 无

## 最近变更

- 2026-05-24: Task 013 LLMAuditor Agent 完成（LLM 语义审查 12 维度 + 公共 JSON 解析工具 llm/parsing.py + Prompt 模板 + 字段验证回退 + 正文截断、33 个测试全部通过、ruff 0 errors、总测试 469 passed）
- 2026-05-24: Task 012 RuleAuditor Agent 完成（纯代码规则检测 + 复用 Quality Utils 5 个工具 + 综合评分 0-10 + 摘要生成、29 个测试全部通过、ruff 0 errors、总测试 436 passed）
- 2026-05-24: Task 011 Writer Agent 完成（章节正文生成 + Prompt 渲染 + Scene 分割 + 字数统计 + 版本保存 + ChapterHead 更新、prompts/writer.md 模板、37 个测试全部通过、ruff 0 errors、总测试 407 passed）
- 2026-05-24: Task 010 ContextManager Agent 完成（ContextPackage 组装 + TokenEstimator tiktoken/回退 + BudgetPruner 按优先级裁剪、SummaryRepository + CharacterStateRepository 新增、36 个测试全部通过、ruff 0 errors、总测试 370 passed）
- 2026-05-24: Task 009 CreativeDirector Agent 完成（CreativeBrief 生成、张力地图 required_tensions + 禁忌 forbidden_patterns + 裂隙 allowed_fissures、张力类型验证、forbidden_patterns 保底填充、prompts/creative_director.md 模板、23 个测试全部通过、ruff 0 errors、总测试 334 passed）
- 2026-05-24: Task 008 GoalPlanner Agent 完成（LLM Client 基础设施 get_llm/call_llm + retry_with_backoff、GoalPlanner define_chapter_goal、prompts/goal_planner.md 模板、JSON 提取/解析/字段修正、32 个测试全部通过、ruff 0 errors、总测试 311 passed）
- 2026-05-24: Task 017 Quality Utils 完成（5 个检测工具 + 77 个 utils 测试、总测试 279 passed）
- 2026-05-24: Task 007 CLI 创建项目完成（8 步交互向导、6 个测试）
- 2026-05-24: Task 006 CreativeModeProfile 系统完成（38 个测试）
- 2026-05-24: Task 005 Genre Profile 系统完成（36 个测试）
- 2026-05-24: Task 004 Repository 层完成（51 个测试）
- 2026-05-24: Task 003 SQLite Schema 完成（26 个测试）
- 2026-05-24: Task 002 Pydantic 数据模型完成（68 个测试）
