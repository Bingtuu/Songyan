# Task 111a: 工作流决策契约修复 — DONE

> **完成日期**: 2026-06-18
> **执行人**: AI Agent
> **状态**: 已完成 ✅

---

## 做了什么

Task 111a 修复了 ReviewMerger、ScoreAggregator、LiteraryAuditor、RevisionHandler 与 QualityGate 之间的决策契约不一致问题。核心目标是避免长跑中出现“非 coherence major 被覆盖”“文学诊断阻塞 accept”“无证据 issue 自动修订”“rewrite_scene 走整章级 revision”“修订引入新问题后继续自动修”的路径错位。

### 1. ReviewMerger 与 ScoreAggregator 信号合并

**修改文件**: `src/songyan/workflows/_nodes.py`

- 新增 `combine_revision_signals()`，将 merged 阻断信号与 score flags 合并。
- `score_card.flags` 只能增强判断，不再覆盖 ReviewMerger 的阻断信号。
- 保留 Task 110e 已确认的 coherence 阈值：单个低风险 coherence major 仍由 ScoreAggregator 决定，不被重新升级为自动修订。
- 非 coherence 的 merged major/critical 会继续触发 `_needs_revision=True`。

### 2. LiteraryAuditor 恢复非阻塞

**修改文件**: `src/songyan/workflows/_nodes.py`

- `literary_auditor_node` 不再写 `_needs_revision`。
- critical literary observation 只保存为诊断结果，不再触发 RevisionHandler 或 rewrite。
- 节点捕获 `LLMError` / `LLMResponseParseError`，返回可诊断状态，避免单次文学审查异常直接炸掉整章流程。

### 3. RevisionHandler 只做 patch

**修改文件**: `src/songyan/agents/revision_handler/__init__.py`

- 新增公开 helper `filter_patchable_issues()`。
- 自动修订只处理 `severity in ("critical", "major")`、`fix_type="patch"` 且 `evidence_quote` 非空的 issue。
- `rewrite_scene` 不进入 patch 链路。
- 移除 `run_revision()` 中 scene split / scene merge 的整章级 LLM 改写路径，避免 RevisionHandler 越界做 rewrite。
- 保留 `_difflib_fuzzy_search` / `_find_text_span` 等内部 helper 的显式 re-export，兼容既有测试。

### 4. LLMAuditor 强制证据要求

**修改文件**: `src/songyan/agents/llm_auditor.py`, `src/songyan/models/review.py`

- `_build_issue()` 过滤无 `evidence_quote` 的 critical/major issue。
- `MergedReviewReport.patchable_issues` 二次过滤空证据 issue。
- 无证据 issue 不进入自动修订。

### 5. 修订引入新问题后停止自动修订

**修改文件**: `src/songyan/workflows/_nodes.py`

- `quality_gate_node` 检测到 `_new_issues_introduced` 非空时，不再回到 `rule_auditing`。
- 路由转为 `human_confirm`，并标记 `_convergence_failed=True`、`_skip_settlement=True`，避免自动链路继续放大污染。

---

## 改了哪些文件

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `src/songyan/workflows/_nodes.py` | 修改 | 合并 revision 信号；Literary 非阻塞；auditor 异常韧性；新问题停止自动修订 |
| `src/songyan/agents/revision_handler/__init__.py` | 修改 | patchable issue 过滤；移除 scene split/merge 自动整章改写 |
| `src/songyan/agents/llm_auditor.py` | 修改 | critical/major issue 强制 evidence_quote |
| `src/songyan/models/review.py` | 修改 | `patchable_issues` 二次过滤空证据 |
| `tests/test_108_core_nodes.py` | 修改 | 覆盖 merged/score 信号合并与 Literary 非阻塞 |
| `tests/test_100b_quality_gate.py` | 修改 | 覆盖新问题引入后停止自动修订 |
| `tests/test_revision_handler.py` | 修改 | 覆盖无证据过滤与 rewrite_scene 不自动改写 |
| `tests/test_llm_auditor.py` | 修改 | 覆盖无证据 critical/major 过滤 |
| `tests/test_error_stage.py` | 修改 | 覆盖 auditor LLM 异常返回诊断状态 |
| `docs/STATUS.md` | 修改 | 更新当前任务与验证结果 |
| `tasks/111a-workflow-decision-contract-fix-DONE.md` | 新增 | 本交付记录 |

---

## 验证结果

### 单元/回归测试

```bash
pytest tests/ -v
```

**结果**: **1628 passed**, 4 skipped, 2 xfailed, 3 xpassed, 10 warnings

```bash
pytest tests/ -q
```

**结果**: **1628 passed**, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings

### 聚焦回归

```bash
pytest tests/test_108_core_nodes.py tests/test_100b_quality_gate.py tests/test_revision_handler.py tests/test_llm_auditor.py tests/test_phase1_graph.py tests/test_error_stage.py -q
```

**结果**: **178 passed**

```bash
pytest tests/integration/test_paths.py -q
```

**结果**: **9 passed**

```bash
pytest tests/test_106_scoring_system.py -q
```

**结果**: **32 passed**

### Lint

```bash
ruff check src/songyan/workflows/_nodes.py src/songyan/agents/revision_handler/__init__.py src/songyan/agents/llm_auditor.py src/songyan/models/review.py tests/test_108_core_nodes.py tests/test_100b_quality_gate.py tests/test_revision_handler.py tests/test_llm_auditor.py tests/test_error_stage.py
```

**结果**: All checks passed.

```bash
ruff check src/ tests/ --statistics
```

**结果**: 仍有 **156 个历史 lint 问题**（主要为 E501/F401/F821/E402/F841），本 Task 未引入修改文件级 lint 错误。

---

## 关键兼容性说明

Task 111a 没有回滚 Task 110e 的 coherence_major 阈值策略。实现上区分了两类 major：

- coherence major：继续由 `ScoreAggregator` 的 110e 阈值决定，单个低风险 major 不触发自动修订。
- 非 coherence major：由 ReviewMerger 作为独立阻断信号保留，避免被 score clean 覆盖。

这保证了 `tests/integration/test_paths.py::test_path_g_major_revision_accept` 仍然通过，同时修复了非 coherence major 被覆盖的问题。

---

## 已知限制

1. 全量 ruff 仍有历史 lint 债务，未在本 Task 中清理，避免扩大变更面。
2. `rewrite_scene` 当前不会自动进入 RevisionHandler；后续若需要整章重写，应由 rewrite/human gate 语义承接，而不是 patch 链路。
3. auditor 异常现在返回诊断状态，但更细的自动降级策略可留给后续工作流韧性任务。

---

## 下一 Task

**Task 111b: Settlement 与事实源一致性修复**

- 修复 validation failed settlement 禁止落库
- 修复 accept / settlement / summary 的事实源一致性边界
- 清理 LangGraph state 中完整业务对象残留
