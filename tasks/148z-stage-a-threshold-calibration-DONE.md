# Task 148z DONE — 阶段 A 出口阈值标定报告（T3/T4/T5/T6/T8 冻结）

> **Phase**: V6 阶段 A 出口
> **状态**: ✅ 完成（标定报告产出 + ⚙ 阈值冻结/延后 + v6-plan §1.4 回写）
> **完成日期**: 2026-07-01
> **规划/设计**: `docs/v6-plan.md` §1.4；任务书 `tasks/148z-stage-a-threshold-calibration.md`

---

## 交付概览

用 Task 145-148 的度量模块对历史库（138n/138k）复算实际分布，校准并冻结 v6-plan §1.4 全部 ⚙ 阈值，产出 `docs/reports/v6-stageA-threshold-calibration.md`，并回写 v6-plan §1.4。

| 交付物 | 文件 |
|--------|------|
| 标定报告 | `docs/reports/v6-stageA-threshold-calibration.md` |
| 一次性采集脚本 | `.tmp/v6_calib.py`（读 138n/138k 三项目 + qg_false jsonl） |
| v6-plan 回写 | §1.4 追加"阶段 A 标定冻结"块 |

## 冻结 / 延后结论

- **T3 冻结**：20% 降幅 / W=5 / baseline=10 —— a2bed648 触线（literary_quality、fissure_preservation），30 章健康 run 不触线，口径能区分退化与健康。
- **T6(a) 冻结**：Ch50-100 窗 orphan 斜率 ≤ **3.14/章**（=138n 基线 6.2836×0.5）；**T6(b)** P1 critical orphan=0；**T6c** T7 基线=1.767/章（138k rehearsal），降幅比值手工核算，"被降级 critical ≤15%" 子句依赖 Task 149 **延后**。
- **T8 冻结**：N=5。
- **T4 延后**：degraded/convergence 历史不可得（仅 qg_false ≈0-3%）→ 延后至 Task 157 首窗实测冻结。
- **T5 延后**：DB/性能红线（≤300MB@Ch100 / ≤1.5×）延后至长跑（Task 156/158）；干净 150ch 基线 ≈196MB 待重测（`.tmp` 库多项目混合非干净基线）。

## 被旧指标掩盖的退化（阶段 A 出口要求已复现）

a2bed648（V5.1 "150/150 accept、health≈8.5" 里程碑）经新度量显形：orphan 斜率 **+6.28/章**、峰值 **912**、critical orphan **81**、长程未兑现伏笔 **494**（其中 **464=94% 逾期归档/被遗忘**）、文学 2 个维度 ≥20% 下滑。health 8.5 完全掩盖了这些退化——阶段 A 价值验证成立。

## 验证

- 报告逐条覆盖 T3/T4/T5/T6/T8（冻结或明确延后 + 依赖任务）。
- 复算命令可复现（附录）。
- v6-plan §1.4 已回写冻结/延后标注（保持唯一阈值出处）。

## 数据可得性缺口（如实记录）

- degraded_accept/convergence_failed 历史分布不可得（全量 run 日志已删）→ T4 延后。
- arc_plans 历史库不存在（早于 V6 骨架）→ 弧级兑现率不可历史复算，仅全局台账。
- T5 干净单项目基线缺失（`.tmp` 库多项目混合）。
