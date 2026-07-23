# Task 154: LLM 限流感知与全局预算 — DONE

> **Phase**: V6 阶段 C（工程加固）
> **状态**: ✅ 完成
> **合入时间**: 2026-07-02
> **事实文档**: 本文件

---

## 完成摘要

给 LLM 调用加两层长跑防护：
1. **限流感知退避**：识别 HTTP 429 / `Retry-After`，按服务器建议或指数退避重试，让偶发限流不再退化成“章节失败 → `on_failure=abort` 级联终止整批”。
2. **单 run 全局预算 + 熔断**：为一次 run 设置 LLM 调用次数上限，超预算触发可观测的熔断（run `status="paused"`、保留已生成章节），而非静默卡死或无限烧调用。

---

## 实现落点

### 154a — 429 / Retry-After 感知退避

- `exceptions.py` 新增：
  - `LLMRateLimitError(LLMError)`：携带 `retry_after: float | None`。
  - `LLMBudgetExceededError(SongyanError)`：携带 `used_calls`、`budget`、`last_chapter`。
- `llm/client.py`：
  - `_invoke` 在包装为 `LLMError` 前先分类限流异常：识别 `status_code == 429` 或异常类名 `RateLimitError` / `RateLimitExceededError`。
  - 从异常的 `headers` / `response.headers` / `litellm_headers` 提取 `Retry-After`（秒）。
  - 分类后抛 `LLMRateLimitError`，保留 `retry_after`。
  - 编程类异常（`TypeError`/`ValueError`/`KeyError`/`AttributeError`）仍直接抛、不重试。
- `llm/retry.py`：
  - `retry_with_backoff` 支持服务器建议等待：当捕获 `LLMRateLimitError` 且 `retry_after` 存在时，等待 `min(retry_after, settings.llm_rate_limit_max_wait)`；否则回退指数退避 + jitter。
  - 所有重试耗尽后，若最后异常已是 `LLMError` 子类，直接复抛原异常（避免吞掉 `LLMRateLimitError` 的 `retry_after`）。

### 154b — 单 run 全局 LLM 预算 + 熔断

- `config.py` 新增可配项：
  - `llm_max_retries: int = 3`
  - `llm_rate_limit_max_wait: float = 60.0`
  - `llm_run_call_budget: int = 0`（0 = 关闭）
- `llm/client.py`：
  - 使用 `contextvars.ContextVar` 实现 per-run 调用计数（非 `@lru_cache` 单例）。
  - 提供 `reset_llm_call_count()` / `get_llm_call_count()` / `set_llm_budget_last_chapter(chapter_number)`。
  - `call_llm` 签名改为 `max_retries: int | None = None`；`None` 时回退 `settings.llm_max_retries`。
  - 每次 `call_llm` 调用前检查预算：`budget > 0` 且本次调用序号 `> budget` 时抛 `LLMBudgetExceededError`。
- `workflows/phase2_graph.py`：
  - run 开始时调用 `reset_llm_call_count()`。
  - 每章循环中调用 `set_llm_budget_last_chapter(chapter_number)`。
  - `_run_single_chapter` 显式 re-raise `LLMBudgetExceededError`。
  - `run_project_pipeline` 捕获 `LLMBudgetExceededError`，调用 `_pause_run_for_auto_halt` 落库 `status="paused"`，记录报告字段后复抛。

---

## 接口契约

```python
# exceptions.py
class LLMRateLimitError(LLMError):
    def __init__(self, message: str, retry_after: float | None = None, ...): ...

class LLMBudgetExceededError(SongyanError):
    def __init__(self, message: str, used_calls: int, budget: int, last_chapter: int): ...

# config.py Settings
llm_max_retries: int = 3
llm_rate_limit_max_wait: float = 60.0
llm_run_call_budget: int = 0  # 0 = 不启用

# llm/client.py
async def call_llm(prompt: str, *, max_retries: int | None = None, ...) -> str: ...
def reset_llm_call_count() -> None: ...
def get_llm_call_count() -> int: ...
```

---

## 关键口径

- **预算默认关闭**：`llm_run_call_budget=0` 时行为与现状完全一致；长跑显式设正值开启。
- **计数按 run 隔离**：通过 `contextvars.ContextVar` + run 开始时 `reset_llm_call_count()` 实现，不污染进程级 `get_llm()` 单例。
- **熔断 ≠ 章节失败**：预算耗尽是 run 级硬边界，直接 pause run；不进入 `on_failure` 分支。
- **不与质量 AutoHalt 混触发**：预算熔断走独立异常 `LLMBudgetExceededError`，落库同样为 `paused`，但触发线独立。
- **可被 Task 153 resume 续跑**：paused run 可通过 `--resume` 续跑；resume 时 `reset_llm_call_count()` 会重置预算计数。
- **不引重量级依赖**：沿用现有手写 `retry.py` 退避，未引入 tenacity。

---

## 测试覆盖

`tests/test_154_llm_rate_limit_and_budget.py`（12 个用例）：

- `call_llm` 识别 429 + `Retry-After` 并按建议退避后成功。
- `Retry-After` 超过 `llm_rate_limit_max_wait` 时被截断。
- 429 无 `Retry-After` 时回退指数退避 + jitter。
- 编程类异常（`TypeError`）直接抛、不重试。
- `retry_with_backoff` 单独验证 `retry_after` 与无 `retry_after` 回退。
- 预算重置/读取。
- `budget=0` 永不熔断。
- `budget=N` 第 N+1 次调用抛 `LLMBudgetExceededError`（含 used/budget/last_chapter）。
- 计数通过 `reset` 隔离。
- `phase2_graph` 捕获预算异常并将 run 置 `paused`。
- `max_retries=None` 时回退 `settings.llm_max_retries`。

---

## 验证结果

- `pytest tests/test_154_llm_rate_limit_and_budget.py -v`：12 passed。
- `pytest tests/test_llm_client.py tests/test_llm_auditor.py -q`：42 passed，无回归。
- `ruff check src/ tests/`：通过。

---

## Layer 3 计划

Task 154 的“429 不级联 abort”与“预算熔断后可 resume”实跑证据将在 **Task 158（Ch1-Ch100 长跑验证）** 中统一采集并入 `docs/reports/`。当前模块测试已覆盖 429 分类、Retry-After 退避、预算熔断与编排层 pause 等全部口径。

---

## 参考

- 规划：`docs/v6-plan.md` §3 阶段 C
- 任务文档：`archive/v6/tasks/154-llm-rate-limit-and-budget.md`
- 相关代码：`src/songyan/llm/client.py`、`src/songyan/llm/retry.py`、`src/songyan/exceptions.py`、`src/songyan/config.py`、`src/songyan/workflows/phase2_graph.py`
