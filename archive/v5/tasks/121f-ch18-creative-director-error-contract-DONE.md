# Task 121f DONE: Ch18 CreativeDirector Error Contract

> **日期**: 2026-06-21
> **类型**: V5.1 preflight / 章节状态契约修复
> **状态**: DONE
> **前置**: Task 121e 重跑 `run-0317a247` 已越过 Ch8，并在 Ch18 暴露 CreativeDirector JSON parse failure 状态污染。

---

## 1. 任务边界

本任务只修复 Ch18 暴露的错误传播和章节最终状态判定契约。

不做：

- Prompt 调优。
- CreativeDirector 输出格式调优。
- QualityGate 阈值调整。
- workflow 节点新增。
- settlement 或 summary 语义改动。

---

## 2. 根因

Ch18 中 CreativeDirector 先发生 JSON 解析失败：

```text
creative_director_node.llm_failed
CreativeDirector LLM call failed:
LLM 返回内容无法解析为 JSON:
Expecting ',' delimiter: line 7 column 72 (char 279)
```

但后续流程继续完成：

```text
human_gate.decision decision=accept quality_gate_passed=True
settlement.validation_passed
settlement.applied chapter_number=18
summary_writer.generated chapter_number=18
```

最终状态已具备正文版本、settlement 和 summary，但 `phase2_graph._run_single_chapter` 先检查 `state["error"]`，再检查 `status=="done"`，导致前置残留 error 污染最终章节判定：

```text
run_logger.chapter_logged chapter_number=18 success=False
project_pipeline.chapter_failed chapter_number=18
```

---

## 3. 修复内容

修改文件：

- `src/songyan/workflows/phase2_graph.py`
- `tests/test_phase2_graph.py`
- `tests/test_run_logger.py`

新增终态成功判定：

```python
def _is_terminal_success_state(state: dict[str, Any]) -> bool:
    return (
        state.get("status") == "done"
        and state.get("current_version_id") is not None
        and state.get("settlement_id") is not None
        and state.get("summary_id") is not None
    )
```

契约：

- 若 `status=done` 且 `current_version_id/settlement_id/summary_id` 均存在，章节视为成功。
- 前置非致命 error 只作为诊断日志保留，记录 `project_pipeline.stale_error_ignored_after_terminal_success`。
- 若未达到终态成功条件，原有 error/status 失败逻辑保持不变。

---

## 4. 验证

已执行：

```powershell
python -m py_compile src\songyan\workflows\phase2_graph.py src\songyan\workflows\_run_logger.py
python -m pytest tests\test_phase2_graph.py tests\test_run_logger.py -q
ruff check src\songyan\workflows\phase2_graph.py tests\test_phase2_graph.py tests\test_run_logger.py
ruff check src\ tests\
python -m pytest tests/ -q
```

结果：

- 聚焦测试：`33 passed`
- 全量 ruff：passed
- 全量回归：`1722 passed, 2 xfailed, 14 warnings`

补充实跑验证：

- 新干净项目：`4b51384ef7f349cc973bc301b46f6d20`
- 聚焦运行：`run-058fb9de`
- 范围：Ch1-Ch18
- 结果：`final_status=completed`，`completed=[1..18]`，`failed=[]`
- Ch18：`success=true`，`settlement_success=true`，`summary_success=true`
- 报告：`logs/reports/report-run-058fb9de.md`
- 备注：Ch17 触发一次 `ContextEmergency`，但章节成功完成；Ch18 未复现状态污染阻断。

---

## 5. 下一步

Ch1-Ch18 聚焦验证已确认 Task 121f 生效。下一步重跑 Ch1-Ch150 single-run，继续记录下一处真实长跑瓶颈。
