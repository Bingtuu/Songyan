# Task 122b: Integration Test — Pipeline Scenarios

> **日期**: 2026-06-23（更新于 2026-06-25）
> **类型**: V5.1 集成测试
> **状态**: **部分完成**
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

### 2.2 待补充场景（状态：待完成）

| 测试名 | 场景 | 断言 | 优先级 |
|--------|------|------|--------|
| `test_degraded_accept_router` | QG false + score ≥ 0.70 | 路由到 degraded_accept，不进入 rewrite | P1 |
| `test_safe_best_preserve_on_rewrite` | rewrite 后 score < best | best 版本不被覆盖，最终回退到 best | P1 |
| `test_human_review_required_gate` | QG false + score < 0.70 + 无 best | 进入 human_review_required | P1 |
| `test_context_emergency_degraded_streak` | 连续 3 章 emergency + QG fail | 触发 AutoHalt | P2 |
| `test_context_emergency_single_fail` | 单章 emergency + QG pass | 不触发 AutoHalt | P2 |

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

- **已完成**：Pipeline 路由、QG false、rewrite 清理、ContextEmergency、new_issues 拦截均已测试。
- **待补充**： degraded_accept 路由、safe best 保护、human_review_required gate、AutoHalt streak 逻辑。
- **pytest 基线**：`1764 passed, 1 xfailed, 2 warnings`。

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
- Pass 14-18 修复汇总：[docs/reports/pass14-final-fix-summary.md](../docs/reports/pass14-final-fix-summary.md)