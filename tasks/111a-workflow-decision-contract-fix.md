# Task 111a: 工作流决策契约修复

> **Phase**: V5.0 Phase 4 前置修复 — Agent/Workflow 一致性
> **优先级**: P0
> **依赖**: Task 110e 完成；整体 review `review-agent-workflow-consistency`
> **预计工作量**: 1-2 天

---

## Goal

修复 Task 112 前置 review 暴露的工作流决策契约问题，确保审查、评分、文学诊断、修订、重写之间的路由语义一致，避免 Ch101-Ch150 长跑前出现“该修不修、该停不停、该人工却自动修”的系统性错位。

## Context

Task 110e 解决了 `coherence_major` 误判，使 Ch80-Ch96 达到 QG 100%。但随后的整体 review 发现，当前工作流仍存在更底层的契约风险：

1. `review_merger_node` 先读取 merged critical/major，再被 `ScoreAggregator` 的 coherence flags 覆盖，非 coherence 的 critical/major 可能绕过修订。
2. `literary_auditor_node` 会写 `_needs_revision`，既违反 LiteraryAuditor “只诊断、不阻塞”的边界，也可能覆盖 ReviewMerger 已判定的修订需求。
3. `rewrite_scene` issue 仍会进入 RevisionHandler 自动修复，实际执行整章级 LLM 改写，违反 “RevisionHandler 只做 patch” 和 “rewrite_scene 不自动修复”。
4. LLMAuditor critical/major issue 未强制 `evidence_quote`，无证据 issue 可能进入自动修订。
5. 修订引入新问题后，QualityGate 仍可能继续自动修订，而不是停止并交给人工。

这些问题不一定在 Task 110e 短样本中触发，但会放大 Task 112 长跑的不确定性。

## In Scope（必须完成）

- [ ] **修复 ReviewMerger 与 ScoreAggregator 的阻断信号合并**
  - 保留 `merged.has_critical / merged.has_major` 作为独立阻断信号
  - `score_card.flags` 只能增强判断，不能覆盖 merged issue 口径
  - 最终 `_has_critical`、`_has_major`、`_needs_revision` 必须能表达所有 critical/major 来源

- [ ] **恢复 LiteraryAuditor 非阻塞语义**
  - `literary_auditor_node` 不再写 `_needs_revision`
  - Literary observation 只作为诊断、报告和后续人工参考
  - 不再触发 RevisionHandler 或 rewrite

- [ ] **阻断 `rewrite_scene` 自动进入 RevisionHandler**
  - `rewrite_scene` 类型 issue 不进入 `patchable_issues`
  - 若 scene structure 问题需要整章重写，应路由到 rewrite 或 human gate
  - RevisionHandler 不再调用整章级 scene split / merge LLM 路径

- [ ] **强制 LLMAuditor critical/major 证据要求**
  - critical/major issue 必须有非空 `evidence_quote`
  - 无证据 critical/major 应降级、丢弃或标记为 `needs_human_review`
  - RevisionHandler 二次过滤无证据 issue

- [ ] **修复“修订引入新问题”后的路由**
  - `_new_issues_introduced` 非空时停止自动修订
  - 路由到 human gate 或 convergence failure，而不是继续下一轮 revision

- [ ] **补齐 auditor 节点错误韧性**
  - `llm_auditor_node`、`literary_auditor_node` 捕获 `LLMError` / `LLMResponseParseError`
  - 返回可诊断状态，不让单次审查 LLM 异常直接炸掉整章流程

## Out of Scope（明确不做）

- 不调整 Task 110e 已确认的 `coherence_major` 阈值策略
- 不重写 Writer prompt
- 不新增 Agent 或 LangGraph 节点
- 不做 Ch101-Ch150 长跑验证（顺延到 Task 112）

## 接口契约

```python
def combine_revision_signals(
    *,
    merged_has_critical: bool,
    merged_has_major: bool,
    score_needs_revision: bool,
) -> tuple[bool, bool, bool]:
    """合并审查与评分阻断信号，返回 has_critical/has_major/needs_revision."""
    ...
```

```python
def filter_patchable_issues(report: MergedReviewReport) -> list[ReviewIssue]:
    """仅返回有证据、fix_type=patch、允许自动修复的 critical/major issue."""
    ...
```

## 数据模型

不新增长期数据模型。可按需新增轻量 helper 或 TypedDict，但不得改变 SQLite schema。

## 测试要求

### Layer 1: 单元测试
- [ ] `ScoreAggregator` 低风险 coherence 不能覆盖 merged critical/major
- [ ] Literary critical observation 不设置 `_needs_revision`
- [ ] 无 `evidence_quote` 的 critical/major 不进入 patchable issues
- [ ] `rewrite_scene` 不进入 RevisionHandler patch 链路

### Layer 2: 工作流节点测试
- [ ] `review_merger_node` 在 merged major + score clean 时仍 `needs_revision=True`
- [ ] `literary_auditor_node` 不改变已有 `_needs_revision`
- [ ] `_new_issues_introduced` 非空时路由到 human/convergence，而非继续 revision
- [ ] LLM auditor / literary auditor 抛解析错误时返回可诊断状态

### Layer 3: 回归测试
- [ ] 覆盖 Task 107/110e 相关测试，确保已有 coherence 修复不回退

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/ -v` 全部通过
- [ ] `pytest tests/ -q` 全量回归无新增失败
- [ ] `ruff check src/ tests/` 无新增 lint 错误
- [ ] 不违反 AGENTS.md P0 #9、#12、#18、#20、#22、#23
- [ ] 生成 `tasks/111a-workflow-decision-contract-fix-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] Git commit 包含代码、测试、DONE 文档和状态更新

## 参考文档

- `AGENTS.md` — P0 Agent 职责边界与审查修订规则
- `.trae/specs/review-agent-workflow-consistency/spec.md` — 整体 review 规格
- `tasks/110e-coherence-major-fix-DONE.md` — 最新评分阈值修复结果

## 下一 Task

**Task 111b: Settlement 与事实源一致性修复**
