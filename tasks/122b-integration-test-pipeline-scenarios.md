# Task 122b: Integration Test — Pipeline Scenarios

> **日期**: 2026-06-23
> **类型**: V5.1 集成测试
> **状态**: TODO
> **前置**: Task 121q 动态阈值逻辑落地

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

---

## 3. 方法

Mock LLM 调用，注入预设 score_card 和 review report，观测 pipeline 路由与终态。

---

## 4. 交付标准

- [ ] 5 个场景测试全部通过
- [ ] pytest 全量通过
- [ ] ruff 通过
