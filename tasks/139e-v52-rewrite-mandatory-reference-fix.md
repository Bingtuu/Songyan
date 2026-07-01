> **任务编号**: 139e
> **类型**: Bugfix
> **状态**: ✅ 已完成
> **前置**: Task 139b 在 Ch21 触发 `health_low_p1_halt`，根因已定位为 `rewrite_node` 丢失 mandatory reference 约束。
> **依赖**: `src/songyan/workflows/_nodes.py`、`src/songyan/workflows/_helpers.py`、`tests/test_rewrite_node.py`。
> **修复时间**: 2026-06-30
> **验证结果**: `tests/test_rewrite_node.py` 16 passed；全量 pytest 2033 passed / 1 xfailed；Task 139b 已重新启动后台实跑（`bash-gzdafv5c`）。

## 背景

Task 139b（enforce 模式 Ch1-Ch50 实跑）在 Ch21 触发 AutoHalt：

```
health_low_p1_halt: P1_count=1 (state_mismatch or critical orphaned setting)
```

P1 来自 critical setting `scifi.main_deck.chen_luo_log`（Ch13 引入，Ch17 后未再提及）。

## 根因

完整链路：

1. Ch21 ContextManager 正确加载 mandatory reference `chen_luo_log`；
2. Writer 初稿未提及 → RuleAuditor 报 `mandatory_reference_check_passed=False`；
3. RevisionHandler 第一次 MR patch（rev-21-2）在正文中添加了一处"日志"提及；
4. 后续 revision 触发 `revision_rebound_detected`，回滚到 rev-21-2 后进入 `rewrite_node`；
5. `rewrite_node` 只注入了 `avoid_list` 和 `word_count_constraint`，**未注入 mandatory references**；
6. Rewrite 生成的 v-21-4 再次缺失 `chen_luo_log` 提及；
7. Human gate accept v-21-4；
8. ContinuityAuditor 判定 `chen_luo_log` 仍为 orphan → P1 → enforce halt。

因此，这不是 enforce 阈值误触发，而是 rewrite 路径未继承 critical 回收约束的代码缺陷。

## 目标

修复 `rewrite_node`，使其在整章重写时保留 mandatory references 约束，确保 rewrite 版本不丢失 critical setting 回收。

## 验收标准

- [x] 修改 `src/songyan/workflows/_nodes.py` 的 `rewrite_node`，在 rewrite 前调用 `_load_critical_mandatory_references` 并注入 `ctx.human_instructions`。
- [x] 新增/更新 `tests/test_rewrite_node.py` 覆盖 rewrite 场景下 mandatory reference 被继承（新增 2 个用例）。
- [x] Task 139b 已重新启动后台实跑验证（新项目 `7229f28ee6f24fe685364bf9a1bc1f84`，后台任务 `bash-gzdafv5c`）。
- [x] 全量 pytest 通过（2033 passed, 1 xfailed）；`ruff check src/ tests/ scripts/run_139b_enforce_ch1_ch50.py` 通过。
- [x] 更新本任务文件为 DONE，并同步 `tasks/V5-README.md`。

## 实现步骤（已执行）

1. **代码修改**
   - 在 `rewrite_node` 中，组装完 `ctx` 后，调用 `_load_critical_mandatory_references(project_id, chapter_number, scenes_count)`；
   - 如果有 mandatory references，向 `ctx.human_instructions` 追加类型为 `mandatory_references` 的约束，内容包含 setting 中文名和回收要求；
   - 日志记录 `rewrite.injected_mandatory_references`。

2. **测试补强**
   - 在 `tests/test_rewrite_node.py` 新增 `TestRewriteNodeMandatoryReferences` 类，2 个用例：
     - `test_injects_mandatory_references`：存在 critical orphan 时注入约束；
     - `test_no_mandatory_references_when_empty`：无 critical orphan 时不注入。

3. **全量验证**
   - `pytest tests/test_rewrite_node.py -v`：16 passed；
   - 全量 pytest：2033 passed, 1 xfailed；
   - `ruff check src/ tests/ scripts/run_139b_enforce_ch1_ch50.py`：通过。

4. **重跑 Task 139b**
   - 新建 clean 项目 `7229f28ee6f24fe685364bf9a1bc1f84`（DB `.tmp/task139b_enforce_ch1_ch50_rerun.db`）；
   - 后台启动 enforce 模式 Ch1-Ch50 实跑（任务 `bash-gzdafv5c`）。
