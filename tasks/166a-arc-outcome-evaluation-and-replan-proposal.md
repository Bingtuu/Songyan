# Task 166a: 弧后评估与 ReplanProposal 生成

> **Phase**: V7 阶段 X（叙事自驱）
> **优先级**: P0（Task 166 的只读/追加式前半段）
> **依赖**: Task 165/165p 阶段 W 通过；Task 166 总览
> **预计工作量**: 中到大
> **事实入口**: `tasks/166-plan-generate-replan-loop.md`

> **执行结果**: 已完成，见
> `tasks/166a-arc-outcome-evaluation-and-replan-proposal-DONE.md`。166b 亦已完成，Task 166
> 总结见 `tasks/166-plan-generate-replan-loop-DONE.md`；下一步进入 Task 167 规划。

---

## Goal

实现离线的弧后评估能力：基于 SQLite 事实源读取前置规划、真实生成结果和长篇质量度量，输出结构化、可审计、默认不应用的 `ReplanProposal`。

166a 只生成 proposal，不修改 `ArcPlan` / `PlotThread` / 正文，也不接入主生成 workflow。

## Context

阶段 W 已经证明修复后的生成管线可以稳定跑完 Ch1-Ch150，并冻结 T9/T10。但人工阅读仍发现后段风格债：句式模型化、概念解释密度高、人物声纹同质。166a 的任务是把这些“读回来的现实问题”转成后续规划建议，而不是自动改写正文。

现有可复用事实源：

- `ArcPlan` / `PlotThread`：前置规划目标与线索生命周期。
- `summaries` / `arc_summaries`：生成后的剧情现实。
- `literary_observations`：文学诊断。
- `text_cleanliness_metrics`：T9 洁净度。
- `continuity_reports` / `setting_tracking`：T6/T7 线索与设定信号。

## In Scope

- [x] 新增 Pydantic 模型：
  - `ArcOutcomeEvaluation`
  - `ReplanProposal`
  - `ReplanAction`
  - `ReplanProposalStatus`
- [x] 新增 SQLite 表与迁移：
  - `replan_proposals`
  - `replan_actions`
- [x] 新增 repository：
  - create/get/list proposal
  - create/list actions
  - 只创建/回读 `draft` proposal；approve/reject/apply 状态流转留给 166b
- [x] 实现 `evaluate_arc_outcome(project_id, *, arc_index=None, chapter_range=None)`：
  - 读取当前或指定 `ArcPlan`。
  - 读取该弧相关 `PlotThread`。
  - 读取 `summaries` / `arc_summaries`。
  - 读取 T9/T10/T6/T7 相关度量。
  - 生成 `ArcOutcomeEvaluation`。
- [x] 实现 `build_replan_proposal(evaluation)`：
  - 对未开启线索生成 open/advance 建议。
  - 对应收束未收束线索生成 resolve-window 建议。
  - 对 T9/T10/T6/T7 风险生成 planning constraint。
  - 对阶段 W 人工读后风格债生成 style constraint。
- [x] 提供离线入口：
  - 建议脚本：`scripts/run_166a_replan_eval.py`
  - 支持 project_id + arc_index 或 chapter_range。
- [x] 支持无骨架项目：
  - 返回 no-op evaluation / proposal。
  - 不报错，不创建误导性 action。

## Out of Scope

- 不应用 proposal。
- 不修改 `ArcPlan` / `PlotThread`。
- 不生成、不修改正文。
- 不调用 RevisionHandler / rewrite。
- 不接入 phase1/phase2 workflow。
- 不跑真实 LLM 长跑。

## 数据模型要求

实现字段可微调，但必须覆盖：

- proposal_id
- project_id
- source_arc_index
- source_start_chapter / source_end_chapter
- status: `draft`
- summary
- evidence
- created_at
- actions:
  - action_id
  - proposal_id
  - action_order
  - target_type
  - target_id
  - field
  - old_value
  - new_value
  - reason

166a 只允许创建 `draft` proposal，不允许写 `approved/rejected/applied`。

`target_type` 至少要能表达 `arc_plan`、`plot_thread`、`style_constraint` 三类目标；其中 `style_constraint` 是未来规划约束，不得落到 LangGraph state。

## 测试要求

目标测试：

```powershell
python -m pytest tests/test_166a_replan_evaluation.py -q
```

必要覆盖：

- [x] 无骨架项目 no-op。
- [x] 弧目标已达成时生成低风险 proposal。
- [x] `threads_to_resolve` 未兑现时生成 replan action。
- [x] T9/T10 通过但存在风格债时生成 style constraint action。
- [x] proposal 与 actions 可写入并回读。
- [x] 166a 不修改 ArcPlan / PlotThread。

如新增 migration/repository：

```powershell
python -m pytest tests/test_142_project_outline.py tests/test_144_thread_economy.py tests/test_166a_replan_evaluation.py -q
```

收尾：

```powershell
python -m pytest tests/ -q
ruff check src/ tests/
```

## 验收标准

- [x] `ReplanProposal` 和 `ReplanAction` 持久化入 SQLite。
- [x] 评估输入全部从 SQLite repository 读取。
- [x] 无骨架项目不报错。
- [x] 至少一个 Task 165 DB 离线样本可生成 proposal。
- [x] proposal 默认 `draft`，不会自动应用。
- [x] 生成 `tasks/166a-arc-outcome-evaluation-and-replan-proposal-DONE.md`。

## 参考文档

- `tasks/166-plan-generate-replan-loop.md`
- `src/songyan/models/narrative.py`
- `src/songyan/db/narrative_repo.py`
- `src/songyan/evals/db_metrics.py`
- `docs/reports/task-165-stage-w-exit-report.md`
