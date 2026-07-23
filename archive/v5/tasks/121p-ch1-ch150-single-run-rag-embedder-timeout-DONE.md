# Task 121p: Ch1-Ch150 Full Single-Run — RAG Embedder Timeout Blocker — DONE

- **状态**: DONE
- **完成日期**: 2026-06-26
- **原始任务**: `tasks/121p-ch1-ch150-single-run-rag-embedder-timeout.md`

---

## 目标摘要

Task 121p 原计划在 Task 121o（Ch1-Ch18 18/18 成功）基线上启动新的干净项目，执行 Ch1-Ch150 full single-run 以获取 V5.0 一次性单命令证据。首次运行 `run-40ceb306` 在 Ch1 完成后因 RAG 向量索引超时崩溃；本任务定位并修复了导致中断的两个工程缺陷。

## 关键改动 / 交付物

### Bug A：Pipeline 未跳过已有 accepted 章节
- **位置**: `src/songyan/workflows/phase2_graph.py:328-339`
- **修复**: `run_project_pipeline` 启动前查询 `chapter_heads`，获取当前项目所有 `status='accepted'` 的章节号，遍历章节范围时直接跳过，避免重复生成。

### Bug B：RAG 索引超时异常未捕获
- **位置**: `src/songyan/workflows/_helpers.py:518`
- **修复**: catch 块增加 `TimeoutError`，确保 `asyncio.wait_for` 超时不再穿透。
- **位置**: `src/songyan/workflows/_nodes.py:2246`
- **修复**: settlement 后的 RAG 索引 catch 块同样增加 `TimeoutError`。
- **位置**: `src/songyan/rag/embedder.py:123`
- **修复**: embedding 超时从 `30.0` 秒延长至 `120.0` 秒，覆盖模型首次冷加载。

## 验证证据

| 项 | 值 |
|---|---|
| 原始失败 run_id | `run-40ceb306`（2026-06-22 22:29 启动，22:35 中断） |
| 失败根因 | Bug A：Ch1 已有 accepted 状态仍被重新生成；Bug B：RAG 索引 `CancelledError` 未捕获 |
| 修复后重跑 run_id | `run-2d7d96c2` |
| 修复后结果 | Ch1-Ch3 成功；Ch4 因 0.82 质量阈值阻断 |
| 后续演进 | Task 121q 继续解决 0.82 阈值问题，并启动 `run-a2bed648` 完成 Ch1-Ch150 150/150 全部成功 |

- 当前全量测试：`1828 passed, 1 xfailed, 2 warnings`
- 当前 lint：`ruff check src/ tests/` 通过

## 遗留 / 后续

- Ch4 的 0.82 阈值阻断由 **Task 121q** 通过动态阈值（Ch1-Ch20→0.75、Ch21-Ch50→0.78、Ch51+→0.82）和 `degraded_accept` 降级回滚路径解决。
- Ch1-Ch150 一次性单命令最终证据由 **Task 121q** `run-a2bed648` 完成：150/150 全部成功，ContextEmergency 0 次，AutoHalt 0 次。
