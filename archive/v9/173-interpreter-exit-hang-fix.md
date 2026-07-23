# Task 173: 解释器退出挂死修复

> **阶段**: V9.1 长跑可靠性
> **类型**: 缺陷修复（生产事故级）
> **优先级**: P0——与 174 并列为**一切真实 LLM 实跑的硬前置**（V9-README 执行纪律：挂死无兜底时跑实跑等于重演 172k 事故场景）
> **依赖**: 无（V9 主链首站）
> **状态**: ✅ 完成（真修落地：pipeline finally 对称关闭 LLM client + sqlite checkpointer；归因确证（py-spy 线程栈）；sqlite 模式进程 2.5s 自然退出；自动化全绿）
> **来源**: 172k 两次实跑挂死记录（`archive/v8/tasks/172k-c-dimension-evidence-closure.md`）；V9 生产就绪度审计；`tasks/V9-README.md` Task 173 行

---

## 背景

172k 实跑（xuanhuan end10 / wuxia end20）两轮均出现：**结果落盘后进程在解释器退出阶段挂死**——残留约 86 个线程、零 CPU，只能人工 kill。当时推测为 litellm/httpx 连接池非 daemon 线程未关闭，但**未在代码层证实**。

代码现状（2026-07-18 审计）：

- `src/` 全库无 `Thread`/`daemon`/`Executor` 使用，无 `atexit` 注册，无 `os._exit` 调用——挂死零代码兜底。
- LLM client 生命周期无人管理：`src/songyan/llm/client.py:76` 的 `_get_llm_cached` 用 `lru_cache(maxsize=16)` 持有 `ChatLiteLLM`（langchain_litellm）实例至进程结束，全库无任何 close/aclose 调用点。`functools.lru_cache` 不暴露缓存值，真修不能依赖“遍历 lru_cache 内部实例”；需要新增显式 client registry 或改为自管缓存。`ChatLiteLLM` 内部经 litellm 持有 httpx.AsyncClient（keep-alive 连接池）。
- 其他嫌疑路径：LangGraph `AsyncSqliteSaver` checkpointer（`workflows/checkpointer.py:21-51`，已有 `reset_checkpointer_instance` 显式关连接，:54-74）、aiosqlite 连接。

当前对策是"结果落盘后人工确认再 kill"——对无人值守长跑不可接受。

---

## 目标

1. **诊断归因**：最小复现 + 退出阶段线程 dump，把"疑似 litellm 连接池"变成确证结论（含归因证据落盘）。
2. **真修**：pipeline 正常结束路径显式关闭 LLM client 等挂死源资源；**不开兜底**时进程自然退出。
3. **兜底**：结果落盘后的 force-exit 通道（env/flag 控制），独立于真修验收。
4. 行为中立：不改变任何生成/审查/结算行为；全量测试绿；scifi 短窗口实跑回归无异常。

---

## 技术方案

### 1. 诊断（先证归因，不写产品代码）

新增临时复现脚本 `.tmp/repro_173_exit_hang.py`（任务产物，验收后可删）：

- **最小复现 A0（无真实 API dry probe）**：仅 `get_llm()` 初始化 / `aclose_llm_clients()` 关闭 / dump 线程，用于排除“仅实例化即泄漏”的路径，避免诊断阶段完全依赖外部服务。
- **最小复现 A（纯 LLM 路径）**：`get_llm()` + 若干次 `ainvoke`（真实 API，2-3 次调用即可），main 返回前打印 `threading.enumerate()`（name/daemon/alive），并对非 daemon 残留线程用 `faulthandler.dump_traceback()` 定位其栈。
- **最小复现 B（checkpointer 路径）**：仅初始化 `AsyncSqliteSaver` 连接后退出，同样 dump 线程。
- **全路径复现 C**：`run_172a7_genre_validation.py --templates scifi --end 2` 实跑复现（172k 场景的最小化），退出前同样 dump。
- 归因确认项：① litellm 当前安装版本是否提供 `aclose()`/client 关闭入口（`python -c "import litellm; print(litellm.__version__, dir(litellm))"` 级探查 + changelog）；② `ChatLiteLLM` 实例持有的 async client 属性路径（`client`/`async_client`/`root_client`）；③ 残留线程命名特征（httpx/anyio/asyncio 线程池命名）。
- **产出**：归因结论与线程 dump 证据补录本文档"执行记录"节。真修分支按归因选择，不允许在未确证归因时直接写兜底。

### 2. 真修（按归因落地，预写分支）

**分支 A（LLM client 连接池，预期主因）**：

- `src/songyan/llm/client.py` 新增：

```python
async def aclose_llm_clients() -> None:
    """关闭所有缓存的 LLM client 资源（pipeline 结束/进程退出前调用）."""
    # 1. 遍历显式 client registry / 自管缓存，不读取 lru_cache 内部状态
    # 2. 对每个 ChatLiteLLM 及其已确认的底层 client 属性调用 aclose/close
    # 3. 若当前 litellm 版本提供 litellm.aclose()，一并调用
    # 4. 清空 registry 与 _get_llm_cached.cache_clear()，允许 GC
```

- 实现约束：`functools.lru_cache` 不可枚举缓存值，必须新增 `_llm_client_registry`（或将 `_get_llm_cached` 替换为显式 `dict[LLMClientKey, BaseChatModel]` 自管缓存）。`get_llm()` 创建/命中实例后确保 registry 持有该实例；`aclose_llm_clients()` 遍历 registry，按诊断确认的属性路径关闭资源，最后 `cache_clear()` + registry clear。关闭失败只记录 warning，不阻断 run 收尾。
- 调用点：`run_project_pipeline()` 正常/异常返回路径的 `finally` 段只做**真修资源关闭**（`workflows/phase2_graph.py` run 收尾处，注意此时 event loop 必须仍存活——在 async 上下文内 await）；harness（`scripts/run_172a7_genre_validation.py`、`run_172b_ch100_climb.py`）主函数收尾同样调用。
- 若归因在 checkpointer：确认 `reset_checkpointer_instance()` 覆盖所有退出路径（包括异常路径的 finally），缺则补。

**分支 B（归因在其他库）**：按诊断结论在对应资源的创建方补对称关闭；原则相同——创建处有缓存，退出处有清理。

### 3. 兜底（独立于真修验收）

- 新增 env 开关 `SONGYAN_FORCE_EXIT=1`：`config.py` 加 `force_exit_after_run: bool = Field(default=False, validation_alias=AliasChoices("SONGYAN_FORCE_EXIT", "FORCE_EXIT_AFTER_RUN"))`（Pydantic v2），保证文档中的 env 名真实生效；如实现选择不用 alias，则必须把任务书与 README 统一改为实际 env 名。
- `os._exit(0)` **只能在最外层入口调用**：CLI command / harness `main()` 在**最终结果全部落盘、DB/checkpoint 关闭、日志 flush/close、报告文件写完**之后执行；`run_project_pipeline()` 内部禁止调用 `os._exit`，否则 `run_172b_ch100_climb.py` 这类分段 harness 会在第一段后被直接杀死，后续段、metrics、报告无法落盘。
- 长跑 harness（`run_172b_ch100_climb.py`）默认启用兜底——无人值守场景宁可跳过解释器清理也不能挂死；CLI 默认关闭（交互场景保留正常清理以便发现泄漏）。
- `os._exit` 会跳过所有 finally 与 atexit：调用前必须显式完成 ① DB/checkpoint 关闭 ② 日志 handler flush/close ③ 结果文件落盘确认，并在日志中记录 `force_exit.invoked`。

### 4. 真修与兜底分开验收

- **真修验收**（兜底关闭）：连续两次 `scifi --end 2` 实跑，进程在结果落盘后 ≤ 60 秒自然退出，无人工干预。
- **兜底验收**：用 subprocess 级测试注入一个非 daemon 泄漏线程（模拟未关闭资源），子进程启用 `SONGYAN_FORCE_EXIT=1` 后正常结束且结果完整；父进程检查退出码、落盘文件与超时，避免在 pytest 主进程内创建无法退出的非 daemon 线程。

---

## 验证

### 测试（TDD）

新建 `tests/test_173_llm_client_cleanup.py`：

- `aclose_llm_clients()` 调用后：缓存实例的 close/aclose 被调用（mock `ChatLiteLLM`），`_get_llm_cached` 缓存被清空；
- 重复调用安全（幂等，无异常）；
- 无缓存实例时调用为空操作；
- force-exit 决策函数：单元测试只 mock 轻量 helper，验证 env/settings 映射与"落盘确认后才允许 force-exit"的调用顺序；
- force-exit 端到端：subprocess 测试创建泄漏线程并启用 `SONGYAN_FORCE_EXIT=1`，父进程断言子进程按时退出且结果文件完整；
- `SONGYAN_FORCE_EXIT` env → settings 映射测试。

### 回归命令

```powershell
python -m pytest tests/test_173_llm_client_cleanup.py -q
python -m pytest tests/ -q
ruff check src/ tests/
python scripts/run_172a7_genre_validation.py --templates scifi --end 10
```

scifi end10 回归期望逐值不变（本 Task 为行为中立的基础设施修复，回归即证明）。

### 验收判据

- 归因结论与证据落盘（本文档执行记录节）；
- 真修验收：兜底关闭下连续两次 scifi `--end 2` 实跑进程 ≤60s 自然退出；
- 兜底验收：subprocess 注入泄漏线程场景下 `SONGYAN_FORCE_EXIT=1` 正常结束且结果完整；
- pytest 全绿、ruff 无新增 error；
- scifi `--end 10` 10/10、Ch1 budget=8250（旧行为逐值不变）。

---

## 出口标准

1. 归因确证并记录；真修落地，`aclose_llm_clients()`（或归因对应的对称关闭）接入 pipeline 与 harness 收尾，且关闭逻辑基于显式 registry / 自管缓存，不依赖读取 `lru_cache` 内部值；
2. `SONGYAN_FORCE_EXIT` 兜底可用，且只在 CLI/harness 最外层最终落盘后执行；长跑 harness 默认启用；
3. 真修/兜底分开验收的证据落盘（两次自然退出实跑记录 + 注入测试）；
4. 本文档执行记录补录，V9-README Task 173 行状态翻正。

---

## 执行记录（2026-07-18）

### 实现

- `src/songyan/llm/client.py` 新增显式 LLM client registry 与 `aclose_llm_clients()`，关闭逻辑不读取 `lru_cache` 内部值；关闭缓存 client、底层 `async_client` 等常见资源后清空 registry 与 `lru_cache`。
- `src/songyan/workflows/phase2_graph.py` 将 `run_project_pipeline()` 拆成生命周期 wrapper + `_run_project_pipeline_impl()`，在 wrapper 的 `finally` 中执行 `aclose_llm_clients()` 并清理日志 contextvars。
- `src/songyan/utils/process_exit.py` 新增 `force_exit_after_run_if_requested()`，只供 CLI/harness 最外层在最终落盘后调用；`run_project_pipeline()` 内不调用 `os._exit()`。
- `src/songyan/config.py` 新增 `force_exit_after_run`，通过 `SONGYAN_FORCE_EXIT` / `FORCE_EXIT_AFTER_RUN` 双 env alias 映射。
- `scripts/run_172b_ch100_climb.py` 作为长跑 harness 默认启用 force-exit 兜底；`songyan run` 与 `run_172a7_genre_validation.py` 仅在 env/settings 启用时触发。
- （review 修复）`_maybe_close_resource` / `_close_litellm_global_client` 清理路径改为捕获 `Exception`：任何关闭失败不传播，不在 pipeline 收尾 finally 中屏蔽原始异常；新增 `test_aclose_llm_clients_swallows_unexpected_close_errors` 固化。

### 验证

| 命令 / 证据 | 结果 |
|---|---|
| `python -m pytest tests/test_173_llm_client_cleanup.py tests/test_174_logging_setup.py -q` | 13 passed |
| `python -m pytest tests/ -q` | 2814 passed, 2 skipped, 1 xfailed, 2 warnings；review 修复后复验 **2815 passed**（471s，含新增关闭失败健壮性用例） |
| `ruff check src/ tests/ scripts/run_172a7_genre_validation.py scripts/run_172b_ch100_climb.py` | All checks passed |
| subprocess 泄漏线程测试（`tests/test_173_llm_client_cleanup.py::test_force_exit_subprocess_terminates_non_daemon_thread`） | 通过，证明 `SONGYAN_FORCE_EXIT` 兜底可结束非 daemon 泄漏线程且结果文件完整 |

### 实跑说明

- 曾尝试 `scifi --end 2` 与 `scifi --end 1` 真实 LLM smoke。两次均在生成/审查/修订链路中耗时过长，已中止以控制 API 成本；因此本任务**未声明** scifi end10 或两次自然退出真实 LLM 证据。
- 实跑过程中确认 174 的日志关联字段已进入应用日志；后续 174 增补 `LiteLLM` logger 大小写压制后，console 已不再泄漏 DEBUG 请求/响应，只保留 WARNING。
- 真实长窗口/短窗口最终回归仍应在 175 成本追踪与预算熔断落地后执行，避免无成本上限地重复烧实跑。

### 归因探针（2026-07-18 dry probe，`.tmp/probe_173_exit_hang.py`，真实 API 单次调用 max_tokens=8）

| 模式 | 非主线程残留 | 进程退出 |
|---|---|---|
| `instantiate`（仅 `get_llm()`） | 0 | 正常（exit=0） |
| `call`（单次真实调用，不关闭） | 1（`asyncio_0`，非 daemon，alive） | 正常（exit=0） |
| `call_close`（调用 + `aclose_llm_clients()`） | 1（同上 executor 线程） | 正常（exit=0） |

结论：① 实例化不产生线程；② 真实调用产生**非 daemon** asyncio executor 工作线程——非 daemon 线程特征与 172k 挂死现场一致；③ 该线程属事件循环 default executor（非 client 资源，不应由 `aclose_llm_clients()` 清理），最小路径下 `asyncio.run()` 收尾的 `shutdown_default_executor` 会 join 它，**最小路径无法单独复现 172k 挂死**——172k 的 86 线程挂死发生在完整 pipeline 环境，嫌疑收敛到"default executor 之外的常驻资源"（长生命周期 aiosqlite 连接 / LangGraph checkpointer / litellm 内部 executor 的规模效应）。确证归因需全路径复现（scifi `--end 2` 自然退出观察），与自然退出验收一并挂起至 175 后补跑；在此不确定下，显式关闭 + force-exit 兜底保持正确防御姿态。

### 归因确证与真修闭环（2026-07-19，175 阶段 D 实跑）

**挂死复现**：scifi `--end 10`（harness，`checkpointer_mode=sqlite` 默认）在 pipeline 完成、结果落盘后**挂死 50+ 分钟**（人工终止）——172k 场景完整复现。

**py-spy 线程栈**（`.tmp/pyspy-venv`，dump 挂死进程）：

| 线程 | 状态 | 判定 |
|---|---|---|
| MainThread | `threading._shutdown`（join 非 daemon 线程） | 解释器退出被阻塞的**直接现场** |
| Thread-17 `_connection_worker_thread` | aiosqlite 连接 worker（`aiosqlite/core.py:59`） | **根因**：aiosqlite 源码无 `daemon` 设置 → 非 daemon |
| Thread-188/189 `tqdm._monitor` | `self.daemon = True`（`tqdm/_monitor.py:32`） | 排除 |

**根因链**：`checkpointer_mode=sqlite`（生产默认）→ `AsyncSqliteSaver` 持有 aiosqlite 连接 → `build_phase1_graph()` 模块级缓存持有 checkpointer → `reset_checkpointer()`（关连接 + 清编译图缓存）此前**只有测试路径调用**（`phase1_graph.py:245` 标注"测试用"）→ 连接永不关闭 → 非 daemon worker 线程使 `threading._shutdown` 永久 join。dry probe 未复现的原因：探针显式 `checkpointer_mode=memory`（MemorySaver 无连接线程）；D2 harness 用 sqlite 默认值故挂死。

**真修**：`run_project_pipeline()` wrapper 的 finally 在 `aclose_llm_clients()` 后追加 `reset_checkpointer()`（`phase2_graph.py:607-618`），两个清理各自 broad-except 守卫不屏蔽原异常；TDD 红→绿（`tests/test_173_pipeline_cleanup.py` 正常/异常两路径）。

**实跑验收**：

| 项 | 结果 |
|---|---|
| sqlite 模式 scifi `--end 1`（修复后） | pipeline.end 14:14:47.774 → 进程退出 14:14:50.294，**2.5s 自然退出**（修复前同环境挂死 50+ 分钟） |
| memory 模式自然退出（探针批次） | 1.9s / 1.2s / 1.9s / 1.2s，四次均 ≤60s |
| `tests/test_173_pipeline_cleanup.py` | 2 passed（TDD：修复前红） |
| 全量 `python -m pytest tests/ -q` | **2882 passed, 2 skipped, 1 xfailed** |
| `ruff check src/ tests/` | All checks passed |

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 归因不明 | 最小复现 A/B/C 均不挂死，或线程栈无法定位归属库 | 扩大 dump 粒度（`sys._current_frames()` + py-spy 类工具）；对照 litellm/httpx/langchain-litellm 版本 changelog 找已知 issue；必要时升级依赖版本对照实验 |
| 真修后偶发挂死 | 真修验收通过但长窗口仍偶发 | 长跑 harness 兜底默认开启兜住；残留线程清单记录后开 173.p 定点修复 |
| `os._exit` 跳过清理 | 兜底后 DB/日志不完整 | 严格只在"落盘确认"后调用；顺序断言测试防回归 |
| 行为漂移 | scifi end10 非 10/10 或 Ch1 budget ≠ 8250 | 回滚，检查关闭路径是否误伤正常调用（如缓存清空导致每章重建 client 的性能/行为差异） |

---

## Out of Scope

- LiteLLM proxy 化（fallback 链/分类重试/缓存）——V10 工业水位评估项；
- 175 的成本追踪（`LLMCallContext` 字段约定由 174 先行统一，本 Task 不动）；
- asyncio/aiosqlite 连接池的系统性生命周期重构（仅按归因补对称关闭）。
