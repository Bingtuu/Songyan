# Task 169 DONE: 自适应 halt 判定

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 Y（enforce 可生产化）
> **结论**: 完成。系统现在具备自适应 halt 判定引擎、decision ledger，并已并行接入 phase2 后处理路径。

---

## 拆分完成情况

| Task | 名称 | 结论 |
|------|------|------|
| 169a | 自适应 halt 判定引擎与决策账本 | ✅ 完成：`tasks/169a-adaptive-halt-decision-engine-DONE.md` |
| 169b | 自适应 halt workflow 接入 | ✅ 完成：`tasks/169b-adaptive-halt-workflow-integration-DONE.md` |

## 交付能力

- `evaluate_adaptive_halt(...)` 可基于 `AdaptiveGateDataPlaneReport` 生成可解释判定。
- `adaptive_halt_decisions` 记录 decision / reason / evidence / policy version。
- phase2 可在章节后处理点并行生成 decision ledger。
- 默认关闭，不改变现有运行行为。
- 显式 enable 后，observe 只记录，enforce 可在 decision=`halt` 时暂停。

## 能力边界

- 不替换旧 `_gates.py`。
- 不改 Writer / RevisionHandler / SettlementExtractor。
- 不自动创建 ReplanProposal。
- 不自动 rewrite。
- 不冻结 T12。
- 不启动 Ch200。

## 验证摘要

```powershell
python -m pytest tests/test_169a_adaptive_halt_decision_engine.py tests/test_169b_adaptive_halt_workflow_integration.py -q
# 14 passed

python -m pytest tests/ -q
# 2397 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
# All checks passed
```

## 后续

进入 Task 170：enforce 小窗口验证 + T12 误报率标定。Task 170 应用良性波动/真实退化两类场景验证 169，并决定是否降权旧绝对阈值 gate。
