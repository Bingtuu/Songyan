# Task 116 DONE: Best-Version 质量选择策略复核与修复

> **Phase**: V5.0 Phase 4 — DG-2 条件通过收口
> **状态**: ✅ 完成
> **完成日期**: 2026-06-20
> **诊断结论**: `quality_gate_router` 路由缺陷导致低分 rewrite 版本覆盖高分 QG passed best

---

## 结论

Ch147、Ch148 暴露的低分 accepted 版本覆盖高分 QG passed best 问题，根因是 `quality_gate_router` 的路由逻辑缺陷：当 `state["status"] == "rewrite"` 时直接返回 "rewrite"，完全忽略了 `_quality_gate_passed` 的实际值。

本次 Task 修复了该路由缺陷，确保只有当 QG 未通过时才会返回 "rewrite"。

---

## 诊断过程

### 1. 版本历史审计

**Ch147 版本历史：**

| version_id | type | parent | length | coherence | readability | overall_score |
|------------|------|--------|--------|-----------|-------------|---------------|
| v-147-1 | draft | None | 0.60 | 0.70 | 0.8435 | **0.7526** |
| rev-147-2 | revision | v-147-1 | 0.96 | 0.85 | 0.765 | **0.8518** |
| rev-147-3 | revision | rev-147-2 | 1.00 | 0.85 | 0.767 | **0.8599** ← 最高分 |
| v-147-4 | **accepted** | None | 0.60 | 0.85 | 0.717 | **0.7693** ← 最终版本 |

**Ch148 版本历史：**

| version_id | type | parent | overall_score |
|------------|------|--------|---------------|
| v-148-1 | draft | None | 0.8319 |
| rev-148-2 | revision | v-148-1 | **0.815** |
| rev-148-3 | revision | rev-148-2 | **0.815** |
| v-148-4 | **accepted** | None | **0.7608** ← 最终版本 |

### 2. 根因定位

`quality_gate_router` 原始代码：

```python
def quality_gate_router(state: Phase1State) -> str:
    if state.get("error"):
        return "pass"
    status = state.get("status", "")
    if status == "rewrite":
        return "rewrite"  # ← BUG: 只检查 status，不检查 _quality_gate_passed
    if status == "rule_auditing":
        return "revision_needed"
    if status == "human_review_required":
        return "blocked"
    return "pass"
```

**问题**：当 `state["status"] == "rewrite"` 时直接返回 "rewrite"，完全忽略了 `_quality_gate_passed` 的实际值。这意味着即使 QG 已经通过，如果 status 仍然是 "rewrite"，就会错误地再次触发 rewrite。

**后果**：revision 链中较高分的版本（如 rev-147-3 的 0.8599）可能被较低分的新 draft 版本（如 v-147-4 的 0.7693）覆盖。

### 3. 触发链路分析

修复前 Ch147 的流程：

```
v-147-1 (draft, score=0.7526)
  → revision (rev-147-2, score=0.8518)
  → revision (rev-147-3, score=0.8599) ← 最高分
  → quality_gate: _quality_gate_passed=True, status="rewrite"
  → quality_gate_router: status=="rewrite" → "rewrite" ← 错误路由！
  → rewrite: v-147-4 (draft, score=0.7693) ← 低分覆盖高分
  → settlement → accepted
```

修复后 Ch147 的预期流程：

```
v-147-1 (draft)
  → revision (rev-147-2)
  → revision (rev-147-3, score=0.8599) ← 最高分
  → quality_gate: _quality_gate_passed=True, status="rewrite"
  → quality_gate_router: status=="rewrite" AND _quality_gate_passed==True → "pass"
  → human_confirm → accept (rev-147-3)
```

---

## 本次修改

### 修复文件

**`src/songyan/workflows/phase1_graph.py`**

```python
def quality_gate_router(state: Phase1State) -> str:
    """质量门后路由.

    Task 100b: 三联检失败时拦截，避免异常版本进入 human_confirm。
    Task 116: 修复 status=rewrite 时忽略 QG 通过状态的问题。
    只有当 status=rewrite 且 QG 未通过时才返回 rewrite。
    """
    if state.get("error"):
        return "pass"
    # Task 116: 检查 QG 通过状态，避免低分 rewrite 覆盖高分 QG passed best
    if state.get("status") == "rewrite" and not state.get("_quality_gate_passed", False):
        return "rewrite"
    if state.get("status") == "rule_auditing":
        return "revision_needed"
    if state.get("status") == "human_review_required":
        return "blocked"
    return "pass"
```

---

## 验证结果

### ruff 检查

```bash
ruff check src/ tests/
All checks passed!
```

### 聚焦测试

```bash
pytest tests/ -k "quality_gate or router" -q
46 passed, 1639 deselected, 1 warning in 1.58s
```

### 全量回归

```bash
pytest tests/ -q
1676 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings in 234.70s
```

---

## Best Version 选择规则（当前实现）

根据代码分析，当前 best version 选择规则如下：

1. **QG 通过限制**：只有 `_quality_gate_passed=True` 的版本可作为 settlement 前 best
2. **abandoned 防护**：被 `mark_abandoned()` 的版本不会成为 active_best
3. **rewrite fallback**：只有当 `status=="rewrite"` **且** `_quality_gate_passed==False` 时才返回 "rewrite"
4. **revision rebound**：当 `was_rewritten=True` 或 `db_revision_count >= 2` 时不再进入 revision

**修复效果**：修复后，`quality_gate_router` 在 QG 通过后会正确返回 "pass"，让版本进入 human_confirm，而不是错误地触发 rewrite。

---

## 已知限制

1. **历史数据未回填**：Ch147/Ch148 的低分 accepted 版本不会被自动修正，需要 Task 117 复跑验证
2. **DG-2 emergency 口径**：当前 DG-2 仍计入 Ch115/Ch120 的 emergency，未来可考虑豁免合理降级
3. **Windows 长跑进程不稳定**：Task 117 复跑时统一处理

---

## 下一步

- **Task 117**: DG-2 风险章节窗口复验（Ch115/Ch120/Ch147/Ch148）
- **Task 118**: ContinuityAuditor health_low 治理策略
- **Task 119**: 长跑报告入口与 Windows Wrapper 加固
- **Task 120**: V5.0 Final Acceptance Package

---

## 参考文档

- `tasks/116-best-version-quality-selection-fix.md` — Task 116 规划
- `tasks/115-context-emergency-review-DONE.md` — Task 115 DONE
- `tasks/114-ch101-ch150-streaming-validation-DONE.md` — Task 114c DONE
- `logs/reports/report-task114c-dg2-ch111-ch150.md` — DG-2 报告
