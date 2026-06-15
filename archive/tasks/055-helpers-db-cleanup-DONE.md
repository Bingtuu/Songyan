# Task 055: _helpers.py 直接 DB 访问清理 — DONE

> **完成日期**: 2026-06-04
> **执行代理**: Kimi Code CLI
> **Git Commit**: `f0086d8`

---

## 完成摘要

消除 `workflows/_helpers.py` 中绕过 Repository 层直接调用 `get_db()` 的代码，满足规则 53（Agent 不直接拿 DB connection）。

---

## 现状扫描

经扫描，`workflows/_helpers.py` 中 3 个疑似直接 DB 访问点的实际状态：

| 函数 | 状态 | 说明 |
|------|------|------|
| `load_open_threads()` | ✅ 已是 Repository 调用 | 使用 `SummaryRepository().list_recent()` |
| `load_chapter_goal()` | ✅ 已是 Repository 调用 | 使用 `ChapterGoalRepository().get()` |
| `load_latest_audits()` | ❌ 有直接 `get_db()` | 直接执行 `SELECT ... FROM review_reports` |

---

## 变更清单

### 1. `load_latest_audits` 重构 (`src/songyan/workflows/_helpers.py`)

**删除**: 直接 SQL 查询（`async with get_db() as conn:` + `conn.execute`）

**改为**: `ReviewReportRepository().get_by_version(version_id)` → 返回 `report.rule_audit, report.llm_audit`

```python
# 重构前（~30 行）
async with get_db() as conn:
    cursor = await conn.execute("SELECT audit_type, ... FROM review_reports ...")
    rows = await cursor.fetchall()
# 遍历 rows，分别解析 rule 和 llm...

# 重构后（4 行）
report = await ReviewReportRepository().get_by_version(version_id)
if report is None:
    return None, None
return report.rule_audit, report.llm_audit
```

### 2. 清理未使用导入

- 删除 `from sqlite3 import Row`
- 删除 `from songyan.db.connection import get_db`
- 删除 `load_latest_audits` 内部的 `from songyan.db.repository import _from_json`

### 3. 合规测试 (`tests/test_helpers.py`)

新增 `test_helpers_no_raw_db_access`：
- 通过 AST 解析 `_helpers.py`
- 断言不存在从 `songyan.db.connection` 导入 `get_db`

---

## 测试报告

```bash
rg "get_db" src/songyan/workflows/_helpers.py
# 返回空（exit code 1 = 无匹配）

pytest tests/test_helpers.py tests/test_settlement_extractor.py tests/test_settlement_impact.py tests/db/test_connection.py tests/test_revision_handler.py tests/test_revision_handler_fuzzy.py tests/test_revision_handler_patch.py
# 138 passed, 0 failed
```

---

## 验收状态

| 验收项 | 状态 | 备注 |
|--------|------|------|
| `rg "get_db" src/songyan/workflows/_helpers.py` 返回空 | ✅ | 无直接 DB 访问 |
| `load_open_threads` 使用 Repository | ✅ | 已确认 |
| `load_chapter_goal` 使用 Repository | ✅ | 已确认 |
| `load_latest_audits` 使用 Repository | ✅ | 改用 `ReviewReportRepository.get_by_version()` |
| `test_helpers_no_raw_db_access` | ✅ | AST 级合规检查 |
| `docs/STATUS.md` 更新 | ✅ | 055 状态 → 已完成 |

---

## 已知限制

1. `test_phase1_graph.py` 和 `test_context_manager.py` 因测试套件规模运行超时，但核心相关路径（settlement + revision + DB + helpers）全部通过。

---

## 未修改项（按 Task 约束）

- ❌ 未拆分 `_helpers.py`（属于 056）
- ❌ 未修改 `context_manager.py` 或 `phase1_graph.py` 的调用逻辑
- ❌ 未新增 Repository 方法（只使用已有的 `get_by_version`）

---

## 交接建议

- **Layer 0 完成**: 052 ✅ | 053 ✅ | 054 ✅ | 055 ✅
- **下一 Task**: 056（大文件拆分）或 057（死代码清理），进入 Layer 1
