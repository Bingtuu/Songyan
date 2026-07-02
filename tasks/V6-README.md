# V6 Task 总索引

> **阶段**: 叙事骨架 MVP + 长篇质量度量 + 可靠长跑底盘
> **当前口径**: **V6 进行中——阶段 0（叙事骨架 MVP，Task 141-144）与阶段 A（长篇质量度量，Task 145-148 + 148z 阈值标定）工程实现均已完成并全量回归（2099 passed）**。前置 V5（V5.0/V5.1/V5.2）已完整完成并验收（Ch1-Ch150 150/150 accept，`failed=[]`，无 AutoHalt，continuity health=8.5）。V6 论证基础见 `docs/300-chapter-gap-analysis.md`，阶段规划见 `docs/v6-plan.md`，验收阈值见 v6-plan §1.4（T1-T8，⚙ 阈值已在 148z 冻结/延后）。任务编号沿用连续编号惯例（V5 收尾于 Task 140），本阶段从 **Task 141** 起连续编号（Task 141-159）。
> **最后整理**: 2026-07-01

本文是 V6 阶段任务文档的事实入口。V5 阶段事实入口见 `tasks/V5-README.md`；历史规划稿统一归档到 `archive/`，仅在追溯设计边界时查阅。V6 各任务最终状态以本文件和各 `*-DONE.md` 为准。

---

## 一句话目标

> **V6 给系统装上一根最小可用的叙事骨架（治本起点），同步建立长篇质量度量，并补足无人值守长跑底盘，验证到 Ch100-150。**
> V6 不承诺"完整高质量 300 章"，那是 V7 的目标（见 `docs/v7-vision.md`）。

根因认知（来自 `docs/300-chapter-gap-analysis.md` §1）：orphan 累积、文学质量无指标、长程伏笔失效，都是**缺自顶向下叙事架构**这一根因的下游症状。因此 V6 把"建最小叙事骨架"提为阶段 0，置于度量与末端治理之前。

---

## 阶段验收判定（§1.3 N/D/S/R/V）

V6 通过 = 同时满足以下五项（阈值与术语见 `docs/v6-plan.md` §1.4，标 T1-T8）：

| 维度 | 判据 |
|------|------|
| **N（骨架）** | 项目可携带全书大纲/弧规划；GoalPlanner 输入包含弧上下文；Ch1-Ch50 至少一条主线线索完成 T1 定义的可追溯状态跃迁 |
| **D（度量）** | orphan 绝对量、新 critical 产生速率、质量债、文学趋势、弧级伏笔兑现率五类长期指标入库且可在 `songyan report`/`songyan metrics` 查看 |
| **S（源头收敛）** | 满足 T6 的 orphan 斜率下降 + 归因判据（用"新 critical 产生速率下降"证明非靠录入丢弃） |
| **R（可靠）** | 单条命令无人值守完成 Ch1-Ch100，中途人为 kill 后可 run 级 resume 续完 |
| **V（验证）** | 在 V5.2 + 骨架管线上取得 Ch1-Ch150 连续运行证据（非旧 `run-a2bed648`），全程满足 T3/T4/T5 红线 |

---

## Task 状态

> 状态口径：`◻ 规划中`（有规划稿，未开工）/ `🔄 进行中` / `✅ 完成`（有 `*-DONE.md`）/ `⚠️ 条件完成`。

### 阶段 0：最小叙事骨架 MVP（治本起点）

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 141 | 叙事骨架数据模型（StoryOutline / ArcPlan / PlotThread；拆 141a/b/c） | ✅ 完成 | `tasks/141-narrative-skeleton-data-model-DONE.md` |
| 142 | 项目创建可携带大纲 | ✅ 完成 | `tasks/142-project-outline-import-DONE.md` |
| 143 | GoalPlanner 自顶向下派生（拆 143a/b） | ✅ 完成 | `tasks/143-goal-planner-topdown-derivation-DONE.md` |
| 144 | 线索经济约束（MVP） | ✅ 完成 | `tasks/144-thread-economy-mvp-DONE.md` |

### 阶段 A：度量同步（让指标说真话 + 让骨架可判定）

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 145 | orphan 绝对量 + 新 critical 产生速率监控 | ✅ 完成 | `tasks/145-orphan-and-critical-rate-metrics-DONE.md` |
| 146 | 质量债账本 | ✅ 完成 | `tasks/146-quality-debt-ledger-DONE.md` |
| 147 | 文学质量趋势化 | ✅ 完成 | `tasks/147-literary-quality-trend-DONE.md` |
| 148 | 弧级伏笔兑现率 + 长程伏笔台账 | ✅ 完成 | `tasks/148-arc-foreshadowing-fulfillment-DONE.md` |
| 148z | 阶段 A 出口：阈值标定报告（T3/T4/T5/T6/T8 冻结） | ✅ 完成 | `tasks/148z-stage-a-threshold-calibration-DONE.md` |

### 阶段 B：末端治理（缓解症状）

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 149 | 录入侧降级（超额 critical 转候选，非硬丢弃；拆 149a/b） | ✅ 完成 | `tasks/149-input-side-demotion-DONE.md` |
| 150 | `_infer_setting_category` 收紧（双命中 + 去硬编码主角名） | ✅ 完成 | `tasks/150-infer-category-tightening-DONE.md` |
| 151 | MR 上限自适应 + 相关性排序（拆 151a/b） | ✅ 完成 | `tasks/151-mr-adaptive-cap-and-relevance-DONE.md` |
| 152 | critical 显式 resolve/作废出口（拆 152a/b） | ✅ 完成 | `tasks/152-critical-explicit-resolve-abandon-DONE.md` |

> **阶段 B 工程实现已收口**：Task 149-152 全部合入主干，`resolved`/`abandoned` 为 critical 设定提供显式回收出口，与逾期归档在 metrics 中可区分。Ch1-Ch50 Layer 3 复跑验证（T6b P1=0）待 Task 157 执行。

### 阶段 C：工程加固（无人值守长跑）


| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 153 | run 级断点续跑 | ◻ 规划中 | `docs/v6-plan.md` §3 阶段 C |
| 154 | LLM 限流感知与全局预算 | ◻ 规划中 | `docs/v6-plan.md` §3 阶段 C |
| 155 | 失败隔离策略 | ◻ 规划中 | `docs/v6-plan.md` §3 阶段 C |
| 156 | 运行中 DB 维护 | ◻ 规划中 | `docs/v6-plan.md` §3 阶段 C |

### 阶段 D：长窗口验证

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 157 | Ch1-Ch50 集成验证 | ◻ 规划中 | `docs/v6-plan.md` §3 阶段 D |
| 158 | Ch1-Ch100 长跑验证 | ◻ 规划中 | `docs/v6-plan.md` §3 阶段 D |
| 159 | Ch1-Ch150 治理管线复现 | ◻ 规划中 | `docs/v6-plan.md` §3 阶段 D |

---

## 依赖关系与执行纪律

```
阶段0（骨架 141-144）┐
                     ├─► B（末端治理 149-152）─► D 部分（157 Ch50）
A（度量 145-148）─────┘                              │
                     └─────► C（工程 153-156）──────►┴─► D（158 Ch100, 159 Ch150）
```

- **阶段 0 与 A 同期启动**：度量需要骨架提供的主线对象来定义弧级指标。
- **阶段 A 出口先产标定报告**：用 138n/138k 历史 DB 复算校准全部 ⚙ 阈值（T3/T4/T5/T6/T8）并冻结为 V6 正式口径，**必须先于任何末端治理**。
- **阶段 B 必须在骨架 + 度量落地后**：否则无法判定 orphan 下降是骨架之功还是录入丢弃的假象。
- C 可与 B 部分并行；158/159 长跑必须在骨架 + B + C 都合入后。
- 每个阶段出口未达标则不进入下一阶段。

---

## 阈值校准依赖（历史 DB，已确认存在）

阶段 A 的 ⚙ 阈值标定依赖以下历史数据库，已在 `.tmp/` 确认存在，不得清理：

| 用途 | 文件 |
|------|------|
| 138n Ch1-Ch30 重跑基线（orphan 斜率、health 8.5/P1=0） | `.tmp/task138n_ch1_ch30_rerun.db` |
| 138k Ch1-Ch30 长窗口 rehearsal 基线（T7 新 critical 速率） | `.tmp/task138k_ch1_ch30_rehearsal_20260629.db` |

---

## V6 明确不做（划归 V7）

| 项 | 归属 |
|----|------|
| 满 Ch300 渐进验证 | V7 |
| enforce 门禁默认化 | V7（V6 只做度量与自适应预研） |
| 题材泛化（数值 allowlist / 设定簇外置为 genre 配置） | V7（可选） |
| 文学质量的"闭环修复"（不止诊断、能驱动改写） | V7 |

---

## 文档入口

- V6 论证基础：`docs/300-chapter-gap-analysis.md`
- V6 阶段规划与 Task 141-159 路线图：`docs/v6-plan.md`
- V7 构想：`docs/v7-vision.md`
- V5 阶段事实入口：`tasks/V5-README.md`
- 项目状态：`docs/STATUS.md`
- 文档路由：`docs/INDEX.md`
