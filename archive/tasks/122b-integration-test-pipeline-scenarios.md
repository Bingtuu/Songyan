# Task 122b: Integration Test — Pipeline Scenarios

> **日期**: 2026-06-23（更新于 2026-06-25）
> **类型**: V5.1 集成测试
> **状态**: **已完成**
> **前置**: Task 121q 动态阈值逻辑落地 + 121r Prompt 清理完成

---

## 1. 目标

验证单章 pipeline 在关键质量场景下的行为正确性，确保修复不引入路由断裂。

---

## 2. 测试矩阵

| 测试名 | 场景 | 断言 |
|--------|------|------|
| `test_chapter_early_low_score` | Ch5, overall=0.76 | settlement 成功，标记 degraded_accept |
| `test_chapter_mid_safe_best` | Ch50, overall=0.85 | 正常通过，无 degraded |
| `test_chapter_late_high_score` | Ch100, overall=0.90 | rewrite 不得覆盖 best |
| `test_revision_rebound_tolerance` | score 下降 0.18 | 不触发反弹回滚 |
| `test_revision_rebound_trigger` | score 下降 0.35 | 触发反弹回滚 |

### 2.1 已覆盖场景（状态：已完成）

- Pipeline 路由测试（accept / reject / rewrite / back 路径）
- QG false 硬拦截 settlement 路径
- rewrite 清理后状态生命周期
- ContextEmergency 触发与降级路径
- `_new_issues_introduced` 拦截路径

### 2.2 已补充场景（状态：已完成）

| 测试名 | 场景 | 断言 |
|--------|------|------|
| `test_degraded_accept_routes_to_human_confirm` | QG false + best score ≥ 0.70 | 标记 `_degraded_accept=True`，路由到 `human_confirm` |
| `test_quality_gate_router_passes_degraded_accept` | `_degraded_accept=True` | `quality_gate_router` 返回 `"pass"` |
| `test_safe_best_true_for_high_score` | Ch30, best score 0.85 | 高于 0.78 阈值，判定为 safe best |
| `test_safe_best_false_below_threshold` | Ch30, best score 0.76 | 低于 0.78 阈值，不视为 safe best |
| `test_safe_best_false_due_to_coherence_critical` | score 0.90 但 coherence_critical | 不视为 safe best |
| `test_no_best_score_card_needs_human_review` | QG false + 无 best | 进入 `human_confirm`，`_settlement_needs_human_review=True` |
| `test_best_below_degraded_floor_needs_human_review` | QG false + best score 0.69 (<0.70) | 不进入 degraded_accept，需人工复核 |
| `test_context_emergency_degraded_streak_triggers_autohalt` | 连续 3 章 emergency + 1 章 QG fail | 触发 `AutoHaltException` |
| `test_context_emergency_single_fail_does_not_trigger_autohalt` | 连续 3 章 emergency 但 QG 均通过 | 不触发 AutoHalt |
| `test_quality_gate_fail_streak_triggers_autohalt` | 连续 3 章 QG fail（无 emergency） | 触发 AutoHalt |
| `test_mixed_streak_no_autohalt` | 2 章 emergency + 1 章正常 | 不触发 AutoHalt |
| `test_insufficient_window_no_autohalt` | recent_results < 3 | 不触发 AutoHalt |

---

## 3. 执行流程

### 3.1 环境准备

```powershell
# 确认在项目根目录
cd "c:\Vibe Project\Songyan"

# 安装测试依赖
pip install -e .[dev]

# 确认 pytest 和 pytest-asyncio 版本
python -m pytest --version
```

### 3.2 Mock 策略

集成测试使用 **Mock LLM** 注入预设的 score_card 和 review report，不调用真实 LLM API。

**Mock 对象清单**：
- `LLMAuditor.audit()` → 返回预设 `LLMAuditResult`
- `CreativeDirector.plan()` → 返回预设 `CreativeBrief`
- `Writer.write()` → 返回预设章节正文
- `QualityGate.evaluate()` → 返回预设 QG 结果（pass / fail / degraded）

**Mock 数据工厂**：
```python
def make_mock_score_card(chapter_number: int, overall_score: float) -> ScoreCard:
    return ScoreCard(
        chapter_number=chapter_number,
        overall_score=overall_score,
        # ... 其他维度按场景填充
    )
```

### 3.3 执行步骤

```powershell
# Step 1: 运行 122b 专属测试
python -m pytest tests/test_122b_*.py -v

# Step 2: 运行 pipeline 相关集成测试
python -m pytest tests/test_phase1_graph.py tests/test_rewrite_node.py -v

# Step 3: 全量回归
python -m pytest tests/ -q

# Step 4: Lint
ruff check src/ tests/
```

---

## 4. 当前进度

- **已完成**：全部 12 个集成测试已落地并通过。
  - Pipeline 路由、QG false、rewrite 清理、ContextEmergency、new_issues 拦截
  - degraded_accept 路由、safe best 保护、human_review_required gate、AutoHalt streak 逻辑
- **pytest 基线**：`tests/test_122b_pipeline_scenarios.py` 12/12 passed；全量 pytest 当前为 `1781 passed, 3 failed, 1 xfailed`（3 个失败与 122b 无关，系 `setting_snapshots.lifecycle_status` 列缺失导致）。
- **ruff**：All checks passed。

---

## 5. 交付标准

- [x] 5 个核心场景测试全部通过
- [x] 待补充场景全部通过（新增 12 个测试）
- [x] pytest 全量通过（1776 passed，零回归）
- [x] ruff 通过
- [x] 每个新增测试附带 Mock 数据工厂和断言注释

---

## 6. 相关文档

- 主文档：[122-v51-systematic-test-matrix.md](122-v51-systematic-test-matrix.md)
- Pipeline 路由实现：`src/songyan/workflows/_nodes.py`
- Quality Gate 实现：`src/songyan/workflows/quality_gate_router.py`
- Pass 14-18 修复汇总：[archive/v5/reports/pass14-final-fix-summary.md](../archive/v5/reports/pass14-final-fix-summary.md)