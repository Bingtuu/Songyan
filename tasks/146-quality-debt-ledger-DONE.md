# Task 146 DONE — 质量债账本

> **Phase**: V6 阶段 A（度量同步）
> **状态**: ✅ 完成（聚合器 + run_quality_debt 表 + 每章增量 upsert + jsonl 适配器 + metrics 段）
> **完成日期**: 2026-07-01
> **规划/设计**: `docs/v6-plan.md` §3 阶段 A、§1.4-T4；任务书 `tasks/146-quality-debt-ledger.md`

---

## 交付概览

跨章累计 `degraded_accept` / `convergence_failed` / `quality_gate_passed=false`，做成质量债账本，持久化到 run 级表，并在 `songyan metrics` 按 T4 口径标红线。

| 交付物 | 文件 |
|--------|------|
| 聚合器 + 模型 | `evals/db_metrics.py`：`compute_quality_debt(logs, window=50)`、`QualityDebtReport`/`QualityDebtWindow`、`quality_debt_row`、`quality_debt_from_metrics_jsonl`、`render_run_quality_debt_section` |
| run 级表 | `run_quality_debt`（迁移 `_migrate_run_quality_debt`，注册 `_EXPECTED_TABLES`+`init_schema`+`run_migrations`；FK→project_runs ON DELETE CASCADE） |
| repo | `db/run_quality_debt_repo.py`：`RunQualityDebtRepository`（upsert/get/list_by_project）+ `RunQualityDebtRow` |
| 增量写入 | `workflows/phase2_graph.py` `_upsert_quality_debt`，每章 `_run_single_chapter` 后调用（非阻塞） |
| metrics 段 | `render_stage_a_metrics` 追加"质量债账本"段（读 `run_quality_debt` by project_id） |
| 测试 | `tests/test_146_quality_debt.py`（10 用例） |

## 关键实现点

- **来源=run 日志**（`ChapterRunLog` 含全部三信号），非 DB；聚合器读 `read_run_logs(run_id)`。
- **T4 口径**：50 章滑窗内 `degraded_ratio > 20%` 或 `convergence_ratio > 10%` 即破线（`≤` 合规用严格 `>` 判破）；总章数 < 50 时 `window_sufficient=False`、不产窗口、不误判。
- **增量 upsert（S4 修正）**：每章 upsert `run_quality_debt`（单行，`ON CONFLICT(run_id) DO UPDATE`），使被 kill 的 run 也留有截至当前的汇总；不再仅 run 收尾写。
- **项目↔run 桥（S2 修正）**：`songyan metrics --project-id X` 从 `run_quality_debt WHERE project_id=X` 读各 run 汇总；历史 DB / 无记录时优雅降级为"无 run 质量债记录"。
- **T4 历史标定缺口（C3）**：degraded/convergence 不在历史数据 → **provisional，冻结推迟到阶段 D 首窗（Task 157）**；`quality_debt_from_metrics_jsonl` 适配器可从 `.tmp/*_per_chapter_metrics.jsonl` 算 qg_false 参考分布（degraded/convergence 恒 0），仅供 148z 标定报告参考。

## 验证

- `pytest tests/test_146_quality_debt.py -q` → **10 passed**（计数/占比/50 章窗破线+边界+窗口不足/表迁移/repo 增量 upsert 幂等/FK 级联/jsonl 适配器/渲染）。
- `pytest tests/db/test_migrations.py tests/db/test_schema.py tests/test_141_narrative_skeleton.py -q` → **38 passed**（新表不破坏 schema 版本口径）。
- `ruff check`（改动文件）→ **All checks passed**。

## Out of Scope（未做）

- 不改 gate/settlement 判定；不做质量债驱动治理（V7）。
- degraded/convergence 与 T5 红线实测冻结留阶段 D；由 `tasks/148z` 标定报告收口。
