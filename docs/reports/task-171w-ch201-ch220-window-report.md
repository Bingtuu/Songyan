# Task 171：Ch201-Ch220 长跑报告（阶段 Z 第一里程碑，文学=观测）

- 生成时间: 2026-07-13T13:12:58.941980
- DB: `.tmp\task171_ch1_ch200.db`
- 项目 ID: `835afdf11a294b5eac74a5d8998bd9a2`
- Run ID: `run-e27b763f`
- 章节范围: Ch201-Ch220
- Gate 模式: enforce；on_failure: isolate
- 完成: 20/20

## 放行判据（稳定性面，不含文学 rubric）

见下方稳定性面验收（T9/health/orphan/T12）；文学 Tier 2 仅观测（下节），不阻塞。

## 文学 Tier 2 观测（框架 §8 D2；observe-only，不阻塞）

- 观测章数: 20
- ⚠️ **建议人工抽读**：character_autonomy_score、conceptual_grounding_score（跌破 base×0.85 或 <3.0）
  - character_autonomy_score：首破窗口起始 Ch201
  - conceptual_grounding_score：首破窗口起始 Ch213

> 文学分为 Tier 2/Tier 3 观测项，**不参与放行判定**；放行只看稳定性面。

# V6 阶段 A 度量报告 — 项目 835afdf11a294b5eac74a5d8998bd9a2（Ch201-Ch220）


## 三层契约摘要（框架 §8 A1；Tier 分区互不混淆）

| 层 | 内容 | 阻塞性 | 当前状态 |
|----|------|--------|----------|
| Tier 1 硬缺陷 | T9 meta 泄漏 / 整段重复 / 时间线 | **阻塞**（冻结阈值） | ✓ 0 硬缺陷 |
| Tier 2 趋势 | 文学 rubric 趋势地板（voice/expo/pacing/concept） | **observe，不阻塞** | ⚠️ 建议人工抽读：character_autonomy_score、conceptual_grounding_score（跌破 base×0.85 或 <3.0） |
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
| 201 | 9 | 0 | 0 | 9 | 0 |
| 204 | 2 | 0 | 0 | 2 | 0 |
| 207 | 0 | 0 | 0 | 0 | 0 |
| 210 | 9 | 0 | 0 | 9 | 0 |
| 213 | 14 | 0 | 0 | 14 | 0 |
| 216 | 12 | 0 | 0 | 12 | 0 |
| 219 | 12 | 0 | 0 | 12 | 0 |

- orphan 总量线性斜率：**0.5119**/章
- P1(critical) orphan 峰值：**0**（T6(b) 要求全程 =0）

## 每章新 critical 产生速率（T7，写入侧）

| 章 | new_critical | new_total |
|----|--------------|-----------|
| 201 | 0 | 7 |
| 202 | 0 | 3 |
| 203 | 0 | 3 |
| 204 | 0 | 5 |
| 205 | 0 | 3 |
| 206 | 0 | 6 |
| 207 | 0 | 3 |
| 208 | 0 | 3 |
| 209 | 0 | 4 |
| 210 | 0 | 5 |
| 211 | 0 | 5 |
| 213 | 0 | 5 |
| 214 | 0 | 6 |
| 215 | 0 | 5 |
| 216 | 0 | 6 |
| 217 | 0 | 9 |
| 218 | 0 | 5 |
| 220 | 1 | 4 |

- 新 critical 合计：**1**；每章均值（T7）：**0.056**

## 质量债账本（run 级；T4：50 章窗 degraded ≤20% 且 convergence ≤10%）

| run | 章数 | degraded | conv_failed | QG=false | degraded% | conv% | T4 |
|-----|------|----------|-------------|----------|-----------|-------|----|
| run-fb39245c | 210 | 0 | 0 | 1 | 0.0% | 0.0% | ✓ |
| run-e27b763f | 23 | 0 | 0 | 0 | 0.0% | 0.0% | ✓ |

## 文学质量趋势（T3：W=5 均值相对前 10 章基线降 ≥20%；只诊断不阻断）

| 章 | literary | char_autonomy | conceptual | fissure |
|----|----------|---------------|------------|---------|
| 201 | 5.50 | 2.50 | 4.00 | 4.50 |
| 202 | 5.50 | 3.00 | 4.50 | 7.50 |
| 203 | 6.00 | 2.50 | 7.00 | 8.00 |
| 204 | 5.50 | 3.50 | 6.00 | 7.50 |
| 205 | 5.50 | 3.00 | 4.50 | 6.50 |
| 206 | 5.50 | 2.50 | 6.50 | 7.00 |
| 207 | 5.50 | 3.50 | 5.00 | 6.50 |
| 208 | 5.50 | 2.50 | 4.00 | 7.00 |
| 209 | 6.50 | 3.50 | 6.00 | 8.00 |
| 210 | 5.50 | 3.00 | 4.50 | 7.00 |
| 211 | 5.50 | 2.50 | 4.00 | 7.50 |
| 212 | 5.50 | 2.50 | 7.00 | 7.50 |
| 213 | 5.50 | 2.00 | 6.00 | 4.00 |
| 214 | 5.50 | 2.50 | 4.00 | 7.50 |
| 215 | 5.50 | 3.00 | 4.50 | 7.00 |
| 216 | 5.50 | 2.50 | 3.50 | 7.00 |
| 217 | 5.50 | 2.50 | 4.00 | 6.50 |
| 218 | 5.50 | 3.50 | 6.00 | 7.00 |
| 219 | 5.50 | 3.50 | 4.50 | 7.00 |
| 220 | 6.00 | 3.00 | 5.00 | 8.00 |

- ✓ 无维度触 T3 红线

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
| fs-835afdf11a294b5eac74a5d8998bd9a2-211a9bcb | 1 | 8 | 219 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2ca9652b | 1 | 12 | 219 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4984b545 | 1 | 10 | 219 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-12f65a35 | 2 | 12 | 218 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3f3d3fcc | 2 | 15 | 218 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-845bfa4c | 2 | 14 | 218 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0c2c1e40 | 3 | 14 | 217 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-111e7700 | 3 | 15 | 217 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-abfa7b3d | 3 | 12 | 217 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-17bb4d8d | 4 | 12 | 216 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a48c6f5c | 4 | 15 | 216 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b8e0d679 | 4 | 20 | 216 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e2a2dceb | 4 | 10 | 216 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-471babc6 | 5 | 14 | 215 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-94de1f22 | 5 | 18 | 215 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eb4deac8 | 5 | 20 | 215 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3523a73c | 6 | 10 | 214 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4847bc36 | 6 | 12 | 214 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a63c8319 | 6 | 14 | 214 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fa2d0fc2 | 6 | 18 | 214 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-30a564e3 | 7 | 12 | 213 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-85229cd6 | 7 | 12 | 213 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e4b312ca | 7 | 15 | 213 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-00c48aac | 8 | 14 | 212 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1db28e1c | 8 | 14 | 212 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-50042320 | 8 | 14 | 212 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-62984f08 | 8 | 15 | 212 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-725ba0ef | 8 | 12 | 212 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-72b49f12 | 8 | 12 | 212 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-de4a8808 | 8 | 15 | 212 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2cd8ac26 | 9 | 14 | 211 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-47de5c41 | 9 | 14 | 211 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a9844be9 | 9 | 15 | 211 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-abc6571c | 9 | 12 | 211 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-176a52ad | 10 | 15 | 210 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9b78017a | 10 | 14 | 210 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a7f217c4 | 10 | 14 | 210 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f0a2b438 | 10 | 15 | 210 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1056b784 | 11 | 14 | 209 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b0bd17ef | 11 | 15 | 209 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b784045a | 11 | 14 | 209 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ccb9868a | 11 | 14 | 209 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5ff757bd | 12 | 13 | 208 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-714466f5 | 12 | 14 | 208 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-98aa9f25 | 12 | 13 | 208 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-baf3e1f6 | 12 | 14 | 208 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-01b0d1d5 | 13 | 14 | 207 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2f70fcf7 | 13 | 14 | 207 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7307fe4b | 13 | 14 | 207 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-96ff892d | 13 | 14 | 207 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b57f34b6 | 13 | 14 | 207 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e4d2b919 | 13 | 14 | 207 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-49185f72 | 14 | 15 | 206 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4aaaa2c8 | 14 | 15 | 206 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a677aa8b | 14 | 15 | 206 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a8ca6961 | 14 | 15 | 206 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-033b43d4 | 20 | 22 | 200 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-67ba608c | 20 | 22 | 200 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f3c375b4 | 20 | 22 | 200 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-52676a4b | 23 | 24 | 197 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9a7c9090 | 23 | 24 | 197 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-de124dba | 23 | 25 | 197 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5aa110ef | 24 | 26 | 196 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c56c0d2f | 24 | 25 | 196 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d01a21dc | 24 | 26 | 196 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a1b70bbb | 25 | 26 | 195 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e33a4509 | 25 | 27 | 195 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f85061d1 | 25 | 26 | 195 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6ba3ec1f | 26 | 27 | 194 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-82a23b69 | 26 | 27 | 194 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-cbfb2743 | 26 | 28 | 194 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e5e2c0d5 | 26 | 27 | 194 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-08f68c55 | 27 | 28 | 193 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-34c07849 | 27 | 30 | 193 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7440f483 | 27 | 28 | 193 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f077a87 | 27 | 30 | 193 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a999572b | 27 | 28 | 193 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2d1697cb | 28 | 30 | 192 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-444fb977 | 28 | 32 | 192 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eaf4bebe | 28 | - | 192 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0c71b1c7 | 30 | 32 | 190 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3198c94e | 30 | 32 | 190 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5e72c572 | 30 | 32 | 190 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6989bf31 | 30 | 32 | 190 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d741275f | 30 | 32 | 190 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-04cee12a | 31 | 32 | 189 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1ec24394 | 31 | 33 | 189 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e6f7a37e | 31 | 34 | 189 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1bb5b89e | 37 | - | 183 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7c34f394 | 37 | - | 183 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ee92c69c | 37 | - | 183 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-47842843 | 41 | 44 | 179 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6927731f | 41 | 44 | 179 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-cbc5de98 | 41 | 44 | 179 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d8dffd4c | 41 | 44 | 179 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f6b0eb47 | 41 | 44 | 179 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-32163fdf | 42 | 44 | 178 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7c4d7ee3 | 42 | 44 | 178 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-88cad144 | 42 | 44 | 178 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f3167ae7 | 42 | 44 | 178 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0c909e63 | 43 | 46 | 177 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1e89738e | 43 | 46 | 177 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2fb1d0af | 43 | 46 | 177 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5d69cb13 | 43 | 46 | 177 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8dd49b9f | 43 | 45 | 177 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae128815 | 43 | 45 | 177 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d217303 | 45 | 47 | 175 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d2aeb5c1 | 45 | 47 | 175 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e527c2b2 | 45 | 47 | 175 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-55e4b728 | 46 | 48 | 174 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-bd918a9f | 46 | 48 | 174 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f799fd46 | 46 | 48 | 174 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-338fb174 | 47 | 49 | 173 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c997a31b | 47 | 49 | 173 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e85017f4 | 51 | - | 169 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fceb3f12 | 51 | - | 169 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-283f9dae | 53 | 55 | 167 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4a31f9f9 | 53 | 55 | 167 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-94351bb5 | 53 | 55 | 167 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a846e663 | 54 | 58 | 166 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f4413437 | 54 | 56 | 166 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fc2ac8d8 | 54 | 56 | 166 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3bdef31f | 55 | 58 | 165 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-51bc5d68 | 55 | 56 | 165 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-db4b937a | 55 | 58 | 165 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ecf100d6 | 55 | 56 | 165 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3d8e835f | 56 | 60 | 164 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d24155b2 | 56 | 62 | 164 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d54257ec | 56 | 58 | 164 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-106b78d0 | 57 | 60 | 163 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d9dc5fe | 57 | 60 | 163 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-659fe646 | 60 | 65 | 160 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ce06a448 | 60 | 62 | 160 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3aa0dfe5 | 62 | - | 158 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-74e5e856 | 62 | 65 | 158 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a70823db | 62 | 64 | 158 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b36d0a6d | 62 | 63 | 158 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-27651848 | 63 | 64 | 157 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-55b1f123 | 63 | 65 | 157 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-886578ce | 63 | 65 | 157 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b47fe159 | 64 | 66 | 156 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c7187d90 | 64 | 65 | 156 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d59e9f4d | 64 | 66 | 156 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0a323fc0 | 66 | 165 | 154 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2e98b312 | 66 | 163 | 154 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8a649597 | 66 | 163 | 154 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3a83af0c | 69 | 160 | 151 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3e36d7b2 | 69 | 160 | 151 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-88d3fca6 | 69 | 160 | 151 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8a4d22eb | 70 | 160 | 150 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8dccba01 | 70 | 160 | 150 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d67ee167 | 70 | 160 | 150 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1fd9ba59 | 73 | 75 | 147 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b8a2750c | 73 | 76 | 147 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3ecf07be | 74 | 80 | 146 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-808817c9 | 74 | 78 | 146 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3a3948d0 | 78 | 83 | 142 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7c872d21 | 78 | 82 | 142 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ccef28ab | 78 | 80 | 142 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2f57b375 | 79 | 83 | 141 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c5199339 | 79 | 84 | 141 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-03112c52 | 80 | 84 | 140 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3a2fcf19 | 80 | 84 | 140 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-82ae8dcb | 80 | 85 | 140 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-50ce3890 | 81 | - | 139 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-734cdf98 | 81 | 84 | 139 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a9db356e | 81 | 84 | 139 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2fa44d57 | 82 | 84 | 138 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b5aec171 | 82 | 86 | 138 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-be18714c | 82 | 85 | 138 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d631bc75 | 82 | 85 | 138 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7f2dc01a | 83 | 85 | 137 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9ee84452 | 83 | 85 | 137 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b2cd20d7 | 83 | 85 | 137 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d2b8efae | 83 | 86 | 137 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-196b43c1 | 84 | 86 | 136 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-30268885 | 84 | 85 | 136 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae509db0 | 84 | 88 | 136 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b3d732fa | 84 | 87 | 136 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e03c493d | 84 | 86 | 136 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-003f5461 | 85 | 87 | 135 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1d700c27 | 85 | 87 | 135 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2eba574d | 85 | 87 | 135 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3be20c56 | 85 | 86 | 135 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eaa4e31b | 85 | 86 | 135 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7fea950b | 93 | - | 127 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d290956a | 93 | - | 127 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0b9cc7b6 | 95 | - | 125 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-49a5f4b4 | 95 | - | 125 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5bbc7b65 | 95 | - | 125 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-92f82cc2 | 96 | - | 124 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ad6a1a5f | 96 | - | 124 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d47ef853 | 96 | - | 124 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-157c5831 | 97 | - | 123 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae14d0c5 | 97 | - | 123 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae4ab4ac | 97 | - | 123 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e352a726 | 97 | - | 123 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-41629cc5 | 99 | 165 | 121 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6ca407d9 | 99 | 165 | 121 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-738bd165 | 99 | 162 | 121 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-76eb0cf8 | 99 | 165 | 121 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9c9e8345 | 99 | 165 | 121 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-801f8fa8 | 100 | - | 120 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-dfa050d9 | 100 | - | 120 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2bee8174 | 101 | - | 119 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b363c64e | 101 | - | 119 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e775c99a | 101 | - | 119 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eae87f66 | 101 | - | 119 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ee535e5c | 101 | - | 119 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-19ccb4de | 102 | - | 118 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6576fc5c | 102 | - | 118 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-74987335 | 102 | - | 118 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4dd6bc3d | 103 | - | 117 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7663797a | 103 | - | 117 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f0f3797 | 103 | - | 117 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-09cf11c7 | 106 | - | 114 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-22cf490a | 106 | - | 114 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3d4a1c80 | 106 | - | 114 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-dbf62f01 | 106 | - | 114 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0c496d60 | 108 | - | 112 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-bd00f167 | 108 | - | 112 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f51fe699 | 108 | - | 112 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0e517f4f | 110 | - | 110 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-15f6ce95 | 110 | - | 110 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3854dabb | 110 | - | 110 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-60daf913 | 110 | - | 110 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-84cfbac4 | 110 | - | 110 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ab9a362c | 110 | - | 110 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2787e053 | 112 | - | 108 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-31c2ca85 | 112 | - | 108 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-93a6ca32 | 112 | - | 108 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ab0032a4 | 112 | - | 108 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0a7393ae | 113 | - | 107 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9edbba3c | 113 | - | 107 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ad34dea3 | 113 | - | 107 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-306827e1 | 114 | - | 106 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e1084c97 | 114 | - | 106 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f0eb6604 | 114 | - | 106 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f213e37b | 114 | - | 106 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3120e6ec | 115 | - | 105 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-57001741 | 115 | - | 105 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8b30b630 | 115 | - | 105 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4544b09c | 116 | 118 | 104 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5617c82a | 116 | 118 | 104 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-77e39a74 | 116 | 120 | 104 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-96faa2ed | 116 | 118 | 104 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1f2f2366 | 117 | 121 | 103 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8b3d427c | 117 | 120 | 103 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ac07161b | 117 | 120 | 103 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6b0f1eb8 | 118 | 123 | 102 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-80c3d56d | 118 | 124 | 102 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-92b5963e | 118 | 122 | 102 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d36bfe2d | 118 | 123 | 102 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f5fbc9bf | 118 | 122 | 102 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-188b8646 | 119 | 123 | 101 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-85d5d386 | 119 | 124 | 101 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-be646b30 | 119 | 123 | 101 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4e7902d0 | 120 | 124 | 100 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c86800c0 | 120 | 125 | 100 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-de020cef | 120 | 125 | 100 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2be3ed07 | 121 | 127 | 99 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-56889abd | 121 | 127 | 99 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-893b893a | 121 | 126 | 99 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b6202b30 | 121 | 126 | 99 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c1492918 | 121 | 126 | 99 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0e8b904d | 122 | 129 | 98 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5f789b4a | 122 | 128 | 98 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6fb26d76 | 122 | 130 | 98 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e19c6b16 | 122 | 128 | 98 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7392ed3d | 123 | 132 | 97 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7a43dd7b | 123 | 131 | 97 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-91a066e8 | 123 | 130 | 97 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9d48f7c3 | 123 | 129 | 97 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-026eae9f | 126 | 133 | 94 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4e985626 | 126 | 132 | 94 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5fb4faea | 126 | 132 | 94 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e416a55a | 126 | 133 | 94 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3c55657a | 129 | 135 | 91 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-70210197 | 129 | 135 | 91 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a78be486 | 129 | 135 | 91 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1b390538 | 130 | 140 | 90 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-36e01093 | 130 | 136 | 90 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-59b8b919 | 130 | 136 | 90 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5d5fed8a | 130 | 136 | 90 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c7033f0e | 130 | 140 | 90 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8a2bbe1a | 131 | 137 | 89 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f036bc3 | 131 | 138 | 89 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d211e7b3 | 131 | 137 | 89 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1606e3a3 | 132 | 138 | 88 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5ae6c694 | 132 | 137 | 88 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b4d8f2eb | 132 | 137 | 88 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-31749a6e | 133 | 136 | 87 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9aa30d5c | 133 | 136 | 87 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-dc8f3290 | 133 | 136 | 87 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2cb634c4 | 134 | 140 | 86 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-321a0dfa | 134 | 140 | 86 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-71130972 | 134 | 140 | 86 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-914e729a | 134 | 138 | 86 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-984b6332 | 134 | 140 | 86 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-000e250e | 135 | 141 | 85 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8bc2a16a | 135 | 141 | 85 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f74ad70 | 135 | 141 | 85 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d6e91b94 | 135 | 141 | 85 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f69399a0 | 135 | 142 | 85 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1b55bcd6 | 138 | 142 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1d576a31 | 138 | 142 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-303a0830 | 138 | 142 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-337d6694 | 138 | 142 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-683ae1f0 | 138 | 142 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-96feced3 | 138 | 142 | 82 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7b928790 | 141 | 143 | 79 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-89c40686 | 141 | 143 | 79 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-cd9798d6 | 141 | 143 | 79 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f0c3d07f | 141 | 143 | 79 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1ce0b39b | 142 | 144 | 78 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5027738d | 142 | 144 | 78 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8488e71e | 142 | - | 78 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-93821ed4 | 142 | 144 | 78 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a6a13724 | 142 | 145 | 78 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-465f4ba5 | 146 | - | 74 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8086b929 | 146 | - | 74 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-aaab60ef | 146 | - | 74 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-39dd6548 | 147 | 148 | 73 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-46aafe24 | 147 | 148 | 73 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-91558f3c | 147 | 148 | 73 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5e6a97b | 147 | 148 | 73 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-645cc7b3 | 148 | 150 | 72 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5eeecad | 148 | 150 | 72 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e46984bf | 148 | 150 | 72 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-19970609 | 149 | 155 | 71 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-94f7ef75 | 149 | 155 | 71 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f557da0 | 149 | 155 | 71 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b2f7d25d | 149 | 155 | 71 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-31f1d7c3 | 151 | 158 | 69 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-72e4b9df | 151 | 160 | 69 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b3040eca | 151 | 162 | 69 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e07c7c54 | 151 | 160 | 69 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-17e95ee2 | 152 | 160 | 68 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a684733e | 152 | 158 | 68 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ce989e04 | 152 | 160 | 68 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f251301b | 152 | 165 | 68 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0fe6b9bd | 154 | 158 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-638b46fa | 154 | 157 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-836bcb46 | 154 | 156 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8f1a5d7d | 154 | 160 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f03e3da6 | 154 | 156 | 66 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-447b5c90 | 155 | 157 | 65 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7ff52e5c | 155 | 158 | 65 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a4c17689 | 155 | 157 | 65 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d02f530d | 155 | 160 | 65 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-940ae171 | 156 | 158 | 64 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d38558c4 | 156 | 158 | 64 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d8c87486 | 156 | 158 | 64 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0bac8404 | 159 | 161 | 61 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-717cfcf2 | 159 | 160 | 61 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a642f9ff | 159 | 161 | 61 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b84dd889 | 159 | 160 | 61 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-74256d8b | 160 | 161 | 60 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e3ffcc99 | 160 | 161 | 60 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fa241809 | 160 | 170 | 60 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-cbea2578 | 162 | 165 | 58 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5357b2a | 162 | 165 | 58 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e71440d6 | 162 | 163 | 58 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ecaf60d9 | 162 | 163 | 58 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-82797af0 | 163 | - | 57 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a63bdd1c | 163 | - | 57 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-bef9ce18 | 163 | - | 57 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c84e540b | 163 | - | 57 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d40beaec | 163 | - | 57 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-675e951e | 166 | 175 | 54 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d598ce30 | 166 | 170 | 54 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e5ffa35c | 166 | 180 | 54 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4a7b6977 | 170 | 175 | 50 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d08258b | 170 | 172 | 50 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b6d81d03 | 170 | 171 | 50 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e26a595c | 170 | 172 | 50 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6a28d8b7 | 171 | 175 | 49 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a9d37c6f | 171 | 175 | 49 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c9cc5145 | 171 | 175 | 49 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-421c174d | 172 | 176 | 48 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6d7ca7b4 | 172 | 178 | 48 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-97d5f5b8 | 172 | 178 | 48 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-298a1941 | 173 | 178 | 47 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5440af7e | 173 | 178 | 47 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3a9e5451 | 179 | 186 | 41 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5350c94d | 179 | 185 | 41 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6e663afc | 179 | 183 | 41 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-afd5111f | 179 | 185 | 41 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-31e18ef5 | 180 | 188 | 40 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3e4743b1 | 180 | 186 | 40 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-465a2826 | 180 | 186 | 40 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-64bf3ae5 | 180 | 186 | 40 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5248be4 | 180 | 190 | 40 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-950610d2 | 182 | 187 | 38 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ccee251c | 182 | 188 | 38 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d197653b | 182 | 186 | 38 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ea5c6c51 | 182 | 186 | 38 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-37cb82d7 | 185 | 186 | 35 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f5cd3f1 | 185 | 186 | 35 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f4fadf45 | 185 | 186 | 35 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-34bccf45 | 187 | 189 | 33 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3f26debd | 187 | 190 | 33 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f974dec9 | 187 | 191 | 33 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0fc72db9 | 190 | 193 | 30 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-17e25307 | 190 | 192 | 30 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-50111325 | 190 | 192 | 30 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e174640f | 190 | 192 | 30 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1eccd778 | 191 | 195 | 29 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-870542cb | 191 | 196 | 29 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-936145b7 | 191 | 194 | 29 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c502bb3f | 191 | 197 | 29 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-19559348 | 192 | 200 | 28 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2bc67470 | 192 | - | 28 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3651d4d3 | 192 | 200 | 28 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e45b282f | 193 | 196 | 27 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e886c7bd | 193 | 196 | 27 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5723662d | 194 | 197 | 26 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ba1a9395 | 194 | - | 26 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e0f3402f | 194 | 198 | 26 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f9cf4929 | 194 | 200 | 26 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-511b8d1b | 195 | 197 | 25 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a9537b1c | 195 | 200 | 25 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-b49bdb66 | 195 | 198 | 25 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d2e451a4 | 195 | 199 | 25 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-eb332306 | 195 | 197 | 25 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4c83a2a2 | 196 | 201 | 24 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-585e3c7c | 196 | 200 | 24 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8b6a4545 | 196 | 202 | 24 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d9709c0e | 196 | 200 | 24 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4474f505 | 197 | 202 | 23 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4c219bae | 197 | 200 | 23 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-bd325ab6 | 197 | 198 | 23 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d8737fdb | 197 | 199 | 23 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-10d32879 | 198 | 200 | 22 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-143725f9 | 198 | 201 | 22 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-371e7065 | 198 | 200 | 22 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-630235c6 | 198 | 200 | 22 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-afbfe377 | 198 | 201 | 22 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-15c9837f | 199 | 210 | 21 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-35003b39 | 199 | 205 | 21 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7fe5c862 | 199 | 210 | 21 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d5335b79 | 199 | 208 | 21 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ded3b434 | 199 | 208 | 21 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1d6a7625 | 200 | 210 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3bce3f46 | 200 | 210 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-422aed1d | 200 | 210 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d4941e5c | 200 | 210 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d611c1ae | 200 | 210 | 20 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-04d9df33 | 202 | 210 | 18 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7622ec3b | 202 | 210 | 18 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-be8b52de | 202 | 210 | 18 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f90fa883 | 202 | 210 | 18 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-1859383e | 203 | 210 | 17 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4af3e12b | 203 | 210 | 17 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6d18255c | 203 | 210 | 17 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9f36c403 | 203 | 210 | 17 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-e869e17f | 204 | 212 | 16 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ebb2fbd9 | 204 | 210 | 16 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-f88a1856 | 204 | 215 | 16 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-116d966e | 205 | 215 | 15 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-34cbbcba | 205 | 212 | 15 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ae320c52 | 205 | 213 | 15 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-2932b48f | 206 | 212 | 14 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-37342218 | 206 | 215 | 14 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-72f675b4 | 206 | 212 | 14 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a5323b00 | 206 | 212 | 14 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5f3d03f9 | 207 | - | 13 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-6d7539ed | 207 | - | 13 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-79c2f823 | 207 | - | 13 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d373ad8 | 207 | - | 13 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-05a60eab | 208 | 215 | 12 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-0714ba92 | 208 | 218 | 12 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-84a040c8 | 208 | 213 | 12 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-9e5fdf89 | 208 | 213 | 12 | overdue | 🔴 |
| fs-835afdf11a294b5eac74a5d8998bd9a2-16a4f304 | 209 | 215 | 11 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3f0d478f | 209 | - | 11 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-723cd63e | 209 | 215 | 11 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3f0bdcfe | 210 | 220 | 10 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-434fd565 | 210 | 220 | 10 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-7a20269f | 210 | 220 | 10 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d1d38ea7 | 210 | 220 | 10 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-4465df82 | 211 | 230 | 9 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-47db85aa | 211 | 220 | 9 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-80e83569 | 211 | 225 | 9 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-965c8a9e | 211 | 220 | 9 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-57bde224 | 214 | 218 | 6 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5b846749 | 214 | 217 | 6 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-63029d3a | 214 | 218 | 6 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ba2c65d0 | 214 | 218 | 6 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-95206941 | 216 | 222 | 4 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-ab5f0be5 | 216 | 220 | 4 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c5a90f3f | 216 | 221 | 4 | due |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c97445af | 216 | 222 | 4 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-139d0bba | 217 | 230 | 3 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-82ca04ac | 217 | 225 | 3 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-90f45149 | 217 | 232 | 3 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-d96baec8 | 217 | 228 | 3 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5ac782d6 | 218 | 220 | 2 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-5cc39eaa | 218 | 222 | 2 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-8d18649f | 218 | 225 | 2 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-a1a5eed3 | 218 | 220 | 2 | overdue |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-c958b994 | 218 | 225 | 2 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-062b8761 | 220 | 225 | 0 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-27bb7962 | 220 | 225 | 0 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-3da7a901 | 220 | 225 | 0 | planted |  |
| fs-835afdf11a294b5eac74a5d8998bd9a2-fd21b746 | 220 | 225 | 0 | planted |  |

## DB 维护遥测（T5：尺寸 ≤300MB；扫描耗时 ≤ 中位数×2.0）

| 章 | DB(MB) | WAL(KB) | pages | scan(ms) | 尺寸红线 | 耗时状态 |
|----|--------|---------|-------|----------|----------|----------|
| 207 | 180.02 | 185.1 | 46085 | 156.000 | ✓ | ✓ |
| 207 | 180.02 | 929.4 | 46085 | 172.000 | ✓ | ✓ |
| 207 | 180.02 | 4055.7 | 46085 | 484.000 | ✓ | ✓ |
| 210 | 167.47 | 4075.8 | 43190 | 187.000 | ✓ | ✓ |
| 220 | 179.05 | 4132.1 | 46084 | 172.000 | ✓ | ✓ |
| 220 | 179.05 | 4132.1 | 46084 | 187.000 | ✓ | ✓ |

- 扫描耗时基线（3 个章级样本中位数）：**179.500 ms**；hard 阈值：**359.000 ms**
- ✓ DB 尺寸未超 300MB 红线
- ✓ 扫描耗时无连续/极端 hard 破线

## 跨章时间线一致性诊断（Task 162，诊断项；不阻塞 accept）

- 抽取确定性时间信号 **9** 条；疑似冲突 **0** 条。
- 闪回/档案上下文信号 **3** 条，仅展示，不参与冲突判定。

- ✓ 未发现确定性时间信号的跨章矛盾。

<details><summary>时间信号明细</summary>

| 章 | 类型 | 值 | 单位 | 定位 | 片段 | 备注 |
|----|------|----|------|------|------|------|
| 202 | countdown | 100 | 分 | 第101段第1句 | 头盔内的氧气指示器显示剩余百分之十一。 |  |
| 202 | absolute_date | 2147-03-19 | date | 第29段第1句 | “纪元标准时 2147.03.19 14:22:07——引力异常加剧，导航系统失灵。船长命令弃船，但逃生舱发射序列无法执行。方舟结构……在吸收我们的信号。” | flashback_context:日志 |
| 202 | absolute_date | 2147-03-19 | date | 第32段第2句 | 林渊的手指在触控板上方悬停——他的瞳孔微微收缩，面罩内的呼吸声变得急促。日志在这一点后中断了三分之二的篇幅，最后一段记录的时间戳是纪元标准时 2147.03.1... | flashback_context:日志 |
| 202 | absolute_date | 2147-03-19 | date | 第43段第1句 | 日志在这一点后中断了三分之二的篇幅，最后一段记录的时间戳是纪元标准时 2147.03.19 15:47:33。 | flashback_context:日志 |
| 202 | countdown | 51 | 分钟 | 第48段第1句 | 氧气剩余五十一分钟。 |  |
| 202 | countdown | 100 | 分 | 第53段第2句 | 他打开宇航服左臂的战术终端，调出逃生舱的燃料余量和推进器模块配置图。数据在屏幕上展开——主推进器燃料罐剩余百分之三十七，姿态控制推进器燃料罐剩余百分之六十二。往... |  |
| 202 | countdown | 100 | 分 | 第53段第2句 | 他打开宇航服左臂的战术终端，调出逃生舱的燃料余量和推进器模块配置图。数据在屏幕上展开——主推进器燃料罐剩余百分之三十七，姿态控制推进器燃料罐剩余百分之六十二。往... |  |
| 202 | countdown | 60 | 分钟 | 第6段第1句 | 头盔内的氧气指示器显示剩余六十分钟。他必须在钟形曲线拐点到来前返回逃生舱——那意味着四十五分钟是安全的极限。 |  |
| 208 | countdown | 47 | 分钟 | 第35段第1句 | “那我还有四十七分钟。”林渊的手指在黑色模块的表面滑动，寻找相位偏移的调节接口，“四十七分钟来打开第二重屏障，进入核心区，然后弄清楚那个所谓的‘方舟意识’到底是... |  |

</details>

## 概念预算诊断（Task 163，规划侧约束；不自动改写）

- 概念总数 **361**；未落地 **185**；本章新概念预算 **2**；触发收紧：**否**。

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

- 汇总：元标记 **0**（含 artifact），重复长段落 **0**，时间线矛盾 **0**。

| 章 | version | 元标记/artifact | 重复长段落 | 时间线矛盾 |
|----|---------|--------|------------|------------|
| 201 | v-201-1-ab644d7d | 0 | 0 | 0 |
| 202 | rev-202-2-b60f8792 | 0 | 0 | 0 |
| 203 | v-203-1-93f95af3 | 0 | 0 | 0 |
| 204 | v-204-1-dea85939 | 0 | 0 | 0 |
| 205 | rev-205-3-8d6fc42e | 0 | 0 | 0 |
| 206 | rev-206-2-76639593 | 0 | 0 | 0 |
| 207 | rev-207-7-edf1218b | 0 | 0 | 0 |
| 208 | rev-208-2-5359e78e | 0 | 0 | 0 |
| 209 | v-209-1-4f5a1d5c | 0 | 0 | 0 |
| 210 | v-210-4-6839e9a1 | 0 | 0 | 0 |
| 211 | v-211-4-cd361d52 | 0 | 0 | 0 |
| 212 | v-212-4-4651ded8 | 0 | 0 | 0 |
| 213 | rev-213-2-38196221 | 0 | 0 | 0 |
| 214 | rev-214-2-b93a24ad | 0 | 0 | 0 |
| 215 | rev-215-3-045c10b9 | 0 | 0 | 0 |
| 216 | rev-216-3-7c6075f2 | 0 | 0 | 0 |
| 217 | rev-217-2-5bc569a4 | 0 | 0 | 0 |
| 218 | rev-218-3-73d806e4 | 0 | 0 | 0 |
| 219 | rev-219-3-cedd8925 | 0 | 0 | 0 |
| 220 | rev-220-3-5e1e8f04 | 0 | 0 | 0 |

- 元标记违规章：无（含 artifact）
- 重复长段落违规章：无
- 时间线矛盾诊断章：无

## 自适应门禁数据面（Task 168；只供 Task 169 判定使用）

本段只展示 gate 输入信号，不输出 pass/fail/halt，不改变 enforce 行为。

### 样本充分性
| 信号域 | present | missing | insufficient | observation |
|--------|---------|---------|--------------|-------------|
| continuity | 19 | 1 | 0 | 0 |
| quality | 0 | 20 | 0 | 0 |
| literary | 20 | 0 | 0 | 0 |
| cleanliness | 20 | 0 | 0 | 0 |
| context | 3 | 17 | 0 | 0 |
| narrative | 6 | 14 | 0 | 0 |

### Continuity / Orphan 窗口
| 窗口 | health_min | health_median | P1_median | orphan_slope | orphan_delta | new_critical_mean |
|------|------------|---------------|-----------|--------------|--------------|-------------------|
| 201-205 | - | - | 0.000 | -1.600 | -9 | 0.000 |
| 202-206 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 203-207 | - | - | 0.000 | -0.200 | 0 | 0.000 |
| 204-208 | - | - | 0.000 | -0.400 | -2 | 0.000 |
| 205-209 | - | - | 0.000 | 0.000 | 0 | 0.000 |
| 206-210 | - | - | 0.000 | 1.800 | 9 | 0.000 |
| 207-211 | - | - | 0.000 | 0.900 | 0 | 0.000 |
| 208-212 | - | - | 0.000 | 0.900 | 0 | 0.000 |
| 209-213 | - | - | 0.000 | 2.829 | 14 | 0.000 |
| 210-214 | - | - | 0.000 | -0.400 | -9 | 0.000 |
| 211-215 | - | - | 0.000 | -0.400 | 0 | 0.000 |
| 212-216 | - | - | 0.000 | -0.600 | -2 | 0.000 |
| 213-217 | - | - | 0.000 | -1.600 | -14 | 0.000 |
| 214-218 | - | - | 0.000 | -0.000 | 0 | 0.000 |
| 215-219 | - | - | 0.000 | 1.200 | 12 | 0.000 |
| 216-220 | - | - | 0.000 | -1.200 | -12 | 0.200 |

### Quality Debt 窗口
| 窗口 | degraded% | convergence% | qg_false% |
|------|-----------|--------------|-----------|
| 201-205 | - | - | - |
| 202-206 | - | - | - |
| 203-207 | - | - | - |
| 204-208 | - | - | - |
| 205-209 | - | - | - |
| 206-210 | - | - | - |
| 207-211 | - | - | - |
| 208-212 | - | - | - |
| 209-213 | - | - | - |
| 210-214 | - | - | - |
| 211-215 | - | - | - |
| 212-216 | - | - | - |
| 213-217 | - | - | - |
| 214-218 | - | - | - |
| 215-219 | - | - | - |
| 216-220 | - | - | - |

### Literary / Cleanliness 窗口
| 窗口 | literary | conceptual | meta | duplicate | timeline(obs) |
|------|----------|------------|------|-----------|---------------|
| 201-205 | 5.600 | 5.200 | 0 | 0 | 0 |
| 202-206 | 5.600 | 5.700 | 0 | 0 | 0 |
| 203-207 | 5.600 | 5.800 | 0 | 0 | 0 |
| 204-208 | 5.500 | 5.200 | 0 | 0 | 0 |
| 205-209 | 5.700 | 5.200 | 0 | 0 | 0 |
| 206-210 | 5.700 | 5.200 | 0 | 0 | 0 |
| 207-211 | 5.700 | 4.700 | 0 | 0 | 0 |
| 208-212 | 5.700 | 5.100 | 0 | 0 | 0 |
| 209-213 | 5.700 | 5.500 | 0 | 0 | 0 |
| 210-214 | 5.500 | 5.100 | 0 | 0 | 0 |
| 211-215 | 5.500 | 5.100 | 0 | 0 | 0 |
| 212-216 | 5.500 | 5.000 | 0 | 0 | 0 |
| 213-217 | 5.500 | 4.400 | 0 | 0 | 0 |
| 214-218 | 5.500 | 4.400 | 0 | 0 | 0 |
| 215-219 | 5.500 | 4.500 | 0 | 0 | 0 |
| 216-220 | 5.600 | 4.600 | 0 | 0 | 0 |

### Schedule Lifecycle 窗口
| 窗口 | injected | satisfied | missed | hit_rate | missed_rate | overdue_rate |
|------|----------|-----------|--------|----------|-------------|--------------|
| 201-205 | 0 | 0 | 0 | - | - | - |
| 202-206 | 0 | 0 | 0 | - | - | - |
| 203-207 | 0 | 0 | 0 | - | - | - |
| 204-208 | 0 | 0 | 0 | - | - | - |
| 205-209 | 0 | 0 | 0 | - | - | - |
| 206-210 | 0 | 0 | 0 | - | - | - |
| 207-211 | 0 | 0 | 0 | - | - | - |
| 208-212 | 0 | 0 | 0 | - | - | - |
| 209-213 | 0 | 0 | 0 | - | - | - |
| 210-214 | 0 | 0 | 0 | - | - | - |
| 211-215 | 0 | 0 | 0 | - | - | 100.0% |
| 212-216 | 0 | 0 | 0 | - | - | 100.0% |
| 213-217 | 0 | 0 | 0 | - | - | 100.0% |
| 214-218 | 0 | 0 | 0 | - | - | 100.0% |
| 215-219 | 0 | 0 | 0 | - | - | 100.0% |
| 216-220 | 0 | 0 | 0 | - | - | 100.0% |

### Context / T5 压力
| 窗口 | context_emergency% | budget_max | db_max_mb | scan_max_ms |
|------|--------------------|------------|-----------|-------------|
| 201-205 | - | - | - | - |
| 202-206 | - | - | - | - |
| 203-207 | 0.0% | - | 180.020 | 484.000 |
| 204-208 | 0.0% | - | 180.020 | 484.000 |
| 205-209 | 0.0% | - | 180.020 | 484.000 |
| 206-210 | 0.0% | - | 180.020 | 484.000 |
| 207-211 | 0.0% | - | 180.020 | 484.000 |
| 208-212 | 0.0% | - | 167.469 | 187.000 |
| 209-213 | 0.0% | - | 167.469 | 187.000 |
| 210-214 | 0.0% | - | 167.469 | 187.000 |
| 211-215 | - | - | - | - |
| 212-216 | - | - | - | - |
| 213-217 | - | - | - | - |
| 214-218 | - | - | - | - |
| 215-219 | - | - | - | - |
| 216-220 | 0.0% | - | 179.051 | 187.000 |

## V6 验收判据（harness 三态）

项目 **835afdf11a294b5eac74a5d8998bd9a2** Ch201-Ch220

| 判据 | 结果 | 实测值 | 阈值 | 充分性 | 详情 |
|------|------|--------|------|--------|------|
| T1 | 🔴 fail | 0.0 | ≥1 mainline thread advanced/resolved | 充分 | 主线线索 3 条，跃迁 0 条 |
| T2 | ✓ pass | 20/20 | 20/20 accepted | 充分 | accepted 20 章 |
| T6a | ✓ pass | 0.5119 | 3.14 | 充分 | orphan_total 线性斜率 0.5119/章（基于 7 章） |
| T6b | ✓ pass | 0.0 | 0 | 充分 | P1 critical orphan 审计点全程为 0（基于 7 个审计点） |
| T6c | ✓ pass | orphan_slope=0.5119, t7=0.0556 | T7≤0.10/章时启用小基数保护；否则 T7降幅≥0.5×orphan降幅 | 充分 | 小基数保护：新 critical 产生率已接近 0，原降幅比值口径会被绝对可降空间限制误伤；orphan 斜率降幅 5.7717，T7 降幅 1.7114 |
| T6c-obs | ◯ 未判定 | 0.0% | ≤15%（观察项，不进入 all_passed） | 充分 | candidate critical 0 / 新增 critical 1 |
| T7 | ◯ 未判定 | 0.0556 | 1.767 | 充分 | 新 critical 速率 0.0556/章（138k 基线 1.767） |
| T3/T8 | ✓ pass | none | breached_dimensions = [] | 充分 | 无维度触 T3/T8 红线 |
| T4 | ◯ 未判定 | - | degraded≤20%, convergence≤10% | 不足 | 未提供 run_logs，T4 未判定 |
| T5 | ✓ pass | max_db=180.02MB, max_latency_ratio=2.84x | DB≤300MB; scan≤median×2.0（连续/极端破线才 hard fail） | 充分 | T5 未破；耗时观察章 [110, 150] |
| T9 | ✓ pass | meta=0, duplicate=0, timeline=0 | meta=0; duplicate=0; timeline report-only | 充分 | T9 洁净度红线未破 |
| health≥7.0 | ✓ pass | 0.0 | 0 | 充分 | health 全程 ≥7.0 |

- **聚合结论：存在未通过的 sufficient 项**（未判定项：['T6c-obs', 'T7', 'T4']）
