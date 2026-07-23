# Task 156: 运行中 DB 维护 — DONE

> **Phase**: V6 阶段 C（工程加固）
> **状态**: ✅ 完成
> **合入时间**: 2026-07-02
> **事实文档**: 本文件

---

## 完成摘要

在长跑中按周期执行 SQLite 物理层维护（`wal_checkpoint(TRUNCATE)` + `PRAGMA optimize`），同步采样 DB 尺寸、WAL 尺寸与代表性连续性扫描耗时遥测并入库，使 T5 红线（Ch100 时 DB ≤300MB、扫描耗时 ≤ 基线 1.5×）从"延后待测"变为"长跑中可读可判"。

---

## 实现落点

### 156a — 周期维护调度

- `workflows/phase2_graph.py`：
  - 新增模块常量 `_DB_MAINTENANCE_INTERVAL = 10`（与质量债刷新周期对齐）。
  - 新增 `_run_db_maintenance(run_id, project_id, chapter_number, *, final=False)`：
    - 用**独立短连接**在章节边界执行；
    - 先采样 DB 尺寸（库文件 + `-wal` 文件 + `page_count`/`page_size`）与 `find_orphaned` 扫描耗时；
    - 执行 `PRAGMA wal_checkpoint(TRUNCATE)` 截断 WAL、`PRAGMA optimize` 更新查询计划；
    - 仅在 `final=True` 且 DB 尺寸超过 200MB 时尝试整库 `VACUUM`，避免中途重写全库；
    - 全程 try/except 非阻塞，失败只告警不中断 run。
  - 主循环每 10 章触发一次维护；run 收尾再兜底触发一次（含 final 标志）。

### 156b — DB 尺寸/查询耗时遥测 + T5 判定

- 新增 `evals/db_maintenance_metrics.py`：
  - `collect_db_size_metrics()`：读取库文件、`-wal` 文件尺寸与 `page_count`/`page_size`。
  - `measure_continuity_scan_latency(project_id, up_to_chapter)`：以 `SettingTrackingRepository.find_orphaned` 为代表性扫描并计时。
  - `check_t5_size_redline(...)` / `check_t5_latency_redline(...)`：T5 红线判定。
- 新增 `db/run_db_metrics_repo.py`：`RunDbMetricsRepository` 读写 `run_db_metrics` 表。
- 新增 `db/run_db_metrics` 表（schema.sql + migrations.py）：按 run/chapter 记录尺寸与扫描耗时；`run_id` 无外键约束（遥测表允许与 run 记录松耦合），`project_id` 保留外键。
- `evals/db_metrics.py` 扩展：
  - `collect_db_maintenance_samples` + `render_db_maintenance_section`；
  - `render_stage_a_metrics` 新增 T5 遥测段，供 `songyan metrics` 直接读出。

---

## 接口契约

```python
# workflows/phase2_graph.py
_DB_MAINTENANCE_INTERVAL = 10
_DB_VACUUM_SIZE_THRESHOLD_BYTES = 200 * 1024 * 1024

async def _run_db_maintenance(
    run_id: str,
    project_id: str,
    chapter_number: int,
    *,
    final: bool = False,
) -> None:
    """章节边界的物理层维护（非阻塞）：采样遥测 + wal_checkpoint(TRUNCATE) + optimize.
    VACUUM 仅在收尾且尺寸超阈时触发。
    """

# evals/db_maintenance_metrics.py
async def collect_db_size_metrics() -> DbSizeMetrics: ...
async def measure_continuity_scan_latency(project_id: str, up_to_chapter: int) -> float: ...

# db/run_db_metrics_repo.py
class RunDbMetricsRepository: ...
```

---

## 关键口径

- **章节边界执行**：维护只在两章之间触发，不在任何写事务中穿插；用独立 `get_db()` 短连接。
- **非阻塞**：维护失败（锁冲突、只读库等）只记录 warning，不中断 run。
- **WAL 截断**：默认每 10 章 `PRAGMA wal_checkpoint(TRUNCATE)`，防止 `-wal` 不无界增长。
- **VACUUM 保守**：不在中途做整库 `VACUUM`；仅在 run 收尾且 DB >200MB 时触发，减少长阻塞。
- **T5 基线**：扫描耗时基线取该 run 前 10 个样本均值，与 T3 "前 10 章基线" 精神一致；红线 = 基线 ×1.5。
- **不改既有逻辑**：不改 `get_db()` PRAGMA / RES-03/RES-04；不改逻辑层生命周期归档；不新增 Agent/LLM。

---

## 测试覆盖

`tests/test_156_in_run_db_maintenance.py`（11 个用例）：

- `test_collect_db_size_metrics`：DB/WAL 尺寸与文件系统一致。
- `test_measure_latency_positive`：扫描耗时返回正值。
- T5 红线：尺寸超 300MB、耗时超基线 1.5×、无基线时不误判。
- `test_persists_sample`：维护把遥测样本写入 `run_db_metrics`。
- `test_non_blocking_on_failure`：维护内部异常不中断调用方。
- `test_wal_checkpoint_truncate`：维护后 WAL 文件被截断或不存在。
- `test_maintenance_triggered_every_interval`：主循环每 10 章触发 + 收尾触发。

---

## 验证结果

- `pytest tests/test_156_in_run_db_maintenance.py -v`：11 passed。
- `pytest tests/test_153_run_level_resume.py tests/test_154_llm_rate_limit_and_budget.py tests/test_155_failure_isolation.py tests/test_156_in_run_db_maintenance.py tests/test_phase2_graph.py tests/workflows/test_checkpointer.py -q`：66 passed，无回归。
- `ruff check src/ tests/`：通过。
- 全量 `pytest tests/ -q` 由 PowerShell Job + 硬超时包装执行（见任务执行记录）。

---

## Layer 3 计划

Task 156 的"开/关维护对比、-wal 不无界增长、T5 遥测曲线"实跑证据将在 **Task 158（Ch1-Ch100 长跑验证）** 中统一采集并入 `docs/reports/`。当前模块测试已覆盖维护动作、遥测采样、周期触发、非阻塞与 T5 判定等全部口径。

---

## 参考

- 规划：`docs/v6-plan.md` §3 阶段 C
- 任务文档：`archive/v6/tasks/156-in-run-db-maintenance.md`
- 相关代码：`src/songyan/workflows/phase2_graph.py`、`src/songyan/evals/db_maintenance_metrics.py`、`src/songyan/db/run_db_metrics_repo.py`、`src/songyan/evals/db_metrics.py`、`src/songyan/db/schema.sql`、`src/songyan/db/migrations.py`
