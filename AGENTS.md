# AGENTS.md - Songyan 开发代理短指令

> 默认只读本短版。长历史、旧规划和旧报告均在 `archive/`，除非任务明确要求追溯，否则不要扫描归档目录。

## 启动协议

1. 读取 `AGENTS.md`。
2. 读取 `docs/STATUS.md`。
3. 当前阶段任务默认先读 `tasks/V11-README.md`；若任务指定历史阶段或历史 Task，再读对应阶段索引，例如 `tasks/V10-README.md` 或 `archive/v10/INDEX.md`。
4. 用 5-8 行说明任务边界，再改代码或文档。
5. 默认按现有架构和当前事实源推进，不重复扫全量历史目录。

## 当前事实入口

| 文件 | 用途 |
|------|------|
| `README.md` | 对外项目入口 |
| `docs/STATUS.md` | 当前状态与下一步 |
| `docs/INDEX.md` | 文档路由 |
| `tasks/V10-README.md` | V10 总结入口 |
| `archive/v10/INDEX.md` | V10 物理归档索引 |
| `archive/v10/reports/207-v10-closure-report.md` | V10 closure report |
| `tasks/V11-README.md` | V11 正式阶段入口 |
| `tasks/V11-Plan.md` | V11 早期规划备忘 |

## 当前阶段

V10 已全量闭环，Task 189-207 已完成并物理归档。当前阶段进入 V11 开源可用化收尾，正式入口为 `tasks/V11-README.md`，首任务为 Task 208 V11 readiness audit。V11 的目标是达到“负责任开源给外部技术用户”的条件，而不是把 Songyan 包装成普通商业产品。

V10 结论：

- sci-fi baseline 冻结，xuanhuan / wuxia / urban 均完成 Ch200 总验收。
- Task 196-203 优秀度信号包只作为 report-only 观察层。
- Task 204-206 结构 spike 均 decision=`defer`，不接 runtime、prompt、CED 或 hard gate。

V11 当前执行纪律：

- Task 208 审计先行：先从外部技术用户路径冻结缺口，再开发 209-215。
- 开源门槛见 `tasks/V11-README.md`，未满足时只能内部使用或发 preview，不标记为正式开源可用版本。
- V11 重点是安装、配置、doctor、项目创建、导出、恢复、run bundle、配置安全和发布纪律。
- `tasks/V11-Plan.md` 只是早期规划备忘，不再作为正式执行事实源。

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
- `GenreRuntimeProfile` 是体裁运行时契约；无 Profile 体裁必须回退旧行为。
- `load_profile()` 以代码注册表为体裁默认值基线，DB 记录作为字段级覆盖层。

### V11 守护项

- V11 只做开源可用化收尾，不扩张生成能力。
- Task 208 readiness audit 先行；未完成审计前，不直接启动 Quickstart / doctor / backup 等实现任务。
- CED 仍只统计 consistency-only、merged/source、正文证据。
- T9 仍是硬红线，PASS 样本必须 clean rerun 后 T9=0。
- Task 197-206 的 report-only / spike 信号不得进入 prompt、CED 或 hard gate。
- KG diff / FactTrack validity interval / Storyline Tree 若要生产化，必须另立 V11+ 任务并提供回归证据。
- 未满足 `tasks/V11-README.md` 的开源门槛前，不标记正式开源可用版本。

## 代码规范

- Python 3.11+；所有函数带类型标注。
- Pydantic v2 模型字段定义完整。
- 数据访问集中在 repository / service / UnitOfWork。
- Prompt 工艺卡放在包内 `src/songyan/prompts/cards/`，代码中不写长 prompt。
- IO 操作优先 async/await。
- 日志用 structlog，不用 print。
- 错误处理用自定义异常，不用裸 except。
- 不新增无用抽象。

## 验证要求

常规代码任务完成前执行：

```powershell
python -m pytest tests/ -q
ruff check src/ tests/
```

Windows 下长跑或 pytest 卡住时，使用防卡 wrapper：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <秒> -- <命令>
```

若改动影响体裁配置、上下文组装、prompt、harness 或质量 hard gate，补 scifi 短窗口回归；若影响 Ch200 口径，还必须重放 sci-fi Ch200 baseline。

## Git 与归档

- 不回滚用户未要求回滚的改动。
- 不用 `git reset --hard` 或 `git checkout --` 覆盖用户改动。
- 当前入口保持短；长历史、旧规划、旧报告放入 `archive/`。
- 归档内容默认不读，除非用户要求追溯历史决策。
- `tasks/` 只保留活跃入口：`TEMPLATE.md`、`V10-README.md`、`V11-README.md`、`V11-Plan.md`；V10 单项任务、报告和 artifact 已归档到 `archive/v10/`。
