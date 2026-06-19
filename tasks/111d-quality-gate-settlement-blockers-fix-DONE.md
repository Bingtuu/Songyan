# Task 111d DONE: QualityGate 与 Settlement 阻断项修复

> **完成日期**: 2026-06-19
> **状态**: ✅ 已完成
> **提交范围**: QualityGate budget 输入 / new issues 终态 / Summary fallback

---

## 完成内容

1. **修复预算评分输入**
   - `review_merger_node()` 不再依赖 `state["context_package"]` 读取 `budget_used`。
   - 新增 `_budget_used_for_scoring()`，优先从 `state["_context_metrics"]["budget_used"]` 读取预算指标。
   - 保留旧测试兼容路径：只有 `_context_metrics.budget_used` 缺失时才 fallback 到 `context_package.budget_used`。

2. **修复 `_new_issues_introduced` 终态**
   - QualityGate 检测到修订引入新问题时返回 `status="human_review_required"`。
   - 该状态通过 `quality_gate_router()` 路由到 END，不再进入 `human_confirm` / auto-confirm。
   - 该路径设置 `_skip_settlement=False` 与 `_settlement_needs_human_review=True`，避免 accepted + missing settlement。

3. **修复 skipped settlement 伪成功**
   - `settlement_extractor_node()` 收到 `_skip_settlement=True` 时不再 accept，不再写 fallback summary，不再返回 `done`。
   - skipped settlement 现在返回 `status="settlement_review"`，并标记 `_settlement_needs_human_review=True`。

4. **修复 SummaryWriter 完整性**
   - Settlement 成功后，`write_chapter_summary()` 抛出 `LLMError` / `LLMResponseParseError` 时会写入代码生成的 fallback summary。
   - fallback summary 返回真实 `summary_id`。
   - 如果 fallback 写入也失败，节点返回 `settlement_review`，不再把缺 summary 的 accepted 章节误报为 `done`。

5. **补充防回归测试**
   - 覆盖 `_context_metrics.budget_used=1.1` 时 `budget_ok=False`。
   - 覆盖 `_context_metrics.budget_used=0.8` 时 `budget_ok=True`。
   - 覆盖 new issues 进入 `human_review_required`，且不设置 `_skip_settlement=True`。
   - 覆盖 skip settlement 不调用 accept 边界、不写 summary、不返回 done。
   - 覆盖 SummaryWriter 失败后 fallback summary 成功与 fallback 失败两条路径。

---

## 修改文件

- `src/songyan/workflows/_nodes.py`
- `src/songyan/workflows/phase1_graph.py`
- `tests/test_100b_quality_gate.py`
- `tests/test_108_core_nodes.py`
- `tests/test_phase1_graph.py`
- `docs/STATUS.md`
- `README.md`
- `docs/INDEX.md`
- `tasks/111d-quality-gate-settlement-blockers-fix.md`
- `tasks/111e-task112-reporting-dg2-gate-fix.md`
- `tasks/111f-context-snapshot-prompt-metadata-fix.md`
- `tasks/111g-long-run-performance-containment.md`
- `tasks/112-ch101-ch150-streaming-validation.md`

---

## 验证结果

```bash
ruff check src/songyan/workflows/_nodes.py src/songyan/workflows/phase1_graph.py tests/test_100b_quality_gate.py tests/test_108_core_nodes.py tests/test_phase1_graph.py
```

结果：`All checks passed!`

```bash
pytest tests/test_phase1_graph.py tests/test_100b_quality_gate.py tests/test_108_core_nodes.py tests/test_107_convergence_guardrail.py -q
```

结果：`71 passed`

```bash
pytest tests/integration/test_paths.py -q
```

结果：`9 passed, 1 warning`

```bash
pytest tests/ -v
```

结果：`1640 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
pytest tests/ -q
```

结果：`1640 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
ruff check src/ tests/
```

结果：失败，仍为历史 lint 存量 `130 errors`，主要集中在未触及测试文件的 E501/F841；本 Task touched files 的 ruff 已通过。

---

## 已知限制

- `_skip_settlement=True` 现在统一进入 `settlement_review`，不再作为成功 accepted 路径；这会让修复耗尽章节在 Task 112 报告中显式暴露为未完成/需复核，而不是伪成功。
- 全量 ruff 仍有历史存量，未在 111d 中清理；后续任务继续保持 touched-file clean。
- Task 111d 不包含 DG-2 报告扩展、Context Snapshot 架构或长跑性能优化，这些分别进入 111e、111f、111g。

---

## 下一步

进入 **Task 111e: Task 112 报告与 DG-2 Gate 完整性修复**。
