# V7 Code Review & Architecture Audit Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan pass-by-pass. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对 Songyan V7 代码库做一次完整的“项目体检”和架构审计，识别 P0/P1/P2 级工程债务，产出可执行的修复清单，确保在 Ch200 爬坡前没有地基裂缝。

**Architecture:** 沿用 V4.0 `docs/code-review-plan.md` 的 Pass 结构，但针对 V7 现状（145 个源文件、V7 新子系统、Ch150 已验证）重新聚焦；审计以“事实源优先、职责分离、版本不可覆盖、上下文节食”四大铁律为基线，覆盖代码、架构、测试、V7 新能力、文档一致性五个层面。

**Tech Stack:** Python 3.11, LangGraph, Pydantic v2, SQLite, pytest, ruff, ripgrep, shell

---

## 1. 背景与审计触发条件

### 1.1 当前基线

- **代码规模**: `src/songyan/` 145 个 `.py` 文件，约 40,062 行；`tests/` 173 个 `.py` 文件，约 50,239 行。
- **验证状态**: V5/V6 已通过 Ch1–Ch150 验收；V7 阶段 W/X/Y 已完成，Task 170（enforce 小窗口验证 + T12 标定）已规划，尚未开工。
- **已知风险**:
  - `src/songyan/workflows/_nodes.py` 已膨胀至 2,652 行，集中了几乎所有节点实现与长尾后处理。
  - `src/songyan/agents/context_manager/__init__.py` 1,136 行、`agents/revision_handler/__init__.py` 1,029 行，接近维护拐点。
  - `src/songyan/db/schema.sql` 表编号存在重复（两个“4.5”）和顺序跳跃（13/14/15 颠倒，之后跳到 23）。
  - `src/songyan/db/migrations.py` 已累积 971 行。
  - 当前工作区 `git status` 显示 8 个文件已修改但 `git diff` 无可见差异，疑似行尾符或文件模式异常。

### 1.2 审计目标

1. 确认 V5/V6/V7 的核心工程纪律（事实源、版本不可覆盖、职责分离、上下文节食）在代码中仍然被遵守。
2. 识别阻止项目继续扩展至 Ch200–Ch300 的结构性债务（超大文件、紧耦合、schema 维护负担）。
3. 检查 V7 新子系统（叙事自驱、自适应门禁）的架构合理性与可测试性。
4. 产出分级修复清单（P0/P1/P2），为 Task 170 及阶段 Z 提供干净的代码基线。

### 1.3 不做的事

- 不直接修复发现的问题（修复另开 Task）。
- 不改 Prompt 内容本身（只检查 Prompt 管理机制）。
- 不启动新的长跑（Ch200 等 Task 170 之后）。

---

## 2. 审查范围与基线

### 2.1 审查范围

| 目录/文件 | 说明 |
|-----------|------|
| `src/songyan/` | 全部业务代码 |
| `tests/` | 全部测试代码 |
| `prompts/cards/` | Agent 工艺卡版本管理 |
| `genres/`, `creative_modes/` | 配置加载与约束 |
| `scripts/` | 长跑脚本与工具 |
| `pyproject.toml` | 依赖、lint、pytest 配置 |
| `docs/STATUS.md`, `tasks/V7-README.md`, `docs/v7-plan.md` | 状态与规划一致性 |

### 2.2 审查基线

- 测试基线: `pytest tests/ -q` 当前应通过（Task 169b 后 `2397 passed, 2 skipped, 1 xfailed, 2 warnings`）。
- Lint 基线: `ruff check src/ tests/` 通过。
- 版本基线: V7 Task 169 完成后的 `HEAD`。

### 2.3 优先级定义

| 级别 | 含义 | 处理要求 |
|------|------|----------|
| **P0** | 违反不可违背规则，或可能导致事实源污染、数据丢失、流程崩溃 | 必须修复后才能进入 Ch200 |
| **P1** | 高风险工程债务，可能放大维护成本或导致长跑不稳定 | 必须在阶段 Z 前修复 |
| **P2** | 中低风险改进项，建议修复但不阻塞 | 可排入后续迭代 |

---

## 3. 审查 Pass 详细清单

### Pass 1: 合规性审查（不可违背规则基线）

**目标:** 确认 `AGENTS.md` 中“不可违背规则”在代码中仍然成立。

**范围文件:**
- `src/songyan/workflows/_nodes.py`
- `src/songyan/db/repository.py`
- `src/songyan/db/context_repo.py`
- `src/songyan/db/settlement_repo.py`
- `src/songyan/agents/**/*.py`
- `src/songyan/models/*.py`

**检查清单:**

- [ ] **Step 1.1: 版本不可覆盖检查**
  - 命令: `rg 'UPDATE chapter_versions' src/songyan/ -n`
  - 期望: 仅在非内容字段（如 `current_head` 指针）上出现；`content`, `word_count`, `scenes` 不应被 `UPDATE`。
  - 方法: 若发现 `UPDATE chapter_versions SET content=...`，记录为 P0。

- [ ] **Step 1.2: character_states INSERT-only 检查**
  - 命令: `rg 'UPDATE character_states' src/songyan/ -n`
  - 期望: 仅 `lifecycle_status` 元数据可更新；状态字段必须只 INSERT。
  - 方法: 检查所有命中，确认是否为 `lifecycle_status` 专用路径；否则记录为 P0。

- [ ] **Step 1.3: Agent 层不直接拿 DB connection**
  - 命令: `rg 'from songyan.db.connection import get_db' src/songyan/agents/ -n`
  - 期望: 0 处命中（允许的例外：`db/repository.py`, `db/migrations.py`, `workflows/`  orchestrator, `cli/`）。
  - 方法: 每处命中检查是否发生在 Agent 包内部；若是，记录为 P0/P1。

- [ ] **Step 1.4: LangGraph state 只存 ID**
  - 文件: `src/songyan/workflows/phase1_graph.py`, `src/songyan/workflows/phase2_graph.py`
  - 期望: `Phase1State` / `Phase2State` 字段均为 `str | int | float | bool | None` 等标量或标量列表，不包含大对象（`ContextPackage`, `ChapterVersion`, `MergedReviewReport`）。
  - 方法: 逐项检查 state 字段类型；发现大对象记录为 P0。

- [ ] **Step 1.5: 结算证据校验检查**
  - 文件: `src/songyan/agents/settlement_extractor/_apply.py`, `_validate.py`
  - 期望: `character_update.old_value` 与 DB 当前值一致、`new_setting.source_quote` 在正文中存在、`numerical_update.closing_value` 公式闭合。
  - 方法: 确认 `_validate.py` 中仍有对应校验函数并被调用。

- [ ] **Step 1.6: 自动修订最多 2 轮**
  - 文件: `src/songyan/workflows/_nodes.py`
  - 期望: `revision_round` 上限为 2，超限时路由到 `rewrite` 或 `human_confirm`。
  - 方法: 检查路由函数中 `revision_round` 的判断条件。

**产出:** `docs/reports/v7-audit/pass1-compliance-report.md`

---

### Pass 2: 架构审计（职责分离与文件规模）

**目标:** 识别超大文件、职责集中、紧耦合、循环依赖等结构性风险。

**范围文件:**
- 全部 `src/songyan/workflows/`
- 全部 `src/songyan/agents/`
- 全部 `src/songyan/services/`
- 全部 `src/songyan/db/`

**检查清单:**

- [ ] **Step 2.1: 超大文件扫描**
  - 命令: `find src/songyan -name '*.py' -exec wc -l {} + | sort -rn | head -30`
  - 阈值: > 800 行视为高风险，> 600 行视为中风险。
  - 期望: 列出每个超大文件，说明其职责，判断是否可拆分。

- [ ] **Step 2.2: _nodes.py 职责清单**
  - 文件: `src/songyan/workflows/_nodes.py`
  - 方法: 逐段阅读，记录每个节点函数和辅助函数；按职责归类为 planning / writing / review / revision / settlement / routing / post-processing。
  - 产出: 一张职责分布表，指出哪些职责可以拆出。

- [ ] **Step 2.3: context_manager 拆分评估**
  - 文件: `src/songyan/agents/context_manager/__init__.py`
  - 方法: 识别 Context Assembler、BudgetPruner、TemporalCompressor、CharacterFocalDecay、SettingEvaporator、HardCeiling 等子组件边界。
  - 产出: 建议拆分为 `assemblers.py`, `pruner.py`, `compressors.py`, `decay.py`, `evaporator.py`。

- [ ] **Step 2.4: revision_handler 拆分评估**
  - 文件: `src/songyan/agents/revision_handler/__init__.py`, `_segmented_revision.py`
  - 方法: 识别 issue 筛选、readability 专精、prompt 渲染、patch 应用、safe-best 保护等职责。
  - 产出: 拆分建议。

- [ ] **Step 2.5: 导入图与循环依赖检查**
  - 命令:
    ```bash
    python -c "from songyan.workflows.phase1_graph import phase1_graph; print('phase1 ok')"
    python -c "from songyan.workflows.phase2_graph import phase2_graph; print('phase2 ok')"
    python -c "from songyan.agents.writer import WriterAgent; print('writer ok')"
    python -c "from songyan.agents.context_manager import assemble_context_package; print('context ok')"
    ```
  - 方法: 若任何导入失败，记录为 P0；使用 `pydeps` 或手动绘制导入图，识别 `_nodes.py` 的扇入扇出。

- [ ] **Step 2.6: Service 层缺失评估**
  - 文件: `src/songyan/services/`
  - 方法: 列出当前 Service 层覆盖范围；检查是否有 orchestration 逻辑散落在 nodes 中而应下沉到 Service。

**产出:** `docs/reports/v7-audit/pass2-architecture-report.md`

---

### Pass 3: 数据事实源与 Schema 审计

**目标:** 确认 SQLite 事实源的完整性、schema 的可维护性、迁移策略的健壮性。

**范围文件:**
- `src/songyan/db/schema.sql`
- `src/songyan/db/migrations.py`
- `src/songyan/db/repository.py`
- `src/songyan/db/context_repo.py`
- `src/songyan/db/settlement_repo.py`

**检查清单:**

- [ ] **Step 3.1: schema.sql 表编号整理**
  - 命令: `grep -nE '^\s*--\s*[0-9]+\.' src/songyan/db/schema.sql`
  - 方法: 列出所有表编号，标记重复、跳跃、顺序颠倒项（已知：两个 4.5，13/14/15 顺序颠倒，17 之后跳到 23）。
  - 产出: 建议重新编号为连续整数或引入版本化迁移编号。

- [ ] **Step 3.2: 表与模型一致性检查**
  - 方法: 对照 `src/songyan/models/` 中的 Pydantic 模型与 `schema.sql` 中的表字段，确认字段名、类型、约束一致。
  - 重点: `chapter_versions`, `character_states`, `setting_snapshots`, `foreshadowings`, `numerical_ledgers`, `replan_proposals`, `adaptive_halt_decisions`。

- [ ] **Step 3.3: migrations.py 复杂度评估**
  - 文件: `src/songyan/db/migrations.py`
  - 方法: 统计每个迁移版本的行数；检查是否依赖 `schema.sql` 初始状态；评估是否应拆分为独立迁移脚本。
  - 产出: 若文件 > 1000 行且无独立脚本，记录为 P1。

- [ ] **Step 3.4: Repository 接口一致性**
  - 方法: 检查 Repository 方法是否统一返回 Pydantic 模型或标量；是否所有写入都通过 `UnitOfWork` 或事务完成。
  - 重点: `accepted` / `current head` / `settlement` 写入是否使用事务。

- [ ] **Step 3.5: V7 新表索引检查**
  - 方法: 检查 `replan_proposals`, `foreshadowing_schedule_plans`, `foreshadowing_schedule_items`, `adaptive_gate_signal_snapshots`, `adaptive_halt_decisions` 是否有合理索引。
  - 命令: `grep -A 20 'CREATE TABLE.*replan_proposals\|CREATE TABLE.*foreshadowing_schedule\|CREATE TABLE.*adaptive' src/songyan/db/schema.sql`

**产出:** `docs/reports/v7-audit/pass3-data-and-schema-report.md`

---

### Pass 4: 工作流与 LangGraph 状态机审计

**目标:** 确认单章闭环和多章运行器的状态机正确、路由无死胡同、错误传播可靠。

**范围文件:**
- `src/songyan/workflows/phase1_graph.py`
- `src/songyan/workflows/phase2_graph.py`
- `src/songyan/workflows/_nodes.py`
- `src/songyan/workflows/_gates.py`
- `src/songyan/workflows/_helpers.py`

**检查清单:**

- [ ] **Step 4.1: Phase1 状态 schema 审计**
  - 文件: `src/songyan/workflows/phase1_graph.py`
  - 方法: 确认 `Phase1State` 字段完整覆盖所有节点输出；确认所有路由函数都读取了所需字段。

- [ ] **Step 4.2: 路由死胡同检查**
  - 方法: 绘制 Phase1 节点图（可用 LangGraph 的 `get_graph().draw_mermaid()`），确认每个状态都有出边；检查 `END` 条件是否只在接受/暂停时触发。

- [ ] **Step 4.3: Phase2 断点续跑与 AutoHalt 逻辑**
  - 文件: `src/songyan/workflows/phase2_graph.py`
  - 方法:
    - 确认 `--resume` / `--run-id` 以 `accepted` head 为唯一事实源。
    - 确认 kill 后续跑时清理孤儿 checkpoint。
    - 确认 `AutoHaltException` 与 V7 `adaptive_halt` 的交互不会重复暂停或漏暂停。

- [ ] **Step 4.4: 错误传播检查**
  - 方法: 检查各节点是否捕获 LLM 异常并写入 `state.error`；未捕获的异常是否会导致 LangGraph checkpoint 损坏。
  - 重点: `creative_director_node`, `writer_node`, `llm_auditor_node`, `settlement_extractor_node`。

- [ ] **Step 4.5: 硬门禁与自适应门禁边界**
  - 文件: `src/songyan/workflows/_gates.py`, `src/songyan/evals/adaptive_halt.py`
  - 方法: 确认 `_gates.py` 中的旧硬门禁是否仍被使用；确认 `adaptive_halt.py` 的 `halt` 决策如何被 Phase2 消费；两者优先级是否清晰。

**产出:** `docs/reports/v7-audit/pass4-workflow-report.md`

---

### Pass 5: Agent 边界与职责审计

**目标:** 确认每个 Agent 只负责单一职责，不越界修改正文或状态。

**范围文件:**
- `src/songyan/agents/writer.py`
- `src/songyan/agents/revision_handler/`
- `src/songyan/agents/rule_auditor.py`
- `src/songyan/agents/llm_auditor.py`
- `src/songyan/agents/literary_auditor.py`
- `src/songyan/agents/settlement_extractor/`
- `src/songyan/agents/context_manager/`
- `src/songyan/agents/creative_director/`
- `src/songyan/agents/continuity_auditor/`
- `src/songyan/agents/setting_evaporator/`

**检查清单:**

- [ ] **Step 5.1: Writer 只做初稿**
  - 方法: 确认 `writer.py` 不调用任何 revise/rewrite/settlement 逻辑；确认输出为 `ChapterVersion(version_type="draft")`。

- [ ] **Step 5.2: RevisionHandler 只做 patch**
  - 方法: 确认 `revision_handler/__init__.py` 不整章重写；确认只处理 `fix_type="patch"` 的 issues；确认 `rewrite_scene` 类型 issue 被排除。

- [ ] **Step 5.3: Auditor 不修改正文**
  - 方法: 确认 `rule_auditor.py`, `llm_auditor.py`, `literary_auditor.py` 只返回审查结果，不修改 `chapter_versions.content`。

- [ ] **Step 5.4: SettlementExtractor 只在 accept 后触发**
  - 文件: `src/songyan/workflows/_nodes.py`
  - 方法: 搜索 `settlement_extractor_node` 调用点，确认仅在 `human_confirm` 返回 `accept` 时触发；确认 `edit/reject/back` 不触发。

- [ ] **Step 5.5: GoalPlanner / CreativeDirector 不写正文**
  - 方法: 确认两者只输出 `ChapterGoal` / `CreativeBrief`，不操作 `chapter_versions.content`。

- [ ] **Step 5.6: ContextManager 不做审查判断**
  - 方法: 确认 `context_manager/__init__.py` 不调用任何 auditor 或 quality gate 逻辑。

**产出:** `docs/reports/v7-audit/pass5-agent-boundaries-report.md`

---

### Pass 6: 质量门与审查体系审计

**目标:** 确认 RuleAuditor、LLMAuditor、QualityGate、ScoreAggregator 的完整性与证据要求。

**范围文件:**
- `src/songyan/agents/rule_auditor.py`
- `src/songyan/agents/llm_auditor.py`
- `src/songyan/agents/literary_auditor.py`
- `src/songyan/evals/score_aggregator.py`
- `src/songyan/workflows/_nodes.py`（quality_gate_node）
- `src/songyan/workflows/_gates.py`

**检查清单:**

- [ ] **Step 6.1: critical/major issue 证据要求**
  - 方法: 检查 `llm_auditor.py` 解析逻辑是否过滤无 `evidence_quote` 的 critical/major issue；检查 `rule_auditor.py` 输出是否带定位信息。

- [ ] **Step 6.2: 元标记/段落重复检测有效性**
  - 文件: `src/songyan/agents/rule_auditor.py`
  - 方法: 确认 Task 160（元标记泄漏）和 Task 161（段落去重）的正则/检测逻辑覆盖 V6 暴露的 52 章元标记和 19 章重复样本。
  - 命令: `pytest tests/ -k 'meta_tag or paragraph_dedup or cleanliness' -v`

- [ ] **Step 6.3: QualityGate 阈值动态化**
  - 方法: 确认 `_SAFE_BEST_MIN_OVERALL_SCORE` 按章节位置动态化（Ch1–Ch20→0.75, Ch21–Ch50→0.78, Ch51+→0.82）；确认 `degraded_accept` 降级回滚路径存在。

- [ ] **Step 6.4: enforce / observe 模式一致性**
  - 文件: `src/songyan/cli/main.py`, `src/songyan/workflows/phase2_graph.py`
  - 方法: 确认 `--gate-mode` 参数正确传递；确认 observe 模式记录 gate 触发但不暂停，enforce 模式触发时暂停。

- [ ] **Step 6.5: 文学性诊断不阻塞 accept**
  - 方法: 确认 `literary_auditor.py` 输出不进入 `quality_gate_node` 的通过/失败判断。

**产出:** `docs/reports/v7-audit/pass6-quality-gates-report.md`

---

### Pass 7: V7 新子系统审计（叙事自驱 + 自适应门禁）

**目标:** 确认 V7 阶段 X/Y 的新能力架构合理、可审计、可回滚。

**范围文件:**
- `src/songyan/services/replan*.py`
- `src/songyan/services/foreshadowing_schedule*.py`
- `src/songyan/evals/adaptive_gate.py`
- `src/songyan/evals/adaptive_halt.py`
- `src/songyan/db/schema.sql`（replan / foreshadowing_schedule / adaptive_* 表）
- 相关测试: `tests/test_16*.py`, `tests/test_167*.py`, `tests/test_168*.py`, `tests/test_169*.py`

**检查清单:**

- [ ] **Step 7.1: re-plan 闭环可审计可回滚**
  - 方法:
    - 确认 `ReplanProposal` 生成不修改 `arc_plans` / `plot_threads`。
    - 确认 approved proposal 事务化应用，并保留 diff（`replan_actions` 表）。
    - 确认支持 rollback（或至少有足够记录支持人工回滚）。

- [ ] **Step 7.2: 伏笔主动调度生命周期**
  - 方法:
    - 确认 `foreshadowing_schedule_plans` / `foreshadowing_schedule_items` 记录调度章、目标章、状态。
    - 确认 GoalPlanner / CreativeDirector 正确注入 active 调度项。
    - 确认 accept 后推进 `satisfied` / `missed` 状态，并有 `source_version_id` 关联。

- [ ] **Step 7.3: 自适应门禁数据面完整性**
  - 方法:
    - 确认 `adaptive_gate_signal_snapshots` 每章记录关键信号（health、orphan、qg score、context emergency 等）。
    - 确认 `adaptive_halt_decisions` 记录判定理由、策略版本、人类复核状态。
    - 确认数据面采集不影响 Phase1 主流程性能。

- [ ] **Step 7.4: 自适应 halt 判定策略**
  - 文件: `src/songyan/evals/adaptive_halt.py`
  - 方法:
    - 确认策略输入使用相对趋势 / 异常因子，而非固定阈值。
    - 确认 `halt` / `halt_candidate` / `warn` / `observe` / `continue` 的决策边界有文档和单测覆盖。
    - 确认默认关闭或处于 observe 模式，不影响当前生产行为。

- [ ] **Step 7.5: V7 新功能测试覆盖**
  - 命令:
    ```bash
    pytest tests/test_166*.py tests/test_167*.py tests/test_168*.py tests/test_169*.py -v
    ```
  - 期望: 全部通过；若失败，记录为 P0/P1。

**产出:** `docs/reports/v7-audit/pass7-v7-subsystems-report.md`

---

### Pass 8: 测试质量与覆盖审计

**目标:** 评估测试结构、覆盖率、脆弱测试、慢测试、集成测试真实性。

**范围文件:**
- `tests/conftest.py`
- `tests/test_*.py`
- `pytest.ini` / `pyproject.toml` 测试配置

**检查清单:**

- [ ] **Step 8.1: 测试文件与源文件映射**
  - 方法: 列出每个 `src/songyan/` 核心模块对应的测试文件；识别无独立测试的子模块（如 `_apply.py`, `_constraints.py`, `_validate.py`）。

- [ ] **Step 8.2: 测试运行时间与慢测试识别**
  - 命令: `pytest tests/ --durations=20 -q`
  - 方法: 记录前 20 个最慢测试；若单个测试 > 30 秒且无 `performance` marker，记录为 P2。

- [ ] **Step 8.3: mock LLM 策略一致性**
  - 方法: 检查 `conftest.py` 是否提供统一 `mock_llm` fixture；检查各测试是否重复实现 mock。

- [ ] **Step 8.4: E2E 测试真实性**
  - 文件: `tests/test_phase1_graph.py`, `tests/test_phase2_graph.py`
  - 方法: 确认 E2E 测试覆盖 accept/edit/reject/back、断点续跑、AutoHalt、adaptive halt 接入；确认不使用真实 LLM（除非显式标记）。

- [ ] **Step 8.5: 参数化测试与边界覆盖**
  - 方法: 抽样检查关键测试（如 `test_rule_auditor.py`, `test_settlement_extractor.py`）是否使用 `@pytest.mark.parametrize` 覆盖边界。

**产出:** `docs/reports/v7-audit/pass8-testing-report.md`

---

### Pass 9: Prompt 与配置管理审计

**目标:** 确认 Prompt 统一放在 `prompts/cards/`，代码中无长 Prompt 字符串；配置加载健壮。

**范围文件:**
- `prompts/cards/**/*.yaml`
- `src/songyan/prompts/loader.py`
- `src/songyan/genres/`
- `src/songyan/creative_modes/`
- 全部 `src/songyan/agents/*.py`

**检查清单:**

- [ ] **Step 9.1: 代码内嵌 Prompt 扫描**
  - 命令: `rg 'def build_.*_prompt|prompt = """|prompt = f"""|system_message = ' src/songyan/ -n | head -50`
  - 期望: 仅 `prompts/loader.py` 和少量 prompt 构建辅助函数中有此类代码；Agent 主逻辑中无长 Prompt 字符串。

- [ ] **Step 9.2: Prompt 工艺卡版本管理**
  - 方法: 检查 `prompts/cards/<agent>/_manifest.yaml` 是否声明 default_version 与版本列表；检查代码中是否通过 `render_agent_prompt(agent, version=...)` 调用。

- [ ] **Step 9.3: Jinja2 模板注入防护**
  - 文件: `src/songyan/prompts/loader.py`
  - 方法: 确认使用 `SandboxedEnvironment` 并对 `{{` / `{%` 做转义。

- [ ] **Step 9.4: Genre / Mode 配置加载**
  - 方法: 确认 `genres/loader.py` 和 `creative_modes/` 注册表能处理缺失文件并给出明确错误；确认配置变更无需改代码。

- [ ] **Step 9.5: Prompt 版本与代码版本一致性**
  - 方法: 检查当前使用的 Prompt 版本是否与任务文档中声明的一致（如 Writer 1.1.0 / CreativeDirector 1.0.5）。

**产出:** `docs/reports/v7-audit/pass9-prompts-config-report.md`

---

### Pass 10: 性能与可观测性审计

**目标:** 识别性能热点、日志质量、运行中可观测性缺口。

**范围文件:**
- `src/songyan/evals/db_metrics.py`
- `src/songyan/rag/`
- `src/songyan/llm/`
- `src/songyan/workflows/_run_logger.py`
- `src/songyan/cli/main.py`

**检查清单:**

- [ ] **Step 10.1: RAG 向量加载性能**
  - 文件: `src/songyan/rag/vector_store.py`, `retriever.py`, `embedder.py`
  - 方法: 确认 VectorStore 是否每次检索都全量加载；确认是否有缓存或增量加载机制。

- [ ] **Step 10.2: Embedder 懒加载影响**
  - 文件: `src/songyan/rag/embedder.py`
  - 方法: 确认模型加载是否在首次检索时触发并导致 Ch2 卡顿；是否有预加载或错误降级。

- [ ] **Step 10.3: LLM 调用耗时与重试**
  - 文件: `src/songyan/llm/client.py`
  - 方法: 确认超时、重试、指数退避策略；确认 `request_id` 跨调用链关联。

- [ ] **Step 10.4: DB 维护遥测**
  - 文件: `src/songyan/evals/db_metrics.py`
  - 方法: 确认 `run_db_metrics` 表记录 DB 大小、表行数、VACUUM 时机；确认遥测不影响主流程。

- [ ] **Step 10.5: 结构化日志**
  - 方法: `rg 'print\(' src/songyan/ -n` 应接近 0；确认使用 `structlog` 并包含 `project_id`, `chapter_number`, `run_id` 等上下文。

**产出:** `docs/reports/v7-audit/pass10-performance-observability-report.md`

---

### Pass 11: 安全与依赖审计

**目标:** 识别依赖声明、凭证处理、输入验证等安全问题。

**范围文件:**
- `pyproject.toml`
- `.env.example`
- `src/songyan/config.py`
- `src/songyan/llm/client.py`
- `src/songyan/cli/main.py`

**检查清单:**

- [ ] **Step 11.1: 依赖声明完整性**
  - 命令: `rg '^(from|import) ' src/songyan/ -o | sed 's/^from //; s/^import //' | sort -u | head -100`
  - 方法: 对照 `pyproject.toml` 的 `dependencies`；确认 `jinja2`, `pyyaml`, `tiktoken`, `sentence-transformers` 等已声明。

- [ ] **Step 11.2: 环境变量与凭证**
  - 方法: 确认 `.env.example` 列出所有必需环境变量；确认代码不记录 API key；确认敏感文件在 `.gitignore` 中。

- [ ] **Step 11.3: 用户输入验证**
  - 文件: `src/songyan/cli/main.py`, `src/songyan/cli/outline_import.py`
  - 方法: 确认 `--project-id`, `--chapters`, `--outline-file` 等参数有类型/存在性校验；确认导入大纲 JSON 时做 schema 校验。

- [ ] **Step 11.4: SQL 注入风险**
  - 方法: 检查 repository 层是否全部使用参数化查询；检查是否有字符串拼接 SQL。

- [ ] **Step 11.5: 反序列化安全**
  - 方法: 检查 `json.loads` / `yaml.safe_load` 使用；确认不使用 `pickle` 或 `yaml.load`（unsafe）。

**产出:** `docs/reports/v7-audit/pass11-security-dependencies-report.md`

---

### Pass 12: 文档与状态一致性审计

**目标:** 确保文档、状态板、代码事实一致，无过期描述或相互矛盾。

**范围文件:**
- `docs/STATUS.md`
- `tasks/V7-README.md`
- `docs/v7-plan.md`
- `README.md`
- `docs/INDEX.md`
- `AGENTS.md`
- `docs/code-review-plan.md`

**检查清单:**

- [ ] **Step 12.1: STATUS.md 实时性**
  - 方法: 确认 `docs/STATUS.md` 中“当前阶段”“下一步规划”“最近全量测试”与代码/任务实际状态一致。

- [ ] **Step 12.2: 任务文档状态一致性**
  - 方法: 确认 `tasks/V7-README.md` 中 Task 160–169 均指向 `-DONE.md`，Task 170 为规划中；确认无“已完成”但无 `-DONE.md` 的任务。

- [ ] **Step 12.3: AGENTS.md 规则与代码一致性**
  - 方法: 将 `AGENTS.md` 中“不可违背规则”与 Pass 1 的发现对照；确认规则未被代码违反。

- [ ] **Step 12.4: 旧 code-review-plan 更新**
  - 文件: `docs/code-review-plan.md`
  - 方法: 确认 V4.0 审查计划是否仍有参考价值；若 V7 审计替代，则在文档中注明 V7 计划路径。

- [ ] **Step 12.5: 行尾符与工作区异常**
  - 命令:
    ```bash
    git status --short
    git diff --stat
    git diff --cached --stat
    ```
  - 方法: 若存在无可见 diff 的 modified 文件，使用 `git diff --ignore-all-space --stat` 和 `git ls-files --eol` 确认是否为 CRLF/文件模式变更；建议统一为 LF。

**产出:** `docs/reports/v7-audit/pass12-docs-consistency-report.md`

---

## 4. 执行路线图

```
Pass 1 (合规性) ──▶ Pass 2 (架构) ──▶ Pass 3 (数据/schema)
    │                    │                    │
    ▼                    ▼                    ▼
Pass 4 (工作流) ──▶ Pass 5 (Agent 边界) ──▶ Pass 6 (质量门)
    │                    │                    │
    ▼                    ▼                    ▼
Pass 7 (V7 新子系统) ──▶ Pass 8 (测试) ──▶ Pass 9 (Prompt/配置)
    │                    │                    │
    ▼                    ▼                    ▼
Pass 10 (性能/可观测) ──▶ Pass 11 (安全/依赖) ──▶ Pass 12 (文档一致性)
                              │
                              ▼
                    ┌──────────────────────┐
                    │  汇总报告 + 修复清单   │
                    │ docs/reports/v7-audit/ │
                    │   final-audit-report.md│
                    └──────────────────────┘
```

**执行纪律:**
- Pass 1 优先于所有其他 Pass；若发现 P0，应立即记录并在最终报告中升级。
- Pass 7 必须在 Pass 4/5/6 之后执行（需要先理解基础工作流和 Agent 边界）。
- 每个 Pass 独立产出报告，不混写。

---

## 5. 产出物清单

| 产出 | 路径 | 说明 |
|------|------|------|
| Pass 1 报告 | `docs/reports/v7-audit/pass1-compliance-report.md` | 合规性发现 |
| Pass 2 报告 | `docs/reports/v7-audit/pass2-architecture-report.md` | 架构审计发现 |
| Pass 3 报告 | `docs/reports/v7-audit/pass3-data-and-schema-report.md` | 数据/schema 审计发现 |
| Pass 4 报告 | `docs/reports/v7-audit/pass4-workflow-report.md` | 工作流审计发现 |
| Pass 5 报告 | `docs/reports/v7-audit/pass5-agent-boundaries-report.md` | Agent 边界发现 |
| Pass 6 报告 | `docs/reports/v7-audit/pass6-quality-gates-report.md` | 质量门审计发现 |
| Pass 7 报告 | `docs/reports/v7-audit/pass7-v7-subsystems-report.md` | V7 新子系统审计发现 |
| Pass 8 报告 | `docs/reports/v7-audit/pass8-testing-report.md` | 测试质量发现 |
| Pass 9 报告 | `docs/reports/v7-audit/pass9-prompts-config-report.md` | Prompt/配置发现 |
| Pass 10 报告 | `docs/reports/v7-audit/pass10-performance-observability-report.md` | 性能/可观测性发现 |
| Pass 11 报告 | `docs/reports/v7-audit/pass11-security-dependencies-report.md` | 安全/依赖发现 |
| Pass 12 报告 | `docs/reports/v7-audit/pass12-docs-consistency-report.md` | 文档一致性发现 |
| 最终汇总 | `docs/reports/v7-audit/final-audit-report.md` | 分级清单、风险热力图、修复建议 |
| 索引更新 | `docs/INDEX.md` | 新增 V7 审计入口 |

---

## 6. 报告模板（每个 Pass 使用）

```markdown
# Pass N: [名称] 审计报告

## 执行摘要
- 发现总数: X
- P0: Y, P1: Z, P2: W
- 关键结论（1-3 句）

## 检查项与发现

### [发现编号] [标题]
- **级别**: P0/P1/P2
- **文件**: `src/songyan/...:行号`
- **问题描述**: ...
- **证据**: 代码片段或命令输出
- **潜在影响**: ...
- **修复建议**: ...
- **验证方式**: 执行什么命令/测试可确认修复

## 通过项
- [列表中确认无问题的检查项]

## 待修复清单
| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| N-1 | P0 | ... | ... | ... |
```

---

## 7. 风险热力图（审计前预判）

| 维度 | 风险强度 | 预判理由 |
|------|----------|----------|
| 架构（超大文件） | █████████ | `_nodes.py` 2652 行、context_manager 1136 行、revision_handler 1029 行 |
| 数据/schema | ███████ | schema 编号混乱、migrations.py 971 行 |
| 工作流 | ██████ | Phase2 与 adaptive halt 交互需复核 |
| V7 新子系统 | ██████ | re-plan / 伏笔调度 / adaptive halt 尚未经 Ch200 验证 |
| 测试 | █████ | 部分 sub-module 无独立测试；E2E 运行时间可能过长 |
| Prompt/配置 | ████ | 工艺卡版本管理已较成熟，但需确认代码中无内嵌 Prompt |
| 性能 | █████ | RAG VectorStore 全量加载、Embedder 懒加载 |
| 安全/依赖 | ███ | 依赖基本完整，需确认无凭证泄露 |
| 文档一致性 | ████ | STATUS.md 更新频繁，可能与旧 code-review-plan 存在口径差异 |

---

## 8. 验证命令速查

```bash
# 全量测试
pytest tests/ -q

# Lint
ruff check src/ tests/

# 超大文件
find src/songyan -name '*.py' -exec wc -l {} + | sort -rn | head -30

# 内嵌 Prompt 扫描
rg 'def build_.*_prompt|prompt = """|prompt = f"""|system_message = ' src/songyan/ -n

# Agent 直连 DB
rg 'from songyan.db.connection import get_db' src/songyan/agents/ -n

# 版本覆盖风险
rg 'UPDATE chapter_versions' src/songyan/ -n

# TODO/FIXME
rg 'TODO|FIXME|XXX|HACK' src/songyan/ -n

# 测试耗时
pytest tests/ --durations=20 -q
```

---

## 9. 后续动作

1. 执行 Pass 1–12，产出 12 份报告。
2. 汇总为 `docs/reports/v7-audit/final-audit-report.md`，给出 P0/P1/P2 分级清单。
3. 根据 P0 修复清单开新 Task；P0 清零后再进入 Task 170 / Ch200。
4. 更新 `docs/INDEX.md` 和 `docs/STATUS.md`，记录审计结论。

> **松烟入墨，字句成锋。**
> 在迈向 Ch300 之前，先确认 150 章之后的地基没有裂缝。
