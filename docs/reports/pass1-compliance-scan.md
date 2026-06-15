# Pass 1 — 合规性审查报告

> **范围**: AGENTS.md §3「不可违背规则」代码合规扫描
> **日期**: 2026-06-10
> **审查者**: Codex (Pass 1 — 静态扫描)
> **状态**: 完成

---

## 摘要

| 等级 | 数量 | 判定 |
|------|------|------|
| P0 — 严重违规 | 3 类 (7+ 处) | 须修复后再进入 Phase B 验证 |
| P1 — 高度违规 | 2 类 (16+ 处) | 建议在 Phase B 验证前修复 |
| P2 — 中度违规 | 3 类 (200+ 处) | 建议在当前 Phase 内排入修复 |
| P3 — 轻微 / 建议 | 2 类 | 可纳入后续迭代 |
| 合规确认 | 20+ 条规则 | 无问题 |

---

## P0 — 严重违规

### P0-1: Rule 7 — chapter_versions 禁止覆盖（3 处）

**Rule 7**: "每次生成/修订创建 chapter_versions 新记录，禁止覆盖"

**检查手段**: 搜索 `UPDATE chapter_versions`

| 文件 | 行 | 代码 | 影响 |
|------|---|------|------|
| `workflows/_nodes.py` | 330 | `UPDATE chapter_versions SET content=?, word_count=?, scenes=?` | **直接覆盖已持久化的版本内容** — 最严重的违规 |
| `db/repository.py` | 464 | `UPDATE chapter_versions SET is_abandoned = 1` | 状态标记更新（低风险） |
| `db/repository.py` | 479 | `UPDATE chapter_versions SET version_type = ''accepted''` | 状态标记更新（低风险） |

**风险评估**:
- `_nodes.py:330` 在 accept 阶段覆盖已有版本的正文内容，而非创建新版本。如果 pipeline 回退到该版本，看到的不是原始生成内容而是被修改后的内容。历史复现能力受损。
- `repository.py:464/479` 是标记字段（`is_abandoned`、`version_type`）的 UPDATE，不涉及正文覆盖。

**建议**: `_nodes.py:327-338` 的 accept 逻辑应创建新版本记录，而非 UPDATE 现有版本。标记字段可改为状态机表。

---

### P0-2: Rule 53 — Agent 层直接访问 DB（2+ 处）

**Rule 53**: "Agent 层不直接拿 DB connection"

**检查手段**: 搜索 Agent 目录中的 `get_db` / `aiosqlite`

| 文件 | 行 | 违规说明 |
|------|---|---------|
| `agents/continuity_auditor/_constraints.py` | 138 | `from songyan.db.connection import get_db` |
| `agents/continuity_auditor/_constraints.py` | 146 | `async with get_db() as conn:` + 直接 `conn.execute(SQL)` |
| `agents/settlement_extractor/_apply.py` | 78 | 接收 `conn: aiosqlite.Connection` 参数 |
| `agents/settlement_extractor/_apply.py` | 279, 357 | 更多函数接收 `conn` 参数 |

**风险评估**:
- `_constraints.py` 最严重 — Agent 内部发起 `get_db()` 并直接执行 SQL 写操作，完全绕过 Repository 层和 NodeResult 模式
- `_apply.py` 接收 conn 参数是 Task 054 重构后的遗留设计，调用方管理事务

**建议**: `_constraints.py:146-155` 应改为通过 Repository 写入 human_marks 或通过 NodeResult 委托 Service 层。

---

### P0-3: Rule 64 — 单文件超过 400 行上限（16 个文件）

**Rule 64**: "单文件不超过 400 行，超过拆模块"

| # | 文件 | 行数 | 超出比 |
+---+------+------+--------+
| 1 | `workflows/_nodes.py` | 973 | 2.4x |
| 2 | `agents/revision_handler/__init__.py` | 745 | 1.9x |
| 3 | `agents/writer.py` | 730 | 1.8x |
| 4 | `agents/context_manager/__init__.py` | 696 | 1.7x |
| 5 | `db/repository.py` | 629 | 1.6x |
| 6 | `db/settlement_repo.py` | 483 | 1.2x |
| 7 | `agents/context_manager/_assemblers.py` | 481 | 1.2x |
| 8 | `workflows/_helpers.py` | 473 | 1.2x |
| 9 | `agents/settlement_extractor/__init__.py` | 458 | 1.1x |
| 10 | `agents/revision_handler/_segmented_revision.py` | 448 | 1.1x |
| 11 | `db/migrations.py` | 437 | 1.1x |
| 12 | `cli/main.py` | 432 | 1.1x |
| 13 | `db/layered_context_repo.py` | 418 | 1.0x |
| 14 | `db/context_repo.py` | 414 | 1.0x |
| 15 | `workflows/phase2_graph.py` | 412 | 1.0x |
| 16 | `agents/creative_director/__init__.py` | 407 | 1.0x |

**建议**: 优先拆分 `_nodes.py`（按节点职责），其次是 `revision_handler/__init__.py` 和 `writer.py`。

---

## P1 — 高度违规

### P1-1: Rule 65 — 裸 except Exception（14 处）

**Rule 65**: "错误处理用自定义异常，不用裸 except"

| 文件 | 行 | 上下文 |
|------+---+--------|
| `agents/writer.py` | 190 | style_samples 兜底 |
| `db/migrations.py` | 248 | 迁移失败兜底 |
| `llm/parsing.py` | 139 | JSON 解析失败兜底 |
| `prompts/loader.py` | 75 | 加载失败兜底 |
| `utils/cost_estimator.py` | 57 | 估算兜底 |
| `utils/token_estimator.py` | 24, 35 | 估算兜底 |
| `db/checkpointer.py` | 70 | 检查点兜底 |
| `workflows/_helpers.py` | 208, 245, 340, 468 | 摘要/审计/RAG |
| `workflows/_nodes.py` | 394, 475 | revision/accept 节点 |

**建议**: 每处应改为捕获具体异常类型，核心 pipeline 路径上的 8 处优先修复。

### P1-2: Rule 10 — character_states UPDATE（2 处）

**Rule 10**: "character_states 为快照表，永远 INSERT 新记录，禁止 UPDATE"

| 文件 | 行 | SQL |
|------+---+-----|
| `db/context_repo.py` | 237 | `UPDATE character_states SET lifecycle_status = ''dormant''` |
| `db/context_repo.py` | 299 | `UPDATE character_states SET lifecycle_status = ''archived''` |

**建议**: 若接受 V4.0 生命周期设计，需在 AGENTS.md 中为 Rule 10 加 lifecycle_status 例外说明。或者改为 INSERT-only 模式。

---

## P2 — 中度违规

### P2-1: Rule 58 — 缺少返回类型标注（~178 处）

**Rule 58**: "所有函数必须带类型标注（Python 3.11+ 语法）"

**重灾区**:
- `agents/` — 52 个函数缺返回类型（_assemblers.py 9 个，context_manager 12 个）
- `db/` — 38 个函数缺返回类型
- `workflows/` — 15 个函数缺返回类型
- `cli/` — 18 个函数缺返回类型（Click 回调豁免）

### P2-2: Rule 61 — 代码内嵌 Prompt 字符串（18 个文件）

**Rule 61**: "Prompt 放在 prompts/ 目录，不在代码里写长字符串"

| 文件 | 字符数 |
|------+--------|
| `agents/creative_director/__init__.py` | 2045 |
| `agents/revision_handler/_segmented_revision.py` | 1244 |
| `agents/context_manager/__init__.py` | 1068 |
| ...共 18 个文件 | ~16K |

**评估**: 大部分代码使用 craft card 系统正确加载 prompt 主体。嵌入的字符串是渲染逻辑的模板部分（变量拼接），而非完整 prompt。属于 P2 优先级。

### P2-3: Rule 42 — 不出场角色不加载（架构级）

**Rule 42**: "不出场的角色不加载详细档案"

`_assemblers.py:210` 的 `list_recent_by_project` 加载所有 active 角色而非仅当章出场角色。需引入出场预测逻辑。

---

## 合规确认（20+ 条规则无问题）

| 规则 | 检查内容 | 结果 |
|------+---------+------|
| Rule 5 | SQLite 唯一事实源 | OK |
| Rule 6 | LangGraph state 只存 ID | OK — Phase1State 确认 |
| Rule 9 | generation_metadata 含 context_snapshot + creative_brief | OK |
| Rule 21 | ReviewMerger 不调用 LLM | OK — 纯 Python |
| Rule 22 | RuleAuditor 有定位信息 | OK |
| Rule 24 | 自动修订最多 2 轮 | OK — 环境变量配置 |
| Rule 26 | rewrite_scene 不自动修复 | OK — 类型过滤 |
| Rule 27-30 | LiteraryAuditor 不阻塞 | OK |
| Rule 31-32 | accept 后触发 Settlement + Summary | OK |
| Rule 43-47 | Genre Profile 关联 | OK |
| Rule 48-52 | CreativeBrief 含 required_tensions + forbidden_patterns | OK |
| Rule 59 | Pydantic 模型完整 | OK |
| Rule 60 | Repository 集中数据访问 | OK（除 P0-2 例外）|
| Rule 62 | 不写无用抽象 | OK |
| Rule 66 | async/await | OK — 所有 IO 异步 |
| Rule 67 | structlog，不用 print | OK — 50+ 文件用 structlog |
| Rule 68-71 | V3.0 特有约束 | OK |

---

## 未检查规则（需人工/运行时审查）

| 规则 | 原因 |
|------+------|
| Rule 11-15 | Agent 职责边界 — 需语义理解 Agent 输出 |
| Rule 16 | GoalPlanner 不写正文 — 需检查输出历史 |
| Rule 17 | CreativeDirector 不新增硬剧情事件 — 需审查 LLM 输出 |
| Rule 18 | SettlementExtractor 只做提取 — 运行时行为 |
| Rule 25 | 修订引入新问题停止 — 运行时行为 |
| Rule 32-38 | 结算精度验证 — 需运行时数据 |

---

## 修复优先级

```
P0-1 (Rule 7)     ██▁▁▁▁▁▁▁▁▁  立刻修复 — accept 阶段覆盖版本内容
P0-2 (Rule 53)    ██▁▁▁▁▁▁▁▁▁  立刻修复 — Agent 直接管理 DB
P0-3 (Rule 64)    █████▁▁▁▁▁  拆分前 5 个大文件（~600 行+）
P1-1 (Rule 65)    ██████▁▁▁▁  替换 pipeline 路径上的 except Exception
P1-2 (Rule 10)    ███████▁▁▁  V4.0 决策讨论或 INSERT-only 改写
P2-1 (Rule 58)    █████████▁▁  补充 agents/ + db/ 返回类型
P2-2 (Rule 61)    ██████████▁  提取渲染常量到 prompts/
P2-3 (Rule 42)    ██████████▁  纳入 Phase C 范围
```

---

## 方法说明

### 扫描范围
- `src/songyan/` — 全部 102 个 `.py` 源文件
- `docs/` — STATUS.md + INDEX.md
- `tasks/` — 全部当前 Task 规格（含 DONE 报告）
- `prompts/` — 全部 craft card 文件

### 局限
- 没有运行时插桩（Pass 3 覆盖）
- 没有 LLM 输出检查
- 静态分析无法验证规则 25（修订引入新问题自动停止）
- SQL 注入和安全性检查不在 Pass 1 范围

---

## 后续步骤

1. **Pass 1 已完成** — 本报告已保存到 `docs/reports/pass1-compliance-scan.md`
2. **推荐 Pass 2（架构审计）**: V4.0 ContextService 过渡完整性、数据流、Agent 职责边界域
3. **推荐 Pass 3（测试质量审计）**: 测试覆盖缺口、边界情况、E2E runner 健壮性
4. P0 违规建议在 Task 096（Ch2-Ch50 回归验证）之前修复

---

> **松烟入墨，字句成锋。**
> 合规是系统稳定的底线 — 每条违规规则背后都是一个已经踩过的坑。
