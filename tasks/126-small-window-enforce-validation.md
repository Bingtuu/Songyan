# Task 126: 候选硬门禁 enforce 模式小窗口实跑验证

> **日期**: 2026-06-26
> **类型**: V5.1 实跑验证
> **状态**: **DONE**
> **前置**: Task 125（阈值调优）已完成
> **目标**: 在干净新项目上以 `gate_mode="enforce"` 跑通 Ch1-Ch20，验证 Task 125 调优后的阈值不会误伤正常长跑。

---

## 1. 目标

1. 创建一个新的干净项目（或与 `run-a2bed648` 同配置的新项目）。
2. 使用 Task 125 调优后的候选 enforce 配置跑 Ch1-Ch20：
   - `health_low_p1_halt`: `min_absolute=50`, `anomaly_factor=1.8`
   - `health_low_streak_halt`: `audit_window=3`, `p1_limit=250`
   - `health_low_absolute_score_halt`: 第一次实跑后因健康分从初始 10.0 正常下跌到 5.2 误触发，已临时禁用，待后续专门设计开局期鲁棒策略。
3. 观察是否出现 gate 触发 / AutoHalt。
4. 若 20/20 成功且 0 gate 触发，认为阈值在干净小窗口上验证通过。
5. 若触发 gate，分析原因并决定是否需要继续调优。

---

## 2. 执行方式

由于 CLI `songyan run` 暂未暴露 `--gate-mode`，本次验证通过直接调用 `run_project_pipeline(..., gate_config=...)` 执行，并记录 run_id。

---

## 3. 验收标准

- [ ] 生成新的 run_id，Ch1-Ch20 全部进入 completed 或 gate 触发原因被记录。
- [ ] 若成功：20/20 success，gate_triggered 0 次，ContextEmergency/AutoHalt 在预期范围内。
- [ ] 若 gate 触发：输出触发章节、原因、对应 continuity report，供人工复核。
- [ ] 全量 pytest / ruff 不受影响。

---

## 4. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 早期章节因铺垫期 P1 低而触发 anomaly gate | 中等 | 使用 `min_absolute=50` 与 `anomaly_factor=1.8`，正常情况下不应触发 |
| health_score 从初始高值跌落到 2.0 触发 score_drop | 低 | 首次审计点前无 previous_score，不触发；后续需观察跌幅是否 ≥2.0 |
| LLM 实跑成本与时间 | 中等 | 仅 Ch1-Ch20，约 20-30 分钟 |
| enforce 触发后 run 暂停 | 低 | 这正是验证目标，捕获后人工复核 |

---

## 5. 实跑结果

- **项目 ID**: `c1b7b6d73c0d4428a58b1175f3316273`
- **Run ID**: `run-13bb5303`
- **最终状态**: `partial`（Ch1–Ch19 成功，Ch20 因 QG false block 失败）
- **总耗时**: 6587 秒（约 1 小时 50 分钟）
- **Gate 触发**: **0 次**
- **Continuity audit 点 P1 计数**: Ch3=0, Ch6=0, Ch9=1, Ch12=3, Ch15=9, Ch18=13
- **ContextEmergency**: 未出现

## 6. 关键结论

1. 在禁用 `health_low_absolute_score_halt` 后，Ch1–Ch19 未出现任何 gate 误触发，`health_low_p1_halt` 与 `health_low_streak_halt` 的调优阈值对干净小窗口是安全的。
2. `health_low_absolute_score_halt`（health_score 相对跌幅 ≥2.0）在新项目上会误伤开局期正常下跌，不适合直接启用。
3. Ch20 失败来自 `settlement_extractor_node.qg_false_blocked`，属于既有 QG false 拦截机制，与本次 enforce 验证无关。

## 7. 下一步

- **Task 127（建议）**: 彻底移除或重构 `health_low_absolute_score_halt`，例如改为“仅在 health_score 低于历史最低值且 P1 同步激增”时才触发。
- 在更大窗口（Ch1–Ch50）或跨项目上复用本次配置，进一步验证 `health_low_p1_halt` / `health_low_streak_halt` 的泛化性。
