# Task 153: run 级断点续跑 — DONE

> **Phase**: V6 阶段 C（工程加固）
> **状态**: ✅ 完成
> **合入时间**: 2026-07-02
> **事实文档**: 本文件

---

## 完成摘要

让一条无人值守长跑在中途被人为 kill（或崩溃）后，**用同一命令真正 resume**：已 `accepted` 的章节跳过、in-flight（生成到一半未 accept）的章节正确恢复而非从头重算整批，孤儿 checkpoint 被清理。

---

## 实现落点

### 153a — resume 点推导 + CLI 入口

- `workflows/phase2_graph.py::run_project_pipeline` 新增关键字参数：
  - `resume: bool = False`：复用该项目最近一次未完成的 run。
  - `run_id: str | None = None`：显式指定 run（优先级高于 `resume`）。
- 新增内部辅助函数：
  - `_find_resume_run(project_id, *, resume, run_id)`：按 run_id 或最近 run 查找。
  - `_compute_resume_start(start, end, accepted_chapters)`：以 `chapter_heads.status == "accepted"` 为唯一完成事实源，计算 resume 起点。
  - `_rebuild_accumulated_summary(project_id, accepted_chapters)`：从 `summaries` 表逐章重建累积摘要，不直接信任 `project_runs.accumulated_summary`。
- `cli/main.py::run` 新增 `--resume` 与 `--run-id` 选项，透传到 pipeline；不传时行为与现状完全一致（新建 run）。

### 153b — in-flight 状态恢复 + 孤儿 checkpoint 清理

- in-flight 章按 **保守重算** 处理：不跳过、从 resume 起点开始重跑；重算前通过 `reset_checkpointer()` + `prune_orphan_checkpoints()` 清理残留 checkpoint。
- `workflows/checkpointer.py` 新增 `prune_orphan_checkpoints(project_id, active_thread_ids)`：
  - 仅删除 `metadata` 中带有 `project_id` 的 checkpoint 行（旧版无 `project_id` 的行不会被误删）。
  - `active_thread_ids` 为当前要保留的 thread_id 集合；resume 启动时传入空集合，清理该项目所有残留 checkpoint。
  - `memory` 模式下直接返回 0（天然无残留）。
- `workflows/phase1_graph.py::run_chapter_pipeline` 在 checkpoint config 中写入 `metadata={project_id, chapter_number}`，使后续清理可按项目精准定位。
- stuck-at-`running` 的 run 视为可续跑；resume 完成后正常收尾为 `completed`/`partial`/`failed`。
- 从 `paused`（AutoHalt）状态 resume 时打印明确警告，不静默跳出门禁；resume 后仍走 `_check_auto_halt_window`。

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
    on_failure: str = "abort",
    continuity_health_threshold: float = 7.0,
    gate_config: GateConfig | None = None,
    resume: bool = False,
    run_id: str | None = None,
) -> ProjectRunResult: ...

# workflows/checkpointer.py
async def prune_orphan_checkpoints(project_id: str, active_thread_ids: set[str]) -> int: ...
```

---

## 关键口径

- **完成事实源唯一**：`chapter_heads.status == "accepted"`。`project_runs.completed_chapters` 仅作断点辅助，不用于跳过决策（硬 kill 时刻可能领先于真正落库的 accepted head）。
- **摘要重建**：`accumulated_summary` 由 `summaries` 表逐章重建，不直接信任 `project_runs.accumulated_summary` 字符串。
- **失败章重跑**：resume 时，范围内已有的 `failed_chapters` 会从失败清单中移除并重新执行；范围外的失败章保留。
- **不弱化 AutoHalt**：resume 后仍执行 `_check_auto_halt_window`；paused run resume 打印警告但继续执行门禁。
- **不新增 Agent/LLM**：纯 run 编排 + 仓储 + checkpointer 改动。

---

## 测试覆盖

`tests/test_153_run_level_resume.py`（13 个用例）：

- `_find_resume_run`：按 run_id、按 resume 标志、无 run 返回 None。
- `_compute_resume_start`：跳过头、空集合、全部完成。
- `_rebuild_accumulated_summary`：从 summaries 表重建累积摘要。
- resume 跳过已 accept 章并重建摘要。
- `completed_chapters` 领先于 accepted head 时以 head 为准。
- stuck-at-`running` run 续完为 `completed`。
- 从 `paused` resume 记录明确警告。
- 默认新 run 行为不变、不触发 prune。
- resume 已 `completed` run 直接返回。
- `prune_orphan_checkpoints` memory 模式返回 0。
- `prune_orphan_checkpoints` sqlite 模式按 `metadata.project_id` 精准清理、不误删其他项目。

---

## 验证结果

- `pytest tests/test_153_run_level_resume.py -v`：13 passed。
- `pytest tests/test_phase2_graph.py tests/workflows/test_checkpointer.py -q`：23 passed，无回归。
- `ruff check src/ tests/`：通过。

---

## Layer 3 计划

Task 153 的 kill→resume 实跑证据将在 **Task 158（Ch1-Ch100 长跑验证）** 中统一采集并入 `docs/reports/`。当前模块测试已覆盖 resume 点推导、in-flight 重算、孤儿清理、stuck/paused 状态恢复等全部口径。

---

## 参考

- 规划：`docs/v6-plan.md` §3 阶段 C
- 任务文档：`tasks/153-run-level-resume.md`
- 相关代码：`src/songyan/workflows/phase2_graph.py`、`src/songyan/workflows/checkpointer.py`、`src/songyan/workflows/phase1_graph.py`、`src/songyan/cli/main.py`
