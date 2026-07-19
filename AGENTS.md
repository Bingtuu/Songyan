# AGENTS.md — Songyan 开发代理短指令

> 默认只读本短版，避免启动上下文膨胀。长版规则已归档：`archive/v5/context-docs/AGENTS-full-20260621.md`。

## 启动协议

1. 读取 `AGENTS.md`。
2. 读取 `docs/STATUS.md`。
3. 若任务指定 Task，读取对应 `tasks/<id>-*.md` 或相关 `*-DONE.md`；V1-V5.0 早期任务（001-120）已归档到 `archive/tasks/`；V6/V7/V8 任务已收尾，事实入口分别见 `tasks/V6-README.md`、`tasks/V7-README.md`、`tasks/V8-README.md`；V8 任务文档与报告已归档 `archive/v8/`。
4. 用 5-8 行说明任务边界，再改代码或文档。
5. 默认按现有架构和文档事实源推进，不重复扫描归档目录。

## 当前事实入口

- 项目状态：`docs/STATUS.md`
- 文档路由：`docs/INDEX.md`
- 当前阶段：V8 已全量闭环（含 V8.5）；V9 已开工（Task 173-188，173-182 已完成）
- V9 任务事实（当前阶段）：`tasks/V9-README.md`
- V8 历史任务事实（已收尾）：`tasks/V8-README.md`；任务文档与报告归档 `archive/v8/`（索引 `archive/v8/INDEX.md`）
- V7 历史任务事实（已收尾）：`tasks/V7-README.md`
- V6 历史任务事实（已收尾）：`tasks/V6-README.md`
- V5 历史任务事实：`tasks/V5-README.md`
- 论证基础：`docs/300-chapter-gap-analysis.md`
- 历史归档：`archive/v7/INDEX.md`、`archive/v6/INDEX.md`、`archive/v5/INDEX.md`、`archive/v4/INDEX.md`；V1-V5.0 早期任务见 `archive/tasks/`

## 项目定位

V5（V5.0/V5.1/V5.2）已全部工程验收通过：Context Diet 2.0 支撑长篇生成，enforce 默认启用，Ch1-Ch150 150/150 accept，P0/P1 风险为 0。

V6（Task 141-159）已完成：叙事骨架 MVP（StoryOutline / ArcPlan / PlotThread）、长篇质量度量、无人值守长跑底盘，验证到 Ch100-150。

V7（Task 160-171w）已收尾：篇章级质量修复 → 叙事自驱 → enforce 可生产化 → **sci-fi 单一体裁 Ch200 达成**。原 Task 172/173 单一体裁 Ch250/Ch300 目标取消；V8 复用 Task 172 编号作为项目模板化任务。

V8（Task 172-172l）已全量闭环：**多体裁可插拔质量 + 章数爬坡**目标达成——`GenreRuntimeProfile` 运行时契约与文学护栏从 sci-fi 隐式画像解耦；P/C/Q/S/V 五维验收全绿；xuanhuan + wuxia 双体裁 Ch100 五门 PASS；V8.5 遗留收口（172j/172k/172l）清零，C 判据 end10/end15/end20 三档证据落盘。V8 任务文档与报告见 `archive/v8/`。

当前阶段为 **V9（设计定稿，Task 173-188）**：生产化地基（V9.1 长跑可靠性 173-176 / V9.2 交付发布 177-181 / V9.3 工具链收编 182-184）+ urban 标定（185）与 Ch100 爬坡（186 任务书 → 187 执行）+ 收口（188）；验收 = A 组地基 8 条 + B 组 urban Ch100 六条 + C 组守护项；跨体裁 Ch200 与优秀度信号包归 V10。事实入口 `tasks/V9-README.md`。

## 不可违背规则

### 数据与状态

- SQLite 是唯一长期事实源。
- LangGraph state 只存 ID，不存完整业务对象或正文。
- 每次生成/修订必须创建 `chapter_versions` 新记录，禁止覆盖。
- 每个节点从 SQLite 加载数据，不从 state 取正文。
- `character_states` 快照表永远 INSERT，禁止 UPDATE（`lifecycle_status` 元数据除外）。
- 写操作集中在 Service/UnitOfWork，Agent 不直接拿 DB connection。
- accepted/current head/settlement 写入必须使用事务。

### Agent 边界

- Writer 只做初稿，不做修订。
- RevisionHandler 只做 patch，不整章重写。
- RuleAuditor 只做代码检测；LLMAuditor 只做语义审查。
- LiteraryAuditor 只诊断，不阻塞 accept，不修改正文。
- GoalPlanner/CreativeDirector 不写正文，只输出结构化规划。
- ReviewMerger 只做内存合并，不调用 LLM。
- ContextManager 不做生成，不做审查判断。
- SettlementExtractor 只做结算提取和验证。
- SummaryWriter 只基于 accepted 正文 + settlement 生成摘要。

### 审查与修订

- LLMAuditor critical/major issue 必须有 `evidence_quote`。
- RuleAuditor 检测结果必须有定位信息。
- 没有证据的 issue 不进入自动修订。
- 自动修订最多 2 轮。
- 修订引入新问题时停止自动修订，上报人工。
- `rewrite_scene` 类型 issue 不自动修复。

### 状态结算

- 每章 accept 后必须执行 SettlementExtractor；edit/reject/back 不触发。
- Settlement 完成后执行 SummaryWriter。
- `character_update.old_value` 必须与 DB 当前值一致。
- `new_setting.source_quote` 必须在正文中存在。
- `new_setting.setting_key` 必须唯一。
- `numerical_update.closing_value` 必须等于公式值。
- `foreshadowings` 必须记录 `source_version_id`。

### Context Diet 2.0

- 上下文包按 Token 预算组装，默认 32K。
- 硬约束不裁剪：genre_rules、mode_rules、chapter_goal、creative_brief、protagonist_profile。
- 不出场角色不加载详细档案；出场角色按未出场章数衰减。
- 设定/伏笔按 `resolve_confidence` 蒸发，低 confidence 自动 archive。
- `budget_used > 1.0` 时触发 ContextEmergency，只保留硬约束 + 主角档案 + ChapterGoal。
- Context Diet 2.0 四组件协同生效，不单独启用。
- **V8 新增**：Context Diet 2.0 的运行时契约（预算分配、门禁阈值、状态压缩、伏笔蒸发）必须能按体裁通过 `GenreRuntimeProfile` 定制；无 Profile 体裁必须 100% 回退旧行为。
- **172i 新增**：`load_profile()` 以代码注册表为体裁默认值基线，DB 记录作为字段级覆盖层；DB 未命中/不可用时回退代码注册表；未知体裁回退 scifi baseline。嵌套子模型按整体替换，不细粒度合并内部键。

## 代码规范

- Python 3.11+；所有函数带类型标注。
- Pydantic v2 模型字段定义完整。
- 数据访问集中在 repository / service / UnitOfWork。
- Prompt 工艺卡放在包内 `src/songyan/prompts/cards/`，代码中不写长 prompt；外部实验卡目录通过 `get_prompt_loader(cards_dir=...)` 注入。
- IO 操作优先 async/await。
- 日志用 structlog，不用 print。
- 错误处理用自定义异常，不用裸 except。
- 不新增无用抽象。`GenreRuntimeProfile` 机制已落地；后续按体裁调参优先走 Profile 注册表/DB 覆盖层，不新增 Agent / Workflow 节点（除非规划稿明确要求）；无 Profile 项目必须能回退旧行为。

## 验证要求

常规代码任务完成前执行：

```powershell
python -m pytest tests/ -q
ruff check src/ tests/
```

Windows 下长跑或 pytest 卡住时，使用防卡 wrapper（Task 176 已工具化）：`powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <秒> -- <命令>`；历史协议背景见 `archive/v5/context-docs/AGENTS-full-20260621.md`。

## Git 与归档

- 不回滚用户未要求回滚的改动。
- 不用 `git reset --hard` 或 `git checkout --` 覆盖用户改动。
- 当前入口保持短；长历史、旧规划、旧报告放入 `archive/`。
- 归档内容默认不读，除非用户要求追溯历史决策。
- 历史产物已归档至 `archive/v5/`、`archive/v6/`、`archive/v7/`、`archive/v8/`（V8 任务文档与报告，2026-07-18），入口见各 `INDEX.md`。
