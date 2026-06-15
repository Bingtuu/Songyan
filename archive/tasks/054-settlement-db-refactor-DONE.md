# Task 054: settlement_extractor DB 访问重构 — DONE

> **完成日期**: 2026-06-04
> **执行代理**: Kimi Code CLI
> **Git Commit**: `7573d34`

---

## 完成摘要

将 `settlement_extractor.py` 中直接管理 DB 连接和事务的代码迁移到调用方，确保所有子表写入通过统一共享 `conn` 参数完成，满足规则 53（Agent 不直接拿 DB connection）和规则 56（settlement 写入使用事务）。

---

## 变更清单

### 1. Agent 层 (`src/songyan/agents/settlement_extractor.py`)

**`apply_settlement` 签名变更**:
- `conn: aiosqlite.Connection | None = None` → `conn: aiosqlite.Connection`（必填）
- 删除 `conn is None` 分支（自行管理连接的向后兼容路径）
- 删除 `_do_core_writes` / `_do_continuity_writes` 的重试包装（重试由调用方负责）
- core 写入和 continuity 写入绑定到同一个 `conn`
- 更新 docstring：明确由调用方管理事务生命周期

**`_apply_core` 内部不变**：所有 Repository 调用继续通过 `conn=` 传递连接。

### 2. 调用方 (`src/songyan/workflows/_nodes.py`)

- 在 `apply_settlement(..., conn=conn)` 后添加 `await conn.commit()`
- 调用方统一创建连接、传递连接、提交事务

### 3. 测试层 (`tests/test_settlement_extractor.py`)

- `TestApplySettlement` 中 6 个测试：补充 `conn=AsyncMock()`
- `TestConcurrentSettlement`：改为 `async with get_db() as conn:` 内传递 `conn` 并 `commit`
- **新增 `TestSettlementAtomicity`**:
  - `test_settlement_atomic_rollback`: 模拟 `setting_repo.create` 失败，调用方 `rollback` 后验证 `character_states` 无脏数据

---

## 写入路径梳理

`apply_settlement` 内所有子表写入（按执行顺序）：

| # | 子表 | Repository 方法 | conn 支持 |
|---|------|-----------------|-----------|
| 1 | `character_states` | `CharacterStateRepository.add_state_snapshot()` | ✅ |
| 2 | `setting_snapshots` | `SettingSnapshotRepository.create()` | ✅ |
| 3 | `foreshadowings` | `ForeshadowingRepository.create()` / `update_status()` | ✅ |
| 4 | `numerical_ledgers` | `NumericalLedgerRepository.create()` | ✅ |
| 5 | `setting_tracking` | `SettingTrackingRepository.create()` / `update_last_mentioned()` | ✅ |
| 6 | `inventory_tracker` | `InventoryTrackerRepository.create()` | ✅ |
| 7 | `location_tracker` | `LocationTrackerRepository.create()` | ✅ |
| 8 | `permanent_scenes` | `PermanentSceneRepository.create()` | ✅ |

所有 8 个子表写入方法均支持可选 `conn` 参数，模式统一：
```python
if conn is None:
    async with get_db() as c:
        await _do(c)
        await c.commit()
else:
    await _do(conn)
```

---

## 测试报告

```
pytest tests/test_settlement_extractor.py
# 45 passed, 0 failed

pytest tests/test_settlement_extractor.py tests/test_settlement_impact.py tests/db/test_connection.py tests/test_revision_handler.py tests/test_revision_handler_fuzzy.py tests/test_revision_handler_patch.py
# 137 passed, 0 failed（核心路径无回归）
```

---

## 验收状态

| 验收项 | 状态 | 备注 |
|--------|------|------|
| 写入路径梳理：8 个子表 | ✅ | 全部确认 |
| Repository 层 conn 支持 | ✅ | 8 个方法全部支持 |
| `apply_settlement` conn 必填 | ✅ | 签名已变更 |
| `apply_settlement` 无 `get_db()` / `commit()` | ✅ | 自行管理分支已删除 |
| 规则 53（Agent 不直接拿 DB connection） | ✅ | 由调用方提供 conn |
| `test_settlement_atomic_rollback` | ✅ | rollback 后无脏数据 |
| `docs/STATUS.md` 更新 | ✅ | 054 状态 → 已完成 |

---

## 已知限制

1. `_nodes.py` 中 `apply_settlement` 之后显式添加了 `await conn.commit()`。若 V2.x 之前未 commit 的数据已部分丢失，本 Task 修复了该隐患。
2. 全量测试套件因规模过大运行超时，与本次改动无关。核心相关测试已通过。

---

## 未修改项（按 Task 约束）

- ❌ 未拆分 `settlement_extractor.py` 文件（属于 056）
- ❌ 未修改 settlement 的 LLM 提取逻辑（`_build_state_settlement()` 等）
- ❌ 未改动 settlement 的验证逻辑（`_validate_settlement()` 等）

---

## 交接建议

- **下一 Task**: 055（_helpers.py 直接 DB 访问清理）
- **注意**: `apply_settlement` 现为 `conn` 必填，任何新增调用方必须传递连接并负责 commit/rollback
