# Task 070: JSONL 诊断增强 — DONE

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-05
> **实际工作量**: ~1.5 小时

---

## 实现摘要

增强 JSONL 运行日志的诊断价值：升级 `_metrics_version` 字段，补录 `error_stage` 全链路阶段名。

### 7.1 `_metrics_version` 字段

- `src/songyan/models/run_log.py`: `metrics_version` 默认值从 `"v1"` → `"v3.1"`
- 新增/修改 metrics 时递增版本号，可区分"版本不支持 null" vs "采集失败 null"
- 向后兼容：旧 JSONL（无 `_metrics_version`）反序列化时自动填充默认值 `"v3.1"`

### 7.2 `error_stage` 全链路补录

**问题**: 058b 运行中 38 条 error 仅 7 条有明确 `error_stage`，其余为 `"error"` 或空字符串。

**根因**: `_nodes.py` 各节点返回 error 时统一设置 `"status": "error"`，丢失了具体阶段信息。`phase2_graph.py` 从 `state.get("status")` 读取时只能拿到 `"error"`。

**修复**: 将 `_nodes.py` 中所有 error 路径的 `status` 从 `"error"` 改为对应的 stage 名：

| 节点 | 错误时 status |
|------|--------------|
| `goal_planner_node` | `"goal_planner"` |
| `creative_director_node` | `"creative_director"` |
| `context_manager_node` | `"context_manager"` |
| `writer_node` | `"writer"` |
| `rule_auditor_node` | `"rule_auditor"` |
| `llm_auditor_node` | `"llm_auditor"` |
| `review_merger_node` | `"review_merger"` |
| `literary_auditor_node` | `"literary_auditor"` |
| `revision_handler_node` | `"revision_handler"` |
| `settlement_extractor_node` | `"settlement_extractor"` |
| `human_gate_node` | `"human_confirm"` |

`phase2_graph.py` 同步更新内部 `_stage` 命名（`"summary"`→`"summary_writer"`, `"log"`→`"run_logger"`）。

---

## 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/songyan/models/run_log.py` | `metrics_version` 默认值 `"v1"` → `"v3.1"` |
| `src/songyan/workflows/_nodes.py` | 13 处 `"status": "error"` → 对应 stage 名 |
| `src/songyan/workflows/phase2_graph.py` | `_stage` 命名对齐 Task 规范 |
| `tests/test_run_logger.py` | 更新 4 个 metrics_version 测试期望值为 `"v3.1"` |
| `tests/test_phase1_graph.py` | 更新 4 个测试期望 status 为 stage 名 |
| `tests/test_error_stage.py` | **新增** 13 个测试，覆盖全部 11 个节点的 error stage |

---

## 测试覆盖

| 测试文件 | 数量 | 说明 |
|----------|------|------|
| `tests/test_error_stage.py` | 13 passed | 新增：全部节点 error stage 验证 |
| `tests/test_run_logger.py` | 16 passed | 更新 metrics_version 为 v3.1 |
| `tests/test_phase1_graph.py` | 更新后通过 | 4 个测试期望更新 |
| `tests/` 全量 | **1161 passed** | 零失败 |

---

## 与 Task 070 原始验收标准的差异

| 原始标准 | 实际完成 | 说明 |
|----------|----------|------|
| `_metrics_version` 字段升级 | ✅ | `"v1"` → `"v3.1"`，常量定义在 `run_log.py` |
| `error_stage` 全链路补录 | ✅ | 11 个节点均返回 stage 名而非 `"error"` |
| 3 个阶段 error_stage 验证 | ✅ | 覆盖 13 个测试（含 missing version / missing audits / unknown decision） |
| 向后兼容 | ✅ | 旧 JSONL 无 `_metrics_version` 仍可解析，默认填充 v3.1 |
| `pytest tests/test_run_logger.py` 通过 | ✅ | 16 passed |
| 更新 STATUS.md | ✅ | 测试数 1148→1161，070 标记完成 |
| 生成 DONE 文件 | ✅ | 本文件 |

---

## 参考

- `src/songyan/models/run_log.py` — `ChapterRunLog` 模型
- `src/songyan/workflows/_nodes.py` — 各节点 error stage 实现
- `tests/test_error_stage.py` — 全节点 error stage 单元测试
