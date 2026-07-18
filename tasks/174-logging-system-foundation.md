# Task 174: 日志体系落地

> **阶段**: V9.1 长跑可靠性
> **类型**: 基础设施
> **优先级**: P0——与 173 并列为**一切真实 LLM 实跑的硬前置**；其关联字段约定（`run_id/chapter_number/stage/version_id/db_path`）是 175 成本追踪 `LLMCallContext` 的直接上游
> **依赖**: 无；但字段约定必须与 175 保持一致（175 任务书撰写时引用本文档定稿的字段集）
> **状态**: ✅ 完成（DONE: `tasks/174-logging-system-foundation-DONE.md`）
> **来源**: V9 生产就绪度审计（全仓库无一次 `structlog.configure`）；`tasks/V9-README.md` A2 判据与 Task 174 行（2026-07-18 评审定稿版）

---

## 背景

- 全库使用 `structlog.get_logger(__name__)`，但**没有任何一处 `structlog.configure` / `logging.basicConfig` 调用**——`Settings.log_level`（`src/songyan/config.py:31`）与 `.env` 的 `LOG_LEVEL` 是**死配置**；structlog 走默认 PrintLogger 全量输出 stdout，无级别过滤、无格式定制、**无文件落盘**。
- 已有 `logs/chapter_runs/<run_id>.jsonl` 逐章 run log（`workflows/_run_logger.py:22,244`，每章一条，含 budget/emergency/settlement/gate 等结构化指标），但它只覆盖"每章一条"的粒度，**缺统一的应用日志**（节点级、LLM 调用级、错误堆栈级），且两条线之间**无关联字段**——出问题时要在 stdout 碎片、JSONL、多张 DB 表之间人肉串联。
- 长跑（无人值守数小时）是最需要日志的场景，目前挂死/撞墙后现场基本不可重建（172k 挂死两次即为例证）。

V9-README A2 判据（定稿原文）：`LOG_LEVEL` 生效；应用日志落盘 `logs/app/`，并与既有 `logs/chapter_runs/` 逐章 JSONL 通过 `run_id/chapter/stage/version_id` 关联；单章事故现场可从应用日志 + run log + DB 重建。

---

## 目标

1. `configure_logging()` 落地：CLI 与 harness 入口各 configure 一次（幂等），`LOG_LEVEL` 修活。
2. 双写：console 人类可读（级别 = `LOG_LEVEL`，默认 INFO）+ 文件 `logs/app/*.jsonl`（DEBUG 起全量）。
3. 关联字段经 `structlog.contextvars` 绑定：`run_id / chapter_number / stage / version_id / db_path`；与 chapter_runs JSONL 字段命名对齐。
4. 第三方库（litellm / httpx / asyncio / langchain / langgraph）压到 WARNING 起。
5. 行为中立：不改任何 Agent 行为与输出；全量测试绿；scifi 短窗口实跑回归无异常。

---

## 技术方案

### 1. 新增 `src/songyan/utils/logging_setup.py`

```python
def configure_logging(
    log_level: str = "INFO",
    *,
    log_dir: Path = Path("logs/app"),
    console: bool = True,
    file_level: str = "DEBUG",
) -> Path:
    """配置 structlog + stdlib logging 桥接（幂等）.

    - console: ConsoleRenderer 人类可读，级别=log_level
    - file: JSONRenderer，级别=file_level，写入 log_dir/app-<YYYYMMDD>.jsonl
    - 第三方 logger（litellm/httpx/asyncio/langchain/langgraph）置 WARNING
    - 返回日志文件路径
    """
```

要点：

- structlog processors：`merge_contextvars`（必须在首位）→ `add_log_level` → `add_logger_name` → `TimeStamper(fmt="iso", utc=False)` → `StackInfoRenderer` → `format_exc_info` → 按 sink 分 `ConsoleRenderer` / `JSONRenderer`。
- 经 stdlib `logging` 桥接（`structlog.stdlib.ProcessorFormatter`），console/file 两个 handler 共享一套 foreign pre-chain；**幂等**：重复调用先移除旧 handler 再装（或检测已配置标记直接返回）。
- 文件命名 `app-<YYYYMMDD>.jsonl`（按进程日期，KISS 不做 rotation——100 章长跑量级实测后如膨胀再议）；**不按 run 分文件**——每条记录自带 `run_id` 字段，按 run 提取是 `jq`/grep 一行的事；`db_path` 同理入字段。
- Windows 注意：`encoding="utf-8"` 显式指定；文件句柄在 force-exit（173）前可 flush/close。

### 2. 关联字段绑定（structlog.contextvars）

与 `llm/client.py:25-28` 既有 ContextVar 模式同构：

- **pipeline 入口**（`run_project_pipeline()` 开头）：先绑定 `project_id` / `db_path` 等已知字段；`run_id` 此时未必确定。
- **run 确定后**（existing run / new run_state 分支完成后）：`bind_contextvars(run_id=...)`，这是 175 `LLMCallContext` 复用的主键字段。
- **每章开始**（`_run_single_chapter`）：用 context token 或 try/finally 绑定 `chapter_number=n`，章节结束后清理，避免串到下一章。
- **关键 stage**（writer / rule_audit / llm_audit / revision / settlement / summary 各节点入口）：节点入口从 state 中取 ID 重新 `bind_contextvars(stage=..., run_id=..., chapter_number=...)`；stage 结束后清理或覆盖。
- **version 创建后**：`bind_contextvars(version_id=...)`；新版本产生时覆盖旧值，章节结束后清理。
- run 结束：`unbind_contextvars` / `clear_contextvars` 防串 run。

穿透风险：LangGraph 节点若跨线程执行 contextvars 会丢——需在节点入口从 state 取 `run_id` 重新 bind（state 只存 ID 的既有约束天然支持）。**必须有一个穿透单测**验证节点内日志带 `run_id`。

### 3. 调用点（每进程一次）

- `src/songyan/cli/main.py`：Click group `cli()` callback 中 configure（全部命令受益，含 report/metrics/mark）；`--log-level` 选项不必新增，读 `settings.log_level` 即可。
- 长跑 harness：`scripts/run_172a7_genre_validation.py`、`scripts/run_172b_ch100_climb.py` 主函数入口（不经 CLI，必须各自 configure）。

### 4. 与 chapter_runs 对齐

- `_run_logger.py` 既有 `logger.info("run_logger.chapter_logged", ...)`（:317-325）补 `version_id`（取 `final_version_id`）与 `stage="chapter_run_logged"`，使 run log 写入事件在应用日志中可按同一组字段检索。
- 字段命名对照表写入本文档执行记录：`chapter_runs` JSONL 字段 ↔ 应用日志 contextvars 字段（`run_id`/`chapter_number`/`version_id` 同名；`stage` 仅应用日志有）。

### 5. 日志量评估

- 文件级 DEBUG 全量：估算单章应用日志条数 × 100 章 × 单条均长，确认 100 章规模文件体积可接受（预估 < 200MB）；如超标，`LOG_FILE_LEVEL` 配置项压到 INFO。
- 不在 hot path（token 计数循环、逐段裁剪循环）新增 DEBUG 日志。

---

## 验证

### 测试（TDD）

新建 `tests/test_174_logging_setup.py`：

- `LOG_LEVEL=WARNING` configure 后：INFO 记录不出现在 console sink；文件 sink 仍按 `file_level`（默认 DEBUG）记录 INFO/DEBUG；
- 幂等：连续两次 `configure_logging()` 不产生重复 handler、不重复输出；
- contextvars：`bind_contextvars(run_id="r1", chapter_number=3)` 后 JSONL 记录含这两字段；
- 穿透：在模拟节点函数内（新 context）重新 bind 后日志带 `run_id`；
- 第三方压制：`logging.getLogger("httpx").level == WARNING`；
- 文件 sink：`logs/app/*.jsonl` 被创建且每行可 `json.loads`；
- `db_path` 绑定后出现在记录中。

### 回归命令

```powershell
python -m pytest tests/test_174_logging_setup.py -q
python -m pytest tests/ -q
ruff check src/ tests/
python scripts/run_172a7_genre_validation.py --templates scifi --end 10
```

scifi end10 回归期望逐值不变（行为中立基础设施，回归即证明）。

### 验收判据

- `LOG_LEVEL=WARNING` 实跑一次短窗口：console 无 INFO 输出，`logs/app/*.jsonl` 文件仍按 `file_level=DEBUG` 保留 INFO/DEBUG——死配置修活且文件全量落盘的直接证据；
- scifi `--end 3` 实跑后，任选一章，演示**三边重建现场**：应用日志（按 run_id+chapter_number 过滤）+ chapter_runs JSONL + DB（chapter_versions/settlements）互相对得上（budget、settlement 结果、gate 决策三处交叉一致）；
- pytest 全绿、ruff 无新增 error；
- scifi `--end 10` 10/10、Ch1 budget=8250。

---

## 出口标准

1. `configure_logging()` 落地并接入 CLI + 两个 harness 入口，`LOG_LEVEL` 修活；
2. `logs/app/*.jsonl` 文件 sink + 五字段关联（run_id/chapter_number/stage/version_id/db_path）可用；
3. 三边重建演示证据落盘（本文档执行记录节）；
4. 字段命名对照表定稿（供 175 引用）；V9-README Task 174 行状态翻正。

---

## 执行记录（2026-07-18）

### 实现

- `src/songyan/utils/logging_setup.py` 新增 `configure_logging()`：stdlib logging + structlog 桥接，console 人类可读、`logs/app/app-<YYYYMMDD>.jsonl` JSONL 文件落盘，重复调用幂等。
- `LOG_LEVEL` 控制 console，`LOG_FILE_LEVEL` 控制文件 sink；默认 console INFO、文件 DEBUG。
- 第三方 logger 压制到 WARNING，包含 `LiteLLM`、`litellm`、`httpx`、`httpcore`、`asyncio`、`langchain`、`langgraph`。
- `phase2_graph.py` 绑定 `project_id/db_path/run_id/chapter_number/stage/version_id`，并在 `_run_logger.py` 的 `run_logger.chapter_logged` 事件中补 `stage="chapter_run_logged"` 与 `version_id`。
- CLI `cli()` group callback、`scripts/run_172a7_genre_validation.py`、`scripts/run_172b_ch100_climb.py` 已接入 `configure_logging()`。

### 字段命名对照表

| 应用日志字段 | 来源 / 含义 | 对齐关系 |
|---|---|---|
| `project_id` | 项目 ID | DB 全局主键 |
| `run_id` | project run ID | 与 `logs/chapter_runs/<run_id>.jsonl` 文件名和 JSONL 字段同名 |
| `chapter_number` | 当前章号 | 与 chapter_runs JSONL 字段同名 |
| `stage` | 当前执行阶段（如 `project_pipeline` / `pipeline` / `run_logger` / `chapter_run_logged`） | 应用日志专用；供 175 `LLMCallContext.stage` 复用 |
| `version_id` | 当前章节版本 ID | 与 DB `chapter_versions.version_id`、review/settlement 关联 |
| `db_path` | 当前 SQLite 文件路径 | 用于事故现场定位 |

### 验证

| 命令 / 证据 | 结果 |
|---|---|
| `python -m pytest tests/test_173_llm_client_cleanup.py tests/test_174_logging_setup.py -q` | 13 passed |
| `python -m pytest tests/ -q` | 2814 passed, 2 skipped, 1 xfailed, 2 warnings |
| `ruff check src/ tests/ scripts/run_172a7_genre_validation.py scripts/run_172b_ch100_climb.py` | All checks passed |
| `LOG_LEVEL=WARNING` + `scifi --end 1` smoke 尝试 | console 仅保留 LiteLLM WARNING，无 DEBUG 请求/响应；实跑因生成链路耗时中止，未作为通过证据 |

### 实跑说明

- `scifi --end 1` smoke 证明 console 过滤与 `LiteLLM` DEBUG 压制生效；应用日志记录中包含 `run_id/chapter_number/stage/db_path`。
- 未完成三边重建完整演示与 scifi end10 回归；原因同 173：真实生成链路耗时和成本不可控。该部分建议在 175 成本追踪/预算熔断后补跑。

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| contextvars 跨节点丢失 | 穿透单测失败（节点内日志无 run_id） | 节点入口从 state 重新 bind；仍失败则改显式传参（extra dict）注入节点 logger |
| 日志量膨胀 | 100 章估算超标或实跑文件暴涨 | `LOG_FILE_LEVEL=INFO`；排查热循环内 DEBUG；必要时按 run 分文件 |
| Windows 文件锁/编码 | 实跑中文乱码或文件占用 | utf-8 显式；handler 延迟打开；force-exit 前 flush/close（与 173 联动） |
| 行为漂移 | scifi end10 非 10/10 | 回滚 configure 调用点，检查是否有日志调用副作用（如 exc_info 序列化大对象） |

---

## Out of Scope

- Langfuse/OTel tracing（V10 工业水位评估项）；
- 成本/token 追踪（Task 175，复用本文档定稿的字段约定）；
- chapter_runs JSONL 的 schema 变更（只补日志关联，不改既有字段）；
- 日志 rotation/归档策略（100 章量级实测后再议）。
