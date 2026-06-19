# Task 111e DONE: Task 112 报告与 DG-2 Gate 完整性修复

> **完成日期**: 2026-06-19
> **状态**: ✅ 已完成
> **提交范围**: Streaming report 稳定性 / DG-2 硬指标 / run log summary 指标

---

## 完成内容

1. **修复 streaming report 缺失指标兼容**
   - `budget_used=None` 在报告明细中显示 `-`，不再触发 `.3f` 格式化异常。
   - `budget_used=0` 保留为 `0.000`。
   - `character_states_loaded`、`soft_refs_loaded`、QG、settlement、summary 等缺失字段统一降级显示 `-` 或 `?`。

2. **扩展 DG-2 判定指标**
   - `generate_report()` 在 Ch101+ 自动调用扩展 DG-2，并输出结构化明细。
   - DG-2 覆盖运行完成率、QG 通过率、平均预算、逐章预算、ContextEmergency、settlement validation、accepted 后 summary、失败章节与失败原因。
   - DG-2 支持 `passed` / `conditional` / `failed` 三态，其中 `conditional` 用于 90%-95% 完成率或可复核失败场景。

3. **补齐 chapter run metrics**
   - `ChapterRunLog` 新增轻量字段 `summary_id` 与 `summary_success`。
   - `_run_logger.build_chapter_run_log()` 从最终 state 的 `summary_id` 填充 summary 指标。
   - 旧 JSONL 缺少新字段时仍可反序列化，报告降级显示 unknown，不崩溃。

4. **补充防回归测试**
   - 覆盖 `budget_used=None` 与 `budget_used=0` 的报告输出。
   - 覆盖平均 budget 达标但单章超限时 DG-2 不通过。
   - 覆盖 settlement validation failed 时 DG-2 不通过。
   - 覆盖 accepted 后缺 summary 时 DG-2 不通过。
   - 覆盖 mixed chapter logs 输出失败章节、失败原因、budget 超限、summary 缺失等明细。

---

## 修改文件

- `src/songyan/evals/streaming_report.py`
- `src/songyan/models/run_log.py`
- `src/songyan/workflows/_run_logger.py`
- `tests/test_105_streaming_validation.py`
- `docs/STATUS.md`
- `README.md`
- `docs/INDEX.md`
- `tasks/111e-task112-reporting-dg2-gate-fix-DONE.md`

---

## 验证结果

```bash
pytest tests/test_105_streaming_validation.py tests/test_run_logger.py -q
```

结果：`49 passed`

```bash
pytest tests/test_105_streaming_validation.py tests/test_run_logger.py tests/test_eval_runner.py tests/evals -q
```

结果：`116 passed, 2 skipped, 4 xpassed, 1 warning`

```bash
pytest tests/ -v
```

结果：`1646 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
pytest tests/ -q
```

结果：`1646 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
ruff check src/songyan/evals/streaming_report.py src/songyan/models/run_log.py src/songyan/workflows/_run_logger.py tests/test_105_streaming_validation.py tests/test_run_logger.py
```

结果：`All checks passed!`

```bash
ruff check src/ tests/
```

结果：失败，仍为历史 lint 存量 `130 errors`，集中在未触及测试文件的 E501/F841；本 Task touched files 的 ruff 已通过。

---

## 已知限制

- `summary_success=None` 的旧日志会在报告中显示 `?`，DG-2 会将其作为无法证明 summary 完整的阻断项处理。
- `conditional` 状态仍以 `passed=False` 表示，避免自动流程把条件通过误当作完全通过。
- `streaming_report.py` 当前超过 400 行，属于 P2 代码体积问题；本 Task 未额外拆文件，避免扩大变更面。

---

## 下一步

进入 **Task 111f: Context Snapshot、Prompt 与 Metadata 一致性修复**。
