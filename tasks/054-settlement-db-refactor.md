# Task 054: settlement_extractor DB 访问重构

> **Phase**: V3.0 Layer 0 — 修复稳定性底线
> **优先级**: P1
> **依赖**: 053
> **预计工作量**: 中（2~3 天）

---

## Goal

将 `settlement_extractor.py` 中直接管理 DB 连接和事务的代码迁移到 Repository 层，确保所有子表写入通过统一共享 `conn` 参数完成，满足规则 53（Agent 不直接拿 DB connection）和规则 56（settlement 写入使用事务）。

## Context

`settlement_extractor.py` 的 `_apply_to_db()` 自行管理 `BEGIN/COMMIT`，内部调用多个 Repository 方法——但这些方法各自有独立 `get_db()` 上下文。虽然部分 Repository 已支持 `conn` 参数，但 `_apply_to_db()` 是否始终传递了同一个 `conn` 未完全确认。这是 V2.x 的结构性债务，也是 `database locked` 的根本诱因之一。

## In Scope（必须完成）

- [ ] **写入路径梳理**: 列出 `_apply_to_db()` 中所有子表写入调用（character_states / setting_snapshots / foreshadowings / numerical_ledger / continuity_tracking / permanent_scenes）
- [ ] **Repository 层补全**: 确保所有被调用的 Repository 方法支持可选 `conn` 参数
  - `CharacterStateRepository.create()`
  - `SettingSnapshotRepository.create()`
  - `ForeshadowingRepository.create()` / `update_status()`
  - `NumericalLedgerRepository.create()`
  - `SettingTrackingRepository.create()` / `update_last_mentioned()`
  - `PermanentSceneRepository.create()`
- [ ] **Agent 层重构**: `_apply_to_db()` 不再自行管理事务，改为：
  - 由调用方（`save_settlement()`）创建连接并开启事务
  - `_apply_to_db()` 接收 `conn` 参数，将所有写入操作绑定到同一连接
  - 调用方统一 `COMMIT` 或 `ROLLBACK`
- [ ] **原子性测试**: 新增 `test_settlement_atomic_rollback` — 模拟中途失败（如第 3 个子表写入失败），验证前 2 个子表未留下脏数据

## Out of Scope（明确不做）

- 不拆分 `settlement_extractor.py` 文件（属于 056 Layer 1）
- 不修改 settlement 的 LLM 提取逻辑（`_build_state_settlement()` 等）
- 不改动 settlement 的验证逻辑（`_validate_settlement()` 等）

## 接口契约

```python
# _apply_to_db() 签名变更
async def _apply_to_db(
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
    version_id: str,
    conn: aiosqlite.Connection,  # 改为必填
) -> None:
    """所有子表写入绑定到同一连接，不自行管理事务."""
    ...
```

## 测试要求

### Layer 2: 模块测试
- [ ] `test_settlement_all_repos_support_conn`: 验证所有相关 Repository 方法支持 `conn` 参数
- [ ] `test_settlement_atomic_rollback`: 中途失败回滚，无脏数据

### Layer 3: 集成测试
- [ ] `test_full_settlement_pipeline`: 从 `extract_settlement()` 到 `save_settlement()` 完整流程，验证所有子表有记录

## 验收标准

- [ ] `pytest tests/ -k "settlement" -v` 全部通过
- [ ] `_apply_to_db()` 不再出现 `async with get_db()` 或 `await conn.commit()`
- [ ] 代码符合规则 53（Agent 不直接拿 DB connection）
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/054-settlement-db-refactor-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 4.1 P1-2
- `AGENTS.md` — 规则 53, 56
