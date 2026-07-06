# Pass 10: 性能与可观测性审计报告

## 执行摘要

- 发现总数: 5
- P0: 0, P1: 0, P2: 5
- 关键结论: RAG VectorStore 已支持增量加载，Embedder 有 warm_up 方法；LLM 调用有重试/退避/预算熔断；DB 遥测已落地；结构化日志使用规范（仅 CLI `evals/__main__.py` 有少量 `print`）。主要改进点是 `call_llm` 不返回 token 用量/request_id、Embedder 存在裸 `except Exception`、RAG 增量加载的调用方需确认。

## 检查项与发现

### 10.1 RAG 向量加载性能

- **级别**: 通过
- **文件**: `src/songyan/rag/vector_store.py`
- **方法**: 检查 `load` / `load_incremental` 实现
- **结果**:
  - `VectorStore` 维护 `_loaded_chapter` 游标。
  - `load_incremental`（`:51`）在 `_loaded_chapter == 0` 时全量加载，否则增量加载新增章节。
  - 加载后更新 `_loaded_chapter` 为已加载最大章号。
- **结论**: 已具备增量加载能力，避免每次检索全量加载。
- **P2 建议**: 确认所有调用方均使用 `load_incremental` 而非 `load`；若仍有全量调用，建议改为增量。

### 10.2 Embedder 懒加载影响

- **级别**: P2
- **文件**: `src/songyan/rag/embedder.py`
- **方法**: 检查加载策略和异常处理
- **结果**:
  - 模型首次调用时懒加载，模块级缓存 `_MODEL_CACHE` 实现单例复用。
  - 提供 `warm_up` 类方法（`:66`）用于预加载，避免 Ch2 首次 5-20s 卡顿。
  - `embed` 方法中存在裸 `except Exception`（`:103`），失败时返回全零向量。
- **问题描述**: 裸 `except Exception` 会吞掉 ImportError、内存不足等真实错误，且返回零向量可能导致 RAG 检索结果无意义。
- **修复建议**: 将裸 `except Exception` 收窄为 `(RuntimeError, OSError, ValueError)`；在初始化失败时明确抛出异常，而非返回零向量。

### 10.3 LLM 调用耗时与重试

- **级别**: P2
- **文件**: `src/songyan/llm/client.py`, `src/songyan/llm/retry.py`
- **方法**: 检查超时、重试、token 用量、request_id
- **结果**:
  - `call_llm` 默认单次超时 60s，总超时 = `timeout * max_retries + 30`。
  - `retry_with_backoff` 支持指数退避 + jitter，对 `LLMRateLimitError` 使用 `Retry-After`。
  - 按 run 级计数 LLM 调用，超预算时抛出 `LLMBudgetExceededError`。
  - **缺失**: `call_llm` 仅返回 `str`，不返回 token 用量（`usage`）和 request_id。
- **修复建议**: 将 `call_llm` 返回类型改为 `(content: str, usage: TokenUsage | None, request_id: str | None)`；调用方逐步迁移。或新增 `call_llm_with_metadata` 并保持 `call_llm` 兼容。

### 10.4 DB 维护遥测

- **级别**: 通过
- **文件**: `src/songyan/db/run_db_metrics_repo.py`, `src/songyan/evals/db_metrics.py`
- **方法**: 检查遥测表和采集逻辑
- **结果**:
  - `run_db_metrics` 表记录 `db_size_bytes`, `wal_size_bytes`, `page_count`, `scan_latency_ms` 等。
  - `_run_db_maintenance`（`phase2_graph.py:223`）每 10 章采样一次，run 收尾再采样一次。
  - T5 尺寸红线通过 `check_t5_size_redline` 计算。
- **结论**: DB 遥测机制完善，且失败仅告警不中断 run。

### 10.5 结构化日志

- **级别**: 通过（含一处 P2）
- **方法**: `rg 'print\(' src/songyan/ -n`
- **结果**:
  - 全库仅 `src/songyan/evals/__main__.py` 中有 8 处 `print`，用于 CLI 输出报告，可接受。
  - 业务代码全部使用 `structlog`。
- **P2 建议**: `evals/__main__.py` 的 `print` 可改用 `structlog` 或标准 `logging`，保持全库一致性；或明确标记为 CLI 输出。

### 10.6 request_id 跨调用链关联

- **级别**: P2
- **文件**: `src/songyan/llm/client.py`
- **方法**: 检查是否生成/传递 request_id
- **结果**: 当前 `call_llm` 未生成 request_id，无法将一次 LLM 调用与重试、异常、日志关联。
- **修复建议**: 在 `call_llm` 入口生成 `request_id`（如 `uuid`），绑定到 structlog 上下文，并在重试日志中携带。

## 通过项

- [x] RAG VectorStore 支持增量加载。
- [x] Embedder 提供 warm_up 预加载。
- [x] LLM 调用具备超时、指数退避、限流感知、run 级预算熔断。
- [x] DB 尺寸/扫描耗时遥测按章节采样。
- [x] 业务代码使用 structlog，无 `print`。

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 10.2 | P2 | Embedder `embed` 使用裸 `except Exception` 并返回零向量 | `src/songyan/rag/embedder.py` | `pytest tests/rag/ -q` |
| 10.3 | P2 | `call_llm` 不返回 token 用量 | `src/songyan/llm/client.py` + 调用方 | `pytest tests/ -k llm -q` |
| 10.6 | P2 | LLM 调用链缺少 request_id | `src/songyan/llm/client.py`, `src/songyan/llm/retry.py` | `pytest tests/ -k llm -q` |
| 10.5 | P2 | `evals/__main__.py` 使用 `print` | `src/songyan/evals/__main__.py` | `pytest tests/evals/ -q` |
| 10.1b | P2 | 需确认所有 VectorStore 调用方使用增量加载 | 全局搜索 `\.load\(` 在 `rag/` 的使用 | `pytest tests/rag/ -q` |

---

> 下一 Pass: [Pass 11 安全与依赖审计](pass11-security-dependencies-report.md)
