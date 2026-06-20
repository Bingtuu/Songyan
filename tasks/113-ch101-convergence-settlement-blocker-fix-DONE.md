# Task 113 DONE: Ch101 收敛回滚与 Settlement 阻断修复

> **Phase**: V5.0 Phase 4 — 150 章规模化验证前置修复
> **状态**: ✅ 完成
> **完成日期**: 2026-06-20

---

## 结论

Task 113 已修复 Ch101 暴露的收敛回滚与 settlement 边界阻断问题。修复后，Ch101 通过 `run-90e08243` 恢复 `accepted + settlement + summary` 基线，Task 114 可以继续以 Ch102-Ch150 为验证范围推进。

本任务不是绕过 QualityGate 或伪造 settlement 成功，而是修复 revision/rewrite 劣化后的最终版本选择、head 指向、HumanGate、QualityGate、SettlementExtractor 和 run logger 的状态契约。

---

## 背景事故

首次 Task 113 长跑窗口在 Ch101 熔断：

| 项 | 值 |
|----|----|
| Run ID | `run-6b462cb9` |
| 失败章节 | Ch101 |
| 失败阶段 | `settlement_review` |
| 关键现象 | `revision_rebound_detected` 后 final head 未稳定指向最佳可接受版本 |
| 数据状态 | `chapter_heads.accepted_version_id=NULL`，settlement/summary 被阻断 |

关键判断：Task 111d 的事实源保护是正确的，`_skip_settlement=True` 不能被记为成功。需要修复的是收敛失败后的 best version 回滚与状态一致性。

---

## 修复内容

1. **best version/head 选择收敛**
   - 修复 revision rebound 后的 final version 选择。
   - 禁止 abandoned 或劣化版本成为最终 accepted 候选。
   - 保证 `current_version_id`、`_best_version_id`、`_score_card`、`_quality_gate_passed` 指向同一最终候选。

2. **QualityGate/HumanGate/Settlement 契约对齐**
   - best version 可接受时走正常 accept + settlement + summary。
   - best version 不可接受时停在明确阻断状态，不产生半提交。
   - HumanGate 不把 `_skip_settlement=True` 的路径推进成成功章节。

3. **run logger 状态判定修正**
   - 区分 QG 通过、QG 收敛失败、settlement validation failed、summary 缺失。
   - 避免 skipped settlement 被记录为 successful chapter。

---

## 验证结果

| 验证项 | 结果 |
|--------|------|
| Ch101 修复回放 | `run-90e08243` |
| Ch101 accepted | ✅ 恢复 |
| Ch101 settlement | ✅ 恢复 |
| Ch101 summary | ✅ 恢复 |
| 后续 Task 114 启动条件 | ✅ 满足 |

状态板记录：

```text
Task 113 回放: Ch101 accepted + settlement + summary 已恢复 (`run-90e08243`)
```

---

## 已知限制

- 本任务只恢复 Ch101 基线，不启动 Ch102-Ch150 长跑。
- 后续 Ch102/Ch103 的 settlement 事实源问题由 Task 114a/114b2 继续处理。
- 最终 150 章规模化验证由 Task 114c 完成。

---

## 后续承接

- Task 114a：修复 Ch103 暴露的 Settlement 事实源契约缺陷。
- Task 114b：记录 Ch102/Ch103 Phase 1 熔断复核。
- Task 114b2：修复 QG 收敛阻断并完成 Ch102/Ch103 settlement 端到端验证。
- Task 114c：完成 Ch111-Ch150 分段流式验证与 DG-2。
