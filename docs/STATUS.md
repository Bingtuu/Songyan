# Songyan 项目状态板

> 每次 AI 接手任务前必须先读此文件。
> 每次任务完成后必须更新此文件。

---

## 当前阶段

Phase 2 — Agent 能力层 **已完成**，准备进入 Phase 3

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
- [x] Task 008: GoalPlanner Agent（LLM Client + 章节目标制定、32 个测试）
- [x] Task 009: CreativeDirector Agent（CreativeBrief 生成 + 张力地图 + 禁忌清单、23 个测试）
- [x] Task 010: ContextManager Agent（上下文包组装 + Token 预算裁剪、36 个测试）
- [x] Task 011: Writer Agent（章节正文生成 + Scene 分割 + 版本保存、37 个测试）
- [x] Task 012: RuleAuditor Agent（纯代码规则检测 + Quality Utils 复用 + 综合评分、29 个测试）
- [x] Task 013: LLMAuditor Agent（LLM 语义审查 12 维度 + JSON 解析 + 综合评分、33 个测试）
- [x] Task 014: LiteraryAuditor Agent（文学性诊断 7 类观察 + 4 维度评分、29 个测试）
- [x] Task 015: RevisionHandler Agent（issue-driven patch 修订 + 保护 valuable_fissure、38 个测试）
- [x] Task 016: SettlementExtractor Agent（状态结算提取 + 代码验证 + INSERT 快照、40 个测试）
- [x] Task 017: Quality Utils（AI 腔/疲劳词/钩子/段落节奏/数值验证、78 个测试）

## 待开始

### Phase 3 — 编排层 + Prompt 工程
- [ ] Task 018: Craft Card Prompts（工艺卡 Prompt 精调、版本化、A/B 测试支持）
- [ ] Task 019: LangGraph 编排 + SummaryWriter（状态机 + Agent 编排 + 章节摘要）

### Phase 4 — 评测与优化
- [ ] 集成测试 + 评测集（端到端单章闭环验证）

## 阻塞项

- 无

## 最近变更

- 2026-05-25: PR #2 合并 — Task 014/015/016 从 `task_14_0525` 分支合并到 `main`
- 2026-05-25: Task 017 修复 — DONE 文档测试数量修正 + 集成性能测试（78 passed）
- 2026-05-24: Task 013 LLMAuditor Agent 完成（33 个测试全部通过、总测试 469 passed）
- 2026-05-24: Task 012 RuleAuditor Agent 完成（29 个测试全部通过、总测试 436 passed）
- 2026-05-24: Task 011 Writer Agent 完成（37 个测试全部通过、总测试 407 passed）
- 2026-05-24: Task 010 ContextManager Agent 完成（36 个测试全部通过、总测试 370 passed）
- 2026-05-24: Task 009 CreativeDirector Agent 完成（23 个测试全部通过、总测试 334 passed）
- 2026-05-24: Task 008 GoalPlanner Agent 完成（32 个测试全部通过、总测试 311 passed）
- 2026-05-24: Task 017 Quality Utils 完成（5 个检测工具 + 78 个 utils 测试）
