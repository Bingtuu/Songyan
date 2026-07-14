# Pass 3: 数据事实源与 Schema 审计报告

## 执行摘要

- 发现总数: 4
- P0: 0, P1: 2, P2: 2
- 关键结论: SQLite 事实源核心契约（版本不可覆盖、INSERT-only character_states、事务化 accept）均得到遵守；V7 新表索引覆盖良好。主要问题是 `schema.sql` 表编号混乱（重复/跳跃/顺序颠倒）和 `migrations.py` 已膨胀到 971 行，长期维护风险高。

## 检查项与发现

### 3.1 `schema.sql` 表编号整理

- **级别**: P1
- **文件**: `src/songyan/db/schema.sql`
- **方法**: `grep -nE '^\s*--\s*[0-9]+\.' src/songyan/db/schema.sql`
- **结果**:

| 编号 | 表名 | 行号 | 问题 |
|------|------|------|------|
| 1 | projects | 8 | — |
| 2 | characters | 35 | — |
| 3 | chapter_goals | 53 | — |
| 4 | creative_briefs | 72 | — |
| 4.5 | setting_tracking | 95 | ⚠️ 与 4.5 human_instructions 重复编号 |
| 4.6 | inventory_tracker | 119 | — |
| 4.7 | location_tracker | 135 | — |
| 4.8 | continuity_reports | 148 | — |
| 4.5 | human_instructions | 164 | ❌ 与 setting_tracking 重复编号 |
| 5 | chapter_versions | 178 | — |
| 5.5 | context_snapshots | 203 | — |
| 6 | chapter_heads | 223 | — |
| 7 | character_states | 237 | — |
| 8 | literary_observations | 254 | — |
| 9 | review_reports | 273 | — |
| 10 | foreshadowings | 295 | — |
| 11 | setting_snapshots | 314 | — |
| 12 | numerical_ledgers | 332 | — |
| 14 | project_runs | 351 | ❌ 13 缺失（或顺序颠倒） |
| 13 | summaries | 371 | ❌ 应在 14 之前 |
| 15 | arc_summaries | 388 | — |
| 16 | volume_summaries | 406 | — |
| 17 | permanent_scenes | 422 | — |
| 18 | human_marks | 438 | — |
| 19 | chapter_chunks | 458 | — |
| 23 | run_db_metrics | 476 | ❌ 20-22 缺失，跳跃 |
| 24 | text_cleanliness_metrics | 495 | — |
| 25 | replan_proposals / replan_actions / planning_constraints | 512 | — |
| 26 | foreshadowing_schedule_* | 578 | — |
| 27 | adaptive_gate_signal_snapshots | 633 | — |
| 28 | adaptive_halt_decisions | 655 | — |

- **问题描述**: 
  1. 编号 `4.5` 被 `setting_tracking` 和 `human_instructions` 重复使用。
  2. `project_runs` 标为 `14`，`summaries` 标为 `13`，顺序颠倒。
  3. `chapter_chunks`（19）之后直接跳到 `run_db_metrics`（23），缺少 20-22。
- **潜在影响**: 新开发者容易误解表依赖顺序；维护 `migrations.py` 时难以快速定位对应 schema 段落。
- **修复建议**: 重新编号为连续整数；或改用“阶段.序号”格式（如 `V5-1`、`V6-1`、`V7-1`）以区分版本。

### 3.2 表与模型一致性检查

- **级别**: P2
- **方法**: 抽样核对 `chapter_versions`, `character_states`, `replan_proposals`, `adaptive_halt_decisions` 等关键表与 `src/songyan/models/` 中对应模型
- **结果**: 
  - `chapter_versions` 字段与 `ChapterVersion` 模型一致（含 `version_id`, `version_number`, `version_type`, `is_abandoned`, `content`, `word_count`, `scenes`, `generation_metadata`, `score_card`, `creative_brief_id`, `parent_version_id`）。
  - `character_states` 与 `CharacterState` 模型一致，含 `lifecycle_status` 字段。
  - V7 新表 `replan_proposals`, `replan_actions`, `planning_constraints`, `foreshadowing_schedule_plans`, `foreshadowing_schedule_items`, `adaptive_gate_signal_snapshots`, `adaptive_halt_decisions` 均有对应 Pydantic 模型。
- **结论**: 未抽样发现字段名/类型明显不一致。建议作为持续维护项，在每次 schema 变更时增加自动化校验脚本。

### 3.3 `migrations.py` 复杂度评估

- **级别**: P1
- **文件**: `src/songyan/db/migrations.py`
- **方法**: 统计迁移函数数量与规模
- **结果**:
  - 文件共 971 行。
  - 包含 35+ 个 `_migrate_*` 函数，从 `_migrate_continuity_tables` 到 `_migrate_adaptive_halt_decisions`。
  - 每个迁移函数内联 CREATE TABLE / ALTER TABLE，无独立 SQL 文件。
- **问题描述**: 历史 ALTER 全部内联在 Python 中，schema 演进历史与 `schema.sql` 分离，长期维护困难；新增迁移需要同时改 `schema.sql` 和 `migrations.py`。
- **修复建议**: 
  - 短期：将迁移函数按版本拆分为 `db/migrations/*.py`，`migrations.py` 仅保留调度器。
  - 长期：引入版本化迁移文件（如 `db/migrations/001_initial.sql`, `db/migrations/002_add_score_card.sql`），与 `schema.sql` 同源生成。

### 3.4 Repository 接口一致性与事务使用

- **级别**: 通过
- **文件**: `src/songyan/db/repository.py`, `src/songyan/workflows/_nodes.py`
- **方法**: 
  - 检查 `Repository.create/accept_version/update/update_head` 等方法是否接受可选 `conn` 参数以支持事务。
  - 检查 `accept_with_settlement_boundary` 是否在同一事务内完成 settlement apply + accept + head update。
- **结果**:
  - `accept_with_settlement_boundary`（`_nodes.py:2183-2220`）使用 `async with get_db() as conn:` 显式事务，依次调用 `apply_settlement`、`accept_version`、`ChapterHeadRepository().update`，最后 `commit`/`rollback`。
  - `ChapterHeadRepository.update`（`repository.py:690-728`）使用 `INSERT ... ON CONFLICT DO UPDATE`，符合“head 指针可变、版本内容不可变”的语义。
  - `ContextSnapshotRepository.create`（`repository.py:582-621`）支持传入 `conn` 参与外部事务。
- **结论**: 关键写入路径使用事务，事实源一致性得到保障。

### 3.5 V7 新表索引检查

- **级别**: 通过
- **方法**: `grep -nE 'CREATE INDEX' src/songyan/db/schema.sql | grep -E 'replan|foreshadowing|adaptive'`
- **结果**:
  - `replan_proposals`: `(project_id, created_at)`, `(project_id, status)`
  - `replan_actions`: `(proposal_id, action_order)`, `(project_id)`
  - `planning_constraints`: `(project_id, status)`, `(source_proposal_id)`
  - `foreshadowing_schedule_plans`: `(project_id, target_chapter)`, `(project_id, status)`
  - `foreshadowing_schedule_items`: `(plan_id, item_order)`, `(project_id, source_type, source_id, target_chapter)`, `(project_id, status)`
  - `adaptive_gate_signal_snapshots`: `(project_id, run_id, chapter_number)`
  - `adaptive_halt_decisions`: `(project_id, run_id, evaluated_at_chapter)`, `(project_id, status)`
- **结论**: V7 新表均按查询模式建立了合理索引。

### 3.6 `chapter_heads` 指针更新语义

- **级别**: 通过
- **文件**: `src/songyan/db/repository.py:690-728`
- **结果**: `ChapterHeadRepository.update` 使用 `INSERT ... ON CONFLICT(project_id, chapter_number) DO UPDATE SET ...`，本质是 upsert。
- **结论**: head 指针可变符合设计；版本链本身（`chapter_versions`）未被覆盖。

## 通过项

- [x] 关键写入路径（settlement apply + accept + head update）在同一事务内完成。
- [x] `chapter_versions` 内容字段未被 UPDATE 覆盖（与 Pass 1 一致）。
- [x] V7 新表索引覆盖合理。
- [x] Repository 方法普遍支持可选 `conn` 参数以参与事务。

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 3.1 | P1 | `schema.sql` 表编号重复/跳跃/顺序颠倒 | `src/songyan/db/schema.sql` | 重新执行 `grep -nE '^\s*--\s*[0-9]+\.'` 检查连续性 |
| 3.3 | P1 | `migrations.py` 971 行，历史 ALTER 内联 | 拆分为 `src/songyan/db/migrations/*.py` 或独立 SQL 文件 | `pytest tests/db/ -q` |
| 3.2 | P2 | 表与模型一致性缺少自动化校验 | 新增 `tests/db/test_schema_model_consistency.py` | `pytest tests/db/test_schema_model_consistency.py -q` |
| 3.6 | P2 | `chapter_heads` 使用 upsert 而非显式 INSERT/UPDATE，语义对新手不够直观 | 保留 upsert，但文档/注释中明确说明 head 指针可变的合理性 | 文档更新，无需测试 |

---

> 下一 Pass: [Pass 4 工作流与 LangGraph 状态机审计](pass4-workflow-report.md)
