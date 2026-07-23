# Task 167: 长程伏笔主动兑现调度

> **Phase**: V7 阶段 X（叙事自驱）
> **优先级**: P0（Task 166 后的直接后续；T11 的前置）
> **状态**: ✅ 完成（167a / 167b 均已完成）
> **依赖**: Task 166 DONE；阶段 W 出口通过，T9/T10 已冻结
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 X

---

## Goal

把长程伏笔从“生成后审计发现是否遗忘”升级为“章节规划前主动调度”。系统应能基于 SQLite 事实源识别临近推进/兑现窗口的主线伏笔、PlotThread 和规划约束，生成可审计的调度计划，并在后续章节规划侧显式使用。

Task 167 的核心不是自动改写正文，而是让 GoalPlanner / CreativeDirector 在写作前看见“本章为什么必须推进某条长线”。

## 背景

Task 166 已建立 plan→generate→re-plan 的基本闭环：

- 166a 能离线评估弧目标、线索状态和质量债，并生成 draft `ReplanProposal`。
- 166b 能在人工确认后事务化应用 proposal，将约束写入未来规划事实源。

但 Task 166 仍偏“弧后调整”。Task 167 要解决的是“每章生成前如何主动选择该推进/兑现的长线伏笔”，否则长线伏笔仍可能只在报告里被发现，而不会稳定进入章节目标。

## 拆分结论

Task 167 拆为两个子任务：

| Task | 名称 | 边界 |
|------|------|------|
| 167a | 主动伏笔调度计划生成 | ✅ 已完成：离线/规划侧生成调度计划，不注入主生成流程 |
| 167b | 调度计划注入与生命周期推进 | ✅ 已完成：将 active 调度计划注入 GoalPlanner / CreativeDirector 输入，并更新调度生命周期 |

这样拆分的原因是：167a 是只读/追加式能力，可独立验证调度排序和证据；167b 是生成前规划侧注入，会影响章节目标，必须等 167a 的数据模型和证据稳定后再做。

## 总体边界

- SQLite 是唯一长期事实源。
- 不从 LangGraph state 拼业务对象。
- 不生成、不修改正文。
- 不调用 RevisionHandler / rewrite。
- 不自动改写历史章节。
- 不新增长期运行 workflow 节点。
- 调度结果只进入规划侧事实源和后续章节输入。
- 无骨架或无线索项目必须 no-op，回退旧行为。
- 167 不启动 Ch200 长跑；Ch200 属于 171。

## 数据源

167 的输入必须来自 SQLite repository/service：

- `PlotThread`：主线/支线状态、`expected_resolve_arc`、当前生命周期。
- `foreshadowings`：伏笔来源、预计兑现章、状态、source_version_id。
- `ArcPlan`：当前弧与未来弧的应开线索 / 应收束线索。
- `planning_constraints`：Task 166 应用后的未来规划约束。
- `summaries` / `arc_summaries`：已生成剧情现实。
- `continuity_reports` / `text_cleanliness_metrics` / `literary_observations`：调度风险参考，不作为自动改文依据。

## 167a: 主动伏笔调度计划生成

### Goal

新增离线调度能力，读取当前项目的长线伏笔和线索状态，生成结构化 `ForeshadowingSchedulePlan` / `ForeshadowingScheduleItem`。

### In Scope

- [x] 新增 Pydantic 模型：
  - `ForeshadowingSchedulePlan`
  - `ForeshadowingScheduleItem`
  - `ForeshadowingScheduleStatus`
  - `ForeshadowingScheduleReason`
- [x] 新增 SQLite 表：
  - `foreshadowing_schedule_plans`
  - `foreshadowing_schedule_items`
- [x] 新增 repository：
  - create/get/list schedule plan
  - create/list schedule items
  - update schedule status（仅状态，不触发生成）
- [x] 实现调度候选收集：
  - 主线 `PlotThread` 优先。
  - 即将进入 `expected_resolve_arc` 的 thread 优先。
  - `foreshadowings.expected_resolve_chapter` 临近或逾期的项优先。
  - Task 166 产生的 `planning_constraints` 可提高优先级。
- [x] 实现排序与限额：
  - 每章最多 N 个主动调度项，避免 Writer 过载。
  - 同一伏笔/线索在短窗口内不能重复调度。
  - overdue / due / mainline / replan-backed 必须有可解释排序。
- [x] 支持无骨架 / 无伏笔 no-op。
- [x] 提供离线入口：
  - 建议脚本：`scripts/run_167a_foreshadowing_schedule.py`

### Out of Scope

- 不注入 GoalPlanner / CreativeDirector。
- 不修改 `PlotThread` / `foreshadowings` 状态。
- 不生成、不修改正文。
- 不自动 approve。
- 不跑真实 LLM 长跑。

### 测试要求

目标测试：

```powershell
python -m pytest tests/test_167a_foreshadowing_schedule.py -q
```

必要覆盖：

- [x] 无骨架/无伏笔 no-op。
- [x] 主线 thread 优先于普通支线。
- [x] expected_resolve_arc 临近时生成 due schedule item。
- [x] overdue foreshadowing 进入高优先级。
- [x] planning constraint 能提升相关项优先级。
- [x] 短窗口内重复调度被抑制。
- [x] schedule plan / items 可写入并回读。

## 167b: 调度计划注入与生命周期推进

### Goal

在 167a 计划稳定后，将 active/approved schedule items 注入章节规划侧输入，使 GoalPlanner / CreativeDirector 能显式使用长程伏笔调度结果。

### In Scope

- [x] 定义 schedule item 状态流转：
  - `draft -> active`
  - `active -> injected`
  - `injected -> satisfied`
  - `injected -> missed`
  - `active/injected -> cancelled`
- [x] 将 active schedule item 注入 GoalPlanner 或 narrative context：
  - 注入为章节目标候选事件、obligation 或 planning constraint。
  - 必须带 source id 和 reason。
- [x] CreativeDirector brief 可见调度项：
  - 通过 `style_constraints` / `required_tensions` / planning section 的现有结构注入，避免新增 Agent。
- [x] 章节 accept 后基于 settlement/summary 更新 schedule item：
  - 若相关 thread/foreshadowing 被推进或兑现，标记 satisfied。
  - 若窗口过期未体现，标记 missed，供 Task 166 生成后续 proposal。
- [x] 支持 no-op 回退：无 active schedule item 时旧行为不变。

### Out of Scope

- 不让 Writer 直接查询调度表。
- 不新增 workflow 节点。
- 不自动 rewrite。
- 不修改历史正文。
- 不做 Ch200 长跑。

### 测试要求

目标测试：

```powershell
python -m pytest tests/test_167b_schedule_injection.py -q
```

必要覆盖：

- [x] active schedule item 能进入规划侧输入。
- [x] 无 active item 时旧行为不变。
- [x] 注入项带 source id 和 reason。
- [x] 同一章注入数量受限。
- [x] accept 后相关线索推进时标记 satisfied。
- [x] 过期未体现时标记 missed。
- [x] missed 项能作为 Task 166 后续评估证据。

## 验收标准

Task 167 完成时必须满足：

- [x] 调度计划与调度项持久化到 SQLite。
- [x] 无骨架 / 无伏笔项目 no-op。
- [x] active 调度项能进入章节规划侧输入。
- [x] 调度生命周期可审计。
- [x] Task 166 的 `planning_constraints` 能参与调度排序。
- [x] 不新增不可控自动改写闭环。
- [x] 不破坏 Task 165/165p 的 T9/T10 冻结口径。
- [x] 生成 `archive/v7/tasks/167-long-range-foreshadowing-active-scheduling-DONE.md`。

## 与后续任务关系

- **Task 168** 应在 167 后启动，把调度命中率、missed rate、overdue rate 等变成自适应门禁数据面的一部分。
- **Task 171 Ch200 长跑** 必须等 167 与 168-170 关键门禁能力落地后再启动。

## 参考文档

- `archive/v7/tasks/166-plan-generate-replan-loop-DONE.md`
- `archive/v7/tasks/166a-arc-outcome-evaluation-and-replan-proposal-DONE.md`
- `archive/v7/tasks/166b-approved-replan-application-DONE.md`
- `src/songyan/models/narrative.py`
- `src/songyan/db/narrative_repo.py`
- `src/songyan/db/replan_repo.py`
- `src/songyan/workflows/_narrative_context.py`
- `src/songyan/workflows/_thread_economy.py`
- `archive/v7/reports/task-165-stage-w-exit-report.md`
