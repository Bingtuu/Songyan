# Pass 2: 架构审计报告

## 执行摘要

- 发现总数: 6
- P0: 0, P1: 3, P2: 3
- 关键结论: 项目整体架构清晰，分层原则（agents / workflows / db / services / evals）得到遵守，但 `_nodes.py`、context_manager、revision_handler 三个文件职责过度集中，已进入维护拐点；Service 层覆盖不足，大量 orchestration 逻辑仍散落在节点层。

## 检查项与发现

### 2.1 超大文件扫描

- **方法**: `find src/songyan -name '*.py' -exec wc -l {} + | sort -rn | head -30`
- **结果**:

| 排名 | 文件 | 行数 | 风险 |
|------|------|------|------|
| 1 | `src/songyan/workflows/_nodes.py` | 2,652 | 高风险 |
| 2 | `src/songyan/workflows/phase2_graph.py` | 1,270 | 中高风险 |
| 3 | `src/songyan/agents/context_manager/__init__.py` | 1,136 | 高风险 |
| 4 | `src/songyan/agents/revision_handler/__init__.py` | 1,029 | 高风险 |
| 5 | `src/songyan/db/migrations.py` | 971 | 中高风险 |
| 6 | `src/songyan/agents/settlement_extractor/_apply.py` | 875 | 中风险 |
| 7 | `src/songyan/db/settlement_repo.py` | 827 | 中风险 |
| 8 | `src/songyan/evals/db_metrics.py` | 789 | 中风险 |
| 9 | `src/songyan/agents/writer.py` | 772 | 中风险 |
| 10 | `src/songyan/evals/v6_acceptance.py` | 769 | 中风险 |

- **结论**: 前 4 个文件均超过 1,000 行，远超工程规范 400 行上限；`migrations.py` 接近 1,000 行。

### 2.2 `_nodes.py` 职责分布

- **级别**: P1
- **文件**: `src/songyan/workflows/_nodes.py`
- **方法**: 逐函数统计职责归属
- **结果**:

| 职责域 | 函数/行号范围 | 说明 |
|--------|---------------|------|
| 评分与 safe-best | 96-340 | `_safe_best_min_score`, `_score_card_*`, `_new_issues_for_current_version` 等 |
| 规划节点 | 365-449 | `goal_planner_node`, `creative_director_node` |
| 上下文节点 | 455-652 | `_get_context_package`, `_assemble_context_*`, `context_manager_node` |
| 写作/重写节点 | 654-1112 | `writer_node`, `rewrite_node` 及辅助函数 |
| 审查节点 | 1114-1648 | `rule_auditor_node`, `llm_auditor_node`, `review_merger_node`, `literary_auditor_node` |
| 修订节点 | 1649-1792 | `revision_handler_node` |
| 质量门/人工门 | 1793-2151 | `quality_gate_node`, `human_gate_node` |
| 生命周期/边界 | 2152-2255 | `_run_lifecycle_cleanup`, `accept_with_settlement_boundary`, `_should_block_empty_settlement` |
| 结算节点 | 2256-2645 | `settlement_extractor_node`（含 RAG/蒸发/摘要/线索/调度/输入侧治理） |

- **问题描述**: `_nodes.py` 同时承担了节点实现、评分策略、safe-best 保护、accept 边界、结算后处理编排等 9 类职责，是事实上的“上帝文件”。
- **潜在影响**: 任何 Phase1 流程改动都需要修改此文件，冲突概率高；单测文件 `tests/test_108_core_nodes.py` 也相应膨胀到 871 行。
- **修复建议**: 按职责拆分为独立模块：
  - `workflows/nodes/planning_nodes.py`（goal / creative / context）
  - `workflows/nodes/writing_nodes.py`（writer / rewrite）
  - `workflows/nodes/review_nodes.py`（rule / llm / merger / literary）
  - `workflows/nodes/revision_nodes.py`（revision_handler）
  - `workflows/nodes/gate_nodes.py`（quality_gate / human_gate）
  - `workflows/nodes/settlement_nodes.py`（settlement 及后处理）
  - `workflows/nodes/scoring.py`（safe-best / score_card 工具）
  - `workflows/_nodes.py` 仅保留兼容导出。

### 2.3 `context_manager/__init__.py` 拆分评估

- **级别**: P1
- **文件**: `src/songyan/agents/context_manager/__init__.py`
- **方法**: 统计顶层函数与主函数规模
- **结果**:
  - 顶层函数仅 6 个，但主函数 `assemble_context_package` 占用了约 1,000 行。
  - 内部已出现 `_dynamic_max_*`、`_rank_foreshadowings` 等辅助函数，说明逻辑复杂。
- **问题描述**: 整个 Context Diet 2.0 的组装与裁剪逻辑集中在一个函数中，包括：分层摘要加载、角色焦点衰减、设定蒸发、预算硬天花板、RAG chunks 注入、human marks 注入等。
- **修复建议**: 拆分为：
  - `context_manager/assemblers.py`（分区组装）
  - `context_manager/pruner.py`（BudgetPruner / 硬天花板）
  - `context_manager/decay.py`（CharacterFocalDecay）
  - `context_manager/evaporator.py`（SettingEvaporator）
  - `context_manager/compressor.py`（TemporalCompressor）
  - `__init__.py` 仅保留 `assemble_context_package` 入口与导出。

### 2.4 `revision_handler/__init__.py` 拆分评估

- **级别**: P1
- **文件**: `src/songyan/agents/revision_handler/__init__.py`
- **方法**: 统计顶层函数
- **结果**: 顶层函数 20 个，涵盖：
  - issue 筛选（`filter_patchable_issues`, `_filter_scene_split_issues`）
  - readability 专精路径（`_readability_metrics_from_report`, `_readability_driven`, `_build_readability_issues`）
  - prompt 渲染（`_render_issues`, `_render_prompt`）
  - patch 应用与分段修订（`_handle_scene_split`, `_handle_scene_overflow`, `_patch_mandatory_reference_missing`, `run_revision`, `save_revision_output`）
  - 新问题检测（`_detect_new_issues`）
- **问题描述**: 虽然已有 `_segmented_revision.py` 子模块，但主文件仍同时承担 issue 筛选、readability 策略、prompt 渲染、patch 执行、输出保存等职责。
- **修复建议**: 拆分为：
  - `revision_handler/issue_filter.py`
  - `revision_handler/readability.py`
  - `revision_handler/prompt_renderer.py`
  - `revision_handler/patch_engine.py`
  - `revision_handler/output_writer.py`
  - `__init__.py` 保留公共入口 `run_revision`。

### 2.5 导入图与循环依赖检查

- **级别**: 通过（需关注）
- **方法**:
  ```bash
  python -c "from songyan.workflows.phase1_graph import build_phase1_graph; print('phase1 ok')"
  python -c "from songyan.workflows.phase2_graph import run_project_pipeline; print('phase2 ok')"
  python -c "from songyan.agents.writer import write_chapter; print('writer ok')"
  python -c "from songyan.agents.context_manager import assemble_context_package; print('context ok')"
  ```
- **结果**: 全部导入成功，无显式循环依赖错误。
- **关注项**: `_nodes.py` 的导入扇出很大：
  ```text
  agents.context_manager, agents.creative_director, agents.goal_planner,
  agents.literary_auditor, agents.llm_auditor, agents.revision_handler,
  agents.rule_auditor, agents.settlement_extractor, agents.summary_writer,
  agents.writer, db.connection, db.context_repo, db.repository, db.review_repo,
  db.settlement_repo, evals.score_aggregator, services.foreshadowing_schedule,
  workflows._input_side_governance, workflows._narrative_context,
  workflows._thread_economy, workflows.review_merger
  ```
- **结论**: 当前无循环依赖错误，但 `_nodes.py` 是事实上的中央枢纽；拆分时应警惕新的循环依赖。

### 2.6 Service 层缺失评估

- **级别**: P2
- **文件**: `src/songyan/services/`
- **方法**: 列出 Service 层文件
- **结果**: Service 层仅 2 个文件：
  - `services/foreshadowing_schedule.py`（5,477 字节）
  - `services/replan_application.py`（11,065 字节）
- **问题描述**: V7 新子系统（re-plan、伏笔调度）已下沉到 Service，但核心工作流（accept 后编排、结算、评分、safe-best）仍由 `_nodes.py` 直接驱动。例如 `accept_with_settlement_boundary`、`_run_lifecycle_cleanup`、`_score_card_*` 等明显属于应用服务层逻辑，却放在节点实现文件中。
- **修复建议**: 新增 `services/chapter_lifecycle.py` 或 `services/settlement_orchestrator.py`，将 accept 边界、结算后处理、生命周期清理、评分聚合等逻辑下沉；`_nodes.py` 仅负责调用 Service 并返回 state 更新。

### 2.7 其他 P2 关注点

- **`phase2_graph.py` 1,270 行**: 同时承担多章运行、断点续跑、AutoHalt、DB 维护、质量债聚合、adaptive halt 调用。可考虑将 resume 逻辑、DB 维护、质量债聚合拆出到 `services/run_orchestrator.py`。
- **`db/migrations.py` 971 行**: 累积大量内联 ALTER；建议拆分为 `db/migrations/*.py` 按版本独立脚本，或引入 alembic-like 编号。

## 通过项

- [x] 核心导入图无循环依赖错误。
- [x] 项目目录结构符合 agents / workflows / db / services / evals 分层。
- [x] V7 新子系统（re-plan、伏笔调度）已正确放入 Service 层。

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 2.2 | P1 | `_nodes.py` 2652 行，承担 9 类职责 | 拆分为 `workflows/nodes/*.py` | `pytest tests/test_108_core_nodes.py tests/test_phase1_graph.py -q` |
| 2.3 | P1 | `context_manager/__init__.py` 1136 行，主函数过大 | 拆分为 `context_manager/{assemblers,pruner,decay,evaporator,compressor}.py` | `pytest tests/test_context_manager.py -q` |
| 2.4 | P1 | `revision_handler/__init__.py` 1029 行，职责混杂 | 拆分为 `revision_handler/{issue_filter,readability,prompt_renderer,patch_engine,output_writer}.py` | `pytest tests/test_revision_handler.py -q` |
| 2.6 | P2 | Service 层覆盖不足，大量 orchestration 逻辑在 `_nodes.py` | 新增 `services/chapter_lifecycle.py` / `services/settlement_orchestrator.py` | `pytest tests/ -q` |
| 2.7a | P2 | `phase2_graph.py` 1270 行，多章编排职责过重 | 拆出 `services/run_orchestrator.py` | `pytest tests/test_phase2_graph.py -q` |
| 2.7b | P2 | `db/migrations.py` 971 行，维护负担重 | 拆分为 `db/migrations/*.py` 或引入版本化迁移工具 | `pytest tests/db/ -q` |

---

> 下一 Pass: [Pass 3 数据事实源与 Schema 审计](pass3-data-and-schema-report.md)
