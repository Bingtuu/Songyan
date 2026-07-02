# Task 154: LLM 限流感知与全局预算

> **Phase**: V6 阶段 C（工程加固）
> **优先级**: P1（无人值守长跑抗抖动：429 退避防级联 abort，全局预算防静默烧钱/卡死）
> **依赖**: 阶段 0/A/B 已落地（不改治理）；复用现有 `llm/client.py` + `llm/retry.py` + `SongyanError` 层
> **预计工作量**: 中（拆 154a 429/Retry-After 感知退避 + 154b 单 run 全局预算与熔断）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 C

---

## Goal

给 LLM 调用加两层长跑防护：
1. **限流感知退避**：识别 HTTP 429 / `Retry-After`，按服务器建议或指数退避重试，让偶发限流不再退化成"章节失败 → `on_failure=abort` 级联终止整批"。
2. **单 run 全局预算 + 熔断**：为一次 run 设置 LLM 调用次数（可选 token/成本）上限，超预算触发**可观测的熔断**（明确停在预算边界并给出报告），而非静默卡死或无限烧调用。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- **LLM 封装唯一入口**：`src/songyan/llm/client.py`。技术栈 = LangChain + litellm（`ChatLiteLLM`，`client.py:33-42`），默认 DeepSeek（`base_url` `client.py:71`）。公共 API：`get_llm()`（`client.py:45`，`@lru_cache`）与 `async def call_llm(prompt, *, temperature, max_tokens, max_retries=3, timeout=60)`（`client.py:101`）。所有 Agent 都走 `call_llm`（writer/goal_planner/settlement_extractor/creative_director/revision_handler/llm_auditor/summary_writer/literary_auditor/arc_summary_generator）。
- **现有重试是"通用异常"退避，非 429 感知**：`src/songyan/llm/retry.py` `retry_with_backoff`（`retry.py:20`）指数退避 + jitter（`retry.py:52-53`），可重试异常 `(LLMError, TimeoutError, ConnectionError)`（`retry.py:26`）。但 `call_llm._invoke` 把任何非编程类 `Exception` 直接包成 `LLMError`（`client.py:137-139`）——**HTTP 状态码/`Retry-After` 头在这一步就被抹平丢失**。全仓 grep `429` / `Retry-After` / `RateLimit` 零命中。
- **超时已有**：`ChatLiteLLM(timeout=...)` 单次超时（默认 60s）+ `call_llm` 用 `asyncio.wait_for(..., total_timeout = timeout * max_retries + 30)`（`client.py:143-155`）；Task 139g settlement 用 `timeout=120, max_retries=2`（`settlement_extractor/__init__.py` 约 L611）。
- **无任何 LLM 调用预算/计数/熔断**：grep `budget`/`circuit`/`breaker`/`call_count`/`quota`/`max_calls` 无 LLM 相关命中。**关键澄清**：Context Diet 2.0 的 "BudgetHardCeiling" / `context_total_budget=32000`（`config.py:24`）是**上下文/prompt token 预算**（一次 prompt 装多少上下文），**与"LLM API 调用次数/成本预算"是两回事**，不可混为一谈。现有唯一"熔断"是**质量维度**的 `AutoHaltException`（`exceptions.py:53`，连续质量异常触发），非速率/成本。
- **错误传播现状**：`SongyanError`（`exceptions.py:6`）→ `LLMError`（`exceptions.py:10`，带 `raw_response`/`cause`）→ `LLMResponseParseError`（`exceptions.py:24`）。LLM 错误通常**只失败当章**（Agent 节点 `except (LLMError, LLMResponseParseError)` 返回 error state，如 `_nodes.py` 多处），批层由 `on_failure` 决定 abort/retry。**但持续 429 现在会表现为普通章节失败 → 默认 `abort` 级联终止整批**——这正是本 Task 要消除的失效模式。
- **配置中心**：`src/songyan/config.py` `Settings`（`config.py:8`），有 `llm_api_key`/`llm_base_url`/`llm_model`/`llm_temperature`；`max_tokens`/`timeout`/`max_retries` 目前是 `call_llm` 的每调用参数、**不在 config**。新增预算/退避旋钮的自然落点是扩展 `Settings`。

**为什么现在做**：阶段 D 的 Ch100/Ch150 长跑动辄数千次 LLM 调用、跑 >10h，偶发 429 与失控烧调用是长跑最常见的两类非质量故障。阶段 C 必须先把这两类"抖动"从"级联 abort/静默卡死"变成"退避续跑 / 可观测熔断"。

## Cross-Task Coordination（阶段 C 统一口径）

- **与 155（失败隔离）的分工**：154 让**单次 LLM 调用**遇 429 时退避重试、并给 run 设总预算；155 让**单章失败**被隔离而不终止整批。二者叠加效果：偶发限流由 154 在调用层吸收（多数不会冒泡成章节失败）；若限流持续到耗尽退避，章节失败再由 155 隔离；若触及全局预算，则由 154 熔断（明确停机、非隔离继续）。**预算熔断 ≠ 章节失败**：熔断是 run 级硬边界，应像 AutoHalt 一样有独立异常与暂停语义。
- **熔断复用 AutoHalt 暂停范式**：新增 `LLMBudgetExceededError`（或复用/并列 `AutoHaltException` 的暂停落库路径 `_pause_run_for_auto_halt`，`phase2_graph.py:127`），把 run 置 `status="paused"` 并可被 Task 153 `--resume` 续跑（续跑时重置预算计数）。**不弱化质量 AutoHalt**：预算熔断与质量熔断是两条独立触发线。
- **预算计数归属 run，不归属全局单例**：`get_llm()` 是 `@lru_cache` 进程级单例，**不适合**挂 per-run 计数。预算计数器应随 run 生命周期创建/传递（如 `contextvars` 或显式传入的轻量计数器对象），避免测试间/多 run 串扰。
- **429 分类落点**：在 `call_llm._invoke`（`client.py:128-139`）包 `LLMError` **之前**先分类 litellm 抛出的限流异常（litellm 通常暴露 `RateLimitError` 或带 `status_code`/`Retry-After` 的异常），保留状态码与建议等待时长，供退避决策。分类后仍可包成 `LLMError` 的子类 `LLMRateLimitError`（保留 `retry_after`），使上层 `except LLMError` 不破坏现有契约。

### 首版参数口径

```python
# config.py Settings 新增（默认值保守、可 .env 覆盖）
llm_max_retries: int = 3               # call_llm 现默认 3，提为可配
llm_rate_limit_max_wait: float = 60.0  # 单次遵从 Retry-After 的上限（防恶意超长等待）
llm_run_call_budget: int = 0           # 0 = 不启用调用预算（默认关闭，长跑显式开启）
# 可选：llm_run_token_budget / llm_run_cost_budget（若能从 litellm 拿到用量）
```

- 429 退避：优先遵从 `Retry-After`（截断到 `llm_rate_limit_max_wait`），无该头则回退到现有指数退避 + jitter。
- 预算默认关闭（`llm_run_call_budget=0` → 行为与现状一致），长跑（阶段 D）显式设正值开启，避免误伤单测/短跑。

## In Scope（必须完成）

### 154a — 429 / Retry-After 感知退避
- [ ] 在 `call_llm._invoke`（`client.py:128-139`）包 `LLMError` 前**分类限流异常**：识别 litellm 的 429 / `RateLimitError` / `status_code == 429`，提取 `Retry-After`（秒）。新增 `LLMRateLimitError(LLMError)`（带 `retry_after: float | None`），置于 `exceptions.py`。
- [ ] `retry_with_backoff`（`retry.py:20`）支持"服务器建议等待时长"：当异常带 `retry_after` 时，等待 `min(retry_after, llm_rate_limit_max_wait)`，否则回退现有指数退避 + jitter（`retry.py:52-53`）。`LLMRateLimitError` 纳入 `retryable_exceptions`。
- [ ] `llm_max_retries` 提为 `config.Settings` 可配项，`call_llm` 默认值改从 settings 读（保持向后兼容：显式传参仍优先）。
- [ ] 遵守边界：限流分类只在 `llm/` 层；不改 Agent 调用签名；编程类异常（`TypeError`/`ValueError`/`KeyError`/`AttributeError`，`client.py:134`）仍直接抛、不重试。

### 154b — 单 run 全局 LLM 预算 + 熔断
- [ ] 引入 per-run LLM 调用计数（按 **Cross-Task Coordination「预算计数归属 run」**：`contextvars` 或显式计数器，非 `@lru_cache` 单例）。每次 `call_llm` 成功/失败计一次调用。
- [ ] `llm_run_call_budget > 0` 时，超预算抛 `LLMBudgetExceededError`（`SongyanError` 子类），在 `phase2_graph` 编排层捕获 → 复用 `_pause_run_for_auto_halt` 落库 `status="paused"` → 产出可观测报告（已用调用数、预算、停在第几章），**不静默继续也不无限烧**。
- [ ] 预算熔断可被 Task 153 `--resume` 续跑（续跑重置本次 run 的预算计数）。
- [ ] （可选子项）若 litellm 回调能拿到 token/成本用量，扩展 `llm_run_token_budget`/`llm_run_cost_budget`；拿不到则仅做调用次数预算，不硬造估算。
- [ ] 遵守边界：预算/熔断在 `llm/` + `phase2_graph` 编排层；不改治理与门禁；不与质量 AutoHalt 混用触发条件。

## Out of Scope（明确不做）

- 不改 Context Diet 2.0 的 **上下文 token 预算**（`context_total_budget` 等）——那是 prompt 装配预算，与本 Task 的**调用/成本预算**正交。
- 不做 run 级断点续跑本身（Task 153，本 Task 只保证熔断后可被其续跑）。
- 不做失败隔离策略（Task 155）。
- 不做多 provider 智能路由/降级切换（V7）。
- 不引入重量级依赖（如 tenacity）——沿用现有 `retry.py` 手写退避扩展即可。

## 接口契约

```python
# exceptions.py
class LLMRateLimitError(LLMError):
    """HTTP 429 / 限流；携带服务器建议的 Retry-After（秒）."""
    def __init__(self, message: str, retry_after: float | None = None, **kwargs) -> None: ...

class LLMBudgetExceededError(SongyanError):  # noqa: N818
    """单 run LLM 调用/预算耗尽的可观测熔断（保留已生成章节）."""
    def __init__(self, message: str, used_calls: int, budget: int, last_chapter: int) -> None: ...

# llm/client.py — 计数与预算校验（签名向后兼容：新增关键字，默认关闭预算）
async def call_llm(
    prompt: str, *,
    temperature: float = 0.7, max_tokens: int = 4096,
    max_retries: int | None = None,   # None -> settings.llm_max_retries
    timeout: int = 60,
) -> str:
    """限流感知退避 + per-run 调用计数；超 settings.llm_run_call_budget 抛 LLMBudgetExceededError."""
```

（最终签名以实现为准；核心：429/Retry-After 感知重试 + per-run 调用预算熔断，且默认关闭预算时行为与现状一致。）

## 测试要求

### Layer 2: 模块测试（Mock LLM / 注入异常）
- [ ] **429 分类**：Mock litellm 抛带 `status_code=429` + `Retry-After: 2` 的异常 → 被识别为 `LLMRateLimitError(retry_after=2)`，退避等待 ≈2s（可 patch sleep 断言等待时长），随后成功返回。
- [ ] **Retry-After 上限**：`Retry-After` 超 `llm_rate_limit_max_wait` 时被截断，不无限等待。
- [ ] **无 Retry-After 回退**：429 无该头时回退指数退避 + jitter（复用现有断言）。
- [ ] **编程异常不重试**：`TypeError` 等仍直接抛（`client.py:134` 契约不变）。
- [ ] **调用预算熔断**：`llm_run_call_budget=N`，第 N+1 次 `call_llm` 抛 `LLMBudgetExceededError`（含 used/budget）；`budget=0` 时永不熔断（默认行为不变）。
- [ ] **计数隔离**：两个独立 run 的预算计数互不串扰（验证非全局单例累加）。
- [ ] **编排层熔断落库**：`phase2_graph` 捕获 `LLMBudgetExceededError` → run `status="paused"` + 报告字段完整；质量 AutoHalt 触发路径不受影响。

### Layer 3: 注入式集成验证（阶段 C 出口佐证）
- [ ] **429 不级联 abort**：集成测试注入间歇性 429（前 K 次限流后成功），验证章节最终成功、run 不 abort（对比未加退避时会失败 abort）。
- [ ] **预算熔断可续跑**：设小预算触发熔断 → `status="paused"` → Task 153 `--resume` 续跑重置预算并续完（若 153 已合入；否则记录联跑计划）。
- [ ] 证据入 `docs/reports/`（注入序列、退避等待、熔断点、resume 续完结果）。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_154_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] 429/`Retry-After` 被识别并按建议退避；持续限流在退避耗尽前不冒泡成章节失败；编程异常仍不重试。
- [ ] 单 run 调用预算可配（默认关闭）；超预算触发**可观测熔断**（`paused` + 报告），非静默卡死/无限烧；计数按 run 隔离。
- [ ] Layer 3 证明注入 429 不再级联 abort，预算熔断可被 153 续跑（证据入 `docs/reports/`）。
- [ ] 不违反不可违背规则：限流/预算在 `llm/` + 编排层；不改治理与门禁；不与质量 AutoHalt 混触发；不引重量级依赖。
- [ ] 生成 `tasks/154-llm-rate-limit-and-budget-DONE.md`，含 429 分类落点、退避口径、预算参数来源、熔断/续跑联动、与"上下文预算"的区分说明。
- [ ] 更新 `tasks/V6-README.md`（154 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §3 阶段 C（Task 154 行 + 阶段 C 出口）；§1.4-T5（长跑红线，间接相关）
- 现有代码：`llm/client.py`（`call_llm`/`get_llm`/`_invoke` 异常包装 `:137-139`）、`llm/retry.py`（`retry_with_backoff`）、`exceptions.py`（`SongyanError`/`LLMError`/`AutoHaltException`）、`config.py`（`Settings`）、`workflows/phase2_graph.py`（`_pause_run_for_auto_halt` `:127`、`on_failure` 分支 `:495-500`）
- 区分说明：Context Diet 2.0 上下文 token 预算（`config.py:24` `context_total_budget`、`context_manager/`）—— **非**本 Task 的调用/成本预算
