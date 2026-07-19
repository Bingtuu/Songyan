# Task 175: 成本追踪与预算熔断

> **阶段**: V9.1 长跑可靠性
> **类型**: 基础设施（可观测性 + 失控防护）
> **优先级**: P0——**长窗口与高成本实跑的前置**（V9-README 执行纪律：进入多轮标定或 187 Ch100 前必须具备成本追踪与预算熔断）；同时是 173/174 挂起实跑验收的解锁条件
> **依赖**: 174 完成（关联字段 `run_id/chapter_number/stage/version_id/db_path/project_id` 已定稿并经 contextvars 绑定，本 Task 直接消费）
> **状态**: 🔄 进行中（阶段 A-C 代码完成：落库/拦截/熔断/report 视图全上线，review follow-up `f0c607e` 已修，全量 2872 passed；阶段 D 实跑验收待 API 预算确认）
> **来源**: V9 生产就绪度审计（成本追踪为零，`phase2_graph.py` 躺 `total_cost=0.0 # TODO`）；外部调研（Sudowrite 第一用户痛点 = 成本黑盒；无人值守失控防护共识清单）；`tasks/V9-README.md` Task 175 行

---

## 背景

- **成本追踪为零**：LLM 响应的 usage（`prompt_tokens/completion_tokens`）全代码库无人读取；`ProjectRunResult.total_cost` 硬编码 `0.0`（`phase2_graph.py:1060`，TODO 自 Task 025 遗留）；`utils/cost_estimator.py` 功能完整（DeepSeek 定价表、tiktoken 计数、`estimate_cost_from_tokens`）但只有 `scripts/run_batched_chapters.py` 一个脚本在用，生产路径未接。
- **失控防护缺花钱维度**：既有 `llm_run_call_budget`（`config.py:24`）只限调用**次数**，不限金额；一次修订循环失控烧的是 token 数倍的输出成本。
- **拦截点理想**：当前 `rg "call_llm\(" src/songyan` 显示所有 Agent LLM 调用点均经 `call_llm()` 单一漏斗；唯一的 `ainvoke` 直调用是 phase1_graph 的 LangGraph graph 调用，非 LLM 调用。任务验收以“所有 `call_llm()` 调用点均可归因/计费”为准，不固定写死调用点数量，避免后续新增调用导致文档过期。
- **字段上游已就绪**：174 把 `project_id/db_path` 绑在 pipeline 入口、`run_id` 绑在 run 确定后、`chapter_number/stage/version_id` 绑在章级，经 `structlog.contextvars` 传播——usage 落库可直接读取，不需要新建双轨绑定。

一个 Task 完成四阶段（A 落库 → B 熔断 → C 视图 → D 实跑验收）：共享同一拦截点与字段链，拆成多个 Task 只会重复搭 instrumentation；各阶段独立可测、独立可提交。

---

## 目标

1. 每次 LLM 调用（含每次重试尝试）落一行 `llm_call_usage`：run/chapter/agent/stage/model/tokens/cost/latency/retry_attempt/success/error，token 来源标记（response 精确 token / estimate 估算 token）与 cost 来源标记（当前 CNY pricing estimate；provider cost 字段保留给未来明确币种来源）。
2. run 级成本预算 `run_cost_budget`（默认 0=不限）：调用前检查历史累计，调用成功后累加并立即二次检查；累计超限抛 `LLMBudgetExceededError`，走既有优雅停跑路径（pause + 保留已生成章 + 可 resume）；与 `llm_run_call_budget` 调用次数预算相互独立。
3. `ProjectRunResult.total_cost` 与 `project_runs.total_cost` 均接真实累计值；`songyan report` 含成本视图（per run / per chapter / per agent）。
4. **实跑验收（本 Task 的 D 阶段同时解锁 173/174 挂起项）**：带成本上限的 scifi `--end 10` 回归 + 173 两次自然退出 + 174 三边重建演示。

---

## 技术方案

### 阶段 A：usage 提取与落库

**1. 新表 `_migrate_llm_call_usage`**（`db/migrations.py`，仿 `_migrate_run_db_metrics` 模式）：

```sql
CREATE TABLE IF NOT EXISTS llm_call_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,                -- 非 run 上下文（脚本/测试）为 NULL
    project_id TEXT,
    chapter_number INTEGER,
    agent TEXT,                 -- writer / llm_auditor / ...；无绑定上下文时 'unknown'
    stage TEXT,                 -- 174 章节编排级 stage
    version_id TEXT,            -- 可为 NULL（writer 调用发生在版本创建前，为上一版本或空）
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cost_cny REAL NOT NULL DEFAULT 0.0,
    token_source TEXT NOT NULL, -- 'response' | 'estimate'
    cost_source TEXT NOT NULL,  -- 'provider_cost' | 'pricing_estimate'
    cached_tokens INTEGER,
    cache_miss_tokens INTEGER,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    retry_attempt INTEGER NOT NULL DEFAULT 0,  -- 0=首次；每次重试尝试独立一行
    success INTEGER NOT NULL DEFAULT 1,
    error TEXT,                 -- 失败尝试的异常摘要
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_llm_call_usage_run ON llm_call_usage(run_id);
CREATE INDEX IF NOT EXISTS idx_llm_call_usage_run_chapter ON llm_call_usage(run_id, chapter_number);
```

同步入口必须覆盖：`src/songyan/db/schema.sql`（冷启动完整 schema）、`src/songyan/db/migrations.py` 的 `_EXPECTED_TABLES`（`verify_schema()` 校验注册表）、`init_schema()`、`run_migrations()`，并补 repository/migration 测试，保证新库和旧库迁移路径都能得到 `llm_call_usage`。

**2. 新 repository `db/llm_call_usage_repo.py`**：`record(...)`（单行写入，**失败只 warning 不阻断生成**——telemetry 丢失可接受，生成不可断）、`sum_cost_for_run(run_id)`、`aggregate_for_run(run_id)`（按 chapter/agent 分组聚合）。

**3. `llm/client.py` 拦截**：

- 新增 `LLMCallContext` dataclass + `_current_call_context()`：从 `structlog.contextvars.get_contextvars()` 读 `run_id/project_id/chapter_number/stage/version_id/db_path/agent` 组装——**复用 174 字段链，不建双轨 ContextVar**（V9-README 的"LLMCallContext/ContextVar 传递"意图是调用上下文可追溯，读取侧实现即可；写入侧只有 `agent` 需新增绑定）。
- `_invoke()` 内（`client.py:200-218`）按尝试记录：成功时先取 `response.usage_metadata`（langchain-core 标准：`input_tokens/output_tokens`），缺失取 `response.response_metadata` 的 token_usage（litellm 风格），仍缺失回退文本估算并标 `token_source='estimate'`；成本统一用 `cost_estimator.estimate_cost_from_tokens(...)` / `estimate_cost(...)` 计算 CNY，并标 `cost_source='pricing_estimate'`。`llm_call_usage.cost_source='provider_cost'` 作为未来扩展保留，但当前 `ChatLiteLLM` 默认不透传 LiteLLM `response_cost`，且 LiteLLM `response_cost` 为 USD，未接明确币种转换前禁止写入 `cost_cny`。DeepSeek cache hit/miss 可从 `prompt_tokens_details.cached_tokens` / `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens` 提取到 `cached_tokens/cache_miss_tokens`；不得把 response token 或 USD cost 误写成“精确人民币金额”。
- 失败尝试记 `success=0` + `error` + 零 usage。`latency_ms` 用 `time.monotonic()` 夹取。`retry_attempt` 优先通过给 `retry_with_backoff()` 增加可选 `on_attempt` / `attempt_index` 回调透传，避免闭包计数在失败/最终失败语义上漂移；退而求其次才使用 `_invoke` 内部闭包计数。
- **agent 归因**：所有 `call_llm()` 调用点所在 Agent 函数入口各加一行 `bind_contextvars(agent="<name>")`（覆盖语义，下一个 Agent 入口自然覆盖前值，无泄漏窗口）。同时新增静态测试扫描 `src/songyan/agents/**` 中所有 `call_llm(`，确认调用前所在函数或其入口具备 agent 绑定，防止后续新增调用漏归因。

### 阶段 B：run 级累计与熔断

**1. 累计器**：`client.py` 新增 `_llm_run_cost_cny: ContextVar[float]`（镜像既有 `_llm_call_count` 模式）；每次成功调用计算出成本后立即累加。**成本累计必须独立于 telemetry 写库是否成功**：即使 `repo.record(...)` 抛异常被 warning 吞掉，`_llm_run_cost_cny` 也必须已增加，避免 telemetry 故障绕过预算熔断。

**2. resume 安全**：run 确定后（`phase2_graph.py` 三个 run_id 绑定分支，174 已落点）调用 `init_run_cost_from_db(run_id, fallback=run_state.total_cost)`——从 `sum_cost_for_run` 初始化累计器，新 run 为 0，resume run 为历史累计；返回值必须同步写入 `run_state.total_cost`，保证章节循环最早的 `_save_run_state(current_chapter)` 不会继续持久化旧值。DB 读取失败时使用 fallback 保留已持久化值。

**3. 配置**：`config.py` 新增 `run_cost_budget: float = Field(default=0.0, validation_alias=AliasChoices("SONGYAN_RUN_COST_BUDGET", "RUN_COST_BUDGET"))`，保证文档命令中的 `SONGYAN_RUN_COST_BUDGET` 真实生效；README/.env.example 同步该变量。

**4. 熔断**：`call_llm` 前置检查（紧挨既有调用次数预算检查 `client.py:185-196`）：

```python
budget = settings.run_cost_budget
if budget > 0:
    used = _llm_run_cost_cny.get(0.0)
    if used >= budget:
        raise LLMBudgetExceededError(
            message=f"单 run 成本预算耗尽（¥{budget:.2f}），已用 ¥{used:.4f}",
            used_calls=_llm_call_count.get(0),
            budget=0,  # 次数预算语义不变；成本字段走新 kwargs
            last_chapter=_llm_budget_last_chapter.get(0),
            used_cost=used,
            budget_cost=budget,
        )
```

调用成功后必须做**后置二次检查**：

```python
_llm_run_cost_cny.set(used + call_cost)
if budget > 0 and _llm_run_cost_cny.get() > budget:
    raise LLMBudgetExceededError(
        message=f"单 run 成本预算超限（¥{budget:.2f}），已用 ¥{_llm_run_cost_cny.get():.4f}",
        used_calls=_llm_call_count.get(0),
        budget=0,
        last_chapter=_llm_budget_last_chapter.get(0),
        used_cost=_llm_run_cost_cny.get(),
        budget_cost=budget,
    )
```

这样预算语义是“保护性硬上限”：调用前不允许已超限继续调用；单次昂贵调用若把预算打穿，会在该次调用返回后立即暂停，不继续进入后续 LLM 调用链。已产生的该次响应是否写入业务库由调用点异常传播决定；当前 `call_llm` 抛出后不会返回文本给 Agent，因此不会继续进入正文/结算写入。

`LLMBudgetExceededError`（`exceptions.py:42-55`）扩展可选字段 `used_cost: float | None = None`、`budget_cost: float | None = None`（向后兼容，既有构造调用不改）。既有处理路径（`phase2_graph.py:853` 章循环 pause + `:1329` 单章捕获）天然接住：run 置 paused、已生成章保留、`--resume` 可续。

`phase2_graph.py` 的 `project_pipeline.budget_exceeded` 日志同步输出 `used_cost/budget_cost`，否则暂停原因仍只有调用次数上下文。

**5. `total_cost` 接线**：`phase2_graph.py:1060` 替换为 `await LLMCallUsageRepository().sum_cost_for_run(run_id)`（run_id 为 None 时 0.0）。同时在所有 `_persist_run_progress()` 前，尤其 `LLMBudgetExceededError` pause 路径，先刷新 `run_state.total_cost`，保证 `project_runs.total_cost` 与 `ProjectRunResult.total_cost` 一致；旧 run 无用量行时保持 0.0。

### 阶段 C：report 成本视图

`cli/main.py:583` `report_cmd` 增加成本段（数据源 `aggregate_for_run` + `source_stats_for_run`）：run 总成本（¥）、章节数与每章均成本、per agent 成本分布（top N）、成功调用数 / 全部尝试行、`token_source='estimate'` 占比与 `cost_source='pricing_estimate'` 占比（估算占比高 = usage/成本提取需要修的早期信号）。完全无 usage 行的旧 run 显示"无成本数据"不报错；只有失败/取消尝试时仍必须渲染失败遥测明细，不得伪装成旧 run。

### 阶段 D：实跑验收（与 173/174 挂起项合并执行）

1. **熔断实证**：临时库（`.tmp/175_budget_probe.db`）+ 极低预算（如 `SONGYAN_RUN_COST_BUDGET=0.05`）跑 scifi `--end 2`：验证 run 优雅停跑（status=paused、已生成章保留、错误信息含成本明细）→ `--resume` 提高预算后续跑完成。
2. **scifi `--end 10` 回归**（设合理预算上限，如 ¥20）：10/10 accepted、Ch1 budget=8250 逐值不变、`llm_call_usage` 行数与调用次数吻合、estimate 占比低（<20%）、report 成本视图输出合理。
3. **173 挂起项**：回归实跑收尾时观察进程 ≤60s 自然退出 ×2（第一次 end10、第二次 resume 续跑收尾），结果补录 `tasks/173-interpreter-exit-hang-fix-DONE.md` 后状态翻 ✅。
4. **174 挂起项**：用该 run 做一次三边重建演示（应用日志按 run_id+chapter 过滤 ↔ chapter_runs JSONL ↔ DB chapter_versions/settlements 三处交叉一致），证据补录 `tasks/174-logging-system-foundation-DONE.md` 后状态翻 ✅。

---

## 验证

### 测试（TDD）

新建 `tests/test_175_cost_tracking.py`：

- response 带 `usage_metadata` → 落库 `token_source='response'`、tokens 来自 response、`cost_source='pricing_estimate'`；
- response_metadata 带 LiteLLM `response_cost` → 当前 CNY 口径下忽略该 USD 字段，仍按本地 CNY pricing estimate 计算；
- response 带 cache hit/miss details → `cached_tokens/cache_miss_tokens` 正确落库；
- response 无 usage → estimate fallback，`token_source='estimate'`、`cost_source='pricing_estimate'`；
- 重试语义：首次失败 + 二次成功 → 两行（attempt 0 `success=0`+error / attempt 1 `success=1`）；
- agent 归因：`bind_contextvars(agent="writer")` 后落库行 `agent='writer'`；无绑定 → `'unknown'`；
- agent 静态覆盖：扫描所有 `src/songyan/agents/**` 的 `call_llm(` 调用点，确认具备 agent 绑定；
- 熔断前置：预算 ¥0.01 + 预置累计 → `LLMBudgetExceededError`，`used_cost/budget_cost` 字段正确；
- 熔断后置：单次调用成本把预算打穿 → `call_llm` 在累加后抛 `LLMBudgetExceededError`，且不返回文本给 Agent；
- resume 初始化：DB 预置历史行 → `init_run_cost_from_db` 后累计器从历史值继续，且 `run_state.total_cost` 在最早 `_save_run_state` 前同步；
- **repo.record 抛异常时 `call_llm` 正常返回**（telemetry 不阻断生成），但 `_llm_run_cost_cny` 已累计本次成本；
- `total_cost` 接线：构造 run 用量行后 `ProjectRunResult.total_cost` 与 `project_runs.total_cost` 均等于 DB 合计（或拆为 sum 查询单测 + 接线点断言）；
- `aggregate_for_run` 分组聚合正确性；只有失败/取消尝试时 report 仍渲染遥测，不显示"无成本数据"。

### 回归命令

```powershell
python -m pytest tests/test_175_cost_tracking.py tests/test_173_llm_client_cleanup.py tests/test_174_logging_setup.py -q
python -m pytest tests/ -q
ruff check src/ tests/
python scripts/run_172a7_genre_validation.py --templates scifi --end 10   # 阶段 D，带 run_cost_budget
```

### 验收判据

- pytest 全绿、ruff 无新增 error；
- 熔断实证：低预算 run 优雅停跑 + resume 续跑完成，证据落盘；
- scifi `--end 10` 10/10、Ch1 budget=8250（旧行为逐值不变）；`llm_call_usage` 落库完整、`token_source='estimate'` 占比 <20%；report 成本视图可用；
- 173 两次自然退出、174 三边重建证据分别补录 DONE 并翻 ✅（V9-README A2/A5 注记同步清除）。

---

## 出口标准

1. `llm_call_usage` 表 + repository + 所有 `call_llm()` 调用点 agent 归因落地，全量测试绿；
2. `run_cost_budget` 熔断接入既有 `LLMBudgetExceededError` 路径，次数/成本双预算独立；
3. `total_cost` 与 report 成本视图可用；
4. 阶段 D 四项实跑证据全部落盘，173/174 状态翻 ✅；
5. 本 Task 执行记录补录本文档，V9-README Task 175 行翻正。

---

## 执行记录（2026-07-18，阶段 A-C）

### 提交链

| 阶段 | 提交 | 内容 |
|---|---|---|
| A1 | `3d72774` + `407ecbc` | `llm_call_usage` 表（19 列+2 索引，schema.sql/migrations/_EXPECTED_TABLES/init_schema/run_migrations 五处同步）+ repo（record 全捕获容错 / sum / aggregate）；review 3 Minor 修复（NULL 分组语义、运行时白名单、索引断言） |
| A2 | `9caa1c5` + `6a92fea` | call_llm 拦截（LLMCallContext 读 174 字段链、usage 三级提取、双 source 标记、cached/miss、按尝试落库、retry on_attempt 回调）+ 15 处 agent 绑定 + AST 静态测试；review 2 Important（conftest 遥测 mute 隔离、取消尝试落行）+ 6 Minor 修复 |
| B | `324c028` + `8a5c799` | `_llm_run_cost_cny` 累计器（独立于 telemetry 成败，attempt_state 回传外层 context——`asyncio.wait_for` Task 副本不回传 ContextVar 写入的实证修正）、`init_run_cost_from_db`、前置`>=`/后置`>` 双检查熔断、`LLMBudgetExceededError` 扩展 used_cost/budget_cost、total_cost 双接线（含 pause 路径）、`_usage.py` 抽离；review 2 Important（短路分支 total_cost 透传、refresh 失败保留持久值）+ 4 顺手项修复 |
| C | `f2982f8` | `source_stats_for_run` 查询 + `evals/cost_report.py::render_cost_section` 纯函数 + `report_cmd` 接线（宽 except 降级）；测试绕开 tests/cli 既有坑 |
| Review follow-up | `f0c607e` | 修复代码 review 发现：LiteLLM `response_cost` USD 不再写入 `cost_cny`，当前统一 CNY pricing estimate；report 增 `total_usage_rows`，失败/取消尝试不再伪装成旧 run 无数据；resume 初始化返回值同步到 `run_state.total_cost`，防早期 `_save_run_state` 写旧值 |

### 验证

- review follow-up 前全量 `python -m pytest tests/ -q`：**2869 passed, 2 skipped, 1 xfailed**；`ruff check src/ tests/` 全绿
- 评审：A1/A2/B/C 规格符合性 + 代码质量双 review 全通过（A2/C 修复后 Approved；B 修复后免复审）；终审（`agent-19`）结论 Yes——6 条 Minor 中唯一影响阶段 D 判据的"失败行污染 estimate 占比"已修（`source_stats_for_run` 加 `success = 1` 过滤，专测锁定）
- review follow-up 聚焦验证：`python -m pytest tests/test_175_cost_tracking.py tests/db/test_llm_call_usage_repo.py tests/test_llm_client.py -q` → **65 passed**；`python -m pytest tests/ -q` → **2872 passed, 2 skipped, 1 xfailed**；`ruff check src/ tests/` 全绿；`git diff --check` 仅 LF/CRLF 提示

### 关键偏差与决策（已记录）

- `_invoke` 内经 `attempt_state` 回传成本到外层 context 累计（`asyncio.wait_for` Task 副本不回传 ContextVar 写入，红测暴露后修正）
- 当前成本金额口径统一为 CNY pricing estimate；LiteLLM `response_cost` 是 USD 且当前 `ChatLiteLLM` 默认不透传该字段，未接币种转换前不得写入 `cost_cny`
- pipeline 三处 sum 查询容错回退（`_sum_run_cost_or_none` 失败 None 保留既有值）：陈旧 dev 库无新表时不杀 run，与"telemetry 丢失可接受"哲学一致；独立验证确认该路径在 parent commit 同样失败（环境性，非本任务回归）
- 「每章均成本」= run 总成本（含 run 级调用）/章节数，run 级调用次数单列注释
- 既有 quirk 未动：`report_cmd -o` 只用 `output.parent`（文件名始终 `report-<run_id>.md`）

### 待办

- 阶段 D 实跑验收（熔断实证 + scifi end10 + 173/174 挂起项补跑）：待 API 预算确认
- dev 库 `songyan.db` 需跑一次 `init_schema` 获得遥测表（幂等）

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| usage 提取失败（langchain-litellm 不回传 usage_metadata） | 实跑 estimate 占比 >20% | 检查 `response.response_metadata` 的 litellm 原始 payload；仍缺则接受 estimate 为主口径并在 DONE 标注，不深改依赖库 |
| DB 写入拖慢生成 | 单章耗时显著增加 | record 改批量缓冲（章末 flush）或 `fire-and-forget` 任务；保持不阻断语义 |
| 熔断误伤长修订章 | 合理 run 被低成本预算停跑 | 预算语义是"保护性暂停"不是失败——resume 提额即续；标定时按实测每章成本设上限（参考值写入 185 任务书） |
| contextvars 在重试/嵌套调用中错位 | agent/stage 归因错乱 | agent 绑定改为 try/finally token 复位（`reset_contextvars`）精细化 |
| 行为漂移 | scifi end10 非 10/10 或 Ch1 budget ≠ 8250 | 回滚拦截层，检查记录路径副作用（如 tiktoken 大文本计数耗时、record 写锁） |

---

## Out of Scope

- LiteLLM proxy 化（fallback 链/分类重试/缓存）、Langfuse tracing、LLM 幂等缓存——V10 工业水位评估项；
- 定价表配置化（`PRICING` 为 2025-05 DeepSeek 价格，价格漂移通过改代码更新；自用场景不做 env 覆盖层）；
- per-day/per-user 预算（当前只有 per-run；自用单用户足够）；
- 修订停滞检测（调研清单项，与本轮修订轮数上限互补，后续按需立项）；
- prompt/response 内容落库（只记 token 数与成本，不记正文——避免日志库膨胀与内容扩散）。
