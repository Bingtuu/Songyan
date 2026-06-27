# Task 129: enforce 模式 Ch1–Ch50 验证 — DONE

> **类型**: 实跑验证  
> **日期**: 2026-06-27  
> **运行ID**: `run-89d7a2d4`  
> **项目ID**: `3cf71586df2a4b5c9170d9b1a5f059cf`  
> **状态**: **条件完成** — 收集到 enforce 模式在中段章节的真实触发证据，未跑通 Ch1–Ch50。

---

## 1. 目标回顾

在 Task 128 修复后的稳定 baseline 上，以 `gate_mode="enforce"` 跑通 Ch1–Ch50，验证调优后的阈值在中段章节不误伤正常长跑。

## 2. 实跑结果

- **实际完成**: Ch1–Ch15（共 15 章）。
- **终止状态**: `paused`。
- **终止原因**: `quality_gate_fail_streak`（Chapter 13、14、15 连续 quality gate 失败）。
- **总字数**: 46,160 字。
- **总耗时**: 58m 11s。
- **平均每章耗时**: 3m 52s。

## 3. 关键指标

| 指标 | 实际值 | 验收标准 | 是否达标 |
|------|--------|----------|----------|
| 覆盖章节 | Ch1–Ch15 | Ch1–Ch50 | ❌ |
| AutoHalt 次数 | 1 | 0 | ❌ |
| Gate 触发次数 | 0 | ≤ 1 | ✅ |
| Quality Gate 失败 | 4 章（Ch3, Ch11, Ch14, Ch15） | 0 | ❌ |
| Convergence 失败 | 4 章 | 0 | ❌ |
| Settlement 失败 | 4 章 | 0 | ❌ |
| Degraded accept | 0 章 | 0 | ✅ |
| ContextEmergency | 0 次 | ≤ 3 | ✅ |
| Failed 章节 | 0 | 0 | ✅ |

## 4. AutoHalt 根因

Chapter 13、14、15 连续 `quality_gate_passed=False`，满足 streak 条件。质量门失败章节详情：

| Ch | 失败原因 | 字数比 | 预算 | 可读性 | 连贯性 | 总分 |
|----|----------|--------|------|--------|--------|------|
| 3 | readability | 1.20 | 0.871 | 0.2065 | 0.8500 | 0.5766 |
| 11 | coherence_major | 0.81 | 0.958 | 0.8400 | 0.7000 | 0.6710 |
| 14 | readability, coherence_major | 1.19 | 0.927 | 0.3355 | 0.7000 | 0.5332 |
| 15 | readability | 1.01 | 0.877 | 0.3425 | 0.8500 | 0.6900 |

## 5. 暴露的关键问题

1. **Writer 结构输出单一**：所有章节的 `scenes_count=1`，低于 prompt 要求的 2+ 场景结构。
2. **角色状态表为空**：`character_states` 与 `numerical_ledgers` 均为 0 条。
3. **Orphaned settings 快速累积**：从 Ch6 的 7 个上升到 Ch15 的 27 个。
4. **Continuity health 持续恶化**：Ch9 1.2 → Ch12/Ch15 跌至 0.0。
5. **Settlement 失败章未建立摘要**：Ch3、Ch11、Ch14、Ch15 无 `summary_id`。
6. **质量门与 continuity health 存在错位**：Ch12 health 0.0 仍通过 QG，Ch14/15 因可读性失败。

## 6. 交付物

- 实跑日志：`logs/chapter_runs/run-89d7a2d4.jsonl`
- 量化报告：`docs/reports/task-129-enforce-validation-report.md`
- 报告脚本：`scripts/generate_task129_report.py`
- 数据库状态：`songyan.db`，project_id `3cf71586df2a4b5c9170d9b1a5f059cf`

## 7. 验证

```powershell
ruff check src/ tests/ scripts/generate_task129_report.py  # passed
python -m pytest tests/ -q                                 # 1856 passed, 2 skipped, 1 xfailed
```

## 8. 结论

本次 enforce 模式 Ch1–Ch50 验证 **未跑通**，但成功收集了 enforce 模式在中段章节真实触发的证据。问题集中在 Writer 结构输出、Settlement 提取、设定回收与连续性维护四个环节。该结果将作为 Task 130 `gate_mode` 默认模式决策的关键输入：在默认路径上继续推荐 `observe` 模式，避免当前 enforce 阈值在 V5.1 闭包阶段阻断用户。

---

*原始规划稿见 `tasks/129-enforce-mode-ch1-ch50-validation.md`。*
