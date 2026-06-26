# Task 121q: Safe-Best Threshold Dynamic Fix

> **日期**: 2026-06-23
> **类型**: V5.1 工程修复
> **状态**: **DONE**
> **前置**: Task 121p 暴露 0.82 阈值对早期章节的致命性

---

## 1. 问题

`_SAFE_BEST_MIN_OVERALL_SCORE = 0.82` 是全局静态阈值。早期章节（Ch1-Ch20）处于铺垫期，叙事张力、角色深度未展开，天然难以达到 0.82。当这些章节触发 rewrite 时，因 best version < 0.82 而无法回滚，导致 `skip_settlement=True` 和项目死亡。

Task 121p 重跑 `run-2d7d96c2` 中，Ch4 overall_score=0.8113 因此死亡（`error_stage=settlement_review`, `convergence_failed=True`），而 Ch1 overall_score=0.7823 反而通过（未触发 rewrite）。

---

## 2. 修复方案

### 2.1 方案 A（推荐）：章节阶段感知动态阈值

```python
def _safe_best_min_score(chapter_number: int) -> float:
    """早期章节天然分数偏低，safe-best 门槛应随章节递进。"""
    if chapter_number <= 20:
        return 0.75
    elif chapter_number <= 50:
        return 0.78
    else:
        return 0.82
```

### 2.2 方案 B（配合方案 A）：允许降级回滚

允许回滚到 < safe-best 门槛的 best version，但标记 `degraded_accept=True`，settlement 继续执行，不直接杀死章节。

**决策逻辑**：
- `best_score >= _safe_best_min_score(chapter)` → 正常回滚，`quality_gate_passed=True`
- `best_score < _safe_best_min_score(chapter)` 但 `best_score >= 0.70` → 降级回滚，`quality_gate_passed=False`，`degraded_accept=True`，settlement 继续
- `best_score < 0.70` 或无 best → `skip_settlement=True`，章节死亡

---

## 3. 代码位置

| 文件 | 位置 | 内容 |
|------|------|------|
| `src/songyan/workflows/_nodes.py` | L78-L79 | `_SAFE_BEST_MIN_OVERALL_SCORE = 0.82` |
| `src/songyan/workflows/_nodes.py` | L221-L226 | `_is_safe_best_version` 函数 |
| `src/songyan/workflows/_nodes.py` | L872-L912 | `settlement_review_node` 回滚决策逻辑 |

---

## 4. 验证方式

1. **单元测试**：边界条件测试（Ch10/0.76, Ch60/0.80, Ch100/0.81）
2. **聚焦实跑**：Ch1-Ch20 验证，预期 ≥18/20 成功
3. **断言**：Ch4 类场景不再因 0.81 分而死亡

---

## 5. 交付标准

- [ ] `_safe_best_min_score` 动态阈值逻辑落地
- [ ] `degraded_accept` 路径支持 settlement 继续
- [ ] pytest 全量通过（1731+ 新增测试）
- [ ] Ch1-Ch20 聚焦验证 ≥18/20 成功
