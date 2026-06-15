整体判断：这版技术方案已经比原架构更适合进入开发。它抓住了三个关键：**ModeProfile 配置化、RuleAuditor/LLMAuditor 分层、状态快照只 INSERT**。方向可行。

但我建议在扩成完整版前，先修几个结构性问题。

**主要问题**

1. **V1.0 范围仍然偏大**  
   你写了“支持 3 种题材 × 3 种创作模式”，这对第一阶段太重。实际会变成 9 套组合，每套都要 prompt、规则、评测种子和人工金标。  
   建议 V1.0 改成：
   - 必做：1 个题材 + 2 种模式，例如 `xuanhuan + webnovel/hybrid`
   - 保留配置能力：目录里可以预置 3 个 genre / 3 个 mode，但验收只要求 1-2 个组合跑通
   - V1.1 再补齐都市/科幻/严肃文学

2. **工作流图里 HumanConfirm 的位置不够清晰**  
   文本写的是“生成 → 审查 → 修订 → 状态结算 → 人工确认”，但后面又写 `accept → Settlement`。正确顺序应该是：

   ```text
   Writer
   -> RuleAuditor + LLMAuditor
   -> LiteraryAuditor
   -> RevisionHandler, 最多 2 轮
   -> HumanConfirm
   -> SettlementExtractor
   -> SummaryWriter
   -> done
   ```

   状态结算必须在人工确认之后，否则会把未接受版本写进事实源。

3. **缺少 SummaryWriter / ChapterSummary 归属**  
   关键输出物里没有 `ChapterSummary`，Agent 表里也没有摘要生成节点。但下一章上下文高度依赖摘要。  
   建议增加一个轻量节点：
   - `SummaryWriter`：基于 accepted version + StateSettlement 生成摘要
   - 不一定算 Agent，可以是 LLM service
   - 输出写入 `summaries`

4. **CreativeDirector 和 GoalPlanner 的边界还会打架**  
   `GoalPlanner` 产出事件、情感弧、钩子；`CreativeDirector` 又产出创作意图、张力地图、禁忌清单。两者容易重复规划。  
   建议明确：
   - `GoalPlanner` 只回答“本章要发生什么”
   - `CreativeDirector` 只回答“这章应该怎么产生张力、避免什么惯性”
   - CreativeDirector 不得新增硬剧情事件，只能重排/解释/施压已有 ChapterGoal

5. **LiteraryAuditor “不阻塞”过于绝对**  
   不阻塞是对的，但它至少应该能影响 RevisionHandler 的策略。否则文学性诊断只是报告装饰。  
   建议改成：
   - 默认不阻塞 accept
   - 可输出 `protected_elements`
   - RevisionHandler 必须遵守 `protected_elements`
   - 严肃文学模式下，`conceptual_idling` 和 `character_autonomy` 可升级为 major，但仍需人工确认是否修

6. **RuleAuditor 的“首屏钩子”不能完全代码判断**  
   前 300 字是否有冲突/危险/情感冲击，纯代码很难可靠判断。  
   建议拆分：
   - 代码检测：前 300 字是否为空泛环境描写、是否无动作/对话/冲突词
   - LLM 判断：是否真的有吸引力事件
   - 合并维度仍叫 `narrative_hook`

7. **缺少统一插件协议**  
   你已经有低耦合方向，但技术方案里还没有写“Agent 插件接口”。这是扩展性的核心。  
   建议加一节：

   ```python
   class PipelineNode(Protocol):
       id: str
       stage: Literal["pre_write", "write", "audit", "revision", "settlement", "post_settlement"]

       async def run(self, ctx: RunContext) -> NodeResult:
           ...
   ```

   `RunContext` 只放 ID 和必要只读快照，不直接让 Agent 访问 DB 写入。所有写库通过 service/repository 层。

8. **CreativeModeProfile 需要更具体**  
   现在只有权重描述，不足以驱动流程。建议至少包含：

   ```python
   class CreativeModeProfile(BaseModel):
       id: str
       enabled_nodes: list[str]
       audit_weights: dict[str, float]
       blocking_dimensions: list[str]
       revision_policy: RevisionPolicy
       context_policy: ContextPolicy
       literary_policy: LiteraryPolicy
   ```

   这样“严肃文学”和“网文”不是只改 prompt，而是真正改变审查、修订、上下文裁剪和阻塞规则。

9. **Repository 层要防止 Agent 绕过事实源规则**  
   文档写了 SQLite 是唯一事实源，但需要技术约束。  
   建议：
   - Agent 层不直接拿 DB connection
   - 写操作集中在 `UnitOfWork` 或 service
   - `chapter_versions`、`character_states`、`review_reports` 都通过专门 repository 创建
   - 对 accepted version、current head、settlement 写入使用事务

10. **验收指标里有几个仍偏主观**  
   `概念空转段落数 = 0` 过硬，尤其严肃文学模式下会误杀。  
   建议改成：
   - 网文/混合：`conceptual_idling major = 0`
   - 严肃文学：`conceptual_idling unresolved = 0`，允许人工标记“有意保留”
   - 审查漏检率 `<20%` 对 V1.0 可能太难，建议先设 `<35%`，V1.1 再降

**建议补充的章节**

在完整版里建议新增 5 节：

1. **Pipeline Plugin 协议**  
   说明每个节点怎么注册、输入输出是什么、如何启停。

2. **RunContext 与数据访问边界**  
   明确 Agent 不能直接改数据库，只能返回结构化结果。

3. **ReviewIssue 标准模型**  
   尤其要定义：
   - `dimension`
   - `severity`
   - `evidence_quote`
   - `suggested_action`
   - `is_blocking`
   - `protected_by_literary_audit`

4. **RevisionPolicy**  
   不同模式下修订策略不同：
   - 网文：优先修节奏、钩子、爽点兑现
   - 严肃文学：避免抹平裂隙，修概念空转和人物工具化
   - 混合：critical 必修，major 人工确认

5. **最小可运行切片**  
   第一阶段不要一次开发 19 个 Task。先定义 vertical slice：
   - 创建项目
   - 输入一章种子
   - 生成下一章
   - 规则审查
   - LLM 审查
   - 人工 accept
   - 状态结算
   - 写入摘要

**推荐修改后的 V1.0 范围**

我会把 V1.0 写成：

```text
V1.0 验证目标：
跑通单题材、单章闭环，并证明系统能通过配置切换创作模式。

必交付：
- xuanhuan genre profile
- webnovel + hybrid mode profile
- GoalPlanner
- CreativeDirector
- ContextManager
- Writer
- RuleAuditor
- LLMAuditor
- LiteraryAuditor
- RevisionHandler
- HumanConfirm
- SettlementExtractor
- SummaryWriter
- SQLite + 版本链 + 快照表
- 3 个种子项目评测

非验收但预留：
- urban/scifi 配置文件
- literary mode 初版配置
```

**最终建议**

这版方案已经可以作为开发底稿，但在进入实现前，优先改三件事：  
第一，把 V1.0 范围收窄到“少数组合跑通”；第二，补上插件协议和数据访问边界；第三，明确 HumanConfirm、Settlement、Summary 的顺序。

这样系统底座会稳，后面无论扩成长篇网文生产线，还是严肃文学创作工作台，都不需要推翻重做。