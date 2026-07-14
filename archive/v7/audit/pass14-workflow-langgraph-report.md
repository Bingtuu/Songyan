# Pass 14: 工作流与 LangGraph 节点审计报告

> **审计日期**: 2026-07-13
> **项目基线**: V7 Task 171w 完成后
> **审查范围**: `src/songyan/workflows/*`, `src/songyan/agents/goal_planner.py`, `arc_boundary_resolver.py`, `arc_summary_generator.py`, `src/songyan/db/replan_repo.py`, `src/songyan/evals/adaptive_halt.py`, `adaptive_gate.py`

---

## 执行摘要

工作流在功能测试层面稳定，路由无死胡同，resume 以 accepted head 为事实源，adaptive halt/gate 默认关闭。但存在 **1 个 P0 级数据一致性风险**（`rewrite_node` 截断失败时的内存/DB 不一致），以及多个 P1/P2 级纪律性问题（裸 except、state 携带业务 dict/list、同步阻塞调用、re-plan 缺 rollback）。

| 级别 | 数量 | 关键问题 |
|---|---|---|
| P0 | 1 | `rewrite_node` 截断后版本创建失败仍继续使用被修改的内存版本 |
| P1 | 4 | 裸 except 吞关键异常、同步编辑器调用、re-plan 缺 rollback、state 业务对象 |
| P2 | 10 | 超大文件、缺失字段、docstring 位置、无意义 DB 查询等 |

---

## P0 级问题

### P0-1 `rewrite_node` 截断后版本创建失败仍继续使用被修改的内存版本

- **文件路径**: `src/songyan/workflows/_nodes.py:872-931`
- **代码片段**:
  ```python
  if _truncation_applied:
      version.content = _new_content
      version.word_count = _new_wc
      version.scenes = _new_scenes
      try:
          ...
          await ChapterVersionRepository().create(new_version)
          await ChapterVersionRepository().mark_abandoned(old_version_id)
          ...
          version = new_version
      except Exception as exc:
          logger.warning(...)
          # 回退：继续使用已更新的内存对象
  ```
- **问题描述**: 当 rewrite 结果需要截断时，代码先就地修改内存对象 `version.content / word_count / scenes`，再尝试创建新版本并废弃旧版本。若后续 `create` / `mark_abandoned` / `update` 失败，`except Exception` 仅记录日志并继续使用已更新的内存对象。
- **潜在影响**:
  - 违反“禁止覆盖版本内容”铁律：旧版本 DB 记录仍是原始长文本，但 `state["current_version_id"]` 指向该旧版本，后续节点看到的 `version` 却是被截断后的内容，导致 DB 与 state 不一致；
  - 可能把未通过质量门的长文本当作已接受版本进入 settlement；
  - 异常原因被日志吞掉，排查困难。
- **修复建议**: 将截断逻辑放入同一事务/同一工作单元：先创建新版本对象，再决定是否废弃旧版本并更新 head。任何写入失败都应回滚到原始版本，**不允许在旧版本对象上就地修改内容**。

---

## P1 级问题

### P1-1 关键路径上的裸 `except Exception` 吞掉关键异常

| 文件 | 位置 | 问题 | 影响 |
|---|---|---|---|
| `_nodes.py` | 1157 | `rule_auditor_node` 加载 `mandatory_references` 失败时整体跳过 | critical orphan 约束漏检 |
| `_nodes.py` | 1320 | `review_merger_node` 保存 `score_card` 失败仅记录 | 版本记录缺少评分卡，影响 safe-best / QG 判断 |
| `_nodes.py` | 1775 | `revision_handler_node` 加载 `mandatory_references` 失败时整体跳过 | revision 后丢失强制回收约束检查 |

- **修复建议**: 将裸 `except Exception` 替换为精确异常类型（`ValidationError`、`LLMError`、`ValueError` 等），或在顶层统一捕获并记录 traceback。

### P1-2 `human_gate_node` 在 async 节点中调用同步阻塞编辑器

- **文件路径**: `src/songyan/workflows/_nodes.py:2055` 及 `_open_editor` (`:363-375`)
- **问题描述**: `human_gate_node` 是 `async def`，但在 `decision == "edit"` 分支中直接调用同步的 `_open_editor`，其内部使用 `subprocess.run([editor, temp_path], check=True)` 和文件 I/O。
- **潜在影响**: 阻塞事件循环，影响其他并发章节/节点；在长跑或 Web 服务场景下会造成整体卡顿。
- **修复建议**: 使用 `await asyncio.to_thread(_open_editor, version.content)` 或 `asyncio.create_subprocess_exec`。

### P1-3 `Phase1State` 仍携带业务 `dict/list`，违反“state 只存 ID”纪律

- **文件路径**: `src/songyan/workflows/phase1_graph.py:49-115`
- **问题描述**: `Phase1State` 声明中存储了多项业务对象或列表：`_best_score_card: dict`、`_score_card: dict`、`_new_issues_introduced: list[dict]`、`_prev_merged_issues: list[dict]`、`_context_metrics: dict`、`_quality_gate_failures: list[str]`、`_deferred_constraints: list[str]`。此外 `human_gate_node` 还动态注入 `human_instructions: list`。
- **潜在影响**:
  - 与 AGENTS.md“LangGraph state 只存 ID，不存完整业务对象或正文”直接冲突；
  - checkpoint 体积增大，跨线程/断点续跑时易出现序列化不一致；
  - `_new_issues_introduced` 等列表需手动按 `version_id` 过滤，说明设计上就不应放在 state 中。
- **修复建议**: 将评分卡、issues 列表、上下文指标改为存入 DB（如 `chapter_versions.score_card`、`review_reports`），state 中仅保留 `*_id`；`human_instructions` 如需跨节点传递，可放入独立表并引用其 ID。

### P1-4 re-plan 闭环缺少自动 rollback 方法

- **文件路径**: `src/songyan/db/replan_repo.py`
- **问题描述**: `ReplanProposalRepository` 提供了 `create`、`approve`、`reject`、`mark_applied` 以及 `create_planning_constraint`，但**没有撤销/rollback 已应用 proposal 的方法**。一旦 `mark_applied` 将修改写入大纲/弧/线索，若后续验证发现错误，只能依赖人工手动修正或重新生成新 proposal。
- **潜在影响**: re-plan 闭环只能前进不能回退，增加“错误规划被固化”的风险；不利于无人值守长跑。
- **修复建议**: 增加 `rollback(proposal_id)` 方法：记录 action 的 `old_value`，按逆序恢复目标对象，并将状态迁移为 `rolled_back`；同时要求 `ReplanAction` 必须保存可回滚的 `old_value_json`。

---

## P2 级问题

### P2-1 `_nodes.py` 职责过度集中

- **文件**: `src/songyan/workflows/_nodes.py`（2695 行）
- **问题**: 单个文件承载规划、写作、审查、修订、质量门、结算等 13+ 个节点，是“上帝文件”。
- **修复建议**: 按生命周期拆分为 `workflows/nodes/{prewrite,audit,revision,confirm,settlement}.py`。

### P2-2 `revision_router` 引用未在 `Phase1State` 中声明的字段

- **文件**: `src/songyan/workflows/phase1_graph.py:156-165`
- **问题**: `revision_router` 读取 `state.get("_mandatory_reference_check_passed")`，但 `Phase1State` 类型定义中无该字段。
- **修复建议**: 在 `Phase1State` 中显式声明 `_mandatory_reference_check_passed: bool | None`。

### P2-3 `human_confirm_router` 将 `None` 决策视为 accept

- **文件**: `src/songyan/workflows/phase1_graph.py:210-227`
- **问题**: `if decision == "accept" or decision is None: return "accept"`。
- **修复建议**: `None` 应路由到 `error` 或重新中断，不应默认为 accept。

### P2-4 `Phase1State` 与实际返回字段不一致

- **文件**: `src/songyan/workflows/phase1_graph.py` 定义 vs. 多处节点返回
- **问题**: 节点返回了 `_degraded_accept`、`_max_revision_rounds`、`thread_id`、`gate_mode`、`human_instructions` 等未声明字段。
- **修复建议**: 全面补全 `Phase1State` 字段，或改为使用 `total=False` 的 `TypedDict`。

### P2-5 async 节点中混入同步 CPU/IO 调用

- **文件**: `_nodes.py` 的 `rule_auditor_node` (1161)、`revision_handler_node` (1779)、`rewrite_node` (805-876)
- **问题**: 直接调用同步函数 `run_rule_audit`、`_enforce_word_count`、`_hard_truncate_at_boundary`、`_parse_scenes`、`_count_chinese_words`。
- **修复建议**: 对明确非 IO 的纯计算函数保留同步并在注释中说明；对任何可能 IO 的函数包装为 async 或 `to_thread`。

### P2-6 `build_phase1_graph` 的 docstring 位置错误

- **文件**: `src/songyan/workflows/phase1_graph.py:245-253`
- **问题**: docstring 写在 `global _compiled_graph` 和缓存返回之后，未紧跟函数签名。
- **修复建议**: 将 docstring 移动到函数体第一行。

### P2-7 `human_gate_node` edit 分支存在无意义调用

- **文件**: `src/songyan/workflows/_nodes.py:2056-2057`
- **问题**: `await ChapterVersionRepository().list_by_chapter(...)` 的结果被直接丢弃。
- **修复建议**: 删除该行，或明确其用途。

### P2-8 `AdaptiveHaltPolicy.min_present_ratio` 未被使用

- **文件**: `src/songyan/evals/adaptive_halt.py`
- **问题**: `min_present_ratio` 字段有默认值 0.6，但 `evaluate_adaptive_halt` 未检查 `present` 占比是否达到该阈值。
- **修复建议**: 在样本充分性检查中加入 `min_present_ratio` 判断，或移除该字段。

### P2-9 `replan_repo.py` 异常处理过于宽泛

- **文件**: `src/songyan/db/replan_repo.py:44-112`, `:227-289`
- **问题**: `except Exception` 会捕获 `KeyboardInterrupt`、`SystemExit` 等不应由仓库吞掉的异常。
- **修复建议**: 收窄为 `(sqlite3.Error, OperationalError, ValueError, SongyanError)`。

### P2-10 `phase1_graph.py` / `phase2_graph.py` 顶层兜底捕获过宽

- **文件**: `phase1_graph.py:432`, `phase2_graph.py:1212`
- **问题**: 顶层 `except Exception` 会吞掉 `SettlementError`、`AutoHaltException` 等应由调用方感知的异常。
- **修复建议**: 收窄异常类型，或显式重新抛出关键业务异常。

---

## 正面发现

- `phase2_graph.py` resume 逻辑以 accepted head 为唯一事实源，跳过已 accept 章节，符合设计。
- `adaptive_halt` / `adaptive_gate` 默认关闭且配置一致，不会自动阻断已有长跑。
- `accept_with_settlement_boundary` 事务设计合理：`apply_settlement`、`accept_version`、`ChapterHeadRepository.update` 绑定到同一 `conn`，异常 rollback、正常 commit。
- `goal_planner.py`、`arc_boundary_resolver.py`、`arc_summary_generator.py` 结构清晰，无越权行为。

---

## 验证结果

```powershell
# 工作流相关测试
python -m pytest tests/test_phase1_graph.py tests/test_phase2_graph.py tests/test_goal_planner.py tests/test_169a_adaptive_halt_decision_engine.py tests/test_168a_adaptive_gate_signal_snapshot.py tests/test_166a_replan_evaluation.py -q
# 98 passed

# ruff
ruff check src/ tests/
# All checks passed
```

---

## 修复优先级

1. **P0-1**: 修复 `rewrite_node` 截断版本创建失败时的内存/DB 不一致问题。
2. **P1-1**: 替换关键路径上的裸 `except Exception`。
3. **P1-2**: `human_gate_node` 编辑器调用改为异步。
4. **P1-3**: 清理 `Phase1State` 业务对象，改为 ID 引用。
5. **P1-4**: 为 re-plan 增加 `rollback(proposal_id)` 能力。
6. **P2**: 拆分 `_nodes.py`、补全 state 字段、修复 docstring 等。
