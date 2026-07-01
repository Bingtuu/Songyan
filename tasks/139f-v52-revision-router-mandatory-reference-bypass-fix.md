> **任务编号**: 139f
> **类型**: Bugfix
> **状态**: ✅ 已完成
> **前置**: Task 139e 已修复 `rewrite_node` 丢失 mandatory reference 约束；Task 139b 重跑在 Ch24 再次因同一类问题触发 `health_low_p1_halt`。
> **依赖**: `src/songyan/workflows/phase1_graph.py`、`src/songyan/workflows/_nodes.py`、`tests/test_phase1_graph.py`。
> **修复时间**: 2026-06-30
> **验证结果**: `tests/test_phase1_graph.py::TestRevisionRouter` 12 passed；全量 pytest 2035 passed / 1 xfailed；Task 139b 已启动第二次后台重跑（`bash-51dxohn9`）。

## 背景

Task 139b 重跑在 Ch24 触发 AutoHalt：

```
health_low_p1_halt: P1_count=1 (state_mismatch or critical orphaned setting)
```

P1 来自 critical setting `alien_builder.remains.crystal_fragment`（Ch11 引入，Ch18 后未再提及）。

## 根因

完整链路：

1. Ch24 ContextManager 正确加载 mandatory reference `alien_builder.remains.crystal_fragment`；
2. Writer 初稿 v-24-1 未提及该 setting；
3. RuleAuditor 报 `mandatory_reference_check_passed=False`；
4. RevisionHandler MR patch 失败：`fixed_keys=[]`；
5. Revision 触发 `revision_rebound_detected`，回滚到 v-24-1；
6. `revision_router` 在 `_revision_rebound=True` 时直接 `return "pass"`，不再进入 revision/rewrite；
7. Human gate auto_confirm 直接 accept v-24-1；
8. ContinuityAuditor 判定该 setting 仍为 critical orphan → P1 → enforce halt。

Task 139e 只修复了 `rewrite_node` 缺失 mandatory reference 的问题，但未覆盖 `revision_rebound` 后的回滚 accept 路径。

## 目标

修复 `revision_router`，使其在 `_revision_rebound=True` 时仍检查当前回滚目标版本的 mandatory reference 状态；若未通过，强制进入 `rewrite_node` 而不是直接 pass。

## 验收标准

- [x] 修改 `src/songyan/workflows/phase1_graph.py` 的 `revision_router`，`_revision_rebound=True` 时仍检查 rule audit 的 `mandatory_reference_check_passed`。
- [x] 若回滚版本 mandatory reference 未通过，返回 `"rewrite"` 触发强制重写。
- [x] 在 `src/songyan/workflows/_nodes.py` 的 `review_merger_node` 回滚分支中加载回滚目标版本的 rule audit，并将 `_mandatory_reference_check_passed` 写入 state。
- [x] 新增 `tests/test_phase1_graph.py::TestRevisionRouter` 2 个用例覆盖上述场景。
- [x] 全量 pytest 通过（2035 passed, 1 xfailed）；`ruff check src/ tests/` 通过。
- [x] 更新本任务文件为 DONE，并同步 `tasks/V5-README.md`。

## 实现步骤（已执行）

1. **代码修改**
   - 在 `review_merger_node` 的两个回滚分支（rewrite rollback 与 revision rebound rollback）中，加载回滚目标版本（`active_best.version_id`）的 rule audit report，并将 `_mandatory_reference_check_passed` 写入返回 state；
   - 在 `revision_router` 的 `_revision_rebound=True` 分支中增加检查：若 `_mandatory_reference_check_passed=False`，返回 `"rewrite"` 触发强制重写；否则返回 `"pass"`。

2. **测试补强**
   - 在 `tests/test_phase1_graph.py::TestRevisionRouter` 新增 2 个用例：
     - `test_revision_rebound_with_mandatory_reference_failure_triggers_rewrite`
     - `test_revision_rebound_with_mandatory_reference_passed_goes_pass`

3. **验证**
   - `pytest tests/test_phase1_graph.py::TestRevisionRouter -v`：12 passed；
   - 全量 pytest：2035 passed, 1 xfailed；
   - `ruff check src/ tests/`：通过。

4. **重跑 Task 139b**
   - 新建 clean 项目 `6dde3f9083f54725b867a6100cefc7eb`（DB `.tmp/task139b_enforce_ch1_ch50_rerun2.db`）；
   - 后台启动 enforce 模式 Ch1-Ch50 实跑（任务 `bash-51dxohn9`）。
