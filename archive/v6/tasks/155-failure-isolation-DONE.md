# Task 155: 失败隔离策略 — DONE

> **Phase**: V6 阶段 C（工程加固）
> **状态**: ✅ 完成
> **合入时间**: 2026-07-02
> **事实文档**: 本文件

---

## 完成摘要

将多章 run 的默认失败语义从"首章硬失败即 `abort` 终止整批"改为"**隔离单章失败、继续后续章、run 结束汇总失败清单**"，让长跑不因中段某一章偶发失败而白跑；同时保留质量 AutoHalt / enforce 门禁的硬停能力，并为失败后续章提供"最近成功摘要"回退，避免 continuity 断链污染。

---

## 实现落点

### 155a — 隔离-继续循环语义

- `workflows/phase2_graph.py::run_project_pipeline`：
  - `on_failure` 取值扩展为 `"abort" | "retry" | "isolate"`，**默认改为 `"isolate"`**。
  - 改写失败分支：保留 `failed.append` / `_persist_run_progress` / `_check_auto_halt_window`；按策略分派——`abort`→`break`；`retry`→仍失败则 `break`；`isolate`→`continue`。
  - `_check_auto_halt_window` 与 enforce 单章门禁仍在 `isolate` 分支之前/之后执行，**隔离不吞熔断**。
- `cli/main.py::run`：新增 `--on-failure` 选项（默认 `isolate`），透传到 pipeline；保留 `abort`/`retry` 供显式选择。

### 155b — 失败清单汇总 + 上下文回退

- `workflows/phase2_graph.py` 新增"最近成功摘要"游标 `_latest_successful_chapter`：成功章推进游标，失败章不推进。
- `_get_previous_summary` 新增 `latest_successful_chapter` 关键字参数；isolate 模式下调用时回退到最近成功章的 `plot_summary`，前面无成功章时返回 `""`。
- CLI `run` 输出升级：失败时列出具体章号 `result.chapters_failed`，而非仅数量。
- 失败清单自然落库 `project_runs.failed_chapters`，`songyan report` 已可逐章读取失败列表。

---

## 接口契约

```python
# workflows/phase2_graph.py
async def run_project_pipeline(
    project_id: str,
    chapter_range: tuple[int, int],
    mode_id: str = "webnovel",
    *,
    auto_confirm: bool = False,
    max_revision_rounds: int = 2,
    on_failure: str = "isolate",   # 变更：默认 isolate（原 abort）
    continuity_health_threshold: float = 7.0,
    gate_config: GateConfig | None = None,
    resume: bool = False,
    run_id: str | None = None,
) -> ProjectRunResult: ...

# cli/main.py
@click.option(
    "--on-failure",
    default="isolate",
    type=click.Choice(["abort", "retry", "isolate"]),
    help="单章失败策略：isolate 隔离并继续（默认），abort 终止整批，retry 重试一次",
)
```

---

## 关键口径

- **isolate 默认**：未显式指定 `on_failure` 时走 isolate；旧行为可通过 `--on-failure abort` 显式恢复。
- **AutoHalt 不弱化**：`isolate` 分支内仍先经 `_check_auto_halt_window`；连续质量门失败 / health_low streak / 降级 ContextEmergency streak 仍抛 `AutoHaltException` 并 pause run。
- **失败章上下文回退**：
  1. 首选最近成功章的 summary；
  2. 首章即失败或此前无成功章时返回 `""`；
  3. 不伪造失败章 head/summary，保持事实源纯净。
- **失败章可定点重跑**：`failed_chapters` 写入 `project_runs` 并打印在 CLI；下次 `--resume` 时失败章不在 accepted 集合，会被重跑（与 Task 153 叠加）。
- **不新增 Agent/LLM**：纯 run 编排 + CLI 改动。

---

## 测试覆盖

`tests/test_155_failure_isolation.py`（7 个用例）：

- `test_isolate_continues_after_single_failure`：Ch2 失败、Ch1/Ch3 成功 → `partial`、`completed=[1,3]`、`failed=[2]`。
- `test_abort_stops_at_first_failure`：`abort` 仍在 Ch2 失败处 break，行为不变。
- `test_default_on_failure_is_isolate`：未传 `on_failure` 时单章调用均收到 `"isolate"`。
- `test_previous_summary_falls_back_to_latest_successful`：Ch2 失败后 Ch3 的 `previous_summary` 回退到 Ch1。
- `test_cursor_not_advanced_by_consecutive_failures`：Ch2/Ch3 连续失败后 Ch4 仍用 Ch1 摘要。
- `test_first_chapter_failure_empty_previous_summary`：首章失败时 Ch2 的 `previous_summary` 为空串。
- `test_auto_halt_still_raises_in_isolate_mode`：连续质量门失败在 isolate 模式下仍触发 `AutoHaltException`，run `status="paused"`。

---

## 验证结果

- `pytest tests/test_155_failure_isolation.py -v`：7 passed。
- `ruff check src/ tests/`：通过。
- 全量 pytest 待 Task 156 完成后统一跑。

---

## Layer 3 计划

Task 155 的"中段注入单章失败被隔离、后续章继续、run 结束 partial"实跑证据将在 **Task 158（Ch1-Ch100 长跑验证）** 中统一采集并入 `docs/reports/`。当前模块测试已覆盖 isolate 继续、abort 兼容、AutoHalt 不吞、上下文回退等全部口径。

---

## 参考

- 规划：`docs/v6-plan.md` §3 阶段 C
- 任务文档：`archive/v6/tasks/155-failure-isolation.md`
- 相关代码：`src/songyan/workflows/phase2_graph.py`、`src/songyan/cli/main.py`
