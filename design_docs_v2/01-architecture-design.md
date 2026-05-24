# Songyan（松烟）— 多 Agent 中文小说写作系统

## 完整架构设计文档（V2.0）

> **版本**: V2.0.0
> **项目代号**: Songyan（松烟）
> **日期**: 2026-05-24
> **状态**: 设计稿（Design Draft）
> **核心变更**: 基于 v2 review 全面修正——流程顺序修复、Planner 拆分、Reviewer 双层化、CreativeModeProfile 引入、CreativeDirector/LiteraryAuditor 新增

---

## 目录

- [1. 设计哲学与核心判断](#1-设计哲学与核心判断)
- [2. V1.0 阶段目标与验证标准](#2-v10-阶段目标与验证标准)
- [3. 系统架构总览](#3-系统架构总览)
- [4. CreativeModeProfile 创作模式系统](#4-creativemodeprofile-创作模式系统)
- [5. Genre Profile 系统](#5-genre-profile-系统)
- [6. 核心 Agent 设计](#6-核心-agent-设计)
- [7. 写作工艺层 Prompt 架构](#7-写作工艺层-prompt-架构)
- [8. 双层审查体系](#8-双层审查体系)
- [9. 状态结算机制](#9-状态结算机制)
- [10. 数据事实源设计](#10-数据事实源设计)
- [11. 版本管理模型](#11-版本管理模型)
- [12. 上下文 Token 预算管理](#12-上下文-token-预算管理)
- [13. 工作流编排](#13-工作流编排)
- [14. 评测集设计](#14-评测集设计)
- [15. 演进路线图](#15-演进路线图)
- [16. 数据库设计](#16-数据库设计)

---

## 1. 设计哲学与核心判断

### 1.1 核心判断

V1.0 唯一要验证的假设：

> **"每生成一章，系统都知道它为什么这么写、哪里可能错、改了什么、状态发生了什么变化、下一章应该继承什么。"**

V1.0 不是要"写出伟大小说"，而是要跑通"可控地生产、审查、修订、沉淀上下文"的工程闭环。伟大小说是 V2.0+ 的目标。

### 1.2 设计原则

**原则 1：质量防线分层**
写作质量不是 Writer 一个人的事，而是六层防线的共同结果：
- 第一层：CreativeModeProfile（创作模式选择）
- 第二层：CreativeDirector（创作意图与张力地图）
- 第三层：Genre Profile（题材规则约束）
- 第四层：写作工艺层 Prompt（文学质量约束）
- 第五层：Writer 生成（创作执行）
- 第六层：Reviewer 双层审查（RuleAuditor + LLMAuditor）
- 第七层：LiteraryAuditor（文学性诊断）
- 第八层：人工确认（最终门控）

**原则 2：Agent 代表"可替换能力"，不是"人"**
不要设计成"总编辑 Agent、作家 Agent、评论家 Agent"。应该设计成"目标规划能力、上下文组装能力、规则审查能力、文学诊断能力"。同一套底层，换不同配置，就能服务长篇网文、类型小说、严肃文学。

**原则 3：数据先行，指标说话**
每个功能必须有明确的评测指标。"质量评分 > 6.5/10"太主观，改为"设定硬错误数 = 0""AI 腔规则命中数 < 2""人工大改比例 < 30%"。

**原则 4：状态闭环**
每一章完成后，不只是生成摘要，而是完成一次完整的状态结算——角色状态、设定快照、伏笔追踪、数值账本全部更新。确保下一章的上下文是准确的。

**原则 5：能删则删，晚点再加**
如果某个功能不是验证当前假设所必需的，就不做。但 CreativeDirector 和 LiteraryAuditor 作为轻量文学性模块，是 V1.0 的一部分——它们防止系统产出"流畅但平庸"的内容。

### 1.3 技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| Python | 3.11+ | 异步优先 `async/await` |
| Pydantic | v2 | 所有数据模型，严格类型校验 |
| LangGraph | >= 0.2 | 工作流编排 |
| LangChain | >= 0.3 | LLM 接口 |
| litellm | latest | 多模型统一接口 |
| SQLite | 内置 | V1.0 唯一事实源 |
| Click | latest | CLI 框架 |
| structlog | latest | 结构化日志 |
| tiktoken | latest | Token 计数 |

---

## 2. V1.0 阶段目标与验证标准

### 2.1 范围

V1.0 目标：**单章闭环验证**（生成 -> 审查 -> 修订 -> 状态结算 -> 确认），每个题材 1-3 章。

### 2.2 验证标准

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| 设定硬错误数 | 0 | critical world_consistency = 0 |
| 人工大改比例 | < 30% | 需人工大幅修改的章节比例 |
| 审查漏检率 | < 20% | 人工发现但 AI 没发现的问题比例 |
| 修订后新问题数 | 0 | 第二轮审查新问题数 = 0 |
| 设定一致性 | 100% | critical world_consistency = 0 |
| 角色行为一致性 | > 85% | character_behavior major 以下比例 |
| AI 腔规则命中数 | < 2 处/章 | style_ai_tells 出现次数 |
| 首屏钩子达标率 | 100% | 前 300 字有吸引力事件 |
| 状态结算字段准确率 | > 90% | character_update.old_value 与数据库一致率 |
| 概念空转段落数 | 0 | "抽象概念多、身体感少"的段落 |
| 疲劳词命中数 | < 3 处/章 | style_fatigue_words 出现次数 |

**移除指标**：overall_score > 6.5/10（太主观，容易自欺）。

---

## 3. 系统架构总览

### 3.1 架构图

```
用户输入 (CLI)
    |
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Songyan V1.0 单章闭环                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CreativeModeProfile（创作模式配置）                              │
│  ├── mode: webnovel (genre_control)   网文模式                    │
│  ├── mode: literary (literary_fissure) 严肃文学模式                │
│  └── mode: hybrid                     混合模式                    │
│       |                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              GoalPlanner Agent                       │        │
│  │  1. 项目设定收集（7 步向导）                          │        │
│  │  2. 章节目标制定 (ChapterGoal)                        │        │
│  └─────────────────────────────────────────────────────┘        │
│       |                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              CreativeDirector Agent  ⭐               │        │
│  │  （写前生成创作意图+张力地图+禁忌清单，不直接写正文）   │        │
│  │  输出: CreativeBrief（结构化，入 Prompt）             │        │
│  └─────────────────────────────────────────────────────┘        │
│       |                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              ContextManager Agent                    │        │
│  │  1. 加载 Genre Profile                              │        │
│  │  2. 按 Token 预算组装 Context Package                │        │
│  │  3. 约束层 + 工艺层 + 题材规则 + CreativeBrief 注入   │        │
│  │  4. 上下文快照保存                                    │        │
│  └─────────────────────────────────────────────────────┘        │
│       |                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              Writer Agent                            │        │
│  │  1. 按场景生成正文（受全部约束层约束）                 │        │
│  │  2. 场景间 ### 分隔                                   │        │
│  │  3. 新设定标记 [[新设定:描述]]                         │        │
│  │  4. 章末钩子                                          │        │
│  └─────────────────────────────────────────────────────┘        │
│       |                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              Reviewer Agent（双层审查）               │        │
│  │  ┌──────────────┐  ┌──────────────────────┐         │        │
│  │  │ RuleAuditor  │  │ LLMAuditor           │         │        │
│  │  │（代码检测）   │  │（语义审查）          │         │        │
│  │  │ • 疲劳词     │  │ • 角色行为一致性     │         │        │
│  │  │ • AI 腔      │  │ • 叙事节奏           │         │        │
│  │  │ • 段落长度   │  │ • 对话区分度         │         │        │
│  │  │ • 首300字   │  │ • 信息倾倒           │         │        │
│  │  │ • 字数统计   │  │ • 设定一致性         │         │        │
│  │  │ • 数值公式   │  │ • 多感官描写         │         │        │
│  │  │              │  │ • ShowDon'tTell     │         │        │
│  │  └──────────────┘  └──────────────────────┘         │        │
│  │       |                    |                        │        │
│  │       └────────┬───────────┘                        │        │
│  │                ▼                                    │        │
│  │         MergedReviewReport                          │        │
│  └─────────────────────────────────────────────────────┘        │
│       |                                                          │
│  ┌────┴────┐                                                    │
│  ▼         ▼                                                    │
│  通过      有问题                                               │
│  |         |                                                    │
│  ▼         ▼                                                    │
│  |    Issue-Driven Patch (RevisionHandler)                     │
│  |    最多 2 轮                                                  │
│  |         |                                                    │
│  |         ▼                                                    │
│  |    Reviewer（重新审查）                                       │
│  |         |                                                    │
│  └────┬────┘                                                    │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              LiteraryAuditor Agent  ⭐               │        │
│  │  （Reviewer 之后，人工之前）                          │        │
│  │  • 人物工具化检测                                    │        │
│  │  • 概念空转检测                                      │        │
│  │  • 过度平滑/陌生性损耗诊断                            │        │
│  │  • 有价值裂隙标记（不修复，供人工判断）               │        │
│  │  输出: LiteraryObservation[]（诊断，不阻塞）          │        │
│  └─────────────────────────────────────────────────────┘        │
│       |                                                          │
│       ▼                                                          │
│  Human Confirm                                                   │
│  accept → SettlementExtractor → 摘要 → SQLite → done            │
│  edit   → 编辑器修改 → accept                                    │
│  reject → GoalPlanner（重新规划）                                │
│  back   → 指定版本                                               │
│                                                                  │
│  存储：SQLite 单库（唯一事实源）                                  │
│  表：projects, characters, character_states,                     │
│      chapter_versions, review_reports, setting_snapshots,        │
│      foreshadowings, summaries, numerical_ledgers,               │
│      creative_briefs, literary_observations                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 六层质量防线

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: CreativeModeProfile（创作模式选择）                 │
│  - webnovel | literary | hybrid                              │
│  - 决定启用哪些 Agent、审查维度、修订策略                      │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: CreativeDirector（创作意图与张力地图）               │
│  - 本章张力、价值冲突、禁忌清单、文学性模式                    │
│  - 输出结构化 CreativeBrief，入 Writer Prompt                 │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: Genre Profile（题材规则约束）                       │
│  - 疲劳词表、爽点类型、节奏规则、数值约束                      │
│  - 题材专用审查维度                                           │
├─────────────────────────────────────────────────────────────┤
│  LAYER 4: 写作工艺层 Prompt（文学质量约束）                    │
│  - 黄金开篇纪律、段落节奏、对话工艺                            │
│  - 情感动作化、信息释放控制、感官沉浸                          │
├─────────────────────────────────────────────────────────────┤
│  LAYER 5: Writer Agent（创作执行）                            │
│  - 按场景生成、对话交替、章末钩子                              │
│  - 温度 0.7，有创造性                                        │
├─────────────────────────────────────────────────────────────┤
│  LAYER 6: Reviewer 双层审查（RuleAuditor + LLMAuditor）       │
│  - RuleAuditor: 疲劳词/AI腔/段落长度/首300字（代码，稳定便宜） │
│  - LLMAuditor: 角色/节奏/对话/信息倾倒/设定一致性（LLM，语义） │
├─────────────────────────────────────────────────────────────┤
│  LAYER 7: LiteraryAuditor（文学性诊断）                        │
│  - 人物工具化、概念空转、过度平滑、有价值裂隙                  │
│  - 诊断不阻塞，供人工判断                                      │
├─────────────────────────────────────────────────────────────┤
│  LAYER 8: 人工确认（最终门控）                                 │
│  - accept / edit / reject / back                             │
│  - 人工金标对比                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. CreativeModeProfile 创作模式系统

### 4.1 设计

CreativeModeProfile 是 V1.0 最关键的**低耦合设计**。它让"严肃文学"和"长篇网文"变成不同配置，而不是不同代码路径。

```python
class CreativeModeProfile(BaseModel):
    """创作模式配置文件——决定整个工作流的 Agent 组合与参数"""
    id: str                                    # "webnovel" | "literary" | "hybrid"
    name: str                                  # "网文模式" | "严肃文学" | "混合模式"
    
    # 各阶段启用的 Agent
    enabled_agents: dict[str, list[str]] = Field(default_factory=dict)
    # {
    #   "pre_write": ["goal_planner", "creative_director"],
    #   "write": ["writer"],
    #   "post_write": ["rule_auditor", "narrative_reviewer", "literary_auditor"],
    #   "revision": ["revision_handler"],
    #   "settlement": ["settlement_extractor"]
    # }
    
    # 审查维度权重（Reviewer 用）
    audit_weights: dict[str, float] = Field(default_factory=dict)
    
    # 审查维度启用列表（RuleAuditor + LLMAuditor 的合并维度）
    active_audit_dimensions: list[str] = []
    
    # 修订策略
    revision_policy: str = "standard"          # "standard" | "selective" | "minimal"
    
    # 容错阈值
    tolerance: dict[str, float] = Field(default_factory=dict)
    # {
    #   "max_ai_tells": 2.0,      # 每章最大 AI 腔命中数
    #   "max_fatigue_words": 3.0,  # 每章最大疲劳词命中数
    #   "max_cliche_risk": 1.0,    # 每章最大套路化风险标记数
    # }
    
    # 上下文裁剪策略
    context_pruning_strategy: str = "default"   # "default" | "character_focused" | "theme_focused"
    
    # 成功指标定义
    success_metrics: dict[str, float] = Field(default_factory=dict)
```

### 4.2 三种模式配置

**网文模式（V1.0 默认）**：
```python
webnovel_mode = {
    "id": "webnovel",
    "name": "网文模式",
    "enabled_agents": {
        "pre_write": ["goal_planner", "creative_director"],
        "write": ["writer"],
        "post_write": ["rule_auditor", "narrative_reviewer", "literary_auditor"],
        "revision": ["revision_handler"],
        "settlement": ["settlement_extractor"]
    },
    "audit_weights": {
        "world_consistency": 1.0,
        "character_behavior": 1.0,
        "narrative_pacing": 1.2,        # 网文节奏权重更高
        "narrative_hook": 1.2,          # 钩子权重更高
        "style_ai_tells": 1.0,
        "style_fatigue_words": 1.0,
        "genre_numerical": 1.0,
        "cliche_risk": 0.8,             # 网文允许一定套路
        "character_autonomy": 0.6,      # 网文人物工具化容忍度更高
        "conceptual_idling": 1.0,
    },
    "revision_policy": "standard",
    "tolerance": {
        "max_ai_tells": 2.0,
        "max_fatigue_words": 3.0,
        "max_cliche_risk": 2.0,         # 网文允许套路
    },
    "success_metrics": {
        "pacing_score_threshold": 7.0,
        "hook_coverage": 1.0,           # 100% 钩子覆盖
        "satisfaction_density": 0.8,    # 爽点密度
    }
}
```

**严肃文学模式（V1.0 可配置）**：
```python
literary_mode = {
    "id": "literary",
    "name": "严肃文学模式",
    "enabled_agents": {
        "pre_write": ["goal_planner", "creative_director", "polyphony_planner"],
        "write": ["writer"],
        "post_write": ["literary_auditor", "character_autonomy_auditor", "conceptual_idling_auditor"],
        "revision": ["selective_revision_handler"],
        "settlement": ["settlement_extractor"]
    },
    "audit_weights": {
        "world_consistency": 1.0,
        "character_behavior": 1.2,      # 人物行为权重更高
        "style_ai_tells": 1.0,
        "conceptual_idling": 1.5,       # 概念空转检测权重更高
        "cliche_risk": 1.5,             # 套路化零容忍
        "character_autonomy": 1.5,      # 人物自治权重更高
        "valuable_fissure": 1.2,        # 有价值裂隙保护
        "narrative_pacing": 0.8,        # 节奏权重降低（文学允许慢）
        "narrative_hook": 0.6,          # 钩子权重降低
    },
    "revision_policy": "selective",     # 选择性修订，保护裂隙
    "tolerance": {
        "max_ai_tells": 1.0,
        "max_fatigue_words": 2.0,
        "max_cliche_risk": 0.0,         # 零容忍套路
    },
    "success_metrics": {
        "polyphony_score": 7.0,         # 复调强度
        "concept_grounding": 1.0,       # 概念落地率
        "fissure_preservation": 0.8,    # 裂隙保留率
    }
}
```

**混合模式**：
```python
hybrid_mode = {
    "id": "hybrid",
    "name": "混合模式",
    "enabled_agents": {
        "pre_write": ["goal_planner", "creative_director"],
        "write": ["writer"],
        "post_write": ["rule_auditor", "narrative_reviewer", "literary_auditor"],
        "revision": ["revision_handler"],
        "settlement": ["settlement_extractor"]
    },
    # 权重介于两者之间
    "revision_policy": "standard",
}
```

### 4.3 低耦合扩展机制

新增创作模式只需：
1. 新建一个 JSON 配置文件
2. 注册到 `CreativeModeRegistry`
3. 无需修改任何 Agent 代码

```python
class CreativeModeRegistry:
    """创作模式注册表——管线 + 插件架构"""
    _modes: dict[str, CreativeModeProfile] = {}
    
    @classmethod
    def register(cls, mode: CreativeModeProfile) -> None:
        cls._modes[mode.id] = mode
    
    @classmethod
    def get(cls, mode_id: str) -> CreativeModeProfile:
        if mode_id not in cls._modes:
            raise ValueError(f"未知创作模式: {mode_id}")
        return cls._modes[mode_id]
    
    @classmethod
    def list_modes(cls) -> list[str]:
        return list(cls._modes.keys())
```

---

## 5. Genre Profile 系统

### 5.1 设计

每个题材一个 JSON 配置文件，V1.0 预置 3 个：

```
genres/
├── xuanhuan.json   # 玄幻
├── urban.json      # 都市
└── scifi.json      # 科幻
```

### 5.2 数据模型

```python
class GenreProfile(BaseModel):
    """题材配置文件"""
    id: str                        # xuanhuan / urban / scifi
    name: str                      # 玄幻 / 都市 / 科幻
    language: str = "zh"
    
    # 章节类型（指导 Writer 的节奏设计）
    chapter_types: list[str] = []
    
    # 疲劳词表（RuleAuditor 检测用）
    fatigue_words: list[str] = []
    
    # 爽点类型（指导 Writer 的事件设计）
    satisfaction_types: list[str] = []
    
    # 是否有数值体系
    has_numerical_system: bool = False
    
    # 是否有战力成长
    has_power_scaling: bool = False
    
    # 节奏规则
    pacing_rule: str = ""
    
    # Writer 专用规则
    writer_rules: list[str] = []
    
    # Reviewer 专用审查焦点
    reviewer_focus: list[str] = []
    
    # 启用的审查维度（从 ReviewCategory 枚举中选）
    active_audit_dimensions: list[str] = []
    
    # 题材禁忌
    taboos: list[str] = []
```

### 5.3 玄幻配置示例

```json
{
  "id": "xuanhuan",
  "name": "玄幻",
  "chapter_types": ["战斗章", "布局章", "过渡章", "回收章"],
  "fatigue_words": [
    "冷笑", "蝼蚁", "倒吸凉气", "瞳孔骤缩", "不可置信",
    "轰然炸裂", "满场死寂", "难以置信", "仿佛", "不禁", "宛如", "竟然"
  ],
  "satisfaction_types": ["打脸", "升级突破", "收益兑现", "智斗碾压", "身份揭示", "底牌亮出"],
  "has_numerical_system": true,
  "has_power_scaling": true,
  "pacing_rule": "三章内必有明确反馈：打脸、收益兑现、信息反转、地位变化",
  "writer_rules": [
    "设定不可吃书：前文确立的设定数值后文不可无升级过程地随意改变",
    "金手指四维约束：能力上限（明确天花板）、附加代价（寿命/体力/副作用）、触发条件（特定场景）、成长路径（与剧情绑定）",
    "同质资源重复吞噬必须写明衰减，不得默认全额结算",
    "不要用'暴涨''海量''难以估量'跳过数值结算",
    "正文中出现的系统提示必须与 POST_SETTLEMENT 一致"
  ],
  "reviewer_focus": [
    "数值一致性（战力/境界是否吃书）",
    "爽点密度是否达标",
    "金手指使用是否符合四维约束",
    "资源结算是否逐笔列出"
  ],
  "active_audit_dimensions": [
    "world_consistency",
    "character_behavior",
    "timeline",
    "new_setting_unregistered",
    "narrative_pacing",
    "narrative_hook",
    "info_dump",
    "dialogue_distinctness",
    "dialogue_subtext",
    "description_sensory",
    "show_dont_tell",
    "style_ai_tells",
    "style_fatigue_words",
    "style_paragraph_rhythm",
    "genre_numerical"
  ],
  "taboos": [
    "主角为推剧情突然仁慈、犯蠢、讲武德",
    "用'暴涨''海量'跳过数值结算",
    "无铺垫的能力觉醒",
    "反派像木桩一样排队送死"
  ]
}
```

---

## 6. 核心 Agent 设计

### 6.1 Agent 总览

| Agent | 核心职责 | 不做什么 | 温度 |
|-------|----------|----------|------|
| **GoalPlanner** | 项目设定收集、章节目标制定 | 不写正文、不做结算 | 目标 0.7 |
| **CreativeDirector** | 写前生成本章创作意图+张力地图+禁忌清单 | 不直接写正文 | 0.7 |
| **ContextManager** | 加载 Genre Profile、组装上下文包、Token 预算管理 | 不做生成、不做审查 | — |
| **Writer** | 按场景生成正文（受全部约束层约束） | 不做审查、不修改设定 | 0.7 |
| **RuleAuditor** | 代码层规则检测（AI 腔/疲劳词/段落/首屏/字数） | 不做语义判断 | — |
| **LLMAuditor** | LLM 语义审查（角色/节奏/对话/设定一致性） | 不做代码检测 | 0.3 |
| **LiteraryAuditor** | 文学性诊断（人物工具化/概念空转/裂隙） | 不阻塞流程、不修改正文 | 0.3 |
| **RevisionHandler** | 按 issue 局部 patch 修订 | 不整章重写 | 0.3 |
| **SettlementExtractor** | 状态结算提取+代码验证+更新 DB | 不写摘要 | 0.3 |
| **HumanConfirm** | CLI 人工确认（accept/edit/reject/back） | 不做自动判断 | — |

### 6.2 GoalPlanner Agent

```python
class GoalPlannerAction(str, Enum):
    COLLECT_PROJECT_SETTING = "collect_project_setting"
    DEFINE_CHAPTER_GOAL = "define_chapter_goal"

class ProjectSetting(BaseModel):
    """项目设定"""
    title: str | None = None
    genre_id: str                              # 引用 GenreProfile.id
    mode_id: str = "webnovel"                  # 引用 CreativeModeProfile.id ⭐ 新增
    protagonist_name: str
    protagonist_background: str
    core_hook: str
    target_reader_expectation: str = ""
    taboos: list[str] = []
    target_word_count: int = 100000
    tone: str = "热血"
    reference_works: list[str] = []
    
class ChapterGoal(BaseModel):
    """章节目标"""
    chapter_number: int
    previous_summary: str = ""
    target_events: list[str] = []
    emotional_arc: str = ""
    hooks: list[str] = []
    obligations: list[str] = []
    word_count_target: int = 3000
    chapter_type: str = ""                     # 从 GenreProfile.chapter_types 选
```

### 6.3 CreativeDirector Agent ⭐ 新增

```python
class CreativeBrief(BaseModel):
    """
    创作导演输出——创作意图与张力地图。
    不直接写正文，而是产出"创作约束与张力地图"。
    """
    mode_id: str                               # webnovel | literary | hybrid
    chapter_goal: ChapterGoal
    creative_intent: str = ""                  # 本章核心创作意图（一句话）
    required_tensions: list[Tension] = []      # 必须制造的张力
    forbidden_patterns: list[str] = []         # 本章必须避开的套路/模式
    allowed_fissures: list[str] = []           # 允许保留的裂隙（文学性）
    style_constraints: list[str] = []          # 风格约束
    reader_contract: str = ""                  # 本章对读者的"承诺"
    polyphony_notes: list[str] = []            # 复调写作指导（文学模式用）

class Tension(BaseModel):
    """张力定义"""
    tension_id: str
    description: str                           # 张力描述
    tension_type: Literal["value_conflict", "information_asymmetry", "power_imbalance", "emotional_contrast", "temporal_pressure"]
    characters_involved: list[str] = []        # 涉及角色
    resolution: str = ""                       # 预期解决方式（或"unresolved"）
    intensity: float = 0.5                     # 强度 0-1
```

### 6.4 ContextManager Agent

```python
class ContextPackage(BaseModel):
    """
    写作上下文包 —— 小说专用的分区上下文注入结构。
    按 Token 预算组装，超出时按优先级裁剪。
    """
    chapter_goal: ChapterGoal
    creative_brief: CreativeBrief | None = None   # ⭐ CreativeDirector 输出
    
    # === 分区 1：硬约束（必须遵守，最高优先级）===
    hard_constraints: list[HardConstraint] = []
    
    # === 分区 2：角色状态快照 ===
    character_states: list[CharacterStateSnapshot] = []
    
    # === 分区 3：最近剧情 ===
    recent_plot: RecentPlot                    # 前 N 章摘要 + 上一章结尾
    
    # === 分区 4：伏笔线索 ===
    foreshadowing: list[ForeshadowingItem] = []
    
    # === 分区 5：软参考（最低优先级，超预算时先裁剪）===
    soft_references: list[SoftReference] = []
    
    # === 分区 6：题材规则（从 GenreProfile 注入）===
    genre_rules: GenreRules | None = None
    
    # === 分区 7：创作模式规则（从 CreativeModeProfile 注入）===
    mode_rules: ModeRules | None = None        # ⭐ 新增
    
    # === 元信息 ===
    estimated_tokens: int = 0
    assembled_at: datetime = Field(default_factory=datetime.now)
    budget_used: float = 0.0                   # 预算使用比例

class HardConstraint(BaseModel):
    type: Literal["character_state", "setting_fact", "timeline", "taboo", "obligation"]
    description: str
    source: str

class CharacterStateSnapshot(BaseModel):
    character_id: str
    name: str
    current_location: str | None = None
    current_cultivation: str | None = None
    emotional_state: str | None = None
    active_relationships: list[str] = []
    unresolved_issues: list[str] = []
    importance_score: float = 0.0              # 本章重要性（主角=1.0，出场=0.8，关联=0.5）

class RecentPlot(BaseModel):
    summaries: list[ChapterSummary]            # 前 N 章摘要
    last_chapter_ending: str = ""              # 上一章结尾 500 字
    open_threads: list[str] = []               # 开放的剧情线

class ForeshadowingItem(BaseModel):
    foreshadowing_id: str
    description: str
    planted_in_chapter: int
    expected_resolve_chapter: int | None = None
    status: Literal["planted", "due", "overdue", "resolved"] = "planted"

class SoftReference(BaseModel):
    type: Literal["world_setting", "character_backstory", "style_sample"]
    content: str
    relevance_score: float = 0.0

class GenreRules(BaseModel):
    """从 GenreProfile 注入 Writer 的规则"""
    genre_id: str = ""
    writer_rules: list[str] = []
    fatigue_words: list[str] = []
    satisfaction_types: list[str] = []
    pacing_rule: str = ""
    taboos: list[str] = []

class ModeRules(BaseModel):                     # ⭐ 新增
    """从 CreativeModeProfile 注入的规则"""
    mode_id: str = ""
    revision_policy: str = "standard"
    tolerance_max_ai_tells: float = 2.0
    tolerance_max_fatigue_words: float = 3.0
    tolerance_max_cliche_risk: float = 2.0
    context_pruning_strategy: str = "default"
```

### 6.5 Writer Agent

```python
class WriterInput(BaseModel):
    context_package: ContextPackage
    chapter_goal: ChapterGoal
    creative_brief: CreativeBrief | None = None    # ⭐ 新增

class WriterOutput(BaseModel):
    content: str                               # 完整正文
    scenes: list[Scene] = []                   # 场景分解
    word_count: int
    generation_metadata: dict = Field(default_factory=dict)

class Scene(BaseModel):
    scene_number: int
    setting: str
    characters_present: list[str]
    key_event: str
    emotional_shift: str = ""
```

### 6.6 RuleAuditor Agent ⭐ 新增（原 Reviewer 的代码检测部分）

```python
class RuleAuditResult(BaseModel):
    """规则检测结果——全部由代码执行，不调用 LLM"""
    auditor_id: str = "rule_auditor"
    
    # AI 腔检测
    ai_tell_matches: list[AiTellMatch] = []
    ai_tell_count: int = 0
    
    # 疲劳词检测
    fatigue_word_matches: list[FatigueWordMatch] = []
    fatigue_word_count: int = 0
    
    # 首屏钩子
    has_opening_hook: bool = False
    
    # 章末钩子
    has_ending_hook: bool = False
    
    # 段落节奏
    paragraph_rhythm_score: float = 0.0        # 0-10
    rhythm_issues: list[str] = []
    
    # 字数统计
    word_count: int = 0
    word_count_target: int = 3000
    word_count_ok: bool = True
    
    # 数值公式检测（玄幻）
    numerical_issues: list[str] = []
    
    # 处理时长
    duration_ms: int = 0

class AiTellMatch(BaseModel):
    pattern: str
    matched_text: str
    location: str                              # "第3段第2句"

class FatigueWordMatch(BaseModel):
    word: str
    count: int
    locations: list[str]
```

### 6.7 LLMAuditor Agent ⭐ 新增（原 Reviewer 的 LLM 审查部分）

```python
class LLMAuditResult(BaseModel):
    """LLM 语义审查结果——需要调用 LLM"""
    auditor_id: str = "llm_auditor"
    issues: list[ReviewIssue] = []
    
    # 各维度评分
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    
    # 文学性维度
    cliche_risk_score: float = 0.0             # 套路化风险 0-10
    character_autonomy_score: float = 0.0      # 人物自治度 0-10
    conceptual_idling_score: float = 0.0       # 概念空转度 0-10
    
    summary: str = ""
    duration_ms: int = 0

class ReviewCategory(str, Enum):
    # === 一致性维度（4 个）===
    WORLD_CONSISTENCY = "world_consistency"
    CHARACTER_BEHAVIOR = "character_behavior"
    TIMELINE = "timeline"
    NEW_SETTING_UNREGISTERED = "new_setting_unregistered"
    
    # === 叙事质量（3 个）===
    NARRATIVE_PACING = "narrative_pacing"
    NARRATIVE_HOOK = "narrative_hook"
    INFO_DUMP = "info_dump"
    
    # === 对话质量（2 个）===
    DIALOGUE_DISTINCTNESS = "dialogue_distinctness"
    DIALOGUE_SUBTEXT = "dialogue_subtext"
    
    # === 描写质量（2 个）===
    DESCRIPTION_SENSORY = "description_sensory"
    SHOW_DONT_TELL = "show_dont_tell"
    
    # === 题材专项（1 个）===
    GENRE_NUMERICAL = "genre_numerical"

class ReviewIssue(BaseModel):
    issue_id: str
    category: ReviewCategory
    severity: Literal["critical", "major", "minor", "info"]
    
    # 证据（必须有）
    evidence_quote: str
    evidence_location: str
    
    # 关联
    related_setting_id: str | None = None
    related_character_id: str | None = None
    
    # 问题说明
    issue_description: str
    expected: str | None = None
    actual: str | None = None
    
    # 修复建议
    suggested_fix: str | None = None
    fix_type: Literal["patch", "rewrite_scene", "confirm", "register_setting"] = "patch"
    
    # 置信度
    confidence: float = 1.0
```

### 6.8 MergedReviewReport ⭐ 新增（RuleAuditor + LLMAuditor 合并报告）

```python
class MergedReviewReport(BaseModel):
    """合并审查报告——RuleAuditor + LLMAuditor 的统一输出"""
    chapter_version_id: str
    
    # RuleAuditor 结果
    rule_audit: RuleAuditResult | None = None
    
    # LLMAuditor 结果
    llm_audit: LLMAuditResult | None = None
    
    # 合并后的 issues（用于 RevisionHandler）
    issues: list[ReviewIssue] = []
    
    # 关键指标
    overall_score: float = 0.0
    ai_tell_count: int = 0
    fatigue_word_count: int = 0
    has_opening_hook: bool = False
    has_ending_hook: bool = False
    
    @property
    def has_critical(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)
    
    @property
    def has_major(self) -> bool:
        return any(i.severity == "major" for i in self.issues)
    
    @property
    def patchable_issues(self) -> list[ReviewIssue]:
        return [i for i in self.issues 
                if i.severity in ("critical", "major") and i.fix_type == "patch"]
    
    # 各维度评分（合并）
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    summary: str = ""
```

### 6.9 LiteraryAuditor Agent ⭐ 新增

```python
class LiteraryObservation(BaseModel):
    """文学性观察——诊断性输出，不阻塞流程"""
    observation_id: str
    observation_type: Literal[
        "character_tooling",           # 人物工具化
        "conceptual_idling",           # 概念空转
        "excessive_smoothing",         # 过度平滑
        "valuable_fissure",            # 有价值裂隙（不是缺陷！）
        "cliche_risk",                 # 套路化风险
        "polyphony_weakness",          # 复调不足
        "authorial_intrusion",         # 作者侵入
    ]
    description: str
    evidence_quote: str | None = None          # 可选证据
    severity: Literal["notice", "suggestion", "highlight"] = "suggestion"
    recommendation: str = ""                   # 建议（不强制修复）
    preserve: bool = False                     # 是否建议保留（对 valuable_fissure）

class LiteraryAuditResult(BaseModel):
    """文学审计结果——不阻塞流程，供人工参考"""
    auditor_id: str = "literary_auditor"
    observations: list[LiteraryObservation] = []
    
    # 综合评分（仅供参考，不阻塞）
    literary_quality_score: float = 0.0        # 0-10
    character_autonomy_score: float = 0.0      # 0-10
    conceptual_grounding_score: float = 0.0    # 概念落地度 0-10
    fissure_preservation_score: float = 0.0    # 裂隙保留度 0-10
    
    summary: str = ""
    duration_ms: int = 0
```

### 6.10 RevisionHandler

```python
class RevisionInput(BaseModel):
    version_id: str
    issues: list[ReviewIssue]                  # 来自 MergedReviewReport.patchable_issues
    max_rounds: int = 2

class Patch(BaseModel):
    issue_id: str
    original_text: str
    revised_text: str
    location: str

class RevisionOutput(BaseModel):
    new_version_id: str
    patches_applied: list[Patch] = []
    issues_fixed: list[str] = []
    issues_remaining: list[str] = []
    new_issues_introduced: list[ReviewIssue] = []
```

### 6.11 SettlementExtractor ⭐ 重命名（原 Planner 的状态结算部分）

```python
class SettlementExtractorInput(BaseModel):
    accepted_version_id: str
    project_id: str
    chapter_number: int

class StateSettlement(BaseModel):
    """章节完成后的结构化状态结算"""
    
    # 角色状态变更
    character_updates: list[CharacterUpdate] = []
    
    # 新设定登记
    new_settings: list[NewSetting] = []
    
    # 伏笔操作
    foreshadowing_updates: list[ForeshadowingUpdate] = []
    
    # 数值变更（玄幻专用）
    numerical_updates: list[NumericalUpdate] = []
    
    # 章末 Hook 状态
    planted_hooks: list[str] = []
    resolved_hooks: list[str] = []
    
    # 验证状态
    validation_status: Literal["valid", "needs_human_review", "failed"] = "valid"
    validation_errors: list[str] = []

class CharacterUpdate(BaseModel):
    character_id: str
    field: str
    old_value: str
    new_value: str
    source_quote: str                           # 原文证据

class NewSetting(BaseModel):
    setting_name: str
    description: str
    source_quote: str
    setting_key: str = ""                      # ⭐ 新增：设定唯一标识符，用于追踪演变

class ForeshadowingUpdate(BaseModel):
    foreshadowing_id: str | None = None
    operation: Literal["plant", "resolve", "update_status"]
    description: str
    expected_resolve_chapter: int | None = None
    source_version_id: str = ""                # ⭐ 新增：关联版本

class NumericalUpdate(BaseModel):
    """数值账本变更"""
    character_id: str
    attribute_name: str                         # 如 "cultivation_level", "spirit_stones"
    opening_value: float
    increments: list[Increment] = []
    decrements: list[Decrement] = []
    closing_value: float

class Increment(BaseModel):
    amount: float
    source: str
    source_quote: str

class Decrement(BaseModel):
    amount: float
    usage: str
    source_quote: str
```

---

## 7. 写作工艺层 Prompt 架构

### 7.1 设计

Writer Prompt 拆分为四层：

```
Writer Prompt = 约束层（动态） + 工艺层（固定模板） + 题材层（GenreProfile） + 创作意图层（CreativeBrief）⭐
```

| 层级 | 内容 | 注入方式 |
|------|------|----------|
| **约束层** | 硬约束、角色状态、本章目标、最近剧情 | ContextManager 动态组装 |
| **工艺层** | 黄金开篇、段落节奏、对话工艺、情感动作化、信息释放 | `prompts/craft_card.md` 固定模板 |
| **题材层** | 题材规则、疲劳词、爽点类型、禁忌 | GenreProfile 动态注入 |
| **创作意图层** | 张力地图、禁忌清单、风格约束、读者契约 | CreativeBrief 动态注入 ⭐ |

### 7.2 工艺层内容

```markdown
## 黄金开篇纪律
- 章节前 300 字必须出现以下之一：冲突事件 / 意外发现 / 危险信号 / 情感冲击
- 禁止以环境描写铺陈开篇（除非环境本身就是冲突）
- 禁止以人物档案式介绍开篇
- 好的开篇：让读者第一句就想知道"然后呢"

## 段落节奏
- 叙述段落：4-6 行
- 对话段落：1-3 行（短促有力）
- 战斗场景：多用短句（5-10 字），制造紧迫感
- 长短交替：2 个长段后必须接 1 个短段
- 移动端阅读：每段不超过 100 字

## 对话工艺
- 每句对话必须推动剧情或揭示性格
- 对话要有潜台词（说 A 想 B）
- 角色间对话要有冲突性，不要和气聊天
- 不同角色的语气要有区分度
- 少用"说道"，多用动作+对话的组合

## 情感描写（Show, Don't Tell）
- 禁止直接写"他很愤怒/很悲伤/很高兴"
- 通过动作、神态、身体反应、环境映射表现情绪
- 好的例子：不写"他很愤怒"，写"他攥紧了拳头，指节泛白，指甲深深嵌进掌心"
- 好的例子：不写"她很难过"，写"她把脸埋进膝盖，肩膀微微发抖，却没有发出声音"

## 信息释放
- 本章只揭示与剧情直接相关的设定
- 背景信息要碎片化融入场景，不要集中倾倒
- 新设定出现时，用剧情冲突带出，不要用旁白解释
- 一个场景最多引入 1 个新设定

## 感官沉浸
- 不要只有视觉描写，激活多感官
- 听觉：风声、脚步声、心跳声、金属碰撞声
- 触觉：温度、质地、疼痛、微风拂面
- 嗅觉：血腥味、花香、烟火气、腐朽味
- 好的描写让读者"身临其境"，而不只是"看到画面"

## 章末钩子
- 最后一段必须留下悬念或冲击
- 禁止用"接下来会发生什么"式的空洞钩子
- 好的钩子类型：
  - 新危机突然出现
  - 一个秘密被意外揭示
  - 关系突然破裂或转变
  - 主角发现真相的一角
  - 反派的真正目的露出冰山一角

## 新设定标记
- 如果必须引入上下文中未提及的新设定，标记为：[[新设定:简要描述]]
- 不要滥用——一章最多 1-2 个新设定
- 标记后继续在正文中自然使用，不要中断叙事解释
```

---

## 8. 双层审查体系

### 8.1 架构

Reviewer 拆分为 **RuleAuditor（代码检测）** 和 **LLMAuditor（语义审查）**，最后合并为 **MergedReviewReport**。

```
章节正文
    |
    ├──▶ RuleAuditor（代码，快速，稳定，便宜）
    |       • AI 腔检测（正则）
    |       • 疲劳词检测（字符串匹配）
    |       • 段落节奏分析（统计）
    |       • 首屏钩子检查（规则）
    |       • 章末钩子检查（规则）
    |       • 字数统计
    |       • 数值公式验证
    |
    └──▶ LLMAuditor（LLM，语义理解，较慢）
            • 设定一致性
            • 角色行为一致性
            • 时间线
            • 叙事节奏
            • 对话区分度
            • 信息倾倒
            • ShowDon'tTell
            • 套路化风险
            • 人物自治度
            |
            ▼
    MergedReviewReport（合并输出）
            |
            ▼
    LiteraryAuditor（文学性诊断，不阻塞）
            |
            ▼
    RevisionHandler / HumanConfirm
```

### 8.2 RuleAuditor 检测规则

```markdown
### AI 腔检测（正则）
以下词语/句式被视为 AI 写作痕迹：
- "不禁""猛然""骤然""陡然" + 意识到/明白/发现
- "这一刻""那一瞬间""那一刻" + 感悟式描写
- "仿佛""似乎""好像" + 过于频繁的抽象比喻
- 过度使用"不可置信""难以置信"
- "天崩地裂""惊天动地"等过度夸张的成语
出现即报，2 处以下 minor，3 处以上 major。

### 疲劳词检测（字符串匹配）
本题材疲劳词表来自 GenreProfile.fatigue_words：
{xuanhuan: [冷笑, 蝼蚁, 倒吸凉气, 瞳孔骤缩, ...]}
同一章内出现 2 次以上即报 minor，3 次以上报 major。

### 首屏钩子检查（规则）
检查前 300 字是否出现吸引力元素之一：
- 冲突事件 / 意外发现 / 危险信号 / 情感冲击
如果没有，报 major（narrative_hook）。

### 段落节奏检查（统计）
统计段落长度分布。如果连续 4 个段落长度差异 < 20%，
报 minor（style_paragraph_rhythm）。

### 字数统计
- 低于 word_count_target * 0.8 → minor
- 低于 word_count_target * 0.5 → major
- 高于 word_count_target * 1.3 → minor

### 数值公式验证（玄幻）
检查正文中出现的数值变化是否满足：
closing_value == opening_value + sum(increments) - sum(decrements)
如果不满足，报 critical（genre_numerical）。
```

### 8.3 LLMAuditor 审查维度

| 编号 | 维度 | 说明 | 严重度下限 |
|------|------|------|-----------|
| 1 | world_consistency | 设定一致性 | critical |
| 2 | character_behavior | 角色行为一致性 | critical |
| 3 | timeline | 时间线矛盾 | critical |
| 4 | new_setting_unregistered | 未登记新设定 | major |
| 5 | narrative_pacing | 节奏起伏（拖沓/仓促） | major |
| 6 | narrative_hook | 叙事钩子质量 | major |
| 7 | info_dump | 信息倾倒 | major |
| 8 | dialogue_distinctness | 对话区分度 | major |
| 9 | dialogue_subtext | 对话潜台词 | minor |
| 10 | description_sensory | 多感官描写 | minor |
| 11 | show_dont_tell | Show don't tell | minor |
| 12 | genre_numerical | 数值一致性（玄幻） | critical |

**说明**：
- 原 `style_ai_tells`、`style_fatigue_words`、`style_paragraph_rhythm` 已移至 RuleAuditor（代码检测）
- `cliche_risk`、`character_autonomy`、`conceptual_idling` 由 LLMAuditor 检测
- `valuable_fissure` 由 LiteraryAuditor 标记

### 8.4 LiteraryAuditor 诊断维度

| 维度 | 说明 | 处理方式 |
|------|------|----------|
| character_tooling | 人物是否像作者意志的执行器 | 记录，不阻塞 |
| conceptual_idling | 抽象概念多、身体感少 | 记录，不阻塞 |
| excessive_smoothing | 过度平滑，失去陌生性 | 记录，不阻塞 |
| valuable_fissure | 可能有价值的异常/裂隙 | **标记为保护，不修复** |
| cliche_risk | 套路化风险 | 记录，minor |
| polyphony_weakness | 复调不足（文学模式） | 记录，不阻塞 |
| authorial_intrusion | 作者声音侵入角色 | 记录，不阻塞 |

**核心原则**：LiteraryAuditor 不阻塞入库，只提供诊断和"保留/修复"建议。`valuable_fissure` 不是缺陷，而是"请人工判断是否保留"。

---

## 9. 状态结算机制

### 9.1 流程

```
HumanConfirm 完成（accept）
    |
    ▼
SettlementExtractor 执行结算提取
    |
    ├── LLM 阅读 accepted 版本正文
    ├── 提取：角色状态变更 / 新设定 / 伏笔操作 / 数值变更
    └── 输出 StateSettlement（结构化 JSON）
    |
    ▼
代码层验证
    |
    ├── character_update.old_value == DB 当前值？
    ├── new_setting.source_quote 在正文中存在？
    ├── new_setting.setting_key 唯一？              ⭐ 新增
    └── numerical_update.closing_value == opening + 增量 - 消耗？
    |
    ▼
验证通过 → 更新 SQLite
    |
    ├── INSERT INTO character_states（永远 INSERT，不 UPDATE）⭐
    ├── INSERT INTO setting_snapshots ...
    ├── UPDATE foreshadowings SET ...（增加 source_version_id）⭐
    └── INSERT INTO numerical_ledgers ...
    |
    ▼
生成人类可读摘要（ChapterSummary）
```

### 9.2 关键规则

1. **StateSettlement 必须通过 Pydantic 验证**
2. **character_update.old_value 必须与数据库当前值一致**（防止 Writer 编造前置状态）
3. **new_setting.source_quote 必须在正文中存在**（防止幻觉）
4. **new_setting.setting_key 必须唯一**（用于追踪同一设定的演变）⭐ 新增
5. **numerical_update 的 closing_value 必须等于公式计算值**（期初 + 增量 - 消耗）
6. **character_states 为快照表，永远 INSERT 新记录，不 UPDATE 旧记录** ⭐ 新增
7. **foreshadowings 增加 source_version_id 字段**（追踪伏笔在哪个版本中被操作）⭐ 新增
8. **验证失败不阻塞**，标记为 `needs_human_review`，进入人工确认
9. **结算完成后才生成 ChapterSummary**，摘要基于结算后的准确状态

---

## 10. 数据事实源设计

### 10.1 三层存储

| 存储 | 用途 | 持久性 | 内容 |
|------|------|--------|------|
| **SQLite** | 唯一长期事实源 | 持久 | 所有业务数据 |
| **Checkpoint** | LangGraph 执行恢复 | 持久 | 仅执行状态（ID + status） |
| **内存** | LLM 上下文 | 重启丢失 | 临时计算 |

### 10.2 SQLite 表结构（V1.0）

```sql
-- 项目
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    title TEXT,
    genre_id TEXT NOT NULL,           -- 关联 GenreProfile
    mode_id TEXT DEFAULT 'webnovel',  -- 关联 CreativeModeProfile ⭐ 新增
    protagonist_name TEXT,
    protagonist_background TEXT,
    core_hook TEXT,
    target_reader_expectation TEXT,
    taboos TEXT,                      -- JSON list
    target_word_count INTEGER DEFAULT 100000,
    tone TEXT DEFAULT '热血',
    reference_works TEXT,             -- JSON list
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 角色
CREATE TABLE characters (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    name TEXT NOT NULL,
    role_type TEXT DEFAULT 'major',   -- major / minor
    profile TEXT,                     -- 完整档案
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 角色状态（每章更新，快照表——永远 INSERT，不 UPDATE）⭐
CREATE TABLE character_states (
    id TEXT PRIMARY KEY,
    character_id TEXT REFERENCES characters(id),
    project_id TEXT,
    chapter_number INTEGER,
    current_location TEXT,
    current_cultivation TEXT,
    emotional_state TEXT,
    active_relationships TEXT,        -- JSON list
    unresolved_issues TEXT,           -- JSON list
    source_version_id TEXT,           -- 从哪个版本结算而来
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 章节版本
CREATE TABLE chapter_versions (
    id TEXT PRIMARY KEY,
    chapter_number INTEGER NOT NULL,
    project_id TEXT REFERENCES projects(id),
    version_number INTEGER NOT NULL,
    version_type TEXT CHECK(version_type IN ('draft', 'revision', 'accepted', 'edited')),
    parent_version_id TEXT REFERENCES chapter_versions(id),
    title TEXT,
    content TEXT NOT NULL,
    word_count INTEGER,
    review_report_id TEXT,
    issues_fixed TEXT,                -- JSON list
    issues_remaining TEXT,            -- JSON list
    generation_metadata TEXT,         -- JSON: 包含 context_snapshot
    change_description TEXT,
    changed_by TEXT CHECK(changed_by IN ('ai', 'human')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, chapter_number, version_number)  -- ⭐ 新增唯一约束
);

-- 章节指针
CREATE TABLE chapter_heads (
    chapter_number INTEGER,
    project_id TEXT,
    current_version_id TEXT REFERENCES chapter_versions(id),
    accepted_version_id TEXT REFERENCES chapter_versions(id),
    PRIMARY KEY (chapter_number, project_id)
);

-- 审查报告
CREATE TABLE review_reports (
    id TEXT PRIMARY KEY,
    chapter_version_id TEXT REFERENCES chapter_versions(id),
    audit_type TEXT CHECK(audit_type IN ('rule', 'llm', 'merged', 'human')),  -- ⭐ 新增
    rule_audit_result TEXT,           -- JSON: RuleAuditResult
    llm_audit_result TEXT,            -- JSON: LLMAuditResult
    issues TEXT,                      -- JSON: list of ReviewIssue
    overall_score REAL,
    summary TEXT,
    dimension_scores TEXT,            -- JSON: dict
    ai_tell_count INTEGER DEFAULT 0,
    fatigue_word_count INTEGER DEFAULT 0,
    has_opening_hook BOOLEAN DEFAULT FALSE,
    has_ending_hook BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文学审计记录 ⭐ 新增表
CREATE TABLE literary_observations (
    id TEXT PRIMARY KEY,
    chapter_version_id TEXT REFERENCES chapter_versions(id),
    observations TEXT,                -- JSON: list of LiteraryObservation
    literary_quality_score REAL,
    character_autonomy_score REAL,
    conceptual_grounding_score REAL,
    fissure_preservation_score REAL,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创作简报 ⭐ 新增表
CREATE TABLE creative_briefs (
    id TEXT PRIMARY KEY,
    chapter_number INTEGER,
    project_id TEXT,
    mode_id TEXT,
    brief_content TEXT,               -- JSON: CreativeBrief
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 设定快照
CREATE TABLE setting_snapshots (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    chapter_number INTEGER,
    setting_key TEXT,                 -- ⭐ 新增：设定唯一标识符
    setting_name TEXT,
    description TEXT,
    source_quote TEXT,
    is_revealed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 伏笔
CREATE TABLE foreshadowings (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    description TEXT,
    planted_in_chapter INTEGER,
    expected_resolve_chapter INTEGER,
    resolved_in_chapter INTEGER,
    status TEXT DEFAULT 'planted',
    source_version_id TEXT,           -- ⭐ 新增：关联版本
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 数值账本（玄幻专用）
CREATE TABLE numerical_ledgers (
    id TEXT PRIMARY KEY,
    character_id TEXT,
    project_id TEXT,
    chapter_number INTEGER,
    attribute_name TEXT,
    opening_value REAL,
    increments TEXT,                  -- JSON: list of Increment
    decrements TEXT,                  -- JSON: list of Decrement
    closing_value REAL,
    source_version_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 章节摘要
CREATE TABLE summaries (
    id TEXT PRIMARY KEY,
    chapter_number INTEGER,
    project_id TEXT,
    plot_summary TEXT,
    key_events TEXT,                  -- JSON list
    characters_appeared TEXT,         -- JSON list
    character_changes TEXT,           -- JSON dict
    settings_referenced TEXT,         -- JSON list
    foreshadowing_planted TEXT,       -- JSON list
    foreshadowing_resolved TEXT,      -- JSON list
    emotional_tone TEXT,
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 11. 版本管理模型

```python
class ChapterVersion(BaseModel):
    version_id: str
    chapter_number: int
    project_id: str
    version_number: int                       # 1, 2, 3...
    version_type: Literal["draft", "revision", "accepted", "edited"]
    parent_version_id: str | None = None
    title: str
    content: str
    word_count: int
    review_report_id: str | None = None
    literary_observation_id: str | None = None  # ⭐ 新增
    issues_fixed: list[str] = []
    issues_remaining: list[str] = []
    generation_metadata: dict = Field(default_factory=dict)
    # generation_metadata 必须包含:
    # - context_snapshot: ContextPackage 完整 JSON
    # - creative_brief: CreativeBrief 完整 JSON          ⭐ 新增
    # - mode_id: 创作模式 ID                              ⭐ 新增
    # - model: 使用的模型
    # - temperature: 温度
    # - prompt_hash: prompt 哈希
    change_description: str = ""
    changed_by: Literal["ai", "human"]
    created_at: datetime = Field(default_factory=datetime.now)

class ChapterHead(BaseModel):
    chapter_number: int
    project_id: str
    current_version_id: str
    accepted_version_id: str | None = None
```

**版本链**：
```
draft_v1 -> revision_v1 -> revision_v2 -> accepted -> edited
```

**规则**：
1. 每次生成/修订创建新版本，不覆盖
2. 只有 accepted/edited 可作为正式版本
3. context_snapshot + creative_brief 保存到 generation_metadata，用于复现 ⭐
4. 人工可随时回溯到任意历史版本
5. chapter_versions 增加唯一约束：(project_id, chapter_number, version_number) ⭐

---

## 12. 上下文 Token 预算管理

### 12.1 预算分配

```python
@dataclass
class ContextBudget:
    total_budget: int = 32_000           # 总预算
    generation_reserve: int = 8_000      # 预留生成空间
    available: int = 24_000              # 实际可用
    
    # 分区预算上限
    hard_constraints_max: int = 6_000
    character_states_max: int = 5_000
    recent_plot_max: int = 6_000
    foreshadowing_max: int = 2_000
    soft_references_max: int = 3_000
    chapter_goal_max: int = 2_000
    creative_brief_max: int = 1_500      # ⭐ 新增：CreativeBrief 预算
```

### 12.2 裁剪策略

当内容超出预算时，按以下优先级裁剪：

1. **软参考**（最先裁剪）→ 减少详细度
2. **CreativeBrief 描述长度** → 压缩张力描述 ⭐
3. **最近剧情章数** → 从 3 章减为 2 章
4. **角色档案详细度** → 只保留核心字段
5. **伏笔描述长度** → 压缩为一句话
6. 硬约束不裁剪
7. 超出总预算时报错

### 12.3 出场角色检测

```python
def detect_appearing_characters(
    previous_summary: ChapterSummary,
    chapter_goal: ChapterGoal
) -> list[str]:
    """
    通过上一章摘要 + 本章目标推断出场角色。
    只加载出场角色，不出场的只保留基本信息。
    """
```

---

## 13. 工作流编排

### 13.1 LangGraph 状态

```python
class Phase1State(TypedDict):
    project_id: str
    chapter_number: int
    mode_id: str                               # 创作模式 ID ⭐ 新增
    current_version_id: str | None
    review_report_id: str | None
    literary_observation_id: str | None        # ⭐ 新增
    creative_brief_id: str | None              # ⭐ 新增
    revision_round: int                        # 0, 1, 2
    status: str                                # 状态机状态
```

### 13.2 修正后的节点与边 ⭐ 核心变更

```python
builder = StateGraph(Phase1State)

# ========== 节点定义 ==========

# 1. GoalPlanner —— 制定章节目标
builder.add_node("goal_planner", goal_planner_node)

# 2. CreativeDirector —— 生成创作意图
builder.add_node("creative_director", creative_director_node)

# 3. ContextManager —— 组装上下文包
builder.add_node("context_manager", context_manager_node)

# 4. Writer —— 写初稿
builder.add_node("writer", writer_node)

# 5. RuleAuditor —— 代码层规则检测
builder.add_node("rule_auditor", rule_auditor_node)

# 6. LLMAuditor —— LLM 语义审查
builder.add_node("llm_auditor", llm_auditor_node)

# 7. ReviewMerger —— 合并审查报告（轻量节点，可内联）
builder.add_node("review_merger", review_merger_node)

# 8. RevisionHandler —— patch 修订
builder.add_node("revision_handler", revision_handler_node)

# 9. LiteraryAuditor —— 文学性诊断
builder.add_node("literary_auditor", literary_auditor_node)

# 10. HumanConfirm —— 人工确认
builder.add_node("human_confirm", human_confirm_node)

# 11. SettlementExtractor —— 状态结算
builder.add_node("settlement_extractor", settlement_extractor_node)

# ========== 边定义（修正后的流程顺序）==========

# 起点 -> GoalPlanner（先定目标）
builder.add_edge(START, "goal_planner")

# GoalPlanner -> CreativeDirector（生成创作意图）
builder.add_edge("goal_planner", "creative_director")

# CreativeDirector -> ContextManager（组装上下文包）
builder.add_edge("creative_director", "context_manager")

# ContextManager -> Writer（写作）
builder.add_edge("context_manager", "writer")

# Writer -> RuleAuditor（代码检测）
builder.add_edge("writer", "rule_auditor")

# RuleAuditor -> LLMAuditor（语义审查）
builder.add_edge("rule_auditor", "llm_auditor")

# LLMAuditor -> ReviewMerger（合并报告）
builder.add_edge("llm_auditor", "review_merger")

# ReviewMerger -> LiteraryAuditor（文学性诊断）
builder.add_edge("review_merger", "literary_auditor")

# LiteraryAuditor -> 条件路由（RevisionHandler 或 HumanConfirm）
# LiteraryAuditor 不阻塞，无论诊断结果如何都继续
builder.add_edge("literary_auditor", "revision_router")

# ========== 条件路由 ==========

# revision_router：根据 MergedReviewReport 决定是否修订
def revision_router(state: Phase1State):
    report = db.get_merged_report(state["review_report_id"])
    if report.has_critical or report.has_major:
        if state["revision_round"] < 2:
            return "revision_handler"
        return "human_confirm"
    return "human_confirm"

builder.add_conditional_edges("revision_router", revision_router, {
    "revision_handler": "revision_handler",
    "human_confirm": "human_confirm",
})

# RevisionHandler -> 重新审查（循环）
builder.add_edge("revision_handler", "rule_auditor")

# HumanConfirm -> 条件路由
def human_confirm_router(state: Phase1State):
    decision = state.get("human_decision")
    if decision == "accept":
        return "settlement_extractor"
    elif decision == "reject":
        return "goal_planner"           # 重新制定目标
    elif decision == "back":
        return "writer"                  # 回退到指定版本后重写
    else:
        return "human_confirm"           # 等待决策

builder.add_conditional_edges("human_confirm", human_confirm_router, {
    "settlement_extractor": "settlement_extractor",
    "goal_planner": "goal_planner",
    "writer": "writer",
    "human_confirm": "human_confirm",
})

# SettlementExtractor -> 摘要生成 -> 结束
builder.add_edge("settlement_extractor", END)
```

### 13.3 修正后的状态机

```
idle -> goal_planning -> creative_direction -> context_assembly -> writing
    -> rule_auditing -> llm_auditing -> review_merging -> literary_auditing
    -> [revision -> rule_auditing -> llm_auditing] (最多 2 轮)
    -> human_confirm

human_confirm:
  accept -> settlement -> done
  reject -> goal_planning
  back -> writing (指定版本)
  edit -> (编辑器) -> accept -> settlement -> done
```

---

## 14. 评测集设计

### 14.1 评测流程

```
对每个题材（玄幻/都市/科幻）：
1. 人工编写前 1 章作为种子
2. AI 生成第 2-4 章（每章走完整闭环）
3. 记录每章的 MergedReviewReport + LiteraryAuditResult
4. 人工独立审查（金标）
5. 对比 AI 审查 vs 人工金标
```

### 14.2 修正后的评测指标 ⭐

| 指标 | 目标 | 计算方式 |
|------|------|----------|
| 设定硬错误数 | 0 | critical world_consistency = 0 |
| 人工大改比例 | < 30% | 需人工大幅修改的章节比例 |
| 审查漏检率 | < 20% | 人工发现但 AI 没发现的问题比例 |
| 修订后新问题数 | 0 | 第二轮审查新问题数 = 0 |
| AI 腔规则命中数 | < 2 处/章 | RuleAuditor 检测的 style_ai_tells 数 |
| 疲劳词命中数 | < 3 处/章 | RuleAuditor 检测的 style_fatigue_words 数 |
| 首屏钩子达标率 | 100% | 前 300 字有吸引力事件 |
| 章末钩子达标率 | 100% | 最后 200 字有有效悬念 |
| 状态结算字段准确率 | > 90% | character_update.old_value 与 DB 一致率 |
| 概念空转段落数 | 0 | LiteraryAuditor 检测的 conceptual_idling 数 |
| 人物语言区分度 | > 70% | 人工评分（1-10）> 7 的章节比例 |
| AI 与人工金标一致率 | > 70% | critical/major 重叠率 |

**移除指标**：overall_score > 6.5/10（太主观）。

### 14.3 人工金标流程

```
1. AI 生成 MergedReviewReport
2. 人工独立审查同一章节（不看 AI 报告），生成 HumanReport
3. 对比：
   - critical/major issues 重叠率
   - AI 漏检率（人工发现但 AI 没发现的问题比例）
   - 人物语言区分度人工评分
   - "概念空转"判断一致性
4. 记录到 evals/gold_standard.json
```

---

## 15. 演进路线图

### V1.0（当前）：单章闭环验证
- **GoalPlanner** + **CreativeDirector** + **ContextManager** + **Writer**
- **RuleAuditor** + **LLMAuditor** 双层审查
- **LiteraryAuditor** 文学性诊断
- Genre Profile 系统
- CreativeModeProfile 创作模式系统
- 状态结算机制
- 上下文 Token 预算管理
- CLI 界面
- SQLite 单库

### V1.5：短篇连续验证
- 连续 5-10 章无需人工干预
- 跨章设定漂移检测
- 角色行为一致性追踪
- 伏笔回收率统计
- 引入 Mem0 管理长期记忆

### V2.0：卷级连续性
- 自动连续生成 10 章+
- 向量检索（Qdrant）升级上下文组装
- 角色弧线追踪
- Web 界面
- 多模型路由（强模型写，快模型审）

### V3.0：完整产品化
- 整本生产
- 风格迁移（文学风格控制）
- 数值体系自动记账
- Studio 工作台
- CharacterAutonomyAuditor：人物自治
- ForeshadowingManager：伏笔与裂隙
- LongFormContinuityAuditor：长篇漂移
- MacroNarrativePlanner：卷级/全书结构

---

## 16. 数据库设计

完整 schema 见第 10.2 节。

### E-R 关系

```
projects (1) ---- (*) characters
projects (1) ---- (*) chapter_versions
projects (1) ---- (*) foreshadowings
projects (1) ---- (*) summaries
projects (1) ---- (*) setting_snapshots
projects (1) ---- (*) numerical_ledgers
projects (1) ---- (*) creative_briefs          ⭐ 新增

characters (1) -- (*) character_states
chapter_versions (1) -- (0..1) review_reports
chapter_versions (1) -- (0..1) literary_observations  ⭐ 新增
chapter_versions (1) -- (*) chapter_versions (parent_version_id 自引用)
```

### 关键索引

```sql
-- 加速上下文组装
CREATE INDEX idx_character_states_lookup 
    ON character_states(project_id, chapter_number, character_id);

CREATE INDEX idx_summaries_lookup 
    ON summaries(project_id, chapter_number);

CREATE INDEX idx_setting_snapshots_lookup 
    ON setting_snapshots(project_id, setting_key);     -- ⭐ 新增 setting_key 索引

CREATE INDEX idx_foreshadowings_status 
    ON foreshadowings(project_id, status);

CREATE INDEX idx_numerical_ledgers_lookup 
    ON numerical_ledgers(project_id, chapter_number, character_id);

CREATE INDEX idx_creative_briefs_lookup          -- ⭐ 新增
    ON creative_briefs(project_id, chapter_number);

CREATE INDEX idx_chapter_versions_unique         -- ⭐ 新增
    ON chapter_versions(project_id, chapter_number, version_number);
```

---

> **松烟**取意古法制墨——松木燃烧，烟灰凝墨。以 AI 为烟，以规则为胶，凝练成可用之墨。
>
> V1.0 目标：**每生成一章，系统都知道它为什么这么写、哪里可能错、改了什么、状态发生了什么变化、下一章应该继承什么。**
>
> 不是写完，而是写好。不是写出伟大小说，而是跑通可控生产的工程闭环。
