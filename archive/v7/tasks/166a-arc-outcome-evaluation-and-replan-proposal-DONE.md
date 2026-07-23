# Task 166a DONE: 弧后评估与 ReplanProposal 生成

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 X（叙事自驱）
> **结论**: 完成。166a 已提供离线弧后评估与 draft `ReplanProposal` 生成能力，不接入主生成 workflow，不修改正文，不应用 proposal。

---

## 交付内容

- 新增 `ArcOutcomeEvaluation` / `ReplanProposal` / `ReplanAction` / `ReplanProposalStatus` 模型。
- 新增 SQLite 表：
  - `replan_proposals`
  - `replan_actions`
- 新增 `ReplanProposalRepository`：
  - 只允许创建 `draft` proposal。
  - proposal 与 actions 在单事务内写入。
  - 支持 get/list/list_actions 回读。
- 新增离线评估：
  - `evaluate_arc_outcome(project_id, *, arc_index=None, chapter_range=None)`
  - `build_replan_proposal(evaluation)`
- 新增离线脚本：
  - `scripts/run_166a_replan_eval.py`

## 边界确认

- 不修改 `ArcPlan` / `PlotThread`。
- 不生成、不修订、不改写正文。
- 不调用 RevisionHandler / rewrite。
- 不接入 phase1/phase2 workflow。
- 不自动 approve/apply proposal。
- 风格债只转为 `style_constraint` action，作为后续规划约束。

## 验证结果

```powershell
python -m pytest tests/test_166a_replan_evaluation.py -q
# 6 passed

python -m pytest tests/test_142_project_outline.py tests/test_144_thread_economy.py tests/test_166a_replan_evaluation.py -q
# 30 passed

python -m pytest tests/test_141_narrative_skeleton.py tests/test_166a_replan_evaluation.py -q
# 23 passed

ruff check src/ tests/
# All checks passed

python -m pytest tests/ -q
# 2345 passed, 2 skipped, 1 xfailed, 2 warnings

python -m py_compile scripts/run_166a_replan_eval.py
# passed
```

Task 165 DB 离线样本验证使用 `.tmp/task165_stage_w_ch150.db` 的复制库执行，未修改原始长跑证据库。样本结果：识别到叙事骨架，生成 4 个 draft replan action。

## 后续

166b 已完成，见 `archive/v7/tasks/166b-approved-replan-application-DONE.md`；Task 166 总结见
`archive/v7/tasks/166-plan-generate-replan-loop-DONE.md`。下一步进入 Task 167 规划：长程伏笔主动兑现调度。
