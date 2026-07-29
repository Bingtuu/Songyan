# Songyan（松烟）V1.0 开发技术方案 V2（简短版）

> 基于 design_docs_v2 + dev_design_v1_review 综合对齐版本。确认方向后扩充为完整实施文档。

---

## 1. 项目定位与验证目标

**Songyan** 是一个面向长篇中文小说创作的多 Agent AI 生产系统。V1.0 只验证一个核心假设：

> 每生成一章，系统都知道它为什么这么写、哪里可能错、改了什么、状态发生了什么变化、下一章应该继承什么。

**V1.0 验证范围**（收窄）：
- **跑通单题材、单章闭环，并证明系统能通过配置切换创作模式**
- **必交付**：xuanhuan genre profile（完整）+ webnovel/hybrid mode profile（2 种模式）+ 全部 10 个节点 + SQLite + 版本链 + 快照表 + 3 个种子项目评测
- **预置但不验收**：urban/scifi genre profile（基础配置）、literary mode profile（初版配置，不跑评测）
- **V1.1 补齐**：urban/scifi 完整评测、literary mode 完整评测 + PolyphonyPlanner

---

## 2. 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| Python | 3.11+ | 异步优先 async/await |
| Pydantic | v2 | 所有数据模型，严格类型校验 |
| LangGraph | >=0.2 | 工作流编排 |
| LangChain | >=0.3 | LLM 接口 |
| litellm | latest | 多模型统一接口（默认 DeepSeek-chat，通过环境变量配置，不硬编码） |
| SQLite | 内置 | V1.0 唯一长期事实源 |
| Click | latest | CLI 框架 |
| structlog | latest | 结构化日志 |
| tiktoken | latest | Token 计数 |
| pytest | +pytest-asyncio | 测试框架 |

**V1.0 不做**：Web UI、PostgreSQL/Qdrant/Redis、Celery、本地模型（vLLM/Ollama）、多租户、复杂权限、Jinja2 模板引擎（Prompt 直接用 `prompts/*.md` + Python 字符串拼接）。

---

## 3. 核心架构：八层质量防线

```
Layer 1: CreativeModeProfile（创作模式选择）     — 网文 or 严肃文学 or 混合
Layer 2: CreativeDirector（创作意图与张力地图）   — 写前定方向
Layer 3: Genre Profile（题材规则约束）            — 玄幻有玄幻的规矩
Layer 4: 写作工艺层 Prompt（文学质量约束）        — 黄金开篇、ShowDon'tTell 等
Layer 5: Writer Agent（创作执行）                — AI 动笔
Layer 6: Reviewer 双层审查                        — RuleAuditor(代码) + LLMAuditor(语义)
Layer 7: LiteraryAuditor（文学性诊断）            — 防"流畅但平庸"
Layer 8: 人工确认（最终门控）                     — accept / edit / reject / back
```

**数据铁律**：SQLite 是唯一长期事实源。LangGraph state 只存 ID，不存完整业务对象。

---

## 4. 节点分工与流程

### 4.1 10 个节点一览

| 节点 | 类型 | 核心职责 | 不做什么 | 温度 |
|------|------|----------|----------|------|
| **GoalPlanner** | LLM Agent | 项目设定收集（8 步向导）、章节目标制定 | 不写正文、不做结算、不输出风格约束 | 0.7 |
| **CreativeDirector** | LLM Agent | 写前生成本章创作意图 + 张力地图 + 禁忌清单 | **不得新增硬剧情事件**、不直接写正文 | 0.7 |
| **ContextManager** | Service | 加载 Genre/Mode Profile、按 Token 预算组装上下文包 | 不做生成、不做审查 | — |
| **Writer** | LLM Agent | 按场景生成正文（受全部约束层约束） | 不做审查、不修改设定 | 0.7 |
| **RuleAuditor** | 代码工具 | 代码层规则检测（AI 腔/疲劳词/段落/首屏/字数） | 不做语义判断 | — |
| **LLMAuditor** | LLM Agent | LLM 语义审查（角色/节奏/对话/设定一致性） | 不做代码检测 | 0.3 |
| **ReviewMerger** | 轻量合并 | 合并 RuleAuditResult + LLMAuditResult → MergedReviewReport | 不调用 LLM | < 10ms |
| **LiteraryAuditor** | LLM Agent | 文学性诊断（人物工具化/概念空转/裂隙） | 不阻塞 accept、不修改正文 | 0.3 |
| **RevisionHandler** | LLM Agent | 按 issue 局部 patch 修订（最多 2 轮） | 不整章重写 | 0.3 |
| **SettlementExtractor** | LLM+代码 | 状态结算提取 + 代码验证 + 更新 DB | 不写摘要 | 0.3 |

**轻量服务**（非独立 Agent）：

| 服务 | 类型 | 职责 |
|------|------|------|
| **SummaryWriter** | LLM 轻量调用 | 基于 accepted version + StateSettlement 生成结构化摘要，写入 `summaries` 表 |

### 4.2 修正后的工作流顺序

```
GoalPlanner ──▶ CreativeDirector ──▶ ContextManager ──▶ Writer
                                                          |
                                                          ▼
                                                ┌──────────────────┐
                                                │   RuleAuditor    │  < 200ms
                                                └────────┬─────────┘
                                                         │
                                                         ▼
                                                ┌──────────────────┐
                                                │   LLMAuditor     │  ~30s
                                                └────────┬─────────┘
                                                         │
                                                         ▼
                                                ┌──────────────────┐
                                                │  ReviewMerger    │  < 10ms
                                                │ MergedReviewReport│
                                                └────────┬─────────┘
                                                         │
                                                         ▼
                                                LiteraryAuditor（诊断）
                                                         │
                              ┌──────────────────────────┼──────────────────────────┐
                              ▼                          ▼                          ▼
                        无 critical/major          RevisionHandler               HumanConfirm
                              |                    （局部 patch，最多 2 轮）      accept → Settlement
                              |                           |                    edit / reject / back
                              └───────────────────────────┘
                                                         |
                                                         ▼
                                              SettlementExtractor
                                                         |
                                                         ▼
                                                 SummaryWriter
                                                         |
                                                         ▼
                                                       done
```

**关键顺序约束**：
- SettlementExtractor **仅在 accept 后执行**，edit/reject/back 不触发
- SummaryWriter 在 SettlementExtractor 完成后执行，基于 accepted 正文 + settlement 结果生成摘要
- ReviewMerger 为纯内存合并，不调用 LLM

### 4.3 边界明确：GoalPlanner vs CreativeDirector

| Agent | 回答什么问题 | 不做什么 |
|-------|-------------|----------|
| **GoalPlanner** | "本章要发生什么"——硬剧情事件（1-3 个关键事件、情感走向、字数目标、章节类型） | 不回答"怎么写"、不输出风格约束 |
| **CreativeDirector** | "这章应该怎么产生张力、避免什么惯性"——创作意图、张力地图、禁忌清单、允许裂隙 | **不得新增硬剧情事件**，只能基于 ChapterGoal 的 target_events 推导张力。若发现张力不足，标记 `tension_gap: true` 供人工判断 |

### 4.4 关键输出物

- **ChapterGoal**：章节目标（事件、情感弧、钩子、字数、章节类型）
- **CreativeBrief**：创作意图 + required_tensions + forbidden_patterns + allowed_fissures + style_constraints + reader_contract
- **ContextPackage**：分区上下文包（硬约束/角色状态/最近剧情/伏笔/软参考/题材规则/模式规则/创作意图层）
- **MergedReviewReport**：RuleAuditor + LLMAuditor 合并审查报告（统一 issue 列表）
- **LiteraryAuditResult**：文学性诊断（observations，含 protected_elements）
- **StateSettlement**：角色状态变更 / 新设定 / 伏笔操作 / 数值变更
- **ChapterSummary**：结构化摘要（plot_summary, key_events, characters_appeared, emotional_tone）

---

## 5. 四大关键机制

### 5.1 CreativeModeProfile（创作模式系统）

同一套代码，不同配置，服务不同创作场景。新增模式只需一个 JSON 配置文件，无需改 Agent 代码。

```python
class CreativeModeProfile(BaseModel):
    id: str
    name: str
    enabled_nodes: dict[str, list[str]]           # 各阶段启用的节点
    audit_weights: dict[str, float]               # 审查维度权重
    active_audit_dimensions: list[str]            # 启用的审查维度
    blocking_dimensions: list[str]                # 哪些维度可阻塞入库
    revision_policy: RevisionPolicy               # 修订策略
    literary_policy: LiteraryPolicy               # 文学性诊断策略
    context_policy: ContextPolicy                 # 上下文裁剪策略
    tolerance: dict[str, float]                   # 容错阈值
    success_metrics: dict[str, float]             # 成功指标

class RevisionPolicy(BaseModel):
    priority_dimensions: list[str]                # 优先修复的维度
    protected_dimensions: list[str]               # 保护的维度（不自动修）
    max_auto_rounds: int = 2

class LiteraryPolicy(BaseModel):
    protected_observation_types: list[str] = ["valuable_fissure"]
    highlight_observation_types: list[str] = []   # 人工确认时高亮
```

| 模式 | 核心差异 | blocking_dimensions | 文学性策略 |
|------|----------|---------------------|-----------|
| **网文** | 节奏/爽点/钩子权重高，容忍一定套路 | world_consistency, character_behavior, timeline, genre_numerical | protected: valuable_fissure |
| **严肃文学** | 人物自治/概念落地/裂隙保留权重高 | world_consistency, character_behavior, timeline | protected: valuable_fissure；highlight: conceptual_idling, character_autonomy |
| **混合** | 平衡两者 | world_consistency, character_behavior, timeline, genre_numerical | protected: valuable_fissure |

### 5.2 双层审查（RuleAuditor + LLMAuditor + ReviewMerger）

| 维度 | 执行方 | 方式 | 耗时 |
|------|--------|------|------|
| AI 腔、疲劳词、段落节奏、字数、数值公式 | RuleAuditor | 代码规则（正则/统计） | < 200ms |
| 首屏钩子（差的特征检测：纯环境描写/无动作对话） | RuleAuditor | 代码规则 | < 200ms |
| 设定一致性、角色行为、叙事节奏、对话区分度、信息倾倒、ShowDon'tTell | LLMAuditor | LLM 语义理解 | ~30s |
| 首屏钩子（语义吸引力判断） | LLMAuditor | LLM 语义理解 | ~30s |
| 合并报告 | ReviewMerger | 纯内存合并 | < 10ms |

- RuleAuditor 检测"差的钩子特征"（纯环境描写、无人称、无动作动词）→ 直接报 major
- LLMAuditor 判断"是否真的有吸引力事件" → 综合评分
- ReviewMerger 合并为统一的 `narrative_hook` 维度
- RuleAuditor 大量 critical 时可跳过 LLMAuditor（快速失败）

### 5.3 LiteraryAuditor 分级影响

| observation_type | 网文模式 | 严肃文学模式 | 混合模式 |
|------------------|----------|-------------|----------|
| **valuable_fissure** | protected（RevisionHandler 必须排除） | protected | protected |
| **conceptual_idling** | notice（不阻塞） | suggestion（人工确认时高亮） | notice |
| **character_autonomy** | notice（不阻塞） | suggestion（人工确认时高亮） | notice |
| **excessive_smoothing** | suggestion | suggestion | suggestion |

- `valuable_fissure` 自动输出 `protected_elements`（文本片段）
- RevisionHandler 筛选 patchable_issues 时必须排除 `protected_elements` 范围内的文本
- 默认不阻塞 accept，但 protected 的内容不可被自动修订

### 5.4 状态结算（SettlementExtractor）+ 摘要生成（SummaryWriter）

**仅在 HumanConfirm accept 后执行**：

1. **SettlementExtractor**：
   - 角色状态变更 → `character_states` **INSERT 新快照，永远不 UPDATE**
   - 新设定登记 → `setting_snapshots`（带 `setting_key` 追踪演变）
   - 伏笔操作 → `foreshadowings`（带 `source_version_id`）
   - 数值变更 → `numerical_ledgers`（代码验证 `closing_value == opening + 增量 - 消耗`）
   - 结算失败 → 标记 `needs_human_review`，不阻塞流程

2. **SummaryWriter**（轻量函数）：
   - 基于 accepted 正文 + settlement 结果生成结构化摘要
   - 写入 `summaries` 表（plot_summary, key_events, characters_appeared, emotional_tone）
   - 供下一章 ContextManager 的 RecentPlot 使用

---

## 6. 数据访问边界与 Pipeline Plugin 协议（轻量版）

### 6.1 数据访问分层

```
Agent 层（只读 RunContext，返回 NodeResult）
  → Orchestrator 层（LangGraph，协调节点执行）
  → Service 层（处理 NodeResult，决定写入）
  → Repository 层（唯一 DB 写入入口）
  → SQLite（唯一事实源）
```

**技术约束**：
- Agent 层不直接拿 DB connection
- 写操作集中在 Service 层 / UnitOfWork
- `chapter_versions`、`character_states`、`review_reports` 都通过专门 repository 创建
- 对 accepted version、current head、settlement 写入使用**事务**
- Repository 层记录所有写入操作日志（用于审计和调试）

### 6.2 PipelineNode Protocol（轻量版）

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class PipelineNode(Protocol):
    node_id: str
    stage: PipelineStage
    enabled_by_default: bool = True
    
    async def run(self, ctx: RunContext) -> NodeResult: ...

class RunContext(BaseModel):
    """只读上下文——Agent 不能直接访问数据库"""
    project_id: str
    chapter_number: int
    mode_id: str
    current_version_id: str | None
    chapter_goal: ChapterGoal | None = None
    creative_brief: CreativeBrief | None = None
    # ... 其他必要快照（从 SQLite 加载）

class NodeResult(BaseModel):
    """节点运行结果——由 orchestrator 统一处理"""
    node_id: str
    success: bool
    output: dict = Field(default_factory=dict)
    db_operations: list[DBOperation] = []         # 数据库操作请求（不直接执行）
    next_stage: PipelineStage | None = None

class DBOperation(BaseModel):
    operation: Literal["insert", "update"]
    table: str
    data: dict
```

**核心原则**：Agent 不直接改数据库，只返回结构化结果 → orchestrator/Service 统一写入。

---

## 7. 项目结构

```
songyan/
├── pyproject.toml, .env.example, README.md
├── AGENTS.md                     # 不可违背规则清单
├── creative_modes/               # 创作模式配置
│   ├── webnovel.json
│   ├── literary.json             # 预置但不验收
│   └── hybrid.json
├── genres/                       # 题材配置文件
│   ├── xuanhuan.json             # 完整配置，验收用
│   ├── urban.json                # 基础配置，预置
│   └── scifi.json                # 基础配置，预置
├── prompts/                      # Agent Prompt 模板（不在代码里写长字符串）
│   ├── writer.md, craft_card.md
│   ├── creative_director.md, goal_planner.md
│   ├── rule_auditor.md, llm_auditor.md, literary_auditor.md
│   ├── settlement_extractor.md
│   ├── summary_writer.md         # 章节摘要生成 Prompt
│   └── planner_settlement.md     # SettlementExtractor LLM extraction Prompt
├── src/songyan/
│   ├── cli/main.py               # CLI 入口（Click）
│   ├── db/                       # SQLite schema + repository + connection
│   ├── models/                   # Pydantic v2 数据模型
│   │   ├── creative_mode.py      # CreativeModeProfile, CreativeBrief, Tension
│   │   └── literary.py           # LiteraryObservation, LiteraryAuditResult
│   ├── agents/                   # 9 个 Agent + ReviewMerger 实现
│   │   ├── review_merger.py      # 轻量合并节点（或作为 utils 函数）
│   │   └── ...
│   ├── workflows/phase1_graph.py # LangGraph 工作流编排
│   ├── utils/                    # 质量检测工具
│   │   ├── ai_tells.py
│   │   ├── fatigue_words.py
│   │   ├── hook_checker.py
│   │   ├── paragraph_rhythm.py
│   │   ├── token_counter.py
│   │   └── numerical_validator.py # 玄幻数值公式验证
│   └── creative_modes/registry.py # CreativeModeProfile 注册表
├── tests/                        # pytest + pytest-asyncio
└── evals/runner.py               # 评测集运行器
```

---

## 8. 开发阶段规划

```
Phase 1：基础设施（Task 001-006）
  项目初始化、Pydantic 模型、SQLite schema、Repository 层
  Genre Profile 加载器 + 3 个题材配置（xuanhuan 完整，urban/scifi 基础）
  CreativeModeProfile 注册表 + 3 个模式配置（webnovel/hybrid 验收，literary 预置）

Phase 2：写前管线 + 写作基础设施（Task 007-011 + 017-018）
  CLI 创建项目（8 步向导，含模式选择）
  GoalPlanner（章节目标制定）
  CreativeDirector（创作意图+张力地图）
  ContextManager（Token 预算 + 上下文包组装）
  Writer Agent（按场景生成，四层 Prompt 注入）
  Quality Utils（AI 腔/疲劳词/钩子/段落/Token 检测工具）
  Craft Card Prompts（写作工艺层 Prompt 加载）

Phase 3：审查与修订（Task 012-015）
  RuleAuditor（代码检测，< 200ms）
  LLMAuditor（12 维度语义审查）
  ReviewMerger（合并报告，< 10ms）
  LiteraryAuditor（文学性诊断，不阻塞 accept）
  RevisionHandler（issue-driven patch，保护 protected_elements，最多 2 轮）

Phase 4：结算与闭环（Task 016 + 019 + SummaryWriter）
  SettlementExtractor（状态提取 + 代码验证 + INSERT 快照）
  SummaryWriter（轻量函数，生成结构化摘要）
  HumanConfirm CLI（accept/edit/reject/back，edit 调用 $EDITOR）
  LangGraph 工作流编排（修正后的顺序）
  集成测试 + 评测集
```

---

## 9. 最小可运行切片（V1.0 MVP）

**先跑通 vertical slice，再逐步叠加**：

```
1. 创建项目（xuanhuan + webnovel）
2. 输入一章人工种子
3. GoalPlanner 制定 ChapterGoal
4. CreativeDirector 生成 CreativeBrief（不得新增事件）
5. ContextManager 组装 ContextPackage
6. Writer 生成下一章
7. RuleAuditor 规则检测（< 200ms）
8. LLMAuditor 语义审查
9. ReviewMerger 合并报告
10. HumanConfirm accept
11. SettlementExtractor 状态结算
12. SummaryWriter 生成摘要
13. 验证下一章上下文正确继承
```

**此切片跑通后，再叠加**：
- LiteraryAuditor 文学性诊断
- RevisionHandler issue-driven 修订（最多 2 轮）
- hybrid mode 切换验证
- 完整 3 种子项目评测

---

## 10. V1.0 验收指标（客观可测量）

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| 设定硬错误数 | 0 | critical world_consistency = 0 |
| 人工大改比例 | < 30% | 需人工大幅修改的章节比例 |
| 审查漏检率 | < 35% | 人工发现但 AI 没发现的问题比例（V1.1 降到 < 20%） |
| 修订后新问题数 | 0 | 第二轮审查新问题数 = 0 |
| AI 腔规则命中数 | < 2 处/章 | RuleAuditor 检测数 |
| 疲劳词命中数 | < 3 处/章 | RuleAuditor 检测数 |
| 首屏钩子达标率 | 100% | 前 300 字有吸引力事件 |
| 章末钩子达标率 | 100% | 最后 200 字有有效悬念 |
| 状态结算字段准确率 | > 90% | old_value 与 DB 一致率 |
| 状态结算 setting_key 准确率 | > 90% | setting_key 唯一 + source_quote 存在 |
| 概念空转段落数 | 网文/混合: 0 | LiteraryAuditor 检测数 |
| 概念空转段落数 | 严肃文学: 允许人工标记"有意保留" | 不自动阻塞 |
| 人物语言区分度 | > 70% | 人工评分 > 7 的章节比例 |
| AI 与人工金标一致率 | > 70% | critical/major 重叠率 |

**移除指标**：overall_score > 6.5/10（太主观，容易自欺）。

---

## 11. 关键约束（不可违背）

1. **SQLite 唯一事实源**：LangGraph state 只存 ID，不存正文/报告/档案。
2. **版本不覆盖**：每次生成/修订都创建新的 `chapter_versions` 记录。
3. **character_states 快照表**：永远 INSERT 新记录，禁止 UPDATE。
4. **critical/major 必须有 evidence_quote**：无证据的 issue 不进入自动修订。
5. **自动修订最多 2 轮**：第 2 轮仍有问题 → 上报人工。
6. **LiteraryAuditor 默认不阻塞 accept**：但 `valuable_fissure` 自动输出 `protected_elements`，RevisionHandler 必须排除。
7. **CreativeDirector 不得新增硬剧情事件**：只能基于 ChapterGoal 推导张力，不足时标记 `tension_gap`。
8. **SettlementExtractor 仅在 accept 后执行**：edit/reject/back 不触发结算和摘要。
9. **Agent 不直接改数据库**：返回 `NodeResult` → orchestrator/Service 统一写入。
10. **新增模式零代码**：CreativeModeProfile 新增模式只需 JSON 配置。
11. **Prompt 直接放在 `prompts/*.md`**：不用 Jinja2，V1.0 不需要模板引擎复杂度。

---

## 12. 已确认的技术决策

| 问题 | 确认答案 |
|------|----------|
| **LLM 选型** | 默认 DeepSeek-chat（通过 litellm 环境变量配置），不硬编码。V1.0 不实现多模型路由。 |
| **评测集执行** | 先 mock 数据跑通流程（Phase 4 前期），再用真实题材跑评测（Phase 4 后期）。3 个种子项目评测在开发中后期准备。 |
| **CLI 交互深度** | HumanConfirm 做简单选择（a/e/r/b），edit 调用系统默认编辑器（`$EDITOR` 环境变量）。不嵌入复杂编辑器。 |
| **Prompt 管理方式** | 直接用 `prompts/*.md` 文件 + Python 字符串拼接。Jinja2 属于"可选但非必须"，V1.0 不需要。 |
| **上下文 Token 预算** | 默认 32K，支持手动调整到 48K/64K。通过 `ContextBudget.total_budget` 配置。不需要动态检测模型窗口大小。 |
| **开发节奏** | 独立模块可并行（如 RuleAuditor 工具函数与 GoalPlanner 可同时开发），LangGraph 编排必须在所有 Agent 跑通后串行接入。Phase 1-2 内部可并行，Phase 3-4 串行。 |

---

> **下一步**：确认 V2 方向后，扩充为包含每个 Task 的详细接口定义、数据库 schema、Prompt 模板、测试策略的完整实施文档。
