# Task 122a: Unit Test Matrix — Dynamic Thresholds & Degraded Accept

> **日期**: 2026-06-23
> **类型**: V5.1 测试补强
> **状态**: TODO
> **前置**: Task 121q 动态阈值逻辑落地

---

## 1. 目标

为 Task 121q 的动态阈值和降级回滚路径增加单测覆盖，确保阈值边界和降级行为可验证、可回归。

---

## 2. 测试矩阵

| 测试名 | 场景 | 断言 |
|--------|------|------|
| `test_safe_best_threshold_ch10` | Ch10, overall=0.76 | 门槛=0.75，视为 safe best |
| `test_safe_best_threshold_ch30` | Ch30, overall=0.76 | 门槛=0.78，视为 unsafe |
| `test_safe_best_threshold_ch60` | Ch60, overall=0.80 | 门槛=0.78，视为 safe |
| `test_safe_best_threshold_ch100` | Ch100, overall=0.81 | 门槛=0.82，视为 unsafe |
| `test_degraded_accept_settlement` | best=0.76, QG 失败 | settlement 成功，标记 degraded_accept |
| `test_degraded_accept_score_card` | best=0.76, QG 失败 | score_card 保留 best 数据 |
| `test_skip_settlement_no_best` | 无 best, score=0.65 | skip_settlement=True |

---

## 3. 交付标准

- [ ] 新增 7 个测试全部通过
- [ ] pytest 全量通过（1731+）
- [ ] ruff 通过
