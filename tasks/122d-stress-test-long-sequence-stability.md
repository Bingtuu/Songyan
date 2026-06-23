# Task 122d: Stress Test — Long Sequence Stability

> **日期**: 2026-06-23
> **类型**: V5.1 压力测试
> **状态**: TODO

---

## 1. 目标

在不调用 LLM 的情况下，验证 150 章长序列的上下文管理和状态机稳定性。

---

## 2. 测试矩阵

| 测试名 | 方法 | 断言 |
|--------|------|------|
| `test_context_budget_150_chapters` | mock LLM，模拟 budget_used 趋势 | 无 >1.2 的异常跳变 |
| `test_human_marks_decay_6_chapters` | 注入 marks，验证蒸发 | 第7章 marks 数量为 0 |
| `test_auto_halt_false_positive` | 连续3章 emergency + QG pass | AutoHalt **不**触发 |
| `test_auto_halt_true_positive` | 连续3章 emergency + QG fail | AutoHalt 触发 |
| `test_accepted_chapter_skip` | pipeline 遇到 accepted 章节 | 跳过，不重复执行 |

---

## 3. 交付标准

- [ ] 5 项压力测试全部通过
- [ ] pytest 全量通过
- [ ] ruff 通过
