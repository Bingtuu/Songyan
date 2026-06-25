<div align="center">
  <img src="docs/icon/logo02.png" alt="Songyan logo" width="160" />

  <h1>Songyan（松烟）</h1>

  <p><strong>多 Agent 中文小说写作系统</strong></p>
  <p><em>松烟入墨，字句成锋。</em></p>
  <p>面向长篇中文小说创作的多 Agent AI 生产系统，基于 LangGraph 多 Agent 协作架构。</p>
</div>

## 项目状态

**V5.0 — Context Diet 2.0 智能遗忘架构已完成**

目标：通过 TemporalCompressor + CharacterFocalDecay + SettingEvaporator + BudgetHardCeiling 四组件协同，控制信息密度，支撑 150+ 章稳定生成。Task 101~120 已完成 Context Diet 2.0 核心组件、流式验证基础设施、评分与收敛护栏、活跃信息池控制、工作流/事实源/Context/Prompt/QualityGate/Settlement 修复、Ch111-Ch150 分段验证、DG-2 风险窗口复验、health_low 治理、报告/wrapper 加固和 V5.0 Final Acceptance。

当前最终口径以 `tasks/V5-README.md` 与 `docs/STATUS.md` 为准：**V5.0 工程验收通过，P0/P1 风险为 0，全量回归 1776 passed，lint 通过**。**Task 121q full single-run `run-a2bed648` 已完成 Ch1-Ch150 150/150 全部成功**，一次性单命令最终证据已获取。Task 121r 已完成 Prompt / 正文质量清理（Writer 1.1.0 + CreativeDirector 1.0.5 + RuleAuditor 格式检测）。Task 122a/122b 已完成系统性测试矩阵（动态阈值单元测试 + Pipeline 集成测试）。Task 122c（E2E 窗口补全）和 Task 122d（150 章压力测试）为当前待启动项。

### 版本概览

| 版本 | 里程碑 | 验证范围 | 状态 |
|------|--------|---------|:----:|
| V1.x | M1~M5 | 单章闭环验证 | 已完成 |
| V2.x | M6~M15 | 长篇支撑能力（RAG / Punch / 一致性）| 已完成 |
| V3.x | M16~M27 | Ch1~Ch70 稳定长跑 | 已完成 |
| V4.0 | M28~M42 | Ch1~Ch50 极限优化（81.6% 达标率）| 已完成 |
| **V5.0** | **M43~M71** | **Context Diet 2.0 → Ch150 全自动 + Final Acceptance** | **已完成** |
| **V5.1** | **M72~M75** | **Prompt 质量清理 + 系统性测试矩阵 + 150 章压力测试** | **预研中** |

### 当前关键指标

| 指标 | 数值 |
|------|------|
| 最近回归测试 | **1776 passed, 2 skipped, 1 xfailed, 0 xpassed, 2 warnings** (`pytest tests/ -q`) |
| V5.0 当前 Task | **Task 120 已完成；Task 121a-121r 全部完成；Pass 14-18 V5.1 Code Review 已完成，8 项缺口全部修复（TS-01/02/03/08、PR-05、ST-03、AG-04、TS-10）；Task 122a/122b 已完成；Task 122c 待补充（Ch40-Ch50 / Ch100-Ch110）；Task 122d 待启动（150 章压力测试）** |
| 前置状态 | **Task 115-121r 全部完成；DG-2 风险窗口已关闭；health_low 已分级追踪；报告/wrapper 已加固；0.82 阈值已动态化并验证；Prompt 质量清理已完成** |
| 当前结论 | **V5.0 工程验收通过：P0/P1 风险为 0；Ch111-Ch150 40/40 成功；Task 121q full single-run `run-a2bed648` Ch1-Ch150 150/150 全部成功，ContextEmergency 0 次，AutoHalt 0 次，failed 0 次，无间隙** |
| 当前 lint | **`ruff check src/ tests/` 已通过** |
| Task 110e 实跑 | **Ch80-Ch96 17/17 成功，QG 100%，coherence_major 0/17** |
| V4.0 最终达标率 | Task 099: Ch2-Ch50 **81.6%** |
| V4.x 归档 | `archive/v4/`（报告 + 任务 + 验证数据）|

测试口径说明：`1 xfailed` 为已知非阻断项；`0 xpassed`（Pass 14-18 已修复）；2 warnings 为 transformers DeprecationWarning（与项目代码无关）。新增 25 个测试，零回归。

### V5.0 核心决策

**Context-on-Demand（检索架构）→ Context Diet 2.0（信息节食）**

```
V4.0: ContextManager 预组装大包 → BudgetPruner 裁剪 → 仍持续增长
V5.0: TemporalCompressor 分层摘要 + CharacterFocalDecay 角色衰减
       + SettingEvaporator 设定蒸发 + BudgetHardCeiling 硬天花板
       → 信息密度 O(log n) → 支撑 150+ 章
```

**四组件协同**:

| 组件 | 功能 | 解决什么问题 |
|------|------|-------------|
| **TemporalCompressor** | 金字塔分层摘要（最近 5 章详细 + 弧摘要 + 卷摘要）| 历史信息 O(n) → O(log n) |
| **CharacterFocalDecay** | 角色档案按未出场章数衰减（完整→精简→符号→不加载）| 活跃角色池膨胀 |
| **SettingEvaporator** | 设定按 resolve_confidence 蒸发 + embedding 合并 | 设定/伏笔累积 |
| **BudgetHardCeiling** | fullness_factor 0.7 + ContextEmergency | 绝对预算天花板 |

---

## 1. 设计方式、逻辑和结构

### 1.1 核心设计哲学

V1.0 唯一要验证的假设：

> **"每生成一章，系统都知道它为什么这么写、哪里可能错、改了什么、状态发生了什么变化、下一章应该继承什么。"**

这不是一个"一键写小说"的工具，而是一个**可控生产、审查、修订、沉淀上下文**的工程闭环。质量不是 Writer 一个人的事，而是贯穿多层防线的共同结果：

```
LAYER 1: CreativeModeProfile（创作模式选择）
LAYER 2: CreativeDirector（创作意图与张力地图）
LAYER 3: Genre Profile（题材规则约束）
LAYER 4: 写作工艺层 Prompt（文学质量约束）
LAYER 5: Writer Agent（创作执行）
LAYER 6: Reviewer 双层审查（RuleAuditor + LLMAuditor）
LAYER 7: LiteraryAuditor（文学性诊断，不阻塞）
LAYER 8: 截断重写（2 轮未收敛时整章重写）
LAYER 9: 人工确认（最终门控）
```

### 1.2 系统架构

```text
                              用户输入 (CLI)
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Songyan 单章闭环流水线                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌─────────────────────────────────────────────────────────────────┐     │
│    │              LangGraph State（只存 ID，不存正文）                  │     │
│    │   project_id / version_id / report_id / brief_id / goal_id...   │     │
│    └─────────────────────────────────────────────────────────────────┘     │
│                                    │                                         │
│   GoalPlanner → CreativeDirector → ContextManager → Writer                 │
│        │             │                │            │                        │
│        ▼             ▼                ▼            ▼                        │
│    ChapterGoal   CreativeBrief   ContextPackage  ChapterVersion            │
│                                                                   │        │
│                    ┌──────────────────────────────────────────────┘        │
│                    ▼                                            ▼           │
│            RuleAuditor（代码）                         LLMAuditor（语义）    │
│                    │                                            │           │
│                    └──────────────────┬─────────────────────────┘           │
│                                       ▼                                     │
│                                 ReviewMerger                                │
│                            MergedReviewReport                               │
│                                       │                                     │
│                                       ▼                                     │
│                                   QualityGate                               │
│                              (质量门 + 降级接受)                              │
│                                       │                                     │
│              ┌────────────────────────┼────────────────────────┐           │
│              ▼                        ▼                        ▼           │
│      LiteraryAuditor          RevisionHandler    [Rewrite]   HumanConfirm  │
│      （诊断，不阻塞）          （patch，最多 2 轮） （整章重写） accept/edit/reject│
│                                       │                        │           │
│                                       └────────────────────────┘           │
│                                                              │              │
│                                                 SettlementExtractor          │
│                                          + SettingEvaporator (V5.0)          │
│                                          + SummaryWriter                     │
│                                                              │              │
│                                                    SQLite（唯一事实源）       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 V5.0 Context Diet 2.0 架构

```
V5.0: Context Diet 2.0

┌─────────────────────────────────────────────────────────────┐
│                     ContextPackage 组装                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │ TemporalCompressor │ │ CharacterFocalDecay │ │ SettingEvaporator   │   │
│  │  (金字塔摘要)        │ │  (角色衰减)          │ │  (设定蒸发)          │   │
│  └──────┬──────┘ └──────┬──────┘ └──────────┬──────────┘   │
│         │               │                    │              │
│         └───────────────┼────────────────────┘              │
│                         ▼                                   │
│              ┌─────────────────┐                            │
│              │ BudgetHardCeiling│  ← 预算硬天花板 + ContextEmergency │
│              │  (V5.0 新增)    │                            │
│              └────────┬────────┘                            │
└───────────────────────┼─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐
   │ Writer  │   │ Auditor  │   │ Revision │
   │(精简Ctx)│   │(精简Ctx) │   │(精简Ctx) │
   └─────────┘   └──────────┘   └──────────┘
```

### 1.4 关键设计原则

- **Agent 代表"可替换能力"，不是"人"**：同一套底层，换不同配置，就能服务长篇网文、类型小说、严肃文学。
- **数据先行，指标说话**：每个功能必须有明确的评测指标，"设定硬错误数 = 0""AI 腔规则命中数 < 2"。
- **状态闭环**：每章完成后完成完整的状态结算——角色状态、设定快照、伏笔追踪、数值账本全部更新。
- **智能遗忘**：V5.0 不是记住更多，而是**更聪明地遗忘**——分层压缩 + 角色衰减 + 设定蒸发。
- **能删则删，晚点再加**：如果某个功能不是验证当前假设所必需的，就不做。

### 1.5 项目结构

```text
songyan/
├── creative_modes/          # 创作模式配置（webnovel / literary / hybrid）
├── genres/                  # 题材配置（7 个：scifi / xuanhuan / urban / ...）
├── prompts/                 # Agent Prompt 工艺卡（YAML，版本化管理）
│   └── cards/               # _manifest.yaml + vX.Y.Z.yaml
├── src/songyan/
│   ├── cli/                 # CLI 命令（Click）
│   ├── db/                  # SQLite Schema + Repository + 迁移
│   ├── models/              # Pydantic v2 数据模型（40+ 个）
│   ├── agents/              # Agent 实现（13 个 + V5.0 新增）
│   │   ├── goal_planner.py
│   │   ├── creative_director/
│   │   ├── context_manager/           # V5.0: TemporalCompressor + FocalDecay
│   │   ├── writer.py
│   │   ├── rule_auditor.py
│   │   ├── llm_auditor.py
│   │   ├── literary_auditor.py
│   │   ├── revision_handler/          # patch 引擎 + diff
│   │   ├── settlement_extractor/      # 结算 + source_quote 去噪
│   │   ├── summary_writer.py
│   │   ├── continuity_auditor/        # 跨章一致性
│   │   └── setting_evaporator.py      # V5.0 新增：设定蒸发
│   ├── workflows/           # LangGraph 工作流编排
│   │   ├── phase1_graph.py  # 主流程：写作 → 审查 → 修订 → 重写
│   │   ├── phase2_graph.py  # 辅助流程
│   │   ├── review_merger.py # Rule + LLM 结果轻量合并
│   │   ├── _nodes.py        # 节点函数（含 rewrite_node）
│   │   └── _helpers.py      # 上下文加载辅助
│   ├── llm/                 # LLM Client + 重试 + JSON 解析
│   ├── prompts/             # PromptLoader + 工艺卡系统
│   ├── rag/                 # RAG 子系统（chunker / embedder / retriever / vector_store）
│   ├── utils/               # 质量检测工具（PunchCheck / 疲劳词 / AI 腔 / ...）
│   ├── genres/              # Genre Profile 加载器
│   └── creative_modes/      # CreativeModeProfile 注册表
├── evals/                   # 评测集 runner + 种子项目 + 指标
├── tests/                   # pytest 测试
├── tasks/                   # Task 规格文件
├── docs/                    # 当前阶段文档
│   ├── INDEX.md
│   ├── STATUS.md
│   └── architecture/        # 工程手册 + 技术参考
├── system_prompt/           # 开发技术方案与协作规范
└── archive/                 # 归档（历史产物）
    ├── v3/                  # V3.x 完整归档（报告 + 任务 + 验证数据）
    ├── v4/                  # V4.x 完整归档（报告 + 任务 + 验证数据）
    ├── evals/               # 历史评测数据（benchmarks / reports / outputs）
    ├── tasks/               # 更早已完成任务的交接报告
    ├── projects/            # 历史项目生成物
    ├── docs/                # 历史文档与 review
    ├── prd/                 # 历史 PRD
    └── prompts/             # 旧版 Prompt 模板
```

---

## 2. 技术设计

### 2.1 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| Python | 3.11+ | 异步优先 `async/await` |
| Pydantic | v2 | 所有数据模型，严格类型校验 |
| LangGraph | >=0.2 | 工作流编排 |
| LangChain | >=0.3 | LLM 接口 |
| litellm | latest | 多模型统一接口 |
| SQLite | 内置 | V1.0 唯一长期事实源 |
| Click | latest | CLI 框架 |
| structlog | latest | 结构化日志 |
| tiktoken | latest | Token 计数 |
| pytest | +pytest-asyncio | 测试框架 |

### 2.2 数据事实源设计

**SQLite 是 V1.0 唯一的长期事实源。**

- LangGraph state 只存 ID，不存完整业务对象
- 每次生成/修订创建 chapter_versions 新记录，禁止覆盖
- 每个节点从 SQLite 加载数据，不从 state 取正文
- character_states 为快照表，永远 INSERT 新记录，禁止 UPDATE

### 2.3 版本管理

| 类型 | 说明 | 谁创建 |
|------|------|--------|
| `draft` | AI 初稿 | Writer |
| `revision` | AI 修订版 | RevisionHandler |
| `rewrite` | AI 重写版 | rewrite_node（2 轮未收敛时）|
| `accepted` | 人工确认版 | HumanConfirm |
| `edited` | 人工编辑版 | HumanConfirm |

### 2.4 审查体系

- **RuleAuditor**（代码检测）：AI 腔、疲劳词、段落长度、首屏钩子、字数统计、数值公式、**markdown 场景标题**、**短段落比例**、**元标记泄漏** + **PunchCheck**（< 200ms）
- **LLMAuditor**（语义审查）：角色行为一致性、叙事节奏、对话区分度、信息倾倒、设定一致性（12 维度）
- **LiteraryAuditor**（文学性诊断）：人物工具化、概念空转、过度平滑、有价值裂隙（不阻塞流程）
- **ContinuityAuditor**：跨章一致性审计 — orphaned / forgotten / state mismatches / overdue foreshadowings（每 3 章，非阻塞）
- **ReviewMerger**（轻量合并）：Rule + LLM 结果合并为统一报告，加权评分，**不调用 LLM**，< 10ms
- **QualityGate**（质量门控）：动态阈值（Ch1-Ch20→0.75, Ch21-Ch50→0.78, Ch51+→0.82）+ `degraded_accept` 降级回滚（score ≥ 0.70）
- **RevisionHandler**（patch 修订）：从 MergedReviewReport 提取 patchable issues，保护 valuable_fissure，最多 2 轮
- **Rewrite**（截断重写）：2 轮 revision 未收敛时，整章重写并注入 avoid-list；若 rewrite 后 score < best - 0.08 则回滚到 safe best

### 2.5 状态结算

每章 **accept 后**必须执行 SettlementExtractor + SummaryWriter；edit/reject/back **不触发** settlement：

- 角色状态更新（old_value 必须与 DB 当前值一致）
- 新设定快照（source_quote 必须在正文中存在，经过去噪过滤）
- 伏笔追踪（source_version_id 必须记录）
- 数值账本（closing_value 必须等于公式值）
- **V5.0**: SettingEvaporator 在 Settlement 后执行，自动 archive 低 confidence 设定
- **V5.1**: QG false 硬拦截 settlement — `quality_gate_passed=False` 时 settlement 被跳过，防止未通过质量门的污染数据进入事实源
- 结算完成后 SummaryWriter 生成结构化摘要

### 2.6 上下文架构演进

**V4.0 — 预组装上下文包优化**

ContextManager 按 Token 预算组装 `ContextPackage`（默认 32K）：

| 层级 | 粒度 | 典型长度 | 覆盖范围 |
|------|------|----------|----------|
| Chapter | 细粒度 | ~200 字符 | 最近 3 章 |
| Arc | 中粒度 | ~500 字符 | 每 10 章聚合 |
| Volume | 粗粒度 | ~300 字符 | 每 30 章聚合 |

超出预算时按优先级裁剪：软参考 → CreativeBrief → 最近剧情章数 → 角色详细度。硬约束不裁剪。

**V5.0 — Context Diet 2.0**

| 组件 | 功能 | 效果 |
|------|------|------|
| TemporalCompressor | 金字塔分层加载 | 历史信息 O(n) → O(log n) |
| CharacterFocalDecay | 角色档案衰减 | 活跃角色池可控 |
| SettingEvaporator | 设定语义蒸发 | active 设定数量下降 |
| **BudgetHardCeiling** | 预算硬天花板 | `budget_used > 1.0` 时触发 ContextEmergency，只保留硬约束 + 主角档案 + ChapterGoal |

---

## 3. 开发历程

### V1.x — 单章闭环验证（Task 001 ~ 026）

> 目标：验证"每生成一章，系统都知道它为什么这么写、哪里可能错、改了什么。"

| 阶段 | Task | 内容 | 状态 |
|------|------|------|:----:|
| M1 地基 | 001~007 | 项目骨架、Pydantic 模型、SQLite Schema、Repository、Genre/Mode 系统、CLI |  |
| M2 Agent 军团 | 008~017 | 13 个 Agent（GoalPlanner → Writer → 三层审查 → Revision → Settlement） |  |
| M3 编排闭环 | 018~019 | YAML 工艺卡 + LangGraph 12 节点状态机 |  |
| M4 评测基础设施 | 020-A~C | Mock E2E + 种子项目 + MetricsCollector |  |
| M5 调优与验证 | 021~026 | Prompt 三轮迭代、多题材评测、多章编排、10 章长篇验证（7.75/10）|  |

### V2.x — 长篇支撑能力（Task 027 ~ 057）

> 目标：回应 V1.x 识别的系统性问题，建立 100+ 章质量保障体系。

| 阶段 | Task | 内容 | 状态 |
|------|------|------|:----:|
| M6 基线固化 | 027 | 环境清理、评估脚本、基线报告 |  |
| M7 Punch Engine | 028 | 节奏太慢、缺爆点 |  |
| M8 人机协作 | 029 | 人工介入僵化 |  |
| M9 跨章一致性 | 030~031 | 设定遗忘、上下文膨胀 |  |
| M10 工程收尾 | 032~034 | DONE 报告、ruff、state_mismatches 验证 |  |
| M11 类型多样化 | 035~038 | Genre 框架过简、风格单一 |  |
| M12 长程调研 | 039 | 100+ 章可行性未知 → **D+B 混合架构** |  |
| M13 人类增强记忆 | 040~044 | 人类标记系统 + 建议标记 |  |
| M14 项目种子增强 | 045~047 | ProjectSetting 扩展、CLI 交互、sub_genre |  |
| M15 RAG 自动层 | 048~051 | Embedding 基准 → Chunker → Retriever → A/B 测试 |  |
| 稳定性修复 | 054~057 | RevisionHandler 截断、database locked、字数超标、死代码 |  |

### V3.x — 稳定长跑与质量跃迁（Task 058 ~ 081）

> **不新增功能，修到 70 章稳定跑通。上下文成本可控、Settlement 干净、Revision 收敛有保障。**

| 阶段 | Task | 内容 | 状态 |
|------|------|------|:----:|
| M16 监控与韧性 | 058a | `ChapterRunLog` + 指标收集 |  |
| M17 封闭验证 | 058b | 30 章封闭验证生成 — 30 章 accepted，无中断 |  |
| M18 上下文修复 | 058c | 上下文膨胀修复 + 字数控制 — 7 项关键修复 |  |
| M19 Revision 收敛 | 058d | `new_issues_introduced` 检测 |  |
| M20 诊断与根因 | 059~062 | JSONL 诊断 + 字数阈值验证 + Ch2-Ch6 根因 + 端到端重跑 |  |
| M21 Layer 3 基建 | 063~066 | RAG/LLM/Agent 重构 + 合规扫描 |  |
| M22 规则与摘要 | 067~071 | Genre Rules + Writer Feedback + 分层摘要 + RAG 独立调试 |  |
| M23 Settlement 与重写 | 072~073 | source_quote 去噪 + 截断重写策略 |  |
| M24 审查体系 | 074~077c | 对话质量 + Checkpointer + Writer 截断 + Setting 库 + BudgetPruner |  |
| M25 生命周期 | 078~080 | 伏笔生命周期 + RevisionHandler 重构 + 角色出场窗口 |  |
| M26 长程验证 | 081 | Ch51-Ch70 验证 — 19/20 章成功，budget_used 1.46 平均 |  |

### V4.0 — Context-on-Demand 极限优化（Task 083 ~ 100c）

> **预组装上下文包的极限优化。BudgetPruner、四信号系统、Accept 守卫，验证到 Ch50 达标率 81.6%。**

| 阶段 | Task | 内容 | 状态 |
|------|------|------|:----:|
| M28 LifecycleScheduler 基建 | 083~087 | Schema + 生命周期框架 + 动态预算 + 集成统计 |  |
| M29 字数硬约束 | 088~090a | RevisionHandler 1.25x/0.75x + Writer 1.20x/0.80x + 达标率修复 |  |
| M30 Rewrite 字数护栏 | 090b | rewrite ±25% → ±20%，硬截断回退 + rewrite 后 1 轮 revision |  |
| M31 Phase B 收官验证 | 091 | Ch2-Ch70 端到端，69 章 0 失败 |  |
| M32 Writer 场景预算 | 092 | scene_budget prompt + 动态目标 |  |
| M33 Revision 约束收紧 | 093 | ±25% → ±20%，保护达标初稿机制生效 |  |
| M34 Health Score 修正 | 094 | 分类加权扣分 + Settlement 去重 + ID 映射 + key 校验 |  |
| M35 场景结构保护 | 095 | 截断保场景完整性 + RevisionHandler 场景拆分/合并 |  |
| M36 Ch2-Ch50 回归 | 096 | 修复后回归验证，达标率 70.2% |  |
| M38 上下文压力计 + Accept 守卫 | 098 | 四信号系统 + Craft Card 1.0.9 + 字数守卫 |  |
| M39 Ch2-Ch50 重跑验证 | 099 | 达标率 81.6%，0 失败 |  |
| M40 RevisionHandler 下限保护 | 100a | MIN_CONTENT_RATIO 0.50→0.85 |  |
| M41 流程质量门 + edit 审计 | 100b | accept 前三联检，edit 后重跑 Audit |  |
| M42 上下文压力优化 | 100c | narrative_fullness 客观化，硬上限动态化 |  |

### V5.0 — Context Diet 2.0（Task 101 ~ 120）

> **"不是所有信息都值得记住。通过智能遗忘与分层压缩，支撑 150+ 章稳定生成。"**

| 阶段 | Task | 内容 | 状态 |
|------|------|------|:----:|
| M43 TemporalCompressor | 101 | 时间分层压缩：金字塔摘要结构 | ✅ |
| M44 CharacterFocalDecay | 102 | 角色焦点衰减：未出场章数驱动档案降级 | ✅ |
| M45 SettingEvaporator | 103 | 设定蒸发器：resolve_confidence + embedding 合并 | ✅ |
| M46 BudgetHardCeiling | 104 | 预算硬天花板：fullness_factor 0.7 + ContextEmergency | ✅ |
| M47 Ch51-Ch100 流式验证基础设施 | 105 | 自动收集指标 + 一键报告 + 决策门 DG-1 | ✅ |
| M48 统一评分体系 | 106 | 5 维评分 + ScoreAggregator + 工作流适配 | ✅ |
| M49 收敛护栏与 150-blockers 修复 | 107 | rewrite 结构完整性；QG 耗尽回滚 best_version；skip_settlement 保护 | ✅ |
| M50 角色退场机制 | 108 | CharacterLifecycleAuditor：非核心角色 dormant；活跃角色硬上限 | ✅ |
| M51 设定合并 + 伏笔监控 | 109 | SettingDeduplication + ForeshadowingPressure | ✅ |
| M52 Ch80-Ch100 压缩/质量/裁剪验证 | 110a-110e | 分层压缩、质量控制、裁剪优化、coherence_major 修复 | ✅ |
| M53 Ch51-Ch100 验证重启 | 105b | 基于 Task 106~110 修复重启实跑，触发 DG-1 | ✅ |
| M54 前置一致性修复 | 111a | 工作流决策契约修复：ReviewMerger/ScoreAggregator/Literary/Revision 路由一致性 | ✅ |
| M55 事实源一致性修复 | 111b | Settlement 与事实源一致性：accept/settlement/summary/state 边界 | ✅ |
| M56 Context/Prompt 一致性修复 | 111c | ContextEmergency、hard constraints、Craft Card、human instruction 口径统一 | ✅ |
| M57 QualityGate/Settlement 阻断修复 | 111d | budget QG、new issues 终态、summary fallback | ✅ |
| M58 报告与 DG-2 Gate 修复 | 111e | streaming report 兼容缺失 metrics；DG-2 覆盖硬指标 | ✅ |
| M59 Context Snapshot/Metadata 修复 | 111f | Writer/Auditor 复用上下文快照；metadata 可回放 | ✅ |
| M60 长跑性能缺陷收敛 | 111g | context assembly、Settlement prompt facts、O(N²) 热点收敛 | ✅ |
| M61 Task 114 前置阻断修复 | 112 | 修复 budget QG 硬门禁与 Settlement setting_key 规范化；恢复 Ch97 基线 | ✅ |
| M62 Ch101 收敛/Settlement 阻断修复 | 113 | 修复 rebound 后 best version/head 选择；恢复 Ch101 基线 | ✅ |
| M63 Settlement 事实源契约修复 | 114a | 修复 Ch103 `old_value` mismatch、`quote_filter` 内部 ID 误杀引用、run logger/post-processing 残留风险 | ✅ |
| M64 Phase 1 重跑 | 114b | Ch103/Ch102 回放因 QG 收敛失败提前跳过 settlement，未达出口条件 | ⚠️ |
| M64b QG 收敛阻断处理 + settlement 验证窗口 | 114b2 | 修复当前 lineage 修复计数、QG best 回滚、rewrite 结构失败路由；Ch102/Ch103 `run-af3ba939` 端到端通过 | ✅ |
| M65 Ch111-Ch150 验证 | 114c | Phase 2/3 分段长跑 + 决策门 DG-2；40/40 成功 | ⚠️ 条件通过 |
| M66 ContextEmergency 复核 | 115 | 复核 Ch115/Ch120 emergency，确认合理降级并补可观测性 | ✅ |
| M67 Best-Version 质量选择 | 116 | 修复 Ch147/Ch148 低分 rewrite fallback 覆盖高分 QG best 风险 | ✅ |
| M68 DG-2 风险窗口复验 | 117 | 复跑 Ch115/Ch120/Ch147/Ch148，确认 DG-2 风险关闭 | ✅ |
| M69 Continuity health 治理 | 118 | health_low P1/P2/P3 分级追踪，保持软复核 | ✅ |
| M70 报告与 wrapper 加固 | 119 | 统一长跑报告入口，修复 Windows wrapper 退出判定漂移 | ✅ |
| M71 V5.0 Final Acceptance | 120 | V5.0 最终验收通过，P0/P1 风险为 0 | ✅ |

---

## 4. 快速开始

### 前置要求

- **Python >= 3.11**（必须，`pyproject.toml` 中 `requires-python = ">=3.11"`)
- DeepSeek API Key 或兼容的 LLM API（通过 litellm 统一接口）
- 磁盘空间：100 章运行时 DB + JSONL 日志约 10MB

### 安装

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
pytest -k "not integration" -q
```

### 验证命令

```bash
pytest tests/ -q
# Current baseline: 1776 passed, 2 skipped, 1 xfailed, 0 xpassed, 2 warnings

ruff check src/ tests/
# Current baseline: All checks passed!
```

---

## 5. 已交付的关键指标

| 指标 | 目标 | 验证方式 |
|------|------|----------|
| 流程跑通率 | 100% | 3 个种子项目均完成闭环 |
| 设定硬错误数 | 0 | critical world_consistency = 0 |
| AI 腔规则命中数 | < 2 处/章 | RuleAuditor 检测数 |
| 疲劳词命中数 | < 3 处/章 | RuleAuditor 检测数 |
| 首屏钩子达标率 | 100% | has_opening_hook == True |
| 章末钩子达标率 | 100% | has_ending_hook == True |
| 状态结算字段准确率 | > 90% | old_value 与 DB 一致率 |
| 状态结算 setting_key 准确率 | > 90% | setting_key 唯一 + source_quote 存在 |
| 概念空转段落数 | 0 | LiteraryAuditor 检测数 |
| 修订后新问题数 | 0 | 第二轮审查新问题数 = 0 |
| **刺激点密度** | **≥ 1/章** | **PunchCheck.punch_density_ok** |
| **情绪转折** | **≥ 1/1500字** | **PunchCheck.emotion_switch_ok** |
| **连续性健康分** | **≥ 7.0** | **ContinuityReport.overall_health_score** |
| **字数预算使用** | **0.75x ~ 1.25x** | **Writer 1.20x/0.80x + Rewrite ±25%** |
| **重写触发率** | **< 10%** | **截断重写触发章节占比** |

---

## 6. 当前阶段与下一步

**V5.0 — Context Diet 2.0 智能遗忘架构。目标：Ch1-Ch150 全自动稳定生成。**

### 已完成：V4.0 修复收尾

- **Task 100a** : RevisionHandler 下限保护 + 字数守卫（消除 Ch45 类暴跌）
- **Task 100b** : 流程质量门 + 人工 edit 审计修复（accept 前三联检）
- **Task 100c** : 上下文压力优化（四信号系统调优，缓解 Ch9 类过载）

### 已完成：V5.0 Phase 1 — Context Diet 2.0 核心组件

- **Task 101** : TemporalCompressor — 时间分层压缩
- **Task 102** : CharacterFocalDecay — 角色焦点衰减
- **Task 103** : SettingEvaporator — 设定蒸发器
- **Task 104** : BudgetHardCeiling — 预算硬天花板

### 已完成基础设施：V5.0 Phase 2 — 流式验证

- **Task 105** : Ch51-Ch100 流式验证 + 决策门 DG-1 基础设施
- 真实试跑 `run-33229919` 已完成 Ch51-Ch59，因 Ch57-Ch59 连续 3 章质量门失败自动暂停。

### 已完成：V5.0 Phase 2.5 — 修复与收敛

- **Task 106** : Unified Scoring System — 统一 5 维评分体系
- **Task 107** : Repair Convergence Guardrail + Fix 150-Blockers — 修复 revision/rewrite 劣化、QG 失败污染 settlement 等 8 项阻断/收敛缺陷

### 已完成：V5.0 Phase 3 — 活跃信息池控制

- **Task 108** : CharacterLifecycleAuditor — 角色退场机制
- **Task 109** : SettingDeduplication + ForeshadowingPressure — 设定去重与伏笔压力监控

### 已完成：V5.0 Phase 4 前置修复 — Task 111d-111g

- **Task 111a** : 工作流决策契约修复 — 修复 ReviewMerger/ScoreAggregator/Literary/Revision 路由一致性 ✅
- **Task 111b** : Settlement 与事实源一致性修复 — 防止 accepted/settlement/summary/state 半提交或污染 ✅
- **Task 111c** : Context 与 Prompt 一致性修复 — 校准 ContextEmergency、hard constraints、Craft Card 和 human instruction ✅
- **Task 111d** : QualityGate 与 Settlement 阻断项修复 — budget QG、new issues 终态、summary fallback ✅
- **Task 111e** : Task 112 报告与 DG-2 Gate 完整性修复 — report 稳定性和决策门硬指标 ✅
- **Task 111f** : Context Snapshot、Prompt 与 Metadata 一致性修复 — prompt 输入可回放、可审计 ✅
- **Task 111g** : 长跑性能缺陷收敛 — 降低重复组装、LLM 调用和 O(N²) 热点 ✅

### 已完成：V5.0 Phase 4 前置阻断修复 — Task 112

- **Task 112** : Task 114 前置阻断修复 — 修复 budget QG 硬门禁与 Settlement `setting_key` 规范化，恢复 Ch97 accepted + settlement + summary 基线 ✅

### 已完成：V5.0 Phase 4 阻断修复 — Task 113

- **Task 113** : Ch101 收敛回滚与 Settlement 阻断修复 ✅
- 首次 Task 113 长跑窗口 `run-6b462cb9` 在 Ch101 触发 `settlement_review` 熔断；修复后通过 `run-90e08243` 恢复 Ch101 accepted、settlement 和 summary 基线。

### 已完成：V5.0 Phase 4 分段验证 — Task 114c

- **Task 114a** : Settlement 事实源契约修复 ✅
- Task 114 Phase 1 首次运行 `run-5105e24b` 中，Ch102 成功，Ch103 因 settlement `old_value` 与 DB 当前事实源不一致进入 `settlement_review`，Ch104-Ch110 未继续执行。
- **Task 114b** : Phase 1 重跑 Ch102-Ch110 ⚠️
  - Ch103 回放 `run-385dc3e0` 因 `readability_score:0.473` 触发 QG 收敛失败，提前 `_skip_settlement=True`。
  - Ch102 重跑 `run-452c4f78` 因 `length_score:0.440` 触发 QG 收敛失败，提前 `_skip_settlement=True`。
  - 两次运行均未进入 settlement，因此不能作为 Task 114a 端到端实跑通过证据。
- **Task 114b2** : QG 收敛阻断处理 + settlement 端到端验证窗口 ✅
  - 修复当前 lineage 修复计数，避免新回放继承历史 revision/rewrite 次数。
  - 修复 QG 合格 best 回滚和 rewrite 结构失败路由。
  - 组合窗口 `run-af3ba939`：Ch102/Ch103 均完成 accept + settlement + summary，`run_logger success=True`。
- **Task 114c** : Ch111-Ch150 已按分段方式完成，40/40 成功，QG/settlement/summary 均 40/40，DG-2 条件通过。

### 已完成：V5.0 Phase 4 收口任务 — Task 115-120

- **Task 115** : ✅ ContextEmergency 触发复核与校准 — 诊断为合理降级（`budget_used` 触发时 1.0007），新增 `budget_used_before_emergency` 字段。
- **Task 116** : ✅ Best-Version 质量选择策略复核与修复 — 修复 QG 通过后错误进入 rewrite 的路由缺陷。
- **Task 117** : ✅ DG-2 风险章节窗口复验 — Ch115/Ch120/Ch147/Ch148 4/4 成功，风险关闭。
- **Task 118** : ✅ ContinuityAuditor Health 低分治理策略 — health_low P1/P2/P3 分级，human marks 可追踪。
- **Task 119** : ✅ 长跑报告入口与 Windows Wrapper 加固 — `songyan report` 入口统一，wrapper 结果码明确。
- **Task 120** : ✅ V5.0 Final Acceptance Package — V5.0 工程验收通过，P0/P1 风险为 0。

当前建议：V5.0 已交付完成；Task 121b-121q 已持续补强 single-run 证据链，依次解除 Ch5、Ch8、Ch18、Ch115、连续 ContextEmergency AutoHalt、0.82 阈值早期章节阻断。**Task 121q full single-run `run-a2bed648` 已完成 Ch1-Ch150 150/150 全部成功，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙**，一次性单命令最终证据已获取。**Pass 14-18 V5.1 Code Review 已完成，全部 8 项缺口已修复**，新增 37 个测试（Pass 14-18 修复 25 个 + 122b 集成测试 12 个），pytest 基线 1776 passed，零回归。**Task 121r 已完成 Prompt / 正文质量清理**（Writer 1.1.0 + CreativeDirector 1.0.5 + RuleAuditor 格式检测）。**Task 122a/122b 已完成系统性测试矩阵**（动态阈值单元测试 + Pipeline 集成测试 12 个新增测试）。Task 122c（E2E 窗口补全）和 Task 122d（150 章压力测试）为当前待启动项。V5 任务状态以 `tasks/V5-README.md` 和各 `*-DONE.md` / TODO 文档为准，规划稿已归档为设计背景。

---

## 7. CLI 常用命令

```bash
# 创建项目
songyan create-project

# 自动生成第 1-5 章
songyan run --project-id mynovel --chapters 1-5 --auto-confirm

# 断点续跑（从失败章节继续）
songyan run --project-id mynovel --chapters 3-5 --auto-confirm  # 前 2 章已生成，从 Ch3 继续

# 查看项目列表
songyan list-projects

# 添加人类标记
songyan mark-add --project-id mynovel --type character --target 角色名 --note "需要调整性格"

# 自定义创作模式
songyan run --project-id mynovel --chapters 1-5 --auto-confirm --mode-id literary
```

## 8. 恢复失败章节

Songyan 支持断点续跑（SQLite checkpoint）：

1. 查阅 `logs/` 目录下的 JSONL 运行日志，找到失败章节的 `chapter_number`
2. 使用 `--chapters` 参数从失败章节重新运行，系统自动检测已完成的章节并跳过

```bash
# 假设 Ch1-Ch3 已完成，Ch4 失败：
songyan run --project-id mynovel --chapters 4-30 --auto-confirm
```

Checkpointer 模式说明：
- `sqlite`：生产环境，持久化 checkpoint，支持断点续跑
- `memory`：测试环境，不写文件锁（推荐 Windows 验证时使用）

通过 `CHECKPOINTER_MODE` 环境变量切换。

## 开发文档

- `AGENTS.md` — 开发代理指令与不可违背规则
- `docs/STATUS.md` — 项目状态看板
- `docs/INDEX.md` — 文档索引
- `tasks/V5-README.md` — V5 / Task 121 事实入口
- `tasks/121h-ch115-quality-gate-rewrite-state-review.md` — Ch115 工程修复完成记录
- `tasks/121i-ch115-focused-rerun-and-quality-window.md` — Ch115 聚焦验证完成记录
- `tasks/121j-ch1-ch150-single-run-after-ch115-fix.md` — 修复后 full single-run partial 记录
- `tasks/121k-prompt-quality-cleanup-plan.md` — Prompt / 正文质量清理规划
- `tasks/121r-prompt-quality-cleanup-execution.md` — Prompt / 正文质量清理执行（Writer 1.1.0 + CD 1.0.5）
- `tasks/121l-context-emergency-autohalt-review.md` — 连续 ContextEmergency AutoHalt 策略修复记录
- `tasks/121p-ch1-ch150-single-run-rag-embedder-timeout.md` — Ch1-Ch150 full single-run 双层根因记录
- `tasks/122-v51-systematic-test-matrix.md` — V5.1 系统性测试矩阵主文档
- `docs/reports/pass14-final-fix-summary.md` — Pass 14-18 V5.1 Code Review 修复汇总
- `archive/v4/INDEX.md` — V4.x 完整归档索引
- `archive/v3/INDEX.md` — V3.x 完整归档索引

## 许可证

AGPL-3.0
