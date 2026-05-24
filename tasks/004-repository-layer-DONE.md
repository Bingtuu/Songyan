# Task 004: Repository 层 — 交接报告

## 完成状态

- [x] 代码实现
- [x] DB 测试通过：51/51
- [x] ruff 检查通过：0 errors
- [x] 文档更新

---

## 改了哪些文件

### 新增文件（4 个）

| 文件 | 说明 |
|------|------|
| `src/songyan/db/repository.py` | 核心 Repository：Project、Character、ChapterGoal、ChapterVersion、ChapterHead |
| `src/songyan/db/review_repo.py` | 审查 Repository：CreativeBrief、ReviewReport、LiteraryObservation |
| `src/songyan/db/settlement_repo.py` | 结算 Repository：Foreshadowing、SettingSnapshot、NumericalLedger |
| `tests/db/test_review_settlement_repository.py` | 审查与结算 Repository 测试 |

### 修改文件（4 个）

| 文件 | 变更 |
|------|------|
| `src/songyan/db/__init__.py` | 导出 Repository 公共接口 |
| `tests/db/test_repository.py` | 新增核心 Repository 测试 |
| `tests/db/test_connection.py` | ruff 自动整理导入空行 |
| `docs/STATUS.md` | 更新 Task 004 完成状态 |

---

## 如何验证

```bash
pytest tests/db/ -v
# Expected: 51 passed

ruff check src/songyan/db/ tests/db/
# Expected: All checks passed
```

---

## 关键实现决策

1. **JSON 序列化在 Repository 层完成**：`list` / `dict` / 嵌套 Pydantic 模型统一转 JSON TEXT，读取时恢复为模型字段。
2. **ID 由调用方生成**：模型中缺少主键的表通过 Repository 方法参数接收 ID，例如 `report_id`、`setting_id`、`ledger_id`。
3. **`character_states` INSERT only**：仅提供 `CharacterRepository.add_state_snapshot()`，没有 UPDATE 方法。
4. **版本链保持不可覆盖语义**：`ChapterVersionRepository` 只提供 `create/get/list/get_chain`，不提供 UPDATE。
5. **外键错误自然透传**：不捕获 `aiosqlite.IntegrityError`，测试覆盖了违反 FK 的路径。
6. **单文件行数限制**：Repository 文件分别为 384、220、194 行，均低于 400 行。

---

## 已知限制

- Repository 每个方法独立打开连接并提交；事务封装 / UnitOfWork 留给后续阶段。
- `CreativeBriefRepository.create()`、`ReviewReportRepository.create()`、`SettingSnapshotRepository.create()`、`NumericalLedgerRepository.create()` 的签名包含额外 ID 参数，用于满足“调用方生成 ID”的约束。

---

## 下一步依赖

- **Task 005（Genre Profile 系统）** 可以直接复用 `ProjectRepository` 读取项目的 `genre_id`。
- **Task 006（CreativeModeProfile 系统）** 可以直接复用 `ProjectRepository` 读取项目的 `mode_id`。
- **Task 007+（CLI / Agent）** 应通过本 Repository 层读写 SQLite，不直接拼 SQL。
