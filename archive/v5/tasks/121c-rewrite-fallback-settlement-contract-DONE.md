# Task 121c DONE — Rewrite Fallback Settlement Contract

> **日期**: 2026-06-21
> **类型**: V5.0 single-run 阻断修复
> **结论**: 已修复 rewrite 回退到可结算版本后 `_skip_settlement=True` 继续阻断 settlement 的问题。

---

## 1. 背景

Task 121b 的 single-run rehearsal `run-21ff158b` 从 Ch1 开始执行，Ch1-Ch4 成功，Ch5 阻断。

Ch5 关键链路：

```text
rewrite.struct_integrity_failed reason=missing_ending_hook
human_gate.decision decision=accept version_id=rev-5-3-4c8f78c7
settlement_extractor_node.skipping_settlement version_id=rev-5-3-4c8f78c7
project_pipeline.end completed=[1, 2, 3, 4] failed=[5] final_status=partial
```

根因不是 ContextEmergency 或 budget，而是工作流状态契约过宽：

- rewrite 失败后已经回退到可结算的 best / previous version。
- 但 `_skip_settlement=True` 仍被透传到 settlement 节点。
- auto-confirm accept 后 settlement 被跳过，违反“accept 后必须 settlement”的 P0 规则。

---

## 2. 修复内容

修改 `src/songyan/workflows/_nodes.py`：

1. `rewrite_node`
   - 结构完整性失败时，若能回退到 active best 或 rewrite 前版本，则 `_skip_settlement=False`。
   - 只有没有任何可回滚版本、当前只能指向结构失败 rewrite 时，才保留 `_skip_settlement=True`。
   - QG 是否通过继续由 `_quality_gate_passed` 记录；收敛失败继续由 `_convergence_failed` 记录。

2. `quality_gate_node`
   - 修复耗尽且 QG 仍失败时，如果能回滚到 active best，则不再跳过 settlement。
   - QG 合格 best 仍恢复为 `_quality_gate_passed=True`。
   - QG 不合格但可结算 best 则保留 `_quality_gate_passed=False` / `_convergence_failed=True`，但允许 settlement 执行。
   - 无 active best / 无可结算 score card 时，仍设置 `_skip_settlement=True` 并进入人工复核。

---

## 3. 测试覆盖

更新 `tests/test_107_convergence_guardrail.py`：

- rewrite scene_count 结构失败回滚 best 后，不跳过 settlement。
- rewrite 缺 ending hook 回滚 best 后，不跳过 settlement。
- 无 QG best 但可回滚 previous version 时，不跳过 settlement。
- rewrite 后 QG 仍失败但回滚 best 时，不跳过 settlement。
- 两轮 revision 后 QG 仍失败但回滚 best 时，不跳过 settlement。
- 无 best version 时仍阻断 settlement，保留原保护。

---

## 4. 验证结果

```powershell
python -m pytest tests/test_107_convergence_guardrail.py tests/test_108_core_nodes.py tests/test_100b_quality_gate.py tests/test_phase1_graph.py -q
ruff check src/ tests/
python -m pytest tests/ -q
git diff --check
```

结果：

- 聚焦测试：`83 passed`。pytest 已输出通过摘要后，Windows teardown 未释放本次 Python 进程，已按协议清理。
- `ruff check src/ tests/`: All checks passed.
- 全量回归：`1718 passed, 2 xfailed, 15 warnings`，`WRAPPER_RESULT=PASS_NORMAL_EXIT`。
- `git diff --check`: 通过。

---

## 5. 已知限制

- 本任务只修复 settlement 被错误跳过的工作流契约。
- 未做 Prompt 调优，也未修复 Ch5 rewrite 内容本身的 `missing_ending_hook`。
- 仍需重跑 Ch1-Ch150 single-run rehearsal，确认 Ch5 不再因 settlement skip 阻断，并观察是否暴露下一处质量或长跑瓶颈。

下一步建议：执行 Task 121d，重跑 Ch1-Ch150 single-run rehearsal。
