# Task 166b DONE: 人工确认后的 re-plan 应用

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 X（叙事自驱）
> **结论**: 完成。approved `ReplanProposal` 已可在人工确认后事务化应用到未来规划，draft/rejected/applied 状态保护生效，失败会 rollback。

---

## 交付内容

- 新增 proposal 状态流转：
  - `draft -> approved`
  - `draft -> rejected`
  - `approved -> applied`
- 新增应用服务：
  - `approve_replan_proposal(...)`
  - `reject_replan_proposal(...)`
  - `apply_replan_proposal(...)`
- 扩展 `NarrativeRepository` 最小写方法：
  - 更新未来 `ArcPlan.arc_goal`
  - 结构化更新 `ArcPlan.threads_to_open`
  - 结构化更新 `ArcPlan.threads_to_resolve`
  - 更新 `PlotThread.expected_resolve_arc`
  - 状态变更仍复用 `advance_thread_status(...)` 并要求 evidence
- 新增最小规划约束事实源：
  - `planning_constraints`
  - 用于承接 `style_constraint` / planning constraint action

## 边界确认

- 不创建 proposal；166a 负责生成 draft。
- 不生成、不修订、不改写正文。
- 不接入主生成 workflow。
- 不允许自动 approve。
- 不改历史或 source arc 覆盖范围内的 `ArcPlan`。
- 任一 action 失败时 rollback，proposal 保持 `approved`。

## 验证结果

```powershell
python -m pytest tests/test_166b_replan_application.py -q
# 7 passed

python -m pytest tests/test_141_narrative_skeleton.py tests/test_142_project_outline.py tests/test_144_thread_economy.py tests/test_166a_replan_evaluation.py tests/test_166b_replan_application.py -q
# 54 passed

ruff check src/ tests/
# All checks passed

python -m pytest tests/ -q
# 2352 passed, 2 skipped, 1 xfailed, 2 warnings
```

## 后续

Task 166 总览已满足：166a 能生成可审计 draft proposal，166b 能人工确认后事务化应用并保留 diff。下一步进入 Task 167 规划：长程伏笔主动兑现调度。
