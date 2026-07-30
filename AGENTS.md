# AGENTS.md — Songyan 开发代理短指令

> 默认只读本短版，避免启动上下文膨胀。长版规则已归档：`archive/v5/context-docs/AGENTS-full-20260621.md`。

## 启动协议

1. 读取 `AGENTS.md`。
2. 读取 `docs/STATUS.md`。
3. 若任务指定 Task，读取对应 `tasks/<id>-*.md` 或相关 `*-DONE.md`；若是 V10 任务，先读 `tasks/V10-README.md` 再读单项任务书。V1-V5.0 早期任务（001-120）已归档到 `archive/tasks/`；V5/V6/V7/V8/V9 均已收尾，事实入口分别见 `tasks/V5-README.md` 至 `tasks/V9-README.md`，单项任务文档归档到对应 `archive/v*/`。
4. 用 5-8 行说明任务边界，再改代码或文档。
5. 默认按现有架构和文档事实源推进，不重复扫描归档目录。

## 当前事实入口

- 项目状态：`docs/STATUS.md`
- 文档路由：`docs/INDEX.md`
- 当前阶段：V10.2 Task 194 urban Ch200 climb 进行中，Task 189/190/191 已完成，Task 192 xuanhuan Ch200 已完成，Task 193 wuxia Ch200 已完成；urban target DB=`.tmp/task_v10_urban_ch200.db`，project_id=`81e345042b124ee2a73094b82e4be555`，run_id=`run-v10-urban-743a979a`；Ch150 checkpoint 已 PASS；Ch151-Ch161 accepted，Ch161 accepted/current head=`v-f0f77ba5`；Ch162 GoalPlanner JSON parse failure 已冻结并开启 194.e，run status=`paused`、pause_reason=`manual_freeze:ch162_goal_planner_json_parse`、current_chapter=162、completed_count=161、failed=[162]、total_cost=8.748416；冻结目录 `.tmp/backups/194e_urban_ch162_goal_planner_json_parse_20260730-1326/`；下一步修复 Ch162 accepted gap，修复前不得继续 Ch163+；Task 196 优秀度样本集与校准协议已完成；V9 已全量闭环（Task 173-188）
- V10 规划入口：`tasks/V10-README.md`；README 本身不占任务号；Task 189 DONE：`tasks/189-ch200-baseline-and-checkpoints-DONE.md`；冻结 baseline：`tasks/189-scifi-ch200-baseline.json`；Task 190 DONE：`tasks/190-ch100-terminal-source-inventory-DONE.md`；Task 191 DONE：`tasks/191-ch200-harness-preparation-DONE.md`；Task 192/193/194 任务书：`tasks/192-xuanhuan-ch200-climb.md`、`tasks/193-wuxia-ch200-climb.md`、`tasks/194-urban-ch200-climb.md`；Task 192 DONE：`tasks/192-xuanhuan-ch200-climb-DONE.md`；Task 193 DONE：`tasks/193-wuxia-ch200-climb-DONE.md`；Task 192.p/q/r/s/t/u/v/w/x/y/z/aa/ab/ac/ad/ae/af/ag/ah/ai/aj/ak/al/am/an/ao/ap/aq/ar/as/at/au/av/aw DONE：`tasks/192.p-scifi-short-regression-context-emergency-DONE.md`、`tasks/192.q-xuanhuan-ch17-creative-director-json-parse-DONE.md`、`tasks/192.r-xuanhuan-ch24-settlement-numerical-validation-DONE.md`、`tasks/192.s-xuanhuan-ch50-t9-duplicate-clean-DONE.md`、`tasks/192.t-xuanhuan-ch75-segment-audit-critical-orphans-DONE.md`、`tasks/192.u-xuanhuan-ch81-health-low-p1-critical-orphan-DONE.md`、`tasks/192.v-xuanhuan-ch93-health-low-p1-critical-orphan-DONE.md`、`tasks/192.w-xuanhuan-ch99-settlement-numerical-validation-DONE.md`、`tasks/192.x-xuanhuan-ch99-segment-audit-critical-orphans-DONE.md`、`tasks/192.y-xuanhuan-ch105-health-low-p1-critical-orphan-DONE.md`、`tasks/192.z-xuanhuan-ch105-segment-audit-critical-orphans-DONE.md`、`tasks/192.aa-xuanhuan-ch106-invalid-model-run-state-cleanup-DONE.md`、`tasks/192.ab-xuanhuan-ch108-settlement-numerical-validation-DONE.md`、`tasks/192.ac-xuanhuan-ch108-segment-audit-critical-orphans-DONE.md`、`tasks/192.ad-xuanhuan-ch111-health-low-streak-halt-DONE.md`、`tasks/192.ae-xuanhuan-ch120-health-low-p1-halt-DONE.md`、`tasks/192.af-xuanhuan-ch129-settlement-json-parse-DONE.md`、`tasks/192.ag-xuanhuan-ch129-segment-audit-critical-orphans-DONE.md`、`tasks/192.ah-xuanhuan-ch131-literary-auditor-json-parse-DONE.md`、`tasks/192.ai-xuanhuan-ch134-health-low-streak-halt-DONE.md`、`tasks/192.aj-xuanhuan-ch138-health-low-p1-halt-DONE.md`、`tasks/192.ak-xuanhuan-ch144-health-low-streak-halt-DONE.md`、`tasks/192.al-xuanhuan-ch150-health-low-p1-halt-DONE.md`、`tasks/192.am-xuanhuan-ch150-segment-audit-critical-orphans-DONE.md`、`tasks/192.an-xuanhuan-ch150-five-gate-health-stale-report-DONE.md`、`tasks/192.ao-xuanhuan-ch156-health-low-streak-halt-DONE.md`、`tasks/192.ap-xuanhuan-ch162-health-low-p1-halt-DONE.md`、`tasks/192.aq-xuanhuan-ch168-health-low-p1-halt-DONE.md`、`tasks/192.ar-xuanhuan-ch175-segment-t9-hard-gates-DONE.md`、`tasks/192.as-xuanhuan-ch180-health-low-p1-halt-DONE.md`、`tasks/192.at-xuanhuan-ch186-health-low-p1-halt-DONE.md`、`tasks/192.au-xuanhuan-ch192-health-low-p1-halt-DONE.md`、`tasks/192.av-xuanhuan-ch198-health-low-p1-halt-DONE.md`、`tasks/192.aw-xuanhuan-ch200-five-gate-health-fail-DONE.md`
- V9 任务事实（已收尾）：`tasks/V9-README.md`；单项任务文档归档 `archive/v9/`（索引 `archive/v9/INDEX.md`）
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

V9（Task 173-188）已全量闭环：生产化地基（V9.1 长跑可靠性 173-176 / V9.2 交付发布 177-181 / V9.3 工具链收编 182-184）+ urban 标定（185）与 Ch100 爬坡（186 任务书 → 187 执行）+ 收口（188）全部完成；A 组地基 8 条、B 组 urban Ch100 六条、C 组守护项均 PASS。V9 事实入口 `tasks/V9-README.md`，归档入口 `archive/v9/INDEX.md`。

V10 规划入口已建立（`tasks/V10-README.md`），目标为**跨体裁 Ch200 + 优秀度信号包 + 结构升级 spike**。Task 189 已完成 sci-fi Ch200 baseline/checkpoint 冻结；Task 190 已完成 Ch100 终点事实源盘点；Task 191 已完成 Ch200 harness；Task 192 xuanhuan Ch200 已完成；Task 193 wuxia Ch200 已完成（five-gate/segment/T9 全 PASS）。当前按编号推进 Task 194 urban Ch200，已完成 Ch150 checkpoint（five-gate/segment/T9 全 PASS），Ch151-Ch161 accepted；Ch162 GoalPlanner JSON parse failure 已冻结并路由 194.e。V10 不补 V9 地基，也不做 V11 的开源用户可用化收尾。后续启动任何非 sci-fi Ch200 长跑前，必须使用 Task 191 harness，并遵守 Task 190 三态准入与 Task 189 baseline。

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

### V10 守护项

- Ch200 终判样本必须先保持生成链路稳定；190-191 完成前不得启动非 sci-fi Ch200 长跑。
- 优秀度信号包初期只做离线分析或 `report/observe` 输出，不得默认注入 Writer / CreativeDirector prompt，不得进入自动硬门。
- CED 仍只统计 consistency-only、merged/source、正文证据；优秀度、文学 craft、同质化、AI 腔不得混入 CED。
- T9 仍是硬红线；PASS 样本必须 clean rerun 后 T9=0，不接受解释性豁免。
- 任何运行时画像、上下文组装、prompt 注入、harness 或质量工具改动后，必须执行 scifi 短窗口回归；影响 Ch200 口径的改动还必须重放 sci-fi Ch200 baseline。
- KG diff / FactTrack validity interval / Storyline Tree 只作为 spike 给出取舍结论，不得伪装成 Ch200 主线阻塞项。

## 代码规范

- Python 3.11+；所有函数带类型标注。
- Pydantic v2 模型字段定义完整。
- 数据访问集中在 repository / service / UnitOfWork。
- Prompt 工艺卡放在包内 `src/songyan/prompts/cards/`，代码中不写长 prompt；外部实验卡目录通过 `get_prompt_loader(cards_dir=...)` 注入。
- IO 操作优先 async/await。
- 日志用 structlog，不用 print。
- 错误处理用自定义异常，不用裸 except。
- 不新增无用抽象。`GenreRuntimeProfile` 机制已落地；后续按体裁调参优先走 Profile 注册表/DB 覆盖层，不新增 Agent / Workflow 节点（除非 V10+ 任务书明确批准并给出回归证据）；无 Profile 项目必须能回退旧行为。

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
- 历史产物已归档至 `archive/v5/`、`archive/v6/`、`archive/v7/`、`archive/v8/`、`archive/v9/` 与 `archive/superpowers/`，入口见各 `INDEX.md`；V10 完成后归档到 `archive/v10/`。
