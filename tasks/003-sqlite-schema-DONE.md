# Task 003: SQLite Schema — 交接报告

## 完成状态

- [x] 代码实现
- [x] 测试通过（26/26）
- [x] ruff 检查通过（0 errors）
- [x] 文档更新

---

## 改了哪些文件

### 新增文件（7 个）

| 文件 | 行数 | 说明 |
|------|------|------|
| `src/songyan/db/__init__.py` | 10 | 公共导出（get_db, init_schema, verify_schema） |
| `src/songyan/db/schema.sql` | 280 | 13 张表 DDL + 索引 + 外键约束 |
| `src/songyan/db/connection.py` | 60 | aiosqlite 异步连接 + PRAGMA 配置 |
| `src/songyan/db/migrations.py` | 80 | 幂等 schema 初始化 + 验证 |
| `tests/db/__init__.py` | 0 | 测试包标记 |
| `tests/db/test_schema.py` | 340 | 18 个测试（结构/约束/语义） |
| `tests/db/test_connection.py` | 120 | 8 个测试（路径/连接/集成） |

### 修改文件（2 个）

| 文件 | 变更 |
|------|------|
| `pyproject.toml` | 添加 `aiosqlite` 依赖 |
| `docs/STATUS.md` | 更新进度（Task 003 完成） |

---

## 如何验证

```bash
# 1. 运行全部测试
pytest tests/ -v
# Expected: 97 passed

# 2. 运行 DB 专项测试
pytest tests/db/ -v
# Expected: 26 passed

# 3. 代码风格
ruff check src/songyan/db/ tests/db/
# Expected: 0 errors

# 4. 命令行验证 schema
sqlite3 songyan.db < src/songyan/db/schema.sql
# Expected: 成功执行，无报错
```

---

## 关键设计决策

1. **JSON 字段存储**：所有 `list`/`dict` 字段存为 `TEXT`（DEFAULT `'[]'` / `'{}'`），由 Repository 层（Task 004）负责 `json.dumps/loads`。避免在 Schema 层引入复杂度。

2. **aiosqlite 而非 sqlite3**：遵循 CLAUDE.md "异步优先" 规则。连接管理使用 `@asynccontextmanager`，PRAGMA（foreign_keys=ON, journal_mode=WAL, synchronous=NORMAL）自动配置。

3. **幂等初始化**：所有 `CREATE TABLE` 带 `IF NOT EXISTS`，`init_schema()` 可多次调用不报错。配合 `verify_schema()` 用于健康检查。

4. **自引用外键**：`chapter_versions.parent_version_id` → `chapter_versions.version_id`，用于版本链追溯。ON DELETE SET NULL 避免级联删除整条链。

5. **character_states 为快照表**：schema 层面无 UPDATE 限制（SQLite 不支持），由 Repository 层（Task 004）通过 `INSERT` only API 保证。

---

## 已知问题 / 限制

- `get_db()` 使用全局 `settings.database_url`，测试中通过 monkeypatch 临时替换。后续如有并发测试冲突，可考虑注入 db_path 参数。
- `verify_schema()` 仅检查表名存在，不验证列结构。Schema 变更检测留给后续迭代。

---

## 下一步依赖

- **Task 004（Repository 层）**：基于本 Schema 实现所有 CRUD，负责 JSON 序列化/反序列化
- **Task 005（Genre Profile）**：projects.genre_id 外键关联
- **Task 006（CreativeMode Profile）**：projects.mode_id 外键关联
- **Task 007+（Agents）**：所有 Agent 通过 Repository 层读写数据
