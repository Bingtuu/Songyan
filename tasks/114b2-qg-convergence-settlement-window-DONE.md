# Task 114b2: QG 收敛阻断处理 + Settlement 端到端验证窗口 — 完成报告

> **Phase**: V5.0 Phase 4 — 150 章规模化验证前置复核
> **优先级**: P0
> **状态**: ✅ 完成，Task 114c 可启动
> **开始时间**: 2026-06-20
> **完成时间**: 2026-06-20

---

## 执行结果摘要

Task 114b2 已完成 Ch102/Ch103 的 QG 收敛阻断处理，并用组合短窗口验证 `accept + settlement + summary` 端到端穿透。

最终通过窗口：

```text
songyan run --project-id proj-e74ef1e4 --chapters 102-103 --mode-id webnovel_intense --auto-confirm
Run ID: run-af3ba939
Result: completed=[102, 103], failed=[], final_status=completed
```

### 最终验收结果

| 章节 | Run ID | 版本 | settlement | summary | run_logger |
|------|--------|------|------------|---------|------------|
| Ch102 | `run-af3ba939` | `rev-102-19-b2cba480` | ✅ `settlement.validation_passed` + `settlement_applied` | ✅ `sum-proj-e74ef1e4-102-a5450a64` | ✅ `success=True` |
| Ch103 | `run-af3ba939` | `rev-103-18-416a655e` | ✅ `old_value_backfilled` + `settlement.validation_passed` + `settlement_applied` | ✅ `sum-proj-e74ef1e4-103-cabd23b8` | ✅ `success=True` |

---

## 根因与修复

### 1. 历史修复状态污染

Task 114b 的 Ch102/Ch103 回放一开始就被判定为修复耗尽，根因是 `_load_chapter_repair_state()` 按章节统计所有历史非废弃 revision/rewrite，导致新回放继承旧 run 的修复次数。

修复：

- `_load_chapter_repair_state()` 新增 `current_version_id` 参数。
- 当存在当前版本时，仅沿 `parent_version_id` 链计算当前 lineage 的 revision/rewrite 状态。
- 保留旧的全章节 fallback，兼容 legacy 调用和历史测试。

### 2. QG 失败版本被保存为 best

Ch103 中曾出现 readability 失败初稿被保存为 best，后续收敛终点回滚到仍然 QG 不合格的版本。

修复：

- 新增 `_score_card_passes_quality_gate()`，用完整 `ChapterScoreCard` flags 判断 QG 硬门是否通过。
- `review_merger_node()` 只允许 QG 合格版本作为 settlement 前的 best 回滚目标。
- QG 不合格但未反弹的版本不覆盖 best，继续进入后续修复链路。

### 3. QG 收敛终点未复用合格 best

当当前版本 QG 失败且修复耗尽时，旧逻辑即使存在 QG 合格 best，也会设置 `_skip_settlement=True`。

修复：

- `quality_gate_node()` 在收敛终点加载 active best。
- 若 best 的 score_card 满足 QG 硬门，则回滚 head 到 best，并清空 `_skip_settlement` / `_settlement_needs_human_review`。
- 该路径继续进入 human gate，再执行 settlement。

### 4. rewrite 结构失败后的图路由错误

组合窗口首次复跑暴露出新的边界：`rewrite_node()` 结构完整性失败时已返回 `status="human_confirm"`，但 graph 使用固定边 `rewrite -> rule_auditor`，导致失败 rewrite 版本继续审查，并携带旧 `_skip_settlement` 进入 accept。

修复：

- 新增 `rewrite_router()`。
- `rewrite` 节点改为条件边：
  - `status="human_confirm"` → `human_confirm`
  - 其他正常 rewrite → `rule_auditor`

---

## 关键日志证据

### Ch102 最终通过

日志：`logs/task114/songyan-114b2-ch102-103-r3-20260620-120742.out.log`

```text
2026-06-20 12:12:20 [info] settlement.validation_passed
2026-06-20 12:12:21 [info] settlement_extractor_node.settlement_applied chapter_number=102 version_id=rev-102-19-b2cba480
2026-06-20 12:12:25 [info] summary_writer.generated chapter_number=102 summary_id=sum-proj-e74ef1e4-102-a5450a64
2026-06-20 12:12:32 [info] run_logger.chapter_logged chapter_number=102 run_id=run-af3ba939 success=True
```

### Ch103 最终通过

日志：`logs/task114/songyan-114b2-ch102-103-r3-20260620-120742.out.log`

```text
2026-06-20 12:18:20 [info] settlement.old_value_backfilled chapter_number=103 character_id=char-ce09ac00 field=mental_state
2026-06-20 12:18:20 [info] settlement.validation_passed
2026-06-20 12:18:21 [info] settlement_extractor_node.settlement_applied chapter_number=103 version_id=rev-103-18-416a655e
2026-06-20 12:18:25 [info] summary_writer.generated chapter_number=103 summary_id=sum-proj-e74ef1e4-103-cabd23b8
2026-06-20 12:18:27 [info] run_logger.chapter_logged chapter_number=103 run_id=run-af3ba939 success=True
2026-06-20 12:18:28 [info] project_pipeline.end completed=[102, 103] failed=[] final_status=completed run_id=run-af3ba939
```

---

## 验证命令

### 聚焦测试

```bash
python -m pytest tests/test_phase1_graph.py::TestRewriteRouter tests/test_107_convergence_guardrail.py tests/test_108_core_nodes.py::TestLoadChapterRepairStateExcludesAbandoned -q
```

结果：**18 passed**

### Ch102/Ch103 端到端窗口

```bash
songyan run --project-id proj-e74ef1e4 --chapters 102-103 --mode-id webnovel_intense --auto-confirm
```

结果：**completed=[102, 103], failed=[], final_status=completed** (`run-af3ba939`)

### 最终回归

```bash
python -m pytest tests/ -v
```

结果：**1671 passed, 4 skipped, 2 xfailed, 3 xpassed**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`。

```bash
python -m pytest tests/ -q
```

结果：**1671 passed, 4 skipped, 2 xfailed, 3 xpassed**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`。

```bash
ruff check src/ tests/
```

结果：**未通过，113 个历史存量 lint**（主要为未触碰测试文件中的 E501/F841）。

```bash
ruff check src/songyan/agents/settlement_extractor/__init__.py src/songyan/agents/settlement_extractor/_quote_filter.py src/songyan/agents/settlement_extractor/_validate.py src/songyan/evals/score_aggregator.py src/songyan/workflows/_nodes.py src/songyan/workflows/_run_logger.py src/songyan/workflows/phase1_graph.py tests/test_106_scoring_system.py tests/test_107_convergence_guardrail.py tests/test_108_core_nodes.py tests/test_phase1_graph.py tests/test_quote_filter.py tests/test_settlement_extractor.py
```

结果：**All checks passed!**

---

## 改动文件

- `src/songyan/workflows/_nodes.py`
- `src/songyan/workflows/phase1_graph.py`
- `tests/test_107_convergence_guardrail.py`
- `tests/test_108_core_nodes.py`
- `tests/test_phase1_graph.py`
- `tasks/114b2-qg-convergence-settlement-window-DONE.md`
- `docs/STATUS.md`
- `README.md`
- `docs/INDEX.md`
- `tasks/114-ch101-ch150-streaming-validation.md`

---

## 已知限制

1. Ch102/Ch103 的内容质量仍存在 LLM 随机波动；本 Task 不做 Prompt 调优或 QG 阈值放宽。
2. 组合窗口中曾出现一次 CreativeDirector JSON parse 偶发失败，后续重跑通过；该问题不属于 QG 收敛根因，但后续长跑仍需监控。
3. Task 114b 仍未补完 Ch104-Ch110；当前结论仅解除进入 Task 114c 前的 Ch102/Ch103 settlement 端到端门禁。

---

## 下一步

进入 Task 114c：按 `tasks/114-ch101-ch150-streaming-validation.md` 分段执行 Ch111-Ch130、Ch131-Ch150，并生成 DG-2 报告。
