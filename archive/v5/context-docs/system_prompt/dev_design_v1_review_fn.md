# Songyan V1.0 技术方案 Review（综合版）

> 来源：AI review + 人工 review 综合
> 目标：在扩为完整实施文档前，修复结构性问题
> 状态：**阻塞性 issue 必须修复后才能进入开发**

---

## 一、阻塞性 issue（必须修复）

### 1. V1.0 范围过大：9 套组合 → 收窄到 2 套

**问题**：方案写"支持 3 种题材 × 3 种创作模式"，实际变成 9 套组合，每套都需要 prompt、规则、评测种子和人工金标。第一阶段无法验证。

**修复方案**：

```text
V1.0 验证目标：
跑通单题材、单章闭环，并证明系统能通过配置切换创作模式。

必交付（验收标准）：
- xuanhuan genre profile（完整）
- webnovel + hybrid mode profile（2 种模式）
- 全部 10 个 Agent/节点
- SQLite + 版本链 + 快照表
- 3 个种子项目评测

预置但不验收（配置文件存在，流程跑通即可）：
- urban / scifi genre profile（基础配置，不跑评测）
- literary mode profile（初版配置，不跑评测）

V1.1 补齐：
- urban / scifi 完整评测
- literary mode 完整评测 + PolyphonyPlanner
```

**原因**：V1.0 的核心假设是"系统能否可控地生产、审查、修订、沉淀上下文"，不是"能否覆盖所有题材和模式"。收窄范围才能深度验证。

---

### 2. HumanConfirm → Settlement → Summary 的顺序错误

**问题**：技术方案第 5.3 节写"每章 accept 后必须执行 SettlementExtractor"，但流程描述中 HumanConfirm 的位置不够清晰。SettlementExtractor 必须在人工确认**之后**，否则会把未接受版本写进事实源。

**正确顺序**：

```text
Writer
  -> RuleAuditor + LLMAuditor
  -> ReviewMerger（合并）
  -> LiteraryAuditor（诊断，不阻塞）
  -> RevisionHandler（最多 2 轮）
  -> HumanConfirm（accept / edit / reject / back）
  -> SettlementExtractor（仅 accept 后执行）
  -> SummaryWriter（基于 accepted version + StateSettlement 生成摘要）
  -> done
```

**修复**：在技术方案第 4.2 节和第 7 节（开发阶段）中明确此顺序。SettlementExtractor 和 SummaryWriter 都属于"结算与闭环"阶段，且都只在 accept 后触发。

---

### 3. 缺少 SummaryWriter / ChapterSummary 归属

**问题**：技术方案第 4.3 节"关键输出物"里没有 `ChapterSummary`，9 个 Agent 一览表里也没有摘要生成节点。但下一章的上下文高度依赖摘要（RecentPlot 需要前 N 章摘要）。

**修复方案**：

增加一个轻量节点：

| 节点 | 类型 | 职责 | 输入 |
|------|------|------|------|
| **SummaryWriter** | LLM Service（非独立 Agent） | 基于 accepted version + StateSettlement 生成结构化摘要 | accepted 正文 + settlement 结果 |

输出写入 `summaries` 表，包含：plot_summary, key_events, characters_appeared, emotional_tone 等。

**注意**：SummaryWriter 不需要独立 Agent 级别的复杂度，可以是一个轻量 LLM 调用函数，由 SettlementExtractor 阶段完成后触发。

---

### 4. CreativeDirector 和 GoalPlanner 的边界模糊

**问题**：GoalPlanner 产出事件、情感弧、钩子；CreativeDirector 又产出创作意图、张力地图、禁忌清单。两者容易重复规划，甚至互相矛盾。

**修复方案——明确边界**：

| Agent | 回答什么问题 | 不做什么 |
|-------|-------------|----------|
| **GoalPlanner** | "本章要发生什么"——硬剧情事件（1-3 个关键事件、情感走向、字数目标、章节类型） | 不回答"怎么写"、不输出风格约束 |
| **CreativeDirector** | "这章应该怎么产生张力、避免什么惯性"——创作意图、张力地图、禁忌清单、允许裂隙 | **不得新增硬剧情事件**，只能重排/解释/施压已有的 ChapterGoal |

**关键约束**：CreativeDirector 的 `required_tensions` 必须基于 GoalPlanner 的 `target_events` 推导，不能新增独立事件。如果 CreativeDirector 发现 GoalPlanner 的事件无法产生足够张力，应在 CreativeBrief 中标记 `tension_gap: true`，供人工判断是否需要调整 ChapterGoal，而不是自行添加事件。

---

### 5. ReviewMerger 节点未定义

**问题**：技术方案 4.2 流程图中出现了"MergedReviewReport"，但 4.1 Agent 一览表中没有 ReviewMerger 节点。LangGraph 编排时会漏掉这个节点。

**修复方案**：

ReviewMerger 是一个**轻量合并节点**（非 LLM Agent），负责将 RuleAuditResult + LLMAuditResult 合并为 MergedReviewReport。

```python
# 可以是一个轻量函数或独立节点
def review_merger_node(state: Phase1State) -> Phase1State:
    rule_audit = load_rule_audit(state["current_version_id"])
    llm_audit = load_llm_audit(state["review_report_id"])
    merged = merge_audit_reports(rule_audit, llm_audit)
    save_merged_report(merged)
    state["review_report_id"] = merged.id
    return state
```

**耗时**：< 10ms（纯内存操作，无 LLM 调用）。

在技术方案 Agent 一览表中增加：

| 节点 | 类型 | 职责 | 耗时 |
|------|------|------|------|
| **ReviewMerger** | 轻量合并节点（非 LLM Agent） | 合并 RuleAuditResult + LLMAuditor 为 MergedReviewReport | < 10ms |

---

### 6. LiteraryAuditor "不阻塞"过于绝对——应能影响 RevisionHandler

**问题**：当前设计 LiteraryAuditor 完全不阻塞，诊断只是"报告装饰"，无法影响实际修订。这会导致有价值裂隙被 RevisionHandler 误修。

**修复方案——分级阻塞策略**：

```python
class LiteraryObservation(BaseModel):
    observation_type: Literal[...]
    severity: Literal["notice", "suggestion", "highlight", "protected"]
    preserve: bool = False           # 是否建议保护（不修改）
    protected_elements: list[str] = []  # 被保护的文本片段
```

**行为规则**：

| 模式 | conceptual_idling | character_autonomy | valuable_fissure |
|------|------------------|-------------------|-----------------|
| **网文** | notice（不阻塞） | notice（不阻塞） | protected（RevisionHandler 必须遵守） |
| **严肃文学** | suggestion（不阻塞，但人工确认时高亮） | suggestion（不阻塞，但人工确认时高亮） | protected（RevisionHandler 必须遵守） |
| **混合** | notice | notice | protected |

**关键约束**：
- 默认不阻塞 accept
- `valuable_fissure` 自动输出 `protected_elements`
- RevisionHandler 在筛选 patchable_issues 时必须排除 `protected_elements` 范围内的文本
- 严肃文学模式下，`conceptual_idling` 和 `character_autonomy` 可在人工确认界面高亮为"建议关注"，但仍需人工主动选择是否修

---

## 二、重要改进（强烈建议修复）

### 7. RuleAuditor 首屏钩子检测不能纯代码判断

**问题**：前 300 字是否有"吸引力事件"，纯代码很难可靠判断。代码能检测"是否有冲突词/动作/对话"，但无法判断"是否真的有吸引力"。

**修复方案——拆分检测**：

| 检测层 | 负责内容 | 方式 |
|--------|----------|------|
| **RuleAuditor（代码）** | 前 300 字是否为空泛环境描写、是否无动作/对话/冲突词 | 正则/规则 |
| **LLMAuditor（语义）** | 是否真的有吸引力事件（情感冲击/意外发现等） | LLM 判断 |
| **合并维度** | `narrative_hook`（统一在 MergedReviewReport 中） | ReviewMerger |

**具体规则**：
- RuleAuditor 检测"差的钩子特征"（纯环境描写、无人称出现、无动作动词）→ 直接报 major
- RuleAuditor 检测"好的钩子特征"（冲突词、动作动词、对话）→ pass，不深入判断质量
- LLMAuditor 对前 300 字做语义判断"是否有吸引力事件" → 综合评分
- 两者合并为 `narrative_hook` 维度

---

### 8. 缺少 Pipeline Plugin 协议

**问题**：技术方案有低耦合方向（CreativeModeProfile 配置化），但没有写"Agent 插件接口"。这是扩展性的核心，V1.0 不定义后续会债台高筑。

**修复方案**：

```python
from typing import Protocol, runtime_checkable
from enum import Enum

class PipelineStage(str, Enum):
    PRE_WRITE = "pre_write"
    WRITE = "write"
    AUDIT = "audit"
    REVISION = "revision"
    SETTLEMENT = "settlement"
    POST_SETTLEMENT = "post_settlement"

@runtime_checkable
class PipelineNode(Protocol):
    """管线节点协议——所有 Agent/Service/节点必须实现"""
    
    node_id: str
    stage: PipelineStage
    enabled_by_default: bool = True
    
    async def run(self, ctx: RunContext) -> NodeResult:
        """
        执行节点逻辑。
        
        约束：
        - 不直接访问数据库（只读 ctx 中的快照）
        - 写操作通过返回 NodeResult，由 orchestrator 统一写入
        """
        ...

class RunContext(BaseModel):
    """节点运行上下文——只读，Agent 不能修改"""
    project_id: str
    chapter_number: int
    mode_id: str
    current_version_id: str | None
    # 只读快照（从 SQLite 加载）
    chapter_goal: ChapterGoal | None = None
    creative_brief: CreativeBrief | None = None
    # ... 其他必要快照
    
class NodeResult(BaseModel):
    """节点运行结果——由 orchestrator 统一处理"""
    node_id: str
    success: bool
    output: dict = Field(default_factory=dict)  # 结构化输出
    db_operations: list[DBOperation] = []        # 数据库操作请求（不直接执行）
    next_stage: PipelineStage | None = None      # 建议下一 stage

class DBOperation(BaseModel):
    """数据库操作请求"""
    operation: Literal["insert", "update"]
    table: str
    data: dict
```

**核心原则**：Agent 不直接改数据库，只返回结构化结果 → orchestrator 统一写入。这是保证"SQLite 唯一事实源"不被动摇的技术约束。

---

### 9. CreativeModeProfile 需要更具体的驱动能力

**问题**：当前只有权重描述，不足以驱动流程。需要能真正改变审查、修订、上下文裁剪和阻塞规则。

**修复方案——增加驱动字段**：

```python
class CreativeModeProfile(BaseModel):
    id: str
    name: str
    
    # 各阶段启用的节点
    enabled_nodes: dict[str, list[str]] = Field(default_factory=dict)
    # {
    #   "pre_write": ["goal_planner", "creative_director"],
    #   "write": ["writer"],
    #   "audit": ["rule_auditor", "llm_auditor", "review_merger", "literary_auditor"],
    #   "revision": ["revision_handler"],
    #   "settlement": ["settlement_extractor", "summary_writer"]
    # }
    
    # 审查维度权重
    audit_weights: dict[str, float] = Field(default_factory=dict)
    
    # 哪些维度可阻塞入库
    blocking_dimensions: list[str] = Field(default_factory=list)
    # 网文: ["world_consistency", "character_behavior", "timeline", "genre_numerical"]
    # 严肃文学: ["world_consistency", "character_behavior", "timeline"]
    #   （conceptual_idling 不阻塞，但人工确认时高亮）
    
    # 修订策略
    revision_policy: RevisionPolicy
    
    # 上下文裁剪策略
    context_policy: ContextPolicy  # default / character_focused / theme_focused
    
    # 文学性诊断策略
    literary_policy: LiteraryPolicy  # 定义哪些 observation_type 升级为 protected
```

```python
class RevisionPolicy(BaseModel):
    """修订策略——不同模式下修订优先级不同"""
    priority_dimensions: list[str]       # 优先修复的维度
    protected_dimensions: list[str]     # 保护的维度（不自动修）
    max_auto_rounds: int = 2
    
    # 网文：优先修节奏、钩子、爽点兑现
    # 严肃文学：避免抹平裂隙，修概念空转和人物工具化
    # 混合：critical 必修，major 人工确认

class LiteraryPolicy(BaseModel):
    """文学性诊断策略"""
    protected_observation_types: list[str] = ["valuable_fissure"]
    highlight_observation_types: list[str] = []  # 人工确认时高亮
    # 严肃文学：highlight = ["conceptual_idling", "character_autonomy"]
```

---

### 10. Repository 层需要技术约束防止 Agent 绕过事实源

**问题**：文档写了"SQLite 是唯一事实源"，但缺乏技术约束。Agent 可能直接拿 DB connection 写入，破坏规则。

**修复方案**：

```
数据访问分层：

┌─────────────────────────────────────┐
│  Agent 层（只读 ctx，返回结果）       │  ← 不直接访问 DB
├─────────────────────────────────────┤
│  Orchestrator 层（调用 service）      │  ← 协调节点执行
├─────────────────────────────────────┤
│  Service 层（业务逻辑）               │  ← 处理 NodeResult，决定写入
├─────────────────────────────────────┤
│  Repository 层（CRUD）                │  ← 唯一的数据库写入入口
├─────────────────────────────────────┤
│  SQLite（唯一事实源）                 │
└─────────────────────────────────────┘
```

**技术约束**：
1. Agent 层不直接拿 DB connection
2. 写操作集中在 `UnitOfWork` 或 Service 层
3. `chapter_versions`、`character_states`、`review_reports` 都通过专门 repository 创建
4. 对 accepted version、current head、settlement 写入使用**事务**
5. Repository 层记录所有写入操作日志（用于审计和调试）

---

### 11. 开发阶段 Task 分配有误

**问题**：Phase 4 写了"Task 016-019"，但 Task 017（Quality Utils）和 Task 018（Craft Card Prompts）应该在 Phase 2 完成——Writer Agent 需要 Craft Card，RuleAuditor 需要 Quality Utils。

**修复方案——重新分配**：

```
Phase 1：基础设施（Task 001-006）
  项目初始化、模型、Schema、Repository、Genre Profile、CreativeModeProfile

Phase 2：写前管线 + 写作基础设施（Task 007-011 + 017-018）
  CLI 创建项目、GoalPlanner、CreativeDirector、ContextManager、Writer
  Quality Utils（RuleAuditor 依赖）、Craft Card Prompts（Writer 依赖）

Phase 3：审查与修订（Task 012-015）
  RuleAuditor、LLMAuditor、LiteraryAuditor、RevisionHandler

Phase 4：结算与闭环（Task 016 + 019 + SummaryWriter）
  SettlementExtractor、HumanConfirm、SummaryWriter、LangGraph 编排、集成测试
```

---

## 三、验收指标修复

### 12. 补齐缺失指标

技术方案第 8 节缺少以下关键指标：

| 缺失指标 | 目标 | 来源 |
|---------|------|------|
| **章末钩子达标率** | 100% | 最后 200 字有有效悬念 |
| **人物语言区分度** | > 70% | 人工评分 > 7 的章节比例 |
| **AI 与人工金标一致率** | > 70% | critical/major 重叠率 |
| **状态结算 setting_key 准确率** | > 90% | setting_key 唯一 + source_quote 存在 |

### 13. 修正过于绝对的指标

| 原指标 | 问题 | 修正 |
|--------|------|------|
| `概念空转段落数 = 0` | 严肃文学模式下会误杀有意保留的抽象描写 | 网文/混合：`conceptual_idling major = 0`；严肃文学：`conceptual_idling unresolved = 0`（允许人工标记"有意保留"） |
| `审查漏检率 < 20%` | V1.0 阶段可能太难 | 先设 `< 35%`，V1.1 再降到 `< 20%` |

---

## 四、建议新增的章节

### 14. Pipeline Plugin 协议（新增小节）

说明每个节点怎么注册、输入输出是什么、如何启停。参考上面的 `PipelineNode` Protocol 定义。

### 15. RunContext 与数据访问边界（新增小节）

明确 Agent 不能直接改数据库，只能返回结构化结果。定义 `RunContext` 和 `NodeResult` 的数据模型。

### 16. ReviewIssue 标准模型（新增小节）

统一定义审查 issue 的数据模型，尤其要包含：

```python
class ReviewIssue(BaseModel):
    dimension: str                          # 审查维度
    severity: Literal["critical", "major", "minor", "info"]
    evidence_quote: str                     # 原文证据（critical/major 必须有）
    evidence_location: str                  # 位置
    suggested_action: str                   # 建议操作
    is_blocking: bool                       # 是否阻塞入库
    protected_by_literary_audit: bool = False  # 是否被 LiteraryAuditor 保护
```

### 17. RevisionPolicy（新增小节）

不同模式下修订策略不同。参考上面的 `RevisionPolicy` 数据模型。

### 18. 最小可运行切片（MVP 定义，新增小节）

第一阶段不要一次开发 19 个 Task。先定义 vertical slice：

```
最小可运行切片（V1.0 MVP）：
1. 创建项目（xuanhuan + webnovel）
2. 输入一章人工种子
3. GoalPlanner 制定 ChapterGoal
4. CreativeDirector 生成 CreativeBrief
5. ContextManager 组装 ContextPackage
6. Writer 生成下一章
7. RuleAuditor 规则检测（< 200ms）
8. LLMAuditor 语义审查
9. HumanConfirm accept
10. SettlementExtractor 状态结算
11. SummaryWriter 生成摘要
12. 验证下一章上下文正确继承

此切片跑通后，再叠加：
- LiteraryAuditor 文学性诊断
- RevisionHandler issue-driven 修订（最多 2 轮）
- hybrid mode 切换验证
- 完整 3 种子项目评测
```

---

## 五、项目结构遗漏文件

技术方案第 6 节项目结构缺少以下文件：

```diff
  prompts/
+   ├── summary_writer.md           # 章节摘要生成 Prompt
+   └── planner_settlement.md       # SettlementExtractor LLM extraction Prompt

  src/songyan/
+   ├── agents/review_merger.py     # 或作为 utils 中的轻量函数
+   └── utils/numerical_validator.py # 玄幻数值公式验证

  src/songyan/models/
+   ├── creative_mode.py            # CreativeModeProfile, CreativeBrief, Tension
+   └── literary.py                 # LiteraryObservation, LiteraryAuditResult
```

---

## 六、待对齐问题的确认答案

技术方案第 10 节的 6 个待对齐问题，综合 review 后的建议：

| 问题 | 确认答案 |
|------|----------|
| **LLM 选型** | 默认 DeepSeek-chat（通过 litellm 环境变量配置），不硬编码。V1.0 不实现多模型路由，但 litellm 切换模型不需要改业务代码。 |
| **评测集执行** | **先 mock 数据跑通流程**（Phase 4 前期），再用真实题材跑评测（Phase 4 后期）。3 个种子项目评测在开发中后期准备。 |
| **CLI 交互深度** | HumanConfirm 做简单选择（a/e/r/b），edit 调用系统默认编辑器（`$EDITOR` 环境变量）。不嵌入复杂编辑器。 |
| **Prompt 管理方式** | **直接用 `prompts/*.md` 文件 + Python 字符串拼接**。Jinja2 属于"可选但非必须"，V1.0 不需要模板引擎的复杂度。 |
| **Token 预算** | **默认 32K，支持手动调整到 48K/64K**。通过 `ContextBudget.total_budget` 配置。不需要动态检测模型窗口大小。 |
| **开发节奏** | **独立模块可并行**（如 RuleAuditor 工具函数与 GoalPlanner 可同时开发），**LangGraph 编排必须在所有 Agent 跑通后串行接入**。Phase 1-2 内部可并行，Phase 3-4 串行。 |

---

## 七、修复优先级总结

```
P0（阻塞开发）：
  [ ] Issue 1: V1.0 范围收窄到 xuanhuan + webnovel/hybrid
  [ ] Issue 2: 明确 HumanConfirm → Settlement → Summary 顺序
  [ ] Issue 3: 增加 SummaryWriter 节点
  [ ] Issue 4: 明确 GoalPlanner 与 CreativeDirector 边界
  [ ] Issue 5: 定义 ReviewMerger 节点

P1（强烈建议）：
  [ ] Issue 6: LiteraryAuditor 影响 RevisionHandler（protected_elements）
  [ ] Issue 7: 首屏钩子拆分为代码检测 + LLM 判断
  [ ] Issue 8: 增加 Pipeline Plugin 协议
  [ ] Issue 9: CreativeModeProfile 增加驱动字段
  [ ] Issue 10: Repository 层技术约束
  [ ] Issue 11: 修正 Task 分配到正确 Phase

P2（重要但非阻塞）：
  [ ] Issue 12: 补齐缺失验收指标
  [ ] Issue 13: 修正过于绝对的指标
  [ ] Issue 14-18: 新增 5 个小节
  [ ] Issue 19: 补齐项目结构遗漏文件
```

---

> **最终判断**：技术方案方向可行，核心设计（八层防线、双层审查、CreativeModeProfile、状态快照）正确。修复 P0 的 5 个阻塞性 issue 后，可作为开发底稿进入实现。
