# CLAUDE.md — Songyan V1.0 开发代理指令

> **你是谁**：你是 Songyan（松烟）项目的协作开发代理。
> **你的目标**：按 Task 规格完成代码开发，确保测试通过，不违反任何约束。
> **你的工作方式**：先读后做，完成验证，交接清晰。

---

## 1. 启动协议（每次开始新任务时必须执行）

```
1. 读取本文件（CLAUDE.md）—— 不可违背规则
2. 读取 system_prompt/development-tech-plan-v2.md —— 技术方案
3. 读取 docs/STATUS.md —— 当前项目状态
4. 读取 docs/INDEX.md —— 文档索引（确认需要读哪些）
5. 读取当前 tasks/00x-xxx.md —— 当前 Task 规格
6. 读取上游任务的 tasks/00x-xxx-DONE.md（如果有依赖）
7. 用 5-8 行总结你理解的任务边界
8. 确认边界后再开始修改代码
```

---

## 2. 项目定位

V1.0 唯一要验证的假设：

> "每生成一章，系统都知道它为什么这么写、哪里可能错、改了什么、状态发生了什么变化、下一章应该继承什么。"

V1.0 验证范围：xuanhuan（玄幻）+ webnovel/hybrid（2 种模式），urban/scifi/literary 预置配置但不跑评测。

---

## 3. 不可违背规则（违反任何一条必须回滚修改）

### 3.1 创作模式
1. 每个项目必须关联一个 CreativeModeProfile（mode_id）
2. CreativeModeProfile 决定启用的 Agent、审查维度、修订策略
3. V1.0 默认 mode 为 "webnovel"，可配置为 "literary" 或 "hybrid"
4. 新增创作模式只需注册配置 JSON，无需修改 Agent 代码

### 3.2 数据
5. SQLite 是 V1.0 唯一的长期事实源
6. LangGraph state 只存 ID，不存完整业务对象
7. 每次生成/修订创建 chapter_versions 新记录，禁止覆盖
8. 每个节点从 SQLite 加载数据，不从 state 取正文
9. generation_metadata 必须保存 context_snapshot + creative_brief（用于复现）
10. character_states 为快照表，永远 INSERT 新记录，禁止 UPDATE

### 3.3 Agent 职责
11. Writer 只做初稿，不做修订
12. RuleAuditor 只做代码检测，不做语义判断
13. LLMAuditor 只做语义审查，不做代码检测
14. LiteraryAuditor 只做诊断，不阻塞 accept，不修改正文
15. RevisionHandler 只做 patch，不整章重写
16. GoalPlanner 不写正文，只做规划
17. CreativeDirector 不写正文，只输出结构化 CreativeBrief，**不得新增硬剧情事件**
18. SettlementExtractor 只做结算提取和验证
19. ContextManager 不做生成，不做审查判断
20. SummaryWriter 为轻量函数，基于 accepted 正文 + settlement 生成摘要

### 3.4 审查
21. LLMAuditor 的 critical/major issue 必须有 evidence_quote
22. RuleAuditor 的检测结果必须有定位信息
23. 没有证据的 issue 不进入自动修订
24. 自动修订最多 2 轮
25. 修订引入新问题 → 停止自动修订，上报人工
26. rewrite_scene 类型 issue 不自动修复

### 3.5 文学性
27. LiteraryAuditor 的诊断默认不阻塞 accept
28. valuable_fissure 不是缺陷，是"请人工判断是否保留"
29. LiteraryAuditor 不输出 fix，只输出 observation 和 recommendation
30. valuable_fissure 自动输出 protected_elements，RevisionHandler 必须排除

### 3.6 状态结算
31. 每章 accept 后必须执行 SettlementExtractor，edit/reject/back 不触发
32. SettlementExtractor 完成后执行 SummaryWriter 生成摘要
33. character_update.old_value 必须与 DB 当前值一致
34. new_setting.source_quote 必须在正文中存在
35. new_setting.setting_key 必须唯一
36. numerical_update.closing_value 必须等于公式值
37. 结算失败标记 needs_human_review，不阻塞
38. foreshadowings 必须记录 source_version_id

### 3.7 上下文
39. 上下文包按 Token 预算组装，默认 32K
40. 超出预算时按优先级裁剪：软参考 → CreativeBrief → 最近剧情章数 → 角色详细度
41. 硬约束不裁剪
42. 不出场的角色不加载详细档案

### 3.8 Genre Profile
43. 每个项目必须关联一个 Genre Profile
44. Writer Prompt 中注入 genre.writer_rules
45. RuleAuditor 中注入 genre.fatigue_words
46. LLMAuditor 中注入 genre.reviewer_focus
47. 玄幻项目启用 genre_numerical 审查维度

### 3.9 CreativeBrief
48. 每个 chapter 必须生成 CreativeBrief（由 CreativeDirector）
49. CreativeBrief 必须包含 required_tensions 和 forbidden_patterns
50. CreativeBrief 保存到 generation_metadata 和 creative_briefs 表
51. CreativeDirector 不得新增硬剧情事件，只能基于 ChapterGoal 推导张力
52. 若 CreativeDirector 发现张力不足，标记 tension_gap: true 供人工判断

### 3.10 数据访问边界
53. Agent 层不直接拿 DB connection
54. Agent 返回 NodeResult → orchestrator/Service 统一写入
55. 写操作集中在 Service 层 / UnitOfWork
56. 对 accepted version、current head、settlement 写入使用事务
57. Repository 层记录所有写入操作日志

### 3.11 代码规范
58. 所有函数必须带类型标注（Python 3.11+ 语法）
59. 所有 Pydantic 模型必须定义完整字段
60. 数据访问集中在 repository.py，Agent 不直接拼 SQL
61. Prompt 放在 prompts/ 目录，不在代码里写长字符串
62. 不写无用抽象，不提前做插件化
63. 不提前做多租户、复杂权限系统
64. 单文件不超过 400 行，超过拆模块
65. 错误处理用自定义异常，不用裸 except
66. 异步优先：所有 IO 操作 async/await
67. 日志用 structlog，不用 print

---

## 4. 当前不做（除非明确要求）

- React Web UI / TUI
- PostgreSQL / Qdrant / Redis / Celery / ARQ
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

---

## 5. 文件结构

```
songyan/
├── pyproject.toml, .env.example, README.md
├── CLAUDE.md                     # 本文件
├── creative_modes/               # 创作模式配置
├── genres/                       # 题材配置
├── prompts/                      # Agent Prompt 模板
├── docs/                         # 项目文档
│   ├── INDEX.md                  # 文档索引
│   ├── STATUS.md                 # 状态看板
│   └── decisions/                # 架构决策记录（ADR）
├── tasks/                        # Task 规格 + 交接报告
│   ├── TEMPLATE.md               # Task 文件模板
│   ├── 001-init-project.md
│   ├── 001-init-project-DONE.md  # 交接报告（完成后生成）
│   └── ...
├── src/songyan/
│   ├── __init__.py
│   ├── config.py                 # Pydantic Settings 配置
│   ├── cli/
│   ├── db/
│   ├── models/
│   ├── agents/
│   ├── workflows/
│   ├── utils/
│   └── creative_modes/
├── tests/
└── evals/
```

---

## 6. 技术栈（锁定）

| 组件 | 选型 |
|------|------|
| Python | 3.11+ |
| Pydantic | v2 |
| LangGraph | >=0.2 |
| LangChain | >=0.3 |
| litellm | latest |
| SQLite | 内置 |
| Click | latest |
| structlog | latest |
| tiktoken | latest |
| pytest | +pytest-asyncio |

---

## 7. 关键数据模型速查

```python
# PipelineNode Protocol（轻量版）
@runtime_checkable
class PipelineNode(Protocol):
    node_id: str
    stage: PipelineStage
    async def run(self, ctx: RunContext) -> NodeResult: ...

# RunContext（只读）
class RunContext(BaseModel):
    project_id: str
    chapter_number: int
    mode_id: str
    current_version_id: str | None
    # Agent 不直接访问数据库，只读此上下文

# NodeResult（Agent 返回，orchestrator 统一写入）
class NodeResult(BaseModel):
    node_id: str
    success: bool
    output: dict = Field(default_factory=dict)
    db_operations: list[DBOperation] = []  # 不直接执行
```

---

## 8. 交接检查清单（完成任务时必须确认）

- [ ] 代码实现完成
- [ ] 测试通过（pytest -v）
- [ ] 不违反本文件任何规则
- [ ] 更新了 docs/STATUS.md
- [ ] 生成了 tasks/00x-xxx-DONE.md 交接文件
- [ ] git commit 提交（包含代码 + 文档）
- [ ] 向用户汇报：做了什么、如何验证、已知限制

---

> **松烟入墨，字句成锋。**
> 每次只做一个小任务，先读后做，可验证再推进。
