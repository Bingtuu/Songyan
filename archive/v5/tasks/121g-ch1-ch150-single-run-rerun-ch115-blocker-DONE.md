# Task 121g DONE: Ch1-Ch150 Single-Run Rerun and Ch115 Blocker

> **日期**: 2026-06-21
> **类型**: V5.1 preflight / full single-run evidence
> **状态**: DONE
> **前置**: Task 121f 已修复 Ch18 CreativeDirector JSON parse failure 状态污染，并通过 `run-058fb9de` Ch1-Ch18 聚焦验证。

---

## 1. 任务边界

本任务目标是用干净项目重跑 Ch1-Ch150 single-run，验证 Task 121c/121e/121f 修复后的真实长跑瓶颈。

不做：

- Prompt 调优。
- workflow 阈值调整。
- Ch115 修复实现。
- 将 partial 结果包装为 Ch1-Ch150 已完成证据。

---

## 2. 运行配置

| 项 | 值 |
|----|----|
| project_id | `7950dbf3b70c468695e5bfe528d66acf` |
| run_id | `run-0fd1456e` |
| task tag | `task121g` / `ch1-ch150-full-single-run` |
| mode | `webnovel_intense` |
| genre | `scifi` |
| 章节范围 | Ch1-Ch150 |
| wrapper timeout | `86400` 秒 |
| JSONL | `logs/chapter_runs/run-0fd1456e.jsonl` |
| wrapper stdout | `logs/task121g/songyan-task121g-ch1-ch150-full-single-run-20260621-203623.out.log` |
| wrapper stderr | `logs/task121g/songyan-task121g-ch1-ch150-full-single-run-20260621-203623.err.log` |

启动前已完成历史日志归档、缓存清理、旧 WAL/SHM 清理、SQLite 完整性检查和残留进程检查。

---

## 3. 运行结果

本次 single-run 未达成 150/150，结果为 `partial`。

| 项 | 结果 |
|----|------|
| final_status | `partial` |
| completed_chapters | Ch1-Ch114 |
| failed_chapters | `[115]` |
| 首个失败点 | Ch115 |
| 运行时长 | 约 `40811s`，约 `11.3` 小时 |

确认已越过的历史阻断：

- Ch5 rewrite fallback settlement skip 阻断已解除。
- Ch8 settlement 伏笔同章预计回收阻断已解除。
- Ch18 CreativeDirector stale error 状态污染阻断已解除。

---

## 4. Ch115 阻断原因

Ch115 的失败表象：

```text
success=false
error_stage=human_review_required
settlement_success=false
settlement_needs_human_review=true
summary_id=null
summary_success=false
skip_settlement=false
```

进一步定位后确认：**Ch115 不是 SettlementExtractor 自身校验失败**。

日志中未出现：

```text
settlement_extractor_node.contract_snapshot
settlement.validation_failed
settlement.applied
```

实际触发链是质量门在 settlement 前将状态路由为 `human_review_required`：

```text
Ch115 rewrite 输出 7771 字
-> 截断到 6062
-> 最终硬截断到 4200
-> quality_gate_passed=false
-> convergence_failed=true
-> _new_issues_introduced 非空
-> status=human_review_required
-> 未进入 settlement_extractor
-> run partial
```

关键指标：

```text
overall_score=0.7335
length=0.6
budget=0.7058
coherence=0.85
momentum=0.8
readability=0.6315
critical=0
```

判断：

- 总分没有崩溃，`overall_score=0.7335`。
- 主要质量风险是 rewrite 字数失控、硬截断后的结构风险和 `readability=0.6315` 偏低。
- 工程风险是 rewrite 后的 `_new_issues_introduced` 状态疑似未随最终版本刷新或清理，旧 revision 的新问题污染了最终质量门判断。

---

## 5. 质量抽查结论

已抽查 Ch2、Ch8、Ch15、Ch18、Ch21。

结论：

- 可读性整体未崩，主线、动作压力和关键线索延续正常。
- Ch1-Ch21 评分没有低于 `0.6` 的章节，平均可读性约 `0.8486`。
- 中段开始出现预算压力、素材形态趋同和正文元标记泄漏风险。
- Ch18 曾出现正文元标记：

```text
<!-- 新设定:空白体巡逻者|存在体|城市核心系统 -->
```

该问题不阻断本次长跑，但应进入后续 Prompt/正文清洗调优范围。

---

## 6. 结论

Task 121g 完成了新的干净 single-run 证据链，但结论是 **未达成 Ch1-Ch150 一次性完成目标**。

本次有效推进：

- 将 single-run 真实瓶颈从 Ch18 推进到 Ch115。
- 取得 Ch1-Ch114 连续成功证据。
- 定位首个新阻断为 Ch115 质量门 human review，而非 settlement extractor 校验。

---

## 7. 下一步

建议创建 Task 121h，聚焦修复 Ch115 暴露的质量门/重写状态污染问题：

- 明确 rewrite 后 `_new_issues_introduced` 的生命周期。
- 确保最终版本重新评分后清理旧 revision 的新问题状态。
- 复核 rewrite 超长输出和硬截断后的 quality gate 路由。
- 修复后先聚焦重跑 Ch115，再重跑 Ch1-Ch150 single-run。
