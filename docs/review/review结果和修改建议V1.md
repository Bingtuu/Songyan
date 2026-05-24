
**总体评价**

设计合理性：中上。  
你把长篇中文小说的核心难题抓住了：世界观一致性、角色连续性、章节摘要、RAG、人工门控、修订闭环。这些方向是对的。LangGraph 也适合这种状态机 + 中断 + 可恢复工作流。

完备性：表面很完整，但关键执行细节还不够。  
文档覆盖了 agent、状态、RAG、数据库、部署、路线图，但很多部分是“概念完整”，缺少可验证的接口、失败处理、版本策略和评测标准。尤其是“一致性检查怎么判断对错”“修订是否真的变好”“RAG 检索失败怎么办”还偏抽象。

实现难度：高，当前 v1 范围过大。  
如果按文档全量实现，难度接近一个中型 AI 产品团队的 3-6 个月工程量，且前期很容易陷入 agent 编排、状态同步、审查循环和 UI 审核流的复杂性里，迟迟验证不了“能不能稳定写出好章节”。

**主要问题**

1. **MVP 过大**  
当前 MVP 写“基本写作 + 人工审核 + 简单审查”，但文档整体设计已经引入 FastAPI、React、TUI、Postgres、Qdrant、Redis、Celery、LangGraph、LangSmith、10 个 Agent。建议 MVP 只保留“项目设定 -> 单章生成 -> 审查 -> 人工修改 -> 结构化摘要入库”这一条闭环。

1. **Agent 数量偏多，职责有重叠**  
WorldBuilder、LoreKeeper、ConsistencyAuditor 都会碰设定；StyleEngine 和 QualityReviewer 都会碰文风；ConflictResolver 又会重新判断审查结果。建议早期收敛成 4 个核心角色：Planner、Writer、Reviewer、Memory/Context Manager。等单章质量稳定后再拆。

1. **状态源太多，容易不一致**  
文档里同时有 LangGraph checkpoint、PostgreSQL JSONB world_state、world_settings 表、Qdrant、Redis、中期 SQLite/Redis。这里会产生“到底谁是事实源”的问题。建议明确：PostgreSQL 是权威事实源；Qdrant 是派生索引；LangGraph checkpoint 是执行现场；Redis 只做临时缓存，不承载长期业务状态。

1. **一致性检查缺少可执行标准**  
“设定偏离度 > 0.3”“角色行为偏差 > 0.5”这些指标现在不可实现，除非定义评分 prompt、证据引用、冲突类型、置信度来源。建议每个审查结论必须输出：问题类型、原文片段、关联设定 ID、冲突说明、严重度、建议修复方式。没有证据引用的审查结果不进入自动返修。

1. **自动修订循环风险被低估**  
最多 5 轮修订不一定能防止质量退化。小说文本常见问题是“越修越平”“修掉风格”“修出新 bug”。建议自动修订最多 2 轮，之后进入人工确认；每轮修订只允许针对明确 issue 修改，不能整章重写。

1. **缺少章节/草稿版本模型**  
`chapters.content` 直接存正文不够。小说写作一定需要 draft、revision、accepted version、diff、人工编辑记录。建议新增 `chapter_versions` 或 `drafts`，每次生成和修订都保存版本，最终章节只指向 accepted version。

1. **RAG 方案偏“知识库通用”，不够小说专用**  
小说不是普通文档问答。检索需要区分：当前章前置事件、角色当前状态、未回收伏笔、禁用设定、时间线位置。建议把 RAG 从“文档检索”升级为“写作上下文包”：硬约束、软参考、最近剧情、角色状态、伏笔线索分区注入。

1. **新手优先的产品流还不够具体**  
你写了“渐进式披露”，但没有定义新手实际怎么开始：输入一句灵感后，系统问哪些问题？哪些自动生成？哪些必须确认？建议补一个“新项目创建向导”：题材、主角、核心爽点/看点、读者预期、禁忌、目标字数、更新节奏。

**修改建议**

我建议把架构改成“三阶段落地”：

1. **Phase 1：单章闭环验证**
   - 只做一个 CLI 或简单 Web 页面。
   - 输入：项目设定、角色卡、章节目标、上一章摘要。
   - 输出：章节草稿、审查报告、修订建议、章节摘要。
   - Agent：ContextAssembler、Writer、Reviewer。
   - 存储：PostgreSQL 或本地 SQLite 二选一，先不引入 Redis/Celery/TUI。

2. **Phase 2：卷级连续性**
   - 增加世界设定表、角色状态表、伏笔表、章节摘要表。
   - 引入 Qdrant，但只索引设定、角色、章节摘要。
   - 增加版本管理和人工审核界面。
   - 自动生成 5-10 章，验证角色/设定是否能持续稳定。

3. **Phase 3：完整多 Agent 产品化**
   - 再拆分 WorldBuilder、CharacterDesigner、PlotPlanner、LoreKeeper 等专业 agent。
   - 引入异步任务队列、WebSocket、监控、LangSmith/Langfuse。
   - 做批量章节生产、分叉时间线、风格模板、拆书分析。

**优先补充的设计内容**

- 明确数据事实源：Postgres 权威，Qdrant 派生，checkpoint 只管执行恢复。
- 增加 `chapter_versions`、`scene_cards`、`foreshadowings`、`character_states`、`timeline_events`。
- 审查结果统一结构化：证据片段、关联设定、严重度、修复建议。
- 自动修订限制为 issue-driven patch，不默认整章重写。
- 增加评测集：至少 3 个题材、每个 10 章，用一致性、可读性、重复率、人工返工率评估。
- 把技术栈路线图从“最终架构”拆成“验证架构 -> 产品架构”。

一句话建议：保留你的终态架构愿景，但把第一版目标改成“稳定生成并审查连续 10 章”，而不是“一开始搭完整多 agent 小说工厂”。这会显著降低实现风险，也更容易判断这个产品核心是否成立。