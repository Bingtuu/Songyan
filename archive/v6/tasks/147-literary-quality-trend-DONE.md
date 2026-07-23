# Task 147 DONE — 文学质量趋势化

> **Phase**: V6 阶段 A（度量同步）
> **状态**: ✅ 完成（范围回读 + W=5 滑窗 T3 趋势检测 + metrics 段；只诊断不阻断）
> **完成日期**: 2026-07-01
> **规划/设计**: `docs/v6-plan.md` §3 阶段 A、§1.4-T3/T8；任务书 `archive/v6/tasks/147-literary-quality-trend.md`

---

## 交付概览

文学四维度已入库；本 Task 增加"按章范围回读 + W=5 滑动窗口趋势查询"，按 T3/T8 检出"连续 5 章某维度均值相对前 10 章基线降 ≥20%"。**不接入 accept/gate，只诊断。**

| 交付物 | 文件 |
|--------|------|
| 范围回读 | `db/review_repo.py` `LiteraryObservationRepository.list_scores_by_chapter_range(project_id, start, end)`（JOIN chapter_versions，每章取最新一条 observation） |
| 趋势模块 | `evals/db_metrics.py`：`LiteraryScorePoint`/`LiteraryTrendResult`、`collect_literary_scores`、`detect_literary_trend`、`render_literary_section` |
| metrics 段 | `render_stage_a_metrics` 追加"文学质量趋势"段 |
| 测试 | `tests/test_147_literary_trend.py`（9 用例） |

## 关键实现点

- **章节关联**：`literary_observations` 无 `chapter_number`，经 `version_id → chapter_versions.chapter_number` JOIN；每章多版本/多次审查时取 `created_at` 最新一条（Python 去重取首）。
- **维度名**：用真实列 `literary_quality_score`/`character_autonomy_score`/`conceptual_grounding_score`/`fissure_preservation_score`；`conceptual_idling` 是 observation 类型（不在本任务趋势化）。
- **T3 口径**：基线=前 `baseline_n=10` 章均值；窗口=`W=5` 滑窗均值；某维度当 `窗口均值 <= 基线 × (1 - 0.20)` 触线（即下降 **≥20%** 触线，含恰好 20% 边界）。基线不足 10 章 → `baseline_available=False`，不判红线。
- **只诊断**：无任何 gate/accept 接入；渲染段标注"只诊断不阻断"，单测断言之。

## 验证

- `pytest tests/test_147_literary_trend.py -q` → **9 passed**（范围回读每章取最新版本 / 空 / 基线不足 / 稳定不误报 / 下滑触线 / 恰好 20% 触线 / <20% 不触线 / 只诊断）。
- `ruff check`（改动文件）→ **All checks passed**。

## Out of Scope（未做）

- 不改 LiteraryAuditor 生成逻辑、不接入 accept/gate；不做文学闭环修复（V7）。
- T3 的 20%/基线口径在 `tasks/148z` 标定报告用 138n `literary_observations` 复算校准后冻结。
