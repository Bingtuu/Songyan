# Task 111b DONE: Settlement 与事实源一致性修复

> **完成日期**: 2026-06-19
> **状态**: ✅ 已完成
> **提交范围**: accept / settlement / summary / LangGraph state / HumanGate inject 契约

---

## 完成内容

1. **阻止 invalid settlement 落库**
   - `apply_settlement()` 增加 `validation_status != "valid"` 硬拦截。
   - `settlement_extractor_node()` 在 validation failed 时不调用 apply，不生成 settlement_id，不标记 accepted。
   - state 返回 `_settlement_needs_human_review=True`，状态为 `settlement_review`。

2. **修复 accept 与 settlement 一致性边界**
   - 新增 `accept_with_settlement_boundary()`，在单个事务内完成：
     - `apply_settlement()`
     - `ChapterVersionRepository.accept_version()`
     - `ChapterHeadRepository.update(... accepted ...)`
   - HumanGate accept 不再提前写 `chapter_heads.accepted_version_id` 或 `version_type='accepted'`。
   - settlement 抽取失败、验证失败或应用失败时不会留下 accepted + missing settlement 的半提交状态。

3. **返回真实 summary_id**
   - `write_chapter_summary()` 改为返回 `(summary_id, ChapterSummary)`。
   - `settlement_extractor_node()` 使用真实落库 summary_id，不再额外生成假 id。
   - `SummaryRepository` 增加 `get()`，并支持外部事务连接写入。

4. **清理 LangGraph state 中的完整 ContextPackage**
   - `context_manager_node()` 不再返回完整 `context_package`。
   - state 仅保留 `_context_metrics`、`_budget_was_enforced` 等轻量控制指标。
   - writer / auditor 下游通过 `_get_context_package()` 按需重新组装上下文。

5. **修复 HumanGate inject 路由契约**
   - 从 HumanGate interrupt options 中移除未接入路由的 `inject`。
   - 保留未知 decision 的错误分支，避免用户可选但 workflow unknown 的状态。

---

## 修改文件

- `src/songyan/workflows/_nodes.py`
- `src/songyan/workflows/phase1_graph.py`
- `src/songyan/agents/settlement_extractor/_apply.py`
- `src/songyan/agents/summary_writer.py`
- `src/songyan/db/repository.py`
- `src/songyan/db/context_repo.py`
- `tests/test_settlement_extractor.py`
- `tests/test_phase1_graph.py`
- `tests/test_error_stage.py`
- `tests/test_summary_writer.py`
- `tests/test_108_core_nodes.py`
- `tests/test_eval_runner.py`
- `tests/integration/conftest.py`
- `tests/integration/test_multi_chapter.py`
- `tests/integration/test_ch41_50_validation.py`
- `docs/STATUS.md`

---

## 验证结果

```bash
pytest tests/ -v
```

结果：`1632 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
pytest tests/ -q
```

结果：`1632 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
ruff check src/songyan/workflows/_nodes.py src/songyan/workflows/phase1_graph.py src/songyan/db/repository.py src/songyan/db/context_repo.py src/songyan/agents/summary_writer.py src/songyan/agents/settlement_extractor/_apply.py tests/test_settlement_extractor.py tests/test_summary_writer.py tests/test_phase1_graph.py tests/test_error_stage.py tests/integration/conftest.py tests/integration/test_multi_chapter.py tests/integration/test_ch41_50_validation.py tests/test_108_core_nodes.py tests/test_eval_runner.py
```

结果：`All checks passed!`

```bash
ruff check src/ tests/ --statistics
```

结果：仍有历史 lint `133 errors`，主要为未触及测试文件的 E501/F401/E402/F841/F821 等；本 Task 触及文件已通过 ruff。

---

## 已知限制

- `ContextPackage` 不再进入 LangGraph state 后，writer / LLM auditor / literary auditor 会按需重新组装上下文；这是对 P0 state 规则的取舍，后续 Task 111c 可继续优化 prompt/context 一致性。
- skip-settlement 路径仍保留 fallback summary 和 accept 边界，用于 Task 107 convergence exhausted 的既有成功路径。
- 全量 ruff 历史错误未在本 Task 清理，避免扩大修复范围。

---

## 下一步

进入 **Task 111c: Context 与 Prompt 一致性修复**。
