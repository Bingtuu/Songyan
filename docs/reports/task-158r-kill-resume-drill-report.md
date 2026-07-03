# Task 158r：§1.3-R kill→resume 真实命令级演练报告

- 生成时间: 2026-07-03T23:10:29.870174
- DB: `.tmp\task158r_kill_resume.db`
- 项目 ID: `f3d962e87f804ef781c3a3c21aac8fc4`
- 章节范围: Ch1-Ch5
- Gate 模式: enforce
- on_failure: isolate
- 真实 LLM: DeepSeek API（LLM_RUN_CALL_BUDGET 未启用）

## 背景

Task 158 长跑未显式执行人为 kill，§1.3-R「中途人为 kill 后同命令 `--resume` 续完」缺命令级证据。本演练在**全新隔离 DB** 上补齐：在 Ch3 生成完成、accept 之前打断（in-flight 非边界 kill），随后 `--resume` 续完，全程走真实产品管线 `run_project_pipeline`。

## 命令时间线

### Phase 1 — 初始化 + in-flight kill

```powershell
$env:DATABASE_URL = "sqlite:///.tmp/task158r_kill_resume.db"
python scripts/run_158r_kill_resume_drill.py --init
python scripts/run_158r_kill_resume_drill.py --kill-at-chapter 3
```

- kill 前已 accept: []
- 是否被 KeyboardInterrupt 打断: 是
- kill 打断信息: `simulated in-flight kill at chapter 3`
- kill 后 run_id: `run-82bd2e07`
- kill 后 run 状态: running
- kill 后 run_state.current_chapter: Ch3
- kill 后已 accept（唯一完成事实源）: [1, 2]
- kill 后残留 checkpoint thread 数: 3

### Phase 2 — 同命令 resume 续完

```powershell
$env:DATABASE_URL = "sqlite:///.tmp/task158r_kill_resume.db"
python scripts/run_158r_kill_resume_drill.py --resume
```

- resume 复用 run_id: `run-82bd2e07`
- resume 前已 accept: [1, 2]
- resume 后已 accept: [1, 2, 3, 4, 5]
- resume 最终 run 状态: completed
- resume completed 集合: [1, 2, 3, 4, 5]
- resume failed 集合: []
- resume 前残留 checkpoint thread 数: 3
- resume 后 checkpoint thread 数: 3

> 注：`resume 前/后 thread 数` 是各阶段末尾的快照。resume **启动时**先执行了孤儿 checkpoint 清理，随后 Ch3/Ch4/Ch5 重算又写入新 thread，故终值回到 3。真正的清理证据见下方日志行。

### 孤儿 checkpoint 清理证据（resume 启动时）

来自 `.tmp/task158r_resume_phase.log`：

```
project_pipeline.resume        completed_count=2 previous_status=running resume_start=3 run_id=run-82bd2e07
project_pipeline.pruned_orphan_checkpoints pruned_count=58 run_id=run-82bd2e07
project_pipeline.chapter_start chapter_number=3 previous_summary_length=123 run_id=run-82bd2e07
```

- `resume_start=3`：以 accepted head（Ch1/Ch2）为唯一完成事实源，从 in-flight 的 Ch3 续起。
- `pruned_orphan_checkpoints pruned_count=58`：kill 遗留的孤儿 checkpoint 行被清理，in-flight 章以新 thread_id 重算。


## 关键断言

| 断言 | 期望 | 实测 | 结论 |
|------|------|------|------|
| kill 为 in-flight（Ch3 生成后 accept 前打断） | 打断=是 且 Ch3∉accepted@kill | 打断=是, Ch3∉accepted@kill | ✅ |
| resume 复用同一 run_id | kill.run_id == resume.run_id | 相同 | ✅ |
| in-flight 章被重算并最终 accept | Ch3∈accepted@final | Ch3∈accepted@final | ✅ |
| resume 续完全部目标章 | accepted@final ⊇ [1, 2, 3, 4, 5] | [1, 2, 3, 4, 5] | ✅ |
| run 最终 completed | status=completed | completed | ✅ |

## chapter_heads 终态

| Ch | status | has_accepted |
|---:|--------|:---:|
| 1 | accepted | Y |
| 2 | accepted | Y |
| 3 | accepted | Y |
| 4 | accepted | Y |
| 5 | accepted | Y |

## 结论

✅ §1.3-R 取得**真实命令级证据**：单命令无人值守运行中，人为 in-flight kill（Ch3 生成后 accept 前打断）后，同命令 `--resume` 复用同一 run_id 续跑——已 accept 章跳过、in-flight 章重算、孤儿 checkpoint 清理，最终 Ch1-Ch5 全部 accept，run 状态 completed。
