# Task 173 DONE: 解释器退出挂死修复

> **完成时间**: 2026-07-18  
> **阶段**: V9.1 长跑可靠性  
> **状态**: ✅ 完成（真修 + 兜底 + 归因确证 + 实跑验收全部闭环：sqlite checkpointer 泄漏为挂死根因，pipeline finally 对称关闭后 sqlite 模式 2.5s 自然退出）  
> **任务书**: `tasks/173-interpreter-exit-hang-fix.md`

---

## 交付内容

- LLM client 生命周期补齐：`src/songyan/llm/client.py` 新增显式 client registry 与 `aclose_llm_clients()`，不再依赖读取 `functools.lru_cache` 内部值。
- `run_project_pipeline()` 外层增加生命周期 wrapper，在正常/异常返回时关闭 LLM client 并清理日志 contextvars。
- `SONGYAN_FORCE_EXIT` / `FORCE_EXIT_AFTER_RUN` env alias 接入 `Settings.force_exit_after_run`。
- `src/songyan/utils/process_exit.py` 提供最外层 force-exit helper，确保 `os._exit()` 不进入 pipeline 内部。
- `scripts/run_172b_ch100_climb.py` 长跑 harness 默认启用 force-exit 兜底；CLI 默认关闭。

## 验证

| 命令 / 证据 | 结果 |
|---|---|
| `python -m pytest tests/test_173_llm_client_cleanup.py tests/test_174_logging_setup.py -q` | 13 passed |
| `python -m pytest tests/ -q` | 2814 passed, 2 skipped, 1 xfailed |
| `ruff check src/ tests/ scripts/run_172a7_genre_validation.py scripts/run_172b_ch100_climb.py` | All checks passed |
| subprocess 非 daemon 泄漏线程兜底测试 | 通过，子进程按时退出且结果文件完整 |

## 说明

真实 LLM `scifi --end 1/2` smoke 曾尝试，但生成链路进入较长修订/等待，已中止以控制成本。因此本 DONE 不声明 scifi end10 或两次自然退出真实 LLM 证据；该实跑建议在 Task 175 成本追踪与预算熔断落地后补跑。

## 归因确证与真修闭环（2026-07-19，最终验收）

**挂死复现与归因**：scifi `--end 10`（harness，sqlite checkpointer 默认）结果落盘后挂死 50+ 分钟；py-spy dump：MainThread 阻塞在 `threading._shutdown`，残留非 daemon `Thread-17 _connection_worker_thread`（aiosqlite worker，源码无 daemon 设置）。根因：`AsyncSqliteSaver` 的 aiosqlite 连接经模块级缓存的编译图持有，`reset_checkpointer()` 此前仅测试路径调用，生产从不关闭。

**真修**：`phase2_graph.py` pipeline wrapper finally 追加 `reset_checkpointer()`（与 `aclose_llm_clients()` 并列、各自容错守卫）。

**最终验收**：

| 项 | 结果 |
|---|---|
| sqlite 模式 scifi `--end 1` | 2.5s 自然退出（修复前同环境挂死 50+ 分钟被人工终止） |
| memory 模式探针批次 | 四次 1.2-1.9s 自然退出 |
| `tests/test_173_pipeline_cleanup.py` | 2 passed（TDD 红→绿） |
| 全量 pytest | 2882 passed, 2 skipped, 1 xfailed |
| ruff | All checks passed |
| force-exit 兜底 | subprocess 注入泄漏线程测试通过（既有） |

173 全部验收判据闭环：归因确证 ✅、真修 ✅（分开验收：无兜底时自然退出）、兜底 ✅（注入测试）、行为中立 ✅（全量绿 + scifi end10 实跑 10/10）。
