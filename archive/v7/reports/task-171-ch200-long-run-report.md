# Task 171：Ch1-Ch200 长跑报告（阶段 Z 第一里程碑，文学=观测）

- 生成时间: 2026-07-13T13:04:35.934311
- DB: `.tmp\task171_ch1_ch200.db`
- 项目 ID: `835afdf11a294b5eac74a5d8998bd9a2`
- Run ID: `run-fb39245c`
- 章节范围: Ch1-Ch200
- Gate 模式: enforce；on_failure: isolate
- 完成: 200/200

## 放行判据（稳定性面，不含文学 rubric）

见下方稳定性面验收（T9/health/orphan/T12）；文学 Tier 2 仅观测（下节），不阻塞。

## 文学 Tier 2 观测（框架 §8 D2；observe-only，不阻塞）

- 观测章数: 200
- ⚠️ **建议人工抽读**：character_autonomy_score、conceptual_grounding_score、fissure_preservation_score（跌破 base×0.85 或 <3.0）
  - character_autonomy_score：首破窗口起始 Ch8
  - conceptual_grounding_score：首破窗口起始 Ch8
  - fissure_preservation_score：首破窗口起始 Ch66

> 文学分为 Tier 2/Tier 3 观测项，**不参与放行判定**；放行只看稳定性面。

# V6 阶段 A 度量报告 — 项目 835afdf11a294b5eac74a5d8998bd9a2（Ch1-Ch200）


## 三层契约摘要（框架 §8 A1；Tier 分区互不混淆）

| 层 | 内容 | 阻塞性 | 当前状态 |
|----|------|--------|----------|
| Tier 1 硬缺陷 | T9 meta 泄漏 / 整段重复 / 时间线 | **阻塞**（冻结阈值） | ✓ 0 硬缺陷 |
| Tier 2 趋势 | 文学 rubric 趋势地板（voice/expo/pacing/concept） | **observe，不阻塞** | ⚠️ 建议人工抽读：character_autonomy_score、conceptual_grounding_score、fissure_preservation_score（跌破 base×0.85 或 <3.0） |
| Tier 3 研究值 | voice/exposition 原始读数（171a-1 已验证效度） | 不判定 | 见文学趋势/exposition 观测段 |

> 三层互不混淆：Tier 1 缺陷阻塞（此处只汇总）；Tier 2 跌破仅触发人工抽读、**绝不自动阻塞**；Tier 3 供研究、不参与任何放行判定。

## setting 生命周期分布（显式 resolve / 显式 abandon / 逾期归档）

- active（仍在监测）：**155**
- resolved（显式剧情收束）：**1**
- abandoned（显式废弃）：**0**
- archived（逾期/被遗忘）：**319**

## orphan 绝对量（total / critical / recurring / other）

| 章 | total | critical | recurring | other | forgotten |
|----|-------|----------|-----------|-------|-----------|
| 3 | 0 | 0 | 0 | 0 | 0 |
| 6 | 0 | 0 | 0 | 0 | 0 |
| 9 | 0 | 0 | 0 | 0 | 0 |
| 12 | 0 | 0 | 0 | 0 | 0 |
| 15 | 0 | 0 | 0 | 0 | 0 |
| 18 | 0 | 0 | 0 | 0 | 0 |
| 21 | 0 | 0 | 0 | 0 | 0 |
| 24 | 0 | 0 | 0 | 0 | 0 |
| 27 | 0 | 0 | 0 | 0 | 0 |
| 30 | 4 | 0 | 0 | 4 | 0 |
| 33 | 0 | 0 | 0 | 0 | 0 |
| 36 | 6 | 0 | 0 | 6 | 0 |
| 39 | 0 | 0 | 0 | 0 | 0 |
| 42 | 0 | 0 | 0 | 0 | 0 |
| 45 | 1 | 0 | 0 | 1 | 0 |
| 48 | 4 | 0 | 0 | 4 | 0 |
| 51 | 1 | 0 | 0 | 1 | 0 |
| 54 | 7 | 0 | 0 | 7 | 0 |
| 57 | 6 | 0 | 0 | 6 | 0 |
| 60 | 3 | 0 | 0 | 3 | 0 |
| 63 | 2 | 0 | 0 | 2 | 0 |
| 66 | 0 | 0 | 0 | 0 | 0 |
| 69 | 0 | 0 | 0 | 0 | 0 |
| 72 | 7 | 0 | 0 | 7 | 0 |
| 75 | 0 | 0 | 0 | 0 | 0 |
| 78 | 0 | 0 | 0 | 0 | 0 |
| 81 | 0 | 0 | 0 | 0 | 0 |
| 84 | 0 | 0 | 0 | 0 | 0 |
| 87 | 1 | 0 | 0 | 1 | 0 |
| 90 | 0 | 0 | 0 | 0 | 0 |
| 93 | 0 | 0 | 0 | 0 | 0 |
| 96 | 7 | 0 | 0 | 7 | 0 |
| 99 | 0 | 0 | 0 | 0 | 0 |
| 102 | 0 | 0 | 0 | 0 | 0 |
| 105 | 7 | 0 | 0 | 7 | 0 |
| 108 | 5 | 0 | 0 | 5 | 0 |
| 111 | 1 | 0 | 0 | 1 | 0 |
| 114 | 0 | 0 | 0 | 0 | 0 |
| 117 | 8 | 0 | 0 | 8 | 0 |
| 120 | 7 | 0 | 0 | 7 | 0 |
| 123 | 7 | 0 | 0 | 7 | 0 |
| 126 | 0 | 0 | 0 | 0 | 0 |
| 129 | 8 | 0 | 0 | 8 | 0 |
| 132 | 0 | 0 | 0 | 0 | 0 |
| 135 | 0 | 0 | 0 | 0 | 0 |
| 138 | 0 | 0 | 0 | 0 | 0 |
| 141 | 5 | 0 | 0 | 5 | 0 |
| 144 | 3 | 0 | 0 | 3 | 0 |
| 147 | 7 | 0 | 0 | 7 | 0 |
| 150 | 1 | 0 | 0 | 1 | 0 |
| 153 | 0 | 0 | 0 | 0 | 0 |
| 156 | 5 | 0 | 0 | 5 | 0 |
| 159 | 5 | 0 | 0 | 5 | 0 |
| 162 | 3 | 0 | 0 | 3 | 0 |
| 165 | 5 | 0 | 0 | 5 | 0 |
| 168 | 2 | 0 | 0 | 2 | 0 |
| 171 | 3 | 0 | 0 | 3 | 0 |
| 174 | 0 | 0 | 0 | 0 | 0 |
| 177 | 0 | 0 | 0 | 0 | 0 |
| 180 | 4 | 0 | 0 | 4 | 0 |
| 183 | 0 | 0 | 0 | 0 | 0 |
| 186 | 2 | 0 | 0 | 2 | 0 |
| 189 | 0 | 0 | 0 | 0 | 0 |
| 192 | 0 | 0 | 0 | 0 | 0 |
| 195 | 0 | 0 | 0 | 0 | 0 |
| 198 | 0 | 0 | 0 | 0 | 0 |

- orphan 总量线性斜率：**0.0062**/章
- P1(critical) orphan 峰值：**0**（T6(b) 要求全程 =0）

## 每章新 critical 产生速率（T7，写入侧）

| 章 | new_critical | new_total |
|----|--------------|-----------|
| 1 | 0 | 3 |
| 2 | 0 | 4 |
| 3 | 0 | 2 |
| 4 | 0 | 4 |
| 5 | 0 | 5 |
| 6 | 0 | 5 |
| 7 | 0 | 3 |
| 8 | 0 | 7 |
| 9 | 0 | 2 |
| 10 | 0 | 6 |
| 11 | 0 | 3 |
| 12 | 0 | 3 |
| 13 | 0 | 5 |
| 14 | 0 | 2 |
| 16 | 0 | 1 |
| 18 | 0 | 4 |
| 20 | 0 | 5 |
| 21 | 0 | 4 |
| 22 | 0 | 4 |
| 23 | 0 | 4 |
| 24 | 0 | 5 |
| 25 | 0 | 5 |
| 26 | 0 | 3 |
| 27 | 0 | 7 |
| 28 | 0 | 4 |
| 29 | 0 | 4 |
| 30 | 0 | 6 |
| 31 | 0 | 4 |
| 32 | 0 | 2 |
| 33 | 0 | 3 |
| 37 | 0 | 4 |
| 38 | 0 | 3 |
| 40 | 0 | 4 |
| 41 | 0 | 3 |
| 42 | 0 | 2 |
| 43 | 0 | 3 |
| 45 | 0 | 3 |
| 46 | 0 | 3 |
| 47 | 0 | 2 |
| 49 | 0 | 3 |
| 51 | 0 | 3 |
| 52 | 0 | 4 |
| 53 | 0 | 5 |
| 54 | 0 | 3 |
| 55 | 0 | 1 |
| 56 | 0 | 4 |
| 57 | 0 | 6 |
| 59 | 0 | 3 |
| 60 | 0 | 3 |
| 62 | 0 | 5 |
| 63 | 0 | 3 |
| 64 | 0 | 4 |
| 66 | 0 | 3 |
| 69 | 0 | 5 |
| 70 | 0 | 3 |
| 71 | 0 | 4 |
| 73 | 0 | 3 |
| 74 | 0 | 4 |
| 75 | 0 | 2 |
| 77 | 0 | 2 |
| 78 | 0 | 3 |
| 79 | 0 | 3 |
| 80 | 0 | 4 |
| 81 | 0 | 3 |
| 82 | 0 | 5 |
| 83 | 0 | 5 |
| 84 | 0 | 5 |
| 85 | 0 | 4 |
| 88 | 0 | 7 |
| 93 | 0 | 6 |
| 94 | 0 | 1 |
| 95 | 0 | 1 |
| 96 | 0 | 4 |
| 97 | 0 | 3 |
| 99 | 0 | 5 |
| 100 | 0 | 6 |
| 101 | 0 | 4 |
| 102 | 0 | 4 |
| 103 | 0 | 5 |
| 104 | 0 | 3 |
| 106 | 0 | 6 |
| 108 | 0 | 3 |
| 109 | 0 | 5 |
| 110 | 0 | 5 |
| 112 | 0 | 1 |
| 113 | 0 | 3 |
| 114 | 0 | 6 |
| 115 | 0 | 5 |
| 116 | 0 | 3 |
| 117 | 0 | 5 |
| 118 | 0 | 5 |
| 119 | 0 | 4 |
| 120 | 0 | 3 |
| 121 | 0 | 6 |
| 122 | 0 | 4 |
| 123 | 0 | 4 |
| 126 | 0 | 5 |
| 127 | 0 | 4 |
| 129 | 0 | 5 |
| 130 | 0 | 4 |
| 131 | 0 | 4 |
| 132 | 0 | 4 |
| 133 | 0 | 5 |
| 134 | 0 | 3 |
| 135 | 0 | 5 |
| 138 | 0 | 5 |
| 140 | 0 | 2 |
| 141 | 0 | 5 |
| 142 | 0 | 3 |
| 146 | 0 | 3 |
| 147 | 0 | 3 |
| 148 | 0 | 3 |
| 149 | 0 | 4 |
| 151 | 0 | 5 |
| 152 | 0 | 5 |
| 154 | 1 | 8 |
| 155 | 0 | 6 |
| 156 | 0 | 4 |
| 158 | 0 | 3 |
| 159 | 0 | 2 |
| 160 | 0 | 4 |
| 161 | 1 | 5 |
| 162 | 1 | 4 |
| 163 | 0 | 5 |
| 165 | 0 | 4 |
| 166 | 1 | 5 |
| 170 | 0 | 4 |
| 171 | 0 | 3 |
| 172 | 0 | 3 |
| 173 | 0 | 3 |
| 179 | 0 | 6 |
| 180 | 0 | 6 |
| 182 | 0 | 4 |
| 185 | 0 | 5 |
| 187 | 0 | 5 |
| 190 | 0 | 5 |
| 191 | 0 | 5 |
| 192 | 0 | 4 |
| 193 | 0 | 7 |
| 194 | 0 | 5 |
| 195 | 0 | 6 |
| 196 | 0 | 4 |
| 197 | 0 | 4 |
| 198 | 0 | 5 |
| 199 | 0 | 9 |
| 200 | 0 | 5 |

- 新 critical 合计：**4**；每章均值（T7）：**0.027**

## 质量债账本（run 级；T4：50 章窗 degraded ≤20% 且 convergence ≤10%）

| run | 章数 | degraded | conv_failed | QG=false | degraded% | conv% | T4 |
|-----|------|----------|-------------|----------|-----------|-------|----|
| run-fb39245c | 210 | 0 | 0 | 1 | 0.0% | 0.0% | ✓ |

## 文学质量趋势（T3：W=5 均值相对前 10 章基线降 ≥20%；只诊断不阻断）

| 章 | literary | char_autonomy | conceptual | fissure |
|----|----------|---------------|------------|---------|
| 1 | 5.50 | 3.00 | 4.50 | 6.50 |
| 2 | 5.50 | 3.00 | 4.50 | 7.00 |
| 3 | 6.50 | 4.00 | 7.50 | 7.00 |
| 4 | 5.50 | 2.50 | 4.50 | 7.00 |
| 5 | 5.50 | 2.50 | 4.50 | 7.50 |
| 6 | 6.50 | 4.00 | 5.50 | 7.50 |
| 7 | 6.50 | 4.00 | 7.00 | 8.00 |
| 8 | 5.50 | 2.50 | 4.00 | 7.00 |
| 9 | 5.50 | 2.50 | 4.00 | 7.00 |
| 10 | 5.50 | 3.50 | 4.50 | 6.00 |
| 11 | 4.50 | 2.50 | 4.00 | 6.00 |
| 12 | 5.50 | 2.50 | 4.00 | 7.50 |
| 13 | 5.50 | 2.50 | 5.00 | 6.50 |
| 14 | 5.50 | 2.50 | 4.00 | 6.50 |
| 15 | 4.50 | 2.50 | 4.00 | 7.50 |
| 16 | 5.50 | 3.00 | 6.50 | 7.00 |
| 17 | 5.50 | 2.50 | 5.00 | 7.00 |
| 18 | 6.50 | 4.00 | 6.00 | 7.50 |
| 19 | 5.50 | 3.50 | 6.00 | 7.50 |
| 20 | 6.50 | 4.00 | 5.50 | 7.50 |
| 21 | 5.50 | 3.50 | 4.00 | 7.50 |
| 22 | 5.50 | 3.00 | 6.50 | 7.50 |
| 23 | 6.50 | 3.00 | 5.50 | 7.50 |
| 24 | 6.50 | 4.00 | 7.00 | 8.00 |
| 25 | 5.50 | 3.00 | 4.50 | 6.50 |
| 26 | 5.50 | 3.00 | 4.50 | 7.50 |
| 27 | 6.00 | 2.50 | 5.50 | 8.50 |
| 28 | 5.50 | 3.00 | 4.50 | 6.50 |
| 29 | 5.50 | 2.50 | 4.00 | 7.00 |
| 30 | 5.50 | 3.00 | 4.50 | 7.00 |
| 31 | 5.50 | 2.50 | 4.50 | 7.00 |
| 32 | 5.50 | 3.50 | 4.00 | 7.50 |
| 33 | 5.50 | 3.00 | 4.50 | 7.50 |
| 34 | 5.50 | 3.00 | 4.50 | 7.50 |
| 35 | 5.50 | 3.00 | 4.50 | 8.00 |
| 36 | 5.50 | 2.50 | 6.00 | 6.50 |
| 37 | 5.50 | 2.50 | 4.00 | 7.00 |
| 38 | 5.50 | 3.50 | 4.50 | 7.00 |
| 39 | 5.50 | 2.50 | 6.00 | 7.00 |
| 40 | 5.50 | 4.00 | 6.00 | 6.50 |
| 41 | 5.50 | 3.00 | 6.50 | 7.00 |
| 42 | 5.50 | 3.00 | 4.50 | 7.00 |
| 43 | 5.50 | 3.50 | 4.00 | 7.00 |
| 44 | 5.50 | 2.50 | 4.00 | 7.50 |
| 45 | 5.50 | 3.50 | 4.00 | 7.50 |
| 46 | 5.50 | 2.50 | 4.00 | 6.50 |
| 47 | 5.50 | 3.00 | 6.00 | 7.50 |
| 48 | 5.50 | 2.50 | 6.00 | 7.50 |
| 49 | 5.50 | 3.50 | 6.00 | 7.00 |
| 50 | 4.50 | 2.50 | 3.50 | 6.00 |
| 51 | 5.50 | 3.00 | 4.50 | 7.50 |
| 52 | 6.00 | 3.50 | 5.50 | 7.50 |
| 53 | 6.00 | 3.00 | 4.50 | 7.00 |
| 54 | 5.50 | 2.50 | 6.00 | 7.50 |
| 55 | 5.00 | 3.00 | 6.00 | 7.00 |
| 56 | 5.00 | 3.00 | 4.50 | 5.50 |
| 57 | 6.50 | 4.50 | 5.50 | 8.00 |
| 58 | 5.50 | 2.50 | 4.00 | 7.50 |
| 59 | 5.50 | 3.50 | 4.00 | 7.50 |
| 60 | 5.50 | 3.50 | 6.50 | 7.00 |
| 61 | 6.00 | 4.50 | 7.50 | 8.00 |
| 62 | 4.50 | 3.00 | 4.00 | 6.00 |
| 63 | 5.50 | 3.00 | 4.50 | 6.50 |
| 64 | 6.50 | 3.00 | 7.50 | 8.00 |
| 65 | 6.50 | 4.00 | 5.50 | 7.00 |
| 66 | 5.50 | 3.50 | 4.50 | 6.00 |
| 67 | 5.50 | 3.00 | 5.00 | 6.50 |
| 68 | 5.50 | 3.50 | 6.50 | 7.00 |
| 69 | 5.50 | 3.00 | 5.00 | 4.50 |
| 70 | 5.50 | 3.00 | 7.00 | 4.50 |
| 71 | 6.00 | 3.50 | 4.50 | 8.00 |
| 72 | 5.50 | 2.50 | 6.00 | 6.50 |
| 73 | 5.50 | 2.00 | 4.50 | 8.00 |
| 74 | 6.50 | 5.00 | 6.00 | 8.00 |
| 75 | 5.50 | 2.50 | 4.00 | 6.50 |
| 76 | 5.50 | 3.00 | 6.00 | 7.50 |
| 77 | 5.50 | 3.50 | 5.00 | 7.00 |
| 78 | 6.50 | 2.00 | 7.50 | 8.00 |
| 79 | 5.50 | 3.00 | 5.00 | 7.00 |
| 80 | 5.50 | 3.00 | 4.00 | 5.50 |
| 81 | 4.50 | 2.50 | 4.00 | 6.50 |
| 82 | 5.00 | 2.50 | 4.00 | 7.50 |
| 83 | 5.50 | 3.50 | 4.50 | 7.50 |
| 84 | 5.50 | 3.00 | 5.50 | 7.50 |
| 85 | 6.00 | 3.50 | 7.00 | 6.50 |
| 86 | 6.50 | 4.50 | 7.00 | 8.50 |
| 87 | 5.50 | 3.00 | 4.50 | 7.50 |
| 88 | 6.50 | 2.50 | 8.00 | 7.50 |
| 89 | 5.50 | 2.00 | 6.00 | 8.00 |
| 90 | 5.50 | 3.00 | 4.50 | 7.50 |
| 91 | 5.50 | 3.00 | 6.50 | 7.00 |
| 92 | 5.50 | 3.00 | 7.00 | 8.00 |
| 93 | 5.50 | 3.00 | 6.50 | 7.00 |
| 94 | 6.00 | 4.50 | 7.50 | 8.00 |
| 95 | 6.50 | 4.00 | 6.00 | 8.00 |
| 96 | 6.00 | 3.50 | 5.50 | 7.00 |
| 97 | 4.50 | 2.50 | 6.00 | 4.00 |
| 98 | 5.50 | 3.00 | 6.50 | 7.00 |
| 99 | 5.50 | 2.50 | 6.50 | 7.00 |
| 100 | 6.50 | 2.50 | 7.50 | 7.00 |
| 101 | 5.50 | 2.50 | 4.50 | 6.50 |
| 102 | 5.50 | 3.00 | 4.50 | 7.00 |
| 103 | 6.50 | 2.00 | 6.00 | 8.00 |
| 104 | 5.50 | 2.50 | 6.50 | 6.00 |
| 105 | 5.50 | 4.00 | 4.50 | 7.00 |
| 106 | 5.50 | 2.50 | 4.00 | 6.00 |
| 107 | 5.50 | 4.50 | 4.00 | 7.50 |
| 108 | 5.50 | 2.00 | 4.00 | 5.50 |
| 109 | 5.00 | 2.00 | 4.00 | 6.00 |
| 110 | 5.50 | 3.00 | 4.50 | 6.50 |
| 111 | 5.50 | 2.50 | 4.00 | 7.00 |
| 112 | 5.50 | 2.50 | 4.00 | 6.50 |
| 113 | 5.50 | 2.50 | 6.00 | 7.50 |
| 114 | 6.00 | 3.00 | 7.00 | 6.50 |
| 115 | 4.50 | 2.00 | 4.00 | 7.00 |
| 116 | 5.50 | 3.00 | 4.50 | 7.50 |
| 117 | 5.50 | 2.50 | 4.50 | 6.50 |
| 118 | 5.50 | 3.50 | 6.00 | 8.00 |
| 119 | 5.50 | 3.50 | 5.00 | 7.50 |
| 120 | 6.00 | 2.50 | 6.50 | 8.00 |
| 121 | 5.50 | 2.50 | 4.50 | 7.50 |
| 122 | 5.50 | 3.50 | 4.00 | 7.00 |
| 123 | 6.00 | 2.50 | 7.00 | 8.00 |
| 124 | 5.50 | 2.50 | 4.00 | 7.00 |
| 125 | 5.50 | 3.50 | 4.00 | 7.00 |
| 126 | 5.50 | 2.50 | 4.50 | 7.00 |
| 127 | 5.50 | 3.50 | 4.50 | 7.00 |
| 128 | 5.50 | 3.50 | 6.00 | 7.00 |
| 129 | 5.50 | 3.00 | 4.50 | 7.00 |
| 130 | 5.50 | 2.50 | 7.00 | 7.50 |
| 131 | 5.50 | 2.50 | 6.00 | 7.50 |
| 132 | 5.50 | 2.50 | 4.00 | 7.00 |
| 133 | 5.50 | 2.50 | 6.50 | 7.00 |
| 134 | 6.50 | 4.00 | 6.00 | 8.00 |
| 135 | 6.50 | 2.00 | 7.00 | 7.50 |
| 136 | 5.50 | 3.00 | 6.00 | 7.00 |
| 137 | 5.50 | 3.00 | 4.50 | 7.50 |
| 138 | 6.50 | 4.00 | 5.00 | 8.00 |
| 139 | 5.50 | 2.50 | 4.00 | 6.50 |
| 140 | 5.50 | 3.00 | 5.00 | 7.50 |
| 141 | 5.50 | 3.00 | 6.50 | 8.00 |
| 142 | 5.50 | 2.50 | 4.50 | 6.50 |
| 143 | 5.50 | 3.50 | 6.00 | 6.00 |
| 144 | 6.50 | 3.50 | 5.00 | 8.00 |
| 145 | 5.50 | 3.00 | 4.50 | 7.00 |
| 146 | 4.50 | 2.50 | 4.00 | 6.50 |
| 147 | 6.00 | 2.00 | 5.50 | 8.00 |
| 148 | 5.50 | 2.50 | 7.00 | 8.00 |
| 149 | 5.50 | 2.50 | 3.50 | 7.00 |
| 150 | 5.50 | 3.00 | 4.00 | 6.50 |
| 151 | 5.50 | 2.50 | 4.00 | 7.00 |
| 152 | 5.50 | 4.00 | 6.50 | 7.00 |
| 153 | 5.50 | 3.00 | 4.50 | 7.00 |
| 154 | 5.50 | 2.50 | 5.00 | 7.00 |
| 155 | 5.50 | 2.50 | 6.00 | 7.00 |
| 156 | 4.50 | 2.00 | 4.00 | 6.50 |
| 157 | 6.50 | 2.50 | 5.50 | 7.00 |
| 158 | 6.50 | 4.00 | 7.50 | 6.00 |
| 159 | 5.00 | 2.50 | 4.50 | 6.50 |
| 160 | 4.50 | 2.50 | 4.00 | 6.50 |
| 161 | 5.50 | 3.50 | 4.00 | 6.50 |
| 162 | 5.50 | 2.50 | 6.00 | 7.50 |
| 163 | 6.50 | 3.00 | 7.00 | 8.50 |
| 164 | 5.50 | 3.00 | 6.50 | 7.00 |
| 165 | 5.50 | 3.00 | 4.50 | 7.00 |
| 166 | 5.50 | 3.00 | 4.50 | 4.00 |
| 167 | 6.50 | 4.00 | 5.00 | 7.00 |
| 168 | 5.50 | 2.50 | 7.00 | 7.50 |
| 169 | 5.50 | 3.50 | 6.00 | 7.50 |
| 170 | 5.50 | 2.50 | 7.00 | 7.50 |
| 171 | 6.00 | 4.50 | 5.50 | 7.50 |
| 172 | 5.50 | 3.00 | 6.50 | 7.00 |
| 173 | 6.50 | 3.00 | 8.00 | 8.50 |
| 174 | 5.50 | 2.50 | 4.00 | 7.50 |
| 175 | 6.50 | 4.50 | 5.50 | 8.00 |
| 176 | 5.50 | 3.00 | 4.50 | 7.00 |
| 177 | 5.50 | 3.00 | 6.50 | 7.50 |
| 178 | 5.50 | 3.50 | 5.00 | 7.50 |
| 179 | 5.50 | 2.00 | 4.50 | 7.00 |
| 180 | 5.50 | 2.50 | 4.00 | 8.00 |
| 181 | 5.50 | 2.50 | 4.00 | 7.50 |
| 182 | 6.00 | 3.50 | 7.00 | 7.50 |
| 183 | 6.50 | 3.50 | 5.50 | 8.00 |
| 184 | 6.00 | 2.50 | 7.00 | 7.50 |
| 185 | 5.50 | 3.50 | 4.00 | 7.00 |
| 186 | 5.50 | 3.50 | 6.50 | 7.50 |
| 187 | 5.50 | 3.00 | 5.00 | 6.50 |
| 188 | 5.50 | 3.50 | 4.00 | 7.50 |
| 189 | 5.50 | 2.50 | 6.00 | 7.50 |
| 190 | 5.50 | 2.50 | 4.00 | 6.50 |
| 191 | 5.50 | 4.00 | 4.50 | 7.50 |
| 192 | 5.50 | 3.50 | 6.50 | 7.50 |
| 193 | 5.50 | 3.00 | 5.00 | 6.50 |
| 194 | 5.50 | 2.00 | 4.50 | 7.00 |
| 195 | 5.50 | 2.50 | 4.50 | 7.00 |
| 196 | 5.50 | 2.50 | 4.00 | 6.00 |
| 197 | 5.50 | 2.50 | 6.50 | 7.50 |
| 198 | 5.50 | 2.50 | 4.00 | 7.00 |
| 199 | 6.00 | 4.00 | 5.00 | 7.50 |
| 200 | 5.50 | 3.50 | 6.00 | 7.00 |

- 🔴 T3 触线维度 **character_autonomy_score**：首个触线窗口起始 Ch11（基线 3.15）

## 弧级伏笔兑现率（fulfilled ⇔ status=resolved）

| 弧 | 章范围 | total | resolved | abandoned | 兑现率 |
|----|--------|-------|----------|-----------|--------|
| 0 | 1-25 | 68 | 0 | 68 | 0.0% |
| 1 | 26-50 | 46 | 0 | 42 | 0.0% |
| 2 | 51-75 | 42 | 0 | 39 | 0.0% |
| 3 | 76-100 | 48 | 0 | 33 | 0.0% |
| 4 | 101-125 | 69 | 0 | 31 | 0.0% |
| 5 | 126-150 | 60 | 0 | 56 | 0.0% |

## 长程伏笔台账（未兑现；abandoned=逾期归档，被系统遗忘）

- 未兑现合计 **506**，其中被遗忘（逾期归档）**394**

| id | planted | expected | span | status | 被遗忘 |
|----|---------|----------|------|--------|--------|
| fs-835afdf11a294b5eac74a5d8998bd9a2-211a9bcb | 1 | 8 | 199 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2ca9652b | 1 | 12 | 199 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4984b545 | 1 | 10 | 199 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-12f65a35 | 2 | 12 | 198 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3f3d3fcc | 2 | 15 | 198 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-845bfa4c | 2 | 14 | 198 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0c2c1e40 | 3 | 14 | 197 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-111e7700 | 3 | 15 | 197 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-abfa7b3d | 3 | 12 | 197 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-17bb4d8d | 4 | 12 | 196 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a48c6f5c | 4 | 15 | 196 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b8e0d679 | 4 | 20 | 196 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e2a2dceb | 4 | 10 | 196 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-471babc6 | 5 | 14 | 195 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-94de1f22 | 5 | 18 | 195 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eb4deac8 | 5 | 20 | 195 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3523a73c | 6 | 10 | 194 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4847bc36 | 6 | 12 | 194 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a63c8319 | 6 | 14 | 194 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fa2d0fc2 | 6 | 18 | 194 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-30a564e3 | 7 | 12 | 193 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-85229cd6 | 7 | 12 | 193 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e4b312ca | 7 | 15 | 193 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-00c48aac | 8 | 14 | 192 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1db28e1c | 8 | 14 | 192 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-50042320 | 8 | 14 | 192 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-62984f08 | 8 | 15 | 192 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-725ba0ef | 8 | 12 | 192 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-72b49f12 | 8 | 12 | 192 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-de4a8808 | 8 | 15 | 192 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2cd8ac26 | 9 | 14 | 191 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-47de5c41 | 9 | 14 | 191 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a9844be9 | 9 | 15 | 191 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-abc6571c | 9 | 12 | 191 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-176a52ad | 10 | 15 | 190 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9b78017a | 10 | 14 | 190 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a7f217c4 | 10 | 14 | 190 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f0a2b438 | 10 | 15 | 190 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1056b784 | 11 | 14 | 189 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b0bd17ef | 11 | 15 | 189 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b784045a | 11 | 14 | 189 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ccb9868a | 11 | 14 | 189 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5ff757bd | 12 | 13 | 188 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-714466f5 | 12 | 14 | 188 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-98aa9f25 | 12 | 13 | 188 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-baf3e1f6 | 12 | 14 | 188 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-01b0d1d5 | 13 | 14 | 187 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2f70fcf7 | 13 | 14 | 187 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7307fe4b | 13 | 14 | 187 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-96ff892d | 13 | 14 | 187 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b57f34b6 | 13 | 14 | 187 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e4d2b919 | 13 | 14 | 187 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-49185f72 | 14 | 15 | 186 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4aaaa2c8 | 14 | 15 | 186 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a677aa8b | 14 | 15 | 186 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a8ca6961 | 14 | 15 | 186 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-033b43d4 | 20 | 22 | 180 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-67ba608c | 20 | 22 | 180 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f3c375b4 | 20 | 22 | 180 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-52676a4b | 23 | 24 | 177 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9a7c9090 | 23 | 24 | 177 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-de124dba | 23 | 25 | 177 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5aa110ef | 24 | 26 | 176 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c56c0d2f | 24 | 25 | 176 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d01a21dc | 24 | 26 | 176 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a1b70bbb | 25 | 26 | 175 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e33a4509 | 25 | 27 | 175 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f85061d1 | 25 | 26 | 175 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6ba3ec1f | 26 | 27 | 174 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-82a23b69 | 26 | 27 | 174 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-cbfb2743 | 26 | 28 | 174 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e5e2c0d5 | 26 | 27 | 174 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-08f68c55 | 27 | 28 | 173 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-34c07849 | 27 | 30 | 173 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7440f483 | 27 | 28 | 173 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f077a87 | 27 | 30 | 173 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a999572b | 27 | 28 | 173 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2d1697cb | 28 | 30 | 172 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-444fb977 | 28 | 32 | 172 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eaf4bebe | 28 | - | 172 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0c71b1c7 | 30 | 32 | 170 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3198c94e | 30 | 32 | 170 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5e72c572 | 30 | 32 | 170 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6989bf31 | 30 | 32 | 170 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d741275f | 30 | 32 | 170 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-04cee12a | 31 | 32 | 169 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1ec24394 | 31 | 33 | 169 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e6f7a37e | 31 | 34 | 169 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1bb5b89e | 37 | - | 163 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7c34f394 | 37 | - | 163 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ee92c69c | 37 | - | 163 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-47842843 | 41 | 44 | 159 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6927731f | 41 | 44 | 159 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-cbc5de98 | 41 | 44 | 159 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d8dffd4c | 41 | 44 | 159 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f6b0eb47 | 41 | 44 | 159 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-32163fdf | 42 | 44 | 158 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7c4d7ee3 | 42 | 44 | 158 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-88cad144 | 42 | 44 | 158 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f3167ae7 | 42 | 44 | 158 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0c909e63 | 43 | 46 | 157 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1e89738e | 43 | 46 | 157 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2fb1d0af | 43 | 46 | 157 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5d69cb13 | 43 | 46 | 157 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8dd49b9f | 43 | 45 | 157 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae128815 | 43 | 45 | 157 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d217303 | 45 | 47 | 155 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d2aeb5c1 | 45 | 47 | 155 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e527c2b2 | 45 | 47 | 155 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-55e4b728 | 46 | 48 | 154 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-bd918a9f | 46 | 48 | 154 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f799fd46 | 46 | 48 | 154 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-338fb174 | 47 | 49 | 153 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c997a31b | 47 | 49 | 153 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e85017f4 | 51 | - | 149 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fceb3f12 | 51 | - | 149 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-283f9dae | 53 | 55 | 147 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4a31f9f9 | 53 | 55 | 147 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-94351bb5 | 53 | 55 | 147 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a846e663 | 54 | 58 | 146 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f4413437 | 54 | 56 | 146 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fc2ac8d8 | 54 | 56 | 146 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3bdef31f | 55 | 58 | 145 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-51bc5d68 | 55 | 56 | 145 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-db4b937a | 55 | 58 | 145 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ecf100d6 | 55 | 56 | 145 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3d8e835f | 56 | 60 | 144 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d24155b2 | 56 | 62 | 144 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d54257ec | 56 | 58 | 144 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-106b78d0 | 57 | 60 | 143 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d9dc5fe | 57 | 60 | 143 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-659fe646 | 60 | 65 | 140 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ce06a448 | 60 | 62 | 140 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3aa0dfe5 | 62 | - | 138 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-74e5e856 | 62 | 65 | 138 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a70823db | 62 | 64 | 138 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b36d0a6d | 62 | 63 | 138 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-27651848 | 63 | 64 | 137 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-55b1f123 | 63 | 65 | 137 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-886578ce | 63 | 65 | 137 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b47fe159 | 64 | 66 | 136 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c7187d90 | 64 | 65 | 136 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d59e9f4d | 64 | 66 | 136 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0a323fc0 | 66 | 165 | 134 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2e98b312 | 66 | 163 | 134 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8a649597 | 66 | 163 | 134 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3a83af0c | 69 | 160 | 131 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3e36d7b2 | 69 | 160 | 131 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-88d3fca6 | 69 | 160 | 131 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8a4d22eb | 70 | 160 | 130 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8dccba01 | 70 | 160 | 130 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d67ee167 | 70 | 160 | 130 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1fd9ba59 | 73 | 75 | 127 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b8a2750c | 73 | 76 | 127 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3ecf07be | 74 | 80 | 126 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-808817c9 | 74 | 78 | 126 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3a3948d0 | 78 | 83 | 122 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7c872d21 | 78 | 82 | 122 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ccef28ab | 78 | 80 | 122 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2f57b375 | 79 | 83 | 121 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c5199339 | 79 | 84 | 121 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-03112c52 | 80 | 84 | 120 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3a2fcf19 | 80 | 84 | 120 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-82ae8dcb | 80 | 85 | 120 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-50ce3890 | 81 | - | 119 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-734cdf98 | 81 | 84 | 119 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a9db356e | 81 | 84 | 119 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2fa44d57 | 82 | 84 | 118 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b5aec171 | 82 | 86 | 118 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-be18714c | 82 | 85 | 118 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d631bc75 | 82 | 85 | 118 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7f2dc01a | 83 | 85 | 117 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9ee84452 | 83 | 85 | 117 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b2cd20d7 | 83 | 85 | 117 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d2b8efae | 83 | 86 | 117 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-196b43c1 | 84 | 86 | 116 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-30268885 | 84 | 85 | 116 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae509db0 | 84 | 88 | 116 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b3d732fa | 84 | 87 | 116 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e03c493d | 84 | 86 | 116 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-003f5461 | 85 | 87 | 115 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1d700c27 | 85 | 87 | 115 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2eba574d | 85 | 87 | 115 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3be20c56 | 85 | 86 | 115 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eaa4e31b | 85 | 86 | 115 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7fea950b | 93 | - | 107 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d290956a | 93 | - | 107 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0b9cc7b6 | 95 | - | 105 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-49a5f4b4 | 95 | - | 105 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5bbc7b65 | 95 | - | 105 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-92f82cc2 | 96 | - | 104 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ad6a1a5f | 96 | - | 104 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d47ef853 | 96 | - | 104 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-157c5831 | 97 | - | 103 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae14d0c5 | 97 | - | 103 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae4ab4ac | 97 | - | 103 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e352a726 | 97 | - | 103 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-41629cc5 | 99 | 165 | 101 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6ca407d9 | 99 | 165 | 101 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-738bd165 | 99 | 162 | 101 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-76eb0cf8 | 99 | 165 | 101 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9c9e8345 | 99 | 165 | 101 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-801f8fa8 | 100 | - | 100 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-dfa050d9 | 100 | - | 100 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2bee8174 | 101 | - | 99 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b363c64e | 101 | - | 99 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e775c99a | 101 | - | 99 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eae87f66 | 101 | - | 99 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ee535e5c | 101 | - | 99 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-19ccb4de | 102 | - | 98 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6576fc5c | 102 | - | 98 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-74987335 | 102 | - | 98 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4dd6bc3d | 103 | - | 97 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7663797a | 103 | - | 97 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f0f3797 | 103 | - | 97 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-09cf11c7 | 106 | - | 94 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-22cf490a | 106 | - | 94 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3d4a1c80 | 106 | - | 94 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-dbf62f01 | 106 | - | 94 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0c496d60 | 108 | - | 92 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-bd00f167 | 108 | - | 92 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f51fe699 | 108 | - | 92 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0e517f4f | 110 | - | 90 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-15f6ce95 | 110 | - | 90 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3854dabb | 110 | - | 90 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-60daf913 | 110 | - | 90 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-84cfbac4 | 110 | - | 90 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ab9a362c | 110 | - | 90 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2787e053 | 112 | - | 88 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-31c2ca85 | 112 | - | 88 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-93a6ca32 | 112 | - | 88 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ab0032a4 | 112 | - | 88 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0a7393ae | 113 | - | 87 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9edbba3c | 113 | - | 87 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ad34dea3 | 113 | - | 87 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-306827e1 | 114 | - | 86 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e1084c97 | 114 | - | 86 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f0eb6604 | 114 | - | 86 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f213e37b | 114 | - | 86 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3120e6ec | 115 | - | 85 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-57001741 | 115 | - | 85 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8b30b630 | 115 | - | 85 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4544b09c | 116 | 118 | 84 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5617c82a | 116 | 118 | 84 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-77e39a74 | 116 | 120 | 84 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-96faa2ed | 116 | 118 | 84 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1f2f2366 | 117 | 121 | 83 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8b3d427c | 117 | 120 | 83 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ac07161b | 117 | 120 | 83 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6b0f1eb8 | 118 | 123 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-80c3d56d | 118 | 124 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-92b5963e | 118 | 122 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d36bfe2d | 118 | 123 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f5fbc9bf | 118 | 122 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-188b8646 | 119 | 123 | 81 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-85d5d386 | 119 | 124 | 81 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-be646b30 | 119 | 123 | 81 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4e7902d0 | 120 | 124 | 80 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c86800c0 | 120 | 125 | 80 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-de020cef | 120 | 125 | 80 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2be3ed07 | 121 | 127 | 79 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-56889abd | 121 | 127 | 79 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-893b893a | 121 | 126 | 79 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b6202b30 | 121 | 126 | 79 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c1492918 | 121 | 126 | 79 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0e8b904d | 122 | 129 | 78 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5f789b4a | 122 | 128 | 78 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6fb26d76 | 122 | 130 | 78 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e19c6b16 | 122 | 128 | 78 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7392ed3d | 123 | 132 | 77 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7a43dd7b | 123 | 131 | 77 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-91a066e8 | 123 | 130 | 77 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9d48f7c3 | 123 | 129 | 77 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-026eae9f | 126 | 133 | 74 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4e985626 | 126 | 132 | 74 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5fb4faea | 126 | 132 | 74 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e416a55a | 126 | 133 | 74 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3c55657a | 129 | 135 | 71 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-70210197 | 129 | 135 | 71 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a78be486 | 129 | 135 | 71 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1b390538 | 130 | 140 | 70 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-36e01093 | 130 | 136 | 70 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-59b8b919 | 130 | 136 | 70 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5d5fed8a | 130 | 136 | 70 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c7033f0e | 130 | 140 | 70 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8a2bbe1a | 131 | 137 | 69 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f036bc3 | 131 | 138 | 69 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d211e7b3 | 131 | 137 | 69 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1606e3a3 | 132 | 138 | 68 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5ae6c694 | 132 | 137 | 68 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b4d8f2eb | 132 | 137 | 68 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-31749a6e | 133 | 136 | 67 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9aa30d5c | 133 | 136 | 67 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-dc8f3290 | 133 | 136 | 67 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2cb634c4 | 134 | 140 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-321a0dfa | 134 | 140 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-71130972 | 134 | 140 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-914e729a | 134 | 138 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-984b6332 | 134 | 140 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-000e250e | 135 | 141 | 65 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8bc2a16a | 135 | 141 | 65 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f74ad70 | 135 | 141 | 65 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d6e91b94 | 135 | 141 | 65 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f69399a0 | 135 | 142 | 65 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1b55bcd6 | 138 | 142 | 62 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1d576a31 | 138 | 142 | 62 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-303a0830 | 138 | 142 | 62 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-337d6694 | 138 | 142 | 62 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-683ae1f0 | 138 | 142 | 62 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-96feced3 | 138 | 142 | 62 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7b928790 | 141 | 143 | 59 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-89c40686 | 141 | 143 | 59 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-cd9798d6 | 141 | 143 | 59 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f0c3d07f | 141 | 143 | 59 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1ce0b39b | 142 | 144 | 58 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5027738d | 142 | 144 | 58 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8488e71e | 142 | - | 58 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-93821ed4 | 142 | 144 | 58 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a6a13724 | 142 | 145 | 58 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-465f4ba5 | 146 | - | 54 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8086b929 | 146 | - | 54 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-aaab60ef | 146 | - | 54 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-39dd6548 | 147 | 148 | 53 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-46aafe24 | 147 | 148 | 53 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-91558f3c | 147 | 148 | 53 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5e6a97b | 147 | 148 | 53 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-645cc7b3 | 148 | 150 | 52 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5eeecad | 148 | 150 | 52 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e46984bf | 148 | 150 | 52 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-19970609 | 149 | 155 | 51 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-94f7ef75 | 149 | 155 | 51 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f557da0 | 149 | 155 | 51 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b2f7d25d | 149 | 155 | 51 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-31f1d7c3 | 151 | 158 | 49 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-72e4b9df | 151 | 160 | 49 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b3040eca | 151 | 162 | 49 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e07c7c54 | 151 | 160 | 49 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-17e95ee2 | 152 | 160 | 48 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a684733e | 152 | 158 | 48 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ce989e04 | 152 | 160 | 48 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f251301b | 152 | 165 | 48 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0fe6b9bd | 154 | 158 | 46 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-638b46fa | 154 | 157 | 46 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-836bcb46 | 154 | 156 | 46 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8f1a5d7d | 154 | 160 | 46 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f03e3da6 | 154 | 156 | 46 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-447b5c90 | 155 | 157 | 45 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7ff52e5c | 155 | 158 | 45 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a4c17689 | 155 | 157 | 45 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d02f530d | 155 | 160 | 45 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-940ae171 | 156 | 158 | 44 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d38558c4 | 156 | 158 | 44 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d8c87486 | 156 | 158 | 44 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0bac8404 | 159 | 161 | 41 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-717cfcf2 | 159 | 160 | 41 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a642f9ff | 159 | 161 | 41 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b84dd889 | 159 | 160 | 41 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-74256d8b | 160 | 161 | 40 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e3ffcc99 | 160 | 161 | 40 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fa241809 | 160 | 170 | 40 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-cbea2578 | 162 | 165 | 38 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5357b2a | 162 | 165 | 38 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e71440d6 | 162 | 163 | 38 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ecaf60d9 | 162 | 163 | 38 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-82797af0 | 163 | - | 37 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a63bdd1c | 163 | - | 37 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-bef9ce18 | 163 | - | 37 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c84e540b | 163 | - | 37 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d40beaec | 163 | - | 37 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-675e951e | 166 | 175 | 34 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d598ce30 | 166 | 170 | 34 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e5ffa35c | 166 | 180 | 34 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4a7b6977 | 170 | 175 | 30 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d08258b | 170 | 172 | 30 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b6d81d03 | 170 | 171 | 30 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e26a595c | 170 | 172 | 30 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6a28d8b7 | 171 | 175 | 29 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a9d37c6f | 171 | 175 | 29 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c9cc5145 | 171 | 175 | 29 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-421c174d | 172 | 176 | 28 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6d7ca7b4 | 172 | 178 | 28 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-97d5f5b8 | 172 | 178 | 28 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-298a1941 | 173 | 178 | 27 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5440af7e | 173 | 178 | 27 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3a9e5451 | 179 | 186 | 21 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5350c94d | 179 | 185 | 21 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6e663afc | 179 | 183 | 21 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-afd5111f | 179 | 185 | 21 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-31e18ef5 | 180 | 188 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3e4743b1 | 180 | 186 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-465a2826 | 180 | 186 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-64bf3ae5 | 180 | 186 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5248be4 | 180 | 190 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-950610d2 | 182 | 187 | 18 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ccee251c | 182 | 188 | 18 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d197653b | 182 | 186 | 18 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ea5c6c51 | 182 | 186 | 18 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-37cb82d7 | 185 | 186 | 15 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f5cd3f1 | 185 | 186 | 15 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f4fadf45 | 185 | 186 | 15 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-34bccf45 | 187 | 189 | 13 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3f26debd | 187 | 190 | 13 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f974dec9 | 187 | 191 | 13 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0fc72db9 | 190 | 193 | 10 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-17e25307 | 190 | 192 | 10 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-50111325 | 190 | 192 | 10 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e174640f | 190 | 192 | 10 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1eccd778 | 191 | 195 | 9 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-870542cb | 191 | 196 | 9 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-936145b7 | 191 | 194 | 9 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c502bb3f | 191 | 197 | 9 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-19559348 | 192 | 200 | 8 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2bc67470 | 192 | - | 8 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3651d4d3 | 192 | 200 | 8 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e45b282f | 193 | 196 | 7 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e886c7bd | 193 | 196 | 7 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5723662d | 194 | 197 | 6 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ba1a9395 | 194 | - | 6 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e0f3402f | 194 | 198 | 6 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f9cf4929 | 194 | 200 | 6 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-511b8d1b | 195 | 197 | 5 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a9537b1c | 195 | 200 | 5 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b49bdb66 | 195 | 198 | 5 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d2e451a4 | 195 | 199 | 5 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eb332306 | 195 | 197 | 5 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4c83a2a2 | 196 | 201 | 4 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-585e3c7c | 196 | 200 | 4 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8b6a4545 | 196 | 202 | 4 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d9709c0e | 196 | 200 | 4 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4474f505 | 197 | 202 | 3 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4c219bae | 197 | 200 | 3 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-bd325ab6 | 197 | 198 | 3 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d8737fdb | 197 | 199 | 3 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-10d32879 | 198 | 200 | 2 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-143725f9 | 198 | 201 | 2 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-371e7065 | 198 | 200 | 2 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-630235c6 | 198 | 200 | 2 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-afbfe377 | 198 | 201 | 2 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-15c9837f | 199 | 210 | 1 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-35003b39 | 199 | 205 | 1 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7fe5c862 | 199 | 210 | 1 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5335b79 | 199 | 208 | 1 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ded3b434 | 199 | 208 | 1 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1d6a7625 | 200 | 210 | 0 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3bce3f46 | 200 | 210 | 0 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-422aed1d | 200 | 210 | 0 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d4941e5c | 200 | 210 | 0 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d611c1ae | 200 | 210 | 0 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-04d9df33 | 202 | 210 | -2 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7622ec3b | 202 | 210 | -2 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-be8b52de | 202 | 210 | -2 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f90fa883 | 202 | 210 | -2 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1859383e | 203 | 210 | -3 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4af3e12b | 203 | 210 | -3 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6d18255c | 203 | 210 | -3 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f36c403 | 203 | 210 | -3 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e869e17f | 204 | 212 | -4 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ebb2fbd9 | 204 | 210 | -4 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f88a1856 | 204 | 215 | -4 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-116d966e | 205 | 215 | -5 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-34cbbcba | 205 | 212 | -5 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae320c52 | 205 | 213 | -5 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2932b48f | 206 | 212 | -6 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-37342218 | 206 | 215 | -6 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-72f675b4 | 206 | 212 | -6 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a5323b00 | 206 | 212 | -6 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5f3d03f9 | 207 | - | -7 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6d7539ed | 207 | - | -7 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-79c2f823 | 207 | - | -7 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d373ad8 | 207 | - | -7 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-05a60eab | 208 | 215 | -8 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0714ba92 | 208 | 218 | -8 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-84a040c8 | 208 | 213 | -8 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9e5fdf89 | 208 | 213 | -8 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-16a4f304 | 209 | 215 | -9 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3f0d478f | 209 | - | -9 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-723cd63e | 209 | 215 | -9 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3f0bdcfe | 210 | 220 | -10 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-434fd565 | 210 | 220 | -10 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7a20269f | 210 | 220 | -10 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d1d38ea7 | 210 | 220 | -10 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4465df82 | 211 | 230 | -11 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-47db85aa | 211 | 220 | -11 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-80e83569 | 211 | 225 | -11 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-965c8a9e | 211 | 220 | -11 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-57bde224 | 214 | 218 | -14 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5b846749 | 214 | 217 | -14 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-63029d3a | 214 | 218 | -14 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ba2c65d0 | 214 | 218 | -14 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-95206941 | 216 | 222 | -16 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ab5f0be5 | 216 | 220 | -16 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c5a90f3f | 216 | 221 | -16 | due |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c97445af | 216 | 222 | -16 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-139d0bba | 217 | 230 | -17 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-82ca04ac | 217 | 225 | -17 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-90f45149 | 217 | 232 | -17 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d96baec8 | 217 | 228 | -17 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5ac782d6 | 218 | 220 | -18 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5cc39eaa | 218 | 222 | -18 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d18649f | 218 | 225 | -18 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a1a5eed3 | 218 | 220 | -18 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c958b994 | 218 | 225 | -18 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-062b8761 | 220 | 225 | -20 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-27bb7962 | 220 | 225 | -20 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3da7a901 | 220 | 225 | -20 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fd21b746 | 220 | 225 | -20 | planted |  |

## DB 维护遥测（T5：尺寸 ≤300MB；扫描耗时 ≤ 中位数×2.0）

| 章 | DB(MB) | WAL(KB) | pages | scan(ms) | 尺寸红线 | 耗时状态 |
|----|--------|---------|-------|----------|----------|----------|
| 10 | 7.50 | 4043.6 | 2077 | 16.000 | ✓ | ✓ |
| 20 | 16.28 | 4087.8 | 4321 | 16.000 | ✓ | ✓ |
| 30 | 26.62 | 4164.3 | 6905 | 16.000 | ✓ | ✓ |
| 40 | 35.08 | 4164.3 | 9190 | 62.000 | ✓ | ✓ |
| 50 | 45.33 | 4164.3 | 11918 | 47.000 | ✓ | ✓ |
| 60 | 56.66 | 4164.3 | 14548 | 109.000 | ✓ | ✓ |
| 70 | 65.45 | 4164.3 | 16960 | 156.000 | ✓ | ✓ |
| 70 | 160.76 | 4309.1 | 41155 | 297.000 | ✓ | ✓ |
| 80 | 75.73 | 4172.3 | 19588 | 234.000 | ✓ | ✓ |
| 90 | 86.33 | 4200.5 | 22300 | 219.000 | ✓ | ✓ |
| 100 | 95.07 | 4200.5 | 24653 | 297.000 | ✓ | 🔴 hard |
| 110 | 106.77 | 4240.7 | 27653 | 313.000 | ✓ | 🔴 hard |
| 120 | 118.21 | 4240.7 | 30264 | 250.000 | ✓ | ✓ |
| 130 | 127.93 | 4240.7 | 32974 | 125.000 | ✓ | ✓ |
| 140 | 137.91 | 4240.7 | 35656 | 125.000 | ✓ | ✓ |
| 150 | 149.31 | 4240.7 | 38460 | 422.000 | ✓ | 🔴 hard |
| 160 | 160.76 | 4353.4 | 41155 | 297.000 | ✓ | 🔴 hard |
| 170 | 160.76 | 4353.4 | 41155 | 125.000 | ✓ | ✓ |
| 180 | 160.76 | 4353.4 | 41155 | 140.000 | ✓ | ✓ |
| 190 | 160.76 | 4353.4 | 41155 | 141.000 | ✓ | ✓ |
| 200 | 160.76 | 4353.4 | 41155 | 156.000 | ✓ | ✓ |
| 200 | 160.76 | 4353.4 | 41155 | 141.000 | ✓ | ✓ |

- 扫描耗时基线（20 个章级样本中位数）：**140.500 ms**；hard 阈值：**281.000 ms**
- ✓ DB 尺寸未超 300MB 红线
- 🔴 扫描耗时 hard 破线章：[100, 110, 150, 160]
- △ 扫描耗时观察章：[100, 110, 150, 160]

## 跨章时间线一致性诊断（Task 162，诊断项；不阻塞 accept）

- 抽取确定性时间信号 **60** 条；疑似冲突 **14** 条。
- 闪回/档案上下文信号 **3** 条，仅展示，不参与冲突判定。

| 类型 | 前章 | 后章 | 前值 | 后值 | 定位 |
|------|------|------|------|------|------|
| countdown_increase | Ch22 | Ch32 | 1 | 43 | 第42段第1句 → 第78段第1句 |
| countdown_increase | Ch47 | Ch50 | 2 | 8 | 第69段第3句 → 第87段第2句 |
| countdown_increase | Ch50 | Ch56 | 8 | 56 | 第87段第2句 → 第20段第1句 |
| countdown_increase | Ch75 | Ch82 | 1 | 32 | 第63段第1句 → 第37段第3句 |
| countdown_increase | Ch82 | Ch83 | 32 | 40 | 第37段第3句 → 第80段第2句 |
| countdown_increase | Ch84 | Ch97 | 31 | 48 | 第51段第1句 → 第51段第2句 |
| countdown_increase | Ch97 | Ch99 | 48 | 52 | 第51段第2句 → 第75段第2句 |
| countdown_increase | Ch120 | Ch122 | 2 | 100 | 第60段第2句 → 第83段第1句 |
| countdown_increase | Ch144 | Ch149 | 2 | 12 | 第35段第2句 → 第22段第1句 |
| countdown_increase | Ch149 | Ch153 | 3 | 4 | 第82段第2句 → 第40段第2句 |
| countdown_increase | Ch160 | Ch161 | 4 | 17 | 第9段第2句 → 第72段第2句 |
| countdown_increase | Ch161 | Ch164 | 17 | 37 | 第72段第2句 → 第81段第1句 |
| countdown_increase | Ch166 | Ch171 | 1 | 10 | 第98段第2句 → 第90段第3句 |
| countdown_increase | Ch178 | Ch181 | 3 | 23 | 第76段第3句 → 第100段第2句 |

<details><summary>时间信号明细</summary>

| 章 | 类型 | 值 | 单位 | 定位 | 片段 | 备注 |
|----|------|----|------|------|------|------|
| 5 | countdown | 6 | 分钟 | 第73段第1句 | 通讯频道里，匿名消息者的声音再次响起，这一次带着一种难以捉摸的意味：“林渊，你还有六分钟。想活命的话，向东走三百米，那里的应急通道锁还没有被舰队接管。” |  |
| 8 | relative_sequence | 七天后 | day_offset | 第42段第1句 | 指挥官录音：'如果我们不启动融合协议，方舟会在七天后自动进入播种模式。到时候所有人都得死。' | flashback_context:录音 |
| 8 | relative_sequence | 七天后 | day_offset | 第68段第3句 | 然后是另一个声音——指挥官的。冷静，克制，每句话都像在记录日志：“没有其他选择。如果我们不启动融合协议，方舟会在七天后自动进入播种模式。到时候所有人都得死。” | flashback_context:日志 |
| 9 | relative_sequence | 三天后 | day_offset | 第8段第4句 | 他想起七年前。月球求救信标被关闭的那天，他正在轨道站值班。信标的信号中断时，他以为是设备故障。直到三天后，月球基地的通讯全面静默，他才意识到那不是故障。 |  |
| 19 | countdown | 72 | 小时 | 第91段第1句 | “你还有七十二小时。”AI的声音在消散的墙壁中变得越来越远，“在这之后，档案馆将进入休眠模式，所有剩余权限将被冻结。” | flashback_context:档案 |
| 22 | relative_sequence | 三天后 | day_offset | 第103段第1句 | 三天后，观察者将抵达太阳系。 |  |
| 22 | relative_sequence | 三天后 | day_offset | 第114段第1句 | 三天后。 |  |
| 22 | countdown | 2 | 分 | 第23段第2句 | 林渊没有回答。他的目光落在操作台上那些跳动的数据上——锁死协议完成度百分之七十一，结构坍塌倒计时两分零七秒，神经共鸣等级正在逼近阈值。如果继续，观察者会在三分钟... |  |
| 22 | countdown | 1 | 分 | 第42段第1句 | 林渊的视野中出现了第二组数据——锁死协议完成度百分之八十三，结构坍塌倒计时一分十九秒，观察者信号增强到了之前的三倍。他能感觉到那个东西正在接近，像是深海中一头正... |  |
| 32 | countdown | 43 | 小时 | 第78段第1句 | “你还有四十三小时五十八分钟。”她的声音回到那种平稳的语调，但林渊能听出底下的变化——不再是那种精确到冷酷的疏离，是某种更迫切的、带着人类情感色彩的东西，“切断... |  |
| 40 | countdown | 17 | 分钟 | 第62段第3句 | 林渊没有回答。他看着立方体表面的铭文，看着陈薇的签名，看着那些正在重新排列的几何纹路。他的脑海中在快速计算：过载保护协议启动还有十七分钟，郑远山的精英小队正在接... |  |
| 42 | countdown | 12 | 分钟 | 第51段第3句 | 林渊没有回答。他的右手从工具包中抽出一把多功能切割器，拇指按在触发键上。神经接口界面显示，封印解除倒计时还剩十二分钟，评估站内部的能量波动正在上升——某种协议正... |  |
| 45 | countdown | 2 | 分 | 第11段第1句 | 他还有两分四十七秒。评估站的反相位信号已经释放，建造者的定位被暂时屏蔽，但这个窗口正在以肉眼可见的速度缩小。 |  |
| 47 | countdown | 1 | 分 | 第107段第1句 | “你还有一分半钟。”观察者的声音恢复了那种刻意的温柔，“你可以选择信任我，断开链接，然后——” |  |
| 47 | countdown | 3 | 分 | 第27段第1句 | “你还有三分五十八秒。”观察者说，“如果你继续——” |  |
| 47 | countdown | 4 | 分 | 第4段第1句 | “你还有四分半钟。”观察者的声音从全息投影中传来，平稳如机械读数，“断开链接，或者继续。” |  |
| 47 | countdown | 2 | 分 | 第69段第3句 | “你猜对了。”她说，“但你没有时间了。自毁协议已经进入不可逆阶段，你还有两分四十七秒。” |  |
| 50 | countdown | 8 | 分钟 | 第87段第2句 | 他的手掌还插在控制台的凹槽里，指尖传来刺痛。神经接口显示，时间已经过去了九分钟——他在地下意识空间里待了九分钟，而协议还有八分钟就要完成。 |  |
| 56 | countdown | 56 | 小时 | 第20段第1句 | “林渊，你还有56小时。不是72小时。我重新校准了时间膨胀系数——方舟的惯性导航系统在最后一次跃迁中累积了16小时的误差。你之前看到的时间是错的。” |  |
| 56 | countdown | 56 | 小时 | 第32段第1句 | “按照当前消耗速率，核心层稳定时间剩余56小时。”观察者停顿了0.5秒，“比原本的72小时缩短了16小时。你的操作——包括刚才的物理隔离区写入——加速了消耗。” |  |
| 56 | countdown | 72 | 小时 | 第34段第2句 | 林渊的呼吸变得急促。他本来以为还有72小时，现在被砍掉了16个小时。而他还需要破开第六层和第七层认知锁，找到陈曦的全部记忆碎片，然后定位建造者真正核心的位置—— |  |
| 56 | absolute_date | 2037-11-14 | date | 第89段第1句 | 2037年11月14日 03:42:17 UTC |  |
| 62 | countdown | 3 | 小时 | 第112段第1句 | “我还有三小时？” |  |
| 63 | countdown | 3 | 小时 | 第37段第1句 | 他还有三小时逃离方舟核心层。陈曦的意识记录里留下了坐标修正数据的写入位置——就在核心层下方的物理隔离区。但写入条件要求他的共鸣频率低于72%。 |  |
| 73 | countdown | 100 | 分 | 第13段第1句 | 他看了一眼逃生舱的能源指示器：剩余百分之二十三。推进系统还能支撑一次近距离机动，但靠近方舟表面意味着进入量子监护者的攻击范围。那些防御机制会在零点三秒内锁定任何... |  |
| 73 | countdown | 100 | 分 | 第54段第1句 | 逃生舱的能源指示器在黑暗中闪烁——剩余百分之十一。 |  |
| 75 | countdown | 1 | 分 | 第63段第1句 | “还剩一分五十二秒。”晶体说。 |  |
| 82 | countdown | 32 | 分钟 | 第37段第3句 | 林渊的手指在控制台上方悬停。他可以选择退出共鸣通道，关闭协议层接口，尝试切断与那个空洞的连接。耦合度会回落，同化速度会减慢，他还有三十二分钟来准备应对逼近的追踪... |  |
| 83 | countdown | 40 | 分钟 | 第80段第2句 | “林渊。”赵铭的声音从通信频道传来，“三个追踪单元还有四十分钟到达。监测站的防御系统最多能撑十分钟。” |  |
| 84 | countdown | 31 | 分钟 | 第51段第1句 | 赵铭的声音从身后传来：“（停顿半秒）追踪单元——还有三十一分钟进入传感器范围。容器#0距离监测站——七千公里，空间褶皱状态，预计三分钟内到达。” |  |
| 97 | countdown | 48 | 小时 | 第51段第2句 | “48小时。”林渊抬起头，“我们还有48小时完成撤销协议，否则方舟核心会锁定所有外来者的神经接口，永久切断与方舟的交互能力。” |  |
| 99 | countdown | 52 | 天 | 第75段第2句 | 林渊的数字在脑海中自动换算——五十二天。他还有五十二天。 |  |
| 107 | relative_sequence | 次日 | day_offset | 第2段第3句 | 不是通过视觉——通道没有光，没有方向，没有上下左右——而是通过一种更深层的感知，像骨头记住了寒冷，像牙齿记住了咬合时的震动。文明的记忆沿着量子触须渗进他的神经系... |  |
| 112 | countdown | 3 | 小时 | 第84段第1句 | “还有三小时。”陈薇的声音在通讯频道中响起，带着一种压抑的平静，“林渊，我们得在三小时内完成核心层封锁。否则——” |  |
| 120 | countdown | 2 | 分 | 第60段第2句 | 他站起身，左臂的侵蚀已经蔓延到下巴，黑色裂纹出现在嘴唇边缘。护盾的能量消耗曲线显示还有两分三十秒——他必须做出选择。 |  |
| 122 | countdown | 100 | 分 | 第83段第1句 | 他还有百分之六十三的视野。 |  |
| 133 | countdown | 3 | 分钟 | 第88段第1句 | 他还有三分钟——也许更短。 |  |
| 144 | countdown | 2 | 分 | 第35段第2句 | “别说话。”妹妹打断他，声音里带着某种不属于人类的精确音调，“你的量子化已经蔓延到胸腔了，还有两分四十七秒，方舟的自毁程序就会启动。坐标归零协议——建造者预设的... |  |
| 149 | countdown | 12 | 分钟 | 第22段第1句 | “林渊，你还有十二分钟。武器接口底层协议的逆向注入窗口还剩八分钟——如果你要在收割者信标里嵌入追踪代码，现在必须开始。” |  |
| 149 | countdown | 8 | 分钟 | 第22段第2句 | “林渊，你还有十二分钟。武器接口底层协议的逆向注入窗口还剩八分钟——如果你要在收割者信标里嵌入追踪代码，现在必须开始。” |  |
| 149 | countdown | 9 | 分钟 | 第35段第2句 | “林渊。”赵铭的声音从通讯频道传来，“你还有九分钟。收割者信标的注入进度——百分之六十三。” |  |
| 149 | countdown | 6 | 分钟 | 第45段第2句 | “百分之九十一。”赵铭的声音变得急促，“林渊，你还有六分钟。撤离通道已经开始关闭。” |  |
| 149 | countdown | 3 | 分钟 | 第82段第2句 | “林渊。”赵铭的声音从通讯频道传来，“你还有三分钟。撤离通道的闸门已经开始关闭——” |  |
| 153 | countdown | 4 | 分 | 第40段第2句 | 林渊的金属化左臂感受到一种压迫感，像整个空间在收缩。他看了一眼控制台上的倒计时——力场完全成型还有四分十七秒。 |  |
| 160 | countdown | 4 | 分 | 第20段第3句 | “你最好……快一点。”她的声音断了一拍，像在忍受什么，“还剩4分23秒。” |  |
| 160 | countdown | 3 | 分 | 第41段第1句 | “还剩3分58秒。”她的声音断成了两段，中间有一个明显的空白，“你……用了25秒。” |  |
| 160 | countdown | 4 | 分 | 第9段第2句 | “听我说，孩子……”陈薇的声音从通道深处传来，带着金属质感的失真，“还剩4分51秒。你只有一次机会。” |  |
| 161 | countdown | 17 | 分钟 | 第72段第2句 | 林渊的视线在倒计时和全息影像之间来回移动。普朗克时间的数字还在减少——**t_P: 1.89 × 10¹⁹**——大约还有十七分钟。十七分钟内，他必须做出选择。 |  |
| 164 | countdown | 37 | 分钟 | 第81段第1句 | 他还有三十七分钟。 |  |
| 165 | countdown | 34 | 分钟 | 第69段第1句 | “你还有34分钟。”残影说，“钥匙持有者，选择。” |  |
| 166 | countdown | 1 | 分 | 第98段第2句 | “哥哥。”妹妹的声音很轻，“还有一分十一秒。” |  |
| 171 | countdown | 10 | 分钟 | 第90段第3句 | 方舟引擎的轰鸣声从甲板深处传来，整个核心层开始震动。十分钟。他还有十分钟。 |  |
| 178 | relative_sequence | 七天后 | day_offset | 第106段第1句 | 七天后，某种不可逆的事情会发生。 |  |
| 178 | countdown | 2 | 分 | 第108段第3句 | “林渊！”赵铭的声音几乎在吼，“裂缝闭合速度在加快！你还有两分二十秒！” |  |
| 178 | countdown | 3 | 分钟 | 第76段第3句 | “林渊！”赵铭的声音炸开，“裂缝在闭合！你还有三分钟！” |  |
| 181 | countdown | 23 | 小时 | 第100段第2句 | “协议继承者已激活。倒计时二十三小时——从现在开始，你是钥匙，也是囚徒。但钥匙也可以打开自己的锁。” |  |
| 182 | countdown | 12 | 小时 | 第109段第1句 | 方舟的自检协议还有十二小时。 |  |
| 182 | countdown | 44 | 小时 | 第33段第3句 | “不。”碎片的声音出现了一个微弱的停顿——不是技术性的，是情感性的，“二十四秒后，这百分之三会消失。但你还有四十四小时五十八分钟，然后剩下的百分之九十六也会消失... |  |
| 189 | absolute_date | 2047-03-17 | date | 第82段第1句 | 公元2047年3月17日。 |  |
| 195 | countdown | 47 | 分钟 | 第90段第1句 | 穿梭机的自动驾驶系统发出提示音：距离坐标点还有四十七分钟航程。 |  |

</details>

## 概念预算诊断（Task 163，规划侧约束；不自动改写）

- 概念总数 **277**；未落地 **138**；本章新概念预算 **2**；触发收紧：**否**。

| 概念 | key | 引入章 | 最近提及 | 状态 | 类别 |
|------|-----|--------|----------|------|------|
| 应急通道锁机制 | ark.emergency_channel.lock_mechanism | 3 | 3 | dormant | historical |
| 方舟核心控制台——观察者休眠舱上方 | ark.core_console.above_observer_chamber | 21 | 21 | dormant | technical |
| 方舟深层结构蓝图——反向耦合通道泄露 | c_8b626631.s_12d79376.n_953c96d7 | 21 | 21 | dormant | technical |
| 观察者休眠舱——生命维持单元 | observer.hibernation_chamber.life_support_unit | 21 | 21 | dormant | technical |
| 观察者——意识污染协议 | observer.consciousness.contamination_protocol | 22 | 22 | dormant | technical |
| 神经共鸣等级系统第三阶段协议 | ark.neural_resonance.level_3_protocol | 26 | 26 | dormant | technical |
| 共鸣节点激活协议 | ark.resonance_node.activation_protocol | 26 | 26 | dormant | technical |
| 方舟强制执行回收程序 | ark.forced.reclamation_protocol | 28 | 28 | dormant | technical |
| 机械猎杀单位——方舟安保模块重构 | ark.security.hunter_unit_reconstructed | 31 | 31 | dormant | background |
| 记忆归档者——建造者文明最后幸存者 | builder.memory_archivist.last_survivor | 31 | 31 | dormant | background |
| 陈薇的全息日志 | ark.chen_wei.holographic_log | 37 | 37 | dormant | technical |
| 意识融合协议物理接口 | ark_consciousness.fusion.physical_interface | 38 | 38 | dormant | technical |
| 意识上传协议 | c_1f08eb7f.s_a977650d.n_b0c43167 | 38 | 38 | dormant | technical |
| 方舟过载保护协议 | ark.overload_protection.protocol | 40 | 40 | dormant | technical |
| 评估站协议界面（借用陈曦形象） | builder_reclamation.assessment.ai_interface | 42 | 42 | dormant | technical |
| 第七十七号播种体休眠舱 | builder.dark_vessel.sowing_body_sleep_chamber | 45 | 45 | dormant | technical |
| 第七十六号观察者信标 | builder.observer.beacon_76 | 45 | 45 | dormant | technical |
| 容器基因激活协议 | builder.container_gene.activation_protocol | 46 | 46 | dormant | technical |
| 方舟原始意识核心激活协议 | ark.original_consciousness_core.activation_protocol | 47 | 47 | dormant | technical |
| 记忆对撞协议 | ark.memory_collision.protocol | 49 | 49 | dormant | technical |

## 文本洁净度（T9 harness 数据源）

- 汇总：元标记 **0**（含 artifact），重复长段落 **0**，时间线矛盾 **14**。

| 章 | version | 元标记/artifact | 重复长段落 | 时间线矛盾 |
|----|---------|--------|------------|------------|
| 1 | clean-1-3-6d5d69ba | 0 | 0 | 0 |
| 2 | clean-2-5-2e10c842 | 0 | 0 | 0 |
| 3 | v-3-1-db8d3e8a | 0 | 0 | 0 |
| 4 | clean-4-5-9de23704 | 0 | 0 | 0 |
| 5 | v-5-1-cd0ca559 | 0 | 0 | 0 |
| 6 | v-6-1-cf21de25 | 0 | 0 | 0 |
| 7 | rev-7-2-8c91cd09 | 0 | 0 | 0 |
| 8 | rev-8-3-1db32bbf | 0 | 0 | 0 |
| 9 | v-9-1-fca9fd35 | 0 | 0 | 0 |
| 10 | rev-10-3-cefac705 | 0 | 0 | 0 |
| 11 | clean-11-5-eaec7ed2 | 0 | 0 | 0 |
| 12 | rev-12-3-8cc7c1f4 | 0 | 0 | 0 |
| 13 | rev-13-3-4a3b27ef | 0 | 0 | 0 |
| 14 | v-14-4-f91e795f | 0 | 0 | 0 |
| 15 | rev-15-3-b8082ea4 | 0 | 0 | 0 |
| 16 | v-16-1-c7893c81 | 0 | 0 | 0 |
| 17 | rev-17-2-85c91acb | 0 | 0 | 0 |
| 18 | rev-18-3-d534e337 | 0 | 0 | 0 |
| 19 | rev-19-3-692d238e | 0 | 0 | 0 |
| 20 | v-20-1-d5d767a2 | 0 | 0 | 0 |
| 21 | rev-21-3-71f464db | 0 | 0 | 0 |
| 22 | rev-22-2-54a42b32 | 0 | 0 | 0 |
| 23 | rev-23-3-f095d922 | 0 | 0 | 0 |
| 24 | v-24-4-0b63f8d3 | 0 | 0 | 0 |
| 25 | v-25-4-0029dcbf | 0 | 0 | 0 |
| 26 | clean-26-4-f2dc1865 | 0 | 0 | 0 |
| 27 | v-27-1-b79cafc0 | 0 | 0 | 0 |
| 28 | v-28-4-f7ba5c16 | 0 | 0 | 0 |
| 29 | rev-29-3-e4b7326d | 0 | 0 | 0 |
| 30 | rev-30-2-bcd01d7e | 0 | 0 | 0 |
| 31 | v-31-1-d7579d27 | 0 | 0 | 0 |
| 32 | clean-32-4-a5a19c4e | 0 | 0 | 1 |
| 33 | v-33-4-2a891192 | 0 | 0 | 0 |
| 34 | rev-34-2-157f70d8 | 0 | 0 | 0 |
| 35 | v-35-1-8bb1e638 | 0 | 0 | 0 |
| 36 | v-36-4-d2d0404f | 0 | 0 | 0 |
| 37 | v-37-4-87f425a4 | 0 | 0 | 0 |
| 38 | v-38-1-16ea9ed0 | 0 | 0 | 0 |
| 39 | rev-39-5-d7343b44 | 0 | 0 | 0 |
| 40 | v-40-4-d46cf123 | 0 | 0 | 0 |
| 41 | clean-41-4-443ad021 | 0 | 0 | 0 |
| 42 | v-42-4-5f8a17fa | 0 | 0 | 0 |
| 43 | rev-43-3-2bee20db | 0 | 0 | 0 |
| 44 | rev-44-3-5a5a0bbb | 0 | 0 | 0 |
| 45 | v-45-4-9660e8d3 | 0 | 0 | 0 |
| 46 | v-46-4-79553d10 | 0 | 0 | 0 |
| 47 | clean-47-5-221d6fbc | 0 | 0 | 0 |
| 48 | rev-48-3-95667360 | 0 | 0 | 0 |
| 49 | rev-49-2-584d2c7b | 0 | 0 | 0 |
| 50 | rev-50-2-d38a99f1 | 0 | 0 | 1 |
| 51 | v-51-1-bd1c2fb7 | 0 | 0 | 0 |
| 52 | v-52-4-689868f1 | 0 | 0 | 0 |
| 53 | v-53-1-7336c8c9 | 0 | 0 | 0 |
| 54 | v-54-1-26a70191 | 0 | 0 | 0 |
| 55 | rev-55-3-598632f1 | 0 | 0 | 0 |
| 56 | rev-56-2-9cbb4a7b | 0 | 0 | 1 |
| 57 | v-57-4-819c951b | 0 | 0 | 0 |
| 58 | v-58-4-67d9fe5c | 0 | 0 | 0 |
| 59 | v-59-4-056f4295 | 0 | 0 | 0 |
| 60 | rev-60-3-d81a5608 | 0 | 0 | 0 |
| 61 | rev-61-3-7adec2a6 | 0 | 0 | 0 |
| 62 | rev-62-3-3945ea55 | 0 | 0 | 0 |
| 63 | v-63-4-6e98aa50 | 0 | 0 | 0 |
| 64 | v-64-4-92f5ef26 | 0 | 0 | 0 |
| 65 | v-65-4-6faa3137 | 0 | 0 | 0 |
| 66 | v-66-2-20c9ebb0 | 0 | 0 | 0 |
| 67 | v-67-5-94aac136 | 0 | 0 | 0 |
| 68 | v-68-7-4aef8671 | 0 | 0 | 0 |
| 69 | v-69-5-0f73a143 | 0 | 0 | 0 |
| 70 | rev-70-5-62b2b4df | 0 | 0 | 0 |
| 71 | rev-71-2-7b30cba0 | 0 | 0 | 0 |
| 72 | v-72-1-4babd2a4 | 0 | 0 | 0 |
| 73 | v-73-4-40331e75 | 0 | 0 | 0 |
| 74 | rev-74-2-577d7fe2 | 0 | 0 | 0 |
| 75 | clean-75-5-c4e31744 | 0 | 0 | 0 |
| 76 | clean-76-5-1ca74161 | 0 | 0 | 0 |
| 77 | rev-77-2-5d61a8a0 | 0 | 0 | 0 |
| 78 | v-78-1-272e77e5 | 0 | 0 | 0 |
| 79 | v-79-4-cd5f4425 | 0 | 0 | 0 |
| 80 | rev-80-3-0c6ac775 | 0 | 0 | 0 |
| 81 | v-81-1-b5e1f255 | 0 | 0 | 0 |
| 82 | v-82-4-79e57418 | 0 | 0 | 1 |
| 83 | v-83-4-9c39c843 | 0 | 0 | 1 |
| 84 | clean-84-4-f08a214f | 0 | 0 | 0 |
| 85 | rev-85-2-e9a4f533 | 0 | 0 | 0 |
| 86 | rev-86-2-70a8880e | 0 | 0 | 0 |
| 87 | v-87-1-30af2513 | 0 | 0 | 0 |
| 88 | v-88-4-90c23e78 | 0 | 0 | 0 |
| 89 | rev-89-3-25894a6f | 0 | 0 | 0 |
| 90 | rev-90-3-2822af77 | 0 | 0 | 0 |
| 91 | rev-91-2-410c5cb6 | 0 | 0 | 0 |
| 92 | rev-92-3-dec6aa05 | 0 | 0 | 0 |
| 93 | v-93-1-1bf0db1a | 0 | 0 | 0 |
| 94 | rev-94-2-457796ef | 0 | 0 | 0 |
| 95 | rev-95-2-f58dd2e6 | 0 | 0 | 0 |
| 96 | rev-96-2-81bdc279 | 0 | 0 | 0 |
| 97 | clean-97-4-3cdbc4ef | 0 | 0 | 1 |
| 98 | rev-98-2-3b1485fe | 0 | 0 | 0 |
| 99 | v-99-3-7a9e1876 | 0 | 0 | 1 |
| 100 | v-100-4-b44b01e6 | 0 | 0 | 0 |
| 101 | clean-101-5-b614f523 | 0 | 0 | 0 |
| 102 | v-102-4-2226f1a1 | 0 | 0 | 0 |
| 103 | v-103-1-93b5d789 | 0 | 0 | 0 |
| 104 | v-104-8-e962fdb0 | 0 | 0 | 0 |
| 105 | v-105-4-5ccc037e | 0 | 0 | 0 |
| 106 | v-106-4-de6184be | 0 | 0 | 0 |
| 107 | v-107-4-11b79ab4 | 0 | 0 | 0 |
| 108 | v-108-4-cf30fd2a | 0 | 0 | 0 |
| 109 | v-109-4-e9971201 | 0 | 0 | 0 |
| 110 | v-110-4-4fb5bab5 | 0 | 0 | 0 |
| 111 | v-111-4-24b2d1f7 | 0 | 0 | 0 |
| 112 | v-112-4-b6323e65 | 0 | 0 | 0 |
| 113 | v-113-1-89b8e07f | 0 | 0 | 0 |
| 114 | v-114-4-524316f0 | 0 | 0 | 0 |
| 115 | rev-115-3-54c7c4bf | 0 | 0 | 0 |
| 116 | v-116-1-b589cedd | 0 | 0 | 0 |
| 117 | v-117-1-dec3e80a | 0 | 0 | 0 |
| 118 | v-118-1-a763b99e | 0 | 0 | 0 |
| 119 | rev-119-3-9e75a1b6 | 0 | 0 | 0 |
| 120 | rev-120-3-fb59ff9d | 0 | 0 | 0 |
| 121 | rev-121-3-320c6963 | 0 | 0 | 0 |
| 122 | v-122-1-bd96d805 | 0 | 0 | 1 |
| 123 | v-123-4-88cfaf77 | 0 | 0 | 0 |
| 124 | clean-124-8-63cacc34 | 0 | 0 | 0 |
| 125 | v-125-4-82167183 | 0 | 0 | 0 |
| 126 | rev-126-2-b208f536 | 0 | 0 | 0 |
| 127 | rev-127-3-a3ee0582 | 0 | 0 | 0 |
| 128 | v-128-4-1eefc229 | 0 | 0 | 0 |
| 129 | rev-129-2-a1230b9b | 0 | 0 | 0 |
| 130 | v-130-4-fe5b1a77 | 0 | 0 | 0 |
| 131 | rev-131-2-66b81d48 | 0 | 0 | 0 |
| 132 | rev-132-2-f125e03c | 0 | 0 | 0 |
| 133 | rev-133-3-a4b1f945 | 0 | 0 | 0 |
| 134 | rev-134-2-1bb7553c | 0 | 0 | 0 |
| 135 | v-135-4-d1c4c57e | 0 | 0 | 0 |
| 136 | rev-136-2-09dd6ba5 | 0 | 0 | 0 |
| 137 | v-137-4-503337e1 | 0 | 0 | 0 |
| 138 | v-138-1-ebfd77b2 | 0 | 0 | 0 |
| 139 | rev-139-3-37df40a4 | 0 | 0 | 0 |
| 140 | rev-140-2-18986c9f | 0 | 0 | 0 |
| 141 | v-141-4-34989d32 | 0 | 0 | 0 |
| 142 | v-142-1-3c60fbd5 | 0 | 0 | 0 |
| 143 | rev-143-2-684cc21a | 0 | 0 | 0 |
| 144 | rev-144-3-94537e1e | 0 | 0 | 0 |
| 145 | v-145-4-8158ebec | 0 | 0 | 0 |
| 146 | rev-146-2-f0cf798b | 0 | 0 | 0 |
| 147 | v-147-1-e082a92e | 0 | 0 | 0 |
| 148 | clean-148-5-b09119b8 | 0 | 0 | 0 |
| 149 | v-149-4-d469a9c6 | 0 | 0 | 1 |
| 150 | rev-150-2-954a32a8 | 0 | 0 | 0 |
| 151 | v-151-4-c62c2e52 | 0 | 0 | 0 |
| 152 | rev-152-2-3cabae95 | 0 | 0 | 0 |
| 153 | rev-153-3-cbd7a48e | 0 | 0 | 1 |
| 154 | v-154-4-840579b4 | 0 | 0 | 0 |
| 155 | v-155-4-f6d6b7d4 | 0 | 0 | 0 |
| 156 | rev-156-2-fa4b0150 | 0 | 0 | 0 |
| 157 | v-157-4-19d13ad7 | 0 | 0 | 0 |
| 158 | rev-158-2-0e2579e4 | 0 | 0 | 0 |
| 159 | clean-159-5-157edd2d | 0 | 0 | 0 |
| 160 | clean-160-5-6cebe283 | 0 | 0 | 0 |
| 161 | v-161-4-76f11abe | 0 | 0 | 1 |
| 162 | v-162-1-9cf8b7ae | 0 | 0 | 0 |
| 163 | v-163-7-22649b5b | 0 | 0 | 0 |
| 164 | clean-164-5-d9c46ef3 | 0 | 0 | 1 |
| 165 | rev-165-2-9207fd37 | 0 | 0 | 0 |
| 166 | rev-166-3-7aabb96e | 0 | 0 | 0 |
| 167 | rev-167-3-9c1e5b67 | 0 | 0 | 0 |
| 168 | v-168-4-80c430c0 | 0 | 0 | 0 |
| 169 | rev-169-2-c16efded | 0 | 0 | 0 |
| 170 | v-170-4-101365ce | 0 | 0 | 0 |
| 171 | clean-171-5-c7f30699 | 0 | 0 | 1 |
| 172 | rev-172-2-1a277912 | 0 | 0 | 0 |
| 173 | v-173-4-cf088098 | 0 | 0 | 0 |
| 174 | clean-174-4-32d14e87 | 0 | 0 | 0 |
| 175 | v-175-4-98cc06d0 | 0 | 0 | 0 |
| 176 | v-176-4-67de1a91 | 0 | 0 | 0 |
| 177 | v-177-1-8d7f7dff | 0 | 0 | 0 |
| 178 | rev-178-2-d69ff758 | 0 | 0 | 0 |
| 179 | v-179-4-2dc52033 | 0 | 0 | 0 |
| 180 | v-180-4-40394543 | 0 | 0 | 0 |
| 181 | v-181-4-ed8181c2 | 0 | 0 | 1 |
| 182 | v-182-4-8e2419b5 | 0 | 0 | 0 |
| 183 | rev-183-3-4b193719 | 0 | 0 | 0 |
| 184 | v-184-4-47fc480e | 0 | 0 | 0 |
| 185 | v-185-4-2ab0d9ed | 0 | 0 | 0 |
| 186 | v-186-1-ef560e5a | 0 | 0 | 0 |
| 187 | rev-187-2-da679188 | 0 | 0 | 0 |
| 188 | rev-188-3-db8a04ea | 0 | 0 | 0 |
| 189 | rev-189-2-f8f896e7 | 0 | 0 | 0 |
| 190 | v-190-1-f72faf16 | 0 | 0 | 0 |
| 191 | v-191-1-5c4b17d5 | 0 | 0 | 0 |
| 192 | v-192-1-4f481cc7 | 0 | 0 | 0 |
| 193 | v-193-4-2840eeb2 | 0 | 0 | 0 |
| 194 | rev-194-3-acda9f0f | 0 | 0 | 0 |
| 195 | v-195-4-74abdb9e | 0 | 0 | 0 |
| 196 | rev-196-2-bd117daf | 0 | 0 | 0 |
| 197 | rev-197-3-9bd8d241 | 0 | 0 | 0 |
| 198 | rev-198-3-0f2c1cf8 | 0 | 0 | 0 |
| 199 | rev-199-2-6c431ef1 | 0 | 0 | 0 |
| 200 | v-200-1-add5be8d | 0 | 0 | 0 |

- 元标记违规章：无（含 artifact）
- 重复长段落违规章：无
- 时间线矛盾诊断章：[32, 50, 56, 82, 83, 97, 99, 122, 149, 153, 161, 164, 171, 181]

## 自适应门禁数据面（Task 168；只供 Task 169 判定使用）

本段只展示 gate 输入信号，不输出 pass/fail/halt，不改变 enforce 行为。

### 样本充分性
| 信号域 | present | missing | insufficient | observation |
|--------|---------|---------|--------------|-------------|
| continuity | 164 | 36 | 0 | 0 |
| quality | 0 | 200 | 0 | 0 |
| literary | 200 | 0 | 0 | 0 |
| cleanliness | 200 | 0 | 0 | 0 |
| context | 20 | 180 | 0 | 0 |
| narrative | 0 | 200 | 0 | 0 |

### Continuity / Orphan 窗口
| 窗口 | health_min | health_median | P1_median | orphan_slope | orphan_delta | new_critical_mean |
|------|------------|---------------|-----------|--------------|--------------|-------------------|
| 1-5 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 2-6 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 3-7 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 4-8 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 5-9 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 6-10 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 7-11 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 8-12 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 9-13 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 10-14 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 11-15 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 12-16 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 13-17 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 14-18 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 15-19 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 16-20 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 17-21 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 18-22 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 19-23 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 20-24 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 21-25 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 22-26 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 23-27 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 24-28 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 25-29 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 26-30 | - | - | 0.000 | 0.800 | 4 | 0.000 |
| 27-31 | - | - | 0.000 | 0.400 | 0 | 0.000 |
| 28-32 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 29-33 | - | - | 0.000 | -0.400 | 0 | 0.000 |
| 30-34 | - | - | 0.000 | -1.200 | -4 | 0.000 |
| 31-35 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 32-36 | - | - | 0.000 | 1.615 | 6 | 0.000 |
| 33-37 | - | - | 0.000 | 0.462 | 0 | 0.000 |
| 34-38 | - | - | 0.000 | -3.000 | -6 | 0.000 |
| 35-39 | - | - | 0.000 | -1.800 | -6 | 0.000 |
| 36-40 | - | - | 0.000 | -1.200 | -6 | 0.000 |
| 37-41 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 38-42 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 39-43 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 40-44 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 41-45 | - | - | 0.000 | 0.257 | 1 | 0.000 |
| 42-46 | - | - | 0.000 | 0.100 | 0 | 0.000 |
| 43-47 | - | - | 0.000 | -0.029 | 0 | 0.000 |
| 44-48 | - | - | 0.000 | 0.900 | 3 | 0.000 |
| 45-49 | - | - | 0.000 | 0.200 | -1 | 0.000 |
| 46-50 | - | - | 0.000 | 0.400 | 0 | 0.000 |
| 47-51 | - | - | 0.000 | -0.086 | 1 | 0.000 |
| 48-52 | - | - | 0.000 | -0.700 | -4 | 0.000 |
| 49-53 | - | - | 0.000 | -0.029 | 0 | 0.000 |
| 50-54 | - | - | 0.000 | 1.800 | 6 | 0.000 |
| 51-55 | - | - | 0.000 | 0.500 | -1 | 0.000 |
| 52-56 | - | - | 0.000 | -0.000 | 0 | 0.000 |
| 53-57 | - | - | 0.000 | 0.500 | 6 | 0.000 |
| 54-58 | - | - | 0.000 | -0.300 | -1 | 0.000 |
| 55-59 | - | - | 0.000 | 0.171 | 0 | 0.000 |
| 56-60 | - | - | 0.000 | 0.000 | 3 | 0.000 |
| 57-61 | - | - | 0.000 | -1.286 | -3 | 0.000 |
| 58-62 | - | - | 0.000 | -0.214 | 0 | 0.000 |
| 59-63 | - | - | 0.000 | 0.100 | 2 | 0.000 |
| 60-64 | - | - | 0.000 | -0.600 | -3 | 0.000 |
| 61-65 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 62-66 | - | - | 0.000 | -0.171 | 0 | 0.000 |
| 63-67 | - | - | 0.000 | -0.571 | -2 | 0.000 |
| 64-68 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 65-69 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 66-70 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 67-71 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 68-72 | - | - | 0.000 | 2.100 | 7 | 0.000 |
| 69-73 | - | - | 0.000 | 0.700 | 0 | 0.000 |
| 70-74 | - | - | 0.000 | -0.000 | 0 | 0.000 |
| 71-75 | - | - | 0.000 | -0.700 | 0 | 0.000 |
| 72-76 | - | - | 0.000 | -2.100 | -7 | 0.000 |
| 73-77 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 74-78 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 75-79 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 76-80 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 77-81 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 78-82 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 79-83 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 80-84 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 81-85 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 82-86 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 83-87 | - | - | 0.000 | 0.257 | 1 | 0.000 |
| 84-88 | - | - | 0.000 | 0.100 | 0 | 0.000 |
| 85-89 | - | - | 0.000 | 0.071 | 0 | 0.000 |
| 86-90 | - | - | 0.000 | -0.286 | -1 | 0.000 |
| 87-91 | - | - | 0.000 | -0.286 | -1 | 0.000 |
| 88-92 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 89-93 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 90-94 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 91-95 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 92-96 | - | - | 0.000 | 2.100 | 7 | 0.000 |
| 93-97 | - | - | 0.000 | 0.700 | 0 | 0.000 |
| 94-98 | - | - | 0.000 | 0.700 | 0 | 0.000 |
| 95-99 | - | - | 0.000 | -0.600 | 0 | 0.000 |
| 96-100 | - | - | 0.000 | -1.400 | -7 | 0.000 |
| 97-101 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 98-102 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 99-103 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 100-104 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 101-105 | - | - | 0.000 | 1.400 | 7 | 0.000 |
| 102-106 | - | - | 0.000 | 0.700 | 0 | 0.000 |
| 103-107 | - | - | 0.000 | 0.700 | 0 | 0.000 |
| 104-108 | - | - | 0.000 | 0.686 | 5 | 0.000 |
| 105-109 | - | - | 0.000 | -0.900 | -7 | 0.000 |
| 106-110 | - | - | 0.000 | -0.143 | 0 | 0.000 |
| 107-111 | - | - | 0.000 | -1.200 | -4 | 0.000 |
| 108-112 | - | - | 0.000 | -0.900 | -5 | 0.000 |
| 109-113 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 110-114 | - | - | 0.000 | -0.100 | 0 | 0.000 |
| 111-115 | - | - | 0.000 | -0.200 | -1 | 0.000 |
| 112-116 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 113-117 | - | - | 0.000 | 1.600 | 8 | 0.000 |
| 114-118 | - | - | 0.000 | 0.800 | 0 | 0.000 |
| 115-119 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 116-120 | - | - | 0.000 | 0.600 | 7 | 0.000 |
| 117-121 | - | - | 0.000 | -0.900 | -8 | 0.000 |
| 118-122 | - | - | 0.000 | -0.000 | 0 | 0.000 |
| 119-123 | - | - | 0.000 | 0.700 | 7 | 0.000 |
| 120-124 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 121-125 | - | - | 0.000 | 3.500 | 7 | 0.000 |
| 122-126 | - | - | 0.000 | -0.538 | 0 | 0.000 |
| 123-127 | - | - | 0.000 | -1.885 | -7 | 0.000 |
| 124-128 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 125-129 | - | - | 0.000 | 2.857 | 8 | 0.000 |
| 126-130 | - | - | 0.000 | 0.800 | 0 | 0.000 |
| 127-131 | - | - | 0.000 | -0.229 | 0 | 0.000 |
| 128-132 | - | - | 0.000 | -2.400 | -8 | 0.000 |
| 129-133 | - | - | 0.000 | -1.600 | -8 | 0.000 |
| 130-134 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 131-135 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 132-136 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 133-137 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 134-138 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 135-139 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 136-140 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 137-141 | - | - | 0.000 | 1.429 | 5 | 0.000 |
| 138-142 | - | - | 0.000 | 0.429 | 0 | 0.000 |
| 139-143 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 140-144 | - | - | 0.000 | 0.343 | 3 | 0.000 |
| 141-145 | - | - | 0.000 | -0.357 | -2 | 0.000 |
| 142-146 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 143-147 | - | - | 0.000 | 0.929 | 4 | 0.000 |
| 144-148 | - | - | 0.000 | -0.171 | -3 | 0.000 |
| 145-149 | - | - | 0.000 | -0.700 | 0 | 0.000 |
| 146-150 | - | - | 0.000 | -0.500 | 1 | 0.000 |
| 147-151 | - | - | 0.000 | -1.300 | -7 | 0.000 |
| 148-152 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 149-153 | - | - | 0.000 | -0.100 | 0 | 0.000 |
| 150-154 | - | - | 0.000 | -0.200 | -1 | 0.200 |
| 151-155 | - | - | 0.000 | 0.000 | 0 | 0.200 |
| 152-156 | - | - | 0.000 | 1.000 | 5 | 0.200 |
| 153-157 | - | - | 0.000 | 1.500 | 5 | 0.250 |
| 154-158 | - | - | 0.000 | 0.143 | 0 | 0.250 |
| 155-159 | - | - | 0.000 | 0.500 | 5 | 0.000 |
| 156-160 | - | - | 0.000 | -0.857 | -5 | 0.000 |
| 157-161 | - | - | 0.000 | -0.500 | 0 | 0.250 |
| 158-162 | - | - | 0.000 | 0.100 | 3 | 0.400 |
| 159-163 | - | - | 0.000 | -0.700 | -5 | 0.400 |
| 160-164 | - | - | 0.000 | 0.300 | 0 | 0.500 |
| 161-165 | - | - | 0.000 | 1.029 | 5 | 0.500 |
| 162-166 | - | - | 0.000 | -0.100 | -3 | 0.500 |
| 163-167 | - | - | 0.000 | 0.357 | 0 | 0.333 |
| 164-168 | - | - | 0.000 | -0.714 | -3 | 0.333 |
| 165-169 | - | - | 0.000 | -0.714 | -3 | 0.333 |
| 166-170 | - | - | 0.000 | 0.000 | 0 | 0.333 |
| 167-171 | - | - | 0.000 | 0.143 | 1 | 0.000 |
| 168-172 | - | - | 0.000 | -0.257 | -2 | 0.000 |
| 169-173 | - | - | 0.000 | -0.300 | 0 | 0.000 |
| 170-174 | - | - | 0.000 | -0.300 | 0 | 0.000 |
| 171-175 | - | - | 0.000 | -0.900 | -3 | 0.000 |
| 172-176 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 173-177 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 174-178 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 175-179 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 176-180 | - | - | 0.000 | 1.143 | 4 | 0.000 |
| 177-181 | - | - | 0.000 | 1.143 | 4 | 0.000 |
| 178-182 | - | - | 0.000 | -0.286 | 0 | 0.000 |
| 179-183 | - | - | 0.000 | -0.400 | 0 | 0.000 |
| 180-184 | - | - | 0.000 | -1.429 | -4 | 0.000 |
| 181-185 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 182-186 | - | - | 0.000 | 0.400 | 2 | 0.000 |
| 183-187 | - | - | 0.000 | 0.171 | 0 | 0.000 |
| 184-188 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 185-189 | - | - | 0.000 | -0.171 | 0 | 0.000 |
| 186-190 | - | - | 0.000 | -0.400 | -2 | 0.000 |
| 187-191 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 188-192 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 189-193 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 190-194 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 191-195 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 192-196 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 193-197 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 194-198 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 195-199 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 196-200 | - | - | 0.000 | 0.000 | 0 | 0.000 |

### Quality Debt 窗口
| 窗口 | degraded% | convergence% | qg_false% |
|------|-----------|--------------|-----------|
| 1-5 | - | - | - |
| 2-6 | - | - | - |
| 3-7 | - | - | - |
| 4-8 | - | - | - |
| 5-9 | - | - | - |
| 6-10 | - | - | - |
| 7-11 | - | - | - |
| 8-12 | - | - | - |
| 9-13 | - | - | - |
| 10-14 | - | - | - |
| 11-15 | - | - | - |
| 12-16 | - | - | - |
| 13-17 | - | - | - |
| 14-18 | - | - | - |
| 15-19 | - | - | - |
| 16-20 | - | - | - |
| 17-21 | - | - | - |
| 18-22 | - | - | - |
| 19-23 | - | - | - |
| 20-24 | - | - | - |
| 21-25 | - | - | - |
| 22-26 | - | - | - |
| 23-27 | - | - | - |
| 24-28 | - | - | - |
| 25-29 | - | - | - |
| 26-30 | - | - | - |
| 27-31 | - | - | - |
| 28-32 | - | - | - |
| 29-33 | - | - | - |
| 30-34 | - | - | - |
| 31-35 | - | - | - |
| 32-36 | - | - | - |
| 33-37 | - | - | - |
| 34-38 | - | - | - |
| 35-39 | - | - | - |
| 36-40 | - | - | - |
| 37-41 | - | - | - |
| 38-42 | - | - | - |
| 39-43 | - | - | - |
| 40-44 | - | - | - |
| 41-45 | - | - | - |
| 42-46 | - | - | - |
| 43-47 | - | - | - |
| 44-48 | - | - | - |
| 45-49 | - | - | - |
| 46-50 | - | - | - |
| 47-51 | - | - | - |
| 48-52 | - | - | - |
| 49-53 | - | - | - |
| 50-54 | - | - | - |
| 51-55 | - | - | - |
| 52-56 | - | - | - |
| 53-57 | - | - | - |
| 54-58 | - | - | - |
| 55-59 | - | - | - |
| 56-60 | - | - | - |
| 57-61 | - | - | - |
| 58-62 | - | - | - |
| 59-63 | - | - | - |
| 60-64 | - | - | - |
| 61-65 | - | - | - |
| 62-66 | - | - | - |
| 63-67 | - | - | - |
| 64-68 | - | - | - |
| 65-69 | - | - | - |
| 66-70 | - | - | - |
| 67-71 | - | - | - |
| 68-72 | - | - | - |
| 69-73 | - | - | - |
| 70-74 | - | - | - |
| 71-75 | - | - | - |
| 72-76 | - | - | - |
| 73-77 | - | - | - |
| 74-78 | - | - | - |
| 75-79 | - | - | - |
| 76-80 | - | - | - |
| 77-81 | - | - | - |
| 78-82 | - | - | - |
| 79-83 | - | - | - |
| 80-84 | - | - | - |
| 81-85 | - | - | - |
| 82-86 | - | - | - |
| 83-87 | - | - | - |
| 84-88 | - | - | - |
| 85-89 | - | - | - |
| 86-90 | - | - | - |
| 87-91 | - | - | - |
| 88-92 | - | - | - |
| 89-93 | - | - | - |
| 90-94 | - | - | - |
| 91-95 | - | - | - |
| 92-96 | - | - | - |
| 93-97 | - | - | - |
| 94-98 | - | - | - |
| 95-99 | - | - | - |
| 96-100 | - | - | - |
| 97-101 | - | - | - |
| 98-102 | - | - | - |
| 99-103 | - | - | - |
| 100-104 | - | - | - |
| 101-105 | - | - | - |
| 102-106 | - | - | - |
| 103-107 | - | - | - |
| 104-108 | - | - | - |
| 105-109 | - | - | - |
| 106-110 | - | - | - |
| 107-111 | - | - | - |
| 108-112 | - | - | - |
| 109-113 | - | - | - |
| 110-114 | - | - | - |
| 111-115 | - | - | - |
| 112-116 | - | - | - |
| 113-117 | - | - | - |
| 114-118 | - | - | - |
| 115-119 | - | - | - |
| 116-120 | - | - | - |
| 117-121 | - | - | - |
| 118-122 | - | - | - |
| 119-123 | - | - | - |
| 120-124 | - | - | - |
| 121-125 | - | - | - |
| 122-126 | - | - | - |
| 123-127 | - | - | - |
| 124-128 | - | - | - |
| 125-129 | - | - | - |
| 126-130 | - | - | - |
| 127-131 | - | - | - |
| 128-132 | - | - | - |
| 129-133 | - | - | - |
| 130-134 | - | - | - |
| 131-135 | - | - | - |
| 132-136 | - | - | - |
| 133-137 | - | - | - |
| 134-138 | - | - | - |
| 135-139 | - | - | - |
| 136-140 | - | - | - |
| 137-141 | - | - | - |
| 138-142 | - | - | - |
| 139-143 | - | - | - |
| 140-144 | - | - | - |
| 141-145 | - | - | - |
| 142-146 | - | - | - |
| 143-147 | - | - | - |
| 144-148 | - | - | - |
| 145-149 | - | - | - |
| 146-150 | - | - | - |
| 147-151 | - | - | - |
| 148-152 | - | - | - |
| 149-153 | - | - | - |
| 150-154 | - | - | - |
| 151-155 | - | - | - |
| 152-156 | - | - | - |
| 153-157 | - | - | - |
| 154-158 | - | - | - |
| 155-159 | - | - | - |
| 156-160 | - | - | - |
| 157-161 | - | - | - |
| 158-162 | - | - | - |
| 159-163 | - | - | - |
| 160-164 | - | - | - |
| 161-165 | - | - | - |
| 162-166 | - | - | - |
| 163-167 | - | - | - |
| 164-168 | - | - | - |
| 165-169 | - | - | - |
| 166-170 | - | - | - |
| 167-171 | - | - | - |
| 168-172 | - | - | - |
| 169-173 | - | - | - |
| 170-174 | - | - | - |
| 171-175 | - | - | - |
| 172-176 | - | - | - |
| 173-177 | - | - | - |
| 174-178 | - | - | - |
| 175-179 | - | - | - |
| 176-180 | - | - | - |
| 177-181 | - | - | - |
| 178-182 | - | - | - |
| 179-183 | - | - | - |
| 180-184 | - | - | - |
| 181-185 | - | - | - |
| 182-186 | - | - | - |
| 183-187 | - | - | - |
| 184-188 | - | - | - |
| 185-189 | - | - | - |
| 186-190 | - | - | - |
| 187-191 | - | - | - |
| 188-192 | - | - | - |
| 189-193 | - | - | - |
| 190-194 | - | - | - |
| 191-195 | - | - | - |
| 192-196 | - | - | - |
| 193-197 | - | - | - |
| 194-198 | - | - | - |
| 195-199 | - | - | - |
| 196-200 | - | - | - |

### Literary / Cleanliness 窗口
| 窗口 | literary | conceptual | meta | duplicate | timeline(obs) |
|------|----------|------------|------|-----------|---------------|
| 1-5 | 5.700 | 5.100 | 0 | 0 | 0 |
| 2-6 | 5.900 | 5.300 | 0 | 0 | 0 |
| 3-7 | 6.100 | 5.800 | 0 | 0 | 0 |
| 4-8 | 5.900 | 5.100 | 0 | 0 | 0 |
| 5-9 | 5.900 | 5.000 | 0 | 0 | 0 |
| 6-10 | 5.900 | 5.000 | 0 | 0 | 0 |
| 7-11 | 5.500 | 4.700 | 0 | 0 | 0 |
| 8-12 | 5.300 | 4.100 | 0 | 0 | 0 |
| 9-13 | 5.300 | 4.300 | 0 | 0 | 0 |
| 10-14 | 5.300 | 4.300 | 0 | 0 | 0 |
| 11-15 | 5.100 | 4.200 | 0 | 0 | 0 |
| 12-16 | 5.300 | 4.700 | 0 | 0 | 0 |
| 13-17 | 5.300 | 4.900 | 0 | 0 | 0 |
| 14-18 | 5.500 | 5.100 | 0 | 0 | 0 |
| 15-19 | 5.500 | 5.500 | 0 | 0 | 0 |
| 16-20 | 5.900 | 5.800 | 0 | 0 | 0 |
| 17-21 | 5.900 | 5.300 | 0 | 0 | 0 |
| 18-22 | 5.900 | 5.600 | 0 | 0 | 0 |
| 19-23 | 5.900 | 5.500 | 0 | 0 | 0 |
| 20-24 | 6.100 | 5.700 | 0 | 0 | 0 |
| 21-25 | 5.900 | 5.500 | 0 | 0 | 0 |
| 22-26 | 5.900 | 5.600 | 0 | 0 | 0 |
| 23-27 | 6.000 | 5.400 | 0 | 0 | 0 |
| 24-28 | 5.800 | 5.200 | 0 | 0 | 0 |
| 25-29 | 5.600 | 4.600 | 0 | 0 | 0 |
| 26-30 | 5.600 | 4.600 | 0 | 0 | 0 |
| 27-31 | 5.600 | 4.600 | 0 | 0 | 0 |
| 28-32 | 5.500 | 4.300 | 0 | 0 | 1 |
| 29-33 | 5.500 | 4.300 | 0 | 0 | 1 |
| 30-34 | 5.500 | 4.400 | 0 | 0 | 1 |
| 31-35 | 5.500 | 4.400 | 0 | 0 | 1 |
| 32-36 | 5.500 | 4.700 | 0 | 0 | 1 |
| 33-37 | 5.500 | 4.700 | 0 | 0 | 0 |
| 34-38 | 5.500 | 4.700 | 0 | 0 | 0 |
| 35-39 | 5.500 | 5.000 | 0 | 0 | 0 |
| 36-40 | 5.500 | 5.300 | 0 | 0 | 0 |
| 37-41 | 5.500 | 5.400 | 0 | 0 | 0 |
| 38-42 | 5.500 | 5.500 | 0 | 0 | 0 |
| 39-43 | 5.500 | 5.400 | 0 | 0 | 0 |
| 40-44 | 5.500 | 5.000 | 0 | 0 | 0 |
| 41-45 | 5.500 | 4.600 | 0 | 0 | 0 |
| 42-46 | 5.500 | 4.100 | 0 | 0 | 0 |
| 43-47 | 5.500 | 4.400 | 0 | 0 | 0 |
| 44-48 | 5.500 | 4.800 | 0 | 0 | 0 |
| 45-49 | 5.500 | 5.200 | 0 | 0 | 0 |
| 46-50 | 5.300 | 5.100 | 0 | 0 | 1 |
| 47-51 | 5.300 | 5.200 | 0 | 0 | 1 |
| 48-52 | 5.400 | 5.100 | 0 | 0 | 1 |
| 49-53 | 5.500 | 4.800 | 0 | 0 | 1 |
| 50-54 | 5.500 | 4.800 | 0 | 0 | 1 |
| 51-55 | 5.600 | 5.300 | 0 | 0 | 0 |
| 52-56 | 5.500 | 5.300 | 0 | 0 | 1 |
| 53-57 | 5.600 | 5.300 | 0 | 0 | 1 |
| 54-58 | 5.500 | 5.200 | 0 | 0 | 1 |
| 55-59 | 5.500 | 4.800 | 0 | 0 | 1 |
| 56-60 | 5.600 | 4.900 | 0 | 0 | 1 |
| 57-61 | 5.800 | 5.500 | 0 | 0 | 0 |
| 58-62 | 5.400 | 5.200 | 0 | 0 | 0 |
| 59-63 | 5.400 | 5.300 | 0 | 0 | 0 |
| 60-64 | 5.600 | 6.000 | 0 | 0 | 0 |
| 61-65 | 5.800 | 5.800 | 0 | 0 | 0 |
| 62-66 | 5.700 | 5.200 | 0 | 0 | 0 |
| 63-67 | 5.900 | 5.400 | 0 | 0 | 0 |
| 64-68 | 5.900 | 5.800 | 0 | 0 | 0 |
| 65-69 | 5.700 | 5.300 | 0 | 0 | 0 |
| 66-70 | 5.500 | 5.600 | 0 | 0 | 0 |
| 67-71 | 5.600 | 5.600 | 0 | 0 | 0 |
| 68-72 | 5.600 | 5.800 | 0 | 0 | 0 |
| 69-73 | 5.600 | 5.400 | 0 | 0 | 0 |
| 70-74 | 5.800 | 5.600 | 0 | 0 | 0 |
| 71-75 | 5.800 | 5.000 | 0 | 0 | 0 |
| 72-76 | 5.700 | 5.300 | 0 | 0 | 0 |
| 73-77 | 5.700 | 5.100 | 0 | 0 | 0 |
| 74-78 | 5.900 | 5.700 | 0 | 0 | 0 |
| 75-79 | 5.700 | 5.500 | 0 | 0 | 0 |
| 76-80 | 5.700 | 5.500 | 0 | 0 | 0 |
| 77-81 | 5.500 | 5.100 | 0 | 0 | 0 |
| 78-82 | 5.400 | 4.900 | 0 | 0 | 1 |
| 79-83 | 5.200 | 4.300 | 0 | 0 | 2 |
| 80-84 | 5.200 | 4.400 | 0 | 0 | 2 |
| 81-85 | 5.300 | 5.000 | 0 | 0 | 2 |
| 82-86 | 5.700 | 5.600 | 0 | 0 | 2 |
| 83-87 | 5.800 | 5.700 | 0 | 0 | 1 |
| 84-88 | 6.000 | 6.400 | 0 | 0 | 0 |
| 85-89 | 6.000 | 6.500 | 0 | 0 | 0 |
| 86-90 | 5.900 | 6.000 | 0 | 0 | 0 |
| 87-91 | 5.700 | 5.900 | 0 | 0 | 0 |
| 88-92 | 5.700 | 6.400 | 0 | 0 | 0 |
| 89-93 | 5.500 | 6.100 | 0 | 0 | 0 |
| 90-94 | 5.600 | 6.400 | 0 | 0 | 0 |
| 91-95 | 5.800 | 6.700 | 0 | 0 | 0 |
| 92-96 | 5.900 | 6.500 | 0 | 0 | 0 |
| 93-97 | 5.700 | 6.300 | 0 | 0 | 1 |
| 94-98 | 5.700 | 6.300 | 0 | 0 | 1 |
| 95-99 | 5.600 | 6.100 | 0 | 0 | 2 |
| 96-100 | 5.600 | 6.400 | 0 | 0 | 2 |
| 97-101 | 5.500 | 6.200 | 0 | 0 | 2 |
| 98-102 | 5.700 | 5.900 | 0 | 0 | 1 |
| 99-103 | 5.900 | 5.800 | 0 | 0 | 1 |
| 100-104 | 5.900 | 5.800 | 0 | 0 | 0 |
| 101-105 | 5.700 | 5.200 | 0 | 0 | 0 |
| 102-106 | 5.700 | 5.100 | 0 | 0 | 0 |
| 103-107 | 5.700 | 5.000 | 0 | 0 | 0 |
| 104-108 | 5.500 | 4.600 | 0 | 0 | 0 |
| 105-109 | 5.400 | 4.100 | 0 | 0 | 0 |
| 106-110 | 5.400 | 4.100 | 0 | 0 | 0 |
| 107-111 | 5.400 | 4.100 | 0 | 0 | 0 |
| 108-112 | 5.400 | 4.100 | 0 | 0 | 0 |
| 109-113 | 5.400 | 4.500 | 0 | 0 | 0 |
| 110-114 | 5.600 | 5.100 | 0 | 0 | 0 |
| 111-115 | 5.400 | 5.000 | 0 | 0 | 0 |
| 112-116 | 5.400 | 5.100 | 0 | 0 | 0 |
| 113-117 | 5.400 | 5.200 | 0 | 0 | 0 |
| 114-118 | 5.400 | 5.200 | 0 | 0 | 0 |
| 115-119 | 5.300 | 4.800 | 0 | 0 | 0 |
| 116-120 | 5.600 | 5.300 | 0 | 0 | 0 |
| 117-121 | 5.600 | 5.300 | 0 | 0 | 0 |
| 118-122 | 5.600 | 5.200 | 0 | 0 | 1 |
| 119-123 | 5.700 | 5.400 | 0 | 0 | 1 |
| 120-124 | 5.700 | 5.200 | 0 | 0 | 1 |
| 121-125 | 5.600 | 4.700 | 0 | 0 | 1 |
| 122-126 | 5.600 | 4.700 | 0 | 0 | 1 |
| 123-127 | 5.600 | 4.800 | 0 | 0 | 0 |
| 124-128 | 5.500 | 4.600 | 0 | 0 | 0 |
| 125-129 | 5.500 | 4.700 | 0 | 0 | 0 |
| 126-130 | 5.500 | 5.300 | 0 | 0 | 0 |
| 127-131 | 5.500 | 5.600 | 0 | 0 | 0 |
| 128-132 | 5.500 | 5.500 | 0 | 0 | 0 |
| 129-133 | 5.500 | 5.600 | 0 | 0 | 0 |
| 130-134 | 5.700 | 5.900 | 0 | 0 | 0 |
| 131-135 | 5.900 | 5.900 | 0 | 0 | 0 |
| 132-136 | 5.900 | 5.900 | 0 | 0 | 0 |
| 133-137 | 5.900 | 6.000 | 0 | 0 | 0 |
| 134-138 | 6.100 | 5.700 | 0 | 0 | 0 |
| 135-139 | 5.900 | 5.300 | 0 | 0 | 0 |
| 136-140 | 5.700 | 4.900 | 0 | 0 | 0 |
| 137-141 | 5.700 | 5.000 | 0 | 0 | 0 |
| 138-142 | 5.700 | 5.000 | 0 | 0 | 0 |
| 139-143 | 5.500 | 5.200 | 0 | 0 | 0 |
| 140-144 | 5.700 | 5.400 | 0 | 0 | 0 |
| 141-145 | 5.700 | 5.300 | 0 | 0 | 0 |
| 142-146 | 5.500 | 4.800 | 0 | 0 | 0 |
| 143-147 | 5.600 | 5.000 | 0 | 0 | 0 |
| 144-148 | 5.600 | 5.200 | 0 | 0 | 0 |
| 145-149 | 5.400 | 4.900 | 0 | 0 | 1 |
| 146-150 | 5.400 | 4.800 | 0 | 0 | 1 |
| 147-151 | 5.600 | 4.800 | 0 | 0 | 1 |
| 148-152 | 5.500 | 5.000 | 0 | 0 | 1 |
| 149-153 | 5.500 | 4.500 | 0 | 0 | 2 |
| 150-154 | 5.500 | 4.800 | 0 | 0 | 1 |
| 151-155 | 5.500 | 5.200 | 0 | 0 | 1 |
| 152-156 | 5.300 | 5.200 | 0 | 0 | 1 |
| 153-157 | 5.500 | 5.000 | 0 | 0 | 1 |
| 154-158 | 5.700 | 5.600 | 0 | 0 | 0 |
| 155-159 | 5.600 | 5.500 | 0 | 0 | 0 |
| 156-160 | 5.400 | 5.100 | 0 | 0 | 0 |
| 157-161 | 5.600 | 5.100 | 0 | 0 | 1 |
| 158-162 | 5.400 | 5.200 | 0 | 0 | 1 |
| 159-163 | 5.400 | 5.100 | 0 | 0 | 1 |
| 160-164 | 5.500 | 5.500 | 0 | 0 | 2 |
| 161-165 | 5.700 | 5.600 | 0 | 0 | 2 |
| 162-166 | 5.700 | 5.700 | 0 | 0 | 1 |
| 163-167 | 5.900 | 5.500 | 0 | 0 | 1 |
| 164-168 | 5.700 | 5.500 | 0 | 0 | 1 |
| 165-169 | 5.700 | 5.400 | 0 | 0 | 0 |
| 166-170 | 5.700 | 5.900 | 0 | 0 | 0 |
| 167-171 | 5.800 | 6.100 | 0 | 0 | 1 |
| 168-172 | 5.600 | 6.400 | 0 | 0 | 1 |
| 169-173 | 5.800 | 6.600 | 0 | 0 | 1 |
| 170-174 | 5.800 | 6.200 | 0 | 0 | 1 |
| 171-175 | 6.000 | 5.900 | 0 | 0 | 1 |
| 172-176 | 5.900 | 5.700 | 0 | 0 | 0 |
| 173-177 | 5.900 | 5.700 | 0 | 0 | 0 |
| 174-178 | 5.700 | 5.100 | 0 | 0 | 0 |
| 175-179 | 5.700 | 5.200 | 0 | 0 | 0 |
| 176-180 | 5.500 | 4.900 | 0 | 0 | 0 |
| 177-181 | 5.500 | 4.800 | 0 | 0 | 1 |
| 178-182 | 5.600 | 4.900 | 0 | 0 | 1 |
| 179-183 | 5.800 | 5.000 | 0 | 0 | 1 |
| 180-184 | 5.900 | 5.500 | 0 | 0 | 1 |
| 181-185 | 5.900 | 5.500 | 0 | 0 | 1 |
| 182-186 | 5.900 | 6.000 | 0 | 0 | 0 |
| 183-187 | 5.800 | 5.600 | 0 | 0 | 0 |
| 184-188 | 5.600 | 5.300 | 0 | 0 | 0 |
| 185-189 | 5.500 | 5.100 | 0 | 0 | 0 |
| 186-190 | 5.500 | 5.100 | 0 | 0 | 0 |
| 187-191 | 5.500 | 4.700 | 0 | 0 | 0 |
| 188-192 | 5.500 | 5.000 | 0 | 0 | 0 |
| 189-193 | 5.500 | 5.200 | 0 | 0 | 0 |
| 190-194 | 5.500 | 4.900 | 0 | 0 | 0 |
| 191-195 | 5.500 | 5.000 | 0 | 0 | 0 |
| 192-196 | 5.500 | 4.900 | 0 | 0 | 0 |
| 193-197 | 5.500 | 4.900 | 0 | 0 | 0 |
| 194-198 | 5.500 | 4.700 | 0 | 0 | 0 |
| 195-199 | 5.600 | 4.800 | 0 | 0 | 0 |
| 196-200 | 5.600 | 5.100 | 0 | 0 | 0 |

### Schedule Lifecycle 窗口
| 窗口 | injected | satisfied | missed | hit_rate | missed_rate | overdue_rate |
|------|----------|-----------|--------|----------|-------------|--------------|
| 1-5 | 0 | 0 | 0 | - | - | - |
| 2-6 | 0 | 0 | 0 | - | - | - |
| 3-7 | 0 | 0 | 0 | - | - | - |
| 4-8 | 0 | 0 | 0 | - | - | - |
| 5-9 | 0 | 0 | 0 | - | - | - |
| 6-10 | 0 | 0 | 0 | - | - | - |
| 7-11 | 0 | 0 | 0 | - | - | - |
| 8-12 | 0 | 0 | 0 | - | - | - |
| 9-13 | 0 | 0 | 0 | - | - | - |
| 10-14 | 0 | 0 | 0 | - | - | - |
| 11-15 | 0 | 0 | 0 | - | - | - |
| 12-16 | 0 | 0 | 0 | - | - | - |
| 13-17 | 0 | 0 | 0 | - | - | - |
| 14-18 | 0 | 0 | 0 | - | - | - |
| 15-19 | 0 | 0 | 0 | - | - | - |
| 16-20 | 0 | 0 | 0 | - | - | - |
| 17-21 | 0 | 0 | 0 | - | - | - |
| 18-22 | 0 | 0 | 0 | - | - | - |
| 19-23 | 0 | 0 | 0 | - | - | - |
| 20-24 | 0 | 0 | 0 | - | - | - |
| 21-25 | 0 | 0 | 0 | - | - | - |
| 22-26 | 0 | 0 | 0 | - | - | - |
| 23-27 | 0 | 0 | 0 | - | - | - |
| 24-28 | 0 | 0 | 0 | - | - | - |
| 25-29 | 0 | 0 | 0 | - | - | - |
| 26-30 | 0 | 0 | 0 | - | - | - |
| 27-31 | 0 | 0 | 0 | - | - | - |
| 28-32 | 0 | 0 | 0 | - | - | - |
| 29-33 | 0 | 0 | 0 | - | - | - |
| 30-34 | 0 | 0 | 0 | - | - | - |
| 31-35 | 0 | 0 | 0 | - | - | - |
| 32-36 | 0 | 0 | 0 | - | - | - |
| 33-37 | 0 | 0 | 0 | - | - | - |
| 34-38 | 0 | 0 | 0 | - | - | - |
| 35-39 | 0 | 0 | 0 | - | - | - |
| 36-40 | 0 | 0 | 0 | - | - | - |
| 37-41 | 0 | 0 | 0 | - | - | - |
| 38-42 | 0 | 0 | 0 | - | - | - |
| 39-43 | 0 | 0 | 0 | - | - | - |
| 40-44 | 0 | 0 | 0 | - | - | - |
| 41-45 | 0 | 0 | 0 | - | - | - |
| 42-46 | 0 | 0 | 0 | - | - | - |
| 43-47 | 0 | 0 | 0 | - | - | - |
| 44-48 | 0 | 0 | 0 | - | - | - |
| 45-49 | 0 | 0 | 0 | - | - | - |
| 46-50 | 0 | 0 | 0 | - | - | - |
| 47-51 | 0 | 0 | 0 | - | - | - |
| 48-52 | 0 | 0 | 0 | - | - | - |
| 49-53 | 0 | 0 | 0 | - | - | - |
| 50-54 | 0 | 0 | 0 | - | - | - |
| 51-55 | 0 | 0 | 0 | - | - | - |
| 52-56 | 0 | 0 | 0 | - | - | - |
| 53-57 | 0 | 0 | 0 | - | - | - |
| 54-58 | 0 | 0 | 0 | - | - | - |
| 55-59 | 0 | 0 | 0 | - | - | - |
| 56-60 | 0 | 0 | 0 | - | - | - |
| 57-61 | 0 | 0 | 0 | - | - | - |
| 58-62 | 0 | 0 | 0 | - | - | - |
| 59-63 | 0 | 0 | 0 | - | - | - |
| 60-64 | 0 | 0 | 0 | - | - | - |
| 61-65 | 0 | 0 | 0 | - | - | - |
| 62-66 | 0 | 0 | 0 | - | - | - |
| 63-67 | 0 | 0 | 0 | - | - | - |
| 64-68 | 0 | 0 | 0 | - | - | - |
| 65-69 | 0 | 0 | 0 | - | - | - |
| 66-70 | 0 | 0 | 0 | - | - | - |
| 67-71 | 0 | 0 | 0 | - | - | - |
| 68-72 | 0 | 0 | 0 | - | - | - |
| 69-73 | 0 | 0 | 0 | - | - | - |
| 70-74 | 0 | 0 | 0 | - | - | - |
| 71-75 | 0 | 0 | 0 | - | - | - |
| 72-76 | 0 | 0 | 0 | - | - | - |
| 73-77 | 0 | 0 | 0 | - | - | - |
| 74-78 | 0 | 0 | 0 | - | - | - |
| 75-79 | 0 | 0 | 0 | - | - | - |
| 76-80 | 0 | 0 | 0 | - | - | - |
| 77-81 | 0 | 0 | 0 | - | - | - |
| 78-82 | 0 | 0 | 0 | - | - | - |
| 79-83 | 0 | 0 | 0 | - | - | - |
| 80-84 | 0 | 0 | 0 | - | - | - |
| 81-85 | 0 | 0 | 0 | - | - | - |
| 82-86 | 0 | 0 | 0 | - | - | - |
| 83-87 | 0 | 0 | 0 | - | - | - |
| 84-88 | 0 | 0 | 0 | - | - | - |
| 85-89 | 0 | 0 | 0 | - | - | - |
| 86-90 | 0 | 0 | 0 | - | - | - |
| 87-91 | 0 | 0 | 0 | - | - | - |
| 88-92 | 0 | 0 | 0 | - | - | - |
| 89-93 | 0 | 0 | 0 | - | - | - |
| 90-94 | 0 | 0 | 0 | - | - | - |
| 91-95 | 0 | 0 | 0 | - | - | - |
| 92-96 | 0 | 0 | 0 | - | - | - |
| 93-97 | 0 | 0 | 0 | - | - | - |
| 94-98 | 0 | 0 | 0 | - | - | - |
| 95-99 | 0 | 0 | 0 | - | - | - |
| 96-100 | 0 | 0 | 0 | - | - | - |
| 97-101 | 0 | 0 | 0 | - | - | - |
| 98-102 | 0 | 0 | 0 | - | - | - |
| 99-103 | 0 | 0 | 0 | - | - | - |
| 100-104 | 0 | 0 | 0 | - | - | - |
| 101-105 | 0 | 0 | 0 | - | - | - |
| 102-106 | 0 | 0 | 0 | - | - | - |
| 103-107 | 0 | 0 | 0 | - | - | - |
| 104-108 | 0 | 0 | 0 | - | - | - |
| 105-109 | 0 | 0 | 0 | - | - | - |
| 106-110 | 0 | 0 | 0 | - | - | - |
| 107-111 | 0 | 0 | 0 | - | - | - |
| 108-112 | 0 | 0 | 0 | - | - | - |
| 109-113 | 0 | 0 | 0 | - | - | - |
| 110-114 | 0 | 0 | 0 | - | - | - |
| 111-115 | 0 | 0 | 0 | - | - | - |
| 112-116 | 0 | 0 | 0 | - | - | - |
| 113-117 | 0 | 0 | 0 | - | - | - |
| 114-118 | 0 | 0 | 0 | - | - | - |
| 115-119 | 0 | 0 | 0 | - | - | - |
| 116-120 | 0 | 0 | 0 | - | - | - |
| 117-121 | 0 | 0 | 0 | - | - | - |
| 118-122 | 0 | 0 | 0 | - | - | - |
| 119-123 | 0 | 0 | 0 | - | - | - |
| 120-124 | 0 | 0 | 0 | - | - | - |
| 121-125 | 0 | 0 | 0 | - | - | - |
| 122-126 | 0 | 0 | 0 | - | - | - |
| 123-127 | 0 | 0 | 0 | - | - | - |
| 124-128 | 0 | 0 | 0 | - | - | - |
| 125-129 | 0 | 0 | 0 | - | - | - |
| 126-130 | 0 | 0 | 0 | - | - | - |
| 127-131 | 0 | 0 | 0 | - | - | - |
| 128-132 | 0 | 0 | 0 | - | - | - |
| 129-133 | 0 | 0 | 0 | - | - | - |
| 130-134 | 0 | 0 | 0 | - | - | - |
| 131-135 | 0 | 0 | 0 | - | - | - |
| 132-136 | 0 | 0 | 0 | - | - | - |
| 133-137 | 0 | 0 | 0 | - | - | - |
| 134-138 | 0 | 0 | 0 | - | - | - |
| 135-139 | 0 | 0 | 0 | - | - | - |
| 136-140 | 0 | 0 | 0 | - | - | - |
| 137-141 | 0 | 0 | 0 | - | - | - |
| 138-142 | 0 | 0 | 0 | - | - | - |
| 139-143 | 0 | 0 | 0 | - | - | - |
| 140-144 | 0 | 0 | 0 | - | - | - |
| 141-145 | 0 | 0 | 0 | - | - | - |
| 142-146 | 0 | 0 | 0 | - | - | - |
| 143-147 | 0 | 0 | 0 | - | - | - |
| 144-148 | 0 | 0 | 0 | - | - | - |
| 145-149 | 0 | 0 | 0 | - | - | - |
| 146-150 | 0 | 0 | 0 | - | - | - |
| 147-151 | 0 | 0 | 0 | - | - | - |
| 148-152 | 0 | 0 | 0 | - | - | - |
| 149-153 | 0 | 0 | 0 | - | - | - |
| 150-154 | 0 | 0 | 0 | - | - | - |
| 151-155 | 0 | 0 | 0 | - | - | - |
| 152-156 | 0 | 0 | 0 | - | - | - |
| 153-157 | 0 | 0 | 0 | - | - | - |
| 154-158 | 0 | 0 | 0 | - | - | - |
| 155-159 | 0 | 0 | 0 | - | - | - |
| 156-160 | 0 | 0 | 0 | - | - | - |
| 157-161 | 0 | 0 | 0 | - | - | - |
| 158-162 | 0 | 0 | 0 | - | - | - |
| 159-163 | 0 | 0 | 0 | - | - | - |
| 160-164 | 0 | 0 | 0 | - | - | - |
| 161-165 | 0 | 0 | 0 | - | - | - |
| 162-166 | 0 | 0 | 0 | - | - | - |
| 163-167 | 0 | 0 | 0 | - | - | - |
| 164-168 | 0 | 0 | 0 | - | - | - |
| 165-169 | 0 | 0 | 0 | - | - | - |
| 166-170 | 0 | 0 | 0 | - | - | - |
| 167-171 | 0 | 0 | 0 | - | - | - |
| 168-172 | 0 | 0 | 0 | - | - | - |
| 169-173 | 0 | 0 | 0 | - | - | - |
| 170-174 | 0 | 0 | 0 | - | - | - |
| 171-175 | 0 | 0 | 0 | - | - | - |
| 172-176 | 0 | 0 | 0 | - | - | - |
| 173-177 | 0 | 0 | 0 | - | - | - |
| 174-178 | 0 | 0 | 0 | - | - | - |
| 175-179 | 0 | 0 | 0 | - | - | - |
| 176-180 | 0 | 0 | 0 | - | - | - |
| 177-181 | 0 | 0 | 0 | - | - | - |
| 178-182 | 0 | 0 | 0 | - | - | - |
| 179-183 | 0 | 0 | 0 | - | - | - |
| 180-184 | 0 | 0 | 0 | - | - | - |
| 181-185 | 0 | 0 | 0 | - | - | - |
| 182-186 | 0 | 0 | 0 | - | - | - |
| 183-187 | 0 | 0 | 0 | - | - | - |
| 184-188 | 0 | 0 | 0 | - | - | - |
| 185-189 | 0 | 0 | 0 | - | - | - |
| 186-190 | 0 | 0 | 0 | - | - | - |
| 187-191 | 0 | 0 | 0 | - | - | - |
| 188-192 | 0 | 0 | 0 | - | - | - |
| 189-193 | 0 | 0 | 0 | - | - | - |
| 190-194 | 0 | 0 | 0 | - | - | - |
| 191-195 | 0 | 0 | 0 | - | - | - |
| 192-196 | 0 | 0 | 0 | - | - | - |
| 193-197 | 0 | 0 | 0 | - | - | - |
| 194-198 | 0 | 0 | 0 | - | - | - |
| 195-199 | 0 | 0 | 0 | - | - | - |
| 196-200 | 0 | 0 | 0 | - | - | - |

### Context / T5 压力
| 窗口 | context_emergency% | budget_max | db_max_mb | scan_max_ms |
|------|--------------------|------------|-----------|-------------|
| 1-5 | - | - | - | - |
| 2-6 | - | - | - | - |
| 3-7 | - | - | - | - |
| 4-8 | - | - | - | - |
| 5-9 | - | - | - | - |
| 6-10 | 0.0% | - | 7.504 | 16.000 |
| 7-11 | 0.0% | - | 7.504 | 16.000 |
| 8-12 | 0.0% | - | 7.504 | 16.000 |
| 9-13 | 0.0% | - | 7.504 | 16.000 |
| 10-14 | 0.0% | - | 7.504 | 16.000 |
| 11-15 | - | - | - | - |
| 12-16 | - | - | - | - |
| 13-17 | - | - | - | - |
| 14-18 | - | - | - | - |
| 15-19 | - | - | - | - |
| 16-20 | 0.0% | - | 16.281 | 16.000 |
| 17-21 | 0.0% | - | 16.281 | 16.000 |
| 18-22 | 0.0% | - | 16.281 | 16.000 |
| 19-23 | 0.0% | - | 16.281 | 16.000 |
| 20-24 | 0.0% | - | 16.281 | 16.000 |
| 21-25 | - | - | - | - |
| 22-26 | - | - | - | - |
| 23-27 | - | - | - | - |
| 24-28 | - | - | - | - |
| 25-29 | - | - | - | - |
| 26-30 | 0.0% | - | 26.625 | 16.000 |
| 27-31 | 0.0% | - | 26.625 | 16.000 |
| 28-32 | 0.0% | - | 26.625 | 16.000 |
| 29-33 | 0.0% | - | 26.625 | 16.000 |
| 30-34 | 0.0% | - | 26.625 | 16.000 |
| 31-35 | - | - | - | - |
| 32-36 | - | - | - | - |
| 33-37 | - | - | - | - |
| 34-38 | - | - | - | - |
| 35-39 | - | - | - | - |
| 36-40 | 0.0% | - | 35.078 | 62.000 |
| 37-41 | 0.0% | - | 35.078 | 62.000 |
| 38-42 | 0.0% | - | 35.078 | 62.000 |
| 39-43 | 0.0% | - | 35.078 | 62.000 |
| 40-44 | 0.0% | - | 35.078 | 62.000 |
| 41-45 | - | - | - | - |
| 42-46 | - | - | - | - |
| 43-47 | - | - | - | - |
| 44-48 | - | - | - | - |
| 45-49 | - | - | - | - |
| 46-50 | 0.0% | - | 45.328 | 47.000 |
| 47-51 | 0.0% | - | 45.328 | 47.000 |
| 48-52 | 0.0% | - | 45.328 | 47.000 |
| 49-53 | 0.0% | - | 45.328 | 47.000 |
| 50-54 | 0.0% | - | 45.328 | 47.000 |
| 51-55 | - | - | - | - |
| 52-56 | - | - | - | - |
| 53-57 | - | - | - | - |
| 54-58 | - | - | - | - |
| 55-59 | - | - | - | - |
| 56-60 | 0.0% | - | 56.660 | 109.000 |
| 57-61 | 0.0% | - | 56.660 | 109.000 |
| 58-62 | 0.0% | - | 56.660 | 109.000 |
| 59-63 | 0.0% | - | 56.660 | 109.000 |
| 60-64 | 0.0% | - | 56.660 | 109.000 |
| 61-65 | - | - | - | - |
| 62-66 | - | - | - | - |
| 63-67 | - | - | - | - |
| 64-68 | - | - | - | - |
| 65-69 | - | - | - | - |
| 66-70 | 0.0% | - | 160.762 | 297.000 |
| 67-71 | 0.0% | - | 160.762 | 297.000 |
| 68-72 | 0.0% | - | 160.762 | 297.000 |
| 69-73 | 0.0% | - | 160.762 | 297.000 |
| 70-74 | 0.0% | - | 160.762 | 297.000 |
| 71-75 | - | - | - | - |
| 72-76 | - | - | - | - |
| 73-77 | - | - | - | - |
| 74-78 | - | - | - | - |
| 75-79 | - | - | - | - |
| 76-80 | 0.0% | - | 75.730 | 234.000 |
| 77-81 | 0.0% | - | 75.730 | 234.000 |
| 78-82 | 0.0% | - | 75.730 | 234.000 |
| 79-83 | 0.0% | - | 75.730 | 234.000 |
| 80-84 | 0.0% | - | 75.730 | 234.000 |
| 81-85 | - | - | - | - |
| 82-86 | - | - | - | - |
| 83-87 | - | - | - | - |
| 84-88 | - | - | - | - |
| 85-89 | - | - | - | - |
| 86-90 | 0.0% | - | 86.328 | 219.000 |
| 87-91 | 0.0% | - | 86.328 | 219.000 |
| 88-92 | 0.0% | - | 86.328 | 219.000 |
| 89-93 | 0.0% | - | 86.328 | 219.000 |
| 90-94 | 0.0% | - | 86.328 | 219.000 |
| 91-95 | - | - | - | - |
| 92-96 | - | - | - | - |
| 93-97 | - | - | - | - |
| 94-98 | - | - | - | - |
| 95-99 | - | - | - | - |
| 96-100 | 0.0% | - | 95.070 | 297.000 |
| 97-101 | 0.0% | - | 95.070 | 297.000 |
| 98-102 | 0.0% | - | 95.070 | 297.000 |
| 99-103 | 0.0% | - | 95.070 | 297.000 |
| 100-104 | 0.0% | - | 95.070 | 297.000 |
| 101-105 | - | - | - | - |
| 102-106 | - | - | - | - |
| 103-107 | - | - | - | - |
| 104-108 | - | - | - | - |
| 105-109 | - | - | - | - |
| 106-110 | 0.0% | - | 106.766 | 313.000 |
| 107-111 | 0.0% | - | 106.766 | 313.000 |
| 108-112 | 0.0% | - | 106.766 | 313.000 |
| 109-113 | 0.0% | - | 106.766 | 313.000 |
| 110-114 | 0.0% | - | 106.766 | 313.000 |
| 111-115 | - | - | - | - |
| 112-116 | - | - | - | - |
| 113-117 | - | - | - | - |
| 114-118 | - | - | - | - |
| 115-119 | - | - | - | - |
| 116-120 | 0.0% | - | 118.211 | 250.000 |
| 117-121 | 0.0% | - | 118.211 | 250.000 |
| 118-122 | 0.0% | - | 118.211 | 250.000 |
| 119-123 | 0.0% | - | 118.211 | 250.000 |
| 120-124 | 0.0% | - | 118.211 | 250.000 |
| 121-125 | - | - | - | - |
| 122-126 | - | - | - | - |
| 123-127 | - | - | - | - |
| 124-128 | - | - | - | - |
| 125-129 | - | - | - | - |
| 126-130 | 0.0% | - | 127.930 | 125.000 |
| 127-131 | 0.0% | - | 127.930 | 125.000 |
| 128-132 | 0.0% | - | 127.930 | 125.000 |
| 129-133 | 0.0% | - | 127.930 | 125.000 |
| 130-134 | 0.0% | - | 127.930 | 125.000 |
| 131-135 | - | - | - | - |
| 132-136 | - | - | - | - |
| 133-137 | - | - | - | - |
| 134-138 | - | - | - | - |
| 135-139 | - | - | - | - |
| 136-140 | 0.0% | - | 137.914 | 125.000 |
| 137-141 | 0.0% | - | 137.914 | 125.000 |
| 138-142 | 0.0% | - | 137.914 | 125.000 |
| 139-143 | 0.0% | - | 137.914 | 125.000 |
| 140-144 | 0.0% | - | 137.914 | 125.000 |
| 141-145 | - | - | - | - |
| 142-146 | - | - | - | - |
| 143-147 | - | - | - | - |
| 144-148 | - | - | - | - |
| 145-149 | - | - | - | - |
| 146-150 | 0.0% | - | 149.309 | 422.000 |
| 147-151 | 0.0% | - | 149.309 | 422.000 |
| 148-152 | 0.0% | - | 149.309 | 422.000 |
| 149-153 | 0.0% | - | 149.309 | 422.000 |
| 150-154 | 0.0% | - | 149.309 | 422.000 |
| 151-155 | - | - | - | - |
| 152-156 | - | - | - | - |
| 153-157 | - | - | - | - |
| 154-158 | - | - | - | - |
| 155-159 | - | - | - | - |
| 156-160 | 0.0% | - | 160.762 | 297.000 |
| 157-161 | 0.0% | - | 160.762 | 297.000 |
| 158-162 | 0.0% | - | 160.762 | 297.000 |
| 159-163 | 0.0% | - | 160.762 | 297.000 |
| 160-164 | 0.0% | - | 160.762 | 297.000 |
| 161-165 | - | - | - | - |
| 162-166 | - | - | - | - |
| 163-167 | - | - | - | - |
| 164-168 | - | - | - | - |
| 165-169 | - | - | - | - |
| 166-170 | 0.0% | - | 160.762 | 125.000 |
| 167-171 | 0.0% | - | 160.762 | 125.000 |
| 168-172 | 0.0% | - | 160.762 | 125.000 |
| 169-173 | 0.0% | - | 160.762 | 125.000 |
| 170-174 | 0.0% | - | 160.762 | 125.000 |
| 171-175 | - | - | - | - |
| 172-176 | - | - | - | - |
| 173-177 | - | - | - | - |
| 174-178 | - | - | - | - |
| 175-179 | - | - | - | - |
| 176-180 | 0.0% | - | 160.762 | 140.000 |
| 177-181 | 0.0% | - | 160.762 | 140.000 |
| 178-182 | 0.0% | - | 160.762 | 140.000 |
| 179-183 | 0.0% | - | 160.762 | 140.000 |
| 180-184 | 0.0% | - | 160.762 | 140.000 |
| 181-185 | - | - | - | - |
| 182-186 | - | - | - | - |
| 183-187 | - | - | - | - |
| 184-188 | - | - | - | - |
| 185-189 | - | - | - | - |
| 186-190 | 0.0% | - | 160.762 | 141.000 |
| 187-191 | 0.0% | - | 160.762 | 141.000 |
| 188-192 | 0.0% | - | 160.762 | 141.000 |
| 189-193 | 0.0% | - | 160.762 | 141.000 |
| 190-194 | 0.0% | - | 160.762 | 141.000 |
| 191-195 | - | - | - | - |
| 192-196 | - | - | - | - |
| 193-197 | - | - | - | - |
| 194-198 | - | - | - | - |
| 195-199 | - | - | - | - |
| 196-200 | 0.0% | - | 160.762 | 141.000 |

## V6 验收判据（harness 三态）

项目 **835afdf11a294b5eac74a5d8998bd9a2** Ch1-Ch200

| 判据 | 结果 | 实测值 | 阈值 | 充分性 | 详情 |
|------|------|--------|------|--------|------|
| T1 | ✓ pass | 3.0 | ≥1 mainline thread advanced/resolved | 充分 | 主线线索 3 条，跃迁 3 条: t_ark(Ch1→Ch129), t_partner(Ch68→Ch69), t_resonance(Ch1→Ch101) |
| T2 | ✓ pass | 200/200 | 200/200 accepted | 充分 | accepted 200 章 |
| T6a | ✓ pass | 0.0062 | 3.14 | 充分 | orphan_total 线性斜率 0.0062/章（基于 66 章） |
| T6b | ✓ pass | 0.0 | 0 | 充分 | P1 critical orphan 审计点全程为 0（基于 66 个审计点） |
| T6c | ✓ pass | orphan_slope=0.0062, t7=0.0274 | T7≤0.10/章时启用小基数保护；否则 T7降幅≥0.5×orphan降幅 | 充分 | 小基数保护：新 critical 产生率已接近 0，原降幅比值口径会被绝对可降空间限制误伤；orphan 斜率降幅 6.2774，T7 降幅 1.7396 |
| T6c-obs | ◯ 未判定 | 0.0% | ≤15%（观察项，不进入 all_passed） | 充分 | candidate critical 0 / 新增 critical 4 |
| T7 | ◯ 未判定 | 0.0274 | 1.767 | 充分 | 新 critical 速率 0.0274/章（138k 基线 1.767） |
| T3/T8 | 🔴 fail | character_autonomy_score | breached_dimensions = [] | 充分 | 触线维度: character_autonomy_score |
| T4 | ◯ 未判定 | - | degraded≤20%, convergence≤10% | 不足 | 未提供 run_logs，T4 未判定 |
| T5 | ✓ pass | max_db=180.02MB, max_latency_ratio=2.84x | DB≤300MB; scan≤median×2.0（连续/极端破线才 hard fail） | 充分 | T5 未破；耗时观察章 [110, 150] |
| T9 | ✓ pass | meta=0, duplicate=0, timeline=14 | meta=0; duplicate=0; timeline report-only | 充分 | 时间线诊断章: [32, 50, 56, 82, 83, 97, 99, 122, 149, 153, 161, 164, 171, 181] |
| health≥7.0 | 🔴 fail | 1.0 | 0 | 充分 | health<7.0 的章: [3] |

- **聚合结论：存在未通过的 sufficient 项**（未判定项：['T6c-obs', 'T7', 'T4']）
