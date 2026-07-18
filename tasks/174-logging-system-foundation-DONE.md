# Task 174 DONE: 日志体系落地

> **完成时间**: 2026-07-18  
> **阶段**: V9.1 长跑可靠性  
> **状态**: ✅ 完成（应用日志基础设施 + 字段约定完成；真实三边重建演示待 175 后补跑）  
> **任务书**: `tasks/174-logging-system-foundation.md`

---

## 交付内容

- 新增 `src/songyan/utils/logging_setup.py`，提供幂等 `configure_logging()` 与 `flush_logging_handlers()`。
- CLI 与两个 harness 接入日志初始化：`songyan` Click group、`run_172a7_genre_validation.py`、`run_172b_ch100_climb.py`。
- 应用日志落盘到 `logs/app/app-<YYYYMMDD>.jsonl`，console 与文件 sink 可独立配置。
- `LOG_LEVEL` 控制 console，`LOG_FILE_LEVEL` 控制文件 sink；默认 console INFO、文件 DEBUG。
- 绑定并传播 `project_id/run_id/chapter_number/stage/version_id/db_path`，与 `logs/chapter_runs/<run_id>.jsonl` 可按 `run_id/chapter_number` 对齐。
- 第三方 logger 压到 WARNING，包含大小写精确的 `LiteLLM` logger，避免 DEBUG 请求/响应泄漏到 console。

## 字段约定

| 字段 | 用途 |
|---|---|
| `project_id` | 项目 ID |
| `run_id` | run ID，与 chapter_runs JSONL 文件名和字段对齐 |
| `chapter_number` | 当前章号 |
| `stage` | 当前执行阶段，供 175 `LLMCallContext.stage` 复用 |
| `version_id` | 当前章节版本 ID |
| `db_path` | 当前 SQLite 文件路径 |

## 验证

| 命令 / 证据 | 结果 |
|---|---|
| `python -m pytest tests/test_173_llm_client_cleanup.py tests/test_174_logging_setup.py -q` | 13 passed |
| `python -m pytest tests/ -q` | 2814 passed, 2 skipped, 1 xfailed |
| `ruff check src/ tests/ scripts/run_172a7_genre_validation.py scripts/run_172b_ch100_climb.py` | All checks passed |
| `LOG_LEVEL=WARNING` + scifi smoke 尝试 | console 仅保留 LiteLLM WARNING，无 DEBUG 请求/响应 |

## 说明

真实 LLM smoke 未完整自然结束，三边重建演示未形成终判证据；原因是生成链路耗时和 API 成本不可控。Task 175 落地后应补跑带成本上限的短窗口实证。
