# Task 075: Checkpointer 抽象层重构 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-06
> **分支**: main

---

## 交付摘要

将 `AsyncSqliteSaver` 的硬编码依赖重构为可配置抽象层，根治 Windows 下 WAL 文件锁竞争导致的卡死/内存暴涨问题。

## 变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/workflows/checkpointer.py` | Checkpointer 工厂：统一入口，支持 memory / sqlite 两种模式 |
| `tests/workflows/test_checkpointer.py` | 工厂模式 + 资源清理 + 配置切换测试（7 个用例） |
| `tests/workflows/__init__.py` | 测试包初始化 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `src/songyan/config.py` | 新增 `checkpointer_mode: Literal["memory", "sqlite"] = "sqlite"` |
| `src/songyan/workflows/phase1_graph.py` | `_get_checkpointer()` 委托工厂；`reset_checkpointer()` 同时清理 checkpointer 实例和 `_compiled_graph` |
| `tests/conftest.py` | `test_db` fixture 自动设置 `checkpointer_mode = "memory"` |
| `tests/integration/test_ch41_50_validation.py` | 移除临时 `patch("_get_checkpointer")`，依赖 fixture 自动切换 |
| `.env.example` | 追加 `CHECKPOINTER_MODE=sqlite` 说明 |
| `.gitignore` | 追加 `*.db-shm` / `*.db-wal` / `*.corrupted` |

## 测试验证

```bash
pytest tests/workflows/test_checkpointer.py -v
# 7 passed

pytest tests/integration/test_ch41_50_validation.py -v
# 1 passed in ~32s

pytest tests/integration/test_multi_chapter.py -v
# 3 passed
```

全量测试：`1271 collected`，`1270 passed`，`1 failed`（预存在：`test_embedding_benchmark.py::test_mock_end_to_end`，因 `projects/orbital_horror/chapters` 目录缺失导致 `total_chunks=0`，与本 Task 无关）。

## 设计决策

### 为什么不直接删除 AsyncSqliteSaver？

生产环境仍需要持久化 checkpoint（V3.1 目标），`MemorySaver` 仅在测试/验证环境使用。

### 为什么保留模块级单例？

保持与旧行为一致，避免同一进程内重复创建连接/编译图带来的开销。

### 为什么 reset_checkpointer 要同时清理 _compiled_graph？

`phase2_graph.run_project_pipeline` 在批量运行前调用 `reset_checkpointer()`，期望下一批章节重新编译图。若只清理 checkpointer 而不清理 `_compiled_graph`，`build_phase1_graph()` 会返回缓存的旧图，可能引用已关闭的连接。

## 已知限制

- `MemorySaver` 不支持跨进程 checkpoint 恢复（测试环境无此需求）
- `checkpointer_mode = "invalid"` 在运行时才抛 `ValueError`，非 Pydantic 校验时（因 `Literal` 已限制，正常配置不会触发）

## 后续建议

- 若将来引入 PostgreSQL checkpointer，只需在 `checkpointer.py` 的 `get_checkpointer()` 中新增分支，无需改动业务代码
- 建议在 CI 中增加 Windows runner，自动捕获此类平台兼容性问题
