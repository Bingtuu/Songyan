这版比 v1 明显成熟很多：目标收敛、阶段拆分、事实源、版本模型、结构化审查、issue-driven 修订都补上了。现在已经从“宏大架构稿”变成了“可以指导 MVP 实现的设计稿”。

我的判断：v2 方向正确，可以作为工程起点；但 Phase 1 还有几处概念冲突和流程断点，需要修掉，否则实现时会踩坑。

主要优点

三阶段路线是对的
Phase 1 只验证单章闭环，Phase 2 验证跨章连续性，Phase 3 再产品化，这个节奏比 v1 健康很多。

Agent 收敛有效
4 个 Agent 的职责基本清楚：Planner、Writer、Reviewer、ContextManager。比 v1 的 10 个 Agent 更适合先落地。

版本管理补得很关键
chapter_versions + chapter_heads 是正确方向。小说写作必须保留 draft、revision、accepted、edited，否则后续人工编辑和回滚都会很痛苦。

审查输出可执行性提升很大
ReviewIssue 里有 evidence、related id、severity、suggested_fix、fix_type，这比抽象评分靠谱很多，也能驱动自动修订。

RAG 改成 Context Package 是正确抽象
对小说写作来说，“上下文包”比“通用知识库检索”更贴近实际需求。硬约束、软参考、最近剧情、角色状态、伏笔分区很合理。

需要修改的关键问题

Phase 1 的目标表述有矛盾
你说 Phase 1 是“单章闭环验证”，但完成标准又是“3 个题材各生成 10 章”，这已经是连续章节验证了，接近 Phase 2。
建议改成：

Phase 1：每个题材验证 1-3 章闭环，重点看生成、审查、修订、确认流程是否成立。
Phase 1.5 或 Phase 2 入门：每个题材连续 10 章。
Phase 2：重点不只是 10 章，而是“有结构化世界状态、角色状态、伏笔状态后的连续性验证”。
“checkpoint 不存业务数据”和 Phase1State 冲突
文档说 LangGraph checkpoint 只存执行现场，不存业务数据，但 Phase1State 里放了 project_setting、context_package、current_version、review_report 这些业务对象。实际 checkpoint 会保存它们。
建议改成：LangGraph state 只保存 ID 和轻量状态，例如 project_id、chapter_number、current_version_id、review_report_id、status、revision_round。业务对象每个节点从 SQLite 加载。

修订流程在图里没有真正建模
设计里说 issue-driven patch，但 LangGraph 里是 reviewer -> writer。这会让 Writer 很容易重新生成整章，而不是局部 patch。
建议增加独立节点：revision_planner 或 revision_handler。流程改成：
writer -> reviewer -> revision_handler -> reviewer。
Writer 只负责初稿，RevisionHandler 只负责按 issue 产出 patch。

Human confirm 没有入图，accepted 版本创建时机不清楚
当前 pass: END，注释说“人工在外部确认”。但数据库里有 accepted 版本，文档没明确谁创建、什么时候创建。
建议 Phase 1 也加一个很轻的 human_confirm CLI 步骤：通过后写入 accepted 版本，并更新 chapter_heads.accepted_version_id。

评测指标有自评循环风险
“质量评分 > 6/10”“结构化审查通过率 > 80%”都依赖 Reviewer 自己判断，容易自我证明。
建议加入少量人工金标：每个题材抽 3 章人工打分，记录“Reviewer 判断与人工判断一致率”。否则你不知道 Reviewer 是真的有效，还是只是稳定地产生评分。

数据库设计和前文表名不一致
3.3 写了 project_settings 表，但 7.1 SQL 里没有这个表，而是把项目设定字段直接放在 projects。二选一即可。
我建议 Phase 1 先直接放 projects，不要单独 project_settings，简单。

Context Package 需要持久化或可重建规则
代码里有 db.get_context_package(version.chapter_number)，但 SQL 没有 context_packages 表。
建议明确：ContextPackage 不作为事实源持久化，只从 SQLite 现有表实时组装；如果为了复现生成结果，可以在 chapter_versions.generation_metadata 里保存当次 context snapshot 的 JSON。

120K token 默认值过高
Phase 1 如果默认 120K，上下文成本和模型兼容性会很差。
建议默认目标设为 16K-32K，上限可配置。Phase 1 的上下文应该靠结构化摘要和硬约束精简，而不是默认塞大窗口。

建议的下一版改动

把 Phase 1 明确成“单章闭环 + 小规模连续验证”，不要和 Phase 2 的连续性目标重叠。
LangGraph state 只保存 ID，不保存完整业务对象。
增加 revision_handler 和 human_confirm 两个节点。
明确 accepted version 的创建规则。
增加 Reviewer 与人工金标的一致率指标。
修正表名不一致，并补充 ContextPackage 的重建/快照策略。
把 token budget 改成可配置，默认 32K 左右。
结论

v2 已经可以进入实现前设计了。现在最大的剩余风险不是“架构太大”，而是 Phase 1 的闭环边界还不够严谨：状态到底存哪里、修订到底谁做、人工确认如何落库、评测是否可信。把这四点补齐后，这份设计就比较适合作为 MVP 开发蓝图。