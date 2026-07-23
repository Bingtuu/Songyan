# Task 167 DONE: 长程伏笔主动兑现调度

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 X（叙事自驱）
> **结论**: 完成。系统现在可以生成主动伏笔调度计划，并将 active 调度项注入章节规划侧输入，同时在章节 accept 后推进调度生命周期。

---

## 拆分完成情况

| Task | 名称 | 结论 |
|------|------|------|
| 167a | 主动伏笔调度计划生成 | ✅ 完成：`archive/v7/tasks/167a-foreshadowing-schedule-plan-DONE.md` |
| 167b | 调度计划注入与生命周期推进 | ✅ 完成：`archive/v7/tasks/167b-schedule-injection-and-lifecycle-DONE.md` |

## 能力边界

- SQLite 是唯一事实源。
- 调度计划持久化在 `foreshadowing_schedule_plans` / `foreshadowing_schedule_items`。
- 调度项可进入 GoalPlanner / CreativeDirector 的规划侧输入。
- Writer 不直接查询调度表。
- 章节 accept 后，调度项可标记为 `satisfied` 或 `missed`。
- 不新增 workflow 节点。
- 不自动改写正文或历史章节。
- 不启动 Ch200 长跑。

## 验证摘要

```powershell
python -m pytest tests/test_167a_foreshadowing_schedule.py tests/test_167b_schedule_injection.py -q
# 16 passed

python -m pytest tests/ -q
# 2368 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/ scripts/run_167a_foreshadowing_schedule.py
# All checks passed
```

## 后续

进入 Task 168：自适应门禁数据面。Task 168 应读取 Task 167 的调度生命周期信号，将调度命中率、missed rate、overdue rate 等沉淀为后续 T11/T12 的 gate 输入。
