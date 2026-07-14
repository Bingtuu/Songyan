# V6 阶段 A 阈值标定报告（T3/T4/T5/T6/T8 冻结）

> **归属**: Task 148z（阶段 A 出口）；日期 2026-07-01
> **数据源**: 历史库 `.tmp/task138n_ch1_ch30_rerun.db`、`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`（只读复算）
> **工具**: Task 145-148 的 `evals/db_metrics.py` collector（一次性脚本 `.tmp/v6_calib.py`）

---

## 1. 方法与项目选择

历史库含多个项目。标定用两类基线：
- **a2bed648（`project_id=e95a1fa3`，150 章，run-a2bed648）**：V5.1 里程碑长跑，用作 **orphan 斜率 / 文学趋势 / 长程伏笔** 基线（138n 与 138k 都含此项目，数值一致）。
- **rehearsal（`project_id=3bef1af8…`，30 章，run-6f2a10d3，仅 138k）**：Ch1-30 长窗口 rehearsal，用作 **T7 新 critical 速率** 基线（v6-plan 指定）。

复算命令（可复现）：
```
DATABASE_URL=sqlite:///.tmp/task138n_ch1_ch30_rerun.db songyan metrics --project-id e95a1fa3 --chapters 1-150
```

## 2. 历史实际分布（复算结果）

| 指标 | a2bed648 (150ch) | rehearsal (30ch) |
|------|------------------|------------------|
| orphan 绝对量斜率 | **6.2836 /章**（50 审计点） | 1.6323 /章（10 点） |
| orphan 总量峰值 | **912** | 52 |
| P1(critical) orphan 峰值 | **81** | 35 |
| 每章新 critical 速率 T7（均值） | 0.547 | **1.767** |
| 文学基线（前 10 章均值） | LQ 7.50 / 自主 7.77 / 概念扎根 6.10 / 裂隙 8.40 | LQ 7.54 / 7.49 / 6.51 / 8.37 |
| 文学 T3 触线维度（W=5, ≥20%↓） | **literary_quality, fissure_preservation** | 无 |
| 长程未兑现伏笔 / 其中逾期归档 | **494 / 464** | 104 / 53 |
| qg_false（jsonl 适配器） | 1/30 | 0/40 |

## 3. 被旧 health 指标掩盖的退化（阶段 A 出口要求复现）

a2bed648 是 V5.1"150/150 accept、continuity health≈8.5"的里程碑 run，但本报告的新度量揭示其真实事实源质量：
- **orphan 持续累积**：总量斜率 +6.28/章，峰值 **912** 个 orphan 设定 —— health 8.5 完全掩盖了这一线性增长。
- **critical orphan 高达 81**（T6(b) 要求全程 =0）—— 说明关键设定被大量遗忘。
- **长程伏笔失效**：494 条未兑现，其中 **464 条（94%）是逾期归档（被系统遗忘），而非真兑现**。
- **文学退化**：literary_quality 与 fissure_preservation 在 150 章内出现 ≥20% 的滑窗下滑。

结论：新度量成功让"被 health 8.5 掩盖的退化"显形，验证了阶段 A 的价值。

## 4. ⚙ 阈值冻结 / 延后

| 阈值 | 首版 | 历史依据 | 冻结口径 | 状态 |
|------|------|----------|----------|------|
| **T3** 文学趋势红线 | W=5 均值相对前 10 章基线 ≥20%↓ | a2bed648 触线（LQ/裂隙），30ch 健康 run 不触线 | **冻结 20% / W=5 / baseline=10**：能区分退化(150ch)与健康(30ch)，无健康 run 误报 | ✅ 冻结 |
| **T4** 质量债红线 | 50 章窗 degraded ≤20% 且 convergence ≤10% | degraded/convergence 历史不可得；qg_false ≈0-3%（极低） | degraded/convergence 子阈值 **provisional**；qg_false 极低无需单独门限 | ⏸ 延后至 Task 157 首窗实测冻结 |
| **T5** DB/性能红线 | Ch100 DB ≤300MB；扫描 ≤基线 1.5× | v6-plan 记 150ch 干净基线 ≈196MB；`.tmp` 多项目库 404-416MB 非干净基线 | 保留 ≤300MB@Ch100 / ≤1.5× | ⏸ 延后至长跑（Task 156/158）实测（须干净单项目基线） |
| **T6** orphan 斜率 + 归因 | (a) ≤138n×0.5；(b) P1=0；(c) 归因 | 138n 斜率 **6.2836/章**；T7 基线（138k rehearsal）**1.767/章** | (a) **目标 ≤3.14/章**（Ch50-100 窗）；(b) **P1 critical orphan=0**；(c) T7 降幅 ≥ orphan 斜率降幅 50% —— 报告手工算 | ✅ 冻结 (a)(b) + T7 基线；(c) ≤15% 子句依赖 Task 149 **延后** |
| **T8** 趋势窗口 N | N=5 | 结构性 | **冻结 N=5**（与 gate streak_window=3 区分） | ✅ 冻结 |

## 5. 冻结值汇总（回写 v6-plan §1.4）

- **T3**：20% 降幅 / W=5 / baseline=10 章 —— 冻结。
- **T6(a)**：Ch50-100 窗 orphan 总量斜率 ≤ **3.14/章**（=138n 基线 6.2836×0.5）—— 冻结。
- **T6(b)**：P1(critical) orphan 全程 =0 —— 冻结。
- **T6c**：T7 基线 1.767/章（138k rehearsal）；降幅比值报告手工核算；"被降级 critical ≤15%" 子句待 Task 149。
- **T8**：N=5 —— 冻结。
- **T4 / T5**：延后至阶段 D（Task 157 质量债 / Task 156-158 DB 性能）实测冻结；本阶段仅记录：qg_false 极低、干净 150ch DB 基线 ≈196MB（待重测）。

## 6. 数据可得性缺口（如实记录）

- **degraded_accept / convergence_failed 历史分布不可得**：仅存于全量 run 日志（V6 清理已删）；`.tmp/*_per_chapter_metrics.jsonl` 只含 qg_false。→ T4 这两项延后。
- **arc_plans 历史库不存在**：138n/138k 早于 V6 骨架 → 弧级伏笔兑现率无法历史复算，仅全局台账（494/464）可算。
- **T5 干净基线缺失**：`.tmp` 库多项目混合，非干净单项目库。

## 7. 复现附录

一次性采集脚本 `.tmp/v6_calib.py`（读三项目 + qg_false）。`songyan metrics --project-id e95a1fa3 --chapters 1-150`（`DATABASE_URL` 指向历史库）产出全六段度量报告。
