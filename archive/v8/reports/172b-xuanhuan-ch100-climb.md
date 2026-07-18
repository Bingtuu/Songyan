# Task 172b: xuanhuan Ch100 爬坡验证报告

- 生成时间: 2026-07-17T20:27:57.492815
- 项目: `1e7ce6279b224e7f8e476f6f4e963417`  体裁: `xuanhuan`  目标: Ch100
- Gate: enforce / isolate / resume  Halt: None

## 分段指标

| up_to | accepted | budget_peak | before_emerg_peak | emerg | overdue | health | CED/1k |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 | 25 | 0.9811 | 0.0 | 0 | 0 | 8.8 | 43.3737 |
| 50 | 50 | 0.9811 | 0.0 | 0 | 2 | 9.3 | 21.4507 |
| 75 | 75 | 0.9811 | 0.0 | 0 | 85 | 9.6 | 14.3515 |
| 100 | 100 | 0.9811 | 0.0 | 0 | 166 | 9.1 | 10.7489 |

## 结论

Ch100 全 accepted 达标，无 halt。V 维度证据见上表。

> **CED 口径注记（2026-07-18 补录）**：上表 `CED/1k` 列为旧 harness 口径（含 llm+merged 双计数与 craft 类 issue），仅作历史存档，**不作为 V 维度判定依据**。终判以 172b.q 修正口径（consistency-only、merged/source、正文证据）为准：xuanhuan Ch100 CED = 0.4434（154 issues / 347,290 词）≤ sci-fi 0.3976 × 1.15 = 0.4573，详见 `tasks/172b.q-consistency-ced-repair.md` §5.2。
