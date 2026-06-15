# Task 053: database locked 修复 — DONE

> **完成日期**: 2026-06-04
> **执行代理**: Kimi Code CLI
> **Git Commit**: `35ea097`

---

## 完成摘要

消灭 settlement 阶段 `continuity_tracking` / `permanent_scenes` 写入时的 `database locked` 错误，实施方案 A（busy_timeout + 写入重试），并补充并发测试覆盖。

---

## 根因分析

`database locked` 根因是 WAL 模式下多个 `get_db()` 调用获取独立连接，写操作与读操作竞争。

**已有临时修复（V2.x 带入）**:
- `connection.py`: `busy_timeout = 30000`（30 秒）
- `settlement_extractor.py`: `continuity_tracking` + `permanent_scenes` 在同一连接块内执行，减少连接数
- `continuity_repo.py`: 所有子表写入方法支持可选 `conn` 参数

**本 Task 补充**:
- 在 `apply_settlement` 的两个独立写入块（core + continuity）外层增加 WAL 重试机制
- 最多 3 次重试，指数退避（100ms → 200ms → 400ms）
- 仅捕获 `sqlite3.OperationalError` 中 message 含 `locked` 或 `busy` 的异常

---

## 变更清单

### 1. 重试辅助函数 (`src/songyan/agents/settlement_extractor.py`)

新增 `_execute_with_db_retry`:
```python
async def _execute_with_db_retry(
    func: Callable[..., Awaitable[_T]],
    *args: Any,
    max_retries: int = 3,
    backoff_ms: float = 100,
    **kwargs: Any,
) -> _T:
```

- 仅对 `OperationalError` 中 message 含 `locked`/`busy` 的异常重试
- 其他异常（如 `IntegrityError`）直接抛出，不重试
- 指数退避：`backoff_ms * (2 ** attempt)`

### 2. apply_settlement 重试封装

- `conn is None` 路径（自行管理连接）：`_do_core_writes()` 带重试
- `continuity` 块：`_do_continuity_writes()` 带重试
- `conn is not None` 路径（调用方管理）：不重试，由调用方负责

### 3. 测试覆盖

| 测试文件 | 测试名 | 验证点 |
|----------|--------|--------|
| `tests/db/test_connection.py` | `test_pragma_busy_timeout` | `busy_timeout >= 30000` |
| `tests/test_settlement_extractor.py` | `test_retry_max_retries_0_fails_immediately` | max_retries=0 立即失败 |
| `tests/test_settlement_extractor.py` | `test_retry_max_retries_1_succeeds_on_retry` | max_retries=1 第二次成功 |
| `tests/test_settlement_extractor.py` | `test_retry_non_locked_error_not_retried` | 非 locked 错误不重试 |
| `tests/test_settlement_extractor.py` | `test_concurrent_settlement_writes` | 3 协程并发写入不同 project，无异常 |

---

## 测试报告

```
pytest tests/test_settlement_extractor.py tests/test_settlement_impact.py tests/db/test_connection.py
# 66 passed, 0 failed

pytest tests/test_settlement_extractor.py tests/test_settlement_impact.py tests/db/test_connection.py tests/test_revision_handler.py tests/test_revision_handler_fuzzy.py tests/test_revision_handler_patch.py
# 136 passed, 0 failed（核心路径无回归）
```

---

## 验收状态

| 验收项 | 状态 | 备注 |
|--------|------|------|
| 根因确认：分析所有 DB 写入点 | ✅ | core + continuity 两个独立连接块 |
| 方案 A 实施：busy_timeout + 重试 | ✅ | busy_timeout 30s 已存在，新增重试层 |
| `test_busy_timeout_config` | ✅ | busy_timeout >= 30000 |
| `test_concurrent_settlement_writes` | ✅ | 3 协程并发写入通过 |
| 重试边界测试 | ✅ | max_retries=0/1 + 非 locked 错误 |
| `docs/STATUS.md` 更新 | ✅ | 053 状态 → 已完成 |

---

## 已知限制

1. **真实章节验证（Ch10~Ch12 复跑）待执行**：当前环境无 LLM API 密钥，无法运行完整 pipeline。Mock 测试和并发测试已覆盖核心路径。
2. **全量测试超时**：整个测试套件（>1000 测试）运行时间超过 5 分钟，与当前改动无关。核心相关测试已通过。

---

## 未修改项（按 Task 约束）

- ❌ 未引入连接池或写队列（方案 C）
- ❌ 未合并 settlement 所有子表为单事务（方案 B，留待 054）
- ❌ 未修改 settlement 主流程（`extract_settlement()` + `_apply_core()`）

---

## 交接建议

- **下一 Task**: 054（settlement_extractor DB 访问重构）或 055（_helpers.py 直接 DB 访问清理）
- **真实验证指令**: 在已配置 LLM API 的环境中从 Ch10 开始运行，观察日志中是否有 `settlement.db_retry` 或 `database locked` 异常
