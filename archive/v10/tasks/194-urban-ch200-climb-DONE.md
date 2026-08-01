# Task 194 DONE: urban Ch200 爬坡

> **阶段**: V10.2 跨体裁 Ch200 爬坡
> **状态**: ✅ 完成
> **完成时间**: 2026-07-31

## 结论

Urban Ch200 已完成。V10 target DB `.tmp/task_v10_urban_ch200.db` 中 project_id=`81e345042b124ee2a73094b82e4be555`、run_id=`run-v10-urban-743a979a` 最终为 completed 1..200、failed=[]、total_cost=14.91622。Ch200 accepted/current head=`clean-200-t9-194k`。

## Checkpoint 结果

| checkpoint | five-gate | segment audit | T9 | 关键指标 |
|------------|-----------|---------------|----|----------|
| Ch125 | PASS | PASS | 0 | budget=0.9595、CED/1k=0.0905、overdue=108、health=9.5、gap=0 |
| Ch150 | PASS | PASS | 0 | budget=0.9595、CED/1k=0.0786、overdue=116、health=8.7、gap=0 |
| Ch175 | PASS | PASS | 0 | budget=0.9595、CED/1k=0.0693、overdue=134、health=8.0、gap=0 |
| Ch200 | PASS | PASS | 0 | budget=0.9595、CED/1k=0.066、overdue=153、health=8.2、gap=0 |

Ch125/150/175/200 five-gate 均显式绑定 `archive/v10/artifacts/189-scifi-ch200-baseline.json`。

## 修复项

- 194.a：Ch123 settlement JSON parse accepted gap 修复。
- 194.b：Ch125 T9 meta clean。
- 194.c：Ch147 health_low_streak_halt 修复。
- 194.d：Ch150 segment/T9 hard gates 修复。
- 194.e：Ch162 GoalPlanner JSON parse retry 修复。
- 194.f：Ch174 health_low_streak_halt 修复。
- 194.g：Ch175 T9 meta hard gate 修复。
- 194.h：Ch179 settlement numerical validation retry 修复。
- 194.i：Ch198 health_low_streak_halt 修复。
- 194.j：Ch199/200 LLM empty parse accepted gap 修复；最终使用 fallback model `deepseek/deepseek-chat`，不得记为 flash clean sample。
- 194.k：Ch200 T9 meta hard gate deterministic clean，Ch200 head=`clean-200-t9-194k`。

## 终点证据

```powershell
python scripts/run_v10_ch200_climb.py --audit --genre urban --up-to 200 --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json --format json
```

- five-gate：PASS，accepted=200，gap=0，budget_used_peak=0.9595，CED/1k=0.066，overdue=153，health_latest=8.2，health_report_chapter=200。
- segment audit：PASS，critical_orphans=0，total_orphans=76，halt_would_fire=false。
- metrics/T9：PASS，meta=0，duplicate=0，timeline=3 report-only。
- DB SHA256：`08921291C3F9E3A5F42199CD7AA109A1164372150D42C08001A845DA9A212861`。

## 落盘路径

- target DB：`.tmp/task_v10_urban_ch200.db`
- project file：`.tmp/task_v10_urban_project.json`
- final report：`.tmp/v10_urban_ch200_final.json`
- five-gate：`.tmp/v10_urban_seg200_five_gate.json`
- segment audit：`.tmp/v10_urban_seg200_audit.json`
- metrics/T9：`.tmp/v10_urban_seg200_metrics.md`

## 后续

Task 194 已满足 urban Ch200 验收线。下一步进入 Task 195：跨体裁 Ch200 总验收与入口文档更新。
