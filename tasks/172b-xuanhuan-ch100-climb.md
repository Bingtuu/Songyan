# Task 172b — 非 sci-fi 体裁 Ch100 爬坡验证

> **状态**: ◻ 规划中（待 172a.7 + 172a.p 短窗口验收全绿后开工）
> **归属**: V8.2 多体裁章数爬坡（V8 验收 **V 维度**）
> **前置**: 172a.7 短窗口质量同标 + 172a.p S 维度达标（overdue<5）
> **候选体裁**: **xuanhuan**（首选）

---

## 1. 目标与验收（V 维度）

V8-README V 维度判据：

> 至少一个非 sci-fi 体裁稳定推进到 **Ch100**，且前 100 章质量指标**不劣于 sci-fi Ch1-Ch100 基线**。

172b 出口 = 同时满足：

| 项 | 判据 | 对标 sci-fi Ch1-100 基线 |
|---|---|---|
| 完成度 | Ch1-100 全 accepted（isolate 失败 ≤ 明确记录且非系统性） | 100/100 |
| budget | budget_used 峰值 < 1.0；无 `context_emergency_budget_ratio_halt` | 长期 <1.0 |
| ContextEmergency | 偶发不连续 | 偶发 |
| T9 hard | = 0 | 0 |
| 连续性 | critical orphan = 0；health median 不持续退化 | median ≥8.5, critical orphan 0 |
| **S（伏笔）** | overdue foreshadowing 受控（172a.p horizon floor 在 Ch100 尺度仍有效） | — |

> **质量同标纪律**：不因"玄幻状态密度高"放宽任何硬指标。撞墙则路由 `172b.p` 定点修复，不放宽阈值、不做 prompt 工程。

## 2. 为什么选 xuanhuan

1. **验证数据最厚**：xuanhuan 已有 end15（base=13000/15000 两轮）+ floor12 三次实跑，budget/CED/overdue 都有基线。
2. **最难的体裁**：genre_rules 比 scifi 贵 +79.9%（172a.1），状态密度最高（功法/境界/势力/法宝）。在最难体裁上证明 Ch100 = V 维度最强证据。
3. **S 修复是 xuanhuan 特化的**：172a.p horizon floor=12 专为 xuanhuan 密集埋伏笔设计，Ch100 尺度是它的真实考验。
4. **模板骨架就绪**：`project_templates/xuanhuan/outline.json` 已含 9 arc（覆盖 Ch1-250）+ 3 thread，Ch100 落在 arc 3 边界（Ch76-100），全程 `has_skeleton=True`。

## 3. 实施（复用既有基础设施，不新增节点）

### harness

新建 `scripts/run_172b_ch100_climb.py`，复用 `run_158_ch1_ch100.py` 的编排（无人值守 + kill/resume + 逐章 metrics + 报告），但：

- 项目初始化改用 `ProjectInitializer.from_template("xuanhuan")`（自动导入 9-arc/3-thread 骨架），**删掉 run_158 的手搓 `_build_outline`**。
- `gate_config = GateConfig.for_mode("enforce")`，`on_failure="isolate"`。
- runtime_profile 由 pipeline 按 genre 自动加载（xuanhuan base=15000, floor=12 生效）。
- 分段跑（每 25 章一段，即 arc 边界），段间读 DB 汇总，避免单次超长阻塞。

### 分段爬坡计划

```
段1 Ch1-25   (arc0)  → 汇总 budget/overdue/health → 无 halt 才进段2
段2 Ch26-50  (arc1)  → 汇总 → gate
段3 Ch51-75  (arc2)  → 汇总 → gate
段4 Ch76-100 (arc3)  → 汇总 → 出 Ch100 报告
```

每段结束跑一次证据收集（continuity_reports、context_snapshots、foreshadowings、review_reports CED），任一段触发 halt 或指标劣化即停并路由 172b.p。

### 证据 & 报告

产出 `docs/reports/172b-xuanhuan-ch100-climb.md`：逐段 budget 曲线、ContextEmergency 频率、overdue 轨迹、CED vs scifi Ch1-100 基线、health 趋势、失败清单。

## 4. 风险与撞墙路由（172b.p 预案）

| 风险 | 触发信号 | 172b.p 预案（不放宽口径） |
|---|---|---|
| 长尺度 budget 溢出 | Ch50+ budget_used 逼近 1.0 或 halt | ramp_per_chapter 按体裁微调 / genre_rules 内容精简（层 3），非分区权重 |
| overdue 反弹 | Ch100 overdue >> 5 | horizon floor 随章号动态 / 主动回收调度（评估是否超 MVP） |
| 连续性退化 | critical orphan > 0 / mismatch 持续 | continuity 容忍度按体裁（172a.6 已有 Profile 字段） |
| health 持续下滑 | median < scifi 基线 | 定点诊断，判定真退化则新开修复 Task |

## 5. 依赖

- **硬前置**：172a.7 报告全绿（scifi/wuxia/urban 回归 + CED 基线）+ 172a.p overdue<5 实证。**未达标不开工**（V8-README 纪律："172a.7 证明短窗口质量达标后才启动 172b"）。
- 若 xuanhuan Ch100 达标 → 172c 选 wuxia 做第二体裁（wuxia --end 10 已证 0 halt、peak 0.958）。
