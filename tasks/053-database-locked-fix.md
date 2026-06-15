# Task 053: database locked 修复

> **Phase**: V3.0 Layer 0 — 修复稳定性底线
> **优先级**: P1
> **依赖**: 052（Layer 0 串行）
> **预计工作量**: 小（0.5~1 天）

---

## Goal

消灭 settlement 阶段 `continuity_tracking` / `permanent_scenes` 写入时的 `database locked` 错误，确保 Ch10~Ch30 每章 settlement 全部子表写入成功率 100%。

## Context

V2.x 末期在 Ch10~Ch12 连续复现 `database locked`。根因是 WAL 模式下多个 `get_db()` 调用获取独立连接，写操作与读操作竞争。当前 `busy_timeout=5000ms`（5 秒）过短。

**注意**: 本 Task 执行前，已有临时修复（busy_timeout 30s + 连接复用）提交到 main。本 Task 需要：
1. 确认临时修复是否足够
2. 如不足，实施 PRD 推荐的方案 A（写入重试）
3. 新增测试覆盖并发写入场景

## In Scope（必须完成）

- [ ] **根因确认**: 分析 `settlement_extractor._apply_to_db()` 的所有 DB 写入点，绘制写入时序图
- [ ] **方案实施**: 采用 PRD 推荐方案 A — `busy_timeout` 调整 + 写入重试（最多 3 次）
  - 若已有临时修复足够，则聚焦测试覆盖
  - 若不足，在 `_update_continuity_tracking()` / `_save_permanent_scenes()` 增加重试装饰器
- [ ] **并发测试**: 新增 `test_concurrent_settlement_writes` — 模拟 3 个并行 settlement 写入，验证无 locked 异常

## Out of Scope（明确不做）

- 不引入连接池或写队列（方案 C，超出 V3.0 范围）
- 不合并 settlement 所有子表为单事务（方案 B，风险较高，留待 054 处理）
- 不修改 settlement 主流程（`extract_settlement()` + `_apply_core()`）

## 接口契约

```python
# 新增重试装饰器（若需要）
def _with_retry(max_retries: int = 3, backoff_ms: float = 100):
    """WAL 写入重试装饰器 — 仅捕获 database locked."""
    ...
```

## 测试要求

### Layer 1: 模型测试
- [ ] 重试装饰器边界值：`max_retries=0` 立即失败，`max_retries=1` 一次重试后成功

### Layer 2: 模块测试
- [ ] `test_concurrent_settlement_writes`: 3 个协程同时写入不同 project，无异常
- [ ] `test_busy_timeout_config`: 验证 `get_db()` 返回的连接 `busy_timeout >= 30000`

### Layer 3: 集成验证
- [ ] 在 Ch10~Ch12 场景下复跑 3 次，每次 settlement 写入全部成功

## 验收标准

- [ ] `database locked` 在 Ch10~Ch12 复跑中不再出现
- [ ] `pytest tests/ -k "settlement or database" -v` 全部通过
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/053-database-locked-fix-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 4.1 P1-1
- `src/songyan/db/connection.py` — PRAGMA 配置
