# Task 167a DONE: 主动伏笔调度计划生成

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 X（叙事自驱）
> **结论**: 完成。系统现在可以离线生成 draft `ForeshadowingSchedulePlan`，把主线线索、临近/逾期伏笔和 Task 166 的 `planning_constraints` 转化为可审计的主动调度项。

---

## 交付内容

- 新增调度模型：
  - `ForeshadowingSchedulePlan`
  - `ForeshadowingScheduleItem`
  - `ForeshadowingScheduleStatus`
  - `ForeshadowingScheduleReason`
- 新增 SQLite 表：
  - `foreshadowing_schedule_plans`
  - `foreshadowing_schedule_items`
- 新增 repository：
  - `ForeshadowingScheduleRepository`
  - 支持 create/get/list/list_recent_items/status update
- 新增离线调度生成：
  - `generate_foreshadowing_schedule_plan(...)`
- 新增脚本：
  - `scripts/run_167a_foreshadowing_schedule.py`
- 扩展 `ForeshadowingRepository.list_schedulable(...)`，读取 active 且 `planted/due/overdue` 的伏笔。

## 调度规则

- 主线 `PlotThread` 优先。
- 当前弧 `threads_to_open` / `threads_to_resolve` 提升优先级。
- `expected_resolve_arc` 临近或已逾期的 thread 提升优先级。
- `expected_resolve_chapter` 临近或已逾期的 foreshadowing 提升优先级。
- Task 166 产生的 `planning_constraints` 能提升相关候选项优先级。
- 同一 source 在短窗口内已调度时抑制重复调度。
- 每章按 `max_items` 限额，避免规划输入过载。

## 边界确认

- 不注入 GoalPlanner / CreativeDirector。
- 不修改 `PlotThread` / `foreshadowings` 状态。
- 不生成、不修改正文。
- 不调用 RevisionHandler / rewrite。
- 不自动 approve。
- 不跑真实 LLM 长跑。

## 验证结果

```powershell
python -m pytest tests/test_167a_foreshadowing_schedule.py -q
# 8 passed

python -m pytest tests/test_141_narrative_skeleton.py tests/test_166a_replan_evaluation.py tests/test_166b_replan_application.py tests/test_167a_foreshadowing_schedule.py -q
# 38 passed

ruff check src/ tests/ scripts/run_167a_foreshadowing_schedule.py
# All checks passed

python -m pytest tests/ -q
# 2360 passed, 2 skipped, 1 xfailed, 2 warnings
```

## 后续

下一步进入 167b：调度计划注入与生命周期推进。167b 应将 active 调度项注入 GoalPlanner / CreativeDirector 的规划侧输入，并在章节 accept 后推进 `injected/satisfied/missed` 生命周期。
