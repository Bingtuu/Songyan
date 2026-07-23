# Task 121e DONE: Ch8 Settlement Foreshadowing Validation Fix

> **日期**: 2026-06-21
> **类型**: V5.1 preflight / settlement 校验修复
> **状态**: DONE
> **前置**: Task 121d `run-f749826e` 已验证 Ch5 阻断解除，并暴露 Ch8 `settlement_review` 新阻断。

---

## 1. 任务边界

本任务只修复 Ch8 暴露的 settlement 伏笔预计回收章节校验逻辑。

不做：

- Prompt 调优。
- QualityGate 阈值调整。
- workflow 节点新增或路由调整。
- 降低 settlement 校验强度。

---

## 2. 根因

Task 121d 的 Ch8 在 rewrite fallback 后正常进入 settlement：

```text
rewrite.struct_integrity_rollback_decision chapter_number=8
  rollback_source=active_best rollback_version_id=rev-8-3-2160c17c
  recovered_with_qg_pass=True skip_settlement=False
```

随后 SettlementExtractor 输出 3 个新埋设伏笔，`expected_resolve_chapter=8`。旧校验将 `plant` 伏笔的 `expected_resolve_chapter <= chapter_number` 一律判为错误：

```text
settlement.validation_failed
  "预计回收章节 (8) 必须大于当前章节 (8)"
```

这类同章值更接近 LLM 对“近期/马上回收”的表达偏差。对 `plant` 操作而言，同章回收不应直接进入人工复核；安全做法是回填到下一章。早于当前章节的值仍然是硬错误。

---

## 3. 修复内容

修改文件：

- `src/songyan/agents/settlement_extractor/_validate.py`
- `tests/test_settlement_extractor.py`

规则：

- `expected_resolve_chapter == chapter_number`：回填为 `chapter_number + 1`，并记录 `settlement.foreshadowing_expected_chapter_backfilled`。
- `expected_resolve_chapter < chapter_number`：继续报错，保持硬校验。
- `expected_resolve_chapter > chapter_number`：保持原行为。

---

## 4. 验证

已执行：

```powershell
python -m py_compile src\songyan\agents\settlement_extractor\_validate.py
python -m pytest tests\test_settlement_extractor.py -q
python -m pytest tests\test_phase1_graph.py tests\test_108_core_nodes.py tests\test_run_logger.py -q
ruff check src\ tests\
python -m pytest tests/ -q
```

结果：

- `tests/test_settlement_extractor.py`: `62 passed, 1 xfailed`
- 相关节点测试：输出 `70 passed`
- `ruff check src\ tests\`: passed
- 全量回归：`1720 passed, 1 xfailed, 1 xpassed, 14 warnings`

说明：相关节点 pytest 在 Windows 下输出完整 summary 后出现 teardown 未释放，已按现有协议视为断言通过。

---

## 5. 重跑验证结果

已重跑 Ch1-Ch150 single-run，结果为 `partial`。

| 项 | 值 |
|----|----|
| project_id | `59b39402b87b4147a0cdc5b2d3915aec` |
| run_id | `run-0317a247` |
| 章节范围 | Ch1-Ch150 |
| 实际完成 | Ch1-Ch17 成功，Ch18 失败 |
| JSONL | `logs/chapter_runs/run-0317a247.jsonl` |
| report | `logs/reports/report-run-0317a247.md` |
| wrapper stdout | `logs/task121e/songyan-task121e-ch1-ch150-rerun-after-121e-20260621-121551.out.log` |
| wrapper result | `logs/task121e/songyan-task121e-ch1-ch150-rerun-after-121e-20260621-121551.result.txt` |

关键结论：

- Ch8 已成功越过旧 `settlement_review` 阻断。
- Ch1-Ch17 均成功，且 `settlement_success=true`、`summary_success=true`、`skip_settlement=false`。
- ContextEmergency 次数为 0。
- Ch18 是新的首个失败点。

Ch18 失败原因：

```text
CreativeDirector LLM call failed:
LLM 返回内容无法解析为 JSON:
Expecting ',' delimiter: line 7 column 72 (char 279)
```

补充观察：

- Ch18 后续正文、settlement 和 summary 实际继续走完。
- 日志显示 `settlement.validation_passed`、`settlement.applied`、`summary_writer.generated`。
- 但 run logger 仍按前置 CreativeDirector 错误将 Ch18 标为失败，并写出 `settlement_success=false`。

因此下一步建议创建 Task 121f，专门处理 CreativeDirector JSON parse failure 后的错误传播和章节成功判定契约：若后续正文、settlement、summary 已成功，不能让前置非致命 CreativeDirector parse error 污染最终章节状态。
