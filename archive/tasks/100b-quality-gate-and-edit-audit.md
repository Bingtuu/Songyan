# Task 100b: 流程质量门 + 人工 edit 审计修复

> **Phase**: V4.0 Phase B — 修复收尾
> **优先级**: P0
> **依赖**: Task 100a
> **预计工作量**: 中

---

## Goal

在 accept 前增加综合质量门节点，拦截字数异常、内容保留率过低、revision 引入新问题的章节；修复人工 edit 分支绕过 Audit 的 Critical 盲区。

## Context

Task 099 深度复盘暴露两个流程级盲区：

1. **质量门缺失**：当前 `revision_router` 仅基于 `_needs_revision`（是否有 critical/major issue）和 `revision_round` 做决策。rewrite 后无论字数、保留率、新问题如何都强制 pass（`was_rewritten → return "pass"`）。Ch46 的 rewrite 后仍超标 1.336x，但系统不拦截。

2. **人工 edit 绕过 Audit**：`human_gate_node` 的 `edit` 分支直接写死 `status="accepted"` 并创建 `edited` 版本，**不经过 RuleAuditor + LLMAuditor**。人工编辑可能引入新问题（如字数超标、AI 腔、设定矛盾），但系统不做任何检测。

## In Scope（必须完成）

- [ ] 新增 `quality_gate_node` 工作流节点，在 `human_confirm` 之前执行（或在 `human_confirm` 内部作为自动检查）
- [ ] 质量门检查项（三联检）：
  - **字数检查**：当前版本字数是否在 [0.80x, 1.30x] 范围内
  - **保留率检查**：若来自 revision，`_content_preservation_ratio` 是否 ≥ 0.70
  - **新问题检查**：`_new_issues_introduced` 是否为空
- [ ] 质量门失败策略：
  - 字数 > 1.30x：路由到 `rewrite`
  - 字数 < 0.80x 或保留率 < 0.70 或新问题非空：标记 `_needs_revision=True`，路由到 `revision_handler`
- [ ] 修复 `human_gate_node` 的 `edit` 分支：edit 后不再直接 accepted，而是创建 `edited` 版本后路由到 `rule_auditing`（重新走 Audit 流程）
- [ ] 更新 `phase1_graph.py` 的状态机和路由函数
- [ ] 运行 5 章端到端验证（含 edit 场景测试）

## Out of Scope（明确不做）

- 不修改 Audit 本身的检测逻辑（RuleAuditor/LLMAuditor 保持不变）
- 不新增 LiteraryAuditor 的阻塞能力
- 不修改 SettlementExtractor 逻辑

## 接口契约

```python
# _nodes.py
async def quality_gate_node(state: dict[str, Any]) -> dict[str, Any]:
    """综合质量门 — accept 前的最后一道自动检查.
    
    Returns:
        状态更新字典，可能包含:
        - _quality_gate_passed: bool
        - _quality_gate_failures: list[str]
        - human_decision: "word_count_guard" | "revision_needed" | None
        - status: "rewrite" | "rule_auditing" | "human_confirm"
    """
    ...

# phase1_graph.py
# 新增边: literary_auditor → quality_gate → human_confirm
# 或在 human_confirm 内部集成
```

## 数据模型

无新增模型，使用现有 state 字段：

```python
# Phase1State 可能新增（可选，视实现而定）
_quality_gate_passed: bool | None
_quality_gate_failures: list[str]
```

## 测试要求

### Layer 1: 单元测试
- [ ] 字数 1.40x → 预期路由到 rewrite
- [ ] 字数 0.70x → 预期标记 revision_needed
- [ ] 保留率 0.60 + 新问题非空 → 预期标记 revision_needed
- [ ] 全部通过 → 预期进入 human_confirm

### Layer 2: 集成测试
- [ ] `edit` 分支后版本重新进入 rule_auditor → llm_auditor → review_merger 流程

### Layer 3: 5 章验证
- [ ] 5 章端到端，验证 edit 后重新审计生效

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_phase1_graph.py -v` 全部通过（新增质量门路由测试）
- [ ] 5 章端到端验证：
  - edit 分支后自动重跑 Audit，无 accepted 版本绕过审查
  - 超标/不足版本在 human_confirm 前被拦截
- [ ] ruff 检查无新增错误
- [ ] 生成 `tasks/100b-quality-gate-and-edit-audit-DONE.md` 交接文件

## 参考文档

- `src/songyan/workflows/_nodes.py` — human_gate_node 实现
- `src/songyan/workflows/phase1_graph.py` — 状态机编排
- `tasks/099-ch71-ch100-extension-DONE.md` — Ch46 rewrite 后仍超标、Ch39 灰色区间分析
