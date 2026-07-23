# Task 156: 运行中 DB 维护

> **Phase**: V6 阶段 C（工程加固）
> **优先级**: P1（长跑中控制 WAL/DB 膨胀与扫描退化，落地 §1.4-T5 红线的实测底盘）
> **依赖**: 阶段 0/A/B 已落地；复用现有 `get_db()` 连接与 phase2 周期刷新 idiom；T5 在本 Task/158 实测
> **预计工作量**: 中（拆 156a 周期维护调度 + 156b DB 尺寸/查询耗时遥测与 T5 判定）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 C

---

## Goal

在长跑中按周期执行 SQLite 维护（`wal_checkpoint` 截断 WAL、必要时增量 `VACUUM`、`PRAGMA optimize`/`ANALYZE`），把 DB 文件与 `-wal` 增长、连续性扫描查询耗时控制在 §1.4-T5 红线内（Ch100 时 DB ≤300MB、扫描查询耗时 ≤ 基线 1.5×）；并新增 DB 尺寸/查询耗时**遥测**，让 T5 从"延后待测"变为"长跑中可读可判"。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- **连接与 PRAGMA**：`get_db()`（`src/songyan/db/connection.py:33-70`），`@asynccontextmanager` over `aiosqlite.connect`。每连接设 `foreign_keys=ON` / `journal_mode=WAL` / `synchronous=NORMAL` / `busy_timeout=30000`（`:47-50`），连接时跑 `PRAGMA quick_check`（`:54`，RES-03，try/except 仅告警）与 RES-04 残留 `-wal`/`-shm` 清理（`:59-69`）。**WAL 已启用**（schema 也声明，`schema.sql:4-5`）。
- **运行中无任何 DB 维护**：`src/` 内无 `VACUUM` / `wal_checkpoint` / `PRAGMA optimize` / `ANALYZE`。唯一 VACUUM 在**离线脚本** `scripts/full_cleanup.py:107-113`（`vacuum_db()` 用裸 `sqlite3.connect`，重跑前手动执行）。gap 分析 `docs/300-chapter-gap-analysis.md:153` 确认"运行中无 VACUUM，VACUUM 仅离线脚本"。（大量 `checkpoint` 命中是 LangGraph checkpointer，与 DB 维护无关。）
- **已有周期 idiom（新维护应照抄此范式）**：`phase2_graph.py` 主循环有 Task 146 的质量债周期刷新——模块常量 `_QUALITY_DEBT_FLUSH_INTERVAL = 10`（`phase2_graph.py:123`）+ 循环内 `if chapter_number % _QUALITY_DEBT_FLUSH_INTERVAL == 0: await _upsert_quality_debt(...)`（`:432-433`，非阻塞 try/except）+ **run 收尾兜底刷新一次**（`:538`）。其它 cadence 例：`_nodes.py` `% 50 == 0`、`_helpers.py` 卷边界 `% 30 == 0`。新维护 = 同样的"模块常量 + `% interval == 0` + 收尾兜底"。
- **T5 红线与遥测缺口**：`docs/v6-plan.md:43`（T5）"Ch100 时 DB ≤300MB（150 章基线 196MB）；单次连续性扫描查询耗时 ≤ 基线 1.5×"；Task 156 行 `v6-plan.md:132`。标定报告 `archive/v6/reports/v6-stageA-threshold-calibration.md:48-49` 明确 **T5 延后到长跑（Task 156/158）实测**（干净 150ch 基线 ≈196MB 待重测；`.tmp` 历史库 404-416MB 是多项目、非干净基线）。**运行时无 DB 尺寸/查询耗时遥测**：grep `getsize`/`page_count`/`db_size`/`st_size`/`elapsed_ms` 在 `src/` 无相关命中（`evals/db_metrics.py` 收 orphan/critical/lifecycle 指标，但无文件尺寸/耗时）；尺寸只在离线 `full_cleanup.py` 用 `DB_PATH.stat().st_size` 量。
- **已有生命周期清理（只归档、不缩库）**：`db/lifecycle_scheduler.py` + `db/lifecycle_cleaners.py`（`get_default_scheduler()` 注册 SettingSnapshot/Dedup/Foreshadowing/HumanMark/CharacterState cleaners）**只 UPDATE `lifecycle_status`、从不 DELETE**，故不缩小 DB 物理体积。它们**每章结算后**触发（`_nodes.py` `_run_lifecycle_cleanup` 于 `:2432`，`if accepted_for_postprocessing:` 守护），非周期；`SettingDeduplicationCleaner` 自带 `if current_chapter % 10 != 0: return`（`lifecycle_cleaners.py:171`）。→ 本 Task 是**物理层维护**（WAL 截断/VACUUM/optimize），与它们的**逻辑层归档**互补、不重叠。
- **并发形态**：连接是**每操作一开**（`async with get_db()`，全仓 143 处、19 文件），无共享/池化连接；单进程 asyncio、单章内 `await` 顺序执行。**WAL 交互要点**：`VACUUM` 需写锁且不能在事务中执行、会重写整库短暂阻塞写者；`PRAGMA wal_checkpoint(TRUNCATE)` 是**长跑中安全便宜**的选项（截断 `-wal`）。→ 维护须在**章节边界**（`% interval == 0`、非事务中）用**独立短连接**执行，绝不在某个操作的事务里穿插。

**为什么现在做**：阶段 D 的 Ch100/Ch150 长跑是 T5 唯一能真实标定的场景。若不在运行中截断 WAL / 周期维护，长跑的 `-wal` 与碎片可能把扫描查询拖过 1.5× 或把库撑过 300MB，且现在**根本没有遥测**能发现它。本 Task 同时补"维护动作"与"看得见的度量"。

## Cross-Task Coordination（阶段 C 统一口径）

- **周期 idiom 复用**：新增 `_DB_MAINTENANCE_INTERVAL`（模块常量，首版取 **10**，与质量债刷新对齐，便于同章边界一起做）+ 循环内 `% interval == 0` 触发 + 收尾兜底一次。维护调用**非阻塞**（try/except 包裹，失败只告警不中断 run），与 `_upsert_quality_debt` 同风格。
- **独立短连接、避开事务**：维护用**自己的 `get_db()` 短连接**执行，且只在章节边界（两章之间、无进行中事务）触发；`VACUUM` 绝不与任何写事务并发。DONE 需说明为何选在边界执行。
- **与 153（resume）的关系**：153 会清理**孤儿 LangGraph checkpoint 行**（逻辑清理）；156 做**物理层 WAL/VACUUM**。二者可先后发生但互不依赖；若 checkpointer 用 sqlite 且与主库同文件，VACUUM 前应确保无活跃 checkpoint 写（章节边界天然满足）。
- **维护动作分级（权威口径）**：
  1. **每 `interval` 章**：`PRAGMA wal_checkpoint(TRUNCATE)` + `PRAGMA optimize`（便宜、不重写全库、不长阻塞）——**默认启用**。
  2. **增量 VACUUM**：仅在**遥测显示碎片/尺寸超阈**时触发（如 DB 尺寸增速异常或 `PRAGMA freelist_count` 过高），或 run 收尾做一次；**不每章 VACUUM**（重写全库代价高）。首版可用 `PRAGMA incremental_vacuum`（需 `auto_vacuum=INCREMENTAL`，评估是否改 schema）或收尾整库 `VACUUM`，DONE 明确选型与理由。
  3. `ANALYZE` 随 `PRAGMA optimize` 由 SQLite 自行决定，不单独强制。

### 遥测口径（权威定义）

- **DB 尺寸**：`db_path.stat().st_size`（复用 `full_cleanup.py` 口径）+ 可选 `PRAGMA page_count * page_size`；WAL 单独量 `-wal` 文件尺寸（截断有效性证据）。
- **扫描查询耗时基线**：选一条**代表性连续性扫描**（如 `find_orphaned` / 全项目 setting_tracking 扫描）作为 T5 的"连续性扫描查询"，在 run 内周期性 `time.monotonic()` 计时，记录 `elapsed_ms`。**基线 = 该 run 前若干章的均值**（与 T3 的"前 10 章基线"精神一致），红线 = 基线 ×1.5。
- 遥测入库到度量表 / run 日志，供 `songyan metrics` 或报告读出，避免只打印不留痕。

## In Scope（必须完成）

### 156a — 周期维护调度
- [ ] 新增 `_DB_MAINTENANCE_INTERVAL`（模块常量，首版 10）与维护函数（如 `_run_db_maintenance(run_id, project_id)`），在 `phase2_graph.py` 主循环按 **Cross-Task Coordination「周期 idiom」** 触发 + 收尾兜底一次；非阻塞 try/except。
- [ ] 维护动作按 **「维护动作分级」**：每 interval 章 `wal_checkpoint(TRUNCATE)` + `PRAGMA optimize`（默认启用）；增量/整库 `VACUUM` 按遥测触发或收尾执行（选型写入 DONE）。
- [ ] 用独立短连接、只在章节边界执行；不穿插进任何写事务；WAL 语义安全（引用 Context 的并发要点）。
- [ ] 遵守边界：只加物理层维护，不改 `get_db()` 的既有 PRAGMA 与 RES-03/RES-04 逻辑；不改逻辑层生命周期归档（lifecycle_cleaners）。

### 156b — DB 尺寸/查询耗时遥测 + T5 判定
- [ ] 新增 DB 尺寸遥测（按 **「遥测口径」**：库文件 + `-wal` 尺寸），周期采样并入库/入 run 日志。
- [ ] 新增代表性连续性扫描查询耗时遥测（`elapsed_ms`），周期采样，计算 run 内基线与 ×1.5 红线判定。
- [ ] 遥测可在 `songyan metrics` / report 读出（新增一段或复用 db_metrics 输出通道），使 T5 可判真假。
- [ ] 遵守边界：遥测只读不改业务数据；采样开销极小（章节边界采样、非每操作）；不新增 Agent/LLM。

## Out of Scope（明确不做）

- 不改逻辑层生命周期归档（`lifecycle_cleaners`/`lifecycle_scheduler` 只归档不缩库，保持现状；本 Task 是物理层维护，互补）。
- 不做 run 级断点续跑（153）、LLM 限流预算（154）、失败隔离（155）。
- 不改 `get_db()` 既有 PRAGMA / RES-03 quick_check / RES-04 WAL 清理逻辑。
- 不做跨进程/多库分片维护（V6 单进程单库）。
- 不在每章做整库 `VACUUM`（代价高、长阻塞）——整库 VACUUM 至多收尾一次或按遥测触发。
- 不冻结 T5 的最终 ⚙ 阈值（干净 150ch 基线在 Task 158 长跑实测后才定；本 Task 提供遥测与维护，实测归 158）。

## 接口契约

```python
# workflows/phase2_graph.py
_DB_MAINTENANCE_INTERVAL = 10  # 与 _QUALITY_DEBT_FLUSH_INTERVAL 对齐，章节边界一起做

async def _run_db_maintenance(run_id: str, project_id: str) -> None:
    """章节边界的物理层维护（非阻塞）：wal_checkpoint(TRUNCATE) + PRAGMA optimize；
    VACUUM 按遥测/收尾触发。用独立短连接，避开写事务。失败仅告警不中断 run。"""

# 遥测（evals/db_metrics.py 或同层新模块）
async def collect_db_size_metrics() -> DbSizeMetrics:
    """采样 DB 文件尺寸、-wal 尺寸、page_count；供 T5 尺寸红线判定."""

async def measure_continuity_scan_latency(project_id: str) -> float:
    """计一条代表性连续性扫描的 elapsed_ms；供 T5 耗时红线（基线 ×1.5）判定."""
```

（最终签名以实现为准；核心：章节边界非阻塞维护 + 尺寸/耗时遥测可读，且不改既有 PRAGMA/清理逻辑。）

## 测试要求

### Layer 2: 模块测试（真实临时 SQLite）
- [ ] **wal_checkpoint 生效**：写入若干数据使 `-wal` 增长后调用维护，验证 `-wal` 尺寸被截断（或 checkpoint 返回成功）；DB 仍可正常读写、数据不丢。
- [ ] **维护非阻塞**：维护函数内部抛异常时被 try/except 吞掉并告警，不中断调用方（模拟锁冲突/只读场景）。
- [ ] **周期触发**：mock 主循环，验证 `% _DB_MAINTENANCE_INTERVAL == 0` 的章触发维护、其它章不触发、收尾兜底触发一次（复用质量债刷新的测试范式）。
- [ ] **尺寸遥测**：`collect_db_size_metrics` 返回的库/`-wal` 尺寸与 `stat().st_size` 一致；`page_count * page_size` 合理。
- [ ] **耗时遥测 + T5 判定**：`measure_continuity_scan_latency` 返回正 `elapsed_ms`；构造基线与超基线 ×1.5 的样本，验证红线判定正确。
- [ ] **不误改数据**：维护/遥测前后业务表行数与内容不变（VACUUM 不丢数据）。

### Layer 3: 长窗口佐证（阶段 C 出口 / 交给 Task 158 实测）
- [ ] 小窗口/隔离副本上验证维护随周期执行、`-wal` 不无界增长、遥测曲线可读；DB 尺寸与扫描耗时可对比"开/关维护"两组。
- [ ] T5 的干净 150ch 基线（≈196MB 待重测）与 Ch100 ≤300MB / 扫描 ≤基线 ×1.5 的**最终判定归 Task 158 长跑**；本 Task 交付遥测 + 维护并记录小窗口趋势。证据入 `docs/reports/`。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_156_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] 长跑中按周期执行 `wal_checkpoint(TRUNCATE)` + `PRAGMA optimize`（默认），VACUUM 按遥测/收尾触发；维护非阻塞、用独立短连接、避开事务。
- [ ] DB 尺寸（库 + `-wal`）与连续性扫描耗时遥测入库可读；T5 尺寸/耗时红线判定逻辑就位（最终阈值实测归 158）。
- [ ] 不违反不可违背规则：不改 `get_db()` 既有 PRAGMA/RES-03/RES-04；不改逻辑层归档；不每章整库 VACUUM；不新增 Agent/LLM。
- [ ] 生成 `archive/v6/tasks/156-in-run-db-maintenance-DONE.md`，含维护动作分级与选型理由、遥测口径、章节边界执行的并发安全说明、小窗口趋势与 T5 待测标注。
- [ ] 更新 `tasks/V6-README.md`（156 状态 + **阶段 C 出口结论**：单命令无人值守 Ch1-Ch100 可 kill→resume 续完，需 153/154/155/156 合入后由阶段 D 佐证）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.4-T5（DB/性能红线）、§3 阶段 C（Task 156 行 + 阶段 C 出口）
- T5 标定延后依据：`archive/v6/reports/v6-stageA-threshold-calibration.md:48-49`
- 现有代码：`db/connection.py:33`（`get_db` PRAGMA/WAL/RES-03/RES-04）、`workflows/phase2_graph.py:123`&`:432`&`:538`（`_QUALITY_DEBT_FLUSH_INTERVAL` 周期 idiom）、`db/lifecycle_cleaners.py`/`lifecycle_scheduler.py`（逻辑层归档，互补非重叠）、`evals/db_metrics.py`（度量输出通道）、`scripts/full_cleanup.py:107`（离线 `vacuum_db` / `stat().st_size` 尺寸口径参考）
