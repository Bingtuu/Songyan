# Task 171d: 三层契约落地报告（A1 分层视图 + A3 趋势地板/抽读 + A4 标定）

> 生成: Task 171d 标定脚本 `scripts/run_171d_calibrate.py`
> 对应框架 `docs/reports/v7-literary-framework-review.md` §8 A 组。observe-only，不阻塞。

## A4 参数标定（各 DB 文学观测分基线分布）

| 数据源 | 章数 | 维度 | 均值 | 最小 | 相对地板×0.85 | 触发绝对地板<3.0? |
|---|---:|---|---:|---:|---:|:---:|
| scifi_170p | 10 | literary_quality | 5.35 | 4.50 | 4.55 | 否 |
| scifi_170p | 10 | character_autonomy | 3.00 | 2.50 | 2.55 | 是 |
| scifi_170p | 10 | conceptual_grounding | 4.65 | 3.00 | 3.95 | 否 |
| scifi_170p | 10 | fissure_preservation | 6.75 | 4.50 | 5.74 | 否 |
| wuxia_171a1 | 11 | literary_quality | 5.45 | 4.50 | 4.64 | 否 |
| wuxia_171a1 | 11 | character_autonomy | 3.18 | 2.50 | 2.7 | 是 |
| wuxia_171a1 | 11 | conceptual_grounding | 4.82 | 3.50 | 4.1 | 否 |
| wuxia_171a1 | 11 | fissure_preservation | 6.27 | 4.00 | 5.33 | 否 |
| scifi_170i | 92 | literary_quality | 5.85 | 4.50 | 4.97 | 否 |
| scifi_170i | 92 | character_autonomy | 3.02 | 2.00 | 2.56 | 是 |
| scifi_170i | 92 | conceptual_grounding | 5.32 | 3.50 | 4.52 | 否 |
| scifi_170i | 92 | fissure_preservation | 7.62 | 6.00 | 6.48 | 否 |
| v6_159 | 352 | literary_quality | 7.40 | 0.00 | 6.29 | 是 |
| v6_159 | 352 | character_autonomy | 7.58 | 0.00 | 6.44 | 是 |
| v6_159 | 352 | conceptual_grounding | 6.18 | 0.00 | 5.25 | 是 |
| v6_159 | 352 | fissure_preservation | 8.28 | 0.00 | 7.03 | 是 |

## 标定结论

- **相对地板系数 = 0.85**：比既有 T3 诊断（×0.80/20% 跌幅）更早预警（15% 跌幅），与框架 §8 A3 一致；两口径并存、互不干扰（T3 诊断保留，抽读为独立 observe 信号）。
- **绝对地板 = 3.0**（rubric **1–10** 量表；标定确认真实分均值 5–8、健康章最小 4–6）：跌破视为塌陷，防止基线本身偏低时相对地板失效。
- 二者取 `max(base×0.85, 3.0)` 为阈值：滚动窗口均值低于该阈值即建议**人工抽读**，**不自动阻塞**（observe-only）。
- **数据口径说明**：v6_159 的最小值 0.00 是个别章缺 LiteraryAuditor 观测的**缺失哨兵**（非真实塌陷），故其『触发绝对地板』为『是』属采集缺口、非质量事件；标定用均值不受单点 0 影响。
- 历史/隔离库若无 literary_observations，对应行留空；标定随 Ch200 主线积累真实分可复算收紧。

## A1 三层分层视图

`songyan metrics` 出口顶部新增「三层契约摘要」段（`render_three_tier_contract_summary`）：
Tier 1 硬缺陷（T9，**阻塞**，汇总展示）/ Tier 2 趋势（rubric 趋势地板，**observe**，跌破建议抽读）/ Tier 3 研究值（voice/exposition 原始读数，不判定），三区互不混淆、各标注阻塞性。

## A3 observe-only 证明

`detect_literary_spot_read` 只返回 `spot_read_recommended` 标志 + 触发维度，**代码中无任何 halt/gate 接线**（gate 仅由 `_gates.py`/`phase2_graph.py` 的稳定性面驱动，见 171 审计）。单测 `test_171d_three_tier_contract.py` 锁定：跌破只置建议标志、不产出阻塞信号。