# Pass 7: V7 新子系统审计报告

## 执行摘要

- 发现总数: 4
- P0: 0, P1: 0, P2: 4
- 关键结论: V7 阶段 X/Y 的新子系统（re-plan、主动伏笔调度、adaptive gate/halt）架构合理、可测试，58 个相关测试全部通过。re-plan 应用有事务和 old_value 校验；adaptive halt 使用相对趋势/异常因子且默认关闭。建议增强 rollback 支持和将 Service 层 `except Exception` 收窄。

## 检查项与发现

### 7.1 re-plan 闭环可审计可回滚

- **级别**: P2
- **文件**: `src/songyan/services/replan_application.py`, `src/songyan/db/schema.sql:512-576`
- **方法**: 检查提案生成、审批、应用、diff 保留
- **结果**:
  - `replan_proposals` 表记录 `status`（draft/approved/rejected/applied）和审批时间/人。
  - `replan_actions` 表记录每个 action 的 `old_value_json` / `new_value_json`，保留 diff。
  - `apply_replan_proposal`（`:59`）在同一事务内顺序应用 actions，并校验 `old_value` 与当前值一致（`:267-278`）。
  - 仅支持修改未来 arc / plot_thread / 新增 planning_constraints（`:256-264` `_ensure_future_arc` 禁止修改历史弧）。
- **P2 建议**: 目前无自动 rollback 功能。虽然 diff 保留支持人工回滚，但建议增加 `rollback_replan_proposal` 方法，将 applied action 的 old_value 写回，以满足“可回滚”判据。

### 7.2 伏笔主动调度生命周期

- **级别**: 通过
- **文件**: `src/songyan/services/foreshadowing_schedule.py`, `src/songyan/db/schema.sql:578-630`
- **方法**: 检查计划/条目状态机和 accept 后推进
- **结果**:
  - `foreshadowing_schedule_plans` 状态：`draft` → `active` → `injected` → `satisfied`/`missed`/`cancelled`。
  - `foreshadowing_schedule_items` 同样具备完整状态机。
  - `activate_foreshadowing_schedule_plan`（`:21`）将 draft plan/items 转为 active。
  - `mark_schedule_items_injected`（`:50`）在规划侧使用后将 active 转为 injected。
  - `update_schedule_after_accept`（`:100`）在 accept 后按 settlement 文本匹配将 injected 推进为 satisfied 或 missed。
- **结论**: 主动调度生命周期完整，source_type/source_id/target_chapter 等字段支持溯源。

### 7.3 自适应门禁数据面完整性

- **级别**: 通过
- **文件**: `src/songyan/evals/adaptive_gate.py`, `src/songyan/db/schema.sql:632-652`
- **方法**: 检查信号域覆盖和刷新逻辑
- **结果**:
  - `adaptive_gate_signal_snapshots` 包含 6 个信号域 JSON 字段：`continuity`, `quality`, `literary`, `cleanliness`, `context`, `narrative`。
  - `refresh_adaptive_gate_signal_snapshots` 从 orphan 指标、新 critical 速率、文学分数、文本洁净度、DB 采样、调度项、可调度伏笔、规划约束、run logs 等多源聚合。
  - 使用 `_safe_collect` 对 DB 操作失败降级，不影响主流程。
- **结论**: 数据面覆盖全面，采集逻辑与主流程解耦。

### 7.4 自适应 halt 判定策略

- **级别**: P2
- **文件**: `src/songyan/evals/adaptive_halt.py`
- **方法**: 检查决策输入、状态边界、默认模式
- **结果**:
  - `_evaluate_window` 使用相对趋势/异常因子：health_min + P1/P2 median、orphan slope/delta、质量债比例、调度 missed/overdue、context pressure、cleanliness hard count。
  - `_status_from_reasons` 在 warmup_chapters 内最高只返回 `warn`；`require_multi_signal` 为 True 时要求跨域信号才 halt。
  - `mode` 为 `enforce` 时返回 `halt`，否则返回 `halt_candidate`。
  - Phase2 中 `gate_config.adaptive_halt_enabled` 默认关闭（`phase2_graph.py:167`）。
- **P2 建议**:
  - 策略阈值分散在 `AdaptiveHaltPolicy` 中，建议增加单测覆盖所有 reason code 触发条件。
  - `halt_candidate` 与 `halt` 的后续处理需明确：当前 `phase2_graph.py` 对两者均 pause run，语义上 `halt_candidate` 可改为只 warn 不暂停。

### 7.5 V7 新功能测试覆盖

- **级别**: 通过
- **方法**: `pytest tests/test_166*.py tests/test_167*.py tests/test_168*.py tests/test_169*.py -q`
- **结果**: `58 passed in 13.09s`
- **结论**: V7 新子系统测试覆盖充分。

### 7.6 Service 层异常处理

- **级别**: P2
- **文件**: `src/songyan/services/replan_application.py:87`, `src/songyan/services/foreshadowing_schedule.py:41,132`
- **方法**: 检查事务回滚处的 `except Exception`
- **结果**:
  - `apply_replan_proposal`: `except Exception` 用于回滚并包装为 `ReplanApplicationError`。
  - `activate_foreshadowing_schedule_plan`: `except Exception` 用于回滚并包装为 `ForeshadowingScheduleServiceError`。
  - `update_schedule_after_accept`: `except Exception` 用于回滚并包装。
- **问题描述**: 虽然注释说明是“rollback and wrap lifecycle errors”，但裸 `except Exception` 仍会吞掉 KeyboardInterrupt 等异常。建议使用 `except (sqlite3.Error, SongyanError, ValueError)` 等具体类型。
- **修复建议**: 收窄异常类型，保留事务回滚语义。

## 通过项

- [x] re-plan 提案生成不修改规划表，approved 后事务化应用。
- [x] re-plan action 保留 old_value/new_value diff。
- [x] 伏笔调度状态机完整：draft → active → injected → satisfied/missed。
- [x] adaptive gate 数据面覆盖 6 个信号域。
- [x] adaptive halt 使用相对趋势/异常因子，warmup 保护，默认关闭。
- [x] V7 新子系统 58 个测试全部通过。

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 7.1 | P2 | re-plan 无自动 rollback 方法 | `src/songyan/services/replan_application.py` + 新增测试 | `pytest tests/test_166*.py -q` |
| 7.4 | P2 | adaptive halt 阈值策略需更多单测覆盖 | `tests/test_169a_adaptive_halt_decision_engine.py` | `pytest tests/test_169*.py -q` |
| 7.4b | P2 | `halt_candidate` 与 `halt` 在 Phase2 中均 pause，语义可更清晰 | `src/songyan/workflows/phase2_graph.py` + `src/songyan/models/adaptive_halt.py` | `pytest tests/test_phase2_graph.py -q` |
| 7.6 | P2 | Service 层事务回滚使用裸 `except Exception` | `src/songyan/services/replan_application.py`, `src/songyan/services/foreshadowing_schedule.py` | `pytest tests/test_166*.py tests/test_167*.py -q` |

---

> 下一 Pass: [Pass 8 测试质量与覆盖审计](pass8-testing-report.md)
