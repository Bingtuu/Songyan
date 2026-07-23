# Task 171d: 三层契约落地 —— DONE（A1/A3/A4 达标）

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 A 组（A1/A3/A4；A2 行为层已达标）
> **状态**: ✅ **完成**
> **报告**: `archive/v7/reports/task-171d-three-tier-contract-report.md`
> **完成时间**: 2026-07-10

---

## 结论

Task 171d 把框架 §8 "三层契约"从**文档概念**落成 **metrics 出口的可见结构 + observe-only 的 Tier 2 趋势地板**。立项源于 171 阶段的代码级审计：A2（文学从不阻塞、T9 硬缺陷阻塞）为真但属既有架构涌现属性，而 **A1（分层视图）/A3（趋势地板+抽读）/A4（数据标定）此前在代码中缺失**。本任务补齐三项，**全程 observe-only：不新增任何阻塞门、不改冻结口径、不做 LLM 闭环、不阻塞 Ch200。**

---

## 验收对照（框架 §8 A 组）

| 编号 | 验收项 | 状态 | 证据 |
|---|---|:---:|---|
| A1 | 三层契约在报告出口可见、互不混淆 | ✅ | `render_three_tier_contract_summary`：metrics 顶部三层分区（Tier1 硬缺陷**阻塞** / Tier2 趋势**observe** / Tier3 研究值**不判定**），各标阻塞性 |
| A2 | Tier 1 硬缺陷仍阻塞 | ✅（行为层，既有） | T9 meta/重复经 `review_merger` 提 major/critical 阻塞；本任务在摘要汇总展示、未改阈值 |
| A3 | Tier 2 改趋势观测 + 抽读触发 | ✅ | `detect_literary_spot_read`：`max(base×0.85, 3.0)` 地板，跌破置 `spot_read_recommended`，**无 halt/gate 接线**（单测锁定 observe-only） |
| A4 | Tier 2 参数用真实数据标定 | ✅ | `run_171d_calibrate.py` 跑 4 个真实 DB（scifi 170p / wuxia 171a-1 / 170i / v6_159 共 465 章），确认 rubric 为 1–10、均值 5–8，据此定绝对地板 3.0 |

---

## 工程改动清单

### `src/songyan/evals/db_metrics.py`
- 新增 `LiterarySpotReadResult` 模型 + `detect_literary_spot_read(...)`：Tier 2 趋势地板（相对 ×0.85 + 绝对 3.0，取 max），滚动窗口均值跌破→建议人工抽读。**observe-only，无 halt/gate 接线**；与既有 `detect_literary_trend`（×0.80/T3 诊断）口径独立并存。
- 新增 `render_three_tier_contract_summary(...)`：A1 三层分区摘要（Tier1/2/3 分列、标阻塞性、互不混淆）。
- `render_stage_a_metrics`：顶部插入三层契约摘要段（Tier1 硬缺陷数从 text_cleanliness 的 meta+重复计数汇总）。

### `scripts/run_171d_calibrate.py`（新增）
- 从 4 个真实 DB 读 `literary_observations`（经 version_id join chapter_versions），输出各维度基线分布 + 参数依据报告。校准发现 rubric 为 **1–10**（非先前假设的 1–5），据此把绝对地板从 2.0 修正为 3.0。

### 测试
- `tests/test_171d_three_tier_contract.py`（9）：基线不足不触发、稳定不触发、相对地板跌破触发、绝对地板保护、**observe-only 形状**（无 halt/blocked/gate 字段）、三层渲染标注、Tier2 行必标"不阻塞"。

---

## 关键校准发现（诚实标注）

- **rubric 是 1–10 量表**（标定实测均值 5.35–8.28、健康章最小 4.0–6.0），非最初假设的 1–5 → 绝对地板 2.0 修正为 3.0。
- **v6_159 的最小值 0.00 是缺失哨兵**（个别章未跑 LiteraryAuditor），非真实塌陷；标定用均值不受单点 0 影响，报告已显式标注不误判为质量事件。

---

## 验证清单
- [x] `ruff check src/ tests/ scripts/run_171d_calibrate.py` 全通过。
- [x] `test_171d_three_tier_contract.py`(9)+`test_145_stage_a_metrics.py`+`test_148_foreshadowing_metrics.py`+`test_llm_client.py`+`test_171c_literary_postproc.py`+`test_171b_sampling.py` **49 passed**（`render_stage_a_metrics` 插入新段无回归）。
- [x] `run_171d_calibrate.py` 跑通 4 DB、465 章，报告落 `archive/v7/reports/task-171d-three-tier-contract-report.md`。
- [x] 框架 §8 A 组表已加"代码现状溯源说明"，A1/A3/A4 指向本任务。

---

## 出口与下一步
- **A 组达标**：三层契约在代码层可见、可复算，Tier 2 趋势地板 observe-only 落地并数据标定。
- **框架 §8 五组进度**：A ✅（171d）/ B ✅（171a/171a-1）/ C ✅（171b）/ E ✅（事实源纪律贯穿）；**仅剩 D（Ch200 规模化真实证据）由 Task 171 主线承接**。
- 171d 不阻塞 Ch200；三层契约里 Tier 2 永远只建议抽读、不自动阻塞。
