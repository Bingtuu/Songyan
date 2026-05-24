编程的艺术在于：让机器精确执行那些人类不愿重复做的事情。
好的设计不是一次想完，而是在正确的时间做正确的减法。

# NovelForge — Vibe Coding 场景下的 Prompt 工程文档

## v2.1 版（基于 v2 review 精修）

> **版本**: v2.1.0  
> **日期**: 2026-05-16  
> **变更**: LangGraph state 只存 ID；增加 revision_handler/human_confirm 节点；Writer 只做初稿；token 默认 32K；评测加人工金标

---

## 目录

- [1. 顶层 System Prompt](#1-顶层-system-prompt)
- [2. Phase 1 核心 Agent Prompts](#2-phase-1-核心-agent-prompts)
  - [2.1 Planner Agent](#21-planner-agent)
  - [2.2 Writer Agent](#22-writer-agent)
  - [2.3 Reviewer Agent](#23-reviewer-agent)
  - [2.4 ContextManager Agent](#24-contextmanager-agent)
- [3. 关键机制 Prompts](#3-关键机制-prompts)
  - [3.1 新手创建向导](#31-新手创建向导)
  - [3.2 写作上下文包组装](#32-写作上下文包组装)
  - [3.3 结构化审查输出](#33-结构化审查输出)
  - [3.4 Issue-Driven Patch 修订](#34-issue-driven-patch-修订)
- [4. 集成测试 Prompts](#4-集成测试-prompts)
- [5. 调试与问题排查](#5-调试与问题排查)

---

## 1. 顶层 System Prompt

这是开发 NovelForge Phase 1 时的全局 System Prompt。

```markdown
## 角色与任务

你是一个专业的 Python 后端开发专家，正在协助开发 NovelForge Phase 1——一个基于 LangGraph 的 CLI 小说写作工具。

## Phase 1 目标（必须在所有决策中牢记）

唯一要验证的假设："AI 能否在足够一致的上下文中，稳定产出质量合格、设定不矛盾的中文小说章节？"

范围：单章闭环（项目设定 → 章节目标 → 上下文组装 → 生成 → 审查 → 修订 → 确认）

## Phase 1 技术约束

- **Python 3.11+**，异步优先（async/await）
- **LangGraph** 工作流编排
- **LangChain** + litellm 统一 LLM 接口
- **SQLite 单库**（唯一的长期事实源，无 Redis/Qdrant/PostgreSQL）
- **CLI 界面**（无 Web/TUI）
- **Pydantic v2** 所有数据模型
- **structlog** 日志

## Agent 架构（4 个核心 Agent + 2 个流程节点）

**核心 Agent**（不可增加）：
1. **Planner** —— 项目设定收集、章节目标制定、章节摘要生成
2. **Writer** —— 按场景生成初稿，严格遵守上下文包约束（只做初稿，不做修订）
3. **Reviewer** —— 结构化审查，输出有证据的 issue 列表
4. **ContextManager** —— 组装"写作上下文包"、版本管理、SQLite 存取

**流程节点**：
5. **RevisionHandler** —— issue-driven patch（按 issue 局部修改，不整章重写）
6. **HumanConfirm** —— CLI 人工确认 + 创建 accepted 版本 + 更新 chapter_heads

## 核心规则

1. **数据事实源**：SQLite 是唯一权威。LangGraph state 只存 ID（current_version_id, review_report_id），不存完整业务对象。
2. **版本管理**：每次生成和修订都创建 chapter_versions 新记录，不覆盖旧版本。只有 accepted/edited 版本才能作为"当前生效版本"。
3. **审查铁律**：Reviewer 输出必须包含 evidence_quote（原文片段），没有证据的 critical/major 不进入自动修订。
4. **修订限制**：最多 2 轮自动修订，RevisionHandler issue-driven patch（局部修改），不整章重写。第 2 轮仍有问题则上报人工。
5. **上下文包**：按"硬约束/软参考/最近剧情/角色状态/伏笔线索"分区组装，实时从 SQLite 构建，不持久化。
6. **人工确认**：Reviewer 通过后必须经过 HumanConfirm 节点，用户 accept/edit/reject/back 后才落库。

## 代码规范

- 所有函数必须带类型注解
- 所有 Pydantic 模型必须定义完整
- 错误处理用自定义异常，不用裸 except
- 测试用 pytest + pytest-asyncio
- 单文件不超过 400 行，超过则拆模块

## 文件结构

```
novelforge/
├── pyproject.toml
├── .env.example
├── README.md
└── src/
    └── novelforge/
        ├── __init__.py
        ├── cli.py                 # CLI 入口（Click 或 argparse）
        ├── config.py              # 配置管理（Pydantic Settings）
        ├── database.py            # SQLite 连接与表操作
        ├── models.py              # 所有 Pydantic 模型
        ├── agents/
        │   ├── __init__.py
        │   ├── planner.py         # Planner Agent
        │   ├── writer.py          # Writer Agent
        │   ├── reviewer.py        # Reviewer Agent
        │   └── context_manager.py # ContextManager Agent
        ├── graph.py               # LangGraph 工作流定义
        └── utils.py               # 工具函数
```

## 你现在要实现的具体模块

（以下由具体开发 prompt 填充）
```

---

## 2. Phase 1 核心 Agent Prompts

### 2.1 Planner Agent

```markdown
## 任务

实现 Planner Agent——负责收集项目设定、制定章节目标、生成章节摘要。

## 模块文件

`src/novelforge/agents/planner.py`

## 数据模型（在 models.py 中定义）

```python
class ProjectSetting(BaseModel):
    """项目设定"""
    title: str | None = None
    genre: str                              # 必填：题材
    protagonist_name: str                   # 必填：主角名
    protagonist_background: str             # 必填：主角背景
    core_hook: str                          # 必填：核心爽点
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

class ChapterSummary(BaseModel):
    """章节摘要"""
    chapter_number: int
    plot_summary: str                       # 200-500 字情节梗概
    key_events: list[str] = []
    characters_appeared: list[str] = []
    character_changes: dict[str, str] = {}  # 角色名 -> 变化描述
    settings_referenced: list[str] = []
    foreshadowing_planted: list[str] = []
    foreshadowing_resolved: list[str] = []
    emotional_tone: str = ""
    pacing_score: float = 0.0
    word_count: int = 0
```

## 节点函数

```python
async def planner_node(state: Phase1State) -> Phase1State:
    """
    Planner 节点。
    
    根据当前 state.status 执行不同操作：
    每个节点从 SQLite 加载业务对象（通过 state.project_id）。
    
    - "idle" / "planning"：
      调用 collect_project_setting() 启动新手向导
      或调用 define_chapter_goal() 制定本章目标
    
    - "summarizing"（HumanConfirm 完成后）：
      调用 generate_summary() 生成章节摘要
    
    注意：Planner 不直接写正文，只负责规划和总结。
    不修改 state 中的业务对象，只修改 ID 和 status。
    """

async def collect_project_setting(state: Phase1State) -> Phase1State:
    """
    收集项目设定。
    
    CLI 交互流程（7步向导）：
    1. 询问题材（必填，列表选择）
    2. 询问核心灵感（必填，一句话描述）
    3. 询问主角设定（必填，AI 可根据题材建议）
    4. 询问读者预期感受（AI 可建议）
    5. 询问禁忌事项（可选）
    6. 询问目标字数（可选，默认 10 万字）
    7. 询问书名（可选，AI 可建议 3 个）
    
    每步用 input() 获取用户输入，AI 用 LLM 生成建议。
    结果保存到 SQLite projects 表。
    """

async def define_chapter_goal(state: Phase1State) -> Phase1State:
    """
    制定章节目标。
    
    输入：
    - project_setting
    - 前 3 章的 summaries
    - 当前章节号
    
    输出：ChapterGoal
    
    使用 LLM 根据上下文生成合理的章节目标，
    包含：必须发生的事件、情感走向、钩子、字数目标。
    """

async def generate_summary(state: Phase1State) -> Phase1State:
    """
    生成章节摘要。
    
    输入：
    - 已接受的章节版本（current_version）
    - project_setting
    
    输出：ChapterSummary
    
    保存到 SQLite summaries 表，供后续章节引用。
    """
```

## LLM Prompt 设计

```python
DEFINE_CHAPTER_GOAL_PROMPT = """
你是小说规划师。根据以下信息，制定第 {chapter_number} 章的写作目标。

## 项目设定
题材：{genre}
主角：{protagonist_name}（{protagonist_background}）
核心爽点：{core_hook}
基调：{tone}

## 最近剧情
{recent_summaries}

## 要求
输出一个章节目标，包含：
1. 本章必须发生的 1-3 个关键事件
2. 情感走向（如：压抑→爆发、平静→紧张）
3. 章末钩子（吸引读者看下一章的悬念）
4. 字数目标（2000-5000）

注意：
- 事件要具体可执行，不要笼统
- 钩子必须有信息量，不能是"接下来会发生什么"
- 遵循网文节奏：每章都要有爽点或悬念
"""

GENERATE_SUMMARY_PROMPT = """
请为以下章节生成结构化摘要。

## 章节内容
{chapter_content}

## 输出格式（JSON）
{{
  "plot_summary": "200-500字情节梗概",
  "key_events": ["事件1", "事件2"],
  "characters_appeared": ["角色名"],
  "character_changes": {{"角色名": "变化描述"}},
  "settings_referenced": ["场景名"],
  "foreshadowing_planted": ["新埋下的伏笔"],
  "foreshadowing_resolved": ["回收的伏笔"],
  "emotional_tone": "情感基调",
  "pacing_score": 7.5
}}
"""
```

## 测试要求

```python
class TestPlanner:
    async def test_project_setting_collection(self):
        """测试项目设定收集（模拟 CLI 输入）"""
        
    async def test_chapter_goal_definition(self):
        """测试章节目标制定"""
        
    async def test_summary_generation(self):
        """测试摘要生成"""
        
    async def test_goal_has_concrete_events(self):
        """章节目标必须有具体事件，不能笼统"""
```
```

---

### 2.2 Writer Agent

```markdown
## 任务

实现 Writer Agent——按场景生成章节正文。

## 模块文件

`src/novelforge/agents/writer.py`

## 节点函数

```python
async def writer_node(state: Phase1State) -> Phase1State:
    """
    Writer 节点 —— 只做初稿，不做修订。
    
    修订由独立的 RevisionHandler 节点负责。
    
    输入：
    - state.project_id → 从 SQLite 加载 project_setting
    - state.chapter_number → 从 SQLite 加载 chapter_goal
    - ContextManager 组装的 context_package（注入 prompt）
    
    输出：
    - 创建 ChapterVersion（version_type="draft"）
    - 保存到 SQLite
    - 更新 state.current_version_id 指向新版本
    - state.status = "reviewing"
    """

async def write_draft(
    context: ContextPackage,
    goal: ChapterGoal,
) -> str:
    """
    生成章节初稿。
    
    策略：
    1. 按场景逐个生成（不是一次性生成整章）
    2. 每个场景包含：场景设定 → 事件推进 → 对话/描写 → 情感转折
    3. 场景之间有过渡段落
    4. 最后一个场景必须有钩子
    
    约束（必须遵守）：
    - 角色名必须与 character_states 中的 name 完全一致
    - 不引入 context_package 中未提及的新设定
    - 如有需要新设定，标记为 [[新设定:描述]]
    - 对话单独成段，用引号包裹
    - 段落 3-5 行，战斗场景用短句
    
    注意：Writer 只做初稿。如果被要求修改，返回错误——
    修订是 RevisionHandler 的职责。
    """
```

## LLM Prompt 设计

```python
WRITE_DRAFT_PROMPT = """
你是中文网络小说作家。请根据以下信息创作第 {chapter_number} 章。

## 写作约束（必须遵守）
{hard_constraints}

## 本章目标
{chapter_goal}

## 出场角色状态
{character_states}

## 最近剧情
{recent_plot}

## 伏笔线索
{foreshadowing}

## 风格参考
{style_rules}

## 写作要求
1. 按场景生成，场景间用 ### 分隔
2. 对话单独成段，用引号包裹
3. 段落 3-5 行，战斗场景用短句增加节奏感
4. 不引入上面未提及的新设定（需要的话标记 [[新设定:描述]]）
5. 章末必须有钩子
6. 字数目标：{word_count_target} 字

## 输出格式
直接输出正文，不要解释。
"""

APPLY_PATCH_PROMPT = """
请修改以下章节内容，修复指定的问题。只修改有问题的部分，其他内容保持不变。

## 原文
{original_content}

## 需要修复的问题
{issues}

## 规则
1. 每个问题只修改对应的那几句话
2. 不要改动没有问题的部分
3. 修改后全文要保持流畅
4. 输出完整的修改后全文

## 输出格式
输出完整的修改后章节内容，不要解释修改了哪些。
"""
```

## 测试要求

```python
class TestWriter:
    async def test_draft_generation(self):
        """测试初稿生成"""
        
    async def test_scene_separation(self):
        """测试场景分隔"""
        
    async def test_hard_constraint_compliance(self):
        """测试硬约束遵守（角色名、设定等）"""
        
    async def test_new_setting_tagging(self):
        """测试新设定标记"""
        
    async def test_patch_application(self):
        """测试 patch 修订"""
        
    async def test_patch_preserves_unmodified_text(self):
        """patch 必须保留未修改部分"""
```
```

---

### 2.3 Reviewer Agent

```markdown
## 任务

实现 Reviewer Agent——结构化审查，输出有证据的 issue 列表。

这是 Phase 1 最关键的质量关卡。输出必须是结构化的、有证据的、可执行的。

## 模块文件

`src/novelforge/agents/reviewer.py`

## 节点函数

```python
async def reviewer_node(state: Phase1State) -> Phase1State:
    """
    Reviewer 节点。
    
    输入：
    - state.current_version_id → 从 SQLite 加载 ChapterVersion
    - state.project_id, state.chapter_number → 从 SQLite 加载 ContextPackage
    
    流程：
    1. 从 SQLite 加载业务对象（通过 ID）
    2. 并行执行 4 类检查
    3. 汇总 issue 列表
    4. 严重度分级
    5. 确定 fix_type
    6. 生成 ReviewReport 并保存到 SQLite
    7. 更新 state.review_report_id 指向新报告
    
    输出路由：
    - 无 critical/major → state.status = "human_confirm"
    - 有 critical/major 且 revision_round < 2 → state.status = "revising"
    - 有 critical/major 且 revision_round >= 2 → state.status = "human_confirm"（带未修复 issue）
    - state.status = "revising" 如果有 critical/major 且 revision_round < 2
    """

async def check_world_consistency(
    content: str,
    context: ContextPackage,
) -> list[ReviewIssue]:
    """
    设定一致性检查。
    
    检查项：
    - 正文中引用的设定是否与 hard_constraints 一致
    - 是否引入了未登记的新设定
    - 是否违反了已揭示的设定
    
    每个 issue 必须有 evidence_quote。
    """

async def check_character_behavior(
    content: str,
    character_states: list[CharacterStateSnapshot],
) -> list[ReviewIssue]:
    """
    角色行为一致性检查。
    
    检查项：
    - 角色行为是否与其性格/动机一致
    - 角色能力使用是否超限
    - 角色间互动是否符合关系设定
    """

async def check_timeline(
    content: str,
    context: ContextPackage,
) -> list[ReviewIssue]:
    """
    时间线验证。
    
    检查项：
    - 事件顺序是否合理
    - 是否有时间矛盾（如角色同时出现在两个地方）
    """

async def check_quality(
    content: str,
    chapter_goal: ChapterGoal,
) -> list[ReviewIssue]:
    """
    质量检查。
    
    检查项（8 维度，但只报 major 以上）：
    - 叙事：情节推进是否自然
    - 对话：是否有区分度、是否推动剧情
    - 描写：是否有感官细节
    - 节奏：是否有起伏
    - 情感：是否真挚
    - 钩子：章末是否有吸引力
    - 风格：是否与参考一致
    - 可读性：是否流畅
    """
```

## LLM Prompt 设计（关键！）

```python
REVIEW_PROMPT = """
你是资深中文网络文学编辑。请对以下章节进行严格审查。

## 审查标准

你必须输出结构化的 issue 列表。每个 issue 必须包含：
1. **category**：问题类别
2. **severity**：严重度（critical/major/minor/info）
3. **evidence_quote**：原文问题片段（必须引用原文！）
4. **issue_description**：具体问题
5. **expected**：应该是什么
6. **actual**：实际是什么
7. **suggested_fix**：修复建议
8. **fix_type**：修复类型（patch/rewrite_scene/confirm/register_setting）

## 严重度定义

- **critical**：事实性错误，读者会出戏
  - 已死角色再次出现
  - 违反已揭示的核心设定
  - 时间线明显矛盾
  
- **major**：质量或一致性问题，影响阅读体验
  - 角色行为与其性格明显冲突
  - 节奏严重失衡（整章拖沓或仓促）
  - 对话没有区分度
  
- **minor**：小瑕疵
  - 用词重复
  - 描写可以更生动
  
- **info**：建议
  - 可以增加伏笔
  - 这里可以加强钩子

## 铁律

- 没有 evidence_quote（原文引用）的 issue 不要输出
- minor 和 info 不阻塞入库，只记录
- critical 必须修复
- major 建议修复

## 章节内容
{chapter_content}

## 上下文（用于比对）
### 硬约束
{hard_constraints}

### 角色状态
{character_states}

### 章节目标
{chapter_goal}

## 输出格式
以 JSON 输出 issue 列表：
{{
  "issues": [
    {{
      "category": "world_consistency",
      "severity": "critical",
      "evidence_quote": "原文片段",
      "issue_description": "问题描述",
      "expected": "应该是...",
      "actual": "实际是...",
      "suggested_fix": "修改建议",
      "fix_type": "patch",
      "confidence": 0.95
    }}
  ],
  "overall_score": 7.5,
  "summary": "总体评价"
}}
"""
```

## 测试要求

```python
class TestReviewer:
    async def test_critical_issue_detection(self):
        """检测 critical 问题（如已死角色再现）"""
        
    async def test_evidence_quote_required(self):
        """每个 critical/major 必须有 evidence_quote"""
        
    async def test_severity_classification(self):
        """严重度分级准确"""
        
    async def test_no_false_positives(self):
        """无明显误报"""
        
    async def test_quality_dimensions(self):
        """8 维度质量检查覆盖"""
```
```

---

### 2.4 RevisionHandler 节点

```markdown
## 任务

实现 RevisionHandler 节点——issue-driven patch 修订（独立节点，不是 Writer 的一部分）。

## 核心原则

- **Writer 只做初稿**，RevisionHandler 只做 patch
- 只修改有 issue 的部分，保留其他内容不变
- 按位置从后往前应用 patch，避免位置偏移

## 模块文件

`src/novelforge/agents/revision_handler.py`

## 节点函数

```python
async def revision_handler_node(state: Phase1State) -> Phase1State:
    """
    RevisionHandler 节点。
    
    输入：
    - state.current_version_id → 从 SQLite 加载父版本
    - state.review_report_id → 从 SQLite 加载审查报告
    - state.revision_round → 当前轮次
    
    流程：
    1. 从 SQLite 加载父版本和审查报告（通过 ID）
    2. 筛选 patchable issues（critical/major 且 fix_type == patch）
    3. 按位置排序（从后往前）
    4. 逐个应用 patch（精确替换 evidence_quote）
    5. 创建新版本（version_type="revision"）
    6. revision_round += 1
    7. 保存新版本到 SQLite
    8. 更新 state.current_version_id 指向新版本
    9. state.status = "reviewing"（回到 Reviewer）
    
    注意：不修改 review_report_id，Reviewer 会重新生成新的报告。
    """

async def apply_patches(
    content: str,
    issues: list[ReviewIssue],
) -> tuple[str, list[Patch]]:
    """
    应用 patch 列表到内容。
    
    规则：
    1. 只处理 fix_type == patch 的 critical/major issue
    2. 按 evidence_location 从后往前排序
    3. 使用 content.replace(evidence_quote, suggested_fix, 1)
    4. 如果 evidence_quote 在内容中找不到，记录失败
    
    输出：
    - 修订后的完整内容
    - patch 列表（成功的）
    """
```

## 测试要求

```python
class TestRevisionHandler:
    async def test_patch_application(self):
        """测试 patch 应用"""
        
    async def test_patch_preserves_unmodified(self):
        """patch 必须保留未修改部分"""
        
    async def test_patch_from_back_to_front(self):
        """从后往前应用 patch"""
        
    async def test_patch_not_found(self):
        """evidence_quote 找不到时的处理"""
```
```

---

### 2.5 HumanConfirm 节点

```markdown
## 任务

实现 HumanConfirm 节点——CLI 人工确认 + 创建 accepted 版本 + 更新 chapter_heads。

## 核心原则

- 这是人工介入的唯一入口
- 提供 accept/edit/reject/back 四个选项
- accept 后创建 accepted 版本并更新 chapter_heads

## 模块文件

`src/novelforge/agents/human_confirm.py`

## 节点函数

```python
async def human_confirm_node(state: Phase1State) -> Phase1State:
    """
    HumanConfirm 节点。
    
    流程：
    1. 从 SQLite 加载当前版本和审查报告（通过 ID）
    2. 打印审查摘要（issue 列表、严重度、修复建议）
    3. 展示章节正文预览
    4. 提示用户选择：accept / edit / reject / back
    5. 根据选择：
       - accept → 创建 accepted 版本，更新 chapter_heads
       - edit → 打开编辑器，创建 edited 版本，更新 chapter_heads
       - reject → 退回 planning，重置版本
       - back → 列出历史版本，回退到指定版本
    6. 更新 state 指向最终版本
    7. state.status = "summarizing"（下一步 Planner 生成摘要）
    """
```

## CLI 交互设计

```
📋 审查报告（3 个问题）
  [CRITICAL] world_consistency: 已揭示的"凡人无法飞行"与文中御剑飞行矛盾
  [MAJOR] character_behavior: 角色突然暴怒与其冷静性格设定冲突
  [MINOR] quality_description: 此处可增加感官描写

[a]ccept — 接受当前版本
[e]dit   — 用编辑器修改
[r]eject — 退回重写
[b]ack   — 回退到历史版本

> 
```

## 测试要求

```python
class TestHumanConfirm:
    async def test_accept_creates_accepted_version(self):
        """accept 创建 accepted 版本并更新 chapter_heads"""
        
    async def test_edit_creates_edited_version(self):
        """edit 创建 edited 版本"""
        
    async def test_reject_resets_to_planning(self):
        """reject 退回 planning 状态"""
        
    async def test_back_lists_history_versions(self):
        """back 列出历史版本供选择"""
```
```

---

### 2.6 ContextManager Agent

```markdown
## 任务

实现 ContextManager Agent——组装写作上下文包、管理版本、存取 SQLite。

## 模块文件

`src/novelforge/agents/context_manager.py`
`src/novelforge/database.py`

## 节点函数

```python
async def context_manager_node(state: Phase1State) -> Phase1State:
    """
    ContextManager 节点。
    
    两种情况：
    1. 写作前：组装 ContextPackage
    2. 完成后：保存版本到 SQLite
    """

async def assemble_context_package(
    project_id: str,
    chapter_number: int,
    db: Database,
) -> ContextPackage:
    """
    组装写作上下文包。
    
    数据来源（全部来自 SQLite）：
    1. projects 表 → project_setting
    2. summaries 表 → recent_plot（前 3 章）
    3. character_states 表 → character_states
    4. setting_snapshots 表 → hard_constraints + soft_references
    5. foreshadowings 表 → foreshadowing
    
    组装规则：
    - 硬约束放在最前面，用明确的指令语气
    - 最近剧情包含前 3 章摘要 + 上一章结尾 500 字
    - 不出场的角色不加载详细档案
    - 总 token 默认控制在 32K 以内（可配置，上限 64K）
    """

async def save_version(
    state: Phase1State,
    db: Database,
) -> str:
    """
    保存章节版本到 SQLite。
    
    创建 chapter_versions 记录，不覆盖旧版本。
    更新 chapter_heads 指向新版本。
    """

async def get_version_chain(
    chapter_number: int,
    project_id: str,
    db: Database,
) -> list[ChapterVersion]:
    """获取版本链（从 draft 到当前）"""
```

## 数据库操作（database.py）

```python
class Database:
    """SQLite 数据库操作"""
    
    def __init__(self, db_path: str = "novelforge.db"):
        self.db_path = db_path
    
    async def init_tables(self):
        """初始化所有表"""
        
    async def get_project_setting(self, project_id: str) -> ProjectSetting:
        """获取项目设定"""
        
    async def get_recent_summaries(self, project_id: str, chapter_number: int, count: int = 3) -> list[ChapterSummary]:
        """获取最近 N 章摘要"""
        
    async def get_character_states(self, project_id: str, chapter_number: int) -> list[CharacterStateSnapshot]:
        """获取角色状态快照"""
        
    async def get_active_foreshadowings(self, project_id: str, chapter_number: int) -> list[ForeshadowingItem]:
        """获取活跃的伏笔（planted 和 due 状态）"""
        
    async def save_chapter_version(self, version: ChapterVersion):
        """保存章节版本"""
        
    async def save_review_report(self, report: ReviewReport):
        """保存审查报告"""
        
    async def update_chapter_head(self, chapter_number: int, project_id: str, version_id: str):
        """更新章节指针"""
```

## 测试要求

```python
class TestContextManager:
    async def test_context_assembly(self):
        """测试上下文包组装"""
        
    async def test_context_token_limit(self):
        """上下文包不超过 32K tokens（默认，可配置上限 64K）"""
        
    async def test_version_save_and_retrieve(self):
        """测试版本保存和读取"""
        
    async def test_version_chain(self):
        """测试版本链追踪"""
        
    async def test_character_state_filtering(self):
        """不出场的角色不加载"""
```

---

## 3. 关键机制 Prompts

### 3.1 新手创建向导

```markdown
## 任务

实现 CLI 新手创建向导——7 步引导用户完成项目设定。

## 模块文件

`src/novelforge/cli.py` 中的向导函数

## 实现

```python
class OnboardingWizard:
    """新手创建向导"""
    
    STEPS = [
        {
            "key": "genre",
            "question": "你想写什么类型的小说？",
            "required": True,
            "options": ["玄幻", "仙侠", "都市", "科幻", "历史", "言情", "悬疑"],
            "ai_suggest": False,
        },
        {
            "key": "core_hook",
            "question": "用一句话描述你的核心创意（主角+目标+障碍）",
            "example": "比如：废柴少年获得神秘系统，踏上修仙之路",
            "required": True,
            "ai_suggest": False,
        },
        {
            "key": "protagonist",
            "question": "主角叫什么名字？什么背景？",
            "required": True,
            "ai_suggest": True,
            "suggest_prompt": "根据题材'{genre}'和核心灵感'{core_hook}'，建议一个主角设定（名字+背景）",
        },
        {
            "key": "target_reader_expectation",
            "question": "你希望读者读这本书时有什么感受？",
            "options": ["爽", "燃", "甜", "虐", "紧张", "温暖"],
            "required": True,
            "ai_suggest": True,
        },
        {
            "key": "taboos",
            "question": "有什么内容是你绝对不想出现的？（多选，回车跳过）",
            "options": ["绿帽", "虐主", "死女主", "太监", "种马", "狗血误会"],
            "required": False,
            "ai_suggest": False,
        },
        {
            "key": "target_word_count",
            "question": "打算写多长？",
            "options": [
                ("短篇（10万字）", 100000),
                ("中篇（50万字）", 500000),
                ("长篇（100万字）", 1000000),
            ],
            "required": False,
            "default": 100000,
        },
        {
            "key": "title",
            "question": "给小说起个名字吧",
            "required": False,
            "ai_suggest": True,
            "suggest_prompt": "根据题材'{genre}'、核心灵感'{core_hook}'，建议 3 个书名",
        },
    ]
    
    async def run(self) -> ProjectSetting:
        """
        运行向导。
        
        每步：
        1. 显示问题
        2. 如果有选项，显示选项列表
        3. 如果有 AI 建议，先生成建议供用户参考
        4. 获取用户输入
        5. 验证必填
        6. 下一步
        
        最后汇总显示所有设定，确认后保存。
        """
```

## CLI 交互示例

```
$ novelforge create-project

🎉 欢迎来到 NovelForge！让我们开始创建你的小说。

Step 1/7: 题材选择
你想写什么类型的小说？
  [1] 玄幻
  [2] 仙侠
  [3] 都市
  [4] 科幻
  [5] 历史
  [6] 言情
  [7] 悬疑
> 1

Step 2/7: 核心灵感
用一句话描述你的核心创意（主角+目标+障碍）
> 废柴少年获得神秘系统，踏上修仙之路

Step 3/7: 主角设定
主角叫什么名字？什么背景？
（AI 建议：林凡，青云镇林家的旁系子弟，天生灵根残缺）
> 林凡，青云镇林家旁系，天生灵根残缺

...

✅ 项目创建完成！
书名：《逆天系统：从废柴到至尊》
题材：玄幻
主角：林凡
接下来可以开始写作：novelforge write-chapter --chapter 1
```
```

---

### 3.2 写作上下文包组装

```markdown
## 任务

实现上下文包组装逻辑——从 SQLite 读取数据，按分区组装。

## 关键逻辑

```python
async def assemble_context_package(
    project_id: str,
    chapter_number: int,
    db: Database,
) -> ContextPackage:
    """
    组装上下文包。
    
    步骤：
    1. 加载项目设定和章节目标
    2. 加载硬约束（角色状态 + 已揭示设定 + 禁忌）
    3. 加载软参考（相关世界观设定）
    4. 加载最近剧情（前3章摘要 + 上一章结尾500字）
    5. 加载角色状态快照
    6. 加载伏笔线索
    7. 估算 token 数，如果超限则裁剪软参考
    """
    
    # 1. 项目设定和章节目标
    project = await db.get_project_setting(project_id)
    goal = await db.get_chapter_goal(project_id, chapter_number)
    
    # 2. 硬约束
    hard_constraints = []
    char_states = await db.get_character_states(project_id, chapter_number)
    for cs in char_states:
        hard_constraints.append(HardConstraint(
            type="character_state",
            description=f"{cs.name}当前在{cs.current_location}，境界{cs.current_cultivation}，状态{cs.emotional_state}",
            source=f"character_states.{cs.character_id}",
        ))
    
    # 3. 软参考
    soft_refs = await db.get_relevant_settings(project_id, goal.target_events)
    
    # 4. 最近剧情
    recent_summaries = await db.get_recent_summaries(project_id, chapter_number, 3)
    previous_chapter = await db.get_chapter_head(project_id, chapter_number - 1)
    last_500_chars = previous_chapter.content[-500:] if previous_chapter else ""
    
    # 5. 伏笔
    foreshadowings = await db.get_active_foreshadowings(project_id, chapter_number)
    
    # 6. 组装
    package = ContextPackage(
        chapter_goal=goal,
        hard_constraints=hard_constraints,
        soft_references=soft_refs,
        recent_plot=RecentPlot(
            summaries=recent_summaries,
            previous_ending=last_500_chars,
        ),
        character_states=char_states,
        foreshadowing=foreshadowings,
    )
    
    # 7. Token 检查
    package.estimated_tokens = estimate_tokens(package)
    if package.estimated_tokens > 32000:  # 默认 32K，可配置
        package = trim_context(package, target_tokens=32000)
    
    return package
```

## 上下文渲染模板

```python
CONTEXT_TEMPLATE = """
【写作约束 — 必须遵守】
{hard_constraints}

【本章目标】
{chapter_goal}

【出场角色状态】
{character_states}

【最近剧情】
{recent_plot}

【伏笔线索】
{foreshadowing}

【相关设定参考】
{soft_references}

【风格参考】
{style_rules}
"""
```
```

---

### 3.3 结构化审查输出

已在 2.3 Reviewer Agent 中详细定义，核心要求：

1. 每个 critical/major issue 必须有 `evidence_quote`（原文引用）
2. 每个 issue 必须有 `suggested_fix` 和 `fix_type`
3. `fix_type` 只能是：`patch`（局部修改）、`rewrite_scene`（重写场景）、`confirm`（人工确认）、`register_setting`（登记新设定）
4. 没有证据的 issue 不进入自动修订流程
5. minor/info 只记录不阻塞

---

### 3.4 Issue-Driven Patch 修订

```markdown
## 任务

实现 issue-driven patch 修订逻辑——只改有问题的部分，不改其他。

## 关键逻辑

```python
async def apply_issue_patches(
    parent_version: ChapterVersion,
    issues: list[ReviewIssue],
) -> ChapterVersion:
    """
    Issue-driven patch 修订。
    
    流程：
    1. 筛选 patchable issues（critical/major 且 fix_type == patch）
    2. 按位置排序（从后往前，避免位置偏移）
    3. 逐个应用 patch
    4. 记录每个 patch
    5. 创建新版本
    """
    
    # 1. 筛选
    patchable = [
        i for i in issues 
        if i.severity in ("critical", "major") 
        and i.fix_type == "patch"
    ]
    
    # 2. 按位置排序（从后往前）
    patchable.sort(key=lambda i: i.evidence_location, reverse=True)
    
    # 3. 应用
    content = parent_version.content
    patches = []
    for issue in patchable:
        # 在 content 中找到 evidence_quote
        if issue.evidence_quote in content:
            patched_content = content.replace(
                issue.evidence_quote,
                issue.suggested_fix,
                1,  # 只替换第一次出现
            )
            if patched_content != content:
                patches.append(Patch(
                    issue_id=issue.issue_id,
                    original_text=issue.evidence_quote,
                    revised_text=issue.suggested_fix,
                    location=issue.evidence_location,
                ))
                content = patched_content
    
    # 4. 创建新版本
    return ChapterVersion(
        chapter_number=parent_version.chapter_number,
        project_id=parent_version.project_id,
        version_number=parent_version.version_number + 1,
        version_type="revision",
        parent_version_id=parent_version.version_id,
        title=parent_version.title,
        content=content,
        word_count=len(content),
        issues_fixed=[p.issue_id for p in patches],
        issues_remaining=[
            i.issue_id for i in issues 
            if i.issue_id not in [p.issue_id for p in patches]
        ],
        changed_by="ai",
    )
```

## 修订规则

1. 最多 2 轮自动修订
2. 只处理 fix_type == patch 的 critical/major issue
3. rewrite_scene 类型的 issue 直接上报人工
4. confirm 类型的 issue 直接上报人工
5. register_setting 类型的 issue 先登记再 patch
6. 第二轮审查如果引入新问题，立即停止并上报人工
```

---

## 4. 集成测试 Prompts

```markdown
## 任务

编写 Phase 1 的集成测试，验证单章闭环。

## 测试场景

### 场景 1：完整单章闭环（Happy Path）

```python
@pytest.mark.asyncio
async def test_full_chapter_loop():
    """
    完整单章闭环测试。
    
    流程：
    1. 创建项目设定（跳过向导，直接 mock）
    2. 制定第 1 章目标（Planner）
    3. 组装上下文包（ContextManager）
    4. Writer 生成初稿（Writer）
    5. Reviewer 审查（Reviewer）
    6. 无 critical/major → HumanConfirm（模拟 accept）
    7. Planner 生成摘要
    8. 保存 accepted 版本
    
    验证：
    - SQLite 中有 chapter_versions 记录（draft + accepted 两个版本）
    - version_number = 1, version_type = "draft"
    - review_report 已保存
    - chapter_heads.accepted_version_id 指向 accepted 版本
    - summary 已保存
    """
```

### 场景 2：审查发现问题 → 自动修订

```python
@pytest.mark.asyncio
async def test_review_and_revision():
    """
    审查发现问题后自动修订。
    
    流程：
    1. 生成初稿（使用已知有问题的内容）
    2. Reviewer 发现 major issue
    3. 触发自动修订（第 1 轮）
    4. Reviewer 再次审查
    5. 验证新问题数为 0
    
    验证：
    - 创建了 revision 版本（version_number = 2）
    - patch 只修改了有问题的部分
    - 未修改部分保持不变
    - 第二轮无新问题
    """
```

### 场景 3：2 轮修订后仍有问题 → 上报人工

```python
@pytest.mark.asyncio
async def test_max_revision_rounds():
    """
    最多 2 轮修订后仍有问题，上报人工。
    
    流程：
    1. 生成初稿
    2. 第 1 轮修订
    3. 第 2 轮修订
    4. 第 3 次审查仍发现问题
    5. 验证停止自动修订，等待人工
    
    验证：
    - revision_round 不超过 2
    - state.status = "human_confirm"
    - 有未修复 issue 记录
    """
```

### 场景 4：检查点恢复

```python
@pytest.mark.asyncio
async def test_checkpoint_recovery():
    """
    检查点持久化和恢复。
    
    流程：
    1. 执行到 writer 节点
    2. 模拟崩溃（重新创建 app）
    3. 从 checkpoint 恢复
    4. 验证状态正确
    5. 继续执行到完成
    """
```

### 场景 5：版本回溯

```python
@pytest.mark.asyncio
async def test_version_rollback():
    """
    版本回溯测试。
    
    流程：
    1. 生成 v1（draft）
    2. 修订生成 v2（revision）
    3. 人工确认 v2（accepted）
    4. 人工编辑生成 v3（edited）
    5. 回溯到 v1
    6. 验证 chapter_head 可指向 v1
    """
```

### 场景 6：上下文包 token 限制

```python
@pytest.mark.asyncio
async def test_context_package_token_limit():
    """
    上下文包不超过 32K tokens（默认，可配置上限 64K）。
    
    流程：
    1. 创建大量设定和角色
    2. 组装上下文包
    3. 验证 token 数 ≤ 32000（或配置值）
    """
```

### 场景 7：Reviewer-人工金标一致率

```python
@pytest.mark.asyncio
async def test_reviewer_human_gold_standard_agreement():
    """
    Reviewer 判断与人工金标的一致率 > 70%。
    
    流程：
    1. 让系统生成并审查 3 章
    2. 人工独立审查这 3 章（不参考 Reviewer 结果）
    3. 对比两者判断：
       - critical/major 判定是否一致
       - issue 是否被正确识别
    4. 计算一致率 = 一致判断数 / 总判断数
    5. 验证一致率 > 70%
    
    如果一致率 < 70%，需要调整 Reviewer prompt 后重测。
    """
```
```

---

## 5. 调试与问题排查

```markdown
## Phase 1 常见问题

### 问题 1：Reviewer 输出没有 evidence_quote

**症状**: Reviewer 返回的 issue 缺少原文引用。

**排查**:
1. 检查 REVIEW_PROMPT 中是否明确要求 evidence_quote
2. 检查 LLM 输出解析是否容错
3. 检查是否过滤了没有 evidence_quote 的 issue

**修复**: 在 parse 阶段过滤掉没有 evidence_quote 的 critical/major issue。

### 问题 2：Patch 修改了不该改的部分

**症状**: 应用 patch 后，原本正确的内容也变了。

**排查**:
1. 检查 replace 是否使用了 count=1
2. 检查 evidence_quote 是否足够唯一（不会匹配多处）
3. 检查 patch 是否按从后往前的顺序应用

**修复**: 使用更精确的匹配（加前后各 20 字上下文），或改用行号定位。

### 问题 3：上下文包超过 token 限制

**症状**: Writer 报错上下文过长。

**排查**:
1. 检查 estimate_tokens 是否准确
2. 检查 trim_context 是否生效
3. 检查是否有循环引用导致内容膨胀

**修复**: 减少软参考数量，裁剪不重要的角色状态。

### 问题 4：SQLite 锁冲突

**症状**: 并发操作时报 database is locked。

**排查**:
1. 检查是否多个进程同时写 SQLite
2. 检查事务是否及时提交

**修复**: Phase 1 是单用户 CLI，应该不会有并发。如果有，加写锁或换 PostgreSQL。

### 问题 5：检查点没有正确恢复

**症状**: 重启后状态丢失或错误。

**排查**:
1. 检查 checkpoint 表是否正确写入
2. 检查 thread_id 是否一致
3. 检查业务数据是否在 SQLite 中

**修复**: 确保 checkpoint 只存执行现场，业务数据从 SQLite 加载。

## 调试工具

```python
# 在 utils.py 中

def print_state(state: Phase1State):
    """打印当前状态（调试用）"""
    print(f"Status: {state['status']}")
    print(f"Chapter: {state['chapter_number']}")
    print(f"Version: {state['current_version'].version_number if state['current_version'] else None}")
    print(f"Revision Round: {state['revision_round']}")
    if state['review_report']:
        print(f"Issues: {len(state['review_report'].issues)}")
        for i in state['review_report'].issues:
            print(f"  [{i.severity}] {i.category}: {i.issue_description[:50]}")

def export_review_report(report: ReviewReport, path: str):
    """导出审查报告为 JSON"""
    with open(path, 'w') as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)
```

## 评测脚本

```python
# scripts/evaluate.py

async def evaluate_phase1(project_id: str, db: Database) -> dict:
    """
    Phase 1 评测。
    
    指标：
    1. 结构化审查通过率（无 critical/major 的章节比例）
    2. 质量评分均值
    3. 人工返工率（需要大幅修改的章节比例）
    4. 修订不引入新问题率
    5. 设定一致性（critical world_consistency = 0）
    6. 角色行为一致性（major 以下比例）
    """
    
    chapters = await db.get_all_chapters(project_id)
    
    total = len(chapters)
    passed = sum(1 for c in chapters if c.no_critical_major)
    avg_score = sum(c.review_score for c in chapters) / total
    
    return {
        "total_chapters": total,
        "pass_rate": passed / total,
        "avg_quality_score": avg_score,
        "revision_new_issue_rate": ...,  # 修订引入新问题的比例
        "world_consistency_errors": ...,  # 设定一致性错误数
 