设计的艺术不是堆砌，而是在正确的时间做正确的取舍。

# NovelForge — 基于 LangGraph 的多 Agent 中文小说写作系统

## 完整架构设计文档（v2 — 三阶段落地版）

> **版本**: v2.1.0（基于 v2 review 精修）  
> **作者**: AI System Architect  
> **日期**: 2026-05-16  
> **状态**: 设计稿（Design Draft）  
> **核心变更**: Phase 1 目标收敛为单章闭环（1-3 章），LangGraph state 只存 ID，增加 revision_handler/human_confirm 节点，token 默认 32K，评测加人工金标

---

## 目录

- [0. 从 v1 到 v2：为什么改](#0-从-v1-到-v2为什么改)
- [1. 设计哲学与核心判断](#1-设计哲学与核心判断)
- [2. 三阶段落地路线图](#2-三阶段落地路线图)
- [3. Phase 1 详细设计：单章闭环](#3-phase-1-详细设计单章闭环)
  - [3.1 Phase 1 架构图](#31-phase-1-架构图)
  - [3.2 四个核心 Agent](#32-四个核心-agent)
  - [3.3 数据事实源设计](#33-数据事实源设计)
  - [3.4 版本管理模型](#34-版本管理模型)
  - [3.5 结构化审查输出](#35-结构化审查输出)
  - [3.6 Issue-Driven 修订机制](#36-issue-driven-修订机制)
  - [3.7 写作上下文包（Context Package）](#37-写作上下文包context-package)
  - [3.8 新手创建向导](#38-新手创建向导)
  - [3.9 工作流编排](#39-工作流编排)
  - [3.10 评测集设计](#310-评测集设计)
- [4. Phase 2 设计概要：卷级连续性](#4-phase-2-设计概要卷级连续性)
- [5. Phase 3 设计概要：完整产品化](#5-phase-3-设计概要完整产品化)
- [6. 终态架构愿景（参考）](#6-终态架构愿景参考)
- [7. 数据库设计（全阶段）](#7-数据库设计全阶段)
- [8. 生产部署（分阶段）](#8-生产部署分阶段)

---

## 0. 从 v1 到 v2：为什么改

v1 文档的问题不是方向错误，而是**复杂度过早膨胀**。它描述的是一个中型 AI 产品团队 3-6 个月的终态目标，不是第一版应该聚焦的问题。

### v1 的核心问题

| # | 问题 | 后果 |
|---|------|------|
| 1 | 10 个 Agent 同时引入 | Agent 编排成为主要工作，迟迟验证不了"能不能写出好章节" |
| 2 | 6 种存储同时引入（Postgres、Qdrant、Redis、SQLite、JSONB、checkpoint） | 状态源混乱，调试成本爆炸 |
| 3 | FastAPI + React + TUI + Celery 全量引入 | 基础设施占用大部分开发时间 |
| 4 | 一致性指标不可执行（"偏离度 > 0.3"） | 审查流于形式，无法驱动有效修订 |
| 5 | 自动修订最多 5 轮整章重写 | 越修越平、修掉风格、修出新 bug |
| 6 | 缺少章节版本模型 | 无法追踪修订历史，人工编辑会丢失 |
| 7 | RAG 是通用文档检索，不是小说上下文组装 | 检索结果不能直接注入写作 |
| 8 | "新手优先"停留在口号，没有具体产品流 | 用户不知道怎么开始 |

### v2 的修正策略

**一句话**：保留终态架构愿景，但第一版目标改成 **"单章闭环验证（生成→审查→修订→确认），每个题材 1-3 章"**。

| 维度 | v1 策略 | v2 策略 |
|------|---------|---------|
| 第一版目标 | 完整多 Agent 小说工厂 | 单章闭环验证，每个题材 1-3 章 |
| Agent 数量 | 10 个 | 4 个核心（Planner、Writer、Reviewer、ContextManager） |
| 存储 | Postgres + Qdrant + Redis + SQLite | Phase 1: SQLite 单库；Phase 2: 加 Qdrant；Phase 3: 加 Redis/Celery |
| 界面 | Web + TUI + API | Phase 1: CLI；Phase 2: 简单 Web；Phase 3: Studio |
| 修订策略 | 最多 5 轮整章重写 | 最多 2 轮 issue-driven patch，之后人工确认 |
| 审查输出 | 抽象评分 | 结构化输出（证据片段+关联设定+严重度+修复建议） |
| RAG | 通用文档检索 | 小说专用"写作上下文包"分区注入 |
| 新手流 | 口号 | 具体的新项目创建向导（7 步引导） |

---

## 1. 设计哲学与核心判断

### 1.1 核心判断

**第一版唯一要验证的假设**："AI 能否在足够一致的上下文中，稳定产出质量合格、设定不矛盾的中文小说章节？"

其他一切都是为这个假设服务的。如果 1-3 章验证不了这个假设，10 章也验证不了。

### 1.2 设计原则

**原则 1：假设驱动，快速闭环**  
每个 Phase 只有一个核心假设要验证。Phase 1 验证单章质量，Phase 2 验证跨章连续性，Phase 3 验证产品化可行性。

**原则 2：能删则删，晚点再加**  
如果某个功能不是验证当前假设所必需的，就不做。Agent 数量、存储种类、界面复杂度都按这个标准裁剪。

**原则 3：数据先行，指标说话**  
每个 Phase 必须有明确的评测指标和评测集。"感觉不错"不是标准，"3 章中人工返工率 < 30%"才是。

**原则 4：人工是最后一道防线，不是替代方案**  
自动修订最多 2 轮，之后必须人工确认。不让人工介入的自动循环是质量退化的高危区。

### 1.3 技术选型（分阶段锁定）

| 组件 | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|
| **工作流引擎** | LangGraph | LangGraph | LangGraph |
| **LLM 接口** | LangChain + litellm | LangChain + litellm | LangChain + litellm |
| **主存储** | SQLite | PostgreSQL | PostgreSQL |
| **向量存储** | 无（sqlite-vec 或内存） | Qdrant | Qdrant |
| **缓存** | 无 | 无 | Redis |
| **界面** | CLI | 简单 Web (React) | Studio Web + TUI |
| **任务队列** | 同步执行 | 同步执行 | Celery / ARQ |
| **监控** | 日志文件 | LangSmith | LangSmith + Langfuse |
| **部署** | pip install | Docker Compose | k8s |

---

## 2. 三阶段落地路线图

### 2.1 阶段总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                     NovelForge 三阶段落地路线                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1: 单章闭环验证        Phase 2: 卷级连续性      Phase 3: 产品化│
│  ─────────────────────        ──────────────────      ────────────  │
│  目标：验证"单章质量"          目标：验证"跨章连续"    目标：完整产品  │
│  范围：1-3 章闭环验证          范围：10 章连续生成    范围：整本生产  │
│  Agent：4 个                   Agent：6 个            Agent：10 个   │
│  存储：SQLite                  存储：PG + Qdrant      存储：PG+Qdrant+Redis│
│  界面：CLI                     界面：简单 Web          界面：Studio    │
│  周期：2-3 周                  周期：4-6 周           周期：8-12 周  │
│                                                                     │
│  ┌─────────┐                  ┌──────────┐           ┌──────────┐  │
│  │项目设定  │─────────────────▶│世界设定表 │──────────▶│WorldBuilder│ │
│  │角色卡    │                  │角色状态表 │           │CharacterDesigner│
│  │上下文包  │                  │伏笔表     │           │PlotPlanner   │
│  │         │                  │章节摘要表 │           │LoreKeeper    │
│  │ ┌─────┐ │    ┌──────┐      │          │           │              │
│  │ │CLI  │ │───▶│ SQLite│─────▶│ ┌──────┐ │           │ ┌──────────┐ │
│  │ └─────┘ │    └──────┘      │ │Qdrant│ │──────────▶│ │Studio Web│ │
│  │         │                  │ └──────┘ │           │ │TUI       │ │
│  │ Planner │                  │          │           │ │Celery    │ │
│  │ Writer  │                  │ Planner  │           │ │k8s       │ │
│  │ Reviewer│                  │ Writer   │           │ └──────────┘ │
│  │ Context │                  │ Reviewer │           │              │
│  │ Manager │                  │ Context  │           │              │
│  └─────────┘                  │ Manager  │           │              │
│                               │ +2 Agent │           │              │
│                               └──────────┘           └──────────────┘│
│                                                                     │
│  验证指标：                     验证指标：            验证指标：      │
│  - 一致性通过率 > 80%           - 跨章设定漂移 < 5%  - 批量生产稳定  │
│  - 质量评分 > 6/10              - 角色行为一致 > 85% - 人工返工率 <20%│
│  - 人工返工率 < 30%             - 跨章设定漂移 < 5%  - 新手完成率 >50%│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 每个 Phase 的验证标准

**Phase 1 完成标准（单章闭环）**：
- [ ] 至少 3 个题材（玄幻、都市、科幻）各验证 1-3 章闭环
- [ ] 结构化审查通过率 > 80%（无 critical/major 问题）
- [ ] 人工返工率 < 30%（3 章中最多 1 章需要人工大幅修改）
- [ ] Reviewer 与人工金标一致率 > 70%（每个题材抽 1 章人工打分，对比 Reviewer 判断）
- [ ] 平均质量评分 > 6/10
- [ ] 修订不引入新问题（第二轮审查新问题数 = 0）

**Phase 1.5 扩展验证（可选）**：
- [ ] 单个题材连续生成 5-10 章，验证流程稳定性

**Phase 2 完成标准（卷级连续性）**：
- [ ] 自动连续生成 10 章无需人工干预
- [ ] 跨章设定漂移检测 < 5%（设定引用错误率）
- [ ] 角色行为一致性 > 85%
- [ ] 伏笔正确回收率 > 70%

**Phase 3 完成标准（产品化）**：
- [ ] 新手用户从安装到完成第一章 < 30 分钟
- [ ] 批量生产 100 章成功率 > 90%
- [ ] 人工返工率 < 20%

---

## 3. Phase 1 详细设计：单章闭环

### 3.1 Phase 1 架构图

```
┌─────────────────────────────────────────────┐
│            Phase 1: 单章闭环架构             │
├─────────────────────────────────────────────┤
│                                             │
│  用户输入                                    │
│  ├── 项目设定（题材、卖点、禁忌等）            │
│  ├── 角色卡（主角、关键配角）                 │
│  └── 上一章摘要 + 本章目标                    │
│         │                                   │
│         ▼                                   │
│  ┌─────────────────────────────┐            │
│  │  新手创建向导（7步引导）      │            │
│  │  (首次使用时触发)            │            │
│  └─────────────┬───────────────┘            │
│                │                            │
│                ▼                            │
│  ┌─────────────────────────────┐            │
│  │  ContextManager Agent       │            │
│  │  ├── 组装"写作上下文包"      │            │
│  │  ├── 硬约束（设定、角色状态） │            │
│  │  ├── 软参考（相关世界观）     │            │
│  │  ├── 最近剧情（前3章摘要）    │            │
│  │  └── 本章目标（钩子、爽点）   │            │
│  └─────────────┬───────────────┘            │
│                │                            │
│                ▼                            │
│  ┌─────────────────────────────┐            │
│  │  Writer Agent               │            │
│  │  ├── 按场景逐个生成          │            │
│  │  ├── 对话与叙述交替          │            │
│  │  └── 输出：章节草稿          │            │
│  └─────────────┬───────────────┘            │
│                │                            │
│                ▼                            │
│  ┌─────────────────────────────┐            │
│  │  Reviewer Agent             │            │
│  │  ├── 设定一致性检查          │            │
│  │  ├── 角色行为一致性          │            │
│  │  ├── 时间线验证              │            │
│  │  ├── 质量评分（8维度）        │            │
│  │  └── 输出：结构化审查报告      │            │
│  └─────────────┬───────────────┘            │
│                │                            │
│          ┌─────┴─────┐                     │
│          ▼           ▼                     │
│      通过          有问题                  │
│          │           │                     │
│          ▼           ▼                     │
│     ┌────────┐  ┌──────────────┐          │
│     │人工确认 │  │Issue-Driven  │          │
│     │(Human) │  │Revision      │          │
│     └────┬───┘  │最多2轮patch  │          │
│          │      └──────┬───────┘          │
│          │             │                   │
│          └──────┬──────┘                   │
│                 ▼                          │
│          ┌────────────┐                    │
│          │版本保存入库 │                    │
│          │生成章节摘要 │                    │
│          │(Planner)   │                    │
│          └────────────┘                    │
│                                             │
│  存储：SQLite 单库                          │
│  表：projects, characters, chapter_versions,│
│      review_reports, setting_snapshots      │
│                                             │
└─────────────────────────────────────────────┘
```

### 3.2 四个核心 Agent

Phase 1 只有 4 个 Agent，职责清晰、不重叠。

| Agent | 核心职责 | 不做什么 |
|-------|----------|----------|
| **Planner** | 项目设定收集、章节目标制定、章节摘要生成 | 不写正文 |
| **Writer** | 按场景生成章节正文、遵守上下文包约束 | 不做审查、不修改设定 |
| **Reviewer** | 结构化审查（设定/角色/时间线/质量）、输出 issue 列表 | 不直接修改正文 |
| **ContextManager** | 组装"写作上下文包"、管理版本、存取 SQLite | 不做生成、不做审查判断 |

#### 3.2.1 Planner Agent

```python
class PlannerAction(str, Enum):
    COLLECT_PROJECT_SETTING = "collect_project_setting"  # 收集项目设定
    DEFINE_CHAPTER_GOAL = "define_chapter_goal"          # 制定章节目标
    GENERATE_SUMMARY = "generate_summary"                # 生成章节摘要
    
class ProjectSetting(BaseModel):
    """项目设定（新手向导收集）"""
    title: str | None = None                # 书名（可空，AI建议）
    genre: str                              # 题材（玄幻/都市/科幻/历史等）
    protagonist_name: str                   # 主角名
    protagonist_background: str             # 主角背景
    core_hook: str                          # 核心爽点/看点
    target_reader_expectation: str          # 读者预期
    taboos: list[str] = []                  # 禁忌（不想出现的内容）
    target_word_count: int = 100000         # 目标字数
    reference_works: list[str] = []         # 参考作品
    tone: str = "热血"                       # 基调
    
class ChapterGoal(BaseModel):
    """章节目标"""
    chapter_number: int
    previous_summary: str                   # 上一章摘要
    target_events: list[str]                # 本章必须发生的事件
    emotional_arc: str                      # 情感走向
    hooks: list[str]                        # 钩子（吸引读者）
    obligations: list[str]                  # 必须兑现的承诺
    word_count_target: int = 3000
```

**Planner 的工作流**：
1. 首次运行时，启动新手向导（7 步引导），收集 `ProjectSetting`
2. 每章写作前，根据上一章内容和整体规划，生成 `ChapterGoal`
3. 每章完成后，生成结构化摘要，存入 SQLite

#### 3.2.2 Writer Agent

```python
class WriterInput(BaseModel):
    """Writer 的输入"""
    context_package: ContextPackage         # 写作上下文包
    chapter_goal: ChapterGoal               # 章节目标
    style_rules: str = ""                   # 风格规则（可选）

class WriterOutput(BaseModel):
    """Writer 的输出"""
    content: str                            # 完整正文
    scenes: list[Scene]                     # 场景分解
    word_count: int
    generation_metadata: dict               # 生成参数记录
```

**Writer 的约束**：
- 按场景逐个生成，场景间有清晰分隔
- 对话和叙述交替，对话单独成段
- 严格引用上下文包中的角色名、设定名
- 不引入上下文包中未提及的新设定（如有需要，标记为 `[[新设定:描述]]`）
- 章末必须有钩子

#### 3.2.3 Reviewer Agent

Reviewer 是 Phase 1 最关键的质量关卡。输出必须是**结构化 issue 列表**，不是抽象评分。

```python
class ReviewIssue(BaseModel):
    """审查发现的单个问题"""
    issue_id: str
    category: Literal[                       # 问题类别
        "world_consistency",                  # 设定一致性
        "character_behavior",                 # 角色行为
        "timeline",                           # 时间线
        "quality_narrative",                  # 叙事质量
        "quality_dialogue",                   # 对话质量
        "quality_description",                # 描写质量
        "quality_pacing",                     # 节奏
        "style",                              # 风格
        "new_setting_unregistered",           # 未登记新设定
    ]
    severity: Literal["critical", "major", "minor", "info"]
    
    # 证据（必须有）
    evidence_quote: str                       # 原文问题片段
    evidence_location: str                    # 位置（第几段第几句）
    
    # 关联（必须有）
    related_setting_id: str | None = None     # 关联设定ID
    related_character_id: str | None = None   # 关联角色ID
    related_chapter_id: str | None = None     # 关联章节ID
    
    # 问题说明
    issue_description: str                    # 具体问题
    expected: str | None = None               # 期望是什么
    actual: str | None = None                 # 实际是什么
    
    # 修复建议
    suggested_fix: str | None = None          # 建议修复方式
    fix_type: Literal["patch", "rewrite_scene", "confirm", "register_setting"] = "patch"
    
    # 置信度
    confidence: float = 1.0                   # 0-1，Reviewer 对此判断的置信度

class ReviewReport(BaseModel):
    """审查报告"""
    chapter_version_id: str
    issues: list[ReviewIssue] = []
    overall_score: float = 0.0                # 0-10，综合评分
    summary: str = ""                         # 总结评价
    
    @property
    def has_critical(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)
    
    @property
    def has_major(self) -> bool:
        return any(i.severity == "major" for i in self.issues)
    
    @property
    def patchable_issues(self) -> list[ReviewIssue]:
        """可通过 patch 修复的 issues"""
        return [i for i in self.issues if i.fix_type == "patch"]
```

**Reviewer 的铁律**：
- 没有 `evidence_quote` 的 issue 不进入自动修订
- `critical` 必须修复才能入库
- `major` 建议修复，可人工确认跳过
- `minor`/`info` 只记录不阻塞

#### 3.2.4 ContextManager Agent

ContextManager 是 Phase 1 的数据枢纽，负责组装"写作上下文包"。

```python
class ContextPackage(BaseModel):
    """
    写作上下文包 —— 小说专用的分区上下文注入结构。
    
    不是通用 RAG 的"相关文档"，而是按小说写作场景组织的
    结构化约束包。
    """
    chapter_goal: ChapterGoal               # 章节目标
    
    # === 硬约束（必须遵守）===
    hard_constraints: list[HardConstraint] = []
    # 包括：角色当前状态、已揭示的设定、时间线位置、禁忌事项
    
    # === 软参考（建议遵循，可灵活处理）===
    soft_references: list[SoftReference] = []
    # 包括：相关世界观设定、角色背景、历史事件
    
    # === 最近剧情（前3章摘要+关键片段）===
    recent_plot: list[ChapterSummary] = []
    
    # === 角色状态快照===
    character_states: list[CharacterStateSnapshot] = []
    
    # === 伏笔线索===
    foreshadowing: list[ForeshadowingItem] = []
    # 包括：已埋下未回收的伏笔、本章需要回收的伏笔
    
    # === 风格规则===
    style_rules: str = ""
    
    # === 元信息===
    estimated_tokens: int = 0
    assembled_at: datetime = Field(default_factory=datetime.now)

class HardConstraint(BaseModel):
    """硬约束 —— Writer 必须严格遵守"""
    type: Literal["character_state", "setting_fact", "timeline", "taboo", "obligation"]
    description: str
    source: str                               # 来源（哪章哪条设定）
    
class CharacterStateSnapshot(BaseModel):
    """角色状态快照"""
    character_id: str
    name: str
    current_location: str | None = None
    current_cultivation: str | None = None    # 修真：当前境界
    emotional_state: str | None = None
    active_relationships: list[str] = []      # 当前活跃关系
    unresolved_issues: list[str] = []         # 未解决的内心冲突
    
class ForeshadowingItem(BaseModel):
    """伏笔项"""
    foreshadowing_id: str
    description: str                          # 伏笔描述
    planted_in_chapter: int                   # 在哪章埋下
    expected_resolve_chapter: int | None = None  # 预计在哪章回收
    status: Literal["planted", "due", "overdue", "resolved"] = "planted"
```

### 3.3 数据事实源设计

**Phase 1 的核心原则：SQLite 是唯一的长期事实源。**

```
┌─────────────────────────────────────────────┐
│              Phase 1 数据架构                 │
├─────────────────────────────────────────────┤
│                                             │
│   SQLite（唯一事实源）                        │
│   ├── projects               # 项目信息      │
│   ├── projects               # 项目设定      │
│   ├── characters             # 角色档案      │
│   ├── character_states       # 角色状态追踪  │
│   ├── chapter_versions       # 章节版本      │
│   ├── review_reports         # 审查报告      │
│   ├── setting_snapshots      # 设定快照      │
│   ├── foreshadowings         # 伏笔追踪      │
│   └── summaries              # 章节摘要      │
│                                             │
│   LangGraph Checkpoint（只存执行现场）        │
│   ├── checkpoints            # 图执行状态    │
│   └── 不存业务数据，只用于崩溃恢复            │
│                                             │
│   内存（临时，重启丢失）                      │
│   └── LLM 上下文窗口                         │
│                                             │
│   明确的分工：                                │
│   - 所有业务数据 → SQLite                     │
│   - 执行恢复现场 → Checkpoint                │
│   - 临时计算缓存 → 内存                       │
│                                             │
└─────────────────────────────────────────────┘
```

**事实源规则**：
1. **SQLite 是所有业务数据的唯一权威来源**
2. **LangGraph checkpoint 只存轻量执行状态**（project_id、chapter_number、current_version_id、review_report_id、status、revision_round），不存完整业务对象
3. **每个节点从 SQLite 加载业务对象**：节点函数通过 ID 从 SQLite 查询完整的 ProjectSetting、ChapterVersion、ReviewReport 等
4. 重启后从 checkpoint 恢复执行位置（到哪一步了），从 SQLite 加载业务数据（具体内容是什么）
5. 禁止任何 Agent 直接修改 checkpoint 中的业务状态

### 3.4 版本管理模型

v1 缺少版本管理是严重缺陷。Phase 1 必须引入 `chapter_versions` 表。

```python
class ChapterVersion(BaseModel):
    """
    章节版本 —— 每次生成和修订都保存一个版本。
    
    版本链：
    draft_v1 (AI生成) → revision_v1 (第1轮修订) → revision_v2 (第2轮修订) 
    → accepted (人工确认) → edited (人工编辑)
    """
    version_id: str
    chapter_number: int
    project_id: str
    
    # 版本信息
    version_number: int                       # 1, 2, 3...
    version_type: Literal[                    # 版本类型
        "draft",                              # AI 初稿
        "revision",                           # AI 修订
        "accepted",                           # 人工确认接受
        "edited",                             # 人工编辑后
    ]
    parent_version_id: str | None = None      # 父版本（谁修订而来）
    
    # 内容
    title: str
    content: str                              # 正文
    word_count: int
    
    # 审查关联
    review_report_id: str | None = None       # 关联的审查报告
    issues_fixed: list[str] = []              # 本轮修复了哪些 issue
    issues_remaining: list[str] = []          # 仍未修复的 issue
    
    # 变更记录
    change_description: str = ""              # 变更说明
    changed_by: Literal["ai", "human"]        # 变更者
    
    # 元信息
    created_at: datetime = Field(default_factory=datetime.now)
    
    def get_version_chain(self, db) -> list["ChapterVersion"]:
        """获取版本链（从 draft 到当前）"""
        ...

class ChapterHead(BaseModel):
    """
    章节指针 —— 指向当前生效的版本。
    
    类似于 git 的 HEAD，始终指向 accepted 或最新的 edited 版本。
    """
    chapter_number: int
    project_id: str
    current_version_id: str                   # 当前生效版本
    accepted_version_id: str | None = None    # 人工确认的版本
```

**版本管理规则**：
1. 每次 AI 生成或修订都创建新版本，不覆盖旧版本
2. 只有 `accepted` 或 `edited` 状态的版本才能作为"当前生效版本"
3. 人工可以随时回溯到任意历史版本
4. 修订时只修改有 issue 的部分，保留其他内容不变

### 3.5 结构化审查输出

Reviewer 的输出必须是结构化的、有证据的、可执行的。

**审查流程**：

```python
async def review_chapter(version_id: str, db: Database) -> ReviewReport:
    """
    章节审查流程。
    
    1. 加载章节版本和上下文包
    2. 并行执行 4 类检查
    3. 汇总 issue 列表
    4. 严重度分级
    5. 生成修复建议
    """
    version = await db.get_chapter_version(version_id)
    context = await assemble_context_package(project_id, version.chapter_number, db)  # 实时组装，不查缓存表
    
    # 并行检查
    results = await asyncio.gather(
        check_world_consistency(version, context),
        check_character_behavior(version, context),
        check_timeline(version, context),
        check_quality(version, context),
    )
    
    # 汇总
    all_issues = []
    for result in results:
        all_issues.extend(result)
    
    # 严重度分级
    for issue in all_issues:
        issue.severity = classify_severity(issue)
        issue.fix_type = determine_fix_type(issue)
    
    return ReviewReport(
        chapter_version_id=version_id,
        issues=sorted(all_issues, key=lambda i: severity_rank(i.severity)),
        overall_score=calculate_overall_score(all_issues),
        summary=generate_summary(all_issues),
    )
```

**严重度分级标准**：

| 严重度 | 定义 | 示例 | 处理规则 |
|--------|------|------|----------|
| **critical** | 事实性错误，读者会出戏 | 已死角色再次出现；违反已揭示的核心设定 | 必须修复，阻塞入库 |
| **major** | 质量或一致性问题，影响阅读体验 | 角色行为与其性格明显冲突；节奏严重失衡 | 建议修复，人工可确认跳过 |
| **minor** | 小瑕疵，不影响整体 | 用词重复；描写可以更生动 | 记录但不阻塞 |
| **info** | 建议性内容 | 可以增加伏笔；这里可以埋钩子 | 仅供参考 |

**可执行性要求**：
- 每个 `critical`/`major` issue 必须有 `evidence_quote`（原文片段）
- 每个 issue 必须有 `suggested_fix`（具体修复建议）
- `fix_type` 必须是以下之一：
  - `patch`：局部修改（改几句话）
  - `rewrite_scene`：重写整个场景
  - `confirm`：人工确认（"这里其实是对的，因为..."）
  - `register_setting`：确认新设定并登记入库

### 3.6 Issue-Driven 修订机制

自动修订不是整章重写，而是**针对 issue 做 patch**。

```python
class RevisionInput(BaseModel):
    """修订输入"""
    version_id: str                           # 要修订的版本
    issues: list[ReviewIssue]                 # 要修复的 issue 列表
    max_rounds: int = 2                       # 最大修订轮数

class RevisionOutput(BaseModel):
    """修订输出"""
    new_version_id: str
    patches_applied: list[Patch]              # 应用的 patch 列表
    issues_fixed: list[str]                   # 已修复 issue IDs
    issues_remaining: list[str]               # 未修复 issue IDs
    new_issues_introduced: list[ReviewIssue]  # 修订引入的新问题（关键！）

class Patch(BaseModel):
    """单个 patch"""
    issue_id: str                             # 对应 issue
    original_text: str                        # 原文
    revised_text: str                         # 修改后
    location: str                             # 位置
```

**修订规则**：
1. **最多 2 轮自动修订**，之后必须人工确认
2. 每轮只修复 `critical` 和 `major` 的 `patch` 类型 issue
3. `rewrite_scene` 类型的 issue 不自动修复，直接上报人工
4. 修订后必须再次审查，检查是否引入新问题
5. 如果第二轮审查发现新问题数量 > 0，停止自动修订，上报人工

```
初稿生成
   │
   ▼
第一轮审查
   │
   ├── 无 critical/major → 通过，人工确认
   │
   └── 有 critical/major
          │
          ▼
   Issue-Driven Patch（只改有问题的部分）
          │
          ▼
   第二轮审查
          │
          ├── 无新问题 → 通过，人工确认
          │
          └── 有新问题 → 停止自动修订，上报人工
```

### 3.6.1 RevisionHandler 节点

RevisionHandler 是独立的图节点，不是 Writer 的重用。**Writer 只做初稿，RevisionHandler 只做 patch。**

```python
async def revision_handler_node(state: Phase1State) -> Phase1State:
    """
    RevisionHandler 节点 —— 按 issue 产出局部 patch。
    
    输入：
    - state.current_version_id → 从 SQLite 加载父版本
    - state.review_report_id → 从 SQLite 加载审查报告
    - state.revision_round → 当前轮次
    
    流程：
    1. 从 SQLite 加载父版本和审查报告
    2. 筛选 patchable issues（critical/major 且 fix_type == patch）
    3. 按位置排序（从后往前，避免位置偏移）
    4. 逐个应用 patch（精确替换 evidence_quote）
    5. 创建新版本（version_type="revision"）
    6. revision_round += 1
    7. 保存新版本到 SQLite
    8. 更新 state.current_version_id 指向新版本
    """
    
    # 加载业务对象（通过 ID）
    parent = await db.get_chapter_version(state["current_version_id"])
    report = await db.get_review_report(state["review_report_id"])
    
    # 筛选 patchable issues
    patchable = [
        i for i in report.issues
        if i.severity in ("critical", "major") and i.fix_type == "patch"
    ]
    
    # 按位置从后往前排序
    patchable.sort(key=lambda i: i.evidence_location, reverse=True)
    
    # 应用 patch
    content = parent.content
    patches = []
    for issue in patchable:
        if issue.evidence_quote in content:
            content = content.replace(issue.evidence_quote, issue.suggested_fix, 1)
            patches.append(Patch(
                issue_id=issue.issue_id,
                original_text=issue.evidence_quote,
                revised_text=issue.suggested_fix,
                location=issue.evidence_location,
            ))
    
    # 创建新版本
    new_version = ChapterVersion(
        chapter_number=parent.chapter_number,
        project_id=parent.project_id,
        version_number=parent.version_number + 1,
        version_type="revision",
        parent_version_id=parent.version_id,
        title=parent.title,
        content=content,
        word_count=len(content),
        issues_fixed=[p.issue_id for p in patches],
        issues_remaining=[i.issue_id for i in report.issues 
                         if i.issue_id not in [p.issue_id for p in patches]],
        generation_metadata={"patches": [p.model_dump() for p in patches],
                            "revision_round": state["revision_round"] + 1},
        changed_by="ai",
    )
    
    # 保存
    await db.save_chapter_version(new_version)
    
    # 更新 state（只更新 ID 和计数器）
    state["current_version_id"] = new_version.version_id
    state["revision_round"] += 1
    return state
```

### 3.6.2 HumanConfirm 节点

HumanConfirm 是 CLI 交互节点，负责：**展示审查结果 → 获取用户决策 → 创建 accepted 版本 → 更新 chapter_heads**。

```python
async def human_confirm_node(state: Phase1State) -> Phase1State:
    """
    HumanConfirm 节点 —— CLI 人工确认。
    
    流程：
    1. 从 SQLite 加载当前版本和审查报告
    2. 打印审查摘要（issue 列表、严重度、修复建议）
    3. 展示章节正文（预览模式）
    4. 提示用户选择：
       [a]ccept — 接受，创建 accepted 版本
       [e]dit   — 用编辑器修改，创建 edited 版本
       [r]eject — 退回重写（Planner 重新制定目标）
       [b]ack   — 回退到历史版本
    5. 根据选择执行相应操作
    6. 更新 chapter_heads 指向最终版本
    7. 触发 Planner 生成摘要
    """
    
    version = await db.get_chapter_version(state["current_version_id"])
    report = await db.get_review_report(state["review_report_id"]) if state["review_report_id"] else None
    
    # 打印审查摘要
    if report:
        print(f"\n📋 审查报告（{len(report.issues)} 个问题）")
        for issue in report.issues:
            print(f"  [{issue.severity.upper()}] {issue.category}: {issue.issue_description[:60]}")
    
    # 用户决策
    choice = input("\n[a]ccept / [e]dit / [r]eject / [b]ack ? ").strip().lower()
    
    if choice == "a":
        # 创建 accepted 版本
        accepted = ChapterVersion(
            **version.model_dump(exclude={"version_id", "version_type", "created_at"}),
            version_id=generate_id(),
            version_type="accepted",
            parent_version_id=version.version_id,
            changed_by="human",
        )
        await db.save_chapter_version(accepted)
        await db.update_chapter_head(version.chapter_number, version.project_id,
                                     current_version_id=accepted.version_id,
                                     accepted_version_id=accepted.version_id)
        state["current_version_id"] = accepted.version_id
        state["status"] = "summarizing"  # 下一步 Planner 生成摘要
        
    elif choice == "e":
        # 打开编辑器
        edited_content = open_editor(version.content)
        edited = ChapterVersion(
            **version.model_dump(exclude={"version_id", "version_type", "content", "created_at"}),
            version_id=generate_id(),
            version_type="edited",
            parent_version_id=version.version_id,
            content=edited_content,
            word_count=len(edited_content),
            changed_by="human",
        )
        await db.save_chapter_version(edited)
        await db.update_chapter_head(version.chapter_number, version.project_id,
                                     current_version_id=edited.version_id,
                                     accepted_version_id=edited.version_id)
        state["current_version_id"] = edited.version_id
        state["status"] = "summarizing"
        
    elif choice == "r":
        state["status"] = "planning"  # 退回 Planner 重新制定目标
        state["revision_round"] = 0
        state["current_version_id"] = None
        
    elif choice == "b":
        # 列出历史版本供选择
        versions = await db.get_version_chain(version.chapter_number, version.project_id)
        # ... 用户选择后回退
        
    return state
```

### 3.7 写作上下文包（Context Package）

Phase 1 的 RAG 不是通用文档检索，而是**小说专用的上下文组装**。

**上下文包的分区结构**：

```python
class ContextPackage(BaseModel):
    """写作上下文包"""
    
    # === 分区 1：硬约束（必须遵守，注入 prompt 最前）===
    # - 角色当前状态（位置、境界、情感）
    # - 已揭示的设定（不能重复作为新设定引入）
    # - 时间线位置（当前是哪一天，接下来该发生什么）
    # - 禁忌事项（用户明确不想出现的内容）
    # - 本章必须完成的事项（obligations）
    hard_constraints: list[HardConstraint]
    
    # === 分区 2：软参考（建议遵循，可灵活处理）===
    # - 相关世界观设定（与本章场景相关的地理、文化等）
    # - 角色背景信息（出场角色的历史、关系）
    # - 参考风格样本（用户提供的样章）
    soft_references: list[SoftReference]
    
    # === 分区 3：最近剧情（前 3 章摘要 + 关键片段）===
    # - 前3章的 structured summary
    # - 上一章结尾的 500 字原文（保证衔接）
    # - 当前开放的 plot thread 列表
    recent_plot: RecentPlot
    
    # === 分区 4：角色状态快照 ===
    # - 每个出场角色的当前状态卡片
    # - 角色间未解决的冲突
    character_states: list[CharacterStateSnapshot]
    
    # === 分区 5：伏笔线索 ===
    # - 已埋下未回收的伏笔（planted）
    # - 本章应该回收的伏笔（due）
    # - 已经过期的伏笔（overdue，需要处理）
    foreshadowing: list[ForeshadowingItem]
    
    # === 分区 6：本章目标 ===
    # - 本章必须发生的事件
    # - 情感走向
    # - 钩子（章末悬念）
    # - 字数目标
    chapter_goal: ChapterGoal
```

**ContextPackage 不是事实源**——它不做持久化存储，每个节点需要时从 SQLite 现有表实时组装。如需复现某次生成结果，在 `chapter_versions.generation_metadata` 中保存当次 context snapshot 的 JSON 副本。

```python
class ChapterVersion(BaseModel):
    # ... 其他字段 ...
    generation_metadata: dict = {}     # 保存当次 context snapshot JSON，用于复现
```

**上下文组装规则**：
1. 总 token 默认不超过 **32K**（可配置，上限 64K），预留空间给生成输出
2. 硬约束优先级最高，放在 prompt 最前面
3. 最近剧情只保留前 3 章摘要 + 上一章结尾 300 字
4. 不出场的角色不加载其详细档案
5. 已回收的伏笔不加载
6. 超出预算时优先裁剪软参考，其次减少最近剧情章数，硬约束不裁剪

### 3.8 新手创建向导

"新手优先"不能是口号，必须是具体的产品流。

```python
class OnboardingStep(BaseModel):
    """向导步骤"""
    step_number: int
    title: str
    description: str                        # 向用户说明的话
    field_key: str                          # 对应的字段
    is_required: bool
    ai_can_suggest: bool                    # AI 是否可以自动生成建议
    suggestion_prompt: str | None = None    # 生成建议的 prompt

ONBOARDING_STEPS = [
    OnboardingStep(
        step_number=1,
        title="题材选择",
        description="你想写什么类型的小说？",
        field_key="genre",
        is_required=True,
        ai_can_suggest=False,
    ),
    OnboardingStep(
        step_number=2,
        title="核心灵感",
        description="用一句话描述你的核心创意（主角+目标+障碍）",
        field_key="core_hook",
        is_required=True,
        ai_can_suggest=False,
    ),
    OnboardingStep(
        step_number=3,
        title="主角设定",
        description="主角叫什么名字？什么背景？",
        field_key="protagonist",
        is_required=True,
        ai_can_suggest=True,
        suggestion_prompt="根据题材和核心灵感，建议一个适合的主角设定",
    ),
    OnboardingStep(
        step_number=4,
        title="读者预期",
        description="你希望读者读这本书时有什么感受？（如：爽、燃、甜、虐）",
        field_key="target_reader_expectation",
        is_required=True,
        ai_can_suggest=True,
    ),
    OnboardingStep(
        step_number=5,
        title="禁忌事项",
        description="有什么内容是你绝对不想出现的？（如：绿帽、虐主、死女主）",
        field_key="taboos",
        is_required=False,
        ai_can_suggest=False,
    ),
    OnboardingStep(
        step_number=6,
        title="目标规模",
        description="你打算写多长？",
        field_key="target_word_count",
        is_required=False,
        ai_can_suggest=True,
    ),
    OnboardingStep(
        step_number=7,
        title="书名确认",
        description="给小说起个名字吧（AI 也可以建议几个）",
        field_key="title",
        is_required=False,
        ai_can_suggest=True,
        suggestion_prompt="根据以上所有信息，建议 3 个书名",
    ),
]
```

**向导交互设计**：
- CLI 模式下，逐步提问，AI 实时生成建议
- 用户可以随时跳过（非必填项），也可以随时修改已填内容
- 完成后自动生成 `ProjectSetting` 和初始角色卡
- 向导结果直接保存到 SQLite，不经过复杂处理

### 3.9 工作流编排

Phase 1 的 LangGraph 工作流非常简单，重点是验证单章质量，不是编排复杂度。

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

# Phase 1 状态 —— 只存 ID 和轻量状态，不存完整业务对象
class Phase1State(TypedDict):
    messages: Annotated[list, add_messages]
    project_id: str                    # 项目 ID
    chapter_number: int                # 当前章节号
    current_version_id: str | None     # chapter_versions.version_id（当前版本指针）
    review_report_id: str | None       # review_reports.report_id（当前审查报告指针）
    revision_round: int                # 0=初稿, 1=第1轮修订, 2=第2轮修订
    status: str  # "idle" | "planning" | "assembling" | "writing" | "reviewing" | "revising" | "human_confirm" | "summarizing" | "done"

# 创建图
builder = StateGraph(Phase1State)

# 6 个节点（4 核心 Agent + 2 流程节点）
builder.add_node("planner", planner_node)           # 制定章节目标
builder.add_node("context_manager", context_manager_node)  # 组装上下文包
builder.add_node("writer", writer_node)             # 生成初稿（只做初稿，不做修订）
builder.add_node("reviewer", reviewer_node)         # 审查
builder.add_node("revision_handler", revision_handler_node)  # issue-driven patch（按 issue 局部修改）
builder.add_node("human_confirm", human_confirm_node)        # CLI 人工确认 + 创建 accepted 版本

# 入口
builder.set_entry_point("planner")

# 主流程：planner -> context_manager -> writer -> reviewer
builder.add_edge("planner", "context_manager")
builder.add_edge("context_manager", "writer")
builder.add_edge("writer", "reviewer")

# 审查后路由
builder.add_conditional_edges(
    "reviewer",
    review_router,
    {
        "pass": "human_confirm",     # 无 critical/major，进入人工确认
        "revise": "revision_handler", # 有 critical/major 且未满 2 轮，进入修订
        "human": "human_confirm",    # 满 2 轮仍有问题，进入人工确认（带未修复 issue）
    }
)

# 修订后回到审查
builder.add_edge("revision_handler", "reviewer")

# 人工确认后结束
builder.add_edge("human_confirm", END)

# 编译（SQLite checkpoint）
memory = SqliteSaver.from_conn_string("novelforge.db")
app = builder.compile(checkpointer=memory)
```

### 3.10 评测集设计

Phase 1 必须有明确的评测标准，否则无法判断是否该进入 Phase 2。

**评测集构成**：
- 3 个题材：玄幻（修仙）、都市（异能）、科幻（星际）
- 每个题材验证 1-3 章闭环
- 每个题材使用不同的项目设定

**评测指标**：

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| **结构化审查通过率** | > 80% | 无 critical/major issue 的章节比例 |
| **质量评分** | > 6/10 | Reviewer 的 overall_score 均值 |
| **人工返工率** | < 30% | 需要人工大幅修改的章节比例 |
| **修订不引入新问题** | 100% | 第二轮审查新问题数 = 0 |
| **设定一致性** | 100% | critical issue 中 world_consistency = 0 |
| **角色行为一致性** | > 85% | character_behavior issue 中 major 以下比例 |
| **Reviewer-人工金标一致率** | > 70% | Reviewer 严重度判断与人工判断的一致比例 |

**人工金标流程（防止自评循环）**：
1. 每个题材抽取 1 章（共 3 章）作为金标样本
2. 人工独立审查这 3 章，标注 issue 和严重度（不参考 Reviewer 结果）
3. 对比 Reviewer 与人工的判断，计算一致率
4. 一致率 < 70% 时，需要调整 Reviewer prompt 后再测

**评测流程**：
1. 为每个题材创建独立项目
2. 运行新手向导生成项目设定
3. 人工编写前 1-2 章作为种子（提供上下文）
4. 让系统闭环生成第 2-4 章（每章经过完整审查-修订-确认流程）
5. 每章收集 ReviewReport
6. 抽取金标样本进行人工独立审查
7. 汇总指标，判断是否达标

---

## 4. Phase 2 设计概要：卷级连续性

Phase 2 的目标是验证"AI 能否在连续 10 章中保持设定和角色的一致性"。

### 4.1 新增 Agent

在 Phase 1 的 4 个 Agent 基础上增加 2 个：

| Agent | 职责 | 引入理由 |
|-------|------|----------|
| **WorldBuilder** | 结构化世界观管理、设定快照、一致性检查 | 10 章后设定量超过上下文窗口，需要结构化存储和检索 |
| **CharacterDesigner** | 角色弧线追踪、关系图谱、状态演变 | 多章后角色状态变化需要追踪 |

### 4.2 新增存储

- **PostgreSQL** 替代 SQLite（数据量增大，需要并发支持）
- **Qdrant** 向量存储（索引设定、角色、章节摘要，支持语义检索）

### 4.3 新增功能

- 世界设定表 + 设定快照
- 角色状态表 + 弧线追踪
- 伏笔表（planted/due/overdue/resolved 状态机）
- 章节摘要表（结构化摘要，用于跨章上下文）
- 时间线事件表
- 简单 Web 界面（查看章节、审核、编辑）

### 4.4 验证标准

- 自动连续生成 10 章无需人工干预
- 跨章设定漂移检测 < 5%
- 角色行为一致性 > 85%
- 伏笔正确回收率 > 70%

---

## 5. Phase 3 设计概要：完整产品化

Phase 3 的目标是构建完整的、可面向用户的产品。

### 5.1 拆分专业 Agent

在 Phase 2 的 6 个 Agent 基础上拆分 4 个专业 Agent：

| Agent | 职责 |
|-------|------|
| **PlotPlanner** | 宏观大纲规划、卷战略、节奏控制 |
| **StyleEngine** | 风格提取、编译、一致性控制 |
| **LoreKeeper** | RAG 知识库管理、拆书分析 |
| **ConflictResolver** | 多 Agent 分歧仲裁、反极化 |

### 5.2 新增基础设施

- **Redis**：会话缓存、实时状态
- **Celery / ARQ**：异步任务队列（批量章节生成）
- **WebSocket**：实时推送 Agent 执行状态
- **LangSmith / Langfuse**：可观测性
- **Studio Web 工作台**：完整 UI
- **TUI 控制台**：终端交互

### 5.3 完整功能

- 从灵感到成书的全自动流水线
- 批量章节生产
- 分叉时间线（检查点时间旅行）
- 风格模板市场
- 拆书分析（从参考小说学习结构）
- 多模型路由（规划/写作/审查用不同模型）
- 完整的人工审核体系

---

## 6. 终态架构愿景（参考）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NovelForge 终态架构                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                │
│  │   Studio Web  │   │  TUI 控制台   │   │  REST API    │                │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                │
│         └──────────────────┬──────────────────┘                         │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────┐                  │
│  │           LangGraph Runtime + Supervisor             │                  │
│  │  Planner │ WorldBuilder │ CharacterDesigner          │                  │
│  │  Writer  │ StyleEngine  │ Reviewer                   │                  │
│  │  LoreKeeper │ ConflictResolver │ Human Gate          │                  │
│  └─────────────────────────┬─────────────────────────────┘                  │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────┐                  │
│  │  PostgreSQL │ Qdrant │ Redis │ Checkpoint Saver      │                  │
│  └─────────────────────────────────────────────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. 数据库设计（全阶段）

### 7.1 Phase 1 表结构（SQLite）

```sql
-- 项目表
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    title TEXT,
    genre TEXT NOT NULL,
    protagonist_name TEXT NOT NULL,
    protagonist_background TEXT,
    core_hook TEXT NOT NULL,
    target_reader_expectation TEXT,
    taboos TEXT,  -- JSON array
    target_word_count INTEGER DEFAULT 100000,
    tone TEXT DEFAULT '热血',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 角色表
CREATE TABLE characters (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    aliases TEXT,  -- JSON array
    role_type TEXT DEFAULT 'protagonist',
    profile TEXT,  -- JSON: age, appearance, personality, abilities, background
    importance INTEGER DEFAULT 3,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 角色状态追踪（每章更新）
CREATE TABLE character_states (
    id TEXT PRIMARY KEY,
    character_id TEXT REFERENCES characters(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    current_location TEXT,
    current_cultivation TEXT,
    emotional_state TEXT,
    active_relationships TEXT,  -- JSON array
    unresolved_issues TEXT,     -- JSON array
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 章节版本表（核心表）
CREATE TABLE chapter_versions (
    version_id TEXT PRIMARY KEY,
    chapter_number INTEGER NOT NULL,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    version_type TEXT NOT NULL,  -- draft, revision, accepted, edited
    parent_version_id TEXT REFERENCES chapter_versions(version_id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    review_report_id TEXT,
    issues_fixed TEXT,          -- JSON array of issue_ids
    issues_remaining TEXT,      -- JSON array of issue_ids
    change_description TEXT,
    changed_by TEXT NOT NULL,   -- ai, human
    created_at TEXT DEFAULT (datetime('now'))
);

-- 章节指针表（HEAD）
CREATE TABLE chapter_heads (
    chapter_number INTEGER PRIMARY KEY,
    project_id TEXT NOT NULL,
    current_version_id TEXT REFERENCES chapter_versions(version_id),
    accepted_version_id TEXT REFERENCES chapter_versions(version_id),
    UNIQUE(project_id, chapter_number)
);

-- 审查报告表
CREATE TABLE review_reports (
    report_id TEXT PRIMARY KEY,
    chapter_version_id TEXT REFERENCES chapter_versions(version_id),
    overall_score REAL DEFAULT 0,
    summary TEXT,
    issues TEXT,  -- JSON array of ReviewIssue
    created_at TEXT DEFAULT (datetime('now'))
);

-- 设定快照表
CREATE TABLE setting_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,  -- JSON array
    importance INTEGER DEFAULT 3,
    version INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 伏笔追踪表
CREATE TABLE foreshadowings (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    description TEXT NOT NULL,
    planted_in_chapter INTEGER,
    expected_resolve_chapter INTEGER,
    actual_resolve_chapter INTEGER,
    status TEXT DEFAULT 'planted',  -- planted, due, overdue, resolved
    created_at TEXT DEFAULT (datetime('now'))
);

-- 章节摘要表
CREATE TABLE summaries (
    id TEXT PRIMARY KEY,
    chapter_number INTEGER NOT NULL,
    project_id TEXT REFERENCES projects(id),
    plot_summary TEXT,
    key_events TEXT,           -- JSON array
    characters_appeared TEXT,  -- JSON array
    character_changes TEXT,    -- JSON object
    settings_referenced TEXT,  -- JSON array
    foreshadowing_planted TEXT,   -- JSON array
    foreshadowing_resolved TEXT,  -- JSON array
    emotional_tone TEXT,
    pacing_score REAL,
    word_count INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 7.2 Phase 2/3 新增表

```sql
-- 世界设定树（Phase 2）
CREATE TABLE world_settings (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    category TEXT NOT NULL,
    parent_id TEXT REFERENCES world_settings(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    importance INTEGER DEFAULT 3,
    tags TEXT,
    version INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 角色关系（Phase 2）
CREATE TABLE character_relationships (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES characters(id),
    target_id TEXT REFERENCES characters(id),
    relation_type TEXT NOT NULL,
    description TEXT,
    strength INTEGER DEFAULT 3,
    evolution TEXT  -- JSON array
);

-- 时间线事件（Phase 2）
CREATE TABLE timeline_events (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    event_description TEXT NOT NULL,
    chapter_number INTEGER,
    event_order INTEGER NOT NULL,
    involved_characters TEXT,  -- JSON array
    created_at TEXT DEFAULT (datetime('now'))
);

-- 人工决策记录（Phase 3）
CREATE TABLE human_decisions (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    chapter_version_id TEXT REFERENCES chapter_versions(version_id),
    decision_type TEXT NOT NULL,
    decision TEXT NOT NULL,  -- approve, reject, revise
    comment TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

## 8. 生产部署（分阶段）

### 8.1 Phase 1 部署

```bash
# 纯 pip 安装
pip install novelforge

# 初始化
novelforge init

# 运行（CLI 交互）
novelforge create-project
novelforge write-chapter --project mynovel --chapter 4
```

不需要 Docker，不需要任何外部服务。一个 SQLite 文件就是全部数据。

### 8.2 Phase 2 部署

```yaml
# docker-compose.yml (Phase 2)
version: "3.8"
services:
  api:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/novelforge
      - QDRANT_URL=http://qdrant:6333
    ports:
      - "8000:8000"
  
  postgres:
    image: pgvector/pgvector:pg16
    volumes:
      - pgdata:/var/lib/postgresql/data
  
  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdata:/qdrant/storage
  
  web:
    build: ./web
    ports:
      - "3000:3000"

volumes:
  pgdata:
  qdata:
```

### 8.3 Phase 3 部署

在 Phase 2 基础上增加 Redis、Celery Worker、监控等组件。

---

> **文档变更记录**
> 
> | 版本 | 日期 | 变更 |
> |------|------|------|
> | v1 | 2026-05-16 | 初始版本，终态理想架构 |
> | v2 | 2026-05-16 | 基于 review 重构为三阶段落地架构，v1 收敛为单章闭环 |
