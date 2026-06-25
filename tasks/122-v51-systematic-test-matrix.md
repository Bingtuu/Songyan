# Task 122: V5.1 系统性测试矩阵

> **日期**: 2026-06-25
> **类型**: V5.1 测试补强
> **状态**: 进行中（122a 已完成，122b 部分完成，122c 部分完成，122d 待启动）
> **前置**: Task 121q 动态阈值落地 + Task 121r Prompt 质量清理完成

---

## 1. 目标

为 V5.1 建立四层测试防护网，覆盖从单元边界到 150 章长序列的完整置信度：

| 层级 | 子任务 | 关注点 | 方法 |
|------|--------|--------|------|
| 单元测试 | 122a | 动态阈值边界、降级回滚路径 | 纯代码，无 LLM |
| 集成测试 | 122b | Pipeline 路由、质量门分支、rewrite 策略 | Mock LLM，单章 pipeline |
| E2E 验证 | 122c | 三窗口实跑（早期/中段/后段） | 真实 LLM，分段验证 |
| 压力测试 | 122d | 150 章上下文衰减、状态机、AutoHalt | 重度 Mock / 实跑 |

---

## 2. 子任务总览与当前状态

| 子任务 | 文档 | 状态 | 说明 |
|--------|------|------|------|
| 122a | [122a-unit-test-matrix-dynamic-thresholds.md](122a-unit-test-matrix-dynamic-thresholds.md) | **已完成** | 7 个边界测试已落地，pytest 通过 |
| 122b | [122b-integration-test-pipeline-scenarios.md](122b-integration-test-pipeline-scenarios.md) | **已完成** | 12 个集成测试全部落地并通过，覆盖 Pipeline 路由、QG false、rewrite 清理、ContextEmergency、new_issues 拦截、degraded_accept、safe best、human_review_required gate、AutoHalt streak |
| 122c | [122c-e2e-validation-windows.md](122c-e2e-validation-windows.md) | **部分完成** | Ch1-Ch20 E2E 已完成（28 秒重度 Mock）；**Ch40-Ch50 / Ch100-Ch110 窗口待补充** |
| 122d | [122d-stress-test-long-sequence-stability.md](122d-stress-test-long-sequence-stability.md) | **TODO** | 150 章长序列压力测试待启动 |

---

## 3. 执行顺序与依赖关系

```
122a (单元) ──┬──► 122b (集成) ──┬──► 122c (E2E) ──┬──► 122d (压力)
              │                   │                  │
121q 完成 ────┘              121r 完成 ──────────────┘
```

**执行原则**：
1. 先完成 122a，确保阈值逻辑边界可靠。
2. 再推进 122b，确保 pipeline 路由不回归。
3. 122c 的 Ch1-Ch20 可与 122b 并行；Ch40-Ch50 和 Ch100-Ch110 必须在 122b 基本完成后启动。
4. 122d 最后执行，因为它依赖前面三层的结果，且成本最高（长序列实跑或全链路 Mock）。

---

## 4. 总体验收标准

- [ ] 122a：7 个单元测试全部通过，pytest 全量通过，ruff 通过。
- [x] 122b：5 个核心场景 + 已补充缺口全部通过，pytest 全量通过，ruff 通过。
- [ ] 122c：三个窗口全部达标（Ch1-Ch20 ≥18/20，Ch40-Ch50 ≥8/10，Ch100-Ch110 ≥8/10）。
- [ ] 122d：5 项压力测试全部通过，pytest 全量通过，ruff 通过。
- [ ] 四层测试合计新增测试 ≥30 个，零回归。

---

## 5. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 122c E2E 窗口实跑成本高 | 时间和 API 费用 | 优先用 Mock 验证窗口逻辑，再决定是否实跑 |
| 122d 150 章 Mock 复杂度高 | 测试维护困难 | 分阶段：先 50 章 Mock，再 100 章，最后 150 章 |
| 新测试与现有代码冲突 | 回归 | 每完成一个子任务立即跑全量 pytest，发现问题立即修复 |

---

## 6. 相关文档

- V5.1 规划：[121a-v50-goal-assessment-and-v51-plan.md](121a-v50-goal-assessment-and-v51-plan.md)
- Pass 14-18 修复汇总：[docs/reports/pass14-final-fix-summary.md](../docs/reports/pass14-final-fix-summary.md)
- STATUS：[docs/STATUS.md](../docs/STATUS.md)