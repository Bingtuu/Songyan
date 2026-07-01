# Task 119-DONE: 长跑报告入口与 Windows Wrapper 加固

> **Phase**: V5.0 Phase 4 — 工程化收口
> **优先级**: P2
> **依赖**: Task 117 完成
> **完成日期**: 2026-06-21
> **测试**: 12 passed（test_119_reporting_wrapper.py）；全量回归 1711 passed
> **lint**: ruff check src/ tests/ 通过
> **全量回归**: 1711 passed（pytest tests/ -q）

---

## 做了什么

### 1. 报告入口统一

**两个正式入口**：

- **CLI 子命令** `songyan report --run-id <run_id>` — 主推入口，集成到 `songyan` CLI
  ```bash
  songyan report --run-id run-8e14bcf1
  songyan report --run-id run-8e14bcf1 -o logs/reports/my-report.md
  songyan report --run-id run-8e14bcf1 --start 111 --end 150
  ```

- **模块入口** `python -m songyan.evals.streaming_report --run-id <run_id>` — 备选入口
  ```bash
  python -m songyan.evals.streaming_report --run-id run-8e14bcf1
  python -m songyan.evals.streaming_report --input /path/to/chapter_runs.jsonl --output report.md
  ```

两者功能完全等价，内部统一调用 `songyan.evals.streaming_report.generate_report()`。

### 2. PowerShell Wrapper 加固

创建 `scripts/run_songyan_chapter.ps1`，实现以下结果码：

| WRAPPER_RESULT | 含义 |
|---|---|
| `PASS_NORMAL_EXIT` | 正常退出：exit=0 且检测到 `project_pipeline.end` |
| `PASS_BUSINESS_COMPLETED_WRAPPER_TIMEOUT` | 业务完成但 wrapper 超时（`project_pipeline.end` 已出现但 Job 未在超时内退出） |
| `FAIL_TIMEOUT` | 超时且无 `project_pipeline.end` |
| `WARN_NO_PIPELINE_END` | exit=0 但未检测到 `project_pipeline.end` |
| `WARN_BUSINESS_DONE_WITH_ERROR` | 业务完成标记出现但 exit≠0 |
| `FAIL_NONZERO_EXIT` | 非零退出码，无 `project_pipeline.end` |

关键改进：
- 同时检查 exit code 和 `project_pipeline.end` 业务完成标记
- 区分"业务完成但 wrapper 超时"与"真超时"
- 输出标准化 result 文件便于自动化解析

### 3. 日志命名规范

标准化路径：`logs/task<N>/songyan-<task>-<tag>-<timestamp>.*`

- `*.out.log` — stdout
- `*.err.log` — stderr
- `*.meta.txt` — 元信息（开始时间、命令）
- `*.result.txt` — WRAPPER_RESULT 结果码
- `*.output.txt` — 原始输出摘要

### 4. 报告一致性检查

在 `evals/__main__.py` 中实现 `_validate_report_consistency()` 函数，检查：

- 报告章节范围与 JSONL 条目数是否一致
- 成功章节是否缺少 `budget_used`（警告）
- 是否有章节触发 `ContextEmergency`（警告）

### 5. 测试覆盖

**`tests/test_119_reporting_wrapper.py`** — 12 个测试：

Layer 1（入口测试）：
- `test_report_cli_requires_run_id` — 无参数时报错
- `test_report_cli_no_jsonl_warns` — JSONL 不存在时警告
- `test_report_cli_generates_report` — 有效 run-id 生成报告
- `test_report_cli_no_logs_warning` — 空日志时警告
- `test_evals_main_missing_jsonl` — 文件不存在返回 1
- `test_evals_main_valid_run_id` — 有效 run-id 返回 0

Layer 2（一致性检查）：
- `test_consistency_ok` — 数据匹配无警告
- `test_consistency_missing_budget` — 缺少 budget_used 时警告
- `test_consistency_context_emergency` — ContextEmergency 时警告
- `test_consistency_chapter_range_mismatch` — 章节范围不符时警告

Layer 2（Wrapper 结果码功能验证）：
- `test_passing_chapters_all_success` — 全成功无警告
- `test_failed_chapter_in_report` — 失败章节不触发虚警

---

## 改了哪些文件

| 文件 | 变更 |
|------|------|
| `src/songyan/evals/__main__.py` | 新建：streaming report CLI 入口（argparse，支持 --run-id/--input/--output） |
| `src/songyan/cli/main.py` | 新增 `songyan report` 子命令（Click 风格） |
| `scripts/run_songyan_chapter.ps1` | 新建：加固版 PowerShell wrapper 模板 |
| `tests/test_119_reporting_wrapper.py` | 新建：12 个测试 |

---

## 验证结果

### Task 119 聚焦测试
```
12 passed in 0.37s
```

### 全量回归
```
1711 passed, 4 skipped, 1 xfailed, 4 xpassed
```

### lint
```
All checks passed!
```

### CLI 入口验证
```
songyan report --help
  Usage: songyan report [OPTIONS]

  从 JSONL 运行日志生成流式验证 markdown 报告。

  示例:
      songyan report --run-id run-8e14bcf1
      songyan report --run-id run-8e14bcf1 -o logs/reports/my-report.md

Options:
  --run-id TEXT      运行 ID（从 logs/chapter_runs/<run_id>.jsonl 读取）  [required]
  -o, --output FILE  输出 markdown 路径（默认 logs/reports/report-<run_id>.md）
  --start INTEGER    章节范围起始（默认从 JSONL 自动推断）
  --end INTEGER      章节范围结束（默认从 JSONL 自动推断）
  --help             Show this message and exit.
```

---

## 已知限制

1. **不迁移历史日志**：日志命名规范只对新日志生效，不移动历史文件。
2. **旧 wrapper 已归档**：`run_task117.ps1` 已移入 `archive/v5/scripts/run_task117.ps1`，当前通用模板为 `scripts/run_songyan_chapter.ps1`。
3. **`collect_continuity_health_metrics` 未在报告中调用**：Task 118 的 health 指标收集函数尚未集成到 streaming report。

---

## 下一步

- Task 120：V5.0 Final Acceptance Package
