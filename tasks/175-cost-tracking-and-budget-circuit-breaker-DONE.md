# Task 175 DONE: 成本追踪与预算熔断

> **完成时间**: 2026-07-19
> **阶段**: V9.1 长跑可靠性
> **状态**: ✅ 完成（阶段 A-D 全部闭环）
> **任务书**: `tasks/175-cost-tracking-and-budget-circuit-breaker.md`（含阶段 A-C 逐阶段提交链与决策记录）

---

## 交付内容

**阶段 A-C（代码，四阶段双 review + 终审全通过）**

- `llm_call_usage` 表（19 列 + 2 索引，schema.sql / `_EXPECTED_TABLES` / `init_schema()` / `run_migrations()` / repo 五处同步入口）+ `LlmCallUsageRepository`（record 全捕获容错 / sum / aggregate / source_stats）。
- `call_llm` 单一漏斗拦截：`LLMCallContext` 读 174 字段链；usage 三级提取（`usage_metadata` → `response_metadata` → estimate）；token/cost 双来源标记；cached/miss tokens；每次重试尝试独立一行（含失败/取消行）；15 处 agent 归因绑定 + AST 静态防漏测试；telemetry 三层容错，永不阻断生成。
- `run_cost_budget`（`SONGYAN_RUN_COST_BUDGET` env alias）：前置 `>=` / 后置 `>` 双检查熔断，接入既有 `LLMBudgetExceededError` pause/resume 路径；与 `llm_run_call_budget` 调用次数预算独立。成本累计**独立于 telemetry 写库成败**。
- `ProjectRunResult.total_cost` 与 `project_runs.total_cost` 双接线（含 pause 路径刷新、短路分支透传、刷新失败保留历史值）；`songyan report` 成本视图（总额/每章均/per agent Top N/双估算占比/每章成本表；取数失败与良性无数据可区分）。
- 成本口径：统一 **CNY pricing estimate**（LiteLLM `response_cost` 为 USD 且默认不透传，未接币种转换前禁止写入 `cost_cny`）。

**阶段 D（实跑验收，2026-07-19）**

- **熔断实证**（`.tmp/probe_175_budget.py`，临时库，scifi `--end 2`）：¥0.05 预算在 ¥0.0514 处熔断——run=**paused**、`budget_exceeded` 日志含 `used_cost/budget_cost/last_chapter`、Ch1 under_review 保留；提额 ¥2 resume → Ch1 accepted →（Ch2 瞬时质量门，按设计 AutoHalt）→ 再 resume → run=**completed**。成本跨 3 进程连续：0.0514 → 0.2519 → 0.3647 = usage 合计逐分吻合。
- **scifi `--end 10` 回归**（`SONGYAN_RUN_COST_BUDGET=20`）：**10/10 accepted、0 halt**、overdue=0、budget 峰值 0.8325（Ch1 total_budget=8250 公式不变）、CED 3.14（V8 同标）；usage **151 行全部 `token_source='response'`（estimate 占比 0% < 20%）**、失败行 0、agent 归因 8/8 无 unknown；run 总成本 **¥0.886**（≈¥0.089/章），`project_runs.total_cost` 与 usage 合计逐分一致；report 成本视图全要素渲染正确。
- **T9=1 分析**：Ch4 `countdown_increase`（Ch1"二十分钟"vs Ch4"三十七天"，两个不同倒计时），diagnostic 级内容启发式误报倾向，与本 Task 改动无关，非系统性，记录在案。

## D 阶段发现并修复的两个生产缺陷（单测全绿、生产失效）

1. **成本累计器跨 LangGraph 节点失效**（`22c1052`）：`_llm_run_cost_cny` ContextVar 写入发生在节点 task 的 context 副本，按节点重置——首跑熔断完全未触发（¥0.217 > ¥0.05 仍 completed）。修复：run 上下文下预算检查改为 **DB 权威**（前置 `sum_cost_for_run`，后置 = 前置合计 + 本次成本），非 run 上下文保持累计器路径。TDD 复现红→绿。
2. **熔断异常被 phase1 宽捕获包装**（`0b07e9d`）：`run_chapter_pipeline` 的 `except Exception` 把 `LLMBudgetExceededError` 包装成章节失败，run 变 failed 而非 paused。修复：phase1 原样 re-raise，传播到 phase2 的 pause 路径。TDD 红→绿。

## 联动成果（173/174 挂起项一并闭环）

- **173**：D2 进程结果落盘后挂死 50+ 分钟（172k 复现）→ py-spy 线程栈确证根因为 sqlite `AsyncSqliteSaver` 连接泄漏（非 daemon aiosqlite worker，经模块级缓存编译图持有，`reset_checkpointer()` 此前仅测试路径调用）→ 真修（pipeline finally 对称关闭 checkpointer + LLM client）后 sqlite 模式 **2.5s 自然退出**。173 翻 ✅。
- **174**：用 D2 实跑完成三边重建演示（run `run-948c136b` Ch4）：应用日志 ↔ chapter_runs JSONL ↔ DB 在 budget（0.5204444444444445 逐分一致）/ settlement / gate 决策 / 版本链四维度交叉一致。174 翻 ✅。

## 验证

| 命令 / 证据 | 结果 |
|---|---|
| `python -m pytest tests/ -q` | **2882 passed, 2 skipped, 1 xfailed** |
| `ruff check src/ tests/` | All checks passed |
| 熔断实证（pause→resume） | run paused → completed，成本跨 3 进程连续 |
| scifi `--end 10`（`.tmp/175_scifi_end10.json`） | 10/10、0 halt、overdue=0、budget 峰值 0.8325 |
| report 成本视图（`logs/reports/report-run-948c136b.md`） | 总额/每章均/per agent/双占比/每章成本表正确 |
| 173 自然退出计时 | sqlite 模式 2.5s + memory 模式四次 1.2-1.9s，均 ≤60s |

## 说明

- 既有 `_llm_call_count` 调用次数预算与成本累计器同为 ContextVar，存在相同的跨节点重置局限（默认 0 不启用）；如需启用次数预算，复用 DB 权威模式另行修复，已记录于 `client.py` 注释。
- `source_stats_for_run` 的估算占比只统计 `success = 1` 调用（失败/取消尝试不计入，防止把瞬态失败率误读为 usage 提取失败率）。
- dev 库 `songyan.db` 已跑 `init_schema` 获得遥测表（幂等，`verify_schema` 无 missing）。
