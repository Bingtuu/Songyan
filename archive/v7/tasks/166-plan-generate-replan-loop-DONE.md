# Task 166 DONE: plan→generate→re-plan 闭环总览

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 X（叙事自驱）
> **结论**: 完成。Task 166 已拆分并完成 166a / 166b：系统现在可以离线评估生成结果与前置规划的偏差，生成 draft `ReplanProposal`，并在人工确认后事务化应用到未来规划。

---

## 拆分完成情况

| Task | 名称 | 结论 |
|------|------|------|
| 166a | 弧后评估与 ReplanProposal 生成 | ✅ 完成：`archive/v7/tasks/166a-arc-outcome-evaluation-and-replan-proposal-DONE.md` |
| 166b | 人工确认后的 re-plan 应用 | ✅ 完成：`archive/v7/tasks/166b-approved-replan-application-DONE.md` |

## 能力边界

- SQLite 是唯一事实源。
- 166a 只生成 draft proposal，不应用。
- 166b 必须人工 approve 后才能 apply。
- apply 只改未来规划与规划约束，不改正文、不回写历史章节。
- action 全部成功才 commit，任一失败 rollback。
- style / planning constraint 落入 `planning_constraints`，不进入 LangGraph state。

## 验证摘要

```powershell
python -m pytest tests/test_166a_replan_evaluation.py tests/test_166b_replan_application.py -q
# 13 passed

python -m pytest tests/ -q
# 2352 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
# All checks passed
```

## 后续

进入 Task 167：长程伏笔主动兑现调度。Task 167 应建立在 166 的可审计 re-plan 结果上，不直接做自动正文改写。
