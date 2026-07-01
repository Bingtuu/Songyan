# Task 003: SQLite Schema

> **Phase**: Phase 1
> **优先级**: P0
> **依赖**: Task 002（Pydantic 数据模型）
> **预计工作量**: 中

---

## Goal

创建 SQLite schema 和数据库连接层，为 Task 004 Repository 层提供底层支持。

## Context

Task 002 已完成 35 个 Pydantic 模型。本 Task 将这些模型映射为 13 张 SQLite 表，建立外键约束、唯一约束和索引，确保数据完整性。

## In Scope（必须完成）

- [ ] `src/songyan/db/schema.sql` — 13 张表的完整 DDL
  - creative_briefs 表 ⭐
  - literary_observations 表 ⭐
  - chapter_versions UNIQUE(project_id, chapter_number, version_number) ⭐
  - review_reports 增加 audit_type + rule_audit_result + llm_audit_result ⭐
  - character_states 快照表注释 ⭐
  - setting_snapshots 增加 setting_key ⭐
  - foreshadowings 增加 source_version_id ⭐
- [ ] `src/songyan/db/connection.py` — aiosqlite 异步连接 + PRAGMA 配置
- [ ] `src/songyan/db/migrations.py` — 幂等 schema 初始化 + 验证
- [ ] `pyproject.toml` — 添加 aiosqlite 依赖
- [ ] `tests/db/test_schema.py` — 表存在、约束生效、外键生效、V2 新增字段
- [ ] `tests/db/test_connection.py` — 连接管理、PRAGMA 配置、路径解析

## Out of Scope（明确不做）

- Repository 层 CRUD（Task 004）
- 业务逻辑 / Agent 代码
- 数据迁移工具（v1→v2 schema upgrade）

## 接口契约

```python
# 异步连接上下文管理器
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """提供已配置 PRAGMA 的数据库连接."""
    ...

# Schema 初始化（幂等）
async def init_schema(db_path: str | Path | None = None) -> None:
    """读取 schema.sql 并执行."""
    ...

# Schema 验证
async def verify_schema(conn: aiosqlite.Connection) -> list[str]:
    """返回缺失的表名列表."""
    ...
```

## 测试要求

### Layer 1: Schema 结构测试
- [ ] 13 张表全部创建
- [ ] 初始化幂等（多次执行不报错）
- [ ] WAL 模式启用
- [ ] 外键启用

### Layer 2: 约束测试
- [ ] chapter_versions 唯一约束生效
- [ ] 外键级联删除生效
- [ ] 外键违反抛 IntegrityError
- [ ] 自引用外键（parent_version_id）生效

### Layer 3: 业务语义测试
- [ ] character_states 可多次 INSERT（快照行为）
- [ ] creative_briefs JSON 字段可存储
- [ ] literary_observations 可关联 chapter_versions
- [ ] review_reports audit 字段可存储
- [ ] foreshadowings source_version_id 可存储
- [ ] setting_snapshots setting_key 可存储

## 验收标准

- [ ] `pytest tests/db/ -v` 全部通过
- [ ] `sqlite3 songyan.db < src/songyan/db/schema.sql` 成功执行
- [ ] 13 张表全部创建，无语法错误
- [ ] 唯一约束生效（chapter_versions）
- [ ] 外键约束生效
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行）
- [ ] 更新了 docs/STATUS.md
- [ ] 生成了 tasks/003-sqlite-schema-DONE.md 交接文件

## 参考文档

- `docs/architecture/04-vibe-coding-engineering.md` — Task 003 规格
- `system_prompt/development-tech-plan-v2.md` — 技术方案
- `tasks/002-data-models-DONE.md` — 上游任务交接（35 个模型字段参考）
