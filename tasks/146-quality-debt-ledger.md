# Task 146: 质量债账本

> **Phase**: V6 阶段 A（度量同步）
> **优先级**: P1
> **依赖**: Task 145（度量出口框架 `db_metrics` + `songyan metrics`）
> **预计工作量**: 中
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 A、§1.4-T4

---

## Goal

跨章累计 `degraded_accept` / `convergence_failed` / `quality_gate_passed=false` 的章数与占比，做成"质量债账本"，持久化到 run 级表，并在度量出口按 §1.4-T4 口径标红线。

## Context（代码核实）

- 三个信号都是 **per-chapter 字段**，已存在于 `ChapterRunLog`（`models/run_log.py`）：`degraded_accept: bool`（L75）、`convergence_failed: bool`（L71）、`quality_gate_passed: bool | None`（L65）。写入 `logs/chapter_runs/<run_id>.jsonl`（`_run_logger.py` `write_run_log`）。**这是三信号的权威来源**；`read_run_logs(run_id)`（`evals/streaming_report.py:33`）只读 `logs/chapter_runs/<run_id>.jsonl`。
- **历史数据缺口（C3）**：导出用的 `.tmp/task138*_per_chapter_metrics.jsonl`（20 键）只含 `quality_gate_passed`，**不含 `degraded_accept`/`convergence_failed`**；历史全量 run 日志（`logs/chapter_runs/`）在 V6 清理时已删；`run_quality_debt` 表历史 DB 也没有。→ **T4 无法从 138n/138k 完整历史标定**：degraded/convergence 分布不可得；qg_false 只能经一次性适配器从 `.tmp/*_per_chapter_metrics.jsonl` 近似。
- `project_runs` 表（`schema.sql:349`）只存进度/成本/状态，无质量聚合；无 per-run 度量表。
- T4 红线：任一连续 50 章窗口内 `degraded_accept` 占比 **≤20%** 且 `convergence_failed` 占比 **≤10%**；超出触红线。

### 设计决策

1. **账本来源 = ChapterRunLog run 日志**（含全部三信号），不是 DB。聚合器读 `logs/chapter_runs/<run_id>.jsonl`（复用 `read_run_logs`）。
2. **run 级持久化 = 新增 `run_quality_debt` 表**，作为**项目↔run 的度量桥**：`songyan metrics --project-id X` 从 `run_quality_debt WHERE project_id=X` 读汇总（列出该项目所有 run 的质量债，默认全部；逐章明细需 `--run-id` 再解析 run 日志）。历史 DB 无此表 → metrics 的质量债段对历史 DB **优雅降级为"无 run 质量债记录"**。
3. **增量持久化（S4）**：`run_quality_debt` 采用**每章 accept 后 upsert**（单行汇总，成本低），而非仅 run 收尾写——否则被 kill 的 run（R 维度 kill→resume 场景）永不写入，"DB 比日志耐久"的理由就落空。resume 时按 run_id upsert 覆盖同一行，避免重复计数。run 收尾再 upsert 一次终值。
4. **T4 标定口径（C3 收口）**：degraded/convergence 子阈值**不做历史标定**，标为 provisional，冻结时机推迟到阶段 D 首个窗口（Task 157）实测；标定报告用一次性适配器把 `.tmp/*_per_chapter_metrics.jsonl` 的 `quality_gate_passed=false` 喂给 `compute_quality_debt`（仅 qg_false 口径）做参考分布，并**明确注明**这不是 degraded/convergence 的历史依据。

## In Scope（必须完成）

- [ ] 质量债聚合器（`evals/db_metrics.py`，与 145 同文件/包）：`compute_quality_debt(logs: list[ChapterRunLog], window: int = 50) -> QualityDebtReport`——总章数、degraded_accept/convergence_failed/qg_false 章列表与占比；**50 章滑窗**内 degraded/convergence 占比；按 T4（degraded ≤20% 且 convergence ≤10%）判定每个 50 章窗口是否触红线。窗口不足 50 章时报"窗口不足"而非误判。
- [ ] `run_quality_debt` 表 + 迁移（`_migrate_run_quality_debt`，注册三处；`REFERENCES project_runs(run_id) ON DELETE CASCADE`）：`run_id PK, project_id, total_chapters, degraded_count, convergence_failed_count, qg_false_count, degraded_ratio, convergence_ratio, t4_breached INTEGER, updated_at`。
- [ ] repo（新 `RunQualityDebtRepository` 或并入 `ProjectRunRepository`）：`upsert_quality_debt(row)` / `get_quality_debt(run_id)` / `list_quality_debt_by_project(project_id)`。
- [ ] 增量写入：在 `workflows/phase2_graph.py` **每章 accept 后**（run 循环内）用当前累计 run 日志 upsert `run_quality_debt`（非阻塞，失败仅告警）；run 收尾再 upsert 终值。
- [ ] `songyan metrics` 增质量债段：从 `run_quality_debt` 读该项目各 run 汇总 + T4 红线提示；`--run-id` 给出时追加逐章降级/收敛失败/QG-false 明细与 50 章滑窗占比。历史 DB / 无记录时降级提示。
- [ ] 一次性标定适配器（`evals/db_metrics.py` 或标定脚本）：`quality_debt_from_metrics_jsonl(path) -> QualityDebtReport`（仅 qg_false，用于标定报告参考分布）。
- [ ] 单测：构造 ChapterRunLog 列表覆盖 degraded/convergence/qg_false 组合 → 断言计数、占比、50 章窗口 T4 判定（含窗口不足、恰好触线边界）；表迁移 + repo 往返 + 增量 upsert 覆盖同 run_id；jsonl 适配器 qg_false 计数。

## Out of Scope（明确不做）

- 不改 gate/settlement 判定逻辑（只统计已产出的信号）。
- 不把 degraded/convergence 补进历史数据（不可得；标定报告注明 provisional）。
- 不做质量债驱动的自动治理（阶段 B/门禁自适应，V7）。

## 接口契约

```python
class QualityDebtWindow(BaseModel):
    start_chapter: int
    end_chapter: int
    degraded_ratio: float
    convergence_ratio: float
    t4_breached: bool

class QualityDebtReport(BaseModel):
    total_chapters: int
    degraded_chapters: list[int]
    convergence_failed_chapters: list[int]
    qg_false_chapters: list[int]
    degraded_ratio: float
    convergence_ratio: float
    windows: list[QualityDebtWindow]     # 每个 50 章滑窗
    t4_breached: bool                    # 任一窗口触红线

def compute_quality_debt(logs: list[ChapterRunLog], window: int = 50) -> QualityDebtReport: ...
```

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_146_quality_debt.py -v` 全通过（计数/占比/50 章滑窗 T4/边界/迁移/repo 增量 upsert/jsonl 适配器）。
- [ ] `ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] run 进行中/结束均可查"降级接受章列表 + 各占比"（`run_quality_debt` 每章 upsert + metrics 段）。
- [ ] metrics 输出质量债汇总段并按 T4 口径标红线；历史 DB 优雅降级。
- [ ] 不违反不可违背规则：run 级写入经 repository；类型标注齐全。
- [ ] 生成 `tasks/146-...-DONE.md`；更新 `tasks/V6-README.md` 与 `docs/STATUS.md`；T4 历史标定缺口（degraded/convergence 不可得、provisional 至 Task 157）如实记录，并交由 `tasks/148z` 标定报告收口。

## 参考文档

- `docs/v6-plan.md` §3 阶段 A（Task 146 行）、§1.4-T4/T2
- 代码：`models/run_log.py`（ChapterRunLog）、`workflows/_run_logger.py`、`evals/streaming_report.py`（`read_run_logs` L33）、`workflows/phase2_graph.py`（run 循环 + 收尾 ~L510）、`db/project_run_repo.py`、`db/migrations.py`
