# Task 135: 设定回收与连续性健康分治理

> **类型**: 代码修复 / 策略调优  
> **日期**: 2026-06-27  
> **前置**: Task 109（SettingDeduplication + ForeshadowingPressure）、Task 118（ContinuityAuditor Health 治理）、Task 129（enforce 模式 Ch1–Ch50 验证）  
> **目标**: 抑制 orphaned settings 的累积速度，修复 continuity health score 在中段快速跌至 0.0 的问题，使 enforce 模式能够稳定跑过 Ch1–Ch50。

---

## 1. 背景与问题

`Task 129` enforce 模式验证（`run-89d7a2d4`）显示：

| 检查点 | 健康分 | Orphaned | Forgotten | StateMismatch | OverdueShadow |
|--------|--------|----------|-----------|---------------|---------------|
| Ch3 | 10.00 | 0 | 0 | 0 | 0 |
| Ch6 | 7.40 | 7 | 0 | 0 | 0 |
| Ch9 | 1.20 | 12 | 0 | 0 | 0 |
| Ch12 | 0.00 | 21 | 2 | 0 | 0 |
| Ch15 | 0.00 | 27 | 2 | 0 | 2 |

- `orphaned_settings` 从 Ch6 的 7 个快速上升到 Ch15 的 27 个。
- continuity health score 在 Ch9 跌至 1.2，Ch12/Ch15 跌至 0.0。
- 在 observe 模式下，这些问题仅作为 human_marks 记录；在 enforce 模式下，`health_low_score_halt` / `health_low_streak_halt` 可能被触发（当前默认 observe 未触发）。

---

## 2. 根因假设（Brainstorming）

### 假设 A：SettingEvaporator 未正确回收低置信度设定
部分设定在引入后长期未被引用，但 confidence 衰减不足，未被 archive。

### 假设 B：ContinuityAuditor 对 “orphaned” 的定义过严
任何在 N 章内未被复用的设定都被标记为 orphaned，而长篇小说中某些设定本就需要较长时间回收。

### 假设 C：CreativeDirector / ChapterGoal 未给 Writer 提供足够的设定回收提示
Writer 不知道哪些设定需要在本章回收，导致设定被“引入即遗忘”。

### 假设 D：健康分加权不合理
orphaned 单一指标权重过高，导致健康分随设定数量线性下降，掩盖了其他维度表现。

---

## 3. 修复策略

1. **设定回收窗口动态化**：
   - 根据设定类型（道具、关系、伏笔、世界观规则）设置不同的回收期望窗口。
   - 世界观规则类允许更长窗口（20–30 章），道具/伏笔类窗口较短（5–10 章）。

2. **CreativeDirector 增加设定回收提示**：
   - 在 `creative_brief` 中显式列出“本章需回收的活跃设定清单”。
   - 对逾期未回收的设定给出降级建议（archive 或在本章触发回收）。

3. **SettingEvaporator 调优**：
   - 降低 orphaned 设定的 archive 阈值，但保留 `source_version_id` 可追溯。
   - 对连续 3 次 continuity 检查未被引用的设定自动标记为 `stale`，降低其 context 预算权重。

4. **ContinuityAuditor 评分校准**：
   - 引入非线性加权：orphaned 数量超过 10 后边际扣分递减，避免健康分快速归零。
   - 区分“可接受 orphaned”（世界观背景设定）与“应回收 orphaned”（伏笔/道具）。

5. **Writer prompt 增加回收约束**：
   - 要求 Writer 在章节中至少回收 1–2 个近期引入的设定或伏笔。

6. **回归测试**：新增 continuity health 趋势测试、SettingEvaporator archive 阈值测试、CreativeDirector 回收提示测试。

---

## 4. 验收标准

- [ ] `pytest` 新增 8–12 个测试，覆盖设定回收窗口、健康分加权、Evaporator archive 策略。
- [ ] enforce 模式 Ch1–Ch20 验证中，Ch15 时 `orphaned_settings` 增长速率 ≤ Ch12 时的一半（相对改善）。
- [ ] enforce 模式 Ch1–Ch20 验证中，continuity health score 不再跌至 0.0（目标 ≥ 3.0）。
- [ ] 不破坏 observe 模式下 `run-a2bed648` 的 continuity 路径。
- [ ] `ruff check src/ tests/` 通过。
- [ ] 输出 `tasks/135-setting-recycling-and-continuity-health-governance-DONE.md`。

---

## 5. 依赖关系

```
Task 109 SettingDeduplication + ForeshadowingPressure ──┐
Task 118 Continuity Health 治理 ────────────────────────┼──► Task 135 设定回收与健康分治理
Task 129 enforce 验证 ──────────────────────────────────┘   （为 V5.2 enforce 默认启用提供证据）
```

---

## 6. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 回收窗口放宽导致伏笔被遗忘 | 长期连贯性受损 | 对伏笔类型保持较短窗口 |
| archive 阈值降低导致有用设定丢失 | 后续章节无法引用 | archive 后保留检索入口，仅在 context 中降级 |
| 健康分加权调整掩盖真实问题 | enforce 模式延迟触发 | 保留原始 raw counts 在 report 中可观测 |

---

## 7. 交付物

- `tasks/135-setting-recycling-and-continuity-health-governance-DONE.md`
- SettingEvaporator / ContinuityAuditor / CreativeDirector / Writer 相关代码改动
- 新增测试文件
- enforce 模式 Ch1–Ch20 验证报告
