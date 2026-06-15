# Task 059: JSONL 监控诊断补全 — DONE

> **Phase**: V3.0 Layer 2 — 核心验证层（收尾）
> **优先级**: P0
> **状态**: ✅ 已完成
> **完成日期**: 2026-06-05

---

## 修改清单

### 1. `src/songyan/models/run_log.py`

- **新增 `metrics_version` 字段**：`metrics_version: str = Field(default="v1", alias="_metrics_version")`
  - Python 访问用 `log.metrics_version`
  - JSONL 序列化用 `"_metrics_version"`（通过 `by_alias=True`）
- **`to_jsonl()` 增加 `by_alias=True`**：使别名字段以 alias 名序列化

### 2. `src/songyan/workflows/phase2_graph.py`

在 `_run_single_chapter` 的 try 块中增加 `_stage` 跟踪机制：

| 阶段 | 位置 | 说明 |
|------|------|------|
| `pipeline` | `run_chapter_pipeline` 调用前 | 捕获整个 Phase1 管线异常 |
| `human_confirm` | `resume_human_confirm` 调用前 | 捕获 human_confirm 恢复异常 |
| `summary` | `_get_summary_text` 调用前 | 捕获摘要提取异常 |
| `continuity_audit` | ContinuityAuditor 调用前 | 捕获连续性审计异常 |
| `log` | `log_chapter_run` 调用前 | 捕获日志写入异常 |

- except 分支改为 `error_stage = error_stage or _stage or "exception"`
- 成功路径不传 `error_stage`（保持为空）

### 3. `tests/test_run_logger.py` — 新增 4 个测试

| 测试 | 验证内容 |
|------|----------|
| `test_metrics_version_default` | 实例化后 `metrics_version == "v1"` |
| `test_to_jsonl_includes_metrics_version` | JSONL 含 `"_metrics_version":"v1"` |
| `test_old_jsonl_without_metrics_version` | 无该字段的旧 JSONL 正常反序列化 |
| `test_build_chapter_run_log_includes_metrics_version` | `build_chapter_run_log` 含默认值 |

### 4. `tests/test_phase2_graph.py` — 新增 3 个测试

| 测试 | 验证内容 |
|------|----------|
| `test_run_single_chapter_pipeline_exception_sets_stage` | Pipeline 异常时 `error_stage == "pipeline"` |
| `test_run_single_chapter_human_confirm_exception_sets_stage` | human_confirm 异常时 `error_stage == "human_confirm"` |
| `test_run_single_chapter_success_no_error_stage` | 成功时不传 `error_stage` |

## 验证结果

| 测试套件 | 结果 |
|----------|------|
| `tests/test_run_logger.py` | ✅ 16/16 passed（新增 4 个） |
| `tests/test_phase2_graph.py` | ✅ 11/11 passed（新增 3 个） |
| 全量测试（排除 CLI） | ✅ **1111 passed**（基线 1107） |

## 已知限制

1. **内部 Pipeline 阶段无法跟踪**：`phase2_graph._run_single_chapter` 调用 `run_chapter_pipeline` 作为一个整体，无法获取 "writer"、"rule_auditor" 等内部节点名称。要实现细粒度阶段跟踪需要在 `phase1_graph.py` 中增加 instrumentation，属于 V3.1 范围。
2. **旧版 JSONL** 的 `continuity_health_score` 和 `content_preservation_ratio` 全 null 的问题：这是 058b 的运行数据，058c/058d 的修复已确保新生成的数据会正确采集这些字段。如需验证需在 Task 062 中端到端重跑。
3. `_metrics_version` 采用 `alias` 机制，Python 代码中通过 `log.metrics_version` 访问，JSONL 中显示为 `"_metrics_version"`。

## 交接检查

- [x] 代码实现完成
- [x] 测试通过（pytest — 1111 passed）
- [x] 不违反 AGENTS.md 规则
- [x] 更新了 docs/STATUS.md
- [x] 生成了本交接文件
- [ ] git commit 提交（待用户确认后执行）