# Pass 2 — 架构审计报告

> **范围**: V4.0 核心变更正确性、Agent 职责边界、字数约束链条、数据流完整性
> **日期**: 2026-06-10
> **审查者**: Codex (Pass 2 — 架构审计)
> **状态**: 完成
> **依赖**: Pass 1 已确认的 P0/P1 违规在本报告中引用但不重复

---

## 摘要

| 维度 | 判定 | 关键发现 |
|------|------|---------|
| 字数约束链条 | ✅ 完整 | GoalPlanner → Writer → RevisionHandler → Rewrite 均强制执行，阈值 ±20% |
| Agent 职责边界 | ✅ 大部分合规 | 13 个 Agent 职责清晰，但有 4 处跨域调用 |
| Settlement 流程 | ⚠️ 结构过重 | 单节点做 6 件事，职责混合 |
| 生命周期管理 | ✅ 设计良好 | 3 级状态机（active→dormant→archived），Protocol 注册模式 |
| 数据访问模式 | ⚠️ 半耦合 | _helpers.py 合规，_nodes.py + 2 个 Agent 直连 DB |
| ContextService 过渡 | ⏸️ 未启动 | Phase C 暂缓，当前仍用 V3.x ContextPackage 预组装模式 |
| 工作流编排 | ⚠️ 单文件过载 | `_nodes.py`（973 行）集编排、数据访问、后处理于一体 |

---

## 1. 字数约束链条审计

### 1.1 链条全景

```
GoalPlanner                    Writer                          RevisionHandler               Rewrite
┌────────────────┐     ┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│ word_count_tgt │────→│ ctx (ContextPack)│────→│ ±20% constraint    │────→│ ±20% constraint  │
│ chapter_type   │     │ _enforce_word_cnt│     │ _enforce_revision_ │     │ hard truncation  │
│ clamping       │     │ hard truncation  │     │ _word_count()      │     │ fallback         │
└────────────────┘     └──────────────────┘     └─────────────────────┘     └──────────────────┘
```

### 1.2 各环节细节

| 环节 | 文件 | 实现 | 合规 |
|------|------|------|------|
| **GoalPlanner** | `goal_planner.py:116` | `_build_chapter_goal()` → `_clamp_word_count()` + `CHAPTER_TYPE_WORD_TARGETS` 类型映射 | ✅ |
| **Writer** | `writer.py:397` | `_enforce_word_count()` → 软截断（±20%) + `_hard_truncate_at_boundary()` 硬回退 | ✅ |
| **Writer craft card** | `prompts/cards/writer/1.0.7.yaml` | scene_budget 注入：场景数建议 + 字数比例指导 | ✅ |
| **RevisionHandler** | `_segmented_revision.py:392` | `_enforce_revision_word_count()` → ±20%（Task 093 收紧自 ±25%） | ✅ |
| **Rewrite** | `_nodes.py:220-350` | Inject ±20% 约束 + post-generation 软截断 + 硬截断回退 | ⚠️ 见 1.3 |

### 1.3 发现的问题

**问题 1**: `rewrite_node` 在 `_nodes.py:327-338` 直接在截断后执行 `conn.execute(UPDATE chapter_versions)` 覆盖持久化内容。这既是 Pass 1 的 P0-1（Rule 7）违规，也绕过了 Writer 的版本管理逻辑。

**问题 2**: `writer.py` 的 `_enforce_word_count()` 和 `_hard_truncate_at_boundary()` 是 **private 函数**，但 `_nodes.py:29-32` 直接 import 使用。Node/Orchestrator 依赖 Agent 的内部实现细节。

**问题 3**: `rewrite_node` 使用前导下划线局部变量（`_goal`, `_upper_soft`, `_content` 等）约 30 个，是 Python 中表示"这个变量不会被外部使用"的习惯。在 150 行的函数中这种模式意味着缺乏结构拆分。

---

## 2. Agent 职责边界审计

### 2.1 13 个 Agent 职责对照表

| Agent | 文件 | 职责 | 合规 |
|-------|------|------|------|
| GoalPlanner | `goal_planner.py` | 生成 ChapterGoal（含 word_count_target）— 不写正文 | ✅ |
| CreativeDirector | `creative_director/__init__.py` | 生成 CreativeBrief（含 required_tensions/forbidden_patterns）— 不新增硬剧情事件 | ✅ |
| ContextManager | `context_manager/__init__.py` | 组装ContextPackage + Token 预算裁剪 — 不做生成/审查判断 | ✅ |
| Writer | `writer.py` | 初稿生成 + 字数截断 — 不做审查判断 | ✅ |
| RuleAuditor | `rule_auditor.py` | 纯代码检测（AI腔/疲劳词/段落节奏）— 不做语义判断 | ✅ |
| LLMAuditor | `llm_auditor.py` | 语义审查 — 不做代码检测 | ✅ |
| LiteraryAuditor | `literary_auditor.py` | 文学诊断（裂隙/风格/情绪弧）— 不阻塞 accept | ✅ |
| RevisionHandler | `revision_handler/` | patch-only 修订 + 字数约束 — 不整章重写 | ✅ |
| ReviewMerger | `workflows/review_merger.py` | 纯内存合并 — 不调用 LLM | ✅ |
| SettlementExtractor | `settlement_extractor/` | LLM 提取 + 代码验证 + 写入 — 职责混合 | ⚠️ |
| SummaryWriter | `summary_writer.py` | 基于 accepted 正文生成摘要 — 轻量函数 | ✅ |
| ContinuityAuditor | `continuity_auditor/` | 跨章一致性扫描 — 直接访问 DB | ⚠️ |
| StyleMimicryEngine | `style_mimicry_engine.py` | 风格注入 — 已在 writer craft card 中引用 | ✅ |

### 2.2 发现的边界违规

**跨域调用 1**: `_nodes.py` 直接 import 4 个 writer 的 private 函数
```python
from songyan.agents.writer import (
    _count_chinese_words,      # 内部工具函数
    _enforce_word_count,        # 字数截断逻辑
    _hard_truncate_at_boundary, # 硬截断
    _parse_scenes,              # 场景解析
)
```
**影响**: 如果 Writer 的内部截断逻辑发生变化，_nodes.py 也要同步修改。违反了"Agent 公共 API 应只暴露 `write_chapter()`"的边界原则。

**跨域调用 2**: `_nodes.py` 直接 import `_build_genre_rules` 和 `_detect_new_issues` 等 private 函数
```python
from songyan.agents.context_manager import _build_genre_rules
from songyan.agents.revision_handler import _detect_new_issues
```
**影响**: 同理，Orchestrator 依赖 Agent 的内部实现细节。

**跨域调用 3**: `continuity_auditor/_constraints.py:138` 直接 `from songyan.db.connection import get_db`
**影响**: Agent 不通过 Repository 访问 DB，已在 Pass 1 报告（P0-2）。

**跨域调用 4**: `context_manager/__init__.py` 直接 import `_assemblers` 的所有函数
**影响**: ContextManager 本身的内部拆分合理，没有外部函数依赖 `_assemblers` 的 private 函数。✅

---

## 3. Settlement 数据流审计

### 3.1 完整流程

```
human_gate_node
  │  decision = "accept"
  │
  ▼
settlement_extractor_node (_nodes.py:843-973)
  ├── 1. Extract settlement (LLM call: extract_settlement)
  ├── 2. Apply settlement to DB (apply_settlement with conn)
  ├── 3. Lifecycle cleanup (get_default_scheduler → run_cleanup)
  ├── 4. Write chapter summary (write_chapter_summary — LLM call)
  ├── 5. RAG index (_index_accepted_chapter)
  └── 6. Layered summaries (trigger_layered_summaries)
```

### 3.2 问题

**问题 1 — 职责过重**: 单节点做 6 件不同的事。每步都包装在 `try/except` 中，失败只记录日志不传播。

```python
# 模式重复 6 次：
try:
    await do_something(...)
except (LLMError, LLMResponseParseError, Exception) as exc:
    logger.warning("...failed", error=str(exc))
    # 继续执行下一步
```

这种模式意味着：
- 第一步失败（settlement extraction），后续 5 步仍会执行，但部分依赖第一步的结果
- 不可见的失败：除非人工查看日志，否则不会发现 settlement 提取失败
- `settlement_id` 和 `summary_id` 在最后被硬编码为 new_id（line 968-970），即使实际步骤失败

**问题 2 — 生命周期清理嵌入**: `lifecycle_cleanup`（line 884-913）内嵌在 settlement_extractor_node 中。V4.0 的核心架构变化之一是生命周期管理，但它被耦合在 settlement 节点中。

**问题 3 — Rule 31 确认**: accept 后确实触发 SettlementExtractor。✅ edit/reject/back 不触发。✅

---

## 4. V4.0 生命周期管理审计

### 4.1 架构

```
LifecycleScheduler (lifecycle_scheduler.py)
  ├── register_cleaner(cleaner: LifecycleCleaner)
  ├── run_cleanup(project_id, current_chapter) → LifecycleCleanupResult
  └── transition(conn, table, entity_id, from_status, to_status) → TransitionLog

Cleaners (lifecycle_cleaners.py)
  ├── SettingSnapshotCleaner       → setting_snapshots
  ├── ForeshadowingCleaner         → foreshadowings
  ├── HumanMarkCleaner             → human_marks
  ├── CharacterStateCleaner        → character_states
  └── ChapterChunkCleaner          → chapter_chunks
```

### 4.2 状态机

```
active ──(N 章未出场)──→ dormant ──(N 章未出场)──→ archived
  │                         │
  └──(再次出场)──→ 保持 active
```

| 表 | active→dormant 阈值 | dormant→archived 阈值 |
|----|---------------------|----------------------|
| setting_snapshots | 5 章未引用 | 15 章未引用 |
| foreshadowings | 基于 due_chapter | 基于 status + 时间 |
| human_marks | resolved → 直接 archived | unresolved → 20 章后 |
| character_states | 8 章未出场 | 15 章未出场 |
| chapter_chunks | N/A | 当章覆盖 |

### 4.3 问题

**问题 1 — 注册机制在代码中硬编码**: `lifecycle_cleaners.py:151` 的 `get_default_scheduler()` 直接实例化所有 Cleaner。应当使用配置或自动发现。

**问题 2 — 清理触发在 settlement_extractor_node 中**: `_nodes.py:884-913`。生命周期清理应当是独立的定时/事件任务，不应耦合在单章 pipeline 中。

---

## 5. 数据访问模式审计

### 5.1 当前模式

```
expected: Agent → Repository → DB
                               ↑
actual:   Agent → Repository __|__ (大部分 Agent)
          _nodes.py → get_db() ___|__ (P0-2)
          _constraints.py → get_db() __|__ (P0-2)
          _apply.py → conn param _______|__ (P0-2)
```

### 5.2 层间关系

| 层 | 文件 | DB 访问方式 | 合规 |
|----|------|-----------|------|
| **Repository** | `db/*_repo.py` | `async with get_db()` | ✅ |
| **Helpers** | `workflows/_helpers.py` | 全部委托给 Repository | ✅ |
| **Nodes** | `workflows/_nodes.py` | Line 36: `from db.connection import get_db` | ⚠️ 大部分委托，小部分直连 |
| **Agent** | `agents/*.py` | 多数委托给 Repository | ⚠️ 2 处直连（Pass 1） |
| **Workflow** | `workflows/*_graph.py` | 不访问 DB（纯编排） | ✅ |

### 5.3 关键问题

**缺乏 Service/UnitOfWork 层**: Rule 54-55 要求"写操作集中在 Service 层 / UnitOfWork"，当前没有 Service 层。`_nodes.py` 同时扮演 orchestrator + 部分数据写入者。如果未来引入事务要求（例如 "accept + settlement 必须全成功或全回滚"），当前模式无法保证。

**跨事务协调**: 当前每个 Repository 方法通过 `get_db()` 上下文管理器自动管理连接。跨 Repository 的事务（如 accept + settlement + summary）当前由 `_nodes.py:327-338` 手动调用 `conn.commit()`。这种模式不可靠 — 如果中间步骤失败，已写入的数据不会回滚。

---

## 6. V4.0 ContextService 过渡状态

| 组件 | V3.x（当前） | V4.0 目标（Phase C） | 实施状态 |
|------|-------------|---------------------|---------|
| 上下文组装 | `ContextPackage`（预组装）| `AgentContext`（按需检索）| 未开始 |
| 预算控制 | `budget used` + `BudgetPruner` | `AgentBudget`（自律约束）| 未开始 |
| 数据加载 | `_helpers.py` 加载全量后裁剪 | `ContextService` 按需检索 | 未开始 |
| Writer 字数 | 硬约束（prompt + 截断） | 硬约束（prompt + 截断双保险）| ✅ 已完善 |
| Revision 字数 | 硬约束 ±20% | 硬约束 ±20% | ✅ 已完善 |

**结论**: V4.0 Phase B 的"Agent 约束硬化"部分已完成。Phase C 的"Context-on-Demand"架构改造尚未启动。由于 Task 091 验证发现 token_budget 表现优秀（平均 1.073），Phase C 被正确搁置 — 没有数据支撑在当前阶段投入架构重写。

---

## 7. 工作流编排审计

### 7.1 LangGraph 状态机

```
GoalPlanner → CreativeDirector → ContextManager → Writer
                                                      │
                    ┌─────────────────────────────────┤
                    │  revision_router                 │
                    ▼                                 │
              RuleAuditor → LLMAuditor → ReviewMerger │
                    │                                 │
                    ▼                                 │
              RevisionHandler (round 0-2)             │
                    │                                 │
                    ▼                                 │
              Rewrite (if not converged)──────────────┤
                    │                                 │
                    ▼                                 ▼
              LiteraryAuditor → HumanGate → SettlementExtractor → END
```

### 7.2 路由策略验证

- **revision_router**: round 0-1 → revise / round 2 with issues → rewrite / rewritten → 1 more revision → pass ✅
- **human_gate_router**: accept → settlement / edit → editor → settlement / reject → retry / back → shutdown ✅
- **after_revision_router**: new issues introduced → repeat / converged → literary ✅

### 7.3 问题

**嵌套条件复杂**: `human_gate_node`（717-842 行）处理 accept/edit/reject/back/inject 5 种分支，加上 editor 调用和缓存逻辑，是目前最复杂的节点函数。

---

## 8. 总结

### 8.1 架构健康度

| 维度 | 健康度 | 关键发现 |
|------|--------|---------|
| 字数约束 | ### | 链条完整，阈值合理（±20%），但 rewrite_node 绕过版本管理 |
| Agent 边界 | #### | 13 个 Agent 职责清晰，但 _nodes.py 跨域调用 4 个 private 函数 |
| Settlement | ### | 流程完整，但单节点 6 件事 + silent failure 模式 |
| 生命周期 | #### | 设计良好（Protocol + 3 级状态机），但嵌入 settlement 节点 |
| 数据访问 | ### | _helpers.py 合规，但缺 Service 层 + 部分直连 DB |
| ContextService | ## | 已知债务，正确搁置，决策门 1 后评估 |
| 工作流 | ### | 编排逻辑正确，但 _nodes.py 973 行维护成本高 |

### 8.2 建议修复项

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| A1 | `_nodes.py` import 4 个 writer private 函数 | 维护耦合 | 提取 `_enforce_word_count` / `_count_chinese_words` 到 `utils/` |
| A2 | settlement_node 做 6 件事 | 职责混合 + silent failure | 拆分 lifecycle + summary + RAG 到独立的 post-accept 节点 |
| A3 | 缺乏 Service 层 | 跨事务无保障 | 引入 `ChapterService.accept_chapter()` 统一事务边界 |
| A4 | lifecycle 内嵌在 settlement 流程 | 耦合 | 独立为定时/回调任务 |
| A5 | ContextService 未启动 | 已知债务 | 决策门 1 后评估是否启动 |
| A6 | rewrite_node `UPDATE chapter_versions` | 覆盖版本（P0-1） | 改为 INSERT new version + 标记旧版本为 replaced |

### 8.3 与 Pass 1 的交叉引用

| Pass 1 违规 | Pass 2 关联 | 状态 |
|------------|------------|------|
| P0-1 (Rule 7: 版本覆盖) | A6: rewrite_node 直接 UPDATE | 交叉确认 |
| P0-2 (Rule 53: Agent DB) | _constraints.py 直连 + 缺 Service 层 | 交叉确认 |
| P0-3 (Rule 64: 文件行数) | `_nodes.py` 973 行 | 交叉确认 — 架构拆分建议 A1-A4 均可缩减 _nodes.py |
| P1-1 (Rule 65: except) | settlement_node 6 个 try/except | 交叉确认 |

---

> **松烟入墨，字句成锋。**
> 架构的优雅程度决定了系统能跑多远。目前 V4.0 的设计选择（放弃 ContextService 重写，改为约束硬化）在运营效率上是正确的。
