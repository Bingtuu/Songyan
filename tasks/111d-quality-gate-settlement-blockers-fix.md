# Task 111d: QualityGate 与 Settlement 阻断项修复

> **Phase**: V5.0 Phase 4 前置修复 — Post-111 P0/P1 Correctness
> **优先级**: P0
> **依赖**: Task 111c 完成；post-111 review 完成
> **预计工作量**: 0.5-1 天

---

## Goal

修复 post-111 review 确认的两个 Critical 阻断项和一个 accepted-summary 完整性问题，确保 Task 112 长跑不会把预算超限、修订引入新问题或 summary 缺失误判为成功章节。

## Context

post-111 review 确认以下问题会直接污染 Task 112 结果：

1. `review_merger_node` / `ScoreAggregator` 仍从 `state["context_package"]` 读取 `budget_used`；Task 111b 后 state 不再保存完整 `ContextPackage`，真实运行会得到 `budget_used=None` 并被当成 `0.0`，导致预算超限漏判。
2. `_new_issues_introduced` 非空时，QualityGate 设置 `_skip_settlement=True`；auto-confirm 接受后，`settlement_extractor_node` 会跳过 settlement 但仍 accepted，产生 accepted 章节无 settlement 的事实源污染。
3. SummaryWriter 失败时只 warning，`summary_id=None` 仍返回 `status="done"`；accepted 章节可能没有真实 summary 或 fallback summary。

## In Scope（必须完成）

- [ ] **修复预算评分输入**
  - `review_merger_node` 优先读取 `state["_context_metrics"]["budget_used"]`
  - 仅兼容测试或旧路径时 fallback 到 `state["context_package"].budget_used`
  - `context_emergency` / `_budget_was_enforced` 如已存在，应进入 score metadata 或至少进入 run metrics

- [ ] **修复 new issues 终态**
  - `_new_issues_introduced` 非空不得静默进入 `_skip_settlement` 成功路径
  - auto-confirm 不得把 “修订引入新问题” 章节标记为 accepted + missing settlement
  - 该路径应进入 human/convergence/failure 状态，或人工明确确认后执行正常 settlement

- [ ] **修复 summary 完整性**
  - settlement 成功后 SummaryWriter 失败必须写 fallback summary
  - fallback summary 也失败时，不得返回 `status="done"`
  - accepted 章节必须满足：真实 summary 或 fallback summary 二选一存在

## Out of Scope（明确不做）

- 不重构 ContextPackage snapshot 架构，该项进入 Task 111f
- 不扩展 DG-2 报告指标，该项进入 Task 111e
- 不做长跑性能优化，该项进入 Task 111g
- 不调整评分阈值、coherence major 规则或 Writer prompt 风格

## 关键实现边界

### Budget 输入契约

```python
context_metrics = state.get("_context_metrics") or {}
budget_used = context_metrics.get("budget_used")
if budget_used is None:
    ctx_pkg = state.get("context_package")
    budget_used = getattr(ctx_pkg, "budget_used", None)
```

### New Issues 终态契约

```python
if state.get("_new_issues_introduced"):
    return {
        "status": "human_review_required",
        "_skip_settlement": False,
        "_settlement_needs_human_review": True,
    }
```

实际字段名可沿用现有 router，但必须满足：不能 accepted、不能 settlement_id 伪成功、不能 summary 伪成功。

### Summary fallback 契约

settlement 成功后：

1. 优先调用 `write_chapter_summary()`
2. 失败后写 `_generate_fallback_summary()`
3. 若 fallback 写入也失败，返回失败/复核状态

## 关键测试标准

### Layer 1: 单元测试

- [ ] `review_merger_node` 在没有 `context_package`、但 `_context_metrics.budget_used=1.1` 时，生成的 `score_card.flags.budget_ok is False`
- [ ] `review_merger_node` 在 `_context_metrics.budget_used=0.8` 时，预算维度正常通过
- [ ] `_new_issues_introduced` 非空时不会设置 `_skip_settlement=True` 的成功路径
- [ ] `_new_issues_introduced` 非空 + auto-confirm 时，不调用 `accept_with_settlement_boundary(settlement=None)`
- [ ] SummaryWriter 抛出 `LLMError` / `LLMResponseParseError` 后会写 fallback summary 并返回真实 `summary_id`
- [ ] SummaryWriter 与 fallback 都失败时，节点不返回 `status="done"`

### Layer 2: 集成测试

- [ ] 一条模拟 Phase1 auto-confirm 路径中，预算超限会导致 QG 失败或进入修订/复核，而不是 accepted
- [ ] 修订引入新问题路径不会产生 accepted chapter head
- [ ] accepted 章节在 DB 中同时具备 `accepted_version_id`、settlement side effects、summary row

### Layer 3: 回归测试

- [ ] `pytest tests/test_phase1_graph.py tests/test_107_convergence_guardrail.py tests/test_108_core_nodes.py -q`
- [ ] `pytest tests/integration/test_paths.py -q`
- [ ] `pytest tests/ -q`
- [ ] 本次触及文件 `ruff check` 通过；全量历史 lint 可继续标注为既有问题

## 验收标准（Acceptance Criteria）

- [ ] budget QG 不再依赖 `state["context_package"]`
- [ ] `_new_issues_introduced` 不会产出 accepted + missing settlement
- [ ] accepted 章节 100% 有真实 summary 或 fallback summary
- [ ] invalid / skipped / review-required settlement 状态不会被误报为 `done`
- [ ] 生成 `tasks/111d-quality-gate-settlement-blockers-fix-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] Git commit 包含代码、测试、DONE 文档和状态更新

## 参考证据

- `src/songyan/workflows/_nodes.py` — `review_merger_node`、`quality_gate_node`、`settlement_extractor_node`
- `src/songyan/evals/score_aggregator.py` — budget score
- `.trae/specs/review-post111-logic-workflow-performance/` — post-111 review spec

## 下一 Task

**Task 111e: Task 112 报告与 DG-2 Gate 完整性修复**
