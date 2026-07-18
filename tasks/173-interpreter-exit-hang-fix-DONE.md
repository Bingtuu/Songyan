# Task 173 DONE: 解释器退出挂死修复

> **完成时间**: 2026-07-18  
> **阶段**: V9.1 长跑可靠性  
> **状态**: ✅ 完成（代码级修复 + 自动化验证完成；真实 LLM end10 回归待 175 后补跑）  
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
