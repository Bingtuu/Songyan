# Task 172b — 非 sci-fi 体裁 Ch100 爬坡验证

> **状态**: 🔄 进行中（172a.7 + 172a.p 全绿，Ch100 爬坡实跑中）
> **归属**: V8.2 多体裁章数爬坡（V8 验收 **V 维度**）
> **前置**: 172a.7 短窗口质量同标 + 172a.p S 维度达标（overdue<5）✅
> **候选体裁**: **xuanhuan**（首选）
> **对标基线**: sci-fi Ch1-100（`.tmp/task171_ch1_ch200.db` = V7「轨道蜃景」220/220 accepted，见 §1.1）

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

### 1.1 sci-fi Ch1-100 基线（冻结对标口径）

用 172b harness 的 `_segment_metrics` 同一方法（issue 数按 `chapter_number <= up_to` 界定）从 V7 sci-fi 实跑 DB `.tmp/task171_ch1_ch200.db`（project `835afdf1…`，genre=scifi，220/220 accepted）提取，脚本 `.tmp/compute_scifi_baseline.py`，落盘 `.tmp/scifi_ch100_baseline.json`：

| checkpoint | accepted | budget_peak | before_emerg_peak | emergency | overdue | health | CED/1k |
|---:|---:|---:|---:|---:|---:|---:|---:|
| Ch25 | 25/25 | 0.989 | 1.267 | 28 | 61 | 9.2 | 9.33 |
| Ch50 | 50/50 | 0.989 | 1.267 | 32 | 110 | 9.4 | 9.28 |
| Ch75 | 75/75 | 0.989 | 1.267 | 32 | 136 | 9.9 | 9.46 |
| Ch100 | 100/100 | 0.989 | 1.267 | 32 | 168 | 10.0 | 9.13 |

**对标口径澄清**（关键，避免误判）：

1. **budget < 1.0**：sci-fi 峰值 0.989（近上限但从不 halt）。xuanhuan 峰值应同样 < 1.0、无 `context_emergency_budget_ratio_halt`。
2. **CED ≤ sci-fi 同级**：sci-fi Ch1-100 CED 稳定在 **9.13-9.46**（不随章数衰减，证明 harness CED 已正确密度归一）。xuanhuan 应 ≤ 该量级（短窗口 end15 已测 10.48，约 +14%，Ch100 尺度需实测）。
3. **overdue 用 Ch100 尺度判**：sci-fi 自身 Ch100 overdue = **168**（未完结长篇天然携带大量 open thread）。V 维度是「≥ sci-fi 基线」——xuanhuan Ch100 overdue 只要 **≤ sci-fi 同尺度（≤168）** 即达标，**不套用 S 维度 end15 的 `<5`**（那是短窗口口径）。172a.p 的 floor=12 保证 xuanhuan 不会比 sci-fi 更短视。
4. **health median ≥ sci-fi**：sci-fi Ch25-100 health 9.2→10.0。xuanhuan median 不持续退化即可。

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

### V 维度验收判定器（可证伪）

`.tmp/vdim_compare.py` 读 live xuanhuan DB，按当前爬坡深度线性插值 sci-fi 基线（`.tmp/scifi_ch100_baseline.json`），对 5 个门禁给 PASS/FAIL。**CED 用 chapter-bounded 口径**（issue 与 words 均按 `chapter_number <= up_to` 界定）——比 harness `_segment_metrics` 更严：后者 issue 计数不设章界，在 live DB 上会被 in-flight 章（如正在写的 Ch11 report）污染，判定器自算 bounded CED 规避此偏差，与冻结基线严格同口径。

| gate | 判据 | sci-fi 对标 |
|---|---|---|
| budget | xuanhuan budget_peak < 1.0 且无 halt | 峰值 0.989 |
| CED | xuanhuan CED ≤ sci-fi × 1.15（172a.7「同级」口径） | 9.13-9.46 |
| overdue | xuanhuan overdue ≤ sci-fi 同章尺度 | Ch9→61 … Ch100→168 |
| health | xuanhuan health ≥ 8.0（median 不退化代理） | 9.2-10.0 |
| completeness | accepted ≥ up_to−1（gap≤1 自动过；gap>1 转 documented-isolate 复核，不静默阻断） | 100/100 |

Ch13 早期读（`up_to≥100` 才是终判）：budget 0.938 / CED 10.12（bounded）/ overdue 0 / health 9.0 / completeness 13/13 → **五门全 PASS**（early-warning，非终判）。终判在 climb 到达 Ch100 深度时给出：`final` 以「爬坡触达 Ch100」为终态，单章瞬时 isolate 会在 completeness 门显性报 REVIEW，而非永久判 partial。

## 4. 风险与撞墙路由（172b.p 预案）

| 风险 | 触发信号 | 172b.p 预案（不放宽口径） |
|---|---|---|
| 长尺度 budget 溢出 | Ch50+ budget_used 逼近 1.0 或 halt | ramp_per_chapter 按体裁微调 / genre_rules 内容精简（层 3），非分区权重 |
| overdue 反弹 | Ch100 overdue > sci-fi 同章（>168） | horizon floor 随章号动态 / 主动回收调度（评估是否超 MVP） |
| 连续性退化 | critical orphan > 0 / mismatch 持续 | continuity 容忍度按体裁（172a.6 已有 Profile 字段） |
| health 持续下滑 | median < scifi 基线 | 定点诊断，判定真退化则新开修复 Task |

## 5. 依赖

- **硬前置**：172a.7 报告全绿（scifi/wuxia/urban 回归 + CED 基线）+ 172a.p overdue<5 实证。**未达标不开工**（V8-README 纪律："172a.7 证明短窗口质量达标后才启动 172b"）。
- 若 xuanhuan Ch100 达标 → 172c 选 wuxia 做第二体裁（wuxia --end 10 已证 0 halt、peak 0.958、CED 8.48 优于 scifi）。

## 172c 预备情报：wuxia 需要 horizon floor

wuxia --end 15 回归 DB 解剖（`.tmp/analyze_foreshadowing.py`）显示 wuxia 的 plant-time horizon **比 xuanhuan 更短**：分布峰值在 +2（8 条）/+3（8 条），max 仅 +11，overdue 达 25（end15, floor=0）。这是与 xuanhuan 相同的短 horizon 病理，且更严重。

实跑 DB 模拟 horizon floor 效果：

| floor | overdue @end10 | overdue @end15 |
|---|---|---|
| 0（现状） | 12 | 25 |
| 8 | 1 | 16 |
| 10 | 0 | 12 |
| **12** | 0 | **5** |

**结论**：172c 启动 wuxia Ch100 前，必须给 wuxia profile 设 `foreshadowing_horizon_floor`（建议 **≥12**，与 xuanhuan 同级；长窗口可能需更高）。这是 172a.p 机制的直接复用，无需新代码——只在 `_default_registry()` wuxia 条目加一行 `foreshadowing_horizon_floor=12`。
