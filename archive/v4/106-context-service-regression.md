# Task 106: ContextService 回归 + 新模式端到端

> **Phase**: V4.0 Phase C — ContextService 演进（门控/暂缓）
> **优先级**: P1（暂缓）
> **依赖**: Task 105（ContextService 集成完成）
> **预计工作量**: 大（4 天）

---

## Goal

新旧模式全量对比验证：旧模式 pytest 全量回归通过；新模式 Ch1-Ch20 端到端跑通，质量不下降（budget_used、字数、health_score 与旧模式对比）。

## Context

Phase C 的最后一道验证。确保 ContextService 引入没有回退旧模式，新模式在短程内质量不下降。

## In Scope（必须完成）

- [ ] **旧模式全量回归**：`pytest -x -q` 通过
- [ ] **新模式 Ch1-Ch20 端到端**：跑通
- [ ] **质量对比**：
  - budget_used 新模式 ≤ 旧模式 + 0.2
  - 字数达标率 新模式 ≥ 旧模式 - 10%
  - health_score 新模式 ≥ 旧模式 - 0.5
- [ ] **问题修复**：任何新模式特有的 bug

## Out of Scope（明确不做）

- Ch21+ 验证（Task 096-099 当前主线）
- 任何架构修改

## 验收标准（Acceptance Criteria）

- [ ] 旧模式 `pytest -x -q` 通过
- [ ] 新模式 Ch1-Ch20 端到端跑通
- [ ] 质量对比报告
- [ ] 生成了 `tasks/106-context-service-regression-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 7.3 节
