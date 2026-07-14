# Pass 15: 数据层与 Schema 审计报告

> **审计日期**: 2026-07-13
> **项目基线**: V7 Task 171w 完成后
> **审查范围**: `src/songyan/db/schema.sql`, `migrations.py`, `connection.py`, `repository.py`, `review_repo.py`, `settlement_repo.py`, `literary_repo.py`, `text_cleanliness_repo.py`, `run_quality_debt_repo.py`, `foreshadowing_schedule_repo.py`, `adaptive_gate_repo.py`, `adaptive_halt_repo.py`, `src/songyan/models/settlement.py`, `review.py`

---

## 执行摘要

数据层在功能测试层面健康（`tests/db` 140 passed），ruff 通过，未发现 SQL 注入漏洞。但存在 **2 个 P0 级风险**：`connection.py` 在 WAL 模式下删除 `-wal`/`-shm` 文件可能损坏数据库；`repository.py` 直接 `UPDATE chapter_versions` 违反版本不可变原则。此外 schema 编号混乱、约束缺失、`formula` 未持久化等 P1 债务需在继续推进前清偿。

| 级别 | 数量 | 关键问题 |
|---|---|---|
| P0 | 2 | WAL 文件删除风险；chapter_versions 原地 UPDATE |
| P1 | 9 | schema 编号混乱、migrations 过大、约束缺失、formula 未持久化等 |
| P2 | 7 | 冗余索引、注释过时、递归深度限制等 |

---

## P0 级问题

### P0-1 `connection.py` 在打开连接时删除 WAL/SHM 文件，存在数据损坏风险

- **文件路径**: `src/songyan/db/connection.py:60-69`
- **代码片段**:
  ```python
  async with aiosqlite.connect(db_path) as conn:
      await conn.execute("PRAGMA foreign_keys = ON")
      await conn.execute("PRAGMA journal_mode = WAL")
      ...
      try:
          db_path = get_db_path()
          wal_path = db_path.with_suffix(db_path.suffix + "-wal")
          shm_path = db_path.with_suffix(db_path.suffix + "-shm")
          if wal_path.exists():
              wal_path.unlink()
          if shm_path.exists():
              shm_path.unlink()
      except OSError:
          pass
  ```
- **问题描述**: 在 WAL 模式且连接已打开的情况下，无条件删除 `-wal` / `-shm` 文件。只要存在未 checkpoint 的事务，删除 WAL 即等同于截断数据库，会导致已提交但未合并的数据丢失，甚至数据库损坏。
- **潜在影响**: 系统启动或首次连接时可能静默丢失最近写入的章节版本、Settlement、审查报告等；并发连接时风险更高。
- **修复建议**:
  1. 删除该段“清理残留 WAL/SHM”的逻辑；WAL 文件应由 SQLite 自身在 checkpoint 后回收。
  2. 若确实需要处理崩溃残留，应在**关闭所有连接后**、以 `PRAGMA journal_mode = DELETE` 或备份恢复的方式处理，而不是在活跃连接内 `unlink()`。

### P0-2 `ChapterVersionRepository` 直接 `UPDATE chapter_versions`，违反版本不可覆盖原则

- **文件路径**: `src/songyan/db/repository.py:491-497`, `:505-528`, `:544-559`
- **代码片段**:
  ```python
  async def mark_abandoned(self, version_id: str) -> None:
      async with get_db() as conn:
          await conn.execute(
              "UPDATE chapter_versions SET is_abandoned = 1 WHERE version_id = ?",
              (version_id,),
          )
          await conn.commit()

  async def accept_version(self, version_id: str, ...) -> None:
      ...
      await c.execute(
          "UPDATE chapter_versions SET version_type = 'accepted' WHERE version_id = ?",
          (version_id,),
      )

  async def update_score_card(self, version_id: str, score_card: dict[str, Any]) -> None:
      ...
      await conn.execute(
          "UPDATE chapter_versions SET score_card = ? WHERE version_id = ?",
          ...
      )
  ```
- **问题描述**: AGENTS.md 明确规定“每次生成/修订必须创建 `chapter_versions` 新记录，禁止覆盖”，schema 注释也写明“永远 INSERT，禁止 UPDATE”。但 repository 对同一 `version_id` 直接修改 `is_abandoned`、`version_type`、`score_card`。
- **潜在影响**: 版本链不可追溯；`accept` 后原 `draft` 版本被覆盖，无法回滚或审计；评分卡追加历史丢失。
- **修复建议**:
  - `accept_version`：应保持旧版本不变，新增一条 `version_type='accepted'` 的新版本，并更新 `chapter_heads.accepted_version_id`。
  - `mark_abandoned`：同样应新增标记版本，或仅在 `chapter_heads` 层做逻辑废弃。
  - `update_score_card`：若评分在 accept 后补充，应新增 `version_type='accepted'` 的 patch 版本，而不是原地更新。
  - 在过渡方案中，如必须原地更新，需在 AGENTS.md / schema 注释中显式例外说明。

---

## P1 级问题

### P1-1 `schema.sql` 表编号混乱、重复、颠倒、缺失

- **文件**: `src/songyan/db/schema.sql`
- **问题示例**:
  - `4.` creative_briefs
  - `4.5` setting_tracking
  - `4.6` inventory_tracker
  - `4.7` location_tracker
  - `4.8` continuity_reports
  - `4.5` human_instructions（与 setting_tracking 重复编号）
  - `14.` project_runs（跳号，且排在 13 之前）
  - `13.` summaries
  - `19.` chapter_chunks → `23.` run_db_metrics（跳号 20-22）
- **修复建议**: 一次性重排为连续整数，去掉小数编号；同步更新 `docs/` 中引用表编号的手册。

### P1-2 `migrations.py` 超过 1000 行且职责单一，可维护性差

- **文件**: `src/songyan/db/migrations.py`（1019 行）
- **问题**: 所有迁移函数集中在一个文件，V4/V6/V7 各阶段混在一起；`init_schema` 与 `run_migrations` 分别维护两份几乎相同的调用列表，容易遗漏。
- **修复建议**: 按版本拆分为 `migrations/v6/`, `migrations/v7/` 等子模块；引入 `schema_migrations` 元数据表记录已执行迁移版本。

### P1-3 `lifecycle_errors` 表在 `schema.sql` 中缺失，仅在 migration 中创建

- **文件**: `src/songyan/db/schema.sql`, `src/songyan/db/migrations.py:424-434`
- **问题**: `_EXPECTED_TABLES` 包含 `"lifecycle_errors"`，但 `schema.sql` 没有该表定义。
- **修复建议**: 把 `lifecycle_errors` 的 `CREATE TABLE` 补到 `schema.sql` 中，migration 中保留 `CREATE TABLE IF NOT EXISTS`。

### P1-4 `setting_snapshots.setting_key` 仅建索引、未加唯一约束

- **文件**: `src/songyan/db/schema.sql:328-334`
- **问题**: AGENTS.md 要求“`new_setting.setting_key` 必须唯一”，但 schema 仅提供非唯一索引。
- **修复建议**: 将索引改为唯一索引；若允许同一 key 多版本，需通过 `lifecycle_status='active'` 过滤保证业务唯一性并文档化。

### P1-5 `foreshadowings.source_version_id` 允许 NULL，违反“必须记录 source_version_id”规则

- **文件**: `src/songyan/db/schema.sql:311`
- **代码**: `source_version_id TEXT REFERENCES chapter_versions(version_id) ON DELETE SET NULL`
- **问题**: 列可空，且外键 `ON DELETE SET NULL` 会在版本删除时将其置空。
- **修复建议**: 改为 `TEXT NOT NULL`，删除 `ON DELETE SET NULL`（改为 `RESTRICT` 或 `CASCADE`）。

### P1-6 `numerical_ledgers` 未持久化 `formula`，无法校验 `closing_value`

- **文件**: `src/songyan/db/schema.sql:340-351`, `src/songyan/db/settlement_repo.py:759-801`, `src/songyan/models/settlement.py:74-84`
- **问题**: 模型 `NumericalUpdate` 含 `formula: str`，但 schema 没有对应列；`NumericalLedgerRepository.create` 不写入 `formula`。
- **修复建议**: 在 `numerical_ledgers` 增加 `formula TEXT` 列，repository 持久化 `update.formula`；并加入 `closing_value` 与公式重算校验。

### P1-7 连续性追踪表缺少外键约束

- **文件**: `src/songyan/db/schema.sql:101-181`
- **问题**: `setting_tracking`、`inventory_tracker`、`location_tracker`、`continuity_reports`、`human_instructions` 都声明 `project_id TEXT NOT NULL` 但都没有 `REFERENCES projects(project_id) ON DELETE CASCADE`。
- **修复建议**: 为这些表补全外键约束；若存在历史脏数据，先清理再上线。

### P1-8 `NewSetting.chapter_number` 模型字段与 schema 不匹配，repository 伪造序号

- **文件**: `src/songyan/db/schema.sql:322-331`, `src/songyan/db/settlement_repo.py:383-406`, `src/songyan/models/settlement.py:38-46`
- **代码**: `chapter_number=i + 1  # 1-indexed ordinal`
- **问题**: `NewSetting` 模型有 `chapter_number`，但 `setting_snapshots` 表没有该列。`list_by_project` 用结果集顺序伪造章节号，不可靠。
- **修复建议**: 在 `setting_snapshots` 增加 `introduced_in_chapter` 列并正确回填；或从 `NewSetting` 模型中删除 `chapter_number`。

### P1-9 `character_update.old_value` 一致性无数据库层保障

- **文件**: `src/songyan/models/settlement.py:10-18`, `src/songyan/db/repository.py`
- **问题**: AGENTS.md 要求“`character_update.old_value` 必须与 DB 当前值一致”，但没有任何约束或校验代码。
- **修复建议**: 在 SettlementExtractor 或 `CharacterRepository.add_state_snapshot` 写入前，读取该 `character_id` + `field` 的最新 `value` 并与 `old_value` 比对，不一致则报错或标记 `needs_human_review`。

---

## P2 级问题

### P2-1 `text_cleanliness_metrics` 主键列上的索引冗余

- **文件**: `src/songyan/db/schema.sql:512-515`
- **问题**: 主键 `(project_id, chapter_number)` 已自动建索引，额外再建同名索引冗余。
- **修复建议**: 删除 `idx_text_cleanliness_project_chapter`。

### P2-2 `connection.py` 未真正检查 `PRAGMA quick_check` 结果

- **文件**: `src/songyan/db/connection.py:52-57`
- **问题**: 只捕获异常，没有 `fetchone()` 检查返回结果是否为 `"ok"`。
- **修复建议**: 获取结果并判断，非 ok 则报错。

### P2-3 `setting_snapshots.source_quote` 允许空字符串

- **文件**: `src/songyan/db/schema.sql:327`
- **问题**: `source_quote TEXT DEFAULT ''`，未限制非空。
- **修复建议**: 改为 `source_quote TEXT NOT NULL`，并在写入前校验引用是否存在于正文。

### P2-4 `run_quality_debt.project_id`、`run_db_metrics.run_id` 无外键

- **文件**: `src/songyan/db/schema.sql:484-498`, `:359-374`
- **问题**: `run_quality_debt.project_id`、`run_db_metrics.run_id` 无外键。
- **修复建议**: 补全 `REFERENCES`。

### P2-5 `schema.sql` 头部注释与实际情况不符

- **文件**: `src/songyan/db/schema.sql:1-2`
- **问题**: 注释仍写“V1.0 / 13 tables”，实际已有 28 个编号段、超过 30 张表。
- **修复建议**: 更新为当前版本号与表数量统计。

### P2-6 `ChapterVersionRepository.get_chain` 递归 CTE 无深度限制

- **文件**: `src/songyan/db/repository.py:561-576`
- **问题**: 未设置 `MAXRECURSION` 或循环检测；若 `parent_version_id` 链成环会无限递归。
- **修复建议**: 增加 `LIMIT` 或递归深度上限；写入时校验不能指向自身/后代。

### P2-7 `migrations.py` 异常处理过于宽泛

- **文件**: `src/songyan/db/migrations.py`
- **问题**: `except Exception` 捕获所有异常。
- **修复建议**: 收窄为具体数据库/操作异常。

---

## 正面发现

- `character_states` 的 INSERT-only 原则总体得到遵守：`repository.py:293-331` 仅做 INSERT；`context_repo.py` 中的几次 `UPDATE character_states` 均只修改 `lifecycle_status`，符合 AGENTS.md 例外条款。
- `review_repo.py`、`settlement_repo.py` 中的动态 `IN (...)` 查询均使用 `?` 占位符拼接，未发现 SQL 注入漏洞。
- 主要核心表（`projects`、`characters`、`chapter_versions`、`chapter_heads`、`foreshadowings` 等）均配置了 `ON DELETE CASCADE`，级联清理基本到位。
- `ContextSnapshotRepository` 与 schema 的 `context_emergency_level`、`budget_used_before_emergency` 字段保持一致。

---

## 验证结果

```powershell
# DB 测试
python -m pytest tests/db -q
# 140 passed, 39.74s

# ruff
ruff check src/ tests/
# All checks passed
```

---

## 修复优先级

1. **P0-1**: 删除 `connection.py` 中删除 WAL/SHM 的逻辑。
2. **P0-2**: 停止原地 UPDATE `chapter_versions`；改为 INSERT 新版本。
3. **P1-1 / P1-2**: 整理 schema 编号，拆分 migrations。
4. **P1-4 / P1-5 / P1-6**: 补全 setting_key 唯一性、source_version_id 非空、formula 持久化。
5. **P1-7 / P1-8 / P1-9**: 补全外键、修正 chapter_number 来源、校验 old_value。
6. **P2**: 清理冗余索引、过期注释、递归深度限制等。
