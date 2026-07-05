# Task 167b DONE: 调度计划注入与生命周期推进

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 X（叙事自驱）
> **结论**: 完成。active `ForeshadowingScheduleItem` 已能进入 GoalPlanner / CreativeDirector 的规划侧输入，并在章节 accept 后推进 `injected/satisfied/missed` 生命周期。

---

## 交付内容

- 扩展 `NarrativeGoalContext.scheduled_items`，从 SQLite 读取 active/injected 调度项。
- GoalPlanner：
  - 将主动调度项合并进临近伏笔段。
  - 保留 source id、目标章、rationale。
- CreativeDirector：
  - 在线索经济约束中追加主动调度项段落。
  - Writer 仍只通过 CreativeBrief 间接接收约束，不直接查调度表。
- 新增生命周期服务：
  - `activate_foreshadowing_schedule_plan(...)`
  - `mark_schedule_items_injected(...)`
  - `update_schedule_after_accept(...)`
- Workflow 接入：
  - `goal_planner_node` 成功保存章节目标后，将 active 调度项标记为 injected。
  - `settlement_extractor_node` accept 后基于 settlement 证据标记 satisfied/missed。

## 边界确认

- 不新增 workflow 节点。
- 不让 Writer 直接查询调度表。
- 不生成、不修改正文。
- 不调用 RevisionHandler / rewrite。
- 不自动修改历史章节。
- 无 active schedule item 时旧行为不变。

## 验证结果

```powershell
python -m pytest tests/test_167b_schedule_injection.py -q
# 8 passed

python -m pytest tests/test_143_goal_planner_topdown.py tests/test_144_thread_economy.py tests/test_167a_foreshadowing_schedule.py tests/test_167b_schedule_injection.py -q
# 37 passed

ruff check src/ tests/ scripts/run_167a_foreshadowing_schedule.py
# All checks passed
```

## 后续

进入 Task 168：自适应门禁数据面。Task 168 应把调度命中率、missed rate、overdue rate 等信号沉淀为 gate 可读数据。
