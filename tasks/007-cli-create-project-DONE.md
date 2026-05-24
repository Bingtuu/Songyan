# Task 007: CLI 创建项目 — 交接报告

## 完成状态

- [x] 代码实现
- [x] 测试通过：6/6（CLI 专项）+ 202/202（全量）
- [x] ruff 检查通过：0 errors
- [x] 文档更新

---

## 改了哪些文件

### 修改文件（2 个）

| 文件 | 变更 |
|------|------|
| `src/songyan/cli/main.py` | 新增 `create-project`（8 步交互向导）和 `list-projects` 命令 |
| `docs/STATUS.md` | 更新 Task 007 完成状态 |

### 新增文件（2 个）

| 文件 | 说明 |
|------|------|
| `tests/cli/__init__.py` | 测试包标识 |
| `tests/cli/test_cli.py` | 6 个测试：命令注册、create-project 交互 + DB 验证、list-projects |

---

## 如何验证

```bash
pytest tests/cli/ -v
# Expected: 6 passed

pytest tests/ -v
# Expected: 202 passed

ruff check src/songyan/cli/ tests/cli/
# Expected: All checks passed

songyan create-project --help
songyan list-projects --help
```

---

## 关键实现决策

1. **8 步交互向导**：使用 Click 的 `click.prompt()` 实现，支持默认值和类型校验。
2. **动态加载选项**：创作模式列表从 `list_creative_mode_profiles()` 加载，题材列表从 `list_genre_profiles()` 加载，不硬编码。
3. **异步 Repository 的同步调用**：`ProjectRepository.create()` 是 async 方法，CLI 命令通过 `asyncio.run(_create_project_async())` 包装。测试中保持同步，避免 pytest-asyncio 事件循环冲突。
4. **Schema 自动初始化**：`create-project` 和 `list-projects` 命令内部自动调用 `init_schema()`，用户无需手动初始化数据库。
5. **project_id 生成**：使用 `uuid.uuid4().hex` 生成 32 位十六进制唯一 ID。
6. **测试数据库隔离**：测试中通过 monkeypatch `songyan.db.connection.settings` 指向临时数据库文件，确保 CLI 测试不污染开发数据库。
7. **DB 验证使用同步 sqlite3**：测试中直接使用标准库 `sqlite3` 连接临时数据库验证持久化结果，避免在测试中再次触发 asyncio。
8. **单文件 136 行**：CLI 逻辑集中在 `main.py`，未超过 400 行限制。

---

## 已知限制

- CLI 命令目前只有 `create-project` 和 `list-projects`，缺少 `edit-project`、`delete-project` 等管理命令（后续 Task 如需可扩展）。
- `create-project` 未实现 AI 实时建议（调用 LLM），当前为纯表单式交互。
- 交互向导不支持中断恢复，用户需一次性完成所有步骤。

---

## 下一步依赖

- **Task 008（GoalPlanner Agent）** 可通过 CLI 创建的项目 `project_id` 加载项目设定，开始章节目标制定。
- **Task 009（CreativeDirector Agent）** 可读取项目的 `mode_id` 加载 `CreativeModeProfile`，决定创作约束。
- **Task 010（ContextPackage 组装）** 可通过 `ProjectRepository.get(project_id)` 获取项目完整设定。
- **Task 011+（Agent 层）** 均依赖 CLI 创建的项目作为工作流入口。
