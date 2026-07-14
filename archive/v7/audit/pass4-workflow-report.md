# Pass 4: 工作流与 LangGraph 状态机审计报告

## 执行摘要

- 发现总数: 5
- P0: 0, P1: 1, P2: 4
- 关键结论: Phase1 状态机和路由逻辑完整，无死胡同；Phase2 断点续跑以 `accepted` head 为事实源，resume 逻辑正确；adaptive halt 与旧硬门禁边界清晰。主要风险是 `_nodes.py` 中多处裸 `except Exception` 隐藏了具体异常类型，不利于调试；`phase2_graph.py` 过长导致单章运行与 run 级编排耦合。

## 检查项与发现

### 4.1 Phase1 状态 schema 审计

- **级别**: 通过
- **文件**: `src/songyan/workflows/phase1_graph.py:49-114`
- **方法**: 逐项检查 `Phase1State` 字段
- **结果**:
  - 字段覆盖所有节点输出：`chapter_goal_id`, `creative_brief_id`, `context_snapshot_id`, `current_version_id`, `review_report_id`, `literary_observation_id`, `settlement_id`, `summary_id`。
  - 控制字段完整：`revision_round`, `status`, `human_decision`, `error`。
  - 路由控制标志覆盖：`_needs_revision`, `_has_critical`, `_has_major`, `_quality_gate_passed`, `_skip_settlement`, `_was_rewritten` 等。
- **结论**: 状态 schema 完整，路由函数读取了所需字段。

### 4.2 路由死胡同检查

- **级别**: 通过
- **文件**: `src/songyan/workflows/phase1_graph.py:122-325`
- **方法**: 根据条件边映射检查每个分支是否有目标节点
- **结果**:
  - `revision_router`: `{revise, pass, rewrite}` 分别映射到 `revision_handler`, `quality_gate`, `rewrite`。
  - `rewrite_router`: `{audit, human_confirm}` 分别映射到 `rule_auditor`, `human_confirm`。
  - `quality_gate_router`: `{pass, rewrite, revision_needed, blocked}` 分别映射到 `human_confirm`, `rewrite`, `revision_handler`, `END`。
  - `human_confirm_router`: `{accept, edit_audit, reject, back, word_count_guard, error}` 分别映射到 `settlement_extractor`, `rule_auditor`, `goal_planner`, `writer`, `rewrite`, `END`。
  - `settlement_extractor` → `END`。
- **结论**: 所有条件分支均有明确目标，无死胡同。

### 4.3 Phase2 断点续跑与 AutoHalt 逻辑

- **级别**: 通过
- **文件**: `src/songyan/workflows/phase2_graph.py:461-518, 576-640, 698-929`
- **方法**: 检查 resume 起点计算、孤儿 checkpoint 清理、accepted 章节跳过
- **结果**:
  - `_compute_resume_start` 以 `accepted_chapters`（来自 `chapter_heads.accepted_version_id`）为唯一完成事实源。
  - resume 时调用 `prune_orphan_checkpoints(project_id, active_thread_ids=set())` 清理孤儿 checkpoint。
  - 循环内遇到 `accepted_chapters` 直接跳过。
  - `_check_auto_halt_window` 实现连续 3 章 QG 失败 / health_low streak / ContextEmergency degraded streak 熔断。
- **结论**: 断点续跑和 AutoHalt 逻辑符合设计。

### 4.4 错误传播检查

- **级别**: P1
- **文件**: `src/songyan/workflows/_nodes.py`
- **方法**: `rg 'except Exception' src/songyan/workflows/_nodes.py -n -B 2`
- **结果**: 发现 10 处裸 `except Exception`：
  - `:210`, `:241`, `:269` — `ChapterScoreCard.model_validate` 失败回退
  - `:904` — rewrite 版本创建失败
  - `:1138`, `:1737` — 加载 context package 失败回退
  - `:1292` — update_score_card 失败
  - `:1400` — degraded accept 维度判断失败
  - `:1825` — score_card 读取失败
  - `:2218` — accept 事务回滚（此处合理）
  - `:2432` — fallback summary 失败
- **问题描述**: 多处非事务性裸 `except Exception` 吞掉了具体异常类型，日志中只能看到 `error=str(exc)`，丢失了 traceback；可能掩盖可修复缺陷。
- **修复建议**: 将裸 `except Exception` 替换为具体异常类型（`ValueError`, `ValidationError`, `LLMError` 等），或在顶层统一捕获并记录 traceback。仅事务回滚处保留 `except Exception`。

### 4.5 硬门禁与自适应门禁边界

- **级别**: 通过
- **文件**: `src/songyan/workflows/_gates.py`, `src/songyan/workflows/phase2_graph.py:154-212`, `:813-880`
- **方法**: 检查两者调用位置与优先级
- **结果**:
  - `_gates.py` 中的 `evaluate_all_gates` 在 `_run_single_chapter` 末尾被调用，用于单章即时门禁判断。
  - `adaptive_halt` 在章节成功/失败后由 `_evaluate_adaptive_halt_for_run` 调用，独立于 `_gates.py`。
  - `GateConfig` 中 `adaptive_halt_enabled` 默认关闭（`phase2_graph.py:167` 显式检查）。
  - 单章硬门禁触发且 `gate_config.is_enforce()` 时，先 pause run；adaptive halt 触发时也 pause run。两者不互斥，但分别由不同配置控制。
- **结论**: 边界清晰，adaptive halt 默认不启用，不影响现有生产行为。

### 4.6 Phase1 图编译性能

- **级别**: P2
- **方法**: 尝试 `build_phase1_graph().get_graph().draw_mermaid()`
- **结果**: 命令超时（60s）。
- **问题描述**: 图编译或绘制耗时过长，可能与初始化 checkpointer/DB 连接有关。
- **修复建议**: 将图编译与 checkpointer 初始化解耦，或在测试/审计脚本中使用 memory checkpointer 加速。

### 4.7 Phase2 单章与 run 级编排耦合

- **级别**: P2
- **文件**: `src/songyan/workflows/phase2_graph.py`
- **方法**: 代码结构分析
- **结果**: `phase2_graph.py` 1270 行中，`_run_single_chapter` 占约 260 行，run 级循环、resume、DB 维护、质量债聚合、adaptive halt 调用等占约 900 行。
- **修复建议**: 将 `_run_single_chapter` 拆分到独立模块 `workflows/single_chapter_runner.py`；将 resume 逻辑、DB 维护、质量债聚合下沉到 Service 层（与 Pass 2 建议一致）。

## 通过项

- [x] Phase1 状态 schema 覆盖所有节点输出。
- [x] 路由条件边无死胡同。
- [x] Phase2 以 accepted head 为事实源，resume 逻辑正确。
- [x] 旧硬门禁与 adaptive halt 边界清晰，后者默认关闭。

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 4.4 | P1 | `_nodes.py` 多处裸 `except Exception` 吞掉具体异常 | `src/songyan/workflows/_nodes.py` | `ruff check src/ workflows/_nodes.py` + `pytest tests/test_108_core_nodes.py -q` |
| 4.6 | P2 | 图编译/绘制耗时过长 | 解耦 checkpointer 初始化或提供 memory 模式快速路径 | `python -c "from songyan.workflows.phase1_graph import build_phase1_graph; ..."` |
| 4.7 | P2 | `phase2_graph.py` 单章与 run 级编排耦合 | 拆出 `workflows/single_chapter_runner.py` | `pytest tests/test_phase2_graph.py -q` |
| 4.8 | P2 | `_nodes.py` 中 `error` 字段未统一类型（有时是字符串，有时可能是其他） | 统一 `error: str` 并在节点入口校验 | `pytest tests/ -q` |

---

> 下一 Pass: [Pass 5 Agent 边界与职责审计](pass5-agent-boundaries-report.md)
