# Task 148z: 阶段 A 出口 — 阈值标定报告（T3/T4/T5/T6/T8 冻结）

> **Phase**: V6 阶段 A 出口（必须先于任何末端治理 / 阶段 B）
> **优先级**: P0（阶段 A 通过的硬门槛；Task 159 的 D/S 维度核对依赖它）
> **依赖**: Task 145/146/147/148（度量模块 `evals/db_metrics.py` 全部落地）
> **预计工作量**: 中（分析 + 报告，无新生产代码；可含一次性标定脚本）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §1.4（阈值校准纪律）、§3 阶段 A 出口

---

## Goal

用 145-148 的度量模块，对历史 DB（`.tmp/task138n_ch1_ch30_rerun.db`、`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`）复算实际分布，校准 v6-plan §1.4 全部 ⚙ 阈值（**T3/T4/T5/T6/T8**），并**冻结为 V6 正式口径**，产出 `archive/v6/reports/v6-stageA-threshold-calibration.md`。这是阶段 A 的出口交付物；没有它，Task 159 的 D（度量）与 S（源头收敛）维度无法逐条核对。

## Context

- v6-plan §1.4 标注 ⚙ 的阈值需"在阶段 A 出口用历史 DB 复算校准后冻结"，并规定纪律：若首版值明显不合理（如 138n 基线本身已超红线），须在标定报告记录并调整——**不允许长跑撞红线后临时放宽**。
- 145-148 每个任务只"在标定报告中引用"，此前**无任务实际产出该报告**（review 发现 C2）。本 Task 收口。
- 数据可得性（各 ⚙ 阈值的真值源不同，见下表）已在 145/146/147/148 的 Context 中核实。

## 各 ⚙ 阈值的标定口径与数据源

| 阈值 | 含义 | 数据源 | 本 Task 动作 |
|------|------|--------|--------------|
| **T3** 文学趋势红线（W=5 均值相对前 10 章基线降 ≥20%） | Task 147 `detect_literary_trend` | 138n `literary_observations`（真值，四维度分布：literary_quality 6.2–8.2、character_autonomy 5.5–9.0、conceptual_grounding 5.0–8.5、fissure_preservation 6.0–9.5） | 复算四维度逐章趋势，检验 20%/W=5/baseline-10 是否会在健康 run 上误伤；据实冻结或调整 |
| **T4** 质量债红线（50 章窗 degraded ≤20% 且 convergence ≤10%） | Task 146 `compute_quality_debt` | **不可完整历史标定**：degraded/convergence 不在历史数据；qg_false 可经 jsonl 适配器从 `.tmp/*_per_chapter_metrics.jsonl` 近似 | degraded/convergence 子阈值标 **provisional**，冻结推迟到阶段 D 首窗（Task 157）实测；报告给出 qg_false 参考分布并注明缺口 |
| **T5** DB/性能红线（Ch100 DB ≤300MB；扫描查询 ≤基线 1.5×） | 文件体积 + 查询计时探针 | 138n `.db` 文件大小（v6-plan 记 150 章基线 ≈196MB）+ 对 continuity 扫描查询计时 | Stage A **只记录基线**（文件大小 + 典型查询耗时）；≤300MB@Ch100 与 ≤1.5× 红线在长跑（Task 156/158）验证，报告显式说明该延后 |
| **T6** orphan 斜率 + 归因 | Task 145 orphan 曲线 + T7 曲线 | 138n（orphan 斜率基线）、138k（T7 基线） | 冻结 T6(a) orphan 斜率基线与 ×0.5 目标；确认 T6(b) P1=0 口径；T6c 比值"T7 降幅 ≥ orphan 斜率降幅 50%"给出**手工计算方法**；T6c"被降级 critical ≤15%"子句标注**依赖 Task 149、Stage A 不评估** |
| **T8** 趋势窗口 N=5 | 结构性 | — | 确认 N=5（与 gate streak_window=3 区分），无需数值标定，冻结 |

## In Scope（必须完成）

- [ ] 一次性标定脚本（`scripts/` 或 `evals/` 下，一次性，不入 CI lint）：对 138n/138k 用 `DATABASE_URL` 覆盖运行 145-148 的 collector（orphan/T7/文学趋势/伏笔全局台账），并用 jsonl 适配器算 qg_false 参考分布。
- [ ] `archive/v6/reports/v6-stageA-threshold-calibration.md`：
  - 逐 ⚙ 阈值：历史实际分布/斜率 + 首版阈值是否合理 + **冻结值或调整后值** + provisional/延后标注（T4 degraded/convergence、T5 红线、T6c ≤15% 子句）。
  - 复现"orphan 总量持续上涨""质量债累积（qg_false 口径）"等被旧 health 指标掩盖的现象（阶段 A 出口要求）。
  - 明确列出"本报告冻结哪些、延后哪些、依赖后续哪个 Task"。
- [ ] 把冻结口径回写 v6-plan §1.4（把 ⚙ 首版值替换/确认为冻结值，或在 §1.4 追加"已冻结/延后"标注），保持 v6-plan 为唯一阈值出处。

## Out of Scope（明确不做）

- 不新增生产代码（只用 145-148 已交付模块 + 一次性脚本）。
- 不做阶段 B 治理动作。
- degraded/convergence 与 T5 红线的实测冻结留给阶段 D（Task 157/156/158），本报告只标定可标定项、明确延后项。

## 验收标准（Acceptance Criteria）

- [ ] `archive/v6/reports/v6-stageA-threshold-calibration.md` 产出，逐条覆盖 T3/T4/T5/T6/T8（冻结或明确延后 + 依赖任务）。
- [ ] 用 138n/138k 复算的曲线数据在报告中给出（可复现命令）。
- [ ] v6-plan §1.4 已回写冻结/延后标注。
- [ ] 复现"被旧指标掩盖的退化"现象（orphan 上涨等）。
- [ ] 生成 `tasks/148z-...-DONE.md`；更新 `tasks/V6-README.md`（阶段 A 出口结论）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.4（T3-T8 + 校准纪律）、§3 阶段 A 出口
- `tasks/145..148`（度量模块）；历史 DB `.tmp/task138n_ch1_ch30_rerun.db`、`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
