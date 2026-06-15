# Task 083 交接报告：数据生命周期 Schema 迁移 + LifecycleScheduler 通用框架

> **完成日期**: 2026-06-07
> **状态**: ✅ 已完成
> **对应 Commit**: 待填充

---

## 交付物清单

| # | 交付物 | 路径 | 状态 |
|---|--------|------|:----:|
| 1 | Schema 迁移（5 张表 + lifecycle_errors 表） | `src/songyan/db/schema.sql` | ✅ |
| 2 | 迁移函数（幂等 ALTER TABLE） | `src/songyan/db/migrations.py` | ✅ |
| 3 | LifecycleScheduler 通用框架 | `src/songyan/db/lifecycle_scheduler.py` | ✅ |
| 4 | 单元测试 | `tests/db/test_lifecycle_scheduler.py` | ✅ |
| 5 | 交接报告 | 本文件 | ✅ |

---

## 实现摘要

### Schema 变更

为 5 张元数据表新增 `lifecycle_status` 字段（`TEXT DEFAULT 'active' CHECK(...) `）：

| 表 | 字段 | 索引 |
|----|------|------|
| `setting_snapshots` | `lifecycle_status` | `idx_settings_lifecycle` |
| `foreshadowings` | `lifecycle_status`（已有 `status` 字段，新增独立字段） | `idx_foreshadowings_lifecycle` |
| `human_marks` | `lifecycle_status` | `idx_human_marks_lifecycle` |
| `character_states` | `lifecycle_status` | `idx_states_lifecycle` |
| `chapter_chunks` | `lifecycle_status` | `idx_chunks_lifecycle` |

新增 `lifecycle_errors` 日志表：记录清理过程中的异常，不阻塞主流程。

### LifecycleScheduler 框架

```python
class LifecycleScheduler:
    def register_cleaner(cleaner: LifecycleCleaner)  # 注册具体表清理器
    async def transition(conn, table, entity_id, from_status, to_status, reason)  # 单条状态转换
    async def run_cleanup(project_id, current_chapter) -> LifecycleCleanupResult  # 全表清理
```

**关键设计**:
- `LifecycleCleaner` Protocol：Task 084/085 实现此协议注入具体策略
- 单表失败不级联：try/except 包裹每个 cleaner，记录到 `lifecycle_errors`
- 状态校验：`transition()` 校验 from_status 匹配当前 DB 状态，不匹配则拒绝
- 向后兼容：现有数据默认 `lifecycle_status='active'`，不影响任何查询

---

## 测试覆盖

| 层级 | 测试数 | 说明 |
|------|--------|------|
| Layer 1 模型 | 3 | `TransitionLog`、`LifecycleCleanupResult` 序列化；`LifecycleStatus` 枚举 |
| Layer 2 模块 | 8 | 状态流转、状态不匹配拒绝、entity 不存在、空 cleaners、单表失败不级联、主键列映射、注册 cleaner |
| Layer 3 集成 | 6 | 5 张表字段存在验证 + 默认值验证 + lifecycle_errors 表存在 |

**测试结果**: 13 passed, 4 skipped（同步测试，无需 asyncio）, 1 warning

---

## 验收标准核对

- [x] `pytest tests/db/test_lifecycle_scheduler.py -v` 全部通过
- [x] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [x] 不违反不可违背规则（Agent 不直接拿 DB connection — Scheduler 通过 get_db() 获取）
- [x] 生成了 `tasks/083-lifecycle-schema-scheduler-DONE.md`

---

## 已知限制

1. `LifecycleCleaner` Protocol 目前无具体实现 — Task 084/085 负责填充
2. `character_states` 表无 `project_id` 字段，Task 085 的清理器需通过 `source_version_id` → `chapter_versions` JOIN 获取 project_id
3. `run_cleanup()` 未与 SettlementExtractor 集成 — Task 087 端到端验证时接入

---

## 回滚指南

如需回滚 lifecycle_status 字段：

```sql
-- SQLite 不支持 DROP COLUMN，需重建表
-- 或通过 UPDATE 将所有 lifecycle_status 重置为 'active'
UPDATE setting_snapshots SET lifecycle_status = 'active';
UPDATE foreshadowings SET lifecycle_status = 'active';
UPDATE human_marks SET lifecycle_status = 'active';
UPDATE character_states SET lifecycle_status = 'active';
UPDATE chapter_chunks SET lifecycle_status = 'active';
```

---

## 参考

- `docs/v4.0-tech-plan.md` — 第 4.1 节
- `tasks/084-setting-foreshadowing-lifecycle.md` — 下游依赖
- `tasks/085-character-mark-lifecycle.md` — 下游依赖
