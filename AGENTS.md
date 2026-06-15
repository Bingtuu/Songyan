# AGENTS.md — Songyan V5.0 开发代理指令

> 按 Task 规格开发，测试通过，不违反 P0 规则。

---

## 1. 启动协议（每次开始新任务时执行）

```
1. 读取本文件（AGENTS.md）
2. 读取 docs/STATUS.md
3. 读取当前 tasks/10x-xxx.md
4. 读取上游 tasks/10x-xxx-DONE.md（如有依赖）
5. 用 5-8 行总结任务边界
6. 确认边界后再改代码
```

---

## 2. 项目定位

V5.0 核心目标：

> **"不是所有信息都值得记住。通过智能遗忘与分层压缩，支撑 150+ 章稳定生成。"**

验证范围：scifi + webnovel_intense，Ch1-Ch150 全自动 `--auto-confirm`。

（V1~V4 历史见 `archive/v3/INDEX.md`、`archive/v4/INDEX.md`）

---

## 3. 不可违背规则（违反必须回滚）

### P0 — 数据与状态（绝对不能违反）

| # | 规则 |
|---|------|
| 1 | SQLite 是唯一长期事实源 |
| 2 | LangGraph state 只存 ID，不存完整业务对象 |
| 3 | 每次生成/修订创建 chapter_versions 新记录，**禁止覆盖** |
| 4 | 每个节点从 SQLite 加载数据，不从 state 取正文 |
| 5 | `character_states` 快照表永远 INSERT，禁止 UPDATE（`lifecycle_status` 元数据除外） |
| 6 | 写操作集中在 Service/UnitOfWork，Agent 不直接拿 DB connection |
| 7 | accepted/current head/settlement 写入使用事务 |

### P0 — Agent 职责边界（绝对不能违反）

| # | 规则 |
|---|------|
| 8 | Writer 只做初稿，不做修订 |
| 9 | RevisionHandler 只做 patch，不整章重写 |
| 10 | RuleAuditor 只做代码检测，不做语义判断 |
| 11 | LLMAuditor 只做语义审查，不做代码检测 |
| 12 | LiteraryAuditor 只做诊断，**不阻塞 accept**，不修改正文 |
| 13 | GoalPlanner/CreativeDirector 不写正文，只输出结构化规划 |
| 14 | ReviewMerger 只做内存合并，**不调用 LLM**，耗时 < 10ms |
| 15 | ContextManager 不做生成，不做审查判断 |
| 16 | SettlementExtractor 只做结算提取和验证 |
| 17 | SummaryWriter 为轻量函数，基于 accepted 正文 + settlement 生成摘要 |

### P0 — 审查与修订（绝对不能违反）

| # | 规则 |
|---|------|
| 18 | LLMAuditor critical/major issue 必须有 evidence_quote |
| 19 | RuleAuditor 检测结果必须有定位信息 |
| 20 | **没有证据的 issue 不进入自动修订** |
| 21 | **自动修订最多 2 轮** |
| 22 | 修订引入新问题 → 停止自动修订，上报人工 |
| 23 | rewrite_scene 类型 issue 不自动修复 |

### P0 — 状态结算（绝对不能违反）

| # | 规则 |
|---|------|
| 24 | 每章 **accept 后必须执行 SettlementExtractor**，edit/reject/back 不触发 |
| 25 | Settlement 完成后执行 SummaryWriter |
| 26 | `character_update.old_value` 必须与 DB 当前值一致 |
| 27 | `new_setting.source_quote` 必须在正文中存在 |
| 28 | `new_setting.setting_key` 必须唯一 |
| 29 | `numerical_update.closing_value` 必须等于公式值 |
| 30 | `foreshadowings` 必须记录 `source_version_id` |

### P0 — 上下文 V5.0（绝对不能违反）

| # | 规则 |
|---|------|
| 31 | 上下文包按 Token 预算组装，默认 32K |
| 32 | **硬约束不裁剪**（genre_rules, mode_rules, chapter_goal, creative_brief, protagonist_profile）|
| 33 | 不出场的角色不加载详细档案；出场角色按未出场章数衰减（完整→精简→符号） |
| 34 | 设定/伏笔按 `resolve_confidence` 蒸发，低 confidence 自动 archive |
| 35 | `budget_used > 1.0` 时触发 ContextEmergency，只保留硬约束 + 主角档案 + ChapterGoal |
| 36 | **Context Diet 2.0 四组件协同生效**，不单独启用 |

### P1 — CreativeBrief 与 Genre（违反需修复）

| # | 规则 |
|---|------|
| 37 | 每章必须生成 CreativeBrief（required_tensions + forbidden_patterns） |
| 38 | CreativeDirector 不得新增硬剧情事件 |
| 39 | 每个项目必须关联 Genre Profile 和 CreativeModeProfile |
| 40 | generation_metadata 必须保存 context_snapshot + creative_brief |

### P1 — 代码规范（违反需修复）

| # | 规则 |
|---|------|
| 41 | 所有函数带类型标注（Python 3.11+） |
| 42 | 所有 Pydantic 模型定义完整字段 |
| 43 | 数据访问集中在 repository.py，Agent 不直接拼 SQL |
| 44 | Prompt 放在 prompts/ 目录，不在代码里写长字符串 |
| 45 | 异步优先：所有 IO 操作 async/await |
| 46 | 日志用 structlog，不用 print |
| 47 | 错误处理用自定义异常，不用裸 except |

### P2 — 工程约束（建议遵守）

| # | 规则 |
|---|------|
| 48 | 单文件不超过 400 行，超过拆模块 |
| 49 | 不写无用抽象，不提前做插件化/多租户 |
| 50 | V5.0 不新增 Genre/Mode/Agent/Workflow 节点 |
| 51 | V5.0 不做 Prompt 调优（字数控制、钩子质量属于 V5.1） |

---

## 4. 快速参考卡

```
当前版本: V5.0 "Context Diet 2.0"
当前 Task: 见 docs/STATUS.md
下一 Task: 101 (TemporalCompressor)

技术栈: Python 3.11+ / Pydantic v2 / LangGraph >=0.2 / SQLite / litellm
测试: pytest -v
代码检查: ruff check src/ tests/

Context Diet 2.0 四组件:
  1. TemporalCompressor — 金字塔分层摘要
  2. CharacterFocalDecay — 角色档案衰减
  3. SettingEvaporator — 设定语义蒸发
  4. BudgetHardCeiling — 预算硬天花板
```

---

## 5. 当前不做

- UI（Web/TUI）、外部数据库（PostgreSQL/Qdrant/Redis）、多模型路由
- 模板市场、拆书分析、完整 Studio
- V2.5+ 功能：角色心理模型、读者情绪模拟、PolyphonyPlanner、CharacterAutonomyAuditor、MacroNarrativePlanner
- ~~ContextService 按需检索~~（V4.0 Phase C 已归档，见 `archive/v4/`）

---

## 6. Task 完成流程（必须严格执行）

代码写完后，按以下顺序执行，**跳过任何一步视为 Task 未完成**。

### Step 1: 单元测试
```bash
pytest tests/ -v
```
**要求**: 所有测试通过。如有 pre-existing 失败，需明确标注并在汇报中说明。

### Step 2: 全量回归测试
```bash
pytest tests/ -q
```
**要求**: 运行完整测试套件。新增失败必须修复，不能留到下一个 Task。

### Step 3: 代码检查
```bash
ruff check src/ tests/
```
**要求**: 不引入新的 lint 错误。pre-existing 错误可在汇报中说明。

### Step 4: 生成 DONE 文档
```
tasks/10x-xxx-DONE.md
```
**要求**:
- **必须生成**，不写 DONE 文档 = Task 未提交
- 内容包含：做了什么、改了哪些文件、测试数据、验证结果、已知限制
- 参考 `archive/tasks/` 中的历史 DONE 文档格式

### Step 5: 更新 STATUS.md
- 标记当前 Task 为完成
- 更新下一 Task 编号
- 更新测试数量、达标率等关键指标

### Step 6: Git 提交
```bash
git add .
git commit -m "feat: Task 10x xxx"
```
**要求**: 提交包含代码修改 + DONE 文档 + STATUS.md 更新。

### Step 7: 向用户汇报
- 做了什么
- 如何验证（测试命令 + 结果数据）
- 已知限制

---

## 7. 交接清单（完成任务时确认）

- [ ] 代码实现完成
- [ ] **单元测试通过**（pytest tests/ -v）
- [ ] **全量回归测试通过**（pytest tests/ -q，无新增失败）
- [ ] 代码检查通过（ruff check src/ tests/，无新增错误）
- [ ] **生成了 tasks/10x-xxx-DONE.md**（强制，不写 = 未完成）
- [ ] 更新了 docs/STATUS.md
- [ ] git commit 提交（代码 + DONE 文档 + STATUS 更新）
- [ ] 向用户汇报：做了什么、如何验证、已知限制

---

> 松烟入墨，字句成锋。每次只做一个小任务，先读后做，可验证再推进。
