# Task 173: 解释器退出挂死修复

> **阶段**: V9.1 长跑可靠性
> **类型**: 缺陷修复（生产事故级）
> **优先级**: P0——与 174 并列为**一切真实 LLM 实跑的硬前置**（V9-README 执行纪律：挂死无兜底时跑实跑等于重演 172k 事故场景）
> **依赖**: 无（V9 主链首站）
> **状态**: ◻ 规划中
> **来源**: 172k 两次实跑挂死记录（`archive/v8/tasks/172k-c-dimension-evidence-closure.md`）；V9 生产就绪度审计；`tasks/V9-README.md` Task 173 行

---

## 背景

172k 实跑（xuanhuan end10 / wuxia end20）两轮均出现：**结果落盘后进程在解释器退出阶段挂死**——残留约 86 个线程、零 CPU，只能人工 kill。当时推测为 litellm/httpx 连接池非 daemon 线程未关闭，但**未在代码层证实**。

代码现状（2026-07-18 审计）：

- `src/` 全库无 `Thread`/`daemon`/`Executor` 使用，无 `atexit` 注册，无 `os._exit` 调用——挂死零代码兜底。
- LLM client 生命周期无人管理：`src/songyan/llm/client.py:71` 的 `_get_llm_cached` 用 `lru_cache(maxsize=16)` 持有 `ChatLiteLLM`（langchain_litellm）实例至进程结束，全库无任何 close/aclose 调用点。`ChatLiteLLM` 内部经 litellm 持有 httpx.AsyncClient（keep-alive 连接池）。
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
    # 1. 遍历 _get_llm_cached 缓存实例，调用其 async client 的 aclose/close
    # 2. 若当前 litellm 版本提供 litellm.aclose()，一并调用
    # 3. 清空 lru_cache（_get_llm_cached.cache_clear()），允许 GC
```

- 调用点：`run_project_pipeline()` 正常返回路径的 `finally` 段（`workflows/phase2_graph.py` run 收尾处，注意此时 event loop 必须仍存活——在 async 上下文内 await）；harness（`scripts/run_172a7_genre_validation.py`、`run_172b_ch100_climb.py`）主函数收尾同样调用。
- 若归因在 checkpointer：确认 `reset_checkpointer_instance()` 覆盖所有退出路径（包括异常路径的 finally），缺则补。

**分支 B（归因在其他库）**：按诊断结论在对应资源的创建方补对称关闭；原则相同——创建处有缓存，退出处有清理。

### 3. 兜底（独立于真修验收）

- 新增 env 开关 `SONGYAN_FORCE_EXIT=1`（`config.py` 加 `force_exit_after_run: bool = False`，env 映射）：run 命令与 harness 在**结果全部落盘、DB 连接关闭、日志 flush 之后**调用 `os._exit(0)`。
- 长跑 harness（`run_172b_ch100_climb.py`）默认启用兜底——无人值守场景宁可跳过解释器清理也不能挂死；CLI 默认关闭（交互场景保留正常清理以便发现泄漏）。
- `os._exit` 会跳过所有 finally 与 atexit：调用前必须显式完成 ① DB/checkpoint 关闭 ② 日志 handler flush/close ③ 结果文件落盘确认，并在日志中记录 `force_exit.invoked`。

### 4. 真修与兜底分开验收

- **真修验收**（兜底关闭）：连续两次 `scifi --end 2` 实跑，进程在结果落盘后 ≤ 60 秒自然退出，无人工干预。
- **兜底验收**：在测试中注入一个非 daemon 泄漏线程（模拟未关闭资源），`SONGYAN_FORCE_EXIT=1` 路径进程正常结束且结果完整。

---

## 验证

### 测试（TDD）

新建 `tests/test_173_llm_client_cleanup.py`：

- `aclose_llm_clients()` 调用后：缓存实例的 close/aclose 被调用（mock `ChatLiteLLM`），`_get_llm_cached` 缓存被清空；
- 重复调用安全（幂等，无异常）；
- 无缓存实例时调用为空操作；
- force-exit 路径：mock `os._exit`，验证其在"DB 关闭 + 日志 flush"之后被调（调用顺序断言）；
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
- 兜底验收：注入泄漏线程场景下 `SONGYAN_FORCE_EXIT=1` 正常结束且结果完整；
- pytest 全绿、ruff 无新增 error；
- scifi `--end 10` 10/10、Ch1 budget=8250（旧行为逐值不变）。

---

## 出口标准

1. 归因确证并记录；真修落地，`aclose_llm_clients()`（或归因对应的对称关闭）接入 pipeline 与 harness 收尾；
2. `SONGYAN_FORCE_EXIT` 兜底可用，长跑 harness 默认启用；
3. 真修/兜底分开验收的证据落盘（两次自然退出实跑记录 + 注入测试）；
4. 本文档执行记录补录，V9-README Task 173 行状态翻正。

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
