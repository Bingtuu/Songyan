# Task 105: Ch51-Ch100 流式验证 + 决策门 DG-1 — DONE

> **完成日期**: 2026-06-13
> **状态**: ✅ 已完成

---

## 做了什么

Task 105 实现了 V5.0 Context Diet 2.0 的流式验证基础设施，包括：

1. **ChapterRunLog 模型扩展** (`src/songyan/models/run_log.py`)
   - 新增 V5.0 指标字段：`budget_used`, `character_states_loaded`, `soft_refs_loaded`, `context_emergency`, `context_pressure`, `quality_gate_passed`
   - `metrics_version` 从 `v3.1` 升级为 `v5.0`
   - `quality_gate_passed` 设为 `bool | None = None` 以兼容旧 JSONL

2. **accept 路径自动指标收集** (`src/songyan/workflows/_nodes.py`)
   - 在 `human_gate_node` accept 路径提取 `_context_metrics` 和 `_quality_gate_passed`
   - 指标从 `context_package` 读取，不阻塞主流程

3. **RunLogger 指标映射** (`src/songyan/workflows/_run_logger.py`)
   - `build_chapter_run_log` 从 `final_state` 提取 `_context_metrics` 并映射到 `ChapterRunLog` 字段
   - 清理未使用导入 (`asyncio`, `json`, `os`)

4. **流式验证报告生成器** (`src/songyan/evals/streaming_report.py`)
   - `generate_report()`: 读取 `ChapterRunLog` 列表，生成 markdown 报告
   - 计算达标率、budget_used 均值、character_states/soft_refs 均值、revision 均值、emergency 次数、字数比例
   - `run_decision_gate_dg1()`: 7 项指标全部满足才算通过
   - `read_run_logs()`: 从 JSONL 读取日志
   - `write_report()`: 写入 markdown 文件

5. **自动熔断机制** (`src/songyan/workflows/phase2_graph.py`)
   - `run_project_pipeline` 循环中维护最近 3 章的 `_recent_results` 窗口
   - 连续 3 章 `quality_gate_passed=False` → `AutoHaltException(reason="quality_gate_fail_streak")`
   - 连续 3 章 `context_emergency=True` → `AutoHaltException(reason="context_emergency_streak")`
   - `quality_gate_passed=None` 的章节不计入熔断窗口（兼容旧测试/无 QG 场景）

6. **AutoHaltException 异常定义** (`src/songyan/exceptions.py`)
   - 新增 `AutoHaltException`，携带 `last_chapter` 和 `reason`
   - 保留已生成章节，不破坏已有状态

---

## 改了哪些文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/songyan/models/run_log.py` | 修改 | 新增 V5.0 指标字段 |
| `src/songyan/workflows/_nodes.py` | 修改 | accept 路径插入 `_context_metrics` + `_quality_gate_passed` |
| `src/songyan/workflows/_run_logger.py` | 修改 | 指标映射 + 清理未使用导入 |
| `src/songyan/workflows/phase2_graph.py` | 修改 | 自动熔断逻辑 + 透传上下文指标 |
| `src/songyan/evals/streaming_report.py` | 新增 | 报告生成器 + 决策门 DG-1 |
| `src/songyan/exceptions.py` | 修改 | 新增 `AutoHaltException` |
| `tests/test_105_streaming_validation.py` | 新增 | 21 个单元测试 |
| `tests/test_run_logger.py` | 修改 | `metrics_version` 断言 v3.1→v5.0 |

---

## 测试数据

### 新增测试

```bash
pytest tests/test_105_streaming_validation.py -v
# 21 passed in 1.79s
```

覆盖：
- `_compute_word_count_ratio` (3 tests)
- `generate_report` (6 tests)
- `run_decision_gate_dg1` (4 tests)
- `read_run_logs / write_report` (2 tests)
- 自动熔断逻辑 (6 tests): 3 连失败触发、3 连 emergency 触发、None 跳过、2 连失败不触发、交错通过不触发

### 全量回归

```bash
pytest tests/ -q
# 1455 passed, 21 failed, 4 skipped, 4 xfailed
```

新增失败：**0**（对比前次全量回归 1431 passed/24 failed，+24 passed / -3 failed，差异完全由 Task 105 修复/新增解释）

Pre-existing 失败（21 项）：
- `test_checkpoint` (3) / `test_paths` (9): `__interrupt__` 不在 state 中 — LangGraph API 变更相关
- `test_multi_chapter` (3) / `test_ch41_50_validation` (1): 集成测试 LLM mock/cache 不稳定
- `test_080_character_appearance_window` (2): importance_score 断言 0.4 vs 0.3
- `test_eval_runner` (2): Pydantic validation / 超时阈值 flaky
- `test_concurrent_settlement_writes` (1): sqlite3 locked 并发问题

---

## 验证结果

- **ruff 检查**: Task 105 修改文件无新增 lint 错误（保留 N818 `AutoHaltException` 按用户指令）
- **单元测试**: 21/21 通过
- **回归测试**: 无新增失败
- **phase2_graph 原有测试**: 11/11 通过（AutoHaltException 不触发 mock 测试）

---

## 已知限制

1. **实际 Ch51-Ch100 流式验证尚未执行**: 本 Task 只完成了基础设施（指标收集 + 报告生成 + 熔断）。实际 50 章全自动跑通需要接入真实/模拟 LLM，属于验证执行阶段。
2. **报告无趋势图**: 规格中提到"趋势图"，当前实现为纯 markdown 表格。如需图表，需额外引入可视化库。
3. **集成测试不稳定**: `test_multi_chapter` 等集成测试受 LLM mock/cache 影响，偶发失败，与 Task 105 逻辑无关。
4. **N818 保留**: `AutoHaltException` 名称未改为 `AutoHaltError`，按用户历史指令保留。

---

## 下一步

- 执行实际 Ch51-Ch100 流式验证（需配置 LLM 和项目）
- 根据 DG-1 结果决定：推进 V5.1（Ch101-Ch150）或启动 Task 109-110（活跃信息池控制）
