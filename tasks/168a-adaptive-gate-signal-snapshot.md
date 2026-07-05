# Task 168a: 自适应门禁信号快照模型

> **Phase**: V7 阶段 Y（enforce 可生产化）
> **优先级**: P0
> **状态**: ✅ 完成
> **父任务**: `tasks/168-adaptive-gate-data-plane.md`
> **依赖**: Task 167 DONE；Task 145-148 / 164 / 165p 度量事实源

---

## Goal

定义自适应门禁的数据契约，把单章或审计点级别的 gate 输入信号统一持久化到 SQLite。168a 只做“事实快照”，不做窗口聚合，不做 halt 判定。

## 背景

当前 gate 相关输入分散在多处：

- `continuity_reports` 保存 health、orphan、forgotten、state mismatch。
- `setting_tracking` 可派生 T7 新 critical 速率。
- `ChapterRunLog` / `run_quality_debt` 保存 quality debt、QG、degraded、convergence。
- `literary_observations` 保存文学四维度。
- `text_cleanliness_metrics` 保存 T9 文本洁净度。
- `run_db_metrics` 保存 T5 DB/scan telemetry。
- `foreshadowing_schedule_items` 保存 Task 167 调度生命周期。

如果 Task 169 直接临时读取这些来源，会把数据读取、缺失样本处理、窗口趋势和 halt 判定耦合在一起。168a 的目标是先建立一层稳定、可复算的事实快照。

## 数据模型建议

### `AdaptiveGateSignalSnapshot`

最小字段：

| 字段 | 说明 |
|------|------|
| `snapshot_id` | 快照 ID |
| `project_id` | 项目 ID |
| `run_id` | 可选 run ID；历史 DB 复算可为空 |
| `chapter_number` | 章节号 |
| `source_status` | 各来源状态：present/missing/insufficient/observation |
| `continuity` | continuity/orphan/health 信号 |
| `quality` | QG/quality debt/run 信号 |
| `literary` | 文学四维度与 conceptual grounding |
| `cleanliness` | T9 文本洁净度 |
| `context` | context emergency / budget / T5 telemetry |
| `narrative` | Task 167 schedule lifecycle / long-range foreshadowing 信号 |
| `created_at` / `updated_at` | 快照时间 |

建议 JSON 字段保持结构化，但模型必须给出 typed view，避免调用方直接拼 dict。

### Source status

来源状态建议使用：

| 状态 | 含义 |
|------|------|
| `present` | 来源充分，可用于后续窗口聚合 |
| `missing` | 来源不存在，例如历史 DB 无该表或该章未生成 |
| `insufficient` | 来源存在但样本不足，不可用于判定 |
| `observation` | 可展示但不进入硬判定，例如 T9 timeline report-only |

## In Scope

- [x] 新增模型文件：
  - `src/songyan/models/adaptive_gate.py`
- [x] 在 `models/__init__.py` 导出新模型。
- [x] 新增 SQLite 表：
  - `adaptive_gate_signal_snapshots`
- [x] 表约束：
  - `snapshot_id` 主键。
  - `(project_id, run_id, chapter_number)` 唯一；`run_id` 为空时需有可重复 upsert 的稳定 key。
  - JSON 字段默认 `{}`，不能为 `NULL`。
- [x] 新增 repository：
  - `AdaptiveGateSignalRepository.upsert(snapshot)`
  - `get(project_id, chapter_number, run_id=None)`
  - `list_range(project_id, start, end, run_id=None)`
  - `delete_range(project_id, start, end, run_id=None)`
- [x] 实现单章 snapshot builder：
  - 从已有 repository/collector 接收已查询结果。
  - 不直接调用 LLM。
  - 不从 LangGraph state 取正文。
- [x] 缺失来源必须写入 `source_status`，不抛异常中断复算。

## Out of Scope

- 不做滑窗趋势。
- 不做 spike factor / anomaly factor。
- 不写 `GateConfig`。
- 不修改 `_gates.py`。
- 不接入 phase2_graph 主循环。
- 不新增 workflow 节点。
- 不启动真实长跑。

## 数据来源映射

| Snapshot 域 | 来源 | 备注 |
|-------------|------|------|
| `continuity` | `ContinuityReportRepository` / `collect_orphan_metrics` | 复用 Task 145 口径，不用 `classify_report` 污染 orphan 计数 |
| `quality` | `ChapterRunLog` / `run_quality_debt` | run JSONL 可作为刷新输入，但快照应落 SQLite |
| `literary` | `LiteraryObservationRepository.list_scores_by_chapter_range` | 每章取最新 observation，沿用 Task 147 |
| `cleanliness` | `TextCleanlinessMetricRepository` / Task 164 collector | timeline 默认 observation |
| `context` | run log context metrics / `run_db_metrics` | T5 只入信号，不在 168a 判红线 |
| `narrative` | `ForeshadowingScheduleRepository` / `ForeshadowingRepository` | 记录 active/injected/satisfied/missed/cancelled 计数 |

## 测试要求

目标测试建议：

```powershell
python -m pytest tests/test_168a_adaptive_gate_signal_snapshot.py -q
```

必要覆盖：

- [x] schema migration 创建表和索引。
- [x] Pydantic 模型默认值完整。
- [x] upsert 幂等。
- [x] `list_range` 按章节排序。
- [x] `delete_range` 只删除指定项目/范围/run。
- [x] 缺失 continuity / literary / schedule 来源时写 `missing`，不报错。
- [x] JSON 字段 round-trip 后类型不丢失。
- [x] 不触碰 `_gates.py` 和 workflow 行为。

## 验收标准

- [x] `adaptive_gate_signal_snapshots` 可被迁移创建。
- [x] 快照可写入、覆盖、回读、按范围复算。
- [x] 所有来源状态显式可查。
- [x] 168b 可以只依赖 repository range 读取，不再直接拼多张表。
- [x] 生成 `tasks/168a-adaptive-gate-signal-snapshot-DONE.md`。

## 风险与约束

- `run_id` 为空的历史复算需要稳定唯一键，不能让同一项目/章节重复膨胀。
- run JSONL 不是长期事实源；168a 可以读它刷新 SQLite，但 169 不应直接依赖 JSONL。
- timeline conflict、T5 latency observation、小基数 T6c 这类信号必须保留 observation/insufficient 语义，防止被 169 误用。
